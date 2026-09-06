# Learned extraction: results

Four systems, one gold set, identical arithmetic. Everything below is produced by
`extraction/evaluate_ml.py`; the stratified reweighting, Wilson intervals and
bootstrap come from `extraction/evaluate.py` unchanged.

## Headline

| system | macro P | macro R | macro F1 | micro P | micro R | micro F1 |
|---|---:|---:|---:|---:|---:|---:|
| **keyword baseline** | **0.98** | 0.87 | **0.90** | **0.98** | **0.88** | **0.93** |
| embedding (MiniLM, budget-matched) | 0.81 | 0.87 | 0.85 | 0.80 | 0.81 | 0.80 |
| multi-label DistilBERT | 0.81 | **0.90** | 0.81 | 0.78 | 0.73 | 0.75 |
| cross-encoder classifier | 0.89 | 0.86 | 0.84 | 0.91 | 0.83 | 0.87 |
| hybrid (retrieval → rerank) | 0.94 | 0.81 | 0.83 | 0.95 | 0.84 | 0.89 |

165 human-judged cells, 28 labels, 28 universities. Every system emits the same
number of positive cells (564) because thresholds are budget-matched, so these are
comparable on placement rather than on volume.

**The keyword baseline is still the best extractor here, and nothing learned beat
it.** That is the result, not a placeholder for a better one.

## Why the learned systems lose, and why that was the expected outcome

There are no segment-level human labels in this project. The 165 judged cells are
judgments about a `(university, label)` pair. So the classifier is trained on
**distant supervision from the keyword baseline** — its ceiling is the baseline, and
its floor is the baseline plus whatever the pretrained encoder adds or corrupts.
Matching the teacher is the good case. It did not match the teacher.

Three specific mechanisms, all visible in `evaluate_ml.py --detail hybrid --errors`:

**1. Probability saturation makes the global threshold a knife edge.** The
cross-encoder trains to near-zero loss on silver labels and its output collapses onto
the ends of the range: 63–66% of cells score above 0.99, and the maximum is 0.993.
Budget-matching then puts the global cut-off at 0.9888, where a handful of
thousandths separates a positive from a negative. Queen's University evidences
`exam_private_room` with "Extra time, scheduled breaks, private exam spaces" — an
unambiguous positive — and lands below the cut. The embedding extractor, whose scores
spread across 0.27–1.00, does not have this problem. **This is the largest single
cause of the gap and the first thing to fix.**

**2. Near-neighbour collapse survives the rerank in one label family.** The whole
point of a cross-encoder is that it reads label and segment jointly and can therefore
separate `counselling_individual` / `counselling_group` / `counselling_same_day`,
which the bi-encoder cannot. It half-works: the hybrid still calls
`counselling_same_day` positive at Algoma on "One-on-one counselling services" and
negative at Brock on "In-person or online 1:1 counselling" — the same distinction
decided both ways. The silver labels for these three come from keyword seeds that are
themselves poorly separated, so the model is learning a boundary that was never
coherent in its training signal.

**3. The redistribution is real but not uniformly good.** Against the baseline the
hybrid moves `speech_to_text` +7 schools, `exam_private_room` +5,
`counselling_same_day` +5, and `per_term_renewal` −8. Some of that is the intended
generalisation past exact-phrase seeds; some is drift. At 165 judged cells the gold
set cannot tell those apart per-label — the per-label intervals span most of [0,1].

## Inductive check: universities the model never saw

`--held-out-only` scores only the 6 universities held out of training, using the model
trained on the `university` split — which additionally drops every text those
universities share with the training set, because 63% of segments have text that
appears at more than one school.

| system | macro P | macro R | macro F1 | judged cells |
|---|---:|---:|---:|---:|
| keyword baseline | 1.00 | 0.97 | 0.98 | 31 |
| cross-encoder (university split) | 0.93 | 0.96 | 0.97 | 31 |

**31 cells over 21 labels is too few to conclude anything.** It is reported because
the alternative — quietly not reporting it — would leave the impression that the
transductive numbers above are an inductive claim. They are not.

## Silver validation (model selection only)

Never used for the comparison above; shown so the training runs are auditable.

| run | split | best epoch | val macro-AP (silver) |
|---|---|---:|---:|
| cross-encoder | text | 6 / 8 | 0.940 |
| cross-encoder | university | 8 / 8 | 0.977 |
| multi-label DistilBERT | text | 6 / 8 | 0.900 |

Average precision, not F1-at-0.5, so model selection does not smuggle in a threshold.
The university-split run scoring *higher* than the text-split run is a warning, not an
achievement: its validation set is drawn from fewer universities and is easier.

## Retrieval stage

At `--recall-target 0.98` the embedding retriever keeps 7,346 of 72,480
`(segment, label)` pairs — **10.1% of the pairs, retaining 97.6% of silver
positives**. That is the hybrid's actual contribution so far: a 10× cut in reranker
cost at ~2% recall loss. Its precision gain over the bare classifier (macro P
0.89 → 0.94) comes at −0.05 recall, which at this sample size is not separable from
noise.

## Two things that make every number here provisional

1. **The gold set is stratified by the keyword baseline's predictions.** Every other
   system is scored on cells sampled around a competitor's decision boundary. This
   predates the ML work and applies to the embedding comparison too.
2. **The learned systems are trained on that same baseline's output.** So the
   comparison is between a teacher and its students, judged on a sample chosen by the
   teacher.

Fixing (1) requires a batch stratified by the challenger's own predictions. Fixing
(2) requires human segment-level labels. `active_learning.py` addresses both: it
selects cells where the systems disagree, which is exactly where the keyword-stratified
sample is least informative.

## Next annotation batch

`data/gold/active_batch1_template.csv` — 40 cells, chosen from 731 unjudged, **all 40
being cells where the four systems split 2–2**. Concentrated on
`accessible_housing` (7), `counselling_individual` (6), `format_audio` (5),
`accessible_buildings` (4), `reduced_course_load` (4). The template is blind: no
predictions, no stratum, no vote counts. Selection reasons are written to a separate
`_provenance.json` that the annotator does not see.
