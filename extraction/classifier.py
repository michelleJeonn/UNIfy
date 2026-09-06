"""
The learned extractor: model definition, checkpoint loading, and inference.

Two heads are supported, because the data justifies one and the brief asked for the
other, and it is cheaper to build both than to argue about it.

`multilabel` -- DistilBERT with 32 sigmoid outputs over the segment text. The
    textbook formulation. At this data size it has a real problem: the rarest labels
    (accessible_parking_transit, 2 silver positives; reduced_course_load, 3) get a
    dedicated output unit trained on almost nothing, and share no parameters with the
    29 labels that do have data.

`cross-encoder` (default) -- one binary output over the pair
    "<label name>: <seeds> [SEP] <segment text>". Every label's examples now train the
    *same* parameters, so a rare label is carried by the 740 positives belonging to
    the others, and a label's own definition text is an input rather than an index.
    It is also, unchanged, the reranker the hybrid needs: score(label, segment).

The cost is inference shape -- 1,169 texts x 32 labels = 37,408 forward passes for a
full corpus pass instead of 1,169. At this corpus size that is seconds, and the
hybrid reduces it further by only scoring retrieved candidates.

Inference produces a probability per (segment, label). A cell is the **max over that
university's segments**: one sentence evidencing an accommodation is enough to say the
school has it, which is the same rule the keyword baseline uses (`any hit -> 1`) and
keeps every positive traceable to the specific segment that produced it.

Usage:
    python extraction/classifier.py --model-dir models/cross_encoder_text
    python extraction/classifier.py --model-dir models/... --threshold 0.5
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

MAX_LENGTH = 192          # corpus max is 657 chars; nothing is truncated in practice
DEFAULT_BATCH = 128


def pair_text(label: dict) -> str:
    """The label side of a cross-encoder pair.

    Name plus seeds, and deliberately not the definition: definitions are written with
    negation ("does not include wayfinding help"), and a bi- or cross-encoder trained
    at this scale represents negated text close to its affirmation, so feeding them in
    pulls the query toward the cases the definition exists to exclude. Same reasoning
    as embedding.label_queries, and kept identical on purpose so the retrieval stage
    and the reranker agree about what a label *is*.
    """
    return f"{label['name']}: " + ", ".join(label["seeds"])


class Classifier:
    """Loads a trained checkpoint and scores (segment, label) pairs."""

    def __init__(self, model_dir: str, device: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        with open(os.path.join(model_dir, "config.json.unify"), encoding="utf-8") as handle:
            self.config = json.load(handle)
        self.head = self.config["head"]
        self.label_ids = self.config["label_ids"]
        self.torch = torch
        if device is None:
            device = ("mps" if torch.backends.mps.is_available()
                      else "cuda" if torch.cuda.is_available() else "cpu")
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(device).eval()

    def _forward(self, first: list[str], second: list[str] | None,
                 batch_size: int) -> np.ndarray:
        outputs = []
        with self.torch.no_grad():
            for start in range(0, len(first), batch_size):
                chunk_a = first[start:start + batch_size]
                chunk_b = second[start:start + batch_size] if second else None
                encoded = self.tokenizer(chunk_a, chunk_b, truncation=True,
                                         max_length=MAX_LENGTH, padding=True,
                                         return_tensors="pt").to(self.device)
                logits = self.model(**encoded).logits
                outputs.append(self.torch.sigmoid(logits).float().cpu().numpy())
        return np.concatenate(outputs) if outputs else np.zeros((0, 1))

    def score(self, texts: list[str], labels: list[dict],
              batch_size: int = DEFAULT_BATCH,
              candidates: np.ndarray | None = None) -> np.ndarray:
        """Probabilities, shape [len(texts), len(labels)].

        `candidates` is an optional boolean mask of the same shape. Pairs outside it
        are not scored and come back as 0 -- that is how hybrid.py spends the
        classifier only on what retrieval surfaced.
        """
        index = {label_id: position for position, label_id in enumerate(self.label_ids)}
        result = np.zeros((len(texts), len(labels)), dtype=np.float32)

        if self.head == "multilabel":
            probabilities = self._forward(texts, None, batch_size)
            for column, label in enumerate(labels):
                if label["id"] in index:
                    result[:, column] = probabilities[:, index[label["id"]]]
            if candidates is not None:
                result = np.where(candidates, result, 0.0)
            return result

        for column, label in enumerate(labels):
            rows = (np.nonzero(candidates[:, column])[0] if candidates is not None
                    else np.arange(len(texts)))
            if len(rows) == 0:
                continue
            query = pair_text(label)
            probabilities = self._forward([query] * len(rows),
                                          [texts[r] for r in rows], batch_size)
            result[rows, column] = probabilities[:, 0]
        return result


def load_corpus(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def budget_threshold(scores: np.ndarray, budget: int) -> float:
    """The cut-off that emits exactly `budget` positive cells.

    Same protocol embedding.py uses, and for the same reason: tuning a threshold
    against the gold set would make the comparison meaningless, since the keyword
    baseline never got to tune anything against it. This reads predictions, never
    gold, and makes every system spend an identical budget of positives -- so the
    score answers the only comparable question: given the same number of calls,
    whose are better placed?
    """
    flat = np.sort(scores.flatten())[::-1]
    position = min(budget, len(flat) - 1)
    return float(flat[position])


def write_outputs(out_dir: str, name: str, universities: list[str], labels: list[dict],
                  matrix: np.ndarray, scores: np.ndarray, best: np.ndarray,
                  segments: list[dict], source: str) -> tuple[str, str]:
    """Emit the same two files every extractor here emits, so evaluate.py scores it
    unchanged and claude_recommender.py can read it without knowing what made it."""
    os.makedirs(out_dir, exist_ok=True)
    matrix_path = os.path.join(out_dir, f"accommodations_{name}.csv")
    with open(matrix_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["university"] + [l["id"] for l in labels])
        for row, university in enumerate(universities):
            writer.writerow([university] + list(matrix[row]))

    detail_path = os.path.join(out_dir, f"accommodations_{name}.jsonl")
    with open(detail_path, "w", encoding="utf-8") as handle:
        for row, university in enumerate(universities):
            for column, label in enumerate(labels):
                segment = segments[int(best[row, column])]
                handle.write(json.dumps({
                    "university": university,
                    "label": label["id"],
                    "value": int(matrix[row, column]),
                    "source": source,
                    "score": round(float(scores[row, column]), 4),
                    "citations": [segment["segment_id"]],
                    "evidence": [segment["text"][:160]],
                }, ensure_ascii=False) + "\n")
    return matrix_path, detail_path


def cells_from_segments(probabilities: np.ndarray, segments: list[dict],
                        universities: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Collapse per-segment probabilities to per-(university, label), keeping the
    argmax segment so every cell still cites the sentence that produced it."""
    index = {university: position for position, university in enumerate(universities)}
    scores = np.zeros((len(universities), probabilities.shape[1]), dtype=np.float32)
    best = np.zeros_like(scores, dtype=np.int64)
    for position, segment in enumerate(segments):
        row = index[segment["university"]]
        better = probabilities[position] > scores[row]
        scores[row] = np.where(better, probabilities[position], scores[row])
        best[row] = np.where(better, position, best[row])
    return scores, best


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--baseline", default=os.path.join(_ROOT, "data/clean/accommodations_baseline.jsonl"),
                        help="used only to match the total positive budget; no gold is read")
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/clean"))
    parser.add_argument("--name", default="classifier")
    parser.add_argument("--threshold", type=float, default=None,
                        help="fixed cut-off; default matches the keyword baseline's positive budget")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args()

    with open(args.taxonomy, encoding="utf-8") as handle:
        labels = json.load(handle)["labels"]
    segments = load_corpus(args.evidence)
    universities = sorted({s["university"] for s in segments})

    classifier = Classifier(args.model_dir)
    print(f"[info] {classifier.head} head on {classifier.device}, "
          f"scoring {len(segments):,} segments x {len(labels)} labels")
    probabilities = classifier.score([s["text"] for s in segments], labels,
                                     batch_size=args.batch_size)
    scores, best = cells_from_segments(probabilities, segments, universities)

    if args.threshold is None:
        budget = sum(json.loads(line)["value"]
                     for line in open(args.baseline, encoding="utf-8"))
        threshold = budget_threshold(scores, budget)
        print(f"[info] matching the keyword baseline's {budget} positive cells puts "
              f"the threshold at {threshold:.4f}")
    else:
        threshold = args.threshold
    matrix = (scores > threshold).astype(int)

    matrix_path, detail_path = write_outputs(
        args.out_dir, args.name, universities, labels, matrix, scores, best,
        segments, classifier.head)
    print(f"[ok]   {len(universities)} universities x {len(labels)} labels "
          f"({int(matrix.sum())} positive cells)")
    for path in (matrix_path, detail_path):
        print(f"[info] wrote {os.path.relpath(path, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
