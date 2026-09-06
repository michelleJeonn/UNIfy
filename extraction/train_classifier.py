"""
Train the accommodation classifier on the silver dataset.

Fine-tunes a small pretrained encoder on the distant-supervision labels built by
dataset.py. Nothing here reads the human gold set -- not for early stopping, not for
threshold selection, not for choosing a backbone. Model selection is on a silver
validation split, which is a weaker signal than gold but the only one that keeps the
final comparison honest.

Heads (see classifier.py for why both exist):
    --head cross-encoder   pair "<label>: <seeds> [SEP] <text>" -> 1 sigmoid  (default)
    --head multilabel      text -> 32 sigmoids

Class imbalance is 2% positive. The two heads handle it differently:
    cross-encoder  negative *sampling*, `--neg-ratio` per positive, half of them mined
                   as the highest-cosine true negatives for that label. Random
                   negatives alone are trivially separable ("Accessible parking" vs
                   "Braille") and the model learns nothing from them.
    multilabel     no sampling is possible (an example carries all 32 targets at once),
                   so imbalance is handled with per-label `pos_weight` in the loss.

Masked pairs (-1) carry zero weight in both. They are the band where the keyword
labels are least trustworthy; supervising them would teach the model the baseline's
false negatives.

Usage:
    python extraction/train_classifier.py
    python extraction/train_classifier.py --split university --out models/cross_encoder_uni
    python extraction/train_classifier.py --head multilabel --backbone distilbert-base-uncased
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from classifier import MAX_LENGTH, pair_text          # noqa: E402

CROSS_ENCODER_BACKBONE = "sentence-transformers/all-MiniLM-L6-v2"
MULTILABEL_BACKBONE = "distilbert-base-uncased"


def load(dataset_path: str, splits_path: str, mode: str):
    with open(dataset_path, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    with open(splits_path, encoding="utf-8") as handle:
        splits = json.load(handle)
    assignment = {}
    for name, ids in splits["splits"][mode].items():
        for text_id in ids:
            assignment[text_id] = name
    for row in rows:
        row["split"] = assignment.get(row["text_id"], "train")
    return rows, splits


def subset(rows: list[dict], split: str) -> list[dict]:
    return [row for row in rows if row["split"] == split]


def build_pairs(rows: list[dict], labels: list[dict], neg_ratio: int,
                rng: random.Random) -> list[tuple[str, str, float]]:
    """Cross-encoder training pairs: every positive, plus sampled negatives.

    Half the negatives are the highest-cosine true negatives for that label -- the
    ones the retrieval stage would surface and the reranker therefore has to reject.
    The other half are uniform, so the model still sees the easy majority it will
    mostly be asked about at inference time.
    """
    pairs = []
    for label in labels:
        label_id = label["id"]
        query = pair_text(label)
        positives = [r for r in rows if r["labels"][label_id] == 1]
        negatives = [r for r in rows if r["labels"][label_id] == 0]
        if not positives:
            continue
        for row in positives:
            pairs.append((query, row["text"], 1.0))
        wanted = min(len(negatives), neg_ratio * len(positives))
        hard_count = wanted // 2
        by_similarity = sorted(negatives, key=lambda r: -r["cos"][label_id])
        chosen = by_similarity[:hard_count]
        remainder = by_similarity[hard_count:]
        rng.shuffle(remainder)
        chosen += remainder[:wanted - hard_count]
        for row in chosen:
            pairs.append((query, row["text"], 0.0))
    rng.shuffle(pairs)
    return pairs


def average_precision(scores: np.ndarray, targets: np.ndarray) -> float:
    """AP for one label. Threshold-free, so it does not smuggle a cut-off into model
    selection the way F1-at-0.5 would."""
    if targets.sum() == 0:
        return float("nan")
    order = np.argsort(-scores)
    hits = targets[order]
    cumulative = np.cumsum(hits)
    precision = cumulative / (np.arange(len(hits)) + 1)
    return float((precision * hits).sum() / hits.sum())


def evaluate_silver(model, tokenizer, torch, device, rows: list[dict],
                    labels: list[dict], head: str, batch_size: int) -> dict:
    """Macro average precision on the silver validation split. Masked pairs excluded."""
    model.eval()
    texts = [row["text"] for row in rows]
    matrix = np.zeros((len(rows), len(labels)), dtype=np.float32)

    def run(first, second):
        out = []
        with torch.no_grad():
            for start in range(0, len(first), batch_size):
                encoded = tokenizer(first[start:start + batch_size],
                                    second[start:start + batch_size] if second else None,
                                    truncation=True, max_length=MAX_LENGTH,
                                    padding=True, return_tensors="pt").to(device)
                out.append(torch.sigmoid(model(**encoded).logits).float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 1))

    if head == "multilabel":
        matrix = run(texts, None)
    else:
        for column, label in enumerate(labels):
            query = pair_text(label)
            matrix[:, column] = run([query] * len(texts), texts)[:, 0]

    aps, positives = [], 0
    per_label = {}
    for column, label in enumerate(labels):
        targets = np.array([row["labels"][label["id"]] for row in rows])
        keep = targets >= 0
        value = average_precision(matrix[keep, column], targets[keep].astype(float))
        per_label[label["id"]] = None if np.isnan(value) else round(value, 4)
        if not np.isnan(value):
            aps.append(value)
            positives += int(targets[keep].sum())
    model.train()
    return {"macro_ap": float(np.mean(aps)) if aps else float("nan"),
            "labels_scored": len(aps), "val_positives": positives,
            "per_label_ap": per_label}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=os.path.join(_ROOT, "data/ml/dataset.jsonl"))
    parser.add_argument("--splits", default=os.path.join(_ROOT, "data/ml/splits.json"))
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--split", choices=["text", "university"], default="text")
    parser.add_argument("--head", choices=["cross-encoder", "multilabel"],
                        default="cross-encoder")
    parser.add_argument("--backbone", default=None)
    parser.add_argument("--out", default=None)
    # 8, because all three configurations were still improving at 4 and the best epoch
    # landed at 6, 8 and 6 respectively. The best-scoring epoch is what gets saved, so
    # a longer run costs time rather than quality.
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--neg-ratio", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    for path in (args.dataset, args.splits, args.taxonomy):
        if not os.path.exists(path):
            print(f"[error] missing input: {path}\n"
                  f"        Run: python extraction/dataset.py", file=sys.stderr)
            return 2

    backbone = args.backbone or (CROSS_ENCODER_BACKBONE if args.head == "cross-encoder"
                                 else MULTILABEL_BACKBONE)
    out_dir = args.out or os.path.join(
        _ROOT, "models", f"{args.head.replace('-', '_')}_{args.split}")

    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    with open(args.taxonomy, encoding="utf-8") as handle:
        labels = json.load(handle)["labels"]
    rows, splits = load(args.dataset, args.splits, args.split)
    train_rows, val_rows = subset(rows, "train"), subset(rows, "val")
    print(f"[info] split={args.split}  train {len(train_rows)} texts / "
          f"val {len(val_rows)} texts / test {len(subset(rows, 'test'))} texts")

    device = ("mps" if torch.backends.mps.is_available()
              else "cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(backbone)
    n_outputs = 1 if args.head == "cross-encoder" else len(labels)
    model = AutoModelForSequenceClassification.from_pretrained(
        backbone, num_labels=n_outputs, problem_type="multi_label_classification")
    model.to(device)

    if args.head == "cross-encoder":
        pairs = build_pairs(train_rows, labels, args.neg_ratio, rng)
        n_pos = sum(1 for p in pairs if p[2] == 1.0)
        print(f"[info] {len(pairs):,} training pairs ({n_pos:,} positive, "
              f"{len(pairs) - n_pos:,} negative; half of the negatives mined by cosine)")

        def collate(batch):
            queries = [b[0] for b in batch]
            texts = [b[1] for b in batch]
            targets = torch.tensor([[b[2]] for b in batch], dtype=torch.float)
            encoded = tokenizer(queries, texts, truncation=True, max_length=MAX_LENGTH,
                                padding=True, return_tensors="pt")
            return encoded, targets, None

        loader = DataLoader(pairs, batch_size=args.batch_size, shuffle=True,
                            collate_fn=collate)
        pos_weight = None
    else:
        targets = np.array([[row["labels"][l["id"]] for l in labels] for row in train_rows],
                           dtype=np.float32)
        weight = (targets >= 0).astype(np.float32)          # masked pairs weigh nothing
        clean = np.clip(targets, 0, 1)
        counts = clean.sum(axis=0)
        # pos_weight = negatives/positives per label, capped: uncapped it reaches ~800
        # for the rarest label and the gradient from three examples dominates training.
        pos_weight = torch.tensor(
            np.clip((len(train_rows) - counts) / np.maximum(counts, 1), 1.0, 50.0),
            dtype=torch.float, device=device)
        print(f"[info] {len(train_rows):,} training texts x {len(labels)} labels; "
              f"pos_weight range {pos_weight.min():.1f}-{pos_weight.max():.1f}")
        items = list(zip([r["text"] for r in train_rows], clean, weight))

        def collate(batch):
            encoded = tokenizer([b[0] for b in batch], truncation=True,
                                max_length=MAX_LENGTH, padding=True, return_tensors="pt")
            target = torch.tensor(np.stack([b[1] for b in batch]), dtype=torch.float)
            mask = torch.tensor(np.stack([b[2] for b in batch]), dtype=torch.float)
            return encoded, target, mask

        loader = DataLoader(items, batch_size=args.batch_size, shuffle=True,
                            collate_fn=collate)

    optimiser = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = max(1, len(loader) * args.epochs)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimiser, max_lr=args.lr, total_steps=total_steps, pct_start=0.1)
    loss_fn = torch.nn.BCEWithLogitsLoss(reduction="none", pos_weight=pos_weight)

    history, best = [], {"macro_ap": -1.0, "epoch": None}
    os.makedirs(out_dir, exist_ok=True)
    started = time.time()
    model.train()
    for epoch in range(1, args.epochs + 1):
        running, seen = 0.0, 0
        for encoded, target, mask in loader:
            encoded = {k: v.to(device) for k, v in encoded.items()}
            target = target.to(device)
            logits = model(**encoded).logits
            loss = loss_fn(logits, target)
            if mask is not None:
                mask = mask.to(device)
                denominator = mask.sum().clamp(min=1.0)
                loss = (loss * mask).sum() / denominator
            else:
                loss = loss.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            scheduler.step()
            optimiser.zero_grad()
            running += float(loss) * target.shape[0]
            seen += target.shape[0]

        metrics = evaluate_silver(model, tokenizer, torch, device, val_rows, labels,
                                  args.head, args.eval_batch_size)
        history.append({"epoch": epoch, "train_loss": round(running / max(seen, 1), 5),
                        "val_macro_ap": round(metrics["macro_ap"], 4),
                        "labels_scored": metrics["labels_scored"]})
        marker = ""
        if metrics["macro_ap"] > best["macro_ap"]:
            # Selection is on silver, never on gold. Keeping the best epoch by a silver
            # signal is weaker than early stopping on real labels, and it is the price
            # of leaving the gold set untouched until the final evaluation.
            best = {"macro_ap": metrics["macro_ap"], "epoch": epoch,
                    "per_label_ap": metrics["per_label_ap"]}
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)
            marker = "  <- best, saved"
        print(f"[epoch {epoch}] loss {running / max(seen, 1):.5f}  "
              f"val macro-AP {metrics['macro_ap']:.4f}{marker}")

    with open(os.path.join(out_dir, "config.json.unify"), "w", encoding="utf-8") as handle:
        json.dump({"head": args.head, "backbone": backbone,
                   "label_ids": [l["id"] for l in labels],
                   "split": args.split, "seed": args.seed,
                   "held_out_universities": splits["held_out_universities"]
                   if args.split == "university" else [],
                   "epochs": args.epochs, "lr": args.lr,
                   "neg_ratio": args.neg_ratio if args.head == "cross-encoder" else None,
                   "supervision": "silver (keyword baseline distant supervision, "
                                  "ambiguous band masked); no human gold read"},
                  handle, indent=2)
    with open(os.path.join(out_dir, "train_report.json"), "w", encoding="utf-8") as handle:
        json.dump({"history": history, "best": best,
                   "train_texts": len(train_rows), "val_texts": len(val_rows),
                   "seconds": round(time.time() - started, 1)}, handle, indent=2)

    print(f"[ok]   best epoch {best['epoch']} at val macro-AP {best['macro_ap']:.4f} "
          f"({time.time() - started:.0f}s)")
    print(f"[info] wrote {os.path.relpath(out_dir, _ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
