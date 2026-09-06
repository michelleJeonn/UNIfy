"""
Score every extractor against the same human gold set, side by side.

evaluate.py scores one system and is the authority on the arithmetic -- stratified
sampling, reweighted recall, Wilson and bootstrap intervals. This module imports that
arithmetic rather than restating it, and adds what a model comparison needs:

  * all four systems in one table, on identical cells
  * micro (cell-pooled) as well as macro (label-averaged) averages
  * per-label breakdown for whichever system you point `--detail` at
  * error analysis: the specific cells where a system disagrees with a human, with the
    evidence text it cited, which is the only view that tells you *why* a number moved
  * a contamination guard (below)

**Contamination guard.** active_learning.py can promote newly annotated cells into
training. If one of those files were later handed to this script as gold, the model
would be scored on its own training labels and the number would be meaningless. So
data/ml/train_manifest.json records every gold file ever consumed for training, and
this script refuses to run if a gold file it was asked to score appears there.
`--allow-contaminated` exists only to make the refusal explicit in a log; it does not
make the number valid.

Two caveats stay attached to every comparison here:

  1. The gold set is stratified by the *keyword baseline's* predictions. Every other
     system is therefore scored on a sample chosen around a competitor's decision
     boundary, which is not neutral ground. Differences are provisional until a
     batch stratified by the new system's own predictions is judged.
  2. The learned systems are trained on distant supervision from that same keyword
     baseline. Matching it is the expected result; beating it requires that the
     pretrained encoder generalise past its seeds, and losing to it means it did not.

Usage:
    python extraction/evaluate_ml.py
    python extraction/evaluate_ml.py --detail hybrid --errors 15
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from evaluate import (bootstrap, gold_column, join_key, rates,  # noqa: E402
                      wilson, MIN_JUDGED_PER_STRATUM)

DEFAULT_GOLD = ["data/gold/gold.csv", "data/gold/gold_supplement.csv",
                "data/gold/gold_supplement2.csv"]
# System names are the file suffixes on purpose: `accommodations_<name>.jsonl` is what
# claude_recommender.py selects on via UNIFY_EXTRACTOR, and what --json-out is keyed by,
# so the name in this table, the name of the file and the name the API reports are all
# the same string.
DEFAULT_SYSTEMS = [
    ("baseline", "data/clean/accommodations_baseline.jsonl"),
    ("embedding", "data/clean/accommodations_embedding.jsonl"),
    ("multilabel", "data/clean/accommodations_multilabel.jsonl"),
    ("classifier", "data/clean/accommodations_classifier.jsonl"),
    ("hybrid", "data/clean/accommodations_hybrid.jsonl"),
]
MANIFEST = "data/ml/train_manifest.json"


def load_predictions(path: str) -> tuple[dict, dict, dict]:
    """(university, label) -> value, plus stratum sizes and the cited evidence."""
    predictions, evidence = {}, {}
    strata: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n_positive": 0, "n_negative": 0})
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            key = (join_key(record["university"]), record["label"])
            predictions[key] = record["value"]
            evidence[key] = (record.get("evidence") or [""])[0]
            strata[record["label"]]["n_positive" if record["value"] == 1
                                    else "n_negative"] += 1
    return predictions, strata, evidence


def load_gold(paths: list[str]) -> dict[tuple[str, str], int]:
    """Merge gold files in order; a later file supersedes an earlier verdict."""
    judgments: dict[tuple[str, str], int] = {}
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            column = gold_column(reader.fieldnames)
            if column is None:
                raise SystemExit(f"[error] no gold column in {path}")
            for row in reader:
                value = (row.get(column) or "").strip()
                if value in {"0", "1"}:
                    judgments[(join_key(row["university"]), row["label"])] = int(value)
    return judgments


def check_contamination(gold_paths: list[str], allow: bool) -> None:
    path = os.path.join(_ROOT, MANIFEST)
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        consumed = {os.path.abspath(os.path.join(_ROOT, p))
                    for p in json.load(handle).get("training_gold_files", [])}
    overlap = sorted({p for p in gold_paths if os.path.abspath(p) in consumed})
    if not overlap:
        return
    message = ("[error] these gold files were consumed for training and cannot also be "
               "used to score:\n        " + "\n        ".join(overlap))
    if not allow:
        raise SystemExit(message + "\n        (see data/ml/train_manifest.json)")
    print(message.replace("[error]", "[warn]") + "\n        --allow-contaminated set; "
          "the numbers below are NOT a valid held-out estimate.", file=sys.stderr)


def score(predictions: dict, strata: dict, judgments: dict,
          rng: random.Random, restrict: set[str] | None = None) -> dict:
    """Stratified metrics for one system over the judged cells."""
    by_label: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"pos": [], "neg": []})
    missing = 0
    for (university, label_id), gold in judgments.items():
        if restrict is not None and university not in restrict:
            continue
        key = (university, label_id)
        if key not in predictions:
            missing += 1
            continue
        by_label[label_id]["pos" if predictions[key] == 1 else "neg"].append(gold)

    per_label, macro = {}, {"precision": [], "recall": [], "f1": []}
    micro = {"tp": 0.0, "fp": 0.0, "fn": 0.0}
    for label_id, stratum in by_label.items():
        n_pos = strata[label_id]["n_positive"]
        n_neg = strata[label_id]["n_negative"]
        precision, recall, f1 = rates(stratum["pos"], stratum["neg"], n_pos, n_neg)
        interval = bootstrap(stratum["pos"], stratum["neg"], n_pos, n_neg, rng)
        per_label[label_id] = {
            "precision": precision, "recall": recall, "f1": f1,
            "n_pos": len(stratum["pos"]), "n_neg": len(stratum["neg"]),
            "precision_ci": wilson(sum(stratum["pos"]), len(stratum["pos"])),
            "recall_ci": interval["recall"],
            "thin": (len(stratum["pos"]) < MIN_JUDGED_PER_STRATUM
                     or len(stratum["neg"]) < MIN_JUDGED_PER_STRATUM),
        }
        for key, value in (("precision", precision), ("recall", recall), ("f1", f1)):
            if not math.isnan(value):
                macro[key].append(value)
        # Micro pools the reweighted counts across labels, so a label with many
        # predicted positives carries proportionally more of the average. Macro treats
        # every label alike. They answer different questions; both are reported because
        # this taxonomy is very unbalanced (149 silver hits for intake_meeting, 2 for
        # accessible parking) and the two can move in opposite directions.
        if not math.isnan(precision):
            micro["tp"] += n_pos * precision
            micro["fp"] += n_pos * (1 - precision)
        if stratum["neg"]:
            micro["fn"] += n_neg * (sum(stratum["neg"]) / len(stratum["neg"]))

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else float("nan")

    micro_p = micro["tp"] / (micro["tp"] + micro["fp"]) if micro["tp"] + micro["fp"] else float("nan")
    micro_r = micro["tp"] / (micro["tp"] + micro["fn"]) if micro["tp"] + micro["fn"] else float("nan")
    micro_f = (2 * micro_p * micro_r / (micro_p + micro_r)
               if micro_p + micro_r and not math.isnan(micro_p + micro_r) else float("nan"))
    return {"per_label": per_label, "missing": missing,
            "labels": len(by_label),
            "judged": sum(len(v["pos"]) + len(v["neg"]) for v in by_label.values()),
            "macro": {k: mean(v) for k, v in macro.items()},
            "micro": {"precision": micro_p, "recall": micro_r, "f1": micro_f}}


def fmt(value: float) -> str:
    return "  n/a" if value is None or math.isnan(value) else f"{value:5.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", action="append", default=None)
    parser.add_argument("--system", action="append", default=None,
                        metavar="NAME=PATH", help="repeatable; overrides the defaults")
    parser.add_argument("--detail", default=None, help="print the per-label table for this system")
    parser.add_argument("--errors", type=int, default=0,
                        help="print N disagreements with the human judgment for --detail")
    parser.add_argument("--held-out-only", action="store_true",
                        help="restrict to the universities held out of training "
                             "(inductive read; see data/ml/splits.json)")
    parser.add_argument("--splits", default=os.path.join(_ROOT, "data/ml/splits.json"))
    parser.add_argument("--allow-contaminated", action="store_true")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    gold_paths = [p if os.path.isabs(p) else os.path.join(_ROOT, p)
                  for p in (args.gold or DEFAULT_GOLD)]
    for path in gold_paths:
        if not os.path.exists(path):
            print(f"[error] no gold file at {path}", file=sys.stderr)
            return 2
    check_contamination(gold_paths, args.allow_contaminated)

    if args.system:
        systems = [tuple(s.split("=", 1)) for s in args.system]
    else:
        systems = DEFAULT_SYSTEMS
    systems = [(name, path if os.path.isabs(path) else os.path.join(_ROOT, path))
               for name, path in systems]

    judgments = load_gold(gold_paths)
    restrict = None
    if args.held_out_only:
        with open(args.splits, encoding="utf-8") as handle:
            held = json.load(handle)["held_out_universities"]
        restrict = {join_key(u) for u in held}
        print(f"[info] restricted to {len(held)} held-out universities: {', '.join(held)}")

    print(f"\nGold: {', '.join(os.path.relpath(p, _ROOT) for p in gold_paths)}  "
          f"({len(judgments)} judged cells)")
    print(f"\n{'system':14s} {'cells':>5s}  {'macro P':>7s} {'macro R':>7s} {'macro F1':>8s}   "
          f"{'micro P':>7s} {'micro R':>7s} {'micro F1':>8s}  {'labels':>6s}")
    print("-" * 92)

    results = {}
    for name, path in systems:
        if not os.path.exists(path):
            print(f"{name:14s} {'--':>5s}  not built yet ({os.path.relpath(path, _ROOT)})")
            continue
        predictions, strata, evidence = load_predictions(path)
        rng = random.Random(args.seed)
        result = score(predictions, strata, judgments, rng, restrict)
        result["_evidence"] = evidence
        result["_predictions"] = predictions
        results[name] = result
        print(f"{name:14s} {result['judged']:5d}  "
              f"{fmt(result['macro']['precision']):>7s} {fmt(result['macro']['recall']):>7s} "
              f"{fmt(result['macro']['f1']):>8s}   "
              f"{fmt(result['micro']['precision']):>7s} {fmt(result['micro']['recall']):>7s} "
              f"{fmt(result['micro']['f1']):>8s}  {result['labels']:6d}")
    print("-" * 92)
    print("Provisional: the gold set is stratified by the keyword baseline's predictions,\n"
          "and the learned systems are trained on distant supervision from that same\n"
          "baseline. Neither is neutral ground for the comparison.")

    if args.detail and args.detail in results:
        result = results[args.detail]
        print(f"\nPer-label -- {args.detail}")
        print(f"{'label':34s} {'prec':>5s} {'recall':>6s} {'F1':>5s}   {'n+':>3s} {'n-':>3s}  "
              f"{'precision 95% CI':>18s}  {'recall 95% CI':>16s}")
        print("-" * 100)
        for label_id in sorted(result["per_label"]):
            stats = result["per_label"][label_id]
            print(f"{label_id:34s} {fmt(stats['precision'])} {fmt(stats['recall']):>6s} "
                  f"{fmt(stats['f1'])}   {stats['n_pos']:3d} {stats['n_neg']:3d}  "
                  f"[{fmt(stats['precision_ci'][0])},{fmt(stats['precision_ci'][1])}]  "
                  f"[{fmt(stats['recall_ci'][0])},{fmt(stats['recall_ci'][1])}]"
                  f"{'  thin' if stats['thin'] else ''}")

        if args.errors:
            predictions = result["_predictions"]
            evidence = result["_evidence"]
            wrong = [(k, gold, predictions[k]) for k, gold in judgments.items()
                     if k in predictions and predictions[k] != gold
                     and (restrict is None or k[0] in restrict)]
            print(f"\nDisagreements with the human judgment -- {args.detail} "
                  f"({len(wrong)} of {result['judged']} judged cells)")
            for (university, label_id), gold, predicted in wrong[:args.errors]:
                kind = "false positive" if predicted == 1 else "false negative"
                cited = evidence.get((university, label_id), "")
                print(f"  [{kind}] {label_id} @ {university}")
                print(f"      cited: {cited[:120] or '(nothing cited)'}")

    if args.json_out:
        payload = {name: {k: v for k, v in result.items() if not k.startswith("_")}
                   for name, result in results.items()}
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=lambda o: None
                      if isinstance(o, float) and math.isnan(o) else o)
        print(f"\n[info] wrote {os.path.relpath(args.json_out, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
