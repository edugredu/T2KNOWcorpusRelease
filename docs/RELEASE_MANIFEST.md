# T2KNOW Release Manifest

This manifest freezes the release boundary for the manuscript-aligned T2KNOW corpus package.

## Manuscript-Aligned Release Package

Canonical new-user entry point: `data/t2know-core-v1.0/`. The official benchmark entry point is `data/t2know-core-v1.0/document_disjoint_hybrid/`; here, `hybrid` means text-included plus text-excluded/reconstructable records in one document-disjoint split representation, not synthetic mixing.


The canonical resource for the paper is **T2KNOW-Core v1.0**: the 821-abstract reviewed corpus represented by the document-disjoint recommended benchmark split and a text-included public BRAT inspection export.

The recommended benchmark package for the paper is under:

- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`
- `data/t2know-core-v1.0/text_included/brat_core/`

The document-disjoint hybrid JSON files should be the source for the manuscript benchmark claims and the public train/validation/test benchmark release. The public BRAT inspection export is split-neutral and text-included only. Do not infer benchmark split membership from the BRAT folder path; use `data/t2know-core-v1.0/document_disjoint_hybrid/` and the JSONL metadata field `meta.split`.

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
- Public-redacted validation verifies document, sentence, entity, label, split, same-span, and structural counts without source-text reconstruction. Token counts and token-based sentence-length statistics over all 821 records require the staged source abstract text or checksum-validated reconstructed abstract text for text-excluded records.


## Rights Boundary

This package follows a rights-aware hybrid release model. In this release, hybrid means that the official split combines text-included records and text-excluded/reconstructable records; it does not mean synthetic mixing. It includes the complete project-generated annotation, split, and evaluation layer for all 821 reviewed source documents, including label schema files, code, documentation, validation scripts, evaluation scripts, checksums, source metadata, and provenance reports. These project-generated materials can be licensed by the authors. Scholarly abstract text is third-party content with a separate rights status.

Article-level redistribution evidence was audited using Europe PMC, Crossref, OpenAlex, and a manual source-link resolution pass. The final audit is `provenance/reports/source_license_audit_v6.tsv`, with text-included records listed in `provenance/reports/source_license_v6_include_text.tsv`, text-excluded records listed in `provenance/reports/source_license_v6_exclude_text.tsv`, and manual resolution evidence stored in `provenance/reports/source_license_manual_overrides.tsv`.

Source abstract text is redistributed only for the 432 records with high-confidence source matches and permissive redistribution evidence. For the remaining 389 records, third-party source abstract text should not be redistributed by default; the release provides source identifiers, checksums, split assignments, and reconstruction metadata so that users can reconstruct the texts from the original publications according to their own access rights and publisher terms. All 389 text-excluded records have a source URL and normalized-document checksum; 387 also have a DOI. Text-based training or offset validation involving those records requires lawful reconstruction and checksum validation. The operational workflow, source lookup order, normalization policy, checksum rules, validation command, and failure handling are specified in `docs/reconstruction.md`. The audit is metadata/licence evidence, not legal advice. API caches under `provenance/cache/` are working audit artefacts and should not be deposited publicly unless separately cleared.

## Supporting Corpus Artefacts

The release includes the previous sentence-level corpus artefacts under `data/sentence_level_legacy/`:

- `data/sentence_level_legacy/trainData.json`
- `data/sentence_level_legacy/evalData.json`
- `data/sentence_level_legacy/testData.json`
- `data/sentence_level_legacy/t2know.jsonl`

The balanced training variant is kept separately under:

- `data/auxiliary/trainBalanced.json`
- `data/brat_auxiliary/trainBalanced/`

The legacy mixed BRAT export is retained under:

- `data/brat/`

These files remain useful for provenance, compatibility, and auxiliary experiments. They should not override T2KNOW-Core unless the paper text is changed accordingly.

Validation status:

```bash
python3 scripts/validate_corpus.py data/sentence_level_legacy/t2know.jsonl --format jsonl
python3 scripts/validate_corpus.py data/sentence_level_legacy --format json
python3 scripts/validate_corpus.py data/auxiliary --format json
python3 scripts/validate_corpus.py data/brat_auxiliary --format brat
```

Observed results:

- JSONL: `15625` sentences, `135065` entities, `1269` synthetic sentences, `0` errors.
- Legacy split JSON: `7967` sentences, `70069` entities, `0` errors.
- Auxiliary balanced JSON: `7154` sentences, `39271` entities, `0` errors.
- Auxiliary BRAT: `1029` documents, `50704` BRAT standoff annotations, `0` errors.

## Commit and Tag Recommendation

For the paper release, preserve the following release-boundary structure:

- `data/t2know-core-v1.0/document_disjoint_hybrid/` for the recommended benchmark package,
- `data/t2know-core-v1.0/text_included/brat_core/` for the text-included public BRAT inspection export of T2KNOW-Core v1.0,
- `data/sentence_level_legacy/` for compatibility/provenance files,
- `data/auxiliary/` for balanced or other auxiliary training artefacts,
- `data/brat_auxiliary/` for auxiliary BRAT artefacts,
- `data/brat/` for legacy mixed BRAT compatibility only,
- `docs/`, `provenance/`, `scripts/`, and `code/` for documentation and reproducibility support.

Final public repository metadata:

- Repository: <https://github.com/edugredu/T2KNOWcorpusRelease>
- Version tag: `t2know-core-v1.0.0`
- GitHub release: <https://github.com/edugredu/T2KNOWcorpusRelease/releases/tag/t2know-core-v1.0.0>
- Release commit: `ea99f2a433751a0e33ec0abdfa19b3bc6cb38f41`
- Release asset: `T2KNOW-public-upload-v1.0.0-20260511-r22.zip`
- Release asset SHA-256: recorded in the GitHub release description and accompanying paper after final packaging.
- Licence: MIT for project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code.
- Archive DOI: recorded on the final Zenodo record and in the accompanying paper.
