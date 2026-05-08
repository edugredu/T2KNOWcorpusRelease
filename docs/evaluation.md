# Evaluation Definition

T2KNOW uses an entity-level overlap-aware evaluator for the benchmark results. The evaluator compares aligned JSONL records in order: line `n` in the reference file is compared with line `n` in the prediction file. Each entity is represented as `(start, end, label)` over the released sentence text.

## Matching Classes

The evaluator assigns each gold or predicted entity to one of five count types:

- `Ca` correct: one reference entity and one predicted entity have identical `start`, `end`, and `label`.
- `Pa` partial: one remaining predicted entity overlaps one remaining reference entity and has the same `label`, but was not already counted as correct.
- `Ia` incorrect: one remaining predicted entity has the same `start` and `end` as one remaining reference entity but a different `label`.
- `Ma` missing: a remaining reference entity was not matched as correct, partial, or incorrect.
- `Sa` spurious: a remaining predicted entity was not matched as correct, partial, or incorrect.

Partial matches receive half credit in the final metrics. Incorrect matches are counted under the reference label. Spurious matches are counted under the predicted label.

## Matching Order and Tie-Breaking

The implementation performs one-to-one matching. Once a gold or predicted entity is matched, it is removed and cannot be reused by another match.

Pseudocode:

```text
for each aligned ref_record, pred_record:
    gold = sort(ref_record.entities, key=(start, label))
    pred = sort(pred_record.entities, key=(start, label))

    for each reference entity in remaining gold:
        if any remaining prediction has same start, end, and label:
            count Ca for the reference label
            remove the reference entity and the matched prediction

    for each reference entity in remaining gold:
        candidates = all remaining predictions whose spans overlap the reference span
        candidates = sort(candidates, key=span_length_ascending)
        if any candidate has the same label as the reference entity:
            count Pa for the reference label
            remove the reference entity and the first same-label candidate

    for each reference entity in remaining gold:
        if any remaining prediction has same start and end but a different label:
            count Ia for the reference label
            remove the reference entity and the matched prediction

    count each remaining reference entity as Ma under its reference label
    count each remaining predicted entity as Sa under its predicted label
```

A span is considered overlapping when the two character intervals intersect or one interval contains the other. If multiple predictions overlap the same reference entity during partial matching, the shortest overlapping prediction is considered first. Ties follow the sorted prediction order produced before partial matching.

## Metric Formulas

For each label and for the global micro-average, counts are converted into metrics as follows:

```text
Precision = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Sa)
Recall    = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Ma)
F1        = 2 * Precision * Recall / (Precision + Recall)
Accuracy  = (Ca + 0.5 * Pa) / (Ca + Ia + Pa + Ma + Sa)
```

If a denominator is zero, the corresponding metric is set to `0.0`.

## Sanity-Check Files

The evaluator includes a minimal expected-output test case:

- `code/t2know_eval/sample_gold.jsonl`
- `code/t2know_eval/sample_pred.jsonl`
- `code/t2know_eval/sample_results.csv`

Run the check from the parent directory of the release archive:

```bash
PYTHONPATH=T2KNOW-release/code python3 -m t2know_eval.run_eval \
  --gold T2KNOW-release/code/t2know_eval/sample_gold.jsonl \
  --pred T2KNOW-release/code/t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv

diff -u T2KNOW-release/code/t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
```

The command should report global metrics `Precision=0.5000`, `Recall=0.3000`, `F1=0.3750`, and `Accuracy=0.3000`, and the `diff` command should produce no output.

## Benchmark Calibration Grids

The manuscript benchmark fixes decoding thresholds after validation-split calibration and reports final results only on the held-out test split.

Flat BIO baselines:

- logit thresholds: `0.0,0.1,0.2,0.3,0.4,0.5`
- start-confidence thresholds: `0.5,0.6,0.7,0.8,0.9`
- selected setting: `logit_threshold=0.5`, `start_confidence=0.9`

W2NER baseline:

- NNW/neighbourhood thresholds: `0.3,0.4,0.5,0.6,0.7`
- THW/tail-head thresholds: `0.3,0.4,0.5,0.6,0.7`
- selected setting: `nnw_threshold=0.7`, `thw_threshold=0.7`

The executable sweep scripts are:

- `code/flat_baselines/tools/sweep_thresholds.py`
- `code/w2ner_baseline/tools/sweep_thresholds.py`

## Benchmark Table Reproduction

The archived prediction files under `predictions/` are annotation-only public artifacts. They omit sentence text and entity surface strings, but retain record IDs, offsets, spans where present, labels, and source-text redistribution status.

Run from the release root:

```bash
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

Expected generated files:

- `benchmark_reproduction_summary.tsv`: per-model/per-seed overlap-aware, exact-match, and structural-recovery values.
- `manuscript_overlap_aware_summary.tsv`: aggregate values for the main benchmark table.
- `manuscript_exact_match_summary.tsv`: aggregate values for the exact-match companion table.
- `manuscript_structural_recovery_summary.tsv`: aggregate values for the structural recovery table.
- `manuscript_benchmark_values.md`: human-readable mean/std values matching the manuscript tables.

Expected rounded overlap-aware F1 means are `0.6498` for BiomedBERT, `0.6102` for BioBERT, and `0.7206` for W2NER + BiomedBERT. Expected exact micro-F1 means are `0.5823`, `0.5432`, and `0.7103`, respectively.

Model checkpoints are not distributed in this package. Encoder model identifiers and recoverable revision status are recorded in `provenance/reports/model_revision_metadata.tsv`. Exact Hugging Face model revision hashes were not recoverable from the archived local evidence, so the release records that limitation rather than inventing revision identifiers.
