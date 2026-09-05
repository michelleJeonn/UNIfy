"""
Keyword baseline for accommodation extraction.

Deliberately simple: seed-phrase matching over the evidence segments, producing a
university x label matrix plus the segment ids that triggered each positive.  It
exists to be *beaten* -- it is the number an embedding classifier or an LLM
extractor has to improve on before either is worth its complexity.

Two labels (peer_support, crisis_line_24_7) also exist as hand-coded columns in the
source sheet.  Those columns are recorded alongside the prediction but are NOT used
as the prediction: annotation showed the peer_support column is over-inclusive,
marking "yes" wherever a school has anything peer-adjacent -- "Peer note-taking" is
note-taking, "Counsellor Assisted E-Support" is counselling, and neither is a
mentorship programme.  Mixing that column into the output would also mean the
reported score describes two different systems at once.

Outputs:
    data/clean/accommodations_baseline.csv        28 x 32 matrix of 0/1
    data/clean/accommodations_baseline.jsonl      per (university, label) with citations

Usage:
    python extraction/baseline.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def seed_pattern(seed: str) -> re.Pattern:
    """Compile a seed phrase into a tolerant matcher.

    Internal spaces and hyphens are interchangeable ("note-taking" ~ "note taking"),
    and a trailing plural is allowed.  The plural matters more than it sounds: this
    corpus is written in the plural throughout ("quiet/private rooms for exams",
    "ramps, elevators, automatic doors"), so a closing \b on the singular seed
    silently scores zero for whole categories.
    """
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", seed.strip()) if p]
    body = r"[\s\-]+".join(parts)
    prefix = r"\b" if seed[:1].isalnum() else ""
    suffix = r"(?:e?s)?\b" if seed[-1:].isalnum() else ""
    return re.compile(prefix + body + suffix, re.I)


def load_taxonomy(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        taxonomy = json.load(handle)
    for label in taxonomy["labels"]:
        label["_patterns"] = [seed_pattern(s) for s in label["seeds"]]
        label["_context"] = [seed_pattern(c) for c in label.get("context", [])]
    return taxonomy["labels"]


def load_evidence(path: str) -> dict[str, list[dict]]:
    by_university: dict[str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            by_university[record["university"]].append(record)
    return by_university


def load_hand_coded(path: str) -> dict[str, dict]:
    """Read the boolean columns the source sheet already provides."""
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["university"]: row for row in csv.DictReader(handle)}


def predict(label: dict, segments: list[dict]) -> list[dict]:
    """Return the segments that trigger this label."""
    hits = []
    for segment in segments:
        text = segment["text"]
        if not any(p.search(text) for p in label["_patterns"]):
            continue
        # Some labels need a disambiguating word in the same segment, e.g. "breaks"
        # only counts as an exam accommodation near "exam"/"test".
        if label["_context"] and not any(c.search(text) for c in label["_context"]):
            continue
        hits.append(segment)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--universities", default=os.path.join(_ROOT, "data/clean/universities.csv"))
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/clean"))
    args = parser.parse_args()

    for path in (args.taxonomy, args.evidence, args.universities):
        if not os.path.exists(path):
            print(f"[error] missing input: {path}", file=sys.stderr)
            return 2

    labels = load_taxonomy(args.taxonomy)
    evidence = load_evidence(args.evidence)
    hand_coded = load_hand_coded(args.universities)
    universities = sorted(evidence)

    matrix: dict[str, dict[str, int]] = {}
    detail: list[dict] = []
    disagreements: list[str] = []

    for university in universities:
        segments = evidence[university]
        row: dict[str, int] = {}
        for label in labels:
            hits = predict(label, segments)
            value = int(bool(hits))

            column_value = None
            column = label.get("hand_coded_column")
            if column and column in hand_coded.get(university, {}):
                column_value = int(str(hand_coded[university][column]).strip().lower()
                                   in {"true", "1", "yes"})
                if column_value != value:
                    disagreements.append(
                        f"{university} / {label['id']}: column={column_value} keyword={value}"
                    )

            row[label["id"]] = value
            detail.append({
                "university": university,
                "label": label["id"],
                "value": value,
                "source": "keyword",
                "hand_coded_column_value": column_value,
                "n_hits": len(hits),
                "citations": [h["segment_id"] for h in hits[:5]],
                "evidence": [h["text"][:160] for h in hits[:3]],
            })
        matrix[university] = row

    os.makedirs(args.out_dir, exist_ok=True)
    matrix_path = os.path.join(args.out_dir, "accommodations_baseline.csv")
    with open(matrix_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["university"] + [l["id"] for l in labels])
        for university in universities:
            writer.writerow([university] + [matrix[university][l["id"]] for l in labels])

    detail_path = os.path.join(args.out_dir, "accommodations_baseline.jsonl")
    with open(detail_path, "w", encoding="utf-8") as handle:
        for record in detail:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[ok]   {len(universities)} universities x {len(labels)} labels")
    print(f"[info] wrote {os.path.relpath(matrix_path, _ROOT)}")
    print(f"[info] wrote {os.path.relpath(detail_path, _ROOT)}")

    print("\npredicted positives per label (of 28 schools):")
    for label in labels:
        n = sum(matrix[u][label["id"]] for u in universities)
        flag = "  <- no variance" if n in (0, len(universities)) else ""
        marker = "*" if label.get("near_universal") else " "
        print(f" {marker} {n:3d}  {label['id']}{flag}")
    print("  (* = flagged near-universal in the taxonomy; excluded from scoring)")

    if disagreements:
        print(f"\n[info] {len(disagreements)} case(s) where the source's hand-coded column "
              f"disagrees with the text; the column is recorded, not used:")
        for line in disagreements[:5]:
            print(f"       {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
