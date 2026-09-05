# UNIfy

Accessibility and accommodation information for the **28 Ontario universities**, turned
into structured, citable data — plus a measured benchmark for how well that extraction
can be automated.

The project has two halves that are worth keeping separate:

1. **A dataset and benchmark** (`preprocessing.py`, `extraction/`) — reproducible,
   hand-labelled, and evaluated with stated uncertainty. This is the part with results.
2. **A recommendation API and React frontend** (`app.py`, `src/`) — backed by Claude
   for judgment and by the extracted dataset for facts. It is not a trained model and
   does not claim to be.

## Status

| Component | State |
|---|---|
| Preprocessing → `programs.csv`, `universities.csv` | Working, validated |
| Evidence corpus (2,265 citable segments) | Working |
| 32-label accommodation taxonomy | Working, 2 definitions revised after annotation |
| Keyword baseline extractor | Measured: **P 0.96 / R 0.87 / F1 0.89** |
| Embedding extractor (MiniLM-L6-v2) | Measured, **provisional** — does not beat the baseline |
| Gold set | 165 human-judged cells; 40-cell fairness batch outstanding |
| LLM extractor | Not started |
| Recommendation API | Working, Claude-backed and grounded in the extracted data |

There is no trained model in this repo. An earlier version contained a neural
"accommodation predictor", a "university recommender", and an HMM; all three were
removed because they did not do what they claimed — the network learned a hand-written
if-statement, the recommender was never fitted and returned identical scores for every
school, and the HMM decoded noise. The accuracy figures previously quoted in this file
(85–90%, MAE < 0.3) were not measured against anything and have been deleted.

## Data

The source is a compiled spreadsheet of Ontario university programs and accessibility
services. `preprocessing.py` parses it into two tables:

- **`data/clean/programs.csv`** — 1,690 programs × 20 columns. Admission averages parsed
  into bands and co-op/regular splits, prerequisites into `{n, options}` groups, with the
  raw text always retained alongside the parse.
- **`data/clean/universities.csv`** — 28 schools × 15 columns of accessibility services,
  support programs, and contact information.

Both are written as CSV and Parquet, with `vocabulary.json` and a `quality_report.md`.

```bash
python preprocessing.py
```

Two things this pipeline exists to prevent, both of which had already happened:

- **Mode-fill mislabelled all 1,690 programs as one university.** Merged spreadsheet
  cells were filled with the column mode rather than forward-filled in sheet order.
  Attribution is now `ffill`, and `validate()` cross-checks program-table university
  names against the university table so this class of bug fails loudly.
- **`pd.NA` is not `None`, and `bool(pd.NA)` raises.** Eighteen missing supplemental-
  application flags silently became `False`. All cell access now goes through a
  null-safe accessor.

## The extraction benchmark

See **`extraction/README.md`** for the pipeline and design decisions, and
**`extraction/RESULTS.md`** for full results and error analysis.

```bash
python extraction/corpus.py      # 2,265 citable evidence segments
python extraction/baseline.py    # 28 × 32 label matrix, every label cites its source
python extraction/make_gold.py   # blind annotation template
python extraction/evaluate.py    # stratified precision / recall / F1 with intervals
```

**Keyword baseline**, 28 labels, 165 human-judged cells:
P 0.96 / R 0.87 / F1 0.89.

**Embedding extractor** vs keyword, on the 23 labels both can be scored on:

| | precision | recall | F1 |
|---|---|---|---|
| keyword | **0.96** | 0.84 | **0.87** |
| embedding | 0.84 | **0.92** | 0.86 |

Recall improved as predicted; precision fell further. The failure mode is
**near-neighbour collapse** — the model matches the topic and then cannot resolve the
distinction that defines the label. `counselling_group` fires on "One-on-one counselling
services" at cosine 0.65. The taxonomy draws contrasts *within* families, and phrase-level
cosine similarity does not represent contrast.

This comparison is **provisional**. The gold set is stratified by the keyword baseline's
predictions, and a gold set stratified by one system's predictions cannot fairly score
another. `data/gold/gold_embedding_template.csv` (40 cells) is the outstanding top-up.

### Findings that constrain any recommender built on this data

- **Five labels are true at nearly every school** — extended time, assistive technology,
  24/7 crisis line, OSAP/BSWD, and accessible digital formats. They cannot discriminate
  between universities; ranking schools on them is ranking on noise. The first four are
  flagged `near_universal` in the taxonomy and excluded from scoring. The fifth,
  `format_accessible_digital`, is still scored — its gold sample drew no negatives, which
  is itself the evidence that it is near-universal.
- **The signal is in the rarer provisions**: ASL 13/28, real-time captioning 15/28,
  accessible housing 7/28, reduced course load 6/28, and in process differences such as
  interim accommodation without documentation (10/28).
- **The source's own hand-coded columns are not gold.** The `peer_support` column marks
  25/28 schools "yes"; annotation of the sampled cells found it counts peer note-taking
  and counselling as mentorship. Hand-coded columns are recorded alongside predictions
  and never used as labels.

### Caveat on generalisation

The source prose was paraphrased by whoever compiled the spreadsheet, so its phrasing is
far more uniform than real university web copy. Accuracy measured here is an **upper
bound** on what the same method would achieve scraping live sites.

### Do not tune on the gold set

`data/gold/gold.csv` is the test set. Keyword seeds must not be tuned against it, and the
extractor's author should not annotate their own test cells. Six `realtime_captioning`
cells in `gold_supplement2.csv` are model-proposed and marked
`annotator: model-proposed (UNCONFIRMED)`; headline numbers use human judgments only.

## Recommendation API

```bash
pip install -r requirements.txt
python app.py
```

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Health check |
| `/api/recommendations` | POST | Recommendations for a student profile |
| `/api/claude` | POST | Same, direct |
| `/api/gemini` | POST | Deprecated alias, kept for existing frontend builds |
| `/api/test` | GET | Smoke test with a fixed profile |

Set `CLAUDE_API_KEY` in `.env`. Without one the recommender still works — see below.

Request body:

```json
{
  "mental_health": "ADHD",
  "physical_health": "None",
  "courses": "Computer Science",
  "gpa": 3.8,
  "severity": "moderate"
}
```

**The model does not choose the universities.** Claude maps the student profile onto the
32 accommodation labels — a judgment task — and ranking is then deterministic arithmetic
over the measured extraction results for the 28 real Ontario universities, weighted by
label rarity so the near-universal provisions cannot drive the result. Every
recommendation quotes the source text each label was extracted from.

This is a structural fix, not a prompt instruction. The previous Gemini backend, with a
dead key, returned HTTP 200, `success: true`, `source: "gemini_ai"` and recommended UBC,
McGill and Alberta — none of them Ontario schools, none of them in this dataset. The
current backend cannot name a school that is not in
`data/clean/accommodations_baseline.csv`; `test_integration.py` asserts it.

Responses still carry **`source`**: `claude_grounded` when Claude mapped the needs,
`rule_based_grounded` when no key was available and rules did. Both rank real schools from
real data — the fallback is blunter, not fabricated.

`accessibility_rating` and `disability_support_rating` are coverage measures — the share
of measured provisions a school's text evidences — not quality judgments. Each
recommendation carries a `rating_basis` saying so. See `CLAUDE_INTEGRATION.md`.

## Frontend

```bash
npm install
npm run dev
```

React 18 + TypeScript + Vite + Tailwind. See `INTEGRATION_GUIDE.md` and `DEPLOYMENT.md`.

## Project structure

```
UNIfy/
├── preprocessing.py            # spreadsheet → validated tables
├── extraction/
│   ├── corpus.py               # evidence segments
│   ├── taxonomy.json           # 32 labels, 8 groups, decidable definitions
│   ├── baseline.py             # keyword extractor
│   ├── embedding.py            # MiniLM extractor
│   ├── make_gold.py            # blind annotation templates
│   ├── evaluate.py             # stratified metrics, Wilson + bootstrap CIs
│   ├── README.md               # pipeline and design decisions
│   └── RESULTS.md              # results and error analysis
├── data/
│   ├── clean/                  # programs, universities, evidence, predictions
│   └── gold/                   # hand-labelled gold set + per-school context
├── app.py                      # Flask API
├── claude_recommender.py       # grounded recommender: Claude for judgment, data for facts
├── src/                        # React frontend
└── requirements.txt
```

## Security

`.env` is **still tracked in git**. The old `GEMINI_API_KEY` is in the history of commits
`2c7e024` and `054c0fc`, and `.env` now holds a `CLAUDE_API_KEY` — so the next commit
would publish that one too.

```bash
git rm --cached .env       # stop tracking; the local file is kept
```

`.env` is now in `.gitignore`, which prevents re-adding it but does nothing about history.
The old Gemini key must still be revoked at https://aistudio.google.com/apikey — removing
a file from the working tree does not remove it from history, and anyone with a clone has
it.

## License

MIT.
