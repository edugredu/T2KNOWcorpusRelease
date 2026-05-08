# T2KNOW Release Manifest

This manifest freezes the release boundary for the manuscript-aligned T2KNOW corpus package.

## Manuscript-Aligned Release Package

Canonical new-user entry point: `data/t2know-core-v1.0/`. Top-level `data/t2know-core-v1.0/document_disjoint_hybrid/` and `data/t2know-core-v1.0/text_included/brat_core/`, if present, are synchronized compatibility mirrors.


The canonical resource for the paper is **T2KNOW-Core**: the 821-abstract reviewed corpus represented by the document-disjoint recommended benchmark split and reviewed-only BRAT export.

The recommended benchmark package for the paper is under:

- `data/t2know-core-v1.0/document_disjoint_hybrid/README.md`
- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`
- `data/t2know-core-v1.0/document_disjoint_hybrid/summary.json`
- `data/t2know-core-v1.0/text_included/brat_core/README.md`
- `data/t2know-core-v1.0/text_included/brat_core/`

The document-disjoint JSON files should be the source for the manuscript benchmark claims and the public train/validation/test benchmark release. The public BRAT export is split-neutral and text-included only. Do not infer benchmark split membership from the BRAT folder path; use `data/t2know-core-v1.0/document_disjoint_hybrid/` and the JSONL metadata field `meta.split`.

The benchmark evaluator is specified in `docs/evaluation.md` and implemented under `code/t2know_eval/`, including sample reference, prediction, and expected-output files for sanity checking the metric implementation.

Candidate-generation provenance is documented in `docs/label_mapping.md`. The original spaCy/scispaCy UMLS pre-annotation environment is not part of the reproducible release boundary; the release boundary starts from the reviewed annotations, frozen label inventory, reviewed document-disjoint split, validation scripts, and benchmark/evaluation code.

Validation status:

```bash
python3 scripts/validate_corpus.py data/t2know-core-v1.0 --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid --format json --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/text_included/brat_core --format brat --mode public-redacted --scope text-included
```

Observed results:

- JSONL: `14356` sentences, `125703` entities, `0` synthetic sentences, `0` errors.
- Split JSON: `10052` train, `1435` validation, `2869` test sentences, `0` errors.
- Public BRAT inspection export: `432` text-included documents, `0` errors.
- Public-redacted validation verifies document, sentence, entity, label, split, same-span, and structural counts without source-text reconstruction. Full-core token counts and token-based sentence-length statistics require the staged full abstract text or checksum-validated reconstructed abstract text for text-excluded records.


## Rights Boundary

This package follows a rights-aware hybrid release model. It includes project-generated annotation layers, label schema files, split definitions, code, documentation, validation scripts, evaluation scripts, checksums, source metadata, and provenance reports for all 821 reviewed source documents. These project-generated materials can be licensed by the authors. Scholarly abstract text is third-party content with a separate rights status.

Article-level redistribution evidence was audited using Europe PMC, Crossref, OpenAlex, and a manual source-link resolution pass. The final audit is `provenance/reports/source_license_audit_v6.tsv`, with text-included records listed in `provenance/reports/source_license_v6_include_text.tsv`, text-excluded records listed in `provenance/reports/source_license_v6_exclude_text.tsv`, and manual resolution evidence stored in `provenance/reports/source_license_manual_overrides.tsv`.

Source text is redistributed only for the 432 records with high-confidence source matches and permissive redistribution evidence. For the remaining 389 records, third-party source text should not be redistributed by default; the release provides source identifiers, checksums, split assignments, and reconstruction metadata so that users can reconstruct the texts from the original publications according to their own access rights and publisher terms. All 389 text-excluded records have a source URL and normalized-document checksum; 387 also have a DOI. The operational workflow, source lookup order, normalization policy, checksum rules, validation command, and failure handling are specified in `docs/reconstruction.md`. The audit is metadata/licence evidence, not legal advice. API caches under `provenance/cache/` are working audit artefacts and should not be deposited publicly unless separately cleared.

## Commit and Tag Recommendation

For the paper release, preserve the following release-boundary structure:

- `data/t2know-core-v1.0/document_disjoint_hybrid/` for the recommended benchmark package,
- `data/t2know-core-v1.0/text_included/brat_core/` for the reviewed-only BRAT export of T2KNOW-Core,
- `docs/`, `provenance/`, `scripts/`, and `code/` for documentation and reproducibility support.

Final public repository metadata:

- Repository: <https://github.com/edugredu/T2KNOWcorpusRelease>
- Version tag: `t2know-core-v1.0.0`
- GitHub release: <https://github.com/edugredu/T2KNOWcorpusRelease/releases/tag/t2know-core-v1.0.0>
- Release commit: recorded on the GitHub release page after upload.
- Release asset: recorded on the GitHub release page after upload.
- Release asset SHA-256: recorded externally after upload; file-level checksums are in `checksums.sha256`.
- Licence: MIT for project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code.
- Archive DOI: `10.5281/zenodo.20082992`
