# T2KNOW Evaluation Library

This package implements the entity-level overlap-aware evaluator used for the T2KNOW benchmark results.

## Input Format

Gold and prediction files are aligned JSONL files. Line `n` in the gold file is compared with line `n` in the prediction file. Each record must contain an `entities` list with character offsets over the released sentence text:

```json
{
  "text": "...",
  "entities": [
    {"start": 0, "end": 10, "label": "DiseaseOrSyndrome"}
  ]
}
```

## Matching Definition

The evaluator assigns entity matches to five count types:

- `Ca`: exact span and label match.
- `Pa`: same-label overlap after exact matches have been removed.
- `Ia`: same span but different label after exact and partial matches have been removed.
- `Ma`: unmatched reference entity.
- `Sa`: unmatched predicted entity.

Matching is one-to-one. Gold and predicted entities are first sorted by `(start, label)`. Exact matches are removed first, partial same-label overlaps are removed second, and same-span wrong-label matches are removed third. For partial matching, if several predictions overlap the same reference entity, the shortest overlapping prediction is considered first; ties follow the sorted prediction order.

## Formulas

Partial matches receive half credit:

```text
Precision = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Sa)
Recall    = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Ma)
F1        = 2 * Precision * Recall / (Precision + Recall)
Accuracy  = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Ma + Sa)
```

If a denominator is zero, the corresponding metric is set to `0.0`.

## Usage

```bash
python3 -m t2know_eval.run_eval \
  --gold path/to/gold.jsonl \
  --pred path/to/predictions.jsonl \
  --output results.csv
```

## Sanity Check

The package includes a small expected-output test:

```bash
python3 -m t2know_eval.run_eval \
  --gold t2know_eval/sample_gold.jsonl \
  --pred t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv

diff -u t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
```

The evaluator should print global metrics `Precision=0.5000`, `Recall=0.3000`, `F1=0.3750`, and `Accuracy=0.3000`. The `diff` command should produce no output.
