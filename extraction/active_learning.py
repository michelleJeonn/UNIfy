"""
Choose the next cells to annotate, and fold reviewed ones back into training.

165 judged cells is not enough to separate four extractors -- the per-label intervals
in evaluate.py are wide enough to swallow most of the differences. More annotation is
the binding constraint, and annotation is the expensive resource, so it should be
spent where it is most informative rather than uniformly.

Two selection signals, both computed without reading any gold:

  disagreement   the systems (keyword / embedding / classifier / hybrid) split on the
                 cell. A cell they all agree on is unlikely to change any conclusion;
                 a 2-2 split is a cell where the annotation decides something.
  uncertainty    the classifier's probability sits near its decision threshold. These
                 are the cells the model itself cannot call.

Disagreement ranks first because it also *diagnoses*: a cell where keyword says yes
and the classifier says no is either a seed firing on the wrong context or the model
failing to generalise, and the annotation tells you which.

Promotion back into training (`--promote`) is deliberately asymmetric, because a
cell-level judgment carries different information depending on its sign:

  gold = 0  ->  every segment at that university is a verified negative for that
                label. That is clean, exact, segment-level supervision, and it is the
                only human signal in this project that is.
  gold = 1  ->  *some* segment at that university evidences the label, but the
                annotation does not say which. That is a bag-level (multiple-instance)
                constraint, not a segment label. It is recorded as `bag_positive` and
                used only to lift the ambiguity mask on that university's segments --
                never written as a positive on a segment nobody judged.

Model predictions are never promoted. A pseudo-label is a prediction, and treating one
as gold is how a benchmark quietly starts measuring itself.

Every promoted file is recorded in data/ml/train_manifest.json, and evaluate_ml.py
refuses to score against a gold file listed there.

Usage:
    # export the next 40 cells to judge, skipping everything already judged
    python extraction/active_learning.py --out data/gold/active_batch1_template.csv \
        --exclude data/gold/gold.csv --exclude data/gold/gold_supplement.csv --n 40

    # after annotation, fold the reviewed batch into training
    python extraction/active_learning.py --promote data/gold/active_batch1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from evaluate import gold_column, join_key          # noqa: E402
from make_gold import build_idf, relevant_segments, safe_name  # noqa: E402

SYSTEMS = [("keyword", "data/clean/accommodations_baseline.jsonl"),
           ("embedding", "data/clean/accommodations_embedding.jsonl"),
           ("classifier", "data/clean/accommodations_classifier.jsonl"),
           ("hybrid", "data/clean/accommodations_hybrid.jsonl")]
MANIFEST = "data/ml/train_manifest.json"
TEMPLATE_COLUMNS = ["university", "label", "label_name", "definition", "related_text",
                    "context_file", "gold", "annotator_note"]


def load_system(path: str) -> tuple[dict, dict]:
    values, scores = {}, {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            key = (record["university"], record["label"])
            values[key] = record["value"]
            if record.get("score") is not None:
                scores[key] = float(record["score"])
    return values, scores


def read_judged(paths: list[str]) -> set[tuple[str, str]]:
    judged = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            column = gold_column(reader.fieldnames)
            for row in reader:
                if column and (row.get(column) or "").strip() in {"0", "1"}:
                    judged.add((join_key(row["university"]), row["label"]))
    return judged


def export(args) -> int:
    with open(args.taxonomy, encoding="utf-8") as handle:
        labels = {l["id"]: l for l in json.load(handle)["labels"]}

    available = []
    for name, path in SYSTEMS:
        full = os.path.join(_ROOT, path)
        if os.path.exists(full):
            available.append((name, *load_system(full)))
        else:
            print(f"[warn] {name} not built; skipping ({path})", file=sys.stderr)
    if len(available) < 2:
        print("[error] need at least two built systems to measure disagreement",
              file=sys.stderr)
        return 2
    print(f"[info] comparing {len(available)} systems: "
          f"{', '.join(n for n, _, _ in available)}")

    judged = read_judged(args.exclude or [])
    cells = set()
    for _, values, _ in available:
        cells.update(values)

    scored = []
    for key in sorted(cells):
        if (join_key(key[0]), key[1]) in judged:
            continue
        votes = [values[key] for _, values, _ in available if key in values]
        if len(votes) < 2:
            continue
        positives = sum(votes)
        # Disagreement peaks at an even split and is 0 at unanimity.
        disagreement = min(positives, len(votes) - positives) / (len(votes) / 2)
        # Uncertainty from whichever learned system has a score for this cell; the
        # classifier's probability is calibrated on a sigmoid, so distance from 0.5 is
        # meaningful. The embedding cosine is not, so it is used only as a tiebreak.
        uncertainty = 0.0
        for name, _, scores in available:
            if name in {"classifier", "hybrid"} and key in scores:
                uncertainty = max(uncertainty, 1.0 - 2 * abs(scores[key] - 0.5))
        scored.append({"university": key[0], "label": key[1],
                       "disagreement": round(disagreement, 3),
                       "uncertainty": round(uncertainty, 3),
                       "votes": {n: values.get(key) for n, values, _ in available},
                       "priority": round(disagreement + 0.5 * uncertainty, 4)})

    scored.sort(key=lambda r: (-r["priority"], r["university"], r["label"]))
    batch = scored[:args.n]
    if not batch:
        print("[error] nothing left to select; every cell is already judged",
              file=sys.stderr)
        return 1

    segments = [json.loads(line) for line in open(args.evidence, encoding="utf-8")]
    by_university = defaultdict(list)
    for segment in segments:
        by_university[segment["university"]].append(segment)
    idf = build_idf(segments)

    rows = []
    for item in batch:
        label = labels[item["label"]]
        excerpts = relevant_segments(label, by_university.get(item["university"], []), idf)
        # relevant_segments returns plain strings, IDF-ranked, identically for every
        # row -- the excerpt must not reveal how any system voted.
        rows.append({
            "university": item["university"],
            "label": item["label"],
            "label_name": label["name"],
            "definition": label.get("definition_revised") or label["definition"],
            "related_text": " | ".join(excerpts),
            "context_file": f"context/{safe_name(item['university'])}.txt",
            "gold": "",
            "annotator_note": "",
        })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Why each row was picked, kept OUT of the annotator's file on purpose: showing an
    # annotator that four systems disagree, or what each voted, is an anchor. Same
    # reasoning as make_gold.py's blind template.
    provenance = os.path.splitext(args.out)[0] + "_provenance.json"
    with open(provenance, "w", encoding="utf-8") as handle:
        json.dump({"selected": batch, "candidates": len(scored),
                   "already_judged": len(judged)}, handle, indent=2)

    split = sum(1 for b in batch if b["disagreement"] > 0)
    print(f"[ok]   selected {len(batch)} of {len(scored)} unjudged cells "
          f"({split} where the systems disagree, {len(batch) - split} by uncertainty alone)")
    print(f"[info] wrote {os.path.relpath(args.out, _ROOT)}  (blind: no predictions shown)")
    print(f"[info] wrote {os.path.relpath(provenance, _ROOT)}  (selection reasons, not for the annotator)")
    return 0


def promote(args) -> int:
    """Fold a reviewed batch into training supervision. Never into gold."""
    path = args.promote
    if not os.path.exists(path):
        print(f"[error] no such file: {path}", file=sys.stderr)
        return 2

    segments = [json.loads(line) for line in open(args.evidence, encoding="utf-8")]
    by_university = defaultdict(list)
    for segment in segments:
        by_university[join_key(segment["university"])].append(segment)

    verified_negatives, bag_positives, unjudged = [], [], 0
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        column = gold_column(reader.fieldnames)
        if column is None:
            print(f"[error] no gold column in {path}", file=sys.stderr)
            return 2
        for row in reader:
            value = (row.get(column) or "").strip()
            if value not in {"0", "1"}:
                unjudged += 1
                continue
            key = join_key(row["university"])
            if value == "0":
                for segment in by_university.get(key, []):
                    verified_negatives.append({"segment_id": segment["segment_id"],
                                               "text": segment["text"],
                                               "label": row["label"], "value": 0,
                                               "university": row["university"],
                                               "source": os.path.basename(path)})
            else:
                bag_positives.append({"university": row["university"],
                                      "label": row["label"],
                                      "segment_ids": [s["segment_id"]
                                                      for s in by_university.get(key, [])],
                                      "source": os.path.basename(path)})

    os.makedirs(os.path.join(_ROOT, "data/ml"), exist_ok=True)
    out_path = os.path.join(_ROOT, "data/ml/human_supervision.jsonl")
    existing = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            record = json.loads(line)
            existing.add((record.get("kind"), record.get("segment_id"),
                          record.get("university"), record.get("label")))
    added = 0
    with open(out_path, "a", encoding="utf-8") as handle:
        for record in verified_negatives:
            key = ("segment_negative", record["segment_id"], None, record["label"])
            if key in existing:
                continue
            existing.add(key)
            handle.write(json.dumps({"kind": "segment_negative", **record},
                                    ensure_ascii=False) + "\n")
            added += 1
        for record in bag_positives:
            key = ("bag_positive", None, record["university"], record["label"])
            if key in existing:
                continue
            existing.add(key)
            handle.write(json.dumps({"kind": "bag_positive", **record},
                                    ensure_ascii=False) + "\n")
            added += 1

    manifest_path = os.path.join(_ROOT, MANIFEST)
    manifest = {"training_gold_files": []}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    relative = os.path.relpath(os.path.abspath(path), _ROOT)
    if relative not in manifest["training_gold_files"]:
        manifest["training_gold_files"].append(relative)
    manifest["note"] = ("Gold files consumed as training supervision. evaluate_ml.py "
                        "refuses to score against anything listed here.")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"[ok]   {len(verified_negatives)} verified segment negatives from "
          f"{len({(r['university'], r['label']) for r in verified_negatives})} negative cell(s)")
    print(f"[ok]   {len(bag_positives)} bag-positive constraint(s) -- recorded, not "
          f"expanded into segment labels")
    print(f"[info] {added} new record(s) appended to data/ml/human_supervision.jsonl"
          + (f"; {unjudged} row(s) left blank" if unjudged else ""))
    print(f"[info] {relative} recorded in {MANIFEST}; it can no longer be used as a "
          f"held-out gold file")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--out", default=os.path.join(_ROOT, "data/gold/active_batch_template.csv"))
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--exclude", action="append", default=None,
                        help="gold csv whose judged cells to skip; repeatable")
    parser.add_argument("--promote", default=None,
                        help="a completed annotation batch to fold into training")
    args = parser.parse_args()
    return promote(args) if args.promote else export(args)


if __name__ == "__main__":
    raise SystemExit(main())
