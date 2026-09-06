"""
Build the training dataset for the learned accommodation extractor.

There are **no segment-level human labels in this project** -- the 165 hand-judged
cells in data/gold/ are judgments about a (university, label) pair, not about a
sentence. So supervised training on human annotation is not possible, and the
training signal has to come from somewhere else. It comes from the keyword
baseline: distant supervision.

That has an obvious ceiling problem. A classifier trained on keyword output learns
the keyword extractor, including its mistakes, and the honest expectation is that it
matches the baseline rather than beating it. One thing is done to break that:

    **The ambiguous band is masked out of the loss, not taught as negative.**

For each label, any segment the keyword missed but which the embedding rates at
least as on-topic as that label's own known positives is written as -1 (ignore)
instead of 0. Those are exactly the cases the baseline's error analysis blames for
its false negatives -- "private *exam* spaces" against the seed "private room" --
and teaching the model to reject them would train in the very failure we want it to
fix. Leaving them unsupervised lets the pretrained encoder decide.

The band is defined by a rule that reads no gold labels:

    mask if  keyword_missed  and  cos >= max(Q25(cos over that label's positives), 0.40)

Q25 rather than the minimum, because a single low-similarity positive would
otherwise swell the band to a third of the corpus. Measured, this masks 338 of
37,408 pairs (0.9%).

Splitting
---------
Two split modes are written, because one of them is a lie by itself.

`text` (default) -- unique normalized texts are shuffled and dealt 70/15/15.
    Necessary because the corpus has 2,265 segments but only 1,169 distinct
    normalized texts; splitting on segment_id would put identical strings on both
    sides of the wall.

`university` -- 6 of the 28 universities are held out, AND every text that appears
    at a held-out university is dropped from train/val entirely. This costs about a
    third of the training texts. It is necessary because 63% of segments share their
    text with another university (424 of 1,169 normalized texts are cross-university,
    and the 28 universities form a single connected component under text sharing), so
    holding out universities *without* dropping shared text does not hold anything
    out. This is the split that supports an inductive claim about an unseen school.

The human gold set enters neither. It is cell-level and is used only by
evaluate.py / evaluate_ml.py, at the end, once.

Outputs:
    data/ml/dataset.jsonl     one row per unique text: labels (1/0/-1) and cosines
    data/ml/splits.json       text ids per split, for both modes
    data/ml/dataset_card.md   counts, so the numbers in the write-up are checkable

Usage:
    python extraction/dataset.py
    python extraction/dataset.py --held-out 6 --seed 0
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import random
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import baseline as keyword          # noqa: E402  seed patterns + predict()
import embedding as emb             # noqa: E402  label_queries + encode_segments

MASK = -1
MASK_QUANTILE = 0.25
MASK_FLOOR = 0.40
DEFAULT_HELD_OUT = 6
VAL_FRACTION = 0.15
TEST_FRACTION = 0.15


def normalise(text: str) -> str:
    """Collapse to the form used for deduplication and for split assignment."""
    return re.sub(r"\W+", " ", text.lower()).strip()


def load_segments(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def dedupe(segments: list[dict]) -> list[dict]:
    """One row per distinct normalized text, carrying every university it appears at.

    A text that several universities share is a single training example. Counting it
    once per university would weight the compiler's copy-paste as if it were
    independent evidence, and would make any per-university split leak.
    """
    order: list[str] = []
    groups: dict[str, dict] = {}
    for segment in segments:
        key = normalise(segment["text"])
        if key not in groups:
            order.append(key)
            groups[key] = {"text_id": key, "text": segment["text"],
                           "universities": [], "segment_ids": []}
        row = groups[key]
        if segment["university"] not in row["universities"]:
            row["universities"].append(segment["university"])
        row["segment_ids"].append(segment["segment_id"])
    return [groups[k] for k in order]


def keyword_hits(label: dict, rows: list[dict]) -> np.ndarray:
    """Boolean mask of which texts the keyword baseline fires on for this label.

    Same rule as baseline.predict -- seed match, then the label's context term if it
    has one -- applied positionally so the result lines up with `rows`.
    """
    out = np.zeros(len(rows), dtype=bool)
    for index, row in enumerate(rows):
        text = row["text"]
        if not any(p.search(text) for p in label["_patterns"]):
            continue
        if label["_context"] and not any(c.search(text) for c in label["_context"]):
            continue
        out[index] = True
    return out


def build_labels(labels: list[dict], rows: list[dict], vectors: np.ndarray,
                 model) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (targets [n_texts, n_labels] in {1,0,-1}, cosines, per-label report)."""
    targets = np.zeros((len(rows), len(labels)), dtype=np.int8)
    cosines = np.zeros((len(rows), len(labels)), dtype=np.float32)
    report = {}
    for index, label in enumerate(labels):
        queries = model.encode(emb.label_queries(label), normalize_embeddings=True)
        # Max over queries, matching embedding.py: a segment that matches one specific
        # seed must not be diluted by the label's other, unrelated seeds.
        cos = (vectors @ queries.T).max(axis=1)
        fired = keyword_hits(label, rows)
        if fired.any():
            threshold = max(float(np.quantile(cos[fired], MASK_QUANTILE)), MASK_FLOOR)
        else:
            threshold = 1.1          # nothing to be ambiguous about
        ambiguous = (~fired) & (cos >= threshold)
        column = np.zeros(len(rows), dtype=np.int8)
        column[fired] = 1
        column[ambiguous] = MASK
        targets[:, index] = column
        cosines[:, index] = cos
        report[label["id"]] = {"positive": int(fired.sum()),
                               "masked": int(ambiguous.sum()),
                               "mask_threshold": round(threshold, 4)}
    return targets, cosines, report


def split_by_text(rows: list[dict], seed: int) -> dict[str, list[str]]:
    ids = [r["text_id"] for r in rows]
    random.Random(seed).shuffle(ids)
    n_test = int(round(TEST_FRACTION * len(ids)))
    n_val = int(round(VAL_FRACTION * len(ids)))
    return {"test": ids[:n_test],
            "val": ids[n_test:n_test + n_val],
            "train": ids[n_test + n_val:]}


def split_by_university(rows: list[dict], seed: int,
                        held_out: int) -> tuple[dict[str, list[str]], list[str]]:
    """Hold out whole universities, and drop every text they share with the rest.

    Without the second half this split would not hold anything out: 63% of segments
    carry text that also appears at another university.
    """
    universities = sorted({u for r in rows for u in r["universities"]})
    rng = random.Random(seed)
    holdout = set(rng.sample(universities, min(held_out, len(universities))))
    test, remaining = [], []
    for row in rows:
        if holdout.intersection(row["universities"]):
            test.append(row["text_id"])       # includes texts shared with train unis
        else:
            remaining.append(row["text_id"])
    rng.shuffle(remaining)
    n_val = int(round(VAL_FRACTION * len(remaining)))
    return ({"test": test, "val": remaining[:n_val], "train": remaining[n_val:]},
            sorted(holdout))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--cache", default=os.path.join(_ROOT, "data/clean/segment_embeddings.npz"))
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/ml"))
    parser.add_argument("--model", default=emb.DEFAULT_MODEL)
    parser.add_argument("--held-out", type=int, default=DEFAULT_HELD_OUT)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    for path in (args.taxonomy, args.evidence):
        if not os.path.exists(path):
            print(f"[error] missing input: {path}", file=sys.stderr)
            return 2

    from sentence_transformers import SentenceTransformer

    labels = keyword.load_taxonomy(args.taxonomy)
    segments = load_segments(args.evidence)
    rows = dedupe(segments)
    print(f"[info] {len(segments):,} segments -> {len(rows):,} unique texts")

    model = SentenceTransformer(args.model)
    all_vectors = emb.encode_segments(model, segments, args.cache)
    # Line up the cached per-segment vectors with the deduplicated rows: take the
    # first occurrence of each text. The cache is keyed to the full segment list, so
    # it stays shared with embedding.py rather than being recomputed here.
    position = {}
    for index, segment in enumerate(segments):
        position.setdefault(normalise(segment["text"]), index)
    vectors = np.stack([all_vectors[position[r["text_id"]]] for r in rows])

    targets, cosines, report = build_labels(labels, rows, vectors, model)

    splits = {"text": split_by_text(rows, args.seed)}
    university_split, holdout = split_by_university(rows, args.seed, args.held_out)
    splits["university"] = university_split

    os.makedirs(args.out_dir, exist_ok=True)
    data_path = os.path.join(args.out_dir, "dataset.jsonl")
    with open(data_path, "w", encoding="utf-8") as handle:
        for index, row in enumerate(rows):
            handle.write(json.dumps({
                "text_id": row["text_id"],
                "text": row["text"],
                "universities": row["universities"],
                "segment_ids": row["segment_ids"],
                "labels": {label["id"]: int(targets[index, j])
                           for j, label in enumerate(labels)},
                "cos": {label["id"]: round(float(cosines[index, j]), 4)
                        for j, label in enumerate(labels)},
            }, ensure_ascii=False) + "\n")

    splits_path = os.path.join(args.out_dir, "splits.json")
    with open(splits_path, "w", encoding="utf-8") as handle:
        json.dump({"seed": args.seed, "held_out_universities": holdout,
                   "splits": splits}, handle, indent=2)

    n_pos = int((targets == 1).sum())
    n_mask = int((targets == MASK).sum())
    n_cells = targets.size
    card = [
        "# ML dataset card",
        "",
        f"Built by `extraction/dataset.py` (seed {args.seed}).",
        "",
        f"- segments in corpus: **{len(segments):,}**",
        f"- unique normalized texts (training examples): **{len(rows):,}**",
        f"- labels: **{len(labels)}**",
        f"- (text, label) pairs: **{n_cells:,}**",
        f"- silver positives: **{n_pos:,}** ({100 * n_pos / n_cells:.1f}%)",
        f"- masked as ambiguous, excluded from loss: **{n_mask:,}** "
        f"({100 * n_mask / n_cells:.1f}%)",
        f"- negatives: **{n_cells - n_pos - n_mask:,}**",
        "",
        "Labels are distant supervision from the keyword baseline. They are not human",
        "annotation and are not gold. The 165 human-judged cells are cell-level and are",
        "held out entirely; they are never read here.",
        "",
        "## Splits",
        "",
        "| mode | train | val | test | leak-free by |",
        "|---|---|---|---|---|",
        f"| text | {len(splits['text']['train'])} | {len(splits['text']['val'])} | "
        f"{len(splits['text']['test'])} | distinct normalized text |",
        f"| university | {len(splits['university']['train'])} | "
        f"{len(splits['university']['val'])} | {len(splits['university']['test'])} | "
        f"whole university + every text it shares |",
        "",
        f"Held-out universities: {', '.join(holdout)}",
        "",
        "## Per-label silver counts",
        "",
        "| label | positives | masked | mask threshold (cos) |",
        "|---|---:|---:|---:|",
    ]
    for label in labels:
        stats = report[label["id"]]
        card.append(f"| {label['id']} | {stats['positive']} | {stats['masked']} | "
                    f"{stats['mask_threshold']} |")
    card_path = os.path.join(args.out_dir, "dataset_card.md")
    with open(card_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(card) + "\n")

    print(f"[ok]   {n_pos:,} silver positives, {n_mask:,} masked, "
          f"{n_cells - n_pos - n_mask:,} negatives")
    print(f"[info] text split      train {len(splits['text']['train'])} / "
          f"val {len(splits['text']['val'])} / test {len(splits['text']['test'])}")
    print(f"[info] university split train {len(splits['university']['train'])} / "
          f"val {len(splits['university']['val'])} / test {len(splits['university']['test'])}"
          f"  (held out: {', '.join(holdout)})")
    for path in (data_path, splits_path, card_path):
        print(f"[info] wrote {os.path.relpath(path, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
