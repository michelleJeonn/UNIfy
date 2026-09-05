"""
Build the hand-annotation template for the gold set.

Sampling is stratified by the baseline's own prediction: for each label we draw up
to N predicted-positive and N predicted-negative schools.  Positives let us measure
precision, negatives are the only way to find false negatives and therefore the only
way to measure recall.  Annotating a purely random sample would spend almost all the
effort on the many easy negatives of rare labels.

This is not an unbiased sample of the matrix, so raw positive counts here are NOT
base-rate estimates; ``evaluate.py`` reweights by stratum size when it reports.

Near-universal labels are excluded: with 28 of 28 predicted positive there is no
negative stratum, nothing to discriminate, and no useful metric.

The template is **blind**: it carries no prediction, no stratum, and no hit count,
and it shows the same kind of excerpt for every row.  If the annotator can tell which
cells the extractor called positive -- including indirectly, from rows that have
evidence attached versus rows that do not -- then agreement is partly measuring
anchoring rather than accuracy, and the resulting precision is inflated.  The excerpts
are therefore the school's own most lexically related segments, ranked identically
whichever way the extractor voted.  ``evaluate.py`` recovers the stratum from the
predictions file when scoring.

Writes:
    data/gold/gold_template.csv   one row per cell to judge, with evidence inline
    data/gold/sampling.json       stratum sizes, needed to reweight the metrics
    data/gold/context/<uni>.txt   every segment for a school, for judging negatives

Usage:
    python extraction/make_gold.py [--per-stratum 3] [--seed 0]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def join_key(name: str) -> str:
    """Match evaluate.py: spreadsheets rewrite typographic punctuation on round-trip."""
    text = unicodedata.normalize("NFKC", str(name)).translate(
        {0x2018: "'", 0x2019: "'", 0x201B: "'", 0x2032: "'"})
    return re.sub(r"\s+", " ", text).strip().casefold()


def safe_name(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", name).strip("_")


# Truncating to a stem lets a seed match its inflections ("interpretation" ->
# "interp" -> matches "interpreting"), and a 3-char floor keeps acronyms that
# carry the whole label, like ASL.
STEM_LENGTH = 6
MIN_TOKEN = 3


def tokenize(text: str) -> list[str]:
    return [t[:STEM_LENGTH] for t in re.split(r"[^a-z0-9]+", text.lower())
            if len(t) >= MIN_TOKEN]


def build_idf(segments: list[dict]) -> dict[str, float]:
    """Inverse document frequency over the whole corpus.

    Without it, ranking counts a hit on "time" the same as a hit on "captioning",
    and generic filler outranks the one segment that decides the label -- which is
    how an annotator came to judge York Keele's captioning on the text
    "Extra time and breaks for exams".
    """
    document_frequency: Counter = Counter()
    for segment in segments:
        document_frequency.update(set(tokenize(segment["text"])))
    total = max(1, len(segments))
    return {token: math.log(total / count) for token, count in document_frequency.items()}


def relevant_segments(label: dict, segments: list[dict], idf: dict[str, float],
                      k: int = 3) -> list[str]:
    """The school's own segments most related to this label, IDF-weighted.

    Computed identically for every row so the excerpt cannot reveal how the
    extractor voted.  Deliberately cruder than the extractor's own matching: it
    ranks reading material, it does not decide the label.
    """
    tokens = {t for seed in label["seeds"] for t in tokenize(seed)}
    if not tokens:
        tokens = set(tokenize(label["id"].replace("_", " ")))
    default_idf = math.log(max(1, len(segments)))

    scored, seen = [], set()
    for segment in segments:
        text = segment["text"]
        key = re.sub(r"\s+", " ", text).strip().lower()
        if key in seen:          # the same sentence recurs across columns
            continue
        lowered = text.lower()
        score = sum(idf.get(t, default_idf) for t in tokens if t in lowered)
        if score > 0:
            seen.add(key)
            # Longest first within a score tier: more context is easier to judge.
            scored.append((score, len(text), text))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [text for _, _, text in scored[:k]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--taxonomy", default=os.path.join(_ROOT, "extraction/taxonomy.json"))
    parser.add_argument("--evidence", default=os.path.join(_ROOT, "data/clean/evidence.jsonl"))
    parser.add_argument("--baseline", default=os.path.join(_ROOT, "data/clean/accommodations_baseline.jsonl"))
    parser.add_argument("--out-dir", default=os.path.join(_ROOT, "data/gold"))
    parser.add_argument("--per-stratum", type=int, default=3,
                        help="schools sampled per (label, predicted class)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--labels", default="",
                        help="comma-separated label ids; default is every scorable label")
    parser.add_argument("--exclude", default=None,
                        help="an existing gold csv whose cells should NOT be sampled again")
    parser.add_argument("--rejudge", default=None,
                        help="an existing gold csv; emit exactly its cells for --labels, "
                             "with fresh excerpts and a blank verdict. Use after a definition "
                             "change, so before/after is measured on the same cells.")
    parser.add_argument("--out", default=None, help="output csv (default gold_template.csv)")
    args = parser.parse_args()

    wanted = {l.strip() for l in args.labels.split(",") if l.strip()}

    def read_cells(path: str) -> set[tuple[str, str]]:
        if not path:
            return set()
        if not os.path.exists(path):
            # Returning an empty set here would silently fall through to a full
            # re-sample, which looks like success and quietly produces the wrong batch.
            raise SystemExit(f"[error] file not found: {path}")
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return {(join_key(r["university"]), r["label"]) for r in csv.DictReader(handle)}

    excluded = read_cells(args.exclude)
    rejudge = read_cells(args.rejudge)

    for path in (args.taxonomy, args.evidence, args.baseline):
        if not os.path.exists(path):
            print(f"[error] missing input: {path} -- run corpus.py and baseline.py first",
                  file=sys.stderr)
            return 2

    with open(args.taxonomy, encoding="utf-8") as handle:
        labels = {l["id"]: l for l in json.load(handle)["labels"]}

    segments: dict[str, list[dict]] = defaultdict(list)
    with open(args.evidence, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            segments[record["university"]].append(record)

    predictions: dict[tuple[str, str], dict] = {}
    for line in open(args.baseline, encoding="utf-8"):
        record = json.loads(line)
        predictions[(record["university"], record["label"])] = record

    universities = sorted(segments)
    idf = build_idf([s for group in segments.values() for s in group])
    rng = random.Random(args.seed)

    rows, sampling = [], {}
    for label_id, label in labels.items():
        if label.get("near_universal"):
            continue
        if wanted and label_id not in wanted:
            continue

        # Re-judge mode: reuse the exact cells already judged for this label so the
        # effect of a definition change is measured on the same universities.
        if rejudge:
            targets = [u for u in universities if (join_key(u), label_id) in rejudge]
            for university in targets:
                rows.append({
                    "university": university, "label": label_id,
                    "label_name": label["name"], "definition": label["definition"],
                    "related_text": " | ".join(relevant_segments(label, segments[university], idf))
                                    or "(nothing lexically related -- check the context file)",
                    "context_file": f"context/{safe_name(university)}.txt",
                    "gold": "", "annotator_note": "",
                })
            sampling[label_id] = {"rejudged": len(targets)}
            continue
        positives = [u for u in universities
                     if predictions[(u, label_id)]["value"] == 1
                     and (join_key(u), label_id) not in excluded]
        negatives = [u for u in universities
                     if predictions[(u, label_id)]["value"] == 0
                     and (join_key(u), label_id) not in excluded]
        if not positives and not negatives:
            sampling[label_id] = {"skipped": "every cell already judged"}
            continue
        if not positives or not negatives:
            # Still worth sampling the side that exists: with no negative stratum
            # recall is unmeasurable, but precision is not.
            sampling[label_id] = {"partial": "only one stratum available",
                                  "n_positive": len(positives), "n_negative": len(negatives)}
        sampling[label_id] = {"n_positive": len(positives), "n_negative": len(negatives),
                              "sampled_positive": min(args.per_stratum, len(positives)),
                              "sampled_negative": min(args.per_stratum, len(negatives))}
        for pool in (positives, negatives):
            for university in rng.sample(pool, min(args.per_stratum, len(pool))):
                excerpts = relevant_segments(label, segments[university], idf)
                rows.append({
                    "university": university,
                    "label": label_id,
                    "label_name": label["name"],
                    "definition": label["definition"],
                    "related_text": " | ".join(excerpts) if excerpts
                                    else "(nothing lexically related -- check the context file)",
                    "context_file": f"context/{safe_name(university)}.txt",
                    "gold": "",
                    "annotator_note": "",
                })

    if not rows:
        print("[error] nothing to sample -- every requested cell is already judged",
              file=sys.stderr)
        return 1
    rows.sort(key=lambda r: (r["university"], r["label"]))

    os.makedirs(os.path.join(args.out_dir, "context"), exist_ok=True)
    template = args.out or os.path.join(args.out_dir, "gold_template.csv")
    with open(template, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with open(os.path.join(args.out_dir, "sampling.json"), "w", encoding="utf-8") as handle:
        json.dump({"seed": args.seed, "per_stratum": args.per_stratum,
                   "n_universities": len(universities), "labels": sampling},
                  handle, indent=2, ensure_ascii=False)

    for university in universities:
        path = os.path.join(args.out_dir, "context", f"{safe_name(university)}.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"{university}\n{'=' * len(university)}\n")
            by_column: dict[str, list[str]] = defaultdict(list)
            for segment in segments[university]:
                by_column[segment["column"]].append(segment["text"])
            for column, texts in by_column.items():
                handle.write(f"\n[{column}]\n")
                for text in dict.fromkeys(texts):
                    handle.write(f"  - {text}\n")

    judged = len(rows)
    scored_labels = sum(1 for v in sampling.values() if "skipped" not in v)
    print(f"[ok]   {judged} cells to judge across {scored_labels} labels")
    print(f"[info] wrote {os.path.relpath(template, _ROOT)}")
    print(f"[info] wrote per-school context files to {os.path.relpath(args.out_dir, _ROOT)}/context/")
    skipped = {k: v["skipped"] for k, v in sampling.items() if "skipped" in v}
    if skipped:
        print(f"[warn] {len(skipped)} label(s) not sampled (baseline predicts one class for all "
              f"28 schools, so precision/recall are undefined):")
        for label_id in skipped:
            print(f"       {label_id}")
    print("\nTo annotate: fill the `gold` column with 1 or 0 for each row, save as "
          "data/gold/gold.csv, then run: python extraction/evaluate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
