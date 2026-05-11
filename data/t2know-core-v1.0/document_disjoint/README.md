# Document-disjoint benchmark package

This directory contains a reviewed-only, document-disjoint benchmark variant derived from the canonical T2KNOW JSONL release.

Files:
- `trainData.json`: line-oriented JSON records for training.
- `evalData.json`: line-oriented JSON records for validation.
- `testData.json`: line-oriented JSON records for test.
- `t2know_document_disjoint.jsonl`: consolidated JSONL with updated split metadata.
- `summary.json`: split counts and provenance.

Offset and linkage metadata:
- JSONL entity offsets are sentence-relative character offsets over the released `text` string for text-included records and over reconstructed sentence text for text-excluded records.
- split-file tag offsets follow the same text-included/reconstructed-text rule.
- JSONL `meta.sentence_id` and split-file `id` use the same `doc_id_sentenceIndex` convention.
- JSONL `meta.sentence_index` is zero-based within each source abstract.
- JSONL `meta.document_start` and `meta.document_end` give the sentence boundary in the matching BRAT `.txt` file when `data/t2know-core-v1.0/brat_core/` is available during generation.
- JSONL `meta.brat_txt_path` and `meta.brat_ann_path` are present only when `brat_available_in_archive = true`.
- Benchmark split membership is defined by `meta.split` and the split JSON files, not by inferring a split from the BRAT folder path.
- `evalData.json` is the validation split.
- Public BRAT inspection files are text-included only.

Design properties:
- only non-synthetic reviewed sentences are included,
- each reviewed source abstract belongs to exactly one split,
- split membership follows the assignment stored in
  `provenance/reports/document_disjoint_split_candidate.json`.

## Split Construction Recipe

The split was generated at the source-abstract level. Candidate assignments were searched with a fixed seed of `0` over `500` randomized iterations. The search balances closeness to the `70/10/20` train/validation/test sentence ratio with full label coverage and retention of nested and same-span multi-label evidence in every split.

The release-local scripts are:

```bash
python3 T2KNOW-release/scripts/analyze_split_tradeoff.py
python3 T2KNOW-release/scripts/create_document_disjoint_benchmark.py
```

The default paths inside those scripts resolve relative to the release root, so the commands above regenerate the provenance reports and benchmark package without referring back to the source repository.

In this release package, the selected assignment and validation artefacts are stored under `provenance/reports/`:

- `document_disjoint_split_candidate.json`: selected document-to-split assignment.
- `document_disjoint_doc_ids.csv`: compact `doc_id,split` manifest.
- `document_disjoint_doc_ids_train.txt`: training document IDs.
- `document_disjoint_doc_ids_val.txt`: validation document IDs.
- `document_disjoint_doc_ids_test.txt`: test document IDs.
- `document_disjoint_label_counts.csv`: per-label train/validation/test counts.
- `document_disjoint_split_validation.json`: validation report confirming document disjointness, all-label coverage in each split, zero synthetic records, and consistency with the label-count table.

The per-label count table should be interpreted conservatively: the minimum per-label count across partitions is `2` and the median of the per-label partition minima is `166`, so the split preserves label availability rather than balanced support for every tail label.
