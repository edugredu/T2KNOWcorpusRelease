# Benchmark Predictions

Public benchmark artifacts for the document-disjoint T2KNOW-Core benchmark.

Files are annotation-only: sentence text and entity surface strings are omitted. Evaluation uses sentence IDs, offsets, spans, and labels.

Layout:

- `<model>/seed_<seed>/test_gold.jsonl`
- `<model>/seed_<seed>/test_predictions.jsonl`
- `<model>/seed_<seed>/global_metrics.json`
- `<model>/seed_<seed>/per_label_metrics.csv`
- `<model>/seed_<seed>/summary.json`

Reproduce the summary tables from the release root:

```bash
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

The command writes:

- `benchmark_reproduction_summary.tsv`: per-model/per-seed recomputed metrics.
- `manuscript_overlap_aware_summary.tsv`: mean/std values for the overlap-aware benchmark table.
- `manuscript_exact_match_summary.tsv`: mean/std values for the exact-match companion table.
- `manuscript_structural_recovery_summary.tsv`: mean/std values for the structural recovery table.
- `manuscript_benchmark_values.md`: copy-readable manuscript values.

The expected headline overlap-aware F1 means are `0.6498` for BiomedBERT, `0.6102` for BioBERT, and `0.7206` for W2NER + BiomedBERT.
