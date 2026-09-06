"""Claude-backed university recommender for UNIfy, grounded in the project's own data.

Replaces the Gemini backend. The important difference is not the vendor.

The Gemini version asked a model to name five Canadian universities from memory. With a
dead key it returned UBC, McGill and Alberta -- none of them Ontario schools, none of
them in this dataset, all of them presented to the caller as a successful answer. Asking
any model to recall universities has that failure mode by construction.

Here the model is used only for the part that needs judgment, and never for the part that
needs facts:

  1. Claude maps a free-text student profile onto the 32 accommodation labels in
     `extraction/taxonomy.json`. This is a judgment task and the model is good at it.
  2. Ranking is deterministic arithmetic over `data/clean/accommodations_baseline.csv`
     -- the measured extraction results for the 28 real Ontario universities. The model
     does not choose the schools and cannot invent one.
  3. Every claim carries the evidence text the label was extracted from.

Labels are weighted by rarity, w = log(N / n_schools_with_label). The five near-universal
provisions (extended time, assistive technology, 24/7 crisis line, OSAP/BSWD, accessible
digital formats) are held by nearly every school, so their weight is at or near zero and
they cannot drive a ranking. That is a direct consequence of the benchmark finding: a
recommender that ranks on those is ranking on noise.

    python claude_recommender.py          # smoke test
"""

import json
import math
import os
from typing import Dict, List, Optional

import pandas as pd

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; the env may be populated some other way
    pass

DEFAULT_MODEL = "claude-sonnet-5"
DATA_DIR = "data/clean"
TAXONOMY = "extraction/taxonomy.json"

# Which extractor's output grounds the ranking.
#
# The default stays the keyword baseline. It is the system whose quality is measured
# against a gold set on neutral terms -- every other extractor here is scored on a gold
# set stratified by *this* one's predictions, and the learned ones are additionally
# trained on its output. Until a batch stratified by the challenger's own predictions
# is judged, switching the default would silently change what every rating the API
# returns actually means.
#
# Set UNIFY_EXTRACTOR=embedding|classifier|hybrid to serve a different matrix. Nothing
# downstream changes: the ranking arithmetic, the rarity weights and the evidence
# quotes all read the same two files whatever produced them.
EXTRACTOR = os.environ.get("UNIFY_EXTRACTOR", "baseline")

# name and measured quality, reported in the API's `grounding` block so a caller can
# tell which system's numbers they are looking at.
EXTRACTORS = {
    "baseline": ("keyword baseline", "extraction/baseline.py"),
    "embedding": ("MiniLM embedding extractor", "extraction/embedding.py"),
    "multilabel": ("fine-tuned multi-label DistilBERT", "extraction/classifier.py --model-dir ..."),
    "classifier": ("fine-tuned cross-encoder", "extraction/classifier.py --model-dir ..."),
    "hybrid": ("embedding retrieval + cross-encoder rerank", "extraction/hybrid.py --model-dir ..."),
}

# Scores are derived from measured label coverage, never invented. See rating_basis
# on each recommendation for what the number actually counts.
RATING_GROUPS = {
    "accessibility_rating": {"campus", "materials", "technology", "instruction"},
    "disability_support_rating": {"process", "wellbeing", "financial", "assessment"},
}


class GroundingUnavailable(RuntimeError):
    """The extraction outputs are missing, so nothing can be grounded."""


def _load_labels() -> List[Dict]:
    with open(TAXONOMY) as handle:
        return json.load(handle)["labels"]


def _extractor_name() -> str:
    if EXTRACTOR not in EXTRACTORS:
        raise GroundingUnavailable(
            f"UNIFY_EXTRACTOR={EXTRACTOR!r} is not one of {sorted(EXTRACTORS)}"
        )
    return EXTRACTOR


def _load_matrix() -> pd.DataFrame:
    name = _extractor_name()
    path = os.path.join(DATA_DIR, f"accommodations_{name}.csv")
    if not os.path.exists(path):
        raise GroundingUnavailable(
            f"{path} not found. Run: python {EXTRACTORS[name][1]}"
        )
    return pd.read_csv(path)


def _load_evidence() -> Dict[tuple, List[str]]:
    """(university, label) -> the source sentences the label was extracted from."""
    path = os.path.join(DATA_DIR, f"accommodations_{_extractor_name()}.jsonl")
    evidence: Dict[tuple, List[str]] = {}
    if not os.path.exists(path):
        return evidence
    with open(path) as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("value") and record.get("evidence"):
                seen, unique = set(), []
                for text in record["evidence"]:
                    if text not in seen:
                        seen.add(text)
                        unique.append(text)
                evidence[(record["university"], record["label"])] = unique[:3]
    return evidence


def _extractor_quality() -> str:
    """The measured quality of whichever extractor is grounding this response.

    Read from extraction/results_ml.json when it exists, so the string the API reports
    cannot drift away from the last evaluation run. Falls back to the keyword
    baseline's published figure, which is the only one recorded in RESULTS.md.
    """
    name = _extractor_name()
    path = os.path.join("extraction", "results_ml.json")
    if os.path.exists(path):
        try:
            with open(path) as handle:
                macro = json.load(handle)[name]["macro"]
            return (f"precision {macro['precision']:.2f} / recall {macro['recall']:.2f} "
                    f"/ F1 {macro['f1']:.2f}, macro-averaged over the human-judged cells")
        except (KeyError, TypeError, ValueError):
            pass
    if name == "baseline":
        return "precision 0.96 / recall 0.87 / F1 0.89 on 165 human-judged cells"
    return "not measured; run python extraction/evaluate_ml.py --json-out extraction/results_ml.json"


class ClaudeRecommender:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        # Set whenever the model did not produce the needs mapping, so the caller can
        # report the real source instead of claiming the model answered.
        self.used_fallback = False
        self.model = model

        # CLAUDE_API_KEY is what this project's .env uses; ANTHROPIC_API_KEY is the
        # SDK's own convention and is accepted so standard tooling works unchanged.
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

        self.labels = _load_labels()
        self.by_id = {label["id"]: label for label in self.labels}
        self.matrix = _load_matrix()
        self.evidence = _load_evidence()

        # Rarity weights. A label held by all 28 schools scores log(1) = 0 and cannot
        # affect the ranking; a label held by 6 scores log(28/6) = 1.54.
        n = len(self.matrix)
        self.weights = {}
        for label_id in self.by_id:
            if label_id in self.matrix.columns:
                held = int(self.matrix[label_id].sum())
                self.weights[label_id] = math.log(n / held) if held else math.log(n)

        self.client = None
        if not self.api_key:
            print("Warning: no CLAUDE_API_KEY set; falling back to rule-based needs mapping.")
            return
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as exc:  # noqa: BLE001 - any SDK/import failure is non-fatal
            print(f"Could not initialise the Anthropic client: {exc}")

    # -- step 1: profile -> needed accommodation labels ---------------------------

    def needed_accommodations(self, student_profile: Dict) -> List[str]:
        """Map a student profile onto taxonomy label ids."""
        if self.client is None:
            return self._rule_based_needs(student_profile)
        try:
            ids = self._claude_needs(student_profile)
            if ids:
                return ids
            print("Claude returned no usable labels; using the rule-based mapping.")
        except Exception as exc:  # noqa: BLE001 - network/API errors are non-fatal
            print(f"Claude needs mapping failed: {exc}")
        return self._rule_based_needs(student_profile)

    def _claude_needs(self, student_profile: Dict) -> List[str]:
        catalogue = "\n".join(
            f"- {label['id']}: {label['name']} — "
            f"{label.get('definition_revised') or label.get('definition', '')}"
            for label in self.labels
        )
        prompt = f"""You are an expert in post-secondary disability accommodations.

Below is a fixed catalogue of accommodation types. Select the ones this student is likely
to need. Choose only ids from the catalogue.

Catalogue:
{catalogue}

Student profile:
- Mental health: {student_profile.get('mental_health', 'None')}
- Physical health: {student_profile.get('physical_health', 'None')}
- Academic focus: {student_profile.get('courses', 'General')}
- GPA: {student_profile.get('gpa', 'unknown')}
- Reported severity: {student_profile.get('severity', 'moderate')}

Select between 3 and 8 ids. Prefer accommodations that follow specifically from this
student's stated conditions over ones that almost every student could claim. Record your
selection with the select_accommodations tool."""

        # A tool schema rather than free-text JSON: the ids are constrained by an enum,
        # so the model cannot return a label that does not exist in the taxonomy.
        tool = {
            "name": "select_accommodations",
            "description": "Record the accommodations this student is likely to need.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "accommodation_ids": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(self.by_id)},
                        "minItems": 3,
                        "maxItems": 8,
                    }
                },
                "required": ["accommodation_ids"],
            },
        }
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=[tool],
            tool_choice={"type": "tool", "name": "select_accommodations"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                ids = block.input.get("accommodation_ids", [])
                # Validate anyway: the enum is a constraint, not a guarantee.
                return [i for i in ids if i in self.by_id][:8]
        return []

    def _rule_based_needs(self, student_profile: Dict) -> List[str]:
        """Deterministic mapping used when Claude is unavailable.

        Still grounded: these are real taxonomy ids scored against real data. It is a
        blunter mapping than the model's, not a fabricated one.
        """
        self.used_fallback = True
        mental = str(student_profile.get("mental_health", "None")).lower()
        physical = str(student_profile.get("physical_health", "None")).lower()
        severity = str(student_profile.get("severity", "moderate")).lower()

        needs = ["exam_extended_time", "personalized_plan"]
        if mental not in ("none", "nan", ""):
            needs += ["counselling_individual", "exam_private_room", "deadline_extension"]
        if any(word in mental for word in ("adhd", "attention", "learning")):
            needs += ["note_taking", "lecture_recording"]
        if "hearing" in physical or "deaf" in physical:
            needs += ["asl_interpretation", "realtime_captioning"]
        if any(word in physical for word in ("vision", "blind", "sight")):
            needs += ["format_braille", "screen_reader", "format_large_print"]
        if any(word in physical for word in ("mobility", "wheelchair", "physical")):
            needs += ["accessible_buildings", "accessible_parking_transit", "accessible_housing"]
        if severity == "severe":
            needs += ["reduced_course_load", "interim_without_documentation"]

        deduped = list(dict.fromkeys(needs))
        return [i for i in deduped if i in self.by_id][:8]

    # -- step 2: rank the 28 real schools -----------------------------------------

    def rank(self, needed: List[str], limit: int = 5) -> List[Dict]:
        """The best `limit` schools. Thin wrapper over score_all."""
        return self.score_all(needed)[:limit]

    def score_all(self, needed: List[str]) -> List[Dict]:
        """Every school in the dataset, scored and sorted best-first.

        Kept separate from rank() so a caller can look up a school the student
        named even when it falls outside the top few.
        """
        scored = []
        total_weight = sum(self.weights.get(i, 0.0) for i in needed)

        for _, row in self.matrix.iterrows():
            university = row["university"]
            matched = [i for i in needed if i in row.index and row[i] == 1]
            missing = [i for i in needed if i in row.index and row[i] != 1]

            if total_weight > 0:
                covered = sum(self.weights.get(i, 0.0) for i in matched)
                score = covered / total_weight
            else:
                # Every needed label is near-universal, so rarity cannot separate the
                # schools. Fall back to plain coverage and say so in rating_basis.
                score = len(matched) / len(needed) if needed else 0.0

            scored.append(
                {
                    "name": university,
                    "score": round(score * 5, 2),
                    "location": "Ontario",
                    "matched_accommodations": [self.by_id[i]["name"] for i in matched],
                    "missing_accommodations": [self.by_id[i]["name"] for i in missing],
                    "available_accommodations": [
                        self.by_id[i]["name"]
                        for i in self.by_id
                        if i in row.index and row[i] == 1
                    ],
                    "evidence": [
                        {"accommodation": self.by_id[i]["name"], "quote": quote}
                        for i in matched
                        for quote in self.evidence.get((university, i), [])[:1]
                    ],
                    "reason": self._reason(university, matched, missing),
                    "rating_basis": (
                        "Rarity-weighted share of this student's needed accommodations "
                        "that the school's published text evidences"
                        if total_weight > 0
                        else "Unweighted share of needed accommodations evidenced "
                        "(all needed labels are near-universal, so rarity cannot rank)"
                    ),
                    **self._group_ratings(row),
                }
            )

        scored.sort(key=lambda item: (-item["score"], item["name"]))
        return scored

    def _group_ratings(self, row: pd.Series) -> Dict[str, float]:
        """Coverage of measured provisions by taxonomy group, scaled to 0-5.

        These replace the invented `accessibility_rating` / `disability_support_rating`
        of the Gemini version. They are counts of evidenced provisions, not quality
        judgments, and no one has rated these schools.
        """
        ratings = {}
        for field, groups in RATING_GROUPS.items():
            ids = [
                label["id"]
                for label in self.labels
                if label["group"] in groups and label["id"] in row.index
            ]
            held = sum(1 for i in ids if row[i] == 1)
            ratings[field] = round((held / len(ids)) * 5, 1) if ids else 0.0
        return ratings

    def _reason(self, university: str, matched: List[str], missing: List[str]) -> str:
        if not matched:
            return (
                f"{university}'s published accessibility text evidences none of the "
                "accommodations identified for this student."
            )
        # Name the rarest matches first: those are the ones that actually distinguish.
        ranked = sorted(matched, key=lambda i: -self.weights.get(i, 0.0))
        names = [self.by_id[i]["name"] for i in ranked[:3]]
        text = f"Evidences {len(matched)} of {len(matched) + len(missing)} needed accommodations, including {', '.join(names)}"
        if missing:
            gap = [self.by_id[i]["name"] for i in missing[:2]]
            text += f". No published evidence found for {', '.join(gap)}"
        return text + "."


def _normalise_name(name: str) -> str:
    """Fold a university name for comparison.

    The dataset uses a curly apostrophe in "Université de l’Ontario français" and
    "Queen’s University"; a client that sends a straight one should still match.
    """
    if not name:
        return ""
    folded = str(name).strip().casefold()
    for curly, straight in (("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-")):
        folded = folded.replace(curly, straight)
    return " ".join(folded.split())


def get_claude_recommendations(student_profile: Dict, api_key: Optional[str] = None) -> Dict:
    """Recommendations for a student profile, grounded in the extracted dataset."""
    try:
        recommender = ClaudeRecommender(api_key)
    except GroundingUnavailable as exc:
        return {
            "success": False,
            "error": str(exc),
            "source": "unavailable",
            "needed_accommodations": [],
            "recommendations": [],
        }

    needed = recommender.needed_accommodations(student_profile)
    all_scored = recommender.score_all(needed)
    universities = all_scored[:5]

    # The school the student actually put first. It is scored against the same
    # 28-school ranking, so it carries a real position even when it misses the
    # top five -- which is the common case, and the whole point of returning it.
    preferred_match = None
    wanted = _normalise_name(student_profile.get("preferred_university", ""))
    if wanted:
        for position, entry in enumerate(all_scored, start=1):
            if _normalise_name(entry["name"]) == wanted:
                preferred_match = {
                    **entry,
                    "rank": position,
                    "total_universities": len(all_scored),
                    "in_top_5": position <= 5,
                }
                break

    return {
        "success": True,
        # claude_grounded  = Claude mapped the needs, data ranked the schools
        # rule_based_grounded = Claude unavailable, rules mapped the needs, data ranked
        # Neither invents a university: both rank only the 28 schools in the dataset.
        "source": "rule_based_grounded" if recommender.used_fallback else "claude_grounded",
        "model": None if recommender.used_fallback else recommender.model,
        "needed_accommodations": [recommender.by_id[i]["name"] for i in needed],
        "needed_accommodation_ids": needed,
        "recommendations": universities,
        # None when the student named no preference, or named something outside
        # the 28 schools in the dataset.
        "preferred_match": preferred_match,
        "grounding": {
            "universities_considered": len(recommender.matrix),
            "extractor": EXTRACTORS[EXTRACTOR][0],
            "extractor_quality": _extractor_quality(),
            "caveat": "Labels come from an automatic extractor over compiled prose, not from the universities. Verify with the school before relying on any of it.",
        },
    }


if __name__ == "__main__":
    profile = {
        "mental_health": "ADHD",
        "physical_health": "Hearing",
        "courses": "Computer Science",
        "gpa": 3.8,
        "severity": "moderate",
    }
    result = get_claude_recommendations(profile)
    print(f"source: {result['source']}  model: {result.get('model')}")
    print(f"needs:  {result['needed_accommodations']}\n")
    for i, uni in enumerate(result["recommendations"], 1):
        print(f"{i}. {uni['name']}  {uni['score']}/5")
        print(f"   {uni['reason']}")
        for item in uni["evidence"][:2]:
            print(f"   cite [{item['accommodation']}]: {item['quote'][:80]}")
        print()
