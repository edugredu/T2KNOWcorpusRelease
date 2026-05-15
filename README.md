# T2KNOW Release

This archive contains the manuscript-aligned release package for T2KNOW-Core v1.0, a biomedical nested named entity recognition resource focused on Huntington's disease literature.

## Repository, Licence, and Citation

- Public repository: <https://github.com/edugredu/T2KNOWcorpusRelease>
- Version tag: `t2know-core-v1.0.0`
- GitHub release: <https://github.com/edugredu/T2KNOWcorpusRelease/releases/tag/t2know-core-v1.0.0>
- Release commit: `ea99f2a433751a0e33ec0abdfa19b3bc6cb38f41`
- Release asset: `T2KNOW-public-upload-v1.0.0-20260511-r22.zip`
- Release asset SHA-256: `cd41b7d459287ca0543e342751b586f8aba36aadf9c176813167340a3cae156e`
- Immutable corpus DOI: `10.5281/zenodo.20121761` (<https://doi.org/10.5281/zenodo.20121761>)
- Licence: MIT for project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code.
- Third-party scholarly abstract text remains governed by the original publication licences and publisher terms. Source abstract text is redistributed only for records cleared by the source-licence audit.

Citation metadata is provided in `CITATION.cff` with the immutable Zenodo version DOI `10.5281/zenodo.20121761`.

## T2KNOW-Core

Canonical new-user entry point: `data/t2know-core-v1.0/`. The official benchmark entry point is `data/t2know-core-v1.0/document_disjoint_hybrid/`; here, `hybrid` means text-included plus text-excluded/reconstructable records in the same official split representation, not synthetic mixing.

> **Important.** Only the files in `data/t2know-core-v1.0/document_disjoint_hybrid/` define the official benchmark and headline corpus statistics. Auxiliary, balanced, legacy, synthetic, and compatibility files distributed elsewhere in the archive must not be used for headline corpus or benchmark claims.


The canonical resource described in the paper is **T2KNOW-Core v1.0**: the 821-abstract reviewed corpus represented by the document-disjoint recommended benchmark split and a text-included public BRAT inspection export.

Official benchmark files:

- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`

The public BRAT inspection export is `data/t2know-core-v1.0/text_included/brat_core/` and contains text-included records only. All-record BRAT can be generated locally after lawful reconstruction and checksum validation. Benchmark split membership is defined by the JSON/JSONL split files, not by BRAT folder names.

## Additional and Compatibility Data

- `data/sentence_level_legacy/`: earlier sentence-level split files and consolidated JSONL, retained for compatibility and provenance.
- `data/auxiliary/trainBalanced.json`: auxiliary balanced training artefact.
- `data/brat_auxiliary/`: BRAT export of auxiliary balanced training material.
- `data/brat/`: legacy mixed BRAT export retained for compatibility; use `data/t2know-core-v1.0/text_included/brat_core/` for the text-included public BRAT inspection export of T2KNOW-Core v1.0.

## Source Abstract Text Provenance and Reuse

This archive follows a rights-aware hybrid release model. In this release, hybrid means that the official split combines text-included records and text-excluded/reconstructable records; it does not mean synthetic mixing. The complete T2KNOW-Core v1.0 project-generated annotation, split, and evaluation layer, including label schema, validation reports, benchmark scripts, source metadata, checksums, and provenance audit, is released for all 821 reviewed source documents. The authors can license project-generated annotations, code, documentation, validation scripts, evaluation scripts, and metadata. Third-party scholarly abstract text has a separate rights status.

Article-level redistribution evidence was audited using Europe PMC, Crossref, OpenAlex, and a manual source-link resolution pass. The final audit is `provenance/reports/source_license_audit_v6.tsv`. Source abstract text is redistributed only for the 432 records listed in `provenance/reports/source_license_v6_include_text.tsv`; for the 389 records listed in `provenance/reports/source_license_v6_exclude_text.tsv`, third-party source abstract text should not be redistributed by default. The manual resolution evidence is stored in `provenance/reports/source_license_manual_overrides.tsv`.

For text-excluded records, the release provides source identifiers, checksums, split assignments, and reconstruction metadata so that users can reconstruct the source abstract texts from the original publications according to their own access rights and publisher terms. All 389 text-excluded records have a source URL and normalized-document checksum; 387 also have a DOI. The operational workflow, source lookup order, normalization policy, checksum algorithm, validation command, and failure handling are specified in `docs/reconstruction.md`. Records that cannot be lawfully accessed or checksum-validated remain available as annotation/provenance metadata but cannot be used for local training over reconstructed abstract text or offset validation involving those records. The audit is metadata/licence evidence, not legal advice. Users are responsible for ensuring that their reconstruction and use of third-party source abstract text complies with their access rights and publisher terms. API caches under `provenance/cache/` are working audit artefacts and should not be deposited publicly unless separately cleared.

The corpus does not contain newly collected human-subject data, patient records, or protected clinical text.

### Non-reproducible construction-provenance elements

The reproducible resource boundary of this release is T2KNOW-Core v1.0 itself, not the source-retrieval pipeline that produced the candidate document pool. The original Web of Science export, retrieval date, pre-annotation tool versions (spaCy, scispaCy, entity linker), and the UMLS release used for pre-annotation are not preserved. Only the surviving acquisition queries (`provenance/source_selection_queries.tsv`) and the source identifiers of the 821 reviewed documents are released. This limitation affects historical provenance but not the reuse of the reviewed corpus: the released annotation layer, splits, evaluator, and benchmark scripts can be inspected and re-run independently of the source-retrieval pipeline.

## Documentation

The `docs/` directory contains the release-facing dataset policy, annotation guidelines, data format specification, label mapping note, evaluation definition, and release manifest.

## Code

- `scripts/`: validation, conversion, statistics, split generation, and label-mapping checks.
- `code/t2know_eval/`: overlap-aware evaluation implementation and sample files.
- `code/flat_baselines/`: BiomedBERT/BioBERT flat baseline training and evaluation code.
- `code/w2ner_baseline/`: W2NER adaptation used for the nested baseline.
- `T2KNOWcode/listaCategorias.txt`: frozen label inventory retained at this compatibility path because the validation scripts expect it there.

Generated model checkpoints, training run directories, Slurm logs, virtual environments, caches, and paper build artefacts are intentionally excluded.

## Validation Commands

Run these commands from the parent directory that contains this archive:

```bash
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl --mode public-redacted
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/t2know-core-v1.0/document_disjoint_hybrid --format json --mode public-redacted
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/t2know-core-v1.0/text_included/brat_core --format brat --mode public-redacted --scope text-included
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/sentence_level_legacy/t2know.jsonl --format jsonl
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/sentence_level_legacy --format json
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/auxiliary --format json
python3 T2KNOW-release/scripts/validate_corpus.py T2KNOW-release/data/brat_auxiliary --format brat
```

Expected T2KNOW-Core validation:

- `14356` sentences
- `125703` entities
- `0` synthetic sentences
- `0` validation errors
- text-included public BRAT inspection export: `432` documents, `0` validation errors

## Evaluation Sanity Check

The overlap-aware evaluator is documented in `docs/evaluation.md` and implemented in `code/t2know_eval/`. The release includes sample gold, prediction, and expected-output files:

- `code/t2know_eval/sample_gold.jsonl`
- `code/t2know_eval/sample_pred.jsonl`
- `code/t2know_eval/sample_results.csv`

Run the evaluator check from the parent directory that contains this archive:

```bash
PYTHONPATH=T2KNOW-release/code python3 -m t2know_eval.run_eval \
  --gold T2KNOW-release/code/t2know_eval/sample_gold.jsonl \
  --pred T2KNOW-release/code/t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv

diff -u T2KNOW-release/code/t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
```

Expected global metrics are `Precision=0.5000`, `Recall=0.3000`, `F1=0.3750`, and `Accuracy=0.3000`; the `diff` command should produce no output.

## Benchmark Table Reproduction

The archived public prediction files are under `predictions/`. They are annotation-only files: sentence text and entity surface strings are omitted, while offsets, spans where present, labels, record IDs, and source-text redistribution status are retained.

Run from this release root:

```bash
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

The command writes per-seed metrics and manuscript-style aggregate tables. The rounded overlap-aware F1 means should be `0.6498` for BiomedBERT, `0.6102` for BioBERT, and `0.7206` for W2NER + BiomedBERT.

Encoder model identifiers and recoverable revision status are in `provenance/reports/model_revision_metadata.tsv`. Exact Hugging Face model revision hashes were not recoverable from archived local evidence; the release records this provenance limitation rather than assigning unverified hashes.

## Split Reproducibility

The recommended benchmark split is reproducible from the release provenance files and scripts. The selected assignment uses seed `0`, was selected from `500` randomized iterations, and is stored in `provenance/reports/document_disjoint_split_candidate.json`.

The selection procedure is implemented in:

- `scripts/analyze_split_tradeoff.py`
- `scripts/create_document_disjoint_benchmark.py`

The split search works at the source-abstract level over reviewed, non-synthetic records. For each candidate seed, documents are greedily assigned to train, validation, or test while balancing four factors:

- closeness to the target `70/10/20` sentence ratio,
- preservation of all 40 labels in every split,
- preservation of nested-sentence coverage in every split,
- preservation of same-span multi-label coverage in every split.

Validation and test missing labels receive the strongest penalty, train missing labels receive a smaller penalty, and splits with zero nested or zero same-span evidence are penalised. The lowest-scoring candidate is retained; equal scores keep the earliest seed.

The release also includes:

- `provenance/reports/document_disjoint_doc_ids.csv`
- `provenance/reports/document_disjoint_doc_ids_train.txt`
- `provenance/reports/document_disjoint_doc_ids_val.txt`
- `provenance/reports/document_disjoint_doc_ids_test.txt`
- `provenance/reports/document_disjoint_label_counts.csv`
- `provenance/reports/document_disjoint_split_validation.json`

The validation report confirms that no source abstract appears in more than one split, all 40 labels appear in train, validation, and test, and no synthetic records are included in the recommended benchmark split. Full per-label counts are listed in `provenance/reports/document_disjoint_label_counts.csv`; the minimum per-label count across partitions is `2` and the median of the per-label partition minima is `166`, so full label coverage should be interpreted as availability rather than balanced support.

## Checksums

Use `checksums.sha256` to verify public archive contents after download or upload.

```bash
cd T2KNOW-public-upload-v1.0.0-20260511-r22
sha256sum -c checksums.sha256
```

## Citation

Use the accompanying `CITATION.cff`. The immutable archive DOI is `10.5281/zenodo.20121761` (<https://doi.org/10.5281/zenodo.20121761>).
