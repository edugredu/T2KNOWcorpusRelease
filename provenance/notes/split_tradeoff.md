# Split Trade-off Analysis

Input JSONL: `data/sentence_level_legacy/t2know.jsonl`

## Current reviewed split

- Unique reviewed source abstracts: `821`
- Train sentences: `10489`
- Validation sentences: `1311`
- Test sentences: `2556`
- Label coverage: train `40`, val `40`, test `40`
- Nested-sentence coverage: train `3928`, val `433`, test `1068`
- Same-span multi-label sentence coverage: train `5881`, val `646`, test `1310`

### Current abstract overlap pattern

- `test`: `150` abstracts
- `test+train`: `13` abstracts
- `test+train+val`: `9` abstracts
- `test+val`: `2` abstracts
- `train`: `575` abstracts
- `train+val`: `5` abstracts
- `val`: `67` abstracts

## Best document-disjoint candidate

- Search iterations: `500`
- Best random seed: `0`
- Candidate score: `0.146280`
- Sentence totals: train `10052`, val `1435`, test `2869`
- Entity totals: train `88234`, val `12593`, test `24876`
- Document totals: train `588`, val `82`, test `151`
- Label coverage: train `40`, val `40`, test `40`
- Nested-sentence coverage: train `3805`, val `596`, test `1028`
- Same-span multi-label sentence coverage: train `5632`, val `736`, test `1469`

### Missing labels in the candidate split

- Train: `[]`
- Validation: `[]`
- Test: `[]`

## Interpretation

- The current sentence-level split preserves full 40-label coverage in all three partitions, but it allows some reviewed source abstracts to contribute sentences to more than one split.
- The searched document-disjoint candidate also preserves full 40-label coverage in train, validation, and test.
- The candidate remains close to the intended `70/10/20` sentence-level proportion while preserving nested and same-span multi-label coverage in all three partitions.
- This means that a stronger document-disjoint benchmark appears feasible for the reviewed corpus and should be considered seriously for the paper benchmark.
