# T2KNOW-Core Public Release

This repository contains the rights-aware public release package for T2KNOW-Core v1.0.0, a biomedical nested named entity recognition resource focused on Huntington's disease literature.

## Repository, Licence, and Citation

- Public repository: <https://github.com/edugredu/T2KNOWcorpusRelease>
- Version tag: `t2know-core-v1.0.0`
- Corpus DOI: `10.5281/zenodo.20082992`
- Licence: MIT for project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code.
- Third-party scholarly abstract text remains governed by the original publication licences and publisher terms. Source text is redistributed only for records cleared by the source-licence audit.

Citation metadata is provided in `CITATION.cff` with the Zenodo archive DOI `10.5281/zenodo.20082992`.

## Release Model

The package follows a hybrid release model. The complete project-generated annotation, metadata, provenance, validation, evaluation, and benchmark layers are provided for all 821 reviewed source documents. Third-party source text is redistributed only where the source-licence audit found high-confidence source matches and permissive redistribution evidence.

- Total reviewed source documents: 821
- Source-text included records: 432
- Source-text excluded records: 389
- Final audit: `provenance/reports/source_license_audit_v6.tsv`
- Text-included subset: `provenance/reports/source_license_v6_include_text.tsv`
- Text-excluded subset: `provenance/reports/source_license_v6_exclude_text.tsv`
- Manual resolution evidence: `provenance/reports/source_license_manual_overrides.tsv`

The audit is metadata/licence evidence, not legal advice. Source text for records marked `exclude_text` is not redistributed in this public package.

## Data Layout

- `data/t2know-core-v1.0/document_disjoint_hybrid/`: all 821 reviewed documents at sentence level. Text is present for `include_text` records and redacted for `exclude_text` records.
- `data/t2know-core-v1.0/text_included/`: full-text JSON/JSONL and BRAT files for the 432 records cleared for redistribution.
- `data/t2know-core-v1.0/text_excluded/annotations_only/`: annotation-only JSON/JSONL for the 389 records whose source text is not redistributed.
- `data/t2know-core-v1.0/metadata/`: label schema, source metadata, source-selection provenance, and validation metadata.
- `docs/`: data format, reconstruction, policy, evaluation, and annotation guidance.
- `provenance/`: source-selection, release-decision, validation, statistics, and benchmark provenance.
- `scripts/` and `code/`: validation, reconstruction, evaluation, and benchmark reproduction support.
- `predictions/`: archived annotation-only benchmark predictions for reproducing the reported public metrics.

For text-excluded records, users should reconstruct source text from the original publications according to their own access rights and publisher terms. The operational workflow, source lookup order, normalization policy, checksum algorithm, validation command, and failure handling are specified in `docs/reconstruction.md`. Offsets and checksums are provided to support reconstruction and verification.

## Recommended Entry Points

- **Official benchmark specification: `OFFICIAL_BENCHMARK.md`** — defines the official benchmark files, split unit, evaluation commands, and excluded artefacts
- Main benchmark data: `data/t2know-core-v1.0/document_disjoint_hybrid/`
- Text-included BRAT inspection export: `data/t2know-core-v1.0/text_included/brat_core/`
- Reconstruction instructions: `docs/reconstruction.md`
- Release policy and licence boundary: `docs/dataset_policy.md`
- Corpus statistics verification notes: `provenance/reports/corpus_stats_public_verifiable.json`
- Reconstructed-full statistics notes: `provenance/reports/corpus_stats_reconstructed_full.json`

## Checksums

Run from this directory:

```bash
sha256sum -c checksums.sha256
```

## Benchmark Table Reproduction

The archived prediction files under `predictions/` are annotation-only public artifacts. Run from this directory:

```bash
python3 scripts/reproduce_benchmark_tables.py   --prediction-root predictions   --out provenance/reports/reproduced_benchmark_tables_public_redacted   --annotation-only
```

The rounded overlap-aware F1 means should be `0.6498` for BiomedBERT, `0.6102` for BioBERT, and `0.7206` for W2NER + BiomedBERT. Encoder model identifiers and recoverable revision status are recorded in `provenance/reports/model_revision_metadata.tsv`; exact Hugging Face revision hashes were not recoverable from archived local evidence.
