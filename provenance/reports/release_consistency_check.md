# Release Consistency Check

Date: 2026-04-22

## Checked Release Boundary

The manuscript-aligned T2KNOW release uses the following archive-relative structure:

- `data/document_disjoint/`: reviewed document-disjoint train, validation, and test package used for the official benchmark.
- `data/sentence_level_legacy/`: previous sentence-level split files and consolidated JSONL retained for compatibility and provenance.
- `data/auxiliary/`: auxiliary training artefacts, currently `trainBalanced.json`.
- `data/brat/`: secondary BRAT standoff export for inspection and interoperability.
- `docs/`, `provenance/`, `scripts/`, and `code/`: documentation, provenance reports, validation scripts, evaluator, and benchmark implementations.

## Consistency Decisions

- The official benchmark is defined only by `data/document_disjoint/`.
- The reviewed core resource is the 821-abstract reviewed corpus represented by the reviewed document-disjoint package and consolidated reviewed JSONL.
- Balanced, synthetic, and legacy files are not part of the headline corpus statistics or official benchmark.
- The manuscript release table, release README, data-format document, dataset policy, and release manifest use the same resource boundary.

## Validation Commands

Run from the `T2KNOW-release/` archive root:

```bash
python3 scripts/validate_corpus.py data/document_disjoint/t2know_document_disjoint.jsonl --format jsonl
python3 scripts/validate_corpus.py data/document_disjoint --format json
python3 scripts/validate_corpus.py data/sentence_level_legacy/t2know.jsonl --format jsonl
python3 scripts/validate_corpus.py data/sentence_level_legacy --format json
python3 scripts/validate_corpus.py data/auxiliary --format json
PYTHONPATH=code python3 -m t2know_eval.run_eval \
  --gold code/t2know_eval/sample_gold.jsonl \
  --pred code/t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv
diff -u code/t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
sha256sum -c checksums.sha256
```

## Observed Results

- Reviewed JSONL: `14356` sentences, `125703` entities, `0` synthetic sentences, `0` errors.
- Reviewed split JSON: `10052` train, `1435` validation, `2869` test sentences, `0` errors.
- Legacy JSONL: `15625` sentences, `135065` entities, `1269` synthetic sentences, `0` errors.
- Legacy split JSON: `7967` sentences, `70069` entities, `0` errors.
- Auxiliary balanced JSON: `7154` sentences, `39271` entities, `0` errors.
- Evaluation sanity check: expected sample output reproduced exactly.
- Checksums: regenerated after documentation edits and verified successfully.
