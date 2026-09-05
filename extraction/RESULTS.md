# Step 2 results — keyword baseline vs. hand-labelled gold

**165 cells judged** across two blind rounds (156 + a 22-cell supplement, 13 of which
superseded earlier verdicts), every cell with a written rationale.

| metric | macro average |
|---|---|
| precision | **0.96** |
| recall | **0.87** |
| F1 | **0.89** |

Over 28 labels with a defined F1. Per-label numbers and intervals: `results.txt`.

### Effect of the definition revisions, like-for-like

Two definitions were rewritten *after* seeing round-one results, which can only be
reported alongside the before/after on the same labels. Restricted to the 26 labels
scorable in both rounds:

| | precision | recall | F1 |
|---|---|---|---|
| v1 definitions | 0.94 | 0.87 | 0.88 |
| v2 definitions | 0.97 | 0.86 | 0.89 |
| delta | **+0.04** | **−0.02** | **+0.01** |

Recall *fell*: broadening `accessible_housing` exposed three genuine false negatives
in the negative stratum that v1 had scored as correct rejections. The revisions
reclassified cells in both directions rather than inflating the headline — net +0.01
F1. The reported 0.96/0.87/0.89 additionally includes `peer_support` and
`format_accessible_digital`, which round one could not score at all.

Per-label confidence intervals are wide (typically [0.44, 1.00] on precision with
n=3) and are **not** usable to rank labels against each other. The macro average is
the comparable number. This is a property of having 28 schools, not a fixable defect.

## What the errors are

**8 false positives.** Two are seed looseness — "workshop" firing on *"Academic
strategy and tech workshops"* for `counselling_group`. Two are definition drift:
`accessible_buildings` matched *"accessible buildings and classrooms"* but the
definition demands ramps/elevators/doors, so the definition is narrower than the
label name and needs tightening. Three were the `peer_support` column (below).

**12 false negatives, and they share one cause:** exact-phrase seeds cannot survive
intervening words or inflection.

| gold text | seed that should have fired |
|---|---|
| "private exam spaces", "Quiet, private…exam rooms" | `private room`, `quiet space` |
| "One-on-one appointments" | `one-on-one counselling` |
| "One-on-one accommodation planning" | `accommodation plan` |
| "Intake & Onboarding appointment" | `intake appointment` |
| "upload incomplete documentation" | `pending documentation` |

That is the case for a semantic extractor, stated in the baseline's own failures
rather than assumed up front. One FN — *"Orientation and peer support for new
students"* for `transition_program` — shares no vocabulary with any seed at all, and
would defeat embeddings too.

## The finding that changed the design

The source sheet hand-codes `peer_support` as **25 yes / 3 no**. All 6 annotated
cells came back negative, with reasons: *"Peer note-taking" is note-taking*,
*"Counsellor Assisted E-Support" is counselling*. Neither is a mentorship programme.
The column marks yes for anything peer-adjacent — 3 false positives, 0 true
positives on the sample.

The baseline had been using that column as authoritative for the label. It no longer
does: hand-coded columns are recorded as `hand_coded_column_value` and never used as
predictions. Two reasons — the column is wrong, and mixing it in meant the reported
score described two different systems at once.

**This generalises: "already labelled" fields in the source are not gold.** The other
hand-coded column, `24/7 support`, is `1` for all 28 schools and is equally
unverified.

## Definition defects found by the annotation

Two definitions were not decidable, and the evidence is that **the same annotator
labelled near-identical text both ways**:

| label | judged 1 | judged 0 |
|---|---|---|
| `accessible_buildings` | Waterloo — "Accessible entrances, buildings, and classrooms" | Glendon — "accessible buildings and classrooms" |
| `accessible_housing` | Waterloo — "Reserved seating and accessible housing" | Guelph — "Help with accessible housing" |

Both pairs contain the key phrase. v1 of `accessible_buildings` enumerated features
(ramps, elevators, doors) while the label name was general, so a summarising school
could be read either way; v1 of `accessible_housing` never said whether *help
obtaining* housing counts as provision. Both are now rewritten to state what counts
and what does not, and marked `definition_revised` in `taxonomy.json`.

`accessible_parking_transit` and `transition_program` were also clarified, but only to
record the rule the annotator already applied consistently to all six of their cells.
Those judgments stand.

**Both revised labels were re-judged blind on the same cells.** Outcome: one flip for
`accessible_buildings` (Glendon, "accessible buildings and classrooms" now counts) and
three for `accessible_housing` (Lakehead, Guelph, Guelph-Humber, under the
help-arranging clause). Ontario Tech's "navigation tools" stayed negative, correctly
caught by v2's explicit exclusion. `accessible_housing` precision went 0.33 → 1.00 and
recall 1.00 → 0.50.

## Known defects in this round

* **One gold label is probably wrong.** York (Keele) / `realtime_captioning` is
  marked 0, but the school's text reads *"Support: captioning services, FM systems,
  assistive audio devices"*. The annotator was shown *"Extra time and breaks for
  exams"* — my excerpt ranker weighted the generic token "time" equally with
  "captioning" and broke ties shortest-first. Fixed (IDF weighting, stemming,
  longest-first, dedup); the captioning line now ranks first. **Re-judge that one
  cell.** Only 3 of 156 cells were affected and the other 2 were judged correctly
  from the context files, so the macro figures move by at most ~0.01.
* **`peer_support` is now unscored.** Its 6 sampled cells all fall in the negative
  stratum of the corrected extractor, so precision is undefined. It needs 3 fresh
  positive-stratum cells.
* **`format_accessible_digital` was never sampled** — the baseline predicts positive
  for all 28 schools, so there is no negative stratum and no measurable recall.
  Precision alone is still measurable and is now sampled.

## Open question: a third ambiguous definition

`realtime_captioning` has the same defect, found in round two. Its definition is
"Live captioning or CART transcription", but its seeds fire on bare "captioning".
The operative rule in the gold set requires the qualifier — both positives read
"Real-time captioning (CART)" and "Captioning (real-time or human-transcribed)" —
while York (Keele)'s "Support: captioning services, FM systems, assistive audio
devices" was judged negative.

That judgment is consistent with the other five cells, so it is left standing and the
label currently scores 0.67 precision. But definition and seeds still disagree about
scope, and the choice is a product question, not a scoring one:

* **Broaden** to any captioning of spoken course content. Most schools do not write
  "real-time" even when they provide it, so the strict rule marks them negative against
  reality. Better for a Deaf/HoH student asking "does this school caption lectures".
  Costs 6 re-judgments — and would convert an FP to a TP, so it favours the extractor.
* **Keep strict** and narrow the seeds to require live/CART/real-time. Precision-safe,
  but under-reports schools that provide captioning without saying "real-time".

Not resolved unilaterally, because it changes what the label means.

## Resolved batch: `data/gold/gold_supplement.csv` (22 cells)

| cells | label | why |
|---|---|---|
| 6 | `accessible_buildings` | re-judge under definition v2 |
| 6 | `accessible_housing` | re-judge under definition v2 |
| 6 | `peer_support` | 0 positive-stratum cells after the hand-coded column was dropped |
| 3 | `format_accessible_digital` | never sampled; precision-only |
| 1 | `realtime_captioning` | York (Keele), judged on excerpts the ranker bug hid |

Scored with:

```
python extraction/evaluate.py --gold data/gold/gold.csv --gold data/gold/gold_supplement.csv
```

Later files supersede earlier verdicts for the same cell, so the re-judged labels
replace rather than double-count: 165 judged cells, 28 scorable labels.

New findings from the supplement:

* **`peer_support` true prevalence is far below the source column's 25/28.** Of 12
  judged cells only 3 are positive. Waterloo's "peer support services" reads as
  peer-assisted note-taking; UTSC's "Peer note-taking" likewise. The two clear
  positives name it outright ("peer mentoring", "peer support groups").
* **`format_accessible_digital` is now measurable on precision: 3/3.** Recall remains
  unmeasurable — the extractor predicts positive for all 28 schools, so there is no
  negative stratum to sample.

## Do not tune the seeds on this gold set

It is the test set. The error table above says what a better extractor must handle;
it is not a patch list for the keyword matcher. Improving the baseline against these
156 cells would make the 0.94 meaningless. A separate dev split is needed first.

## Caveat on generalisation

The source prose was paraphrased by whoever compiled the spreadsheet, so its phrasing
is far more uniform than real university web copy. **0.94/0.87 is an upper bound** on
what this method achieves scraping live sites.


---

# Round three — embedding extractor

`extraction/embedding.py`, sentence-transformers `all-MiniLM-L6-v2`, over the same
2,265 segments and scored on the same gold set.

**Threshold is not tuned on gold.** It is fixed by a rule that reads no labels: the
single global cosine cut-off at which this extractor emits the same total number of
positive cells as the keyword baseline (564 → threshold 0.5847). Both systems spend an
identical budget of positives, so the score answers "given the same number of calls,
whose are better placed?" Tuning a cut-off against the gold set would have been
straightforward and worthless — the keyword baseline never got to tune anything.

## Result, on the 23 labels both extractors can be scored on

| | precision | recall | F1 |
|---|---|---|---|
| keyword baseline | **0.96** | 0.84 | **0.87** |
| embedding (MiniLM-L6-v2) | 0.84 | **0.92** | 0.86 |

**The prediction was half right and the conclusion was wrong.** Recall improved by
+0.08, as the false-negative analysis predicted — `exam_private_room` 0.75 → 0.96,
`accessible_parking_transit` 0.26 → 1.00, `interim_without_documentation` 0.45 → 1.00.
But precision fell 0.96 → 0.84 and F1 is a wash. On this corpus, semantic matching is
not an improvement; it is a different trade.

## Why precision fell: near-neighbour collapse

18 false positives against the keyword baseline's 3. They are not random — the
extractor identifies the *topic* correctly and then cannot resolve the *distinction
that defines the label*:

| label | matched text | cos |
|---|---|---|
| `counselling_group` | "One-on-one counselling services" | 0.65 |
| `counselling_individual` | "Same-day counselling" | 0.75 |
| `counselling_same_day` | "Brief individual counselling" | 0.74 |
| `reduced_course_load` | "Course Load Requirements" (an admissions rule) | 0.67 |
| `lecture_recording` | "Captioned videos and lectures" | 0.66 |

`counselling_group` firing on "One-on-one" is the clearest case: the literal opposite,
at high similarity. This taxonomy draws fine distinctions *within* families —
individual vs group vs same-day counselling — and cosine similarity over short phrases
collapses exactly those. Contrast is what these labels are made of, and bag-of-
embedding similarity does not represent contrast.

That is a concrete, tested motivation for an LLM extractor: the open question is
whether a model that can reason about a contrast ("is this individual or group?")
recovers the recall gain without the precision loss.

## The comparison is not yet fully fair

The gold set was sampled stratified by the **keyword baseline's** predictions. Scoring
a different extractor on it is biased: the sample concentrates around the baseline's
decision boundary and under-covers cells where the embedding extractor newly fires.
Five labels (`confidentiality`, `format_audio`, `per_term_renewal`, `speech_to_text`,
`bursaries_scholarships`) have too few embedding-positive cells in the sample to
estimate precision at all, which is why the comparison runs over 23 labels rather
than 28.

`evaluate.py` already derives stratum *sizes* from whichever extractor it scores, so
the reweighting is right. The residual bias is in which cells were *sampled*, and no
arithmetic fixes that — it needs cells drawn from the new extractor's strata.

**Open batch: `data/gold/gold_embedding_template.csv` (40 cells, 22 labels.)** The
minimum that brings every label to >=3 judged cells in both of the embedding
extractor's strata; a full re-sample would have been 153. Until it is annotated, treat
0.84/0.92/0.86 as provisional.

**General lesson for the benchmark:** a gold set stratified by one system's predictions
cannot fairly score another. Comparing N extractors needs sampling from the union of
their decision boundaries, and each new extractor costs a top-up batch.
