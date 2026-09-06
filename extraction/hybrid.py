"""
Retrieval + rerank: MiniLM embeddings propose, the trained classifier disposes.

The two learned systems fail in opposite directions, which is the whole reason to
combine them. The embedding extractor measured recall 0.92 / precision 0.84 -- it
finds paraphrases the keyword seeds miss, then collapses near-neighbours together
("One-on-one counselling services" scores 0.65 against *group* counselling). The
cross-encoder can tell those apart, because it reads the label and the segment
jointly instead of comparing two independently-built vectors, but running it over
every (segment, label) pair is 37,408 forward passes and most of them are obviously
irrelevant.

So: embeddings retrieve a high-recall candidate set, the classifier reranks it, and
anything not retrieved scores zero.

    retrieval threshold per label = the cosine below which only (1 - recall_target)
    of that label's *silver* positives fall.

That is a percentile of the keyword extractor's own hits. It reads predictions, never
gold. The target defaults to 0.98, deliberately generous: a candidate the retriever
drops can never be recovered, so recall lost here is lost for good, while precision
lost here is the reranker's job to fix.

Outputs the same two files as every other extractor, so evaluate.py scores it unchanged:
    data/clean/accommodations_hybrid.csv
    data/clean/accommodations_hybrid.jsonl

Usage:
    python extraction/hybrid.py --model-dir models/cross_encoder_text
    python extraction/hybrid.py --model-dir ... --recall-target 0.95
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import baseline as keyword          # noqa: E402
import embedding as emb             # noqa: E402
from classifier import (Classifier, budget_threshold, cells_from_segments,  # noqa: E402
                        load_corpus, write_outputs)


def retrieval_mask(segments: list[dict], labels: list[dict], vectors: np.ndarray,
                   model, recall_target: float) -> tuple[np.ndarray, list[dict]]:
    """Boolean [n_segments, n_labels] candidate mask, plus a per-label report."""
    mask = np.zeros((len(segments), len(labels)), dtype=bool)
    report = []
    for column, label in enumerate(labels):
        queries = model.encode(emb.label_queries(label), normalize_embeddings=True)
        cos = (vectors @ queries.T).max(axis=1)
        silver = np.array([
            bool(any(p.search(s["text"]) for p in label["_patterns"])
                 and (not label["_context"]
                      or any(c.search(s["text"]) for c in label["_context"])))
            for s in segments])
        if silver.any():
            threshold = float(np.quantile(cos[silver], 1.0 - recall_target))
        else:
            # No silver positives to calibrate on; fall back to a fixed cut-off rather
            # than retrieving the whole corpus for a label nothing is known about.
            threshold = 0.35
        column_mask = cos >= threshold
        mask[:, column] = column_mask
        kept = int((silver & column_mask).sum())
        report.append({"label": label["id"], "threshold": round(threshold, 4),
                       "candidates": int(column_mask.sum()),
                       "silver_positives": int(silver.sum()),
                       "silver_retained": kept,
                       "retrieval_recall": round(kept / max(int(silver.sum()), 1), 3)})
    return mask, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--cache", default=os.path.join(_ROOT, "data/clean/segment_embeddings.npz"))
    parser.add_argument("--baseline", default=os.path.join(_ROOT, "data/clean/accommodations_baseline.jsonl"))
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/clean"))
    parser.add_argument("--name", default="hybrid")
    parser.add_argument("--embedding-model", default=emb.DEFAULT_MODEL)
    parser.add_argument("--recall-target", type=float, default=0.98)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    from sentence_transformers import SentenceTransformer

    labels = keyword.load_taxonomy(args.taxonomy)      # compiles seed patterns
    segments = load_corpus(args.evidence)
    universities = sorted({s["university"] for s in segments})

    retriever = SentenceTransformer(args.embedding_model)
    vectors = emb.encode_segments(retriever, segments, args.cache)
    mask, report = retrieval_mask(segments, labels, vectors, retriever, args.recall_target)

    pairs = int(mask.sum())
    total = mask.size
    retained = sum(r["silver_retained"] for r in report)
    silver = sum(r["silver_positives"] for r in report)
    print(f"[info] retrieval keeps {pairs:,} of {total:,} pairs ({100 * pairs / total:.1f}%), "
          f"retaining {retained}/{silver} silver positives "
          f"({100 * retained / max(silver, 1):.1f}% recall)")

    classifier = Classifier(args.model_dir)
    print(f"[info] reranking with the {classifier.head} head on {classifier.device}")
    probabilities = classifier.score([s["text"] for s in segments], labels,
                                     batch_size=args.batch_size, candidates=mask)
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
        segments, f"hybrid:{classifier.head}")
    report_path = os.path.join(args.out_dir, f"accommodations_{args.name}_retrieval.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"recall_target": args.recall_target,
                   "pairs_scored": pairs, "pairs_total": total,
                   "silver_retrieval_recall": round(retained / max(silver, 1), 4),
                   "per_label": report}, handle, indent=2)

    print(f"[ok]   {len(universities)} universities x {len(labels)} labels "
          f"({int(matrix.sum())} positive cells)")
    for path in (matrix_path, detail_path, report_path):
        print(f"[info] wrote {os.path.relpath(path, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
