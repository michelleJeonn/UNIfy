"""
Score an extractor against the hand-labelled gold set.

The gold set is stratified by the extractor's own prediction, so the arithmetic is
not the usual counting of a confusion matrix -- the strata are sampled at different
rates and must be reweighted back to the 28-school population before recall means
anything:

    precision = P(gold=1 | predicted=1)          measured directly on the positive
                                                 stratum; sampling is uniform within
                                                 it, so the raw fraction is unbiased.

    TP_hat    = N_pos * (gold=1 rate in positive stratum)
    FN_hat    = N_neg * (gold=1 rate in negative stratum)
    recall    = TP_hat / (TP_hat + FN_hat)

Reporting the naive pooled recall instead would understate false negatives by
whatever factor the negative stratum was under-sampled -- typically 5-8x here.

Intervals: precision gets a Wilson score interval (correct for small n and for rates
at 0 or 1, where the normal approximation is degenerate).  Recall and F1 are ratios
of two random quantities, so they get a stratified bootstrap instead.  With ~6 judged
cells per label these intervals are wide, and that is the honest result: it says the
gold set is too small to rank extractors on a single label, and that conclusions
should be drawn from the macro average across labels.

Usage:
    python extraction/evaluate.py [--gold data/gold/gold.csv]
                                  [--predictions data/clean/accommodations_baseline.jsonl]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import sys
import unicodedata
from collections import defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOTSTRAP_SAMPLES = 2000
MIN_JUDGED_PER_STRATUM = 2


# Gold sets come back from spreadsheets, which silently rewrite typographic
# punctuation -- "Universite de l'Ontario francais" loses its U+2019 apostrophe on a
# CSV round-trip and then fails to join. Normalising the key is safer than asking an
# annotator to preserve invisible characters.
_QUOTES = {0x2018: "'", 0x2019: "'", 0x201B: "'", 0x2032: "'",
           0x201C: '"', 0x201D: '"', 0x2033: '"'}


def join_key(name: str) -> str:
    text = unicodedata.normalize("NFKC", str(name)).translate(_QUOTES)
    return re.sub(r"\s+", " ", text).strip().casefold()


GOLD_COLUMNS = ("gold", "gold (1/0)", "gold(1/0)", "gold_1_0", "label_gold")


def gold_column(fieldnames: list[str]) -> str | None:
    """Find the judgment column, tolerating the header a spreadsheet produced."""
    lookup = {f.strip().lower(): f for f in fieldnames or []}
    for candidate in GOLD_COLUMNS:
        if candidate in lookup:
            return lookup[candidate]
    for lowered, original in lookup.items():
        if lowered.startswith("gold"):
            return original
    return None


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return (float("nan"), float("nan"))
    phat = successes / total
    denominator = 1 + z * z / total
    centre = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def rates(pos_gold: list[int], neg_gold: list[int],
          n_pos: int, n_neg: int) -> tuple[float, float, float]:
    """Reweighted precision, recall, F1 for one label."""
    if not pos_gold:
        return (float("nan"),) * 3
    precision = sum(pos_gold) / len(pos_gold)
    tp = n_pos * precision
    fn = n_neg * (sum(neg_gold) / len(neg_gold)) if neg_gold else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    if precision + recall == 0 or math.isnan(recall):
        return precision, recall, float("nan")
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def bootstrap(pos_gold: list[int], neg_gold: list[int], n_pos: int, n_neg: int,
              rng: random.Random) -> dict[str, tuple[float, float]]:
    """Percentile intervals, resampling within each stratum."""
    recalls, f1s = [], []
    for _ in range(BOOTSTRAP_SAMPLES):
        pos = [rng.choice(pos_gold) for _ in pos_gold] if pos_gold else []
        neg = [rng.choice(neg_gold) for _ in neg_gold] if neg_gold else []
        _, recall, f1 = rates(pos, neg, n_pos, n_neg)
        if not math.isnan(recall):
            recalls.append(recall)
        if not math.isnan(f1):
            f1s.append(f1)

    def interval(values: list[float]) -> tuple[float, float]:
        if len(values) < 2:
            return (float("nan"), float("nan"))
        values = sorted(values)
        return (values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1])

    return {"recall": interval(recalls), "f1": interval(f1s)}


def fmt(value: float) -> str:
    return "  n/a" if value is None or math.isnan(value) else f"{value:5.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", action="append", default=None,
                        help="gold csv; repeatable. Later files override earlier ones for "
                             "the same cell, which is how a re-judged batch supersedes the "
                             "original after a definition change.")
    parser.add_argument("--predictions",
                        default=os.path.join(_ROOT, "data/clean/accommodations_baseline.jsonl"),
                        help="jsonl with university/label/value -- swap this to score another extractor")
    parser.add_argument("--name", default="keyword baseline")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    gold_paths = args.gold or [os.path.join(_ROOT, "data/gold/gold.csv")]


    for path in gold_paths:
        if not os.path.exists(path):
            print(f"[error] no gold file at {path}\n"
                  f"        Fill the `gold` column in data/gold/gold_template.csv with 1/0 "
                  f"and save it as data/gold/gold.csv.", file=sys.stderr)
            return 2
    if not os.path.exists(args.predictions):
        print(f"[error] missing input: {args.predictions}", file=sys.stderr)
        return 2

    predictions = {}
    strata: dict[str, dict[str, int]] = defaultdict(lambda: {"n_positive": 0, "n_negative": 0})
    for line in open(args.predictions, encoding="utf-8"):
        record = json.loads(line)
        predictions[(join_key(record["university"]), record["label"])] = record["value"]
        side = "n_positive" if record["value"] == 1 else "n_negative"
        strata[record["label"]][side] += 1

    # Merge the gold files in order; a later file supersedes an earlier verdict for
    # the same cell. Keeping one judgment per cell matters: a re-judged label would
    # otherwise be counted twice, once under each definition.
    judgments: dict[tuple[str, str], int] = {}
    superseded = 0
    unjudged = 0
    unmatched = []
    for path in gold_paths:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            column = gold_column(reader.fieldnames)
            if column is None:
                print(f"[error] no gold column in {path}; expected one of {GOLD_COLUMNS}",
                      file=sys.stderr)
                return 2
            for row in reader:
                value = (row.get(column) or "").strip()
                if value not in {"0", "1"}:
                    unjudged += 1
                    continue
                key = (join_key(row["university"]), row["label"])
                if key not in predictions:
                    unmatched.append((row["university"], row["label"]))
                    continue
                if key in judgments:
                    superseded += 1
                judgments[key] = int(value)

    by_label: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"pos": [], "neg": []})
    for (university, label_id), value in judgments.items():
        # Stratum comes from the extractor being scored, not from the template,
        # so the same gold file can score a different extractor correctly.
        stratum = "pos" if predictions[(university, label_id)] == 1 else "neg"
        by_label[label_id][stratum].append(value)

    if unmatched:
        print(f"[error] {len(unmatched)} gold row(s) name a cell absent from the predictions; "
              f"the gold set and the extractor disagree about the universe:", file=sys.stderr)
        for university, label in unmatched[:5]:
            print(f"        {university} / {label}", file=sys.stderr)
        return 1
    if not by_label:
        print(f"[error] no judged rows found (column `{column}` is empty)", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    print(f"\nExtractor: {args.name}")
    print(f"Gold files: {', '.join(os.path.relpath(p, _ROOT) for p in gold_paths)}"
          + (f"  ({superseded} cell(s) superseded by a later file)" if superseded else ""))
    print(f"Gold cells judged: {sum(len(v['pos']) + len(v['neg']) for v in by_label.values())}"
          f"{f'  ({unjudged} left blank)' if unjudged else ''}")
    print(f"\n{'label':34s} {'prec':>5s} {'recall':>6s} {'F1':>5s}   {'n+':>3s} {'n-':>3s}  "
          f"{'precision 95% CI':>18s}  {'recall 95% CI':>16s}")
    print("-" * 108)

    macro = {"precision": [], "recall": [], "f1": []}
    thin = []
    for label_id in sorted(by_label):
        stats = strata[label_id]
        n_pos, n_neg = stats["n_positive"], stats["n_negative"]
        pos_gold, neg_gold = by_label[label_id]["pos"], by_label[label_id]["neg"]
        precision, recall, f1 = rates(pos_gold, neg_gold, n_pos, n_neg)
        ci = bootstrap(pos_gold, neg_gold, n_pos, n_neg, rng)
        p_low, p_high = wilson(sum(pos_gold), len(pos_gold))
        r_low, r_high = ci["recall"]

        if len(pos_gold) < MIN_JUDGED_PER_STRATUM or len(neg_gold) < MIN_JUDGED_PER_STRATUM:
            thin.append(label_id)
        for key, value in (("precision", precision), ("recall", recall), ("f1", f1)):
            if not math.isnan(value):
                macro[key].append(value)

        print(f"{label_id:34s} {fmt(precision)} {fmt(recall):>6s} {fmt(f1)}   "
              f"{len(pos_gold):3d} {len(neg_gold):3d}  "
              f"[{fmt(p_low)},{fmt(p_high)}]  [{fmt(r_low)},{fmt(r_high)}]")

    print("-" * 108)

    def mean(values: list[float]) -> float:
        # A metric can be undefined for every label at once -- an extractor that
        # predicts nothing correctly has no defined recall anywhere -- so this must
        # not assume the list is non-empty.
        return sum(values) / len(values) if values else float("nan")

    print(f"{'MACRO AVERAGE':34s} {fmt(mean(macro['precision']))} "
          f"{fmt(mean(macro['recall'])):>6s} {fmt(mean(macro['f1']))}   "
          f"over {len(macro['f1'])} label(s) with a defined F1")
    for key in ("precision", "recall", "f1"):
        if not macro[key]:
            print(f"[warn] {key} is undefined for every label "
                  f"(no true positives anywhere in the gold sample)")

    if thin:
        print(f"\n[warn] {len(thin)} label(s) have fewer than {MIN_JUDGED_PER_STRATUM} judged "
              f"cells in a stratum; their intervals are not meaningful:")
        print("       " + ", ".join(thin))
    print("\nNote: per-label intervals are wide by construction at this sample size. "
          "Compare extractors on the macro average, not on individual labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
