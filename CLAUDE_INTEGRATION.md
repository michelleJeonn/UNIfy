# Claude backend integration

`claude_recommender.py` replaces the previous Gemini backend. The vendor change is the
least interesting part of it.

## Why the design changed, not just the model

The Gemini version asked a model to name five Canadian universities from memory. When its
key stopped working it returned UBC, McGill, and the University of Alberta — none of them
Ontario schools, none of them in this dataset — with HTTP 200, `success: true`, and
`source: "gemini_ai"`. Nothing in the response indicated that the answer was invented.

Any model asked to recall universities can do that. So the model is no longer asked.

## How it works

| Step | Who does it | Why |
|---|---|---|
| 1. Profile → needed accommodations | **Claude** | Genuine judgment: mapping "ADHD, moderate" onto accommodation types. Models are good at this. |
| 2. Rank the universities | **Deterministic arithmetic** | Facts. Uses the measured extraction results for the 28 real Ontario universities. |
| 3. Justify each recommendation | **The data** | Each claim quotes the source text the label was extracted from. |

Step 1 is constrained by a tool schema whose `enum` is the 32 label ids in
`extraction/taxonomy.json`, and the returned ids are validated against the taxonomy
again afterwards. The model cannot return an accommodation that does not exist.

Step 2 never consults the model, so **the recommender cannot name a university that is
not in `data/clean/accommodations_baseline.csv`.** That is a structural guarantee, not a
prompt instruction. `test_integration.py` asserts it.

## Rarity weighting

Labels are weighted `w = log(N / n_schools_with_label)`.

A label held by all 28 schools gets `log(1) = 0` and cannot move the ranking. This is the
benchmark finding applied directly: extended time, assistive technology, the 24/7 crisis
line, OSAP/BSWD and accessible digital formats are held by nearly every Ontario school, so
a recommender that ranks on them ranks on noise. Rare provisions — ASL (13/28), real-time
captioning (15/28), accessible housing (7/28), reduced course load (6/28) — carry the
weight, because they are what actually distinguishes one school from another.

## Configuration

```bash
CLAUDE_API_KEY=sk-ant-...     # what this project's .env uses
# ANTHROPIC_API_KEY is also accepted, so standard tooling works unchanged
```

Model: `claude-sonnet-5` by default, override with `ClaudeRecommender(model=...)`.

**Without a key the recommender still works.** It falls back to a rule-based mapping from
profile to accommodation labels, and ranks with the same data and the same arithmetic. The
fallback is blunter, not fabricated — it still names only real Ontario schools with real
citations. The old hard-coded UBC/McGill/Alberta list is gone.

## Response format

```python
{
    'success': True,
    'source': 'claude_grounded' | 'rule_based_grounded' | 'unavailable',
    'model': 'claude-sonnet-5',      # None when the fallback was used
    'needed_accommodations': ['Extended time on exams', 'Screen readers', ...],
    'needed_accommodation_ids': ['exam_extended_time', 'screen_reader', ...],
    'recommendations': [
        {
            'name': 'University of Guelph',
            'score': 3.72,
            'accessibility_rating': 3.6,
            'disability_support_rating': 4.4,
            'rating_basis': 'Rarity-weighted share of this student's needed '
                            'accommodations that the school's published text evidences',
            'matched_accommodations': [...],
            'missing_accommodations': [...],
            'evidence': [{'accommodation': '...', 'quote': '...'}],
            'location': 'Ontario',
            'reason': 'Evidences 6 of 7 needed accommodations, including ...'
        }
    ],
    'grounding': {
        'universities_considered': 28,
        'extractor': 'keyword baseline',
        'extractor_quality': 'precision 0.96 / recall 0.87 / F1 0.89 on 165 human-judged cells',
        'caveat': '...'
    }
}
```

### About the two ratings

`accessibility_rating` and `disability_support_rating` are **coverage measures**: the
fraction of measured provisions in the relevant taxonomy groups that the school's
published text evidences, scaled to 0–5. They are not quality judgments. No one has rated
these schools, and these numbers must not be presented as though someone had. The
`rating_basis` field says what the number counts; show it wherever you show the rating.

The Gemini version returned invented ratings like `4.7` with no basis at all. These at
least count something real, but "counts something real" is a low bar, and a coverage
fraction is not a measure of how well a school actually serves students.

## What this still does not do

The rankings rest on the keyword extractor's output (P 0.96 / R 0.87 / F1 0.89), which in
turn rests on prose that a human compiled and paraphrased — not on what the universities
published, and not on what they actually provide. A missing label means *no evidence was
found in the compiled text*, which is not the same as the school not offering it. The
`grounding.caveat` field says this in every response; surface it in the UI.

## Endpoints

- `POST /api/recommendations` — main endpoint
- `POST /api/claude` — identical, direct
- `POST /api/gemini` — deprecated alias, kept so existing frontend builds keep working
- `GET /api/test` — smoke test with a fixed profile
