# T2KNOW-Core Official Benchmark

This file defines the official benchmark for T2KNOW-Core v1.0. The GitHub/Zenodo release tag is `t2know-core-v1.0.0`. All paper claims refer to these files and this configuration.

## Official Benchmark Files

All paths are relative to the release root.

```
data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json
data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json
data/t2know-core-v1.0/document_disjoint_hybrid/testData.json
data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl
```

The split JSON files and the consolidated JSONL file are two serialisations of the same reviewed annotation layer.

## Official Split Unit

**Document-disjoint.** Each reviewed source abstract belongs to exactly one of train, validation, or test. No abstract contributes sentences to more than one split. Split membership is defined by `meta.split` in each record.

## Official Label Inventory

40 biomedical entity types. The frozen label schema is `data/t2know-core-v1.0/metadata/label_schema.tsv`.

## Evaluation Command

Run from the release root:

```bash
# Overlap-aware evaluation (headline metric)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code \
  python3 -m t2know_eval.run_eval \
  --gold data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl \
  --pred <predictions.jsonl> \
  --output <results.csv>

# Exact-match evaluation (companion metric)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code \
  python3 -m t2know_eval.run_eval \
  --gold data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl \
  --pred <predictions.jsonl> \
  --output <results.csv> \
  --exact-match

# Reproduce benchmark tables from archived predictions
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

The headline resource-specific metric is overlap-aware F1. Exact-match metrics are companion/conventional scores.

## Excluded Files and Directories

The following files and directories are **not** part of the official T2KNOW-Core benchmark:

| Path | Reason |
|---|---|
| `data/sentence_level_legacy/` | Legacy sentence-level corpus; includes synthetic records and pre-audit text |
| `data/auxiliary/trainBalanced.json` | Balanced training variant; not document-disjoint |
| `data/brat_auxiliary/` | Auxiliary BRAT export; includes balanced-training documents |
| `data/brat/` | Legacy mixed BRAT layout; includes pre-audit text |
| `data/t2know-core-v1.0/text_included/` | Convenience view; same annotation layer as `document_disjoint_hybrid/` |
| `data/t2know-core-v1.0/text_excluded/` | Convenience view; same annotation layer as `document_disjoint_hybrid/` |

Only `document_disjoint_hybrid/` defines the official train/validation/test split. The `text_included/` and `text_excluded/` directories are provided for convenience and contain the same annotations, split only by redistribution status.

## Source Abstract Text Status

- **432 records**: source abstract text included (high-confidence source matches, permissive redistribution evidence)
- **389 records**: source abstract text excluded (source identifiers, checksums, and reconstruction metadata provided)

Public-redacted evaluation (annotation-only, no source abstract text) can verify all paper benchmark claims for the text-included subset and structural/annotation claims for all 821 records. Text-based training or offset validation over all 821 documents requires lawful user-side reconstruction and checksum validation for text-excluded records per `docs/reconstruction.md`.

## Checksums

```bash
sha256sum -c checksums.sha256
```

## Validation

```bash
python3 scripts/validate_corpus.py data/t2know-core-v1.0 --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid --format json --mode public-redacted
```

Expected: 14,356 sentences, 125,703 entities, 0 synthetic sentences, 0 errors.
