# Release Restructure Log

Date: 2026-05-04

This revision adds a stricter canonical T2KNOW-Core hierarchy without deleting existing release paths. Existing paths remain compatibility exports.

Added or refreshed paths:

- `data/t2know-core-v1.0/document_disjoint/` copied from `data/document_disjoint/`.
- `data/t2know-core-v1.0/brat_core/` copied from `data/brat_core/`.
- `data/t2know-core-v1.0/metadata/source_metadata.tsv` generated from the reviewed document-disjoint JSONL and linked BRAT files.
- `data/t2know-core-v1.0/metadata/source_metadata_README.md` documents recoverable and missing provenance fields.
- `data/t2know-core-v1.0/metadata/label_schema.tsv` generated from the frozen label inventory.
- `data/t2know-core-v1.0/metadata/mapping.tsv` points each active target label to the release mapping documentation.
- `data/t2know-core-v1.0/metadata/validation_report.json` copied from the document-disjoint validation report.
- `data/t2know-core-v1.0/metadata/source_selection_queries.tsv` copied from acquisition-level provenance.

No files were removed. The legacy and compatibility paths `data/document_disjoint/`, `data/brat_core/`, `data/brat/`, `data/brat_auxiliary/`, `data/sentence_level_legacy/`, and `data/auxiliary/` remain in place. New users should start from `data/t2know-core-v1.0/`.
