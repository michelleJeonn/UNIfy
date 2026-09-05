"""
Embedding extractor: semantic matching over the same evidence segments.

Tests one specific hypothesis, taken from the keyword baseline's own error analysis:
its false negatives are dominated by exact-phrase seeds failing on intervening words
and inflection ("private *exam* spaces" vs seed "private room", "accommodation
*planning*" vs "accommodation plan"). Sentence embeddings should recover those.

**Threshold selection is the trap here.** Tuning a cut-off against the gold set would
make the comparison meaningless -- the gold set is the test set, and the keyword
baseline never got to tune anything against it. So the threshold is fixed by a rule
that reads no gold labels at all: pick the single global cosine cut-off at which this
extractor predicts the *same total number* of positive cells as the keyword baseline.
Both systems then spend an identical budget of positives, and the score answers the
only interesting question -- given the same number of calls, whose are better placed?

Individual labels are free to fire more or less often than the baseline, so recall can
still improve where the baseline under-fired. `--sweep` reports other thresholds for
transparency; those numbers are diagnostics, not headline results.

Outputs (same shape as baseline.py, so evaluate.py scores it unchanged):
    data/clean/accommodations_embedding.csv
    data/clean/accommodations_embedding.jsonl

Usage:
    python extraction/embedding.py [--model ...] [--sweep]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def label_queries(label: dict) -> list[str]:
    """Short, focused query strings for one label.

    Deliberately excludes the definition prose: definitions carry negation ("does NOT
    include wayfinding help"), and sentence embeddings represent negated text almost
    identically to its affirmation, so feeding them in pulls the query toward exactly
    the cases the definition means to exclude.
    """
    queries = [label["name"]]
    queries.extend(label["seeds"])
    return queries


def encode_segments(model, segments: list[dict], cache_path: str) -> np.ndarray:
    """Encode every segment once and cache; the corpus changes far less often than
    the taxonomy does."""
    fingerprint = str(len(segments)) + "|" + (segments[0]["segment_id"] if segments else "")
    if os.path.exists(cache_path):
        stored = np.load(cache_path, allow_pickle=True)
        if str(stored["fingerprint"]) == fingerprint:
            print(f"[info] reusing cached segment embeddings ({cache_path})")
            return stored["vectors"]
    print(f"[info] encoding {len(segments):,} segments ...")
    vectors = model.encode([s["text"] for s in segments], normalize_embeddings=True,
                           batch_size=64, show_progress_bar=False)
    np.savez(cache_path, vectors=vectors, fingerprint=fingerprint)
    return vectors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--baseline", default=os.path.join(_ROOT, "data/clean/accommodations_baseline.jsonl"),
                        help="used only to match the total positive budget; no gold labels are read")
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/clean"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sweep", action="store_true", help="print positives at other thresholds")
    args = parser.parse_args()

    for path in (args.taxonomy, args.evidence, args.baseline):
        if not os.path.exists(path):
            print(f"[error] missing input: {path}", file=sys.stderr)
            return 2

    from sentence_transformers import SentenceTransformer

    with open(args.taxonomy, encoding="utf-8") as handle:
        labels = json.load(handle)["labels"]
    segments = [json.loads(line) for line in open(args.evidence, encoding="utf-8")]

    by_university: dict[str, list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        by_university[segment["university"]].append(index)
    universities = sorted(by_university)

    model = SentenceTransformer(args.model)
    segment_vectors = encode_segments(
        model, segments, os.path.join(args.out_dir, "segment_embeddings.npz"))

    # Best-matching segment per (university, label), plus which segment it was.
    scores = np.zeros((len(universities), len(labels)), dtype=np.float32)
    best_segment = np.zeros((len(universities), len(labels)), dtype=np.int64)
    for label_index, label in enumerate(labels):
        query_vectors = model.encode(label_queries(label), normalize_embeddings=True)
        # Max over queries: a segment matching one specific seed should not be diluted
        # by the label's other, unrelated seeds.
        similarity = segment_vectors @ query_vectors.T
        per_segment = similarity.max(axis=1)
        for uni_index, university in enumerate(universities):
            indices = by_university[university]
            local = per_segment[indices]
            winner = int(np.argmax(local))
            scores[uni_index, label_index] = float(local[winner])
            best_segment[uni_index, label_index] = indices[winner]

    # Threshold: match the keyword baseline's total positive count. Reads predictions,
    # never gold.
    baseline_positives = sum(
        json.loads(line)["value"] for line in open(args.baseline, encoding="utf-8"))
    flat = np.sort(scores.flatten())[::-1]
    budget = min(baseline_positives, len(flat) - 1)
    threshold = float(flat[budget]) if budget < len(flat) else 0.0
    print(f"[info] keyword baseline predicts {baseline_positives} positive cells; "
          f"matching that budget puts the cosine threshold at {threshold:.4f}")

    matrix = (scores > threshold).astype(int)

    os.makedirs(args.out_dir, exist_ok=True)
    matrix_path = os.path.join(args.out_dir, "accommodations_embedding.csv")
    with open(matrix_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["university"] + [l["id"] for l in labels])
        for uni_index, university in enumerate(universities):
            writer.writerow([university] + list(matrix[uni_index]))

    detail_path = os.path.join(args.out_dir, "accommodations_embedding.jsonl")
    with open(detail_path, "w", encoding="utf-8") as handle:
        for uni_index, university in enumerate(universities):
            for label_index, label in enumerate(labels):
                segment = segments[best_segment[uni_index, label_index]]
                handle.write(json.dumps({
                    "university": university,
                    "label": label["id"],
                    "value": int(matrix[uni_index, label_index]),
                    "source": "embedding",
                    "score": round(float(scores[uni_index, label_index]), 4),
                    "citations": [segment["segment_id"]],
                    "evidence": [segment["text"][:160]],
                }, ensure_ascii=False) + "\n")

    print(f"[ok]   {len(universities)} universities x {len(labels)} labels "
          f"({int(matrix.sum())} positive cells)")
    print(f"[info] wrote {os.path.relpath(matrix_path, _ROOT)}")
    print(f"[info] wrote {os.path.relpath(detail_path, _ROOT)}")

    if args.sweep:
        print("\nthreshold sweep (diagnostic only -- not a headline result):")
        for candidate in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
            print(f"   cos > {candidate:.2f}: {int((scores > candidate).sum()):4d} positive cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
