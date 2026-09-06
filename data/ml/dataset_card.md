# ML dataset card

Built by `extraction/dataset.py` (seed 0).

- segments in corpus: **2,265**
- unique normalized texts (training examples): **1,169**
- labels: **32**
- (text, label) pairs: **37,408**
- silver positives: **742** (2.0%)
- masked as ambiguous, excluded from loss: **338** (0.9%)
- negatives: **36,328**

Labels are distant supervision from the keyword baseline. They are not human
annotation and are not gold. The 165 human-judged cells are cell-level and are
held out entirely; they are never read here.

## Splits

| mode | train | val | test | leak-free by |
|---|---|---|---|---|
| text | 819 | 175 | 175 | distinct normalized text |
| university | 700 | 123 | 346 | whole university + every text it shares |

Held-out universities: Brock University, Ontario Tech University, Trent University (Durham GTA), University of Guelph, Wilfrid Laurier University, York University (Markham)

## Per-label silver counts

| label | positives | masked | mask threshold (cos) |
|---|---:|---:|---:|
| exam_extended_time | 17 | 2 | 0.6147 |
| exam_breaks | 16 | 0 | 0.6046 |
| exam_private_room | 11 | 3 | 0.6801 |
| deadline_extension | 8 | 3 | 0.4 |
| reduced_course_load | 3 | 0 | 0.7436 |
| note_taking | 34 | 0 | 0.5676 |
| lecture_recording | 11 | 0 | 0.7466 |
| asl_interpretation | 14 | 0 | 0.4099 |
| realtime_captioning | 12 | 1 | 0.53 |
| format_braille | 13 | 0 | 0.5895 |
| format_audio | 26 | 6 | 0.494 |
| format_large_print | 22 | 0 | 0.429 |
| format_accessible_digital | 32 | 1 | 0.6093 |
| assistive_tech_general | 31 | 1 | 0.6436 |
| screen_reader | 18 | 1 | 0.5827 |
| speech_to_text | 7 | 1 | 0.5001 |
| accessible_buildings | 8 | 133 | 0.5923 |
| accessible_housing | 6 | 5 | 0.6444 |
| accessible_parking_transit | 2 | 1 | 0.6592 |
| personalized_plan | 22 | 3 | 0.6968 |
| per_term_renewal | 18 | 0 | 0.4 |
| interim_without_documentation | 9 | 20 | 0.5873 |
| confidentiality | 15 | 0 | 0.5277 |
| intake_meeting | 148 | 59 | 0.413 |
| counselling_individual | 6 | 0 | 0.8809 |
| counselling_group | 12 | 26 | 0.5628 |
| counselling_same_day | 8 | 19 | 0.5157 |
| peer_support | 5 | 5 | 0.6283 |
| crisis_line_24_7 | 22 | 5 | 0.4 |
| transition_program | 6 | 1 | 0.6287 |
| osap_bswd | 83 | 30 | 0.4991 |
| bursaries_scholarships | 97 | 12 | 0.4885 |
