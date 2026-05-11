# T2KNOW Dataset Policy

## Purpose

This document fixes the dataset identity for the `T2KNOW-Core v1.0` paper and release workflow.
It exists to stop the paper from mixing the core resource with auxiliary training artefacts.

## Core decision

Canonical new-user entry point: `data/t2know-core-v1.0/`. The official benchmark entry point is `data/t2know-core-v1.0/document_disjoint_hybrid/`; here, `hybrid` means text-included plus text-excluded/reconstructable records in the same document-disjoint split representation, not synthetic mixing.


The **reviewed core resource** is **T2KNOW-Core v1.0**, the 821-abstract manually reviewed corpus described as the main object of the paper.

For the manuscript-aligned release, the recommended benchmark package is the reviewed-only document-disjoint split:

- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`
- `data/t2know-core-v1.0/text_included/brat_core/`

These files define the main benchmark claim in the paper. They contain only reviewed records, keep each source abstract in exactly one partition, and preserve all 40 labels across train, validation, and test. Public JSON/JSONL records are redacted for text-excluded documents: `text = null`, JSONL entity surface strings are `null`, and offsets are defined over reconstructed sentence text.

The earlier sentence-level split files remain in the repository for compatibility and provenance:

- `data/sentence_level_legacy/trainData.json`
- `data/sentence_level_legacy/evalData.json`
- `data/sentence_level_legacy/testData.json`
- `data/sentence_level_legacy/t2know.jsonl`

They should not be treated as the manuscript benchmark split unless the paper text is changed accordingly.

## Auxiliary variants

### Balanced training variant

`data/auxiliary/trainBalanced.json` and `data/brat_auxiliary/` are **auxiliary training artefacts**.

It may be useful for:
- model training,
- robustness experiments,
- ablations involving class imbalance.

It is **not** the reviewed core resource and must not be used for:
- the headline corpus description,
- the main corpus statistics table,
- the core resource claim,
- wording that implies it is the primary reviewed core resource.

### Synthetic or augmented data

Synthetic or augmented data is **supplementary only**.

Current policy:
- it is not part of the core resource claim,
- it must be released separately if released at all,
- it must be explicitly labeled as synthetic or augmented,
- it must never be merged silently into the reviewed core resource statistics.

At the time of writing, the release exposes a balanced training file but does not expose a separate reviewed synthetic-release artefact under `data/t2know-core-v1.0/document_disjoint_hybrid/`.

### Legacy mixed BRAT compatibility path

`data/brat/` is retained as a compatibility export because earlier internal workflows used a mixed BRAT layout. It contains reviewed train/eval/test folders together with the auxiliary `trainBalanced` folder. New resource users should use `data/t2know-core-v1.0/text_included/brat_core/` for the text-included public BRAT inspection export and `data/brat_auxiliary/` for auxiliary BRAT material. For benchmark split membership, use `data/t2know-core-v1.0/document_disjoint_hybrid/`; BRAT folder names are for file organisation and inspection, not the authority for the document-disjoint split.

## Manuscript policy

The paper must distinguish three layers:

1. **Reviewed core resource**
   - T2KNOW-Core v1.0, the 821-abstract manually reviewed corpus
   - this is the main object of the paper

2. **Auxiliary training artefact**
   - the balanced training artefact
   - useful for experiments, not for the main resource claim

3. **Supplementary augmentation artefacts**
   - any synthetic or generated data
   - optional, explicitly secondary

## Reporting rules

### Corpus statistics

Main corpus statistics must be computed on the reviewed core resource only.

If balanced or synthetic variants are described, they must be reported separately and clearly labeled.

### Benchmark experiments

Benchmark experiments may use:
- the reviewed document-disjoint training split,
- or the balanced training split,

but the manuscript must explicitly state which one is used.

If balanced training is used, the paper must say it is an auxiliary training variant rather than the core dataset.

### Release and documentation

Any public release should keep these artefacts separate:
- reviewed core resource (`data/t2know-core-v1.0/document_disjoint_hybrid/` and `data/t2know-core-v1.0/text_included/brat_core/`),
- balanced auxiliary training artefact,
- supplementary synthetic/augmented artefacts.

The public repository for the release is <https://github.com/edugredu/T2KNOWcorpusRelease>, with release tag `t2know-core-v1.0.0` for the T2KNOW-Core v1.0 corpus package. The GitHub release is <https://github.com/edugredu/T2KNOWcorpusRelease/releases/tag/t2know-core-v1.0.0>, commit `ea99f2a433751a0e33ec0abdfa19b3bc6cb38f41`. The release asset is `T2KNOW-public-upload-v1.0.0-20260511-r22.zip`; its SHA-256 checksum is recorded in the GitHub release description and accompanying paper after final packaging. The immutable corpus archive DOI is recorded on the final Zenodo record and in the accompanying paper.

Project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code are distributed under the MIT licence. Third-party scholarly abstract text remains governed by the original publication licences and publisher terms, and is redistributed only for records cleared by the source-licence audit.

## Source abstract text provenance and reuse

The release follows a rights-aware hybrid model. In this release, hybrid means that the official split combines text-included records and text-excluded/reconstructable records; it does not mean synthetic mixing. The complete T2KNOW-Core v1.0 project-generated annotation, split, and evaluation layer, including label schema, validation reports, benchmark scripts, source metadata, checksums, and provenance audit, is released for all 821 reviewed source documents. The authors can license project-generated annotations, code, documentation, validation scripts, evaluation scripts, and metadata. Third-party scholarly abstract text has a separate rights status.

Article-level redistribution evidence was audited using Europe PMC, Crossref, OpenAlex, and a manual source-link resolution pass. The final audit is `provenance/reports/source_license_audit_v6.tsv`, with text-included records listed in `provenance/reports/source_license_v6_include_text.tsv`, text-excluded records listed in `provenance/reports/source_license_v6_exclude_text.tsv`, and manual resolution evidence stored in `provenance/reports/source_license_manual_overrides.tsv`.

Source abstract text is redistributed only for the 432 records with high-confidence source matches and permissive redistribution evidence. For the remaining 389 records, third-party source abstract text is not redistributed; the release provides source identifiers, checksums, split assignments, and reconstruction metadata so that users can reconstruct the texts from the original publications according to their own access rights and publisher terms. All 389 text-excluded records have a source URL and normalized-document checksum; 387 also have a DOI. Text-based training or offset validation involving those records requires lawful reconstruction and checksum validation. The operational workflow, source lookup order, normalization policy, checksum rules, validation command, and failure handling are specified in `docs/reconstruction.md`. The audit is metadata/licence evidence, not legal advice. Users are responsible for ensuring that their reconstruction and use of third-party source abstract text complies with their access rights and publisher terms. API caches under `provenance/cache/` are working audit artefacts and should not be deposited publicly unless separately cleared.

The corpus does not contain newly collected human-subject data, patient records, or protected clinical text.

## Statistic verification modes

The public-redacted package is sufficient to verify document counts, sentence counts, entity counts, label counts, split membership, source-text redistribution status, same-span counts, and structural offset counts for T2KNOW-Core. Token counts and token-based sentence-length statistics for text-excluded records are computed from the staged source abstract text or checksum-validated reconstructed abstract text using Python `str.split()` over the fixed reviewed sentence strings. Users who cannot lawfully reconstruct and checksum-match all text-excluded records can inspect annotations and run annotation-only evaluation, but cannot independently verify 821-record token counts or reproduce text-based training over all 821 source abstract texts.

## Repository facts used for this policy

Current file counts:
- `data/sentence_level_legacy/trainData.json`: `5578` lines
- `data/auxiliary/trainBalanced.json`: `7154` lines
- `data/sentence_level_legacy/evalData.json`: `795` lines
- `data/sentence_level_legacy/testData.json`: `1594` lines
- `data/sentence_level_legacy/t2know.jsonl`: `15625` records
- `data/t2know-core-v1.0/text_included/brat_core/`: `432` `.txt` files and `432` `.ann` files
- `data/brat_auxiliary/`: `1029` `.txt` files and `1029` `.ann` files

Current split counts observed in `data/sentence_level_legacy/t2know.jsonl`:
- `train`: `11758`
- `val`: `1311`
- `test`: `2556`

Current split counts observed in `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`:
- `train`: `10052`
- `val`: `1435`
- `test`: `2869`

These counts are documentation evidence only. The reviewed-core-vs-auxiliary decision is a paper policy decision, not just a file-count decision.
