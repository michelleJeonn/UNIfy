# Accommodation extraction (Step 2)

Turns the accessibility prose in the university sheet into a checkable
`university × accommodation` matrix, and measures how well that can be done
automatically.

## Pipeline

```
python extraction/corpus.py      # evidence.jsonl      2,265 citable segments
python extraction/baseline.py    # 28 × 32 matrix + citations
python extraction/make_gold.py   # 156-cell blind annotation template
#   ... annotate: fill `gold` with 1/0, save as data/gold/gold.csv ...
python extraction/evaluate.py    # stratified precision / recall / F1
```

`evaluate.py --predictions <other.jsonl>` scores any other extractor against the
same gold set, which is the point: the keyword baseline exists to be beaten, and
"beaten" has to mean a number.

Top-up batches, for gaps and for re-judging after a definition change:

```
# fresh cells only, skipping anything already judged
python extraction/make_gold.py --exclude data/gold/gold.csv --labels peer_support --out batch.csv

# the same cells again, blind, with the new definition
python extraction/make_gold.py --rejudge data/gold/gold.csv --labels accessible_housing --out batch.csv

# score across several gold files; later ones supersede earlier verdicts
python extraction/evaluate.py --gold data/gold/gold.csv --gold data/gold/gold_supplement.csv
```

## Design decisions

**Union, not mode.** `preprocessing.py` picks one canonical wording per
(university, column) for display. Extraction uses *every* distinct wording instead,
so the 14 transcription conflicts become extra evidence rather than a blocking
decision. Resolving them still matters for display; it does not gate this work.

**Everything cites.** Each label carries the `segment_id`s that produced it. A claim
about a school's accommodations that a student cannot trace to source text is not
worth making.

**Definitions must be decidable.** A definition that enumerates specifics under a
general label name is not: annotation of `accessible_buildings` v1 judged
"accessible buildings and classrooms" negative at one school and
"Accessible entrances, buildings, and classrooms" positive at another. Each
definition now states what counts *and* what does not. Revised definitions carry a
`definition_revised` field, because changing one invalidates every judgment made
under the old wording.

**Blind annotation.** The template shows no prediction, no stratum, no hit count, and
ranks excerpts identically regardless of how the extractor voted. Otherwise
agreement partly measures anchoring. Residual leak: 99% of predicted-positive rows
have an excerpt versus 75% of predicted-negative rows, so the tell is weakened, not
eliminated.

**Stratified sampling, reweighted metrics.** Sampling is by predicted class, so
recall must be reweighted by stratum size — the naive pooled figure overstates it by
5–8× here. `evaluate.py` documents and implements the correction; it is verified
against a hand-computed case.

## What the corpus already says

Five labels are true at (nearly) all 28 schools — extended time, assistive
technology, 24/7 crisis line, OSAP/BSWD, accessible digital formats — and the
source's own `24/7 support` column is 1 for every school. **These cannot
discriminate between universities.** Any recommender ranking on them ranks on noise.
The signal is in the rarer provisions (ASL 13/28, real-time captioning 15/28,
accessible housing 7/28, reduced course load 6/28) and in process differences
(interim accommodation without documentation 10/28).

`peer_support` is hand-coded in the source (25 yes / 3 no), and an earlier version of
this pipeline trusted that column as gold. **Annotation falsified that.** Of the sampled
cells judged, the column marks "yes" wherever a school has anything peer-adjacent —
"Peer note-taking" is note-taking, "Counsellor Assisted E-Support" is counselling — and
the judged cells came back overwhelmingly negative. True prevalence is far below 25/28.
Hand-coded columns are now recorded as `hand_coded_column_value` and never used as
predictions or as labels. This is the one design decision here that was overturned by
data rather than by argument.

## Caveat on generalisation

The source prose was paraphrased by whoever compiled the spreadsheet, so its phrasing
is far more uniform than real university web copy. Accuracy measured here is an
**upper bound** on what the same method would achieve scraping live sites.
