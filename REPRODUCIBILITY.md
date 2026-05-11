# T2KNOW-Core Reproducibility

This document provides a single entry point for reproducing the T2KNOW-Core paper results. All commands assume the release root as working directory.

## Environment

Python 3.11+, CUDA-capable GPU for training (flat baselines: A100-40GB or equivalent; W2NER: RTX PRO 6000 or equivalent). Exact environment details per model family are recorded in Supplementary Note S2 and in `code/flat_baselines/BENCHMARK_LOG.md`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r code/flat_baselines/requirements.txt   # flat baselines
pip install -r code/w2ner_baseline/requirements.txt    # W2NER baseline
```

No additional installation is required for the evaluator or validation scripts.

---

## 1. Public Package Integrity Check

```bash
sha256sum -c checksums.sha256
```

---

## 2. Corpus Validation

### Public-redacted validation (no source-text reconstruction)

```bash
python3 scripts/validate_corpus.py data/t2know-core-v1.0 --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid --format json --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/text_included/brat_core --format brat --mode public-redacted --scope text-included
```

Expected:
- JSONL: `14356` sentences, `125703` entities, `0` synthetic sentences, `0` errors
- Split JSON: `10052` train, `1435` validation, `2869` test sentences, `0` errors
- Public BRAT inspection export: `432` text-included documents, `0` errors

### Text leakage check

```bash
python3 scripts/check_no_text_leakage.py data
python3 scripts/check_no_text_leakage.py predictions
```

Expected: `SUCCESS` for both.

---

## 3. Reconstruction Validation

For users who have lawfully obtained source abstract texts for the 389 text-excluded records:

```bash
python3 scripts/build_reconstructed_core.py \
  --manifest provenance/reports/reconstruction_manifest.tsv \
  --sentence-manifest provenance/reports/reconstruction_sentence_manifest.tsv \
  --source-text-root <path/to/local/reconstructed_abstracts> \
  --out work/reconstructed/t2know-core-v1.0

python3 scripts/validate_reconstructed_core.py \
  work/reconstructed/t2know-core-v1.0
```

Expected: `SUCCESS: reconstructed core is valid.` with zero failures. Full documentation is in `docs/reconstruction.md`.

---

## 4. Benchmark Table Reproduction (Annotation-Only, No Training Required)

Reproduce the paper's benchmark tables from archived predictions:

```bash
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

Expected: matches 9 prediction files. Rounded overlap-aware F1 means reproduce to `0.6498` (BiomedBERT), `0.6102` (BioBERT), `0.7206` (W2NER + BiomedBERT).

---

## 5. Evaluator Smoke Test

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code \
  python3 -m t2know_eval.run_eval \
  --gold code/t2know_eval/sample_gold.jsonl \
  --pred code/t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv

diff -u code/t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
```

Expected: `Precision=0.5000`, `Recall=0.3000`, `F1=0.3750`, `Accuracy=0.3000`. `diff` produces no output.

---

## 6. Evaluation Commands

### Overlap-aware evaluation (headline metric)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code \
  python3 -m t2know_eval.run_eval \
  --gold data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl \
  --pred <predictions.jsonl> \
  --output <results.csv>
```

### Exact-match evaluation (companion metric)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code \
  python3 -m t2know_eval.run_eval \
  --gold data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl \
  --pred <predictions.jsonl> \
  --output <results.csv> \
  --exact-match
```

Input format: aligned JSONL files where line `n` in the prediction file matches line `n` in the gold file. Each record contains `entities` with `start`, `end`, `label`.

---

## 7. Training Commands

Text-based training over all 821 documents requires lawful reconstruction and checksum validation for text-excluded records. The commands below document the exact invocation used for the paper results; GPU resources (A100-40GB for flat models, RTX PRO 6000 for W2NER) are required.

### Flat baseline training (BiomedBERT example)

```bash
# Prepare data (requires reconstructed data for text-excluded records)
python3 code/flat_baselines/tools/prepare_data.py \
  --input-dir data/t2know-core-v1.0/document_disjoint_hybrid \
  --output-dir runs/flat_data

# Train
PYTHONPATH=code python3 code/flat_baselines/train.py \
  --model_name microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext \
  --data_dir runs/flat_data \
  --output_dir runs/biomedbert_seed12345 \
  --seed 12345 \
  --epochs 30 \
  --batch_size 32 \
  --learning_rate 1e-5 \
  --max_seq_len 256 \
  --weight_decay 0.2 \
  --max_pos_weight 50.0

# Export predictions (use validation-calibrated thresholds)
PYTHONPATH=code python3 code/flat_baselines/evaluate.py \
  --model_path runs/biomedbert_seed12345/best_model \
  --data_dir runs/flat_data \
  --output_dir predictions/biomedbert/seed_12345 \
  --logit_threshold 0.5 \
  --start_confidence 0.9
```

Repeat for seeds `23456` and `34567`. For BioBERT, replace `--model_name` with `dmis-lab/biobert-base-cased-v1.1`.

### W2NER baseline training

```bash
# Prepare data
python3 code/w2ner_baseline/tools/prepare_t2know_w2ner.py \
  --input-dir data/t2know-core-v1.0/document_disjoint_hybrid \
  --output-dir runs/w2ner_data/t2know_disjoint

# Train
PYTHONPATH=code python3 code/w2ner_baseline/main.py \
  --config code/w2ner_baseline/config/t2know_biomedbert.json \
  --data_dir runs/w2ner_data/t2know_disjoint \
  --output_dir runs/w2ner_biomedbert_seed12345 \
  --bert_name microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext \
  --seed 12345 \
  --epochs 30 \
  --batch_size 8 \
  --bert_lr 5e-6 \
  --task_lr 1e-3 \
  --weight_decay 0.0 \
  --gradient_clip 5.0
```

Repeat for seeds `23456` and `34567`. Validation-calibrated decoding thresholds are `0.7` for both neighbourhood and tail-head.

### HPC / Slurm

The Slurm launch scripts used for the paper runs are archived at:
- `code/flat_baselines/slurm/` (flat baselines)
- `code/w2ner_baseline/slurm/` (W2NER baseline)

These scripts contain the exact environment, queue, and GPU allocation that produced the reported results. They assume an HPC cluster with Slurm, CUDA modules, and the GPU classes noted above. Local rerun without HPC resources may require adjusting paths, module loads, and GPU device selection.

---

## 8. Archived Predictions

Paper predictions for all three reported seeds (`12345`, `23456`, `34567`) are archived under `predictions/`:

```
predictions/biomedbert/seed_12345/
predictions/biomedbert/seed_23456/
predictions/biomedbert/seed_34567/
predictions/biobert/seed_12345/
predictions/biobert/seed_23456/
predictions/biobert/seed_34567/
predictions/w2ner_biomedbert/seed_12345/
predictions/w2ner_biomedbert/seed_23456/
predictions/w2ner_biomedbert/seed_34567/
```

Each directory contains `test_predictions.jsonl`, `test_gold.jsonl`, `global_metrics.json`, `per_label_metrics.csv`, and `summary.json`.

---

## 9. Requirements Files

| Component | Requirements file |
|---|---|
| Flat baselines (BioBERT, BiomedBERT) | `code/flat_baselines/requirements.txt` |
| W2NER baseline | `code/w2ner_baseline/requirements.txt` |
| Evaluator and validation scripts | No additional dependencies beyond Python stdlib |

---

## 10. Quick Verification Summary

To verify the package without training:

```bash
sha256sum -c checksums.sha256                                    # 1. integrity
python3 scripts/validate_corpus.py data/t2know-core-v1.0 --mode public-redacted   # 2. corpus
python3 scripts/check_no_text_leakage.py data                    # 3. no leakage
python3 scripts/check_no_text_leakage.py predictions             # 4. no leakage in preds
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=code python3 -m t2know_eval.run_eval \
  --gold code/t2know_eval/sample_gold.jsonl \
  --pred code/t2know_eval/sample_pred.jsonl \
  --output /tmp/t2know_sample_results.csv                        # 5. smoke test
diff -u code/t2know_eval/sample_results.csv /tmp/t2know_sample_results.csv
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only                                              # 6. benchmark tables
```

All six steps should complete without errors.
