"""
Build the extraction evidence corpus.

Turns the accessibility prose in the university sheet into small, individually
addressable segments so that every downstream label can cite the exact text it came
from.  A label without a citation is not checkable, and this dataset's whole value
proposition is that its claims are traceable.

Two decisions worth stating:

* **Union, not mode.**  ``preprocessing.py`` picks one canonical wording per
  (university, column) for display.  For extraction we instead keep *every* distinct
  wording.  Where transcription left a school with several variants, the extra text
  is extra evidence rather than a conflict to resolve -- Guelph's disability-types
  cell is the case in point: the minority variant holds the content the majority
  wording lacks.  Resolving those conflicts still matters for display; it does not
  block extraction.

* **Line-level segments.**  The source prose is written one claim per line
  ("Exam accommodations: private room, assistive tech").  Lines are therefore the
  natural unit.  Long unbroken paragraphs are split further on sentence boundaries
  so no segment is too coarse to cite usefully.

Output: ``data/clean/evidence.jsonl``, one JSON object per segment:
    {"segment_id", "university", "column", "variant", "text"}

Usage:
    python extraction/corpus.py [--db Unify.db] [--out data/clean/evidence.jsonl]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys

# preprocessing.py lives at the repo root and owns the sheet-reading rules.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("pp", os.path.join(_ROOT, "preprocessing.py"))
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

# Segments shorter than this carry no extractable claim (stray bullets, "N/A").
MIN_SEGMENT_CHARS = 12
# Above this, split a line further on sentence boundaries.
MAX_SEGMENT_CHARS = 400

SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
BULLET_PREFIX = re.compile(r"^\s*(?:[-•·*•●]|\d+[.)]|Step\s*\d+[.:]?)\s*", re.I)


def split_segments(text: str) -> list[str]:
    """Split one cell into citable segments: lines first, then long lines by sentence."""
    segments: list[str] = []
    for raw_line in re.split(r"[\r\n]+", text):
        line = BULLET_PREFIX.sub("", raw_line).strip(" \t;")
        if not line:
            continue
        pieces = SENTENCE_END.split(line) if len(line) > MAX_SEGMENT_CHARS else [line]
        for piece in pieces:
            piece = piece.strip(" \t;-–—")
            if len(piece) >= MIN_SEGMENT_CHARS:
                segments.append(piece)
    return segments


def segment_id(university: str, column: str, text: str) -> str:
    """Stable id: survives re-runs and reordering, so gold labels keep pointing at
    the same text."""
    digest = hashlib.sha1(f"{university}\x00{column}\x00{text}".encode("utf-8"))
    return digest.hexdigest()[:12]


def build(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    try:
        body = pp.read_sheet(conn, pp.RAW_UNI).map(pp.norm_ws)
    finally:
        conn.close()
    body = body.assign(university=body["University Name"].ffill())

    records: list[dict] = []
    seen: set[str] = set()
    for university, group in body.groupby("university", sort=False):
        for column in pp.UNIVERSITY_TEXT_COLUMNS:
            # Distinct wordings only; keep the longest spelling of each.
            variants: dict[str, str] = {}
            for value in group[column].tolist():
                if isinstance(value, str) and value:
                    key = pp.norm_key(value)
                    if len(value) > len(variants.get(key, "")):
                        variants[key] = value
            for variant_index, value in enumerate(variants.values()):
                for text in split_segments(value):
                    sid = segment_id(university, column, text)
                    if sid in seen:      # identical text repeated across variants
                        continue
                    seen.add(sid)
                    records.append({
                        "segment_id": sid,
                        "university": university,
                        "column": pp.UNIVERSITY_COLUMN_NAMES[column],
                        "variant": variant_index,
                        "text": text,
                    })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.path.join(_ROOT, "Unify.db"))
    parser.add_argument("--out", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[error] database not found: {args.db}", file=sys.stderr)
        return 2

    records = build(args.db)
    if not records:
        print("[error] no segments produced", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    universities = {r["university"] for r in records}
    lengths = sorted(len(r["text"]) for r in records)
    print(f"[ok]   {len(records):,} segments across {len(universities)} universities")
    print(f"[info] segment length: median {lengths[len(lengths) // 2]}, "
          f"p90 {lengths[int(len(lengths) * 0.9)]}, max {lengths[-1]} chars")
    print(f"[info] wrote {args.out}")

    thin = sorted(universities, key=lambda u: sum(1 for r in records if r["university"] == u))[:3]
    for university in thin:
        count = sum(1 for r in records if r["university"] == university)
        print(f"[info] fewest segments: {count:4d}  {university}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
