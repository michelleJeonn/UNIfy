"""
UNIfy preprocessing pipeline.

Reads the three raw sheets loaded from the source workbook by ``pj.py`` and emits
validated, analysis-ready tables.

The source workbook is a hand-maintained spreadsheet, not an export, so it carries
three structural quirks that a generic "clean every column the same way" pass gets
wrong.  Each is handled explicitly here:

  1. Two-row header.  Row 0 of every sheet holds merged *group* headers
     ("University information", "Accessibility Services"); the real column names sit
     in row 1.  We promote row 1 and drop it from the body.

  2. Merged cells.  ``University Name`` and ``Faculty`` are set only on the first row
     of each block and are null for the rest.  They must be forward-filled in sheet
     order.  Filling them by column mode -- as a generic imputer does -- relabels
     every program with whichever name sorts first, which is how all 1,690 programs
     previously ended up attributed to Algoma University.

  3. Free text that is not a number.  ``Average GPA`` ("mid 80s", "low 80s (co-op),
     high 70s (regular)"), ``prereq courses`` ("ENG4U, 1 of MHF4U/MCV4U") and the
     minimum-requirement column are structured expressions.  They are parsed into
     explicit fields and the raw string is always retained alongside.

Nothing is imputed.  A value we cannot parse stays null and is listed in the quality
report rather than being replaced by a median or a mode.

Outputs (default ``data/clean/``):
    programs.csv / .parquet      one row per university-program  (1,690)
    universities.csv / .parquet  one row per university          (28)
    vocabulary.json              controlled vocabularies for UI + label space
    quality_report.md            unparsed values, text conflicts, empty columns

Usage:
    python preprocessing.py [path/to/Unify.db] [--out data/clean] [--write-db]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from typing import Any

import pandas as pd

RAW_UNI = "uni info"
RAW_STUDENT = "student info"
RAW_USER = "user input"

EXPECTED_UNIVERSITIES = 28
EXPECTED_PROGRAMS = 1690

# Columns carried at the university level: identical (modulo transcription noise)
# for every program of a given school.
UNIVERSITY_TEXT_COLUMNS = [
    "types of physical disability supported",
    "types of mental disability supported",
    "(P) accommodation services offered",
    "(M) accommodation services offered",
    "documentation requirements",
    "how to submit required docs",
    "registration process",
    "counselling services",
    "peer support/ mentorship program",
    "24/7 support info (Y /N)",
    "24/7 support info (contact info)",
    "OSAP disability eligibility info",
    "disability bursaries/ scholarships",
]

UNIVERSITY_COLUMN_NAMES = {
    "types of physical disability supported": "physical_disabilities_supported",
    "types of mental disability supported": "mental_disabilities_supported",
    "(P) accommodation services offered": "physical_accommodations",
    "(M) accommodation services offered": "mental_accommodations",
    "documentation requirements": "documentation_requirements",
    "how to submit required docs": "documentation_submission",
    "registration process": "registration_process",
    "counselling services": "counselling_services",
    "peer support/ mentorship program": "peer_support",
    "24/7 support info (Y /N)": "support_24_7",
    "24/7 support info (contact info)": "support_24_7_contact",
    "OSAP disability eligibility info": "osap_eligibility",
    "disability bursaries/ scholarships": "bursaries",
}

# Two of the "text" columns are actually hand-coded Y/N flags (stored as 1/0),
# not prose.  They are already labelled data and must be typed as booleans rather
# than carried as one-character strings.
UNIVERSITY_BOOLEAN_COLUMNS = {
    "peer support/ mentorship program",
    "24/7 support info (Y /N)",
}

# Placeholders the spreadsheet uses for "nothing here".
NULL_TOKENS = {"", "nan", "none", "null", "n/a", "na", "x", "-", "--"}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def norm_ws(value: Any) -> str | None:
    """Collapse whitespace (including NBSP) and map placeholder tokens to None."""
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text).strip()
    if text.lower() in NULL_TOKENS:
        return None
    return text


def cell(row: pd.Series, name: str) -> str | None:
    """Read one cell as a clean string or None.

    Arrow-backed columns yield ``pd.NA`` for missing values.  ``pd.NA`` is not
    ``None`` and raises on ``bool()``, so reading cells directly makes null checks
    quietly wrong -- it is what silently turned 18 missing supplemental-application
    flags into ``False``.  Everything downstream reads through here.
    """
    return norm_ws(row.get(name))


def norm_key(value: Any) -> str:
    """Aggressive normalisation used only to decide whether two texts are the same."""
    text = norm_ws(value) or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \"'“”").lower()


# --------------------------------------------------------------------------- #
# Average GPA:  "mid 80s" | "75-77%" | "low 80s (co-op), high 70s (regular)"
# --------------------------------------------------------------------------- #

BAND_OFFSETS = {"low": (0, 3), "mid": (4, 6), "high": (7, 9)}
BAND_RE = re.compile(r"\b(low|mid|high)\s*(?:(?:to|-|–|—)\s*(low|mid|high)\s*)?(\d0)\s*s\b")
PERCENT_RE = re.compile(r"\b(\d{2,3}(?:\.\d+)?)\b")
COOP_RE = re.compile(r"co-?op")


def _range_of(segment: str) -> tuple[float | None, float | None]:
    """Parse one comma-free segment into a (low, high) percent range."""
    bands = []
    for match in BAND_RE.finditer(segment):
        first, second, decade = match.group(1), match.group(2) or match.group(1), int(match.group(3))
        bands.append((decade + BAND_OFFSETS[first][0], decade + BAND_OFFSETS[second][1]))
    if bands:
        return float(min(b[0] for b in bands)), float(max(b[1] for b in bands))

    # No band words: drop parentheticals and trailing prose, then read bare numbers.
    stripped = re.sub(r"\([^)]*\)?", " ", segment)
    stripped = re.split(r"\b(?:plus|with|weighting|recently)\b", stripped)[0]
    numbers = [float(n) for n in PERCENT_RE.findall(stripped) if 0 <= float(n) <= 100]
    if numbers:
        return min(numbers), max(numbers)
    return None, None


def parse_average_gpa(text: Any) -> dict[str, Any]:
    """Split an ``Average GPA`` cell into regular / co-op percent ranges."""
    result: dict[str, Any] = {
        "avg_gpa_low": None,
        "avg_gpa_high": None,
        "avg_gpa_coop_low": None,
        "avg_gpa_coop_high": None,
        "avg_gpa_has_note": False,
    }
    raw = norm_ws(text)
    if raw is None:
        return result
    text_l = raw.lower().replace("%", "")

    if COOP_RE.search(text_l):
        coop_parts, regular_parts = [], []
        for segment in re.split(r"[,;]", text_l):
            (coop_parts if COOP_RE.search(segment) else regular_parts).append(segment)
        low, high = _range_of(" ".join(regular_parts)) if regular_parts else (None, None)
        coop_low, coop_high = _range_of(" ".join(coop_parts))
        if low is None:  # only a co-op figure was recorded
            low, high = coop_low, coop_high
        result.update(
            avg_gpa_low=low, avg_gpa_high=high,
            avg_gpa_coop_low=coop_low, avg_gpa_coop_high=coop_high,
        )
    else:
        low, high = _range_of(text_l)
        result.update(avg_gpa_low=low, avg_gpa_high=high)

    # Flag cells whose prose we did not fully consume, so they can be reviewed.
    leftover = BAND_RE.sub(" ", text_l)
    leftover = PERCENT_RE.sub(" ", leftover)
    leftover = re.sub(r"\b(co-?op|regular|to|and|or|in|avg|average|s)\b", " ", leftover)
    result["avg_gpa_has_note"] = bool(re.search(r"[a-z]{2,}", leftover))
    return result


# --------------------------------------------------------------------------- #
# prereq courses:  "ENG4U, 1 of MHF4U/MCV4U, two sciences (SBI4U, SCH4U, SPH4U)"
# --------------------------------------------------------------------------- #

COURSE_RE = re.compile(r"\b([A-Z]{3}\d[A-Z])\b")
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
SENIOR_COURSES_RE = re.compile(
    r"\+?\s*(\d+|one|two|three|four|five|six)\s*(?:additional\s*)?\(?4U/4M\)?\s*courses", re.I
)
COUNT_RE = re.compile(r"\b(\d+|one|two|three|four|five|six)\s+(?:of\b|\w+\s*\()", re.I)
# "1 4U Math", "1 other 4U course", "six grade 12 4U/M courses" -- a count of senior
# courses constrained by subject, with no specific code named.
LEVEL_RE = re.compile(r"\b4\s*[UM]\b|\b4U\s*/\s*4?M\b", re.I)
LEAD_COUNT_RE = re.compile(r"^\s*(?:any\s+)?(\d+|one|two|three|four|five|six)\b", re.I)
# Cell references / formula fragments that leaked out of the workbook.
FORMULA_RE = re.compile(r"[A-Z]{1,2}\d+\s*:\s*[A-Z]{1,2}\d+|^\s*[+=]")


def _as_int(token: str) -> int:
    return int(token) if token.isdigit() else WORD_NUMBERS[token.lower()]


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside parentheses."""
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def parse_prerequisites(text: Any) -> tuple[list[dict], list[str]]:
    """Return (requirement groups, chunks we could not read).

    A group is ``{"n": k, "options": [codes]}`` meaning "k course(s) from this set".
    ``{"n": k, "options": [], "any_senior": True}`` means "k further 4U/4M courses".
    This is the shape an eligibility check needs: satisfying every group satisfies
    the prerequisite.
    """
    raw = norm_ws(text)
    if raw is None:
        return [], []

    groups: list[dict] = []
    unparsed: list[str] = []
    for chunk in _split_top_level(raw):
        senior = SENIOR_COURSES_RE.search(chunk)
        if senior:
            for code in COURSE_RE.findall(chunk):
                groups.append({"n": 1, "options": [code]})
            groups.append({"n": _as_int(senior.group(1)), "options": [], "any_senior": True})
            continue

        if FORMULA_RE.search(chunk):
            unparsed.append(chunk)  # corrupted source cell -- do not guess
            continue

        codes = COURSE_RE.findall(chunk)
        if not codes:
            # A subject-constrained count of senior courses, e.g. "1 4U Math".
            # We record how many are needed and keep the wording; we do not try to
            # resolve "Math" to a code list.
            if LEVEL_RE.search(chunk):
                lead = LEAD_COUNT_RE.match(chunk)
                count_n = _as_int(lead.group(1)) if lead else 1
                groups.append({"n": count_n, "options": [], "any_senior": True,
                               "description": chunk})
            else:
                unparsed.append(chunk)
            continue

        count = COUNT_RE.search(chunk)
        if count:
            groups.append({"n": min(_as_int(count.group(1)), len(codes)), "options": codes})
        elif len(codes) > 1 and "/" in chunk:
            groups.append({"n": 1, "options": codes})  # "ENG4U/FRA4U" = one of
        else:
            groups.extend({"n": 1, "options": [code]} for code in codes)
    return groups, unparsed


# --------------------------------------------------------------------------- #
# Minimum requirement:  "min 60 in ENG4U, 70 in MHF4U" | "above 70 in all"
# --------------------------------------------------------------------------- #

ALL_PREREQ_RE = re.compile(
    r"(?:min|above|minimum)?\s*(\d{2})\s*%?\s*(?:avg|average)?\s*in\s+all\b", re.I
)
OVERALL_RE = re.compile(
    r"(\d{2})\s*%?\s*(?:overall|combined)?\s*(?:on\s+)?(?:academic\s*)?(?:average|avg)|"
    r"(?:overall|combined)\s*(?:academic\s*)?(?:average|avg)\s*(?:of\s*)?(\d{2})",
    re.I,
)
COURSE_MIN_RE = re.compile(
    r"(?:min|minimum)?\s*(\d{2})\s*%?\s*in\s+((?:[A-Z]{3}\d[A-Z])(?:\s*/\s*[A-Z]{3}\d[A-Z])*)", re.I
)


def parse_minimum_requirement(text: Any) -> dict[str, Any]:
    """Pull the numeric floors out of the free-text requirement column."""
    result: dict[str, Any] = {
        "min_req_overall": None,
        "min_req_all_prereqs": None,
        "min_req_courses": [],
        "min_req_parsed": False,
    }
    raw = norm_ws(text)
    if raw is None:
        return result

    consumed = []

    match = ALL_PREREQ_RE.search(raw)
    if match:
        result["min_req_all_prereqs"] = float(match.group(1))
        consumed.append(match.span())

    match = OVERALL_RE.search(raw)
    if match:
        result["min_req_overall"] = float(match.group(1) or match.group(2))
        consumed.append(match.span())

    course_minimums = []
    for match in COURSE_MIN_RE.finditer(raw):
        floor = float(match.group(1))
        for code in re.findall(r"[A-Z]{3}\d[A-Z]", match.group(2).upper()):
            course_minimums.append({"course": code, "min": floor})
        consumed.append(match.span())
    result["min_req_courses"] = course_minimums

    # A cell that is nothing but a number is an overall minimum.
    if not consumed and re.fullmatch(r"\d{2}(?:\.\d+)?", raw):
        result["min_req_overall"] = float(raw)
        consumed.append((0, len(raw)))

    result["min_req_parsed"] = bool(consumed)
    return result


# --------------------------------------------------------------------------- #
# sheet readers
# --------------------------------------------------------------------------- #

def read_sheet(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    """Read a raw sheet and promote its second physical row to the header."""
    frame = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
    header = [norm_ws(v) or f"unnamed_{i}" for i, v in enumerate(frame.iloc[0])]
    body = frame.iloc[1:].reset_index(drop=True)
    body.columns = header
    return body


def build_programs(body: pd.DataFrame, issues: dict) -> pd.DataFrame:
    """One row per university-program, with the parsed admission fields."""
    text = body.map(norm_ws)

    # Merged cells: forward-fill in sheet order.  This is the fix for the
    # every-program-is-Algoma bug; order must not be sorted before this point.
    university = text["University Name"].ffill()
    faculty = text["Faculty"].ffill()

    if university.isna().any():
        raise ValueError(
            f"{int(university.isna().sum())} rows precede the first university name; "
            "the sheet order was not preserved on load."
        )

    records = []
    for position, (idx, row) in enumerate(text.iterrows(), start=1):
        prereq_raw = cell(row, "prereq courses")
        min_req_raw = cell(row, "Minimum / Approximate GPA Requirement")
        avg_gpa_raw = cell(row, "Average GPA")
        program_name = cell(row, "Programs")

        groups, unparsed = parse_prerequisites(prereq_raw)
        minimums = parse_minimum_requirement(min_req_raw)
        averages = parse_average_gpa(avg_gpa_raw)

        supplemental = cell(row, "Supplemental application (Y/N)")
        if supplemental is not None:
            supplemental = supplemental.lower() in {"1", "1.0", "y", "yes", "true"}

        if unparsed:
            issues["prereq_unparsed"].append((university[idx], program_name, unparsed))
        if avg_gpa_raw and averages["avg_gpa_low"] is None:
            issues["avg_gpa_unparsed"].append((university[idx], program_name, avg_gpa_raw))
        if min_req_raw and not minimums["min_req_parsed"]:
            issues["min_req_unparsed"].append((university[idx], program_name, min_req_raw))

        records.append({
            "program_id": position,
            "university": university[idx],
            "faculty": faculty[idx],
            "program": program_name,
            "ouac_code": cell(row, "OUAC Program Code"),
            "supplemental_application": supplemental,
            "prereq_raw": prereq_raw,
            "prereq_groups": json.dumps(groups),
            "prereq_unparsed": json.dumps(unparsed),
            "min_req_raw": min_req_raw,
            "min_req_overall": minimums["min_req_overall"],
            "min_req_all_prereqs": minimums["min_req_all_prereqs"],
            "min_req_courses": json.dumps(minimums["min_req_courses"]),
            "min_req_parsed": minimums["min_req_parsed"],
            "avg_gpa_raw": avg_gpa_raw,
            "avg_gpa_low": averages["avg_gpa_low"],
            "avg_gpa_high": averages["avg_gpa_high"],
            "avg_gpa_coop_low": averages["avg_gpa_coop_low"],
            "avg_gpa_coop_high": averages["avg_gpa_coop_high"],
            "avg_gpa_has_note": averages["avg_gpa_has_note"],
        })

    programs = pd.DataFrame.from_records(records)
    programs["supplemental_application"] = programs["supplemental_application"].astype("boolean")
    return programs


def build_universities(body: pd.DataFrame, programs: pd.DataFrame, issues: dict) -> pd.DataFrame:
    """One row per university.

    The accessibility columns are repeated on every program row, but manual
    transcription left some schools with several wordings in the same column.  We
    take the most common wording and record every conflict in the quality report
    instead of silently averaging them away -- some of the minority variants hold
    the *correct* content (Guelph's disability-types cell is one such case).
    """
    text = body.map(norm_ws)
    text = text.assign(university=text["University Name"].ffill())

    records = []
    for name, group in text.groupby("university", sort=False):
        record = {"university": name, "n_programs": int(len(group))}
        for column in UNIVERSITY_TEXT_COLUMNS:
            values = [v for v in group[column].tolist() if isinstance(v, str) and v]
            if not values:
                record[UNIVERSITY_COLUMN_NAMES[column]] = None
                continue
            if column in UNIVERSITY_BOOLEAN_COLUMNS:
                flags = {v.strip().lower() in {"1", "1.0", "y", "yes", "true"} for v in values}
                if len(flags) > 1:
                    issues["notes"].append(
                        f"{name}: `{column}` disagrees across its program rows; kept the majority"
                    )
                record[UNIVERSITY_COLUMN_NAMES[column]] = (
                    Counter(v.strip().lower() in {"1", "1.0", "y", "yes", "true"}
                            for v in values).most_common(1)[0][0]
                )
                continue
            counts = Counter(norm_key(v) for v in values)
            winner, winner_n = counts.most_common(1)[0]
            # Representative: the longest raw spelling of the winning variant.
            record[UNIVERSITY_COLUMN_NAMES[column]] = max(
                (v for v in values if norm_key(v) == winner), key=len
            )
            if len(counts) > 1:
                issues["text_conflicts"].append({
                    "university": name,
                    "column": column,
                    "chosen_rows": winner_n,
                    "variants": [
                        {"rows": n, "text": max((v for v in values if norm_key(v) == k), key=len)}
                        for k, n in counts.most_common()
                    ],
                })
        records.append(record)

    universities = pd.DataFrame.from_records(records)
    observed = programs.groupby("university").size()
    mismatch = [
        row.university for row in universities.itertuples()
        if int(observed.get(row.university, 0)) != row.n_programs
    ]
    if mismatch:
        raise ValueError(f"program counts disagree between tables for: {mismatch}")
    return universities


def build_vocabulary(student: pd.DataFrame, user: pd.DataFrame, issues: dict) -> dict:
    """Extract the controlled vocabularies from the two enumeration sheets.

    Neither sheet holds observations.  ``student info`` is a two-level taxonomy laid
    out as a grid (category across, sub-values down) and ``user input`` is a set of
    independent option lists -- these are the dropdown contents and the label space
    for downstream extraction, so they are emitted as JSON rather than as CSV tables
    that would imply they are records.
    """
    def column_values(frame: pd.DataFrame, index: int) -> list[str]:
        return [v for v in (norm_ws(x) for x in frame.iloc[:, index]) if v]

    def taxonomy(frame: pd.DataFrame, columns: range) -> dict:
        """First value in a column is the category; the values below it are its
        sub-values, split into runs by an optional ``Types`` / ``Symptoms`` /
        ``Severity`` label.  Some columns (Eating Disorders, Neurological) list
        their subtypes with no label at all, so an unlabelled run is read as
        ``types`` rather than dropped."""
        labels = {"Types", "Symptoms", "Severity"}
        out: dict[str, dict] = {}
        for index in columns:
            values = column_values(frame, index)
            if not values:
                continue
            category, rest = values[0], values[1:]
            entry: dict[str, list[str]] = {}
            current = "types"
            for value in rest:
                if value in labels:
                    current = value.lower()
                else:
                    entry.setdefault(current, []).append(value)
            out[category] = {k: v for k, v in entry.items() if v}
        return out

    mental = taxonomy(student, range(1, 6))
    physical = taxonomy(student, range(7, 10))

    # "mid" is a transcription slip for "mild" in the severity scale.
    for taxo in (mental, physical):
        for category, entry in taxo.items():
            if "severity" in entry and "mid" in entry["severity"]:
                entry["severity"] = ["mild" if s == "mid" else s for s in entry["severity"]]
                issues["notes"].append(
                    f"severity value 'mid' under {category} read as 'mild'"
                )

    course_names = column_values(student, 11)
    course_codes = column_values(student, 12)
    if len(course_names) != len(course_codes):
        issues["notes"].append(
            f"course catalogue: {len(course_names)} names vs {len(course_codes)} codes; "
            "pairing truncated to the shorter list"
        )
    courses = [
        {"name": n, "codes": [c.strip() for c in code.split("/")]}
        for n, code in zip(course_names, course_codes)
    ]

    grades = [
        {"letter": letter, "percent_low": float(rng.split("-")[0]), "percent_high": float(rng.split("-")[1])}
        for letter, rng in zip(column_values(user, 1), column_values(user, 2))
    ]
    # user input column 3 is a 4.0-scale column, but it maps A->2.0 and B+->3.0.
    issues["notes"].append(
        "user input: the 4.0-scale GPA column is inconsistent (A=2.0, B+=3.0); "
        "dropped in favour of the letter/percent scale, which is self-consistent"
    )

    return {
        "mental_health": mental,
        "physical_health": physical,
        "severity": ["mild", "moderate", "severe"],
        "courses": courses,
        "grade_scale": grades,
        "extracurriculars": column_values(user, 12),
        "admission_type": column_values(user, 13),
    }


# --------------------------------------------------------------------------- #
# validation & reporting
# --------------------------------------------------------------------------- #

def validate(programs: pd.DataFrame, universities: pd.DataFrame) -> None:
    """Structural invariants.  These raise -- they mean the load went wrong."""
    checks = [
        (len(universities) == EXPECTED_UNIVERSITIES,
         f"expected {EXPECTED_UNIVERSITIES} universities, got {len(universities)}"),
        (len(programs) == EXPECTED_PROGRAMS,
         f"expected {EXPECTED_PROGRAMS} programs, got {len(programs)}"),
        (programs["university"].notna().all(), "some programs have no university"),
        (programs["program"].notna().all(), "some programs have no name"),
        (programs["program_id"].is_unique, "program_id is not unique"),
        (universities["university"].is_unique, "university names are not unique"),
        (int(universities["n_programs"].sum()) == len(programs),
         "university program counts do not sum to the program table"),
    ]

    # Cross-table agreement.  This is the check that catches the failure this
    # pipeline exists to prevent: an imputation that collapses every program onto
    # one university still yields 28 universities and 1,690 rows, so only comparing
    # the two tables against each other detects it.
    program_names = set(programs["university"])
    university_names = set(universities["university"])
    checks.append((program_names == university_names,
                   "universities named in programs do not match the university table: "
                   f"only in programs={sorted(program_names - university_names)[:3]}, "
                   f"only in universities={sorted(university_names - program_names)[:3]}"))
    if program_names == university_names:
        observed = programs.groupby("university").size()
        expected = universities.set_index("university")["n_programs"]
        disagreeing = [u for u in university_names if int(observed[u]) != int(expected[u])]
        checks.append((not disagreeing,
                       f"per-university program counts disagree for: {sorted(disagreeing)[:5]}"))

    for column in ("avg_gpa_low", "avg_gpa_high", "min_req_overall", "min_req_all_prereqs"):
        series = programs[column].dropna()
        checks.append((series.between(0, 100).all(),
                       f"{column} has values outside 0-100: {sorted(set(series[~series.between(0, 100)]))[:5]}"))
    bad_range = programs.dropna(subset=["avg_gpa_low", "avg_gpa_high"])
    checks.append(((bad_range["avg_gpa_low"] <= bad_range["avg_gpa_high"]).all(),
                   "avg_gpa_low exceeds avg_gpa_high on some rows"))

    failures = [message for ok, message in checks if not ok]
    if failures:
        raise ValueError("validation failed:\n  - " + "\n  - ".join(failures))


def write_report(path: str, programs: pd.DataFrame, universities: pd.DataFrame,
                 vocabulary: dict, issues: dict, empty_columns: list[str]) -> None:
    lines: list[str] = ["# UNIfy data quality report", ""]
    lines += [
        "Generated by `preprocessing.py`. Nothing below has been imputed; these are",
        "values the parsers could not read, or places where the source disagrees with",
        "itself. They need a human decision.",
        "",
        "## Coverage", "",
        f"- universities: **{len(universities)}**",
        f"- programs: **{len(programs)}**",
        f"- programs with a parsed average GPA: "
        f"**{int(programs['avg_gpa_low'].notna().sum())} / {int(programs['avg_gpa_raw'].notna().sum())}** with a value present",
        f"- programs with parsed prerequisites: "
        f"**{int((programs['prereq_groups'] != '[]').sum())} / {int(programs['prereq_raw'].notna().sum())}** with a value present",
        f"- programs with a parsed minimum requirement: "
        f"**{int(programs['min_req_parsed'].sum())} / "
        f"{int(programs['min_req_raw'].notna().sum())}** with a value present",
        f"- courses in the catalogue: **{len(vocabulary['courses'])}**",
        "",
    ]

    if empty_columns:
        lines += ["## Columns that are entirely empty in the source", "",
                  "These exist as headers only. Any model that needs them requires new data collection.", ""]
        lines += [f"- `{c}`" for c in empty_columns] + [""]

    lines += ["## Unparsed values", ""]
    for key, title in [("avg_gpa_unparsed", "Average GPA"),
                       ("min_req_unparsed", "Minimum requirement"),
                       ("prereq_unparsed", "Prerequisite fragments")]:
        entries = issues[key]
        lines += [f"### {title} ({len(entries)} rows)", ""]
        if not entries:
            lines += ["None.", ""]
            continue
        seen: Counter = Counter()
        for uni, program, value in entries:
            seen[str(value)] += 1
        for value, count in seen.most_common(40):
            lines.append(f"- `{value}` — {count} row(s)")
        lines.append("")

    conflicts = issues["text_conflicts"]
    lines += ["## Conflicting university-level text", "",
              "The accessibility columns should be constant within a university. Where they",
              "are not, the most common wording was kept. **The majority wording is not",
              "always the correct one** — e.g. only one Guelph row records actual disability",
              "*types* in the disability-types column; the other 45 hold service descriptions.",
              "Resolving these 28 schools by hand is the highest-value manual pass on this dataset.",
              ""]
    if not conflicts:
        lines += ["None.", ""]
    else:
        lines += [f"{len(conflicts)} column(s) across "
                  f"{len({c['university'] for c in conflicts})} universities:", ""]
        for conflict in conflicts:
            lines.append(f"### {conflict['university']} — `{conflict['column']}`")
            for variant in conflict["variants"]:
                excerpt = re.sub(r"\s+", " ", variant["text"])[:220]
                lines.append(f"- **{variant['rows']} row(s)**: {excerpt}…")
            lines.append("")

    constant = [c for c in universities.columns
                if c not in {"university", "n_programs"} and universities[c].nunique(dropna=False) <= 1]
    if constant:
        lines += ["## Columns with no variance across universities", "",
                  "Identical for all 28 schools, so they cannot discriminate between them.",
                  "Useful as facts about Ontario; useless as recommender features.", ""]
        lines += [f"- `{c}`" for c in constant] + [""]

    if issues["notes"]:
        lines += ["## Notes", ""] + [f"- {n}" for n in issues["notes"]] + [""]

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(line for line in lines if line is not None))


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db", nargs="?", default="Unify.db", help="path to Unify.db")
    parser.add_argument("--out", default="data/clean", help="output directory")
    parser.add_argument("--write-db", action="store_true",
                        help="also write programs/universities tables back into the SQLite file")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[error] database not found: {args.db}", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)

    issues: dict[str, Any] = defaultdict(list)
    conn = sqlite3.connect(args.db)
    try:
        uni_body = read_sheet(conn, RAW_UNI)
        student_body = pd.read_sql_query(f'SELECT * FROM "{RAW_STUDENT}"', conn)
        user_body = pd.read_sql_query(f'SELECT * FROM "{RAW_USER}"', conn)

        empty_columns = [c for c in uni_body.columns if uni_body[c].map(norm_ws).isna().all()]

        print(f"[info] {RAW_UNI}: {uni_body.shape[0]} program rows")
        programs = build_programs(uni_body, issues)
        universities = build_universities(uni_body, programs, issues)
        vocabulary = build_vocabulary(student_body, user_body, issues)

        validate(programs, universities)
        print(f"[ok]   {len(universities)} universities, {len(programs)} programs — validation passed")

        for name, frame in [("programs", programs), ("universities", universities)]:
            frame.to_csv(os.path.join(args.out, f"{name}.csv"), index=False)
            frame.to_parquet(os.path.join(args.out, f"{name}.parquet"), index=False)
            print(f"[info] wrote {name}.csv / .parquet ({len(frame)} rows)")
            if args.write_db:
                frame.to_sql(name, conn, if_exists="replace", index=False)
                print(f"[info] wrote table {name} into {args.db}")

        with open(os.path.join(args.out, "vocabulary.json"), "w", encoding="utf-8") as handle:
            json.dump(vocabulary, handle, indent=2, ensure_ascii=False)
        print("[info] wrote vocabulary.json")

        write_report(os.path.join(args.out, "quality_report.md"),
                     programs, universities, vocabulary, issues, empty_columns)
        print("[info] wrote quality_report.md")

        stale = [t for t in ("clean_uni_info", "clean_student_info", "clean_user_input")
                 if conn.execute(
                     "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()]
        if stale:
            print(f"[warn] stale tables from the previous pipeline remain in {args.db}: "
                  f"{', '.join(stale)} — these hold the mislabelled data and should be dropped")
        if args.write_db:
            conn.commit()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
