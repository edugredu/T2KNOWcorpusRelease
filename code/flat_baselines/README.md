# T2KNOW Flat Baselines

Clean benchmark training package for the LRE paper.

## Scope

This package contains the flat biomedical baselines used for the T2KNOW paper runs:

- `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` (PubMedBERT / BiomedBERT)
- `dmis-lab/biobert-base-cased-v1.1` (BioBERT)

It does **not** implement nested models such as `W2NER`. Those should remain separate if added later.

The current runner is intentionally limited to **BERT-family checkpoints**. That covers the planned paper baselines:

- `dmis-lab/biobert-base-cased-v1.1`
- `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`

## Files

- `train.py`: CLI trainer
- `evaluate.py`: exports `pred.jsonl`, `gold.jsonl`, `per_label_metrics.csv`, and `global_metrics.json`
- `common.py`: corpus and label utilities
- `modeling.py`: lightweight multilabel token-classification model wrapper
- `slurm/`: Slurm launch scripts
- `BENCHMARK_LOG.md`: human-readable log of benchmark decisions, completed runs, and next experiments

## Install

From the release root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r code/flat_baselines/requirements.txt
```

## Release-Local Benchmark Commands

These commands use the release package layout. Full training over all 821 documents requires local reconstruction of text-excluded records before training; the public hybrid files alone are sufficient for inspecting annotations and reproducing archived prediction metrics, but not for full benchmark retraining over redacted text.

```bash
RELEASE_ROOT=$(pwd)
DATA_DIR="$RELEASE_ROOT/data/t2know-core-v1.0/document_disjoint_hybrid"
LABELS_FILE="$RELEASE_ROOT/T2KNOWcode/listaCategorias.txt"

PYTHONPATH="$RELEASE_ROOT/code" python3 code/flat_baselines/train.py \
  --model-name microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext \
  --train-file "$DATA_DIR/trainData.json" \
  --eval-file "$DATA_DIR/evalData.json" \
  --labels-file "$LABELS_FILE" \
  --output-dir runs/biomedbert_seed12345 \
  --max-length 256 \
  --learning-rate 1e-5 \
  --batch-size 32 \
  --num-epochs 30 \
  --weight-decay 0.2 \
  --seed 12345

PYTHONPATH="$RELEASE_ROOT/code" python3 code/flat_baselines/evaluate.py \
  --model-dir runs/biomedbert_seed12345/model \
  --test-file "$DATA_DIR/testData.json" \
  --labels-file "$LABELS_FILE" \
  --output-dir runs/biomedbert_seed12345/eval_test \
  --max-length 256 \
  --logit-threshold 0.5 \
  --start-confidence 0.9
```

For BioBERT, replace the model name with `dmis-lab/biobert-base-cased-v1.1`. Repeat with seeds `12345`, `23456`, and `34567` to match the manuscript protocol.

## Expected dataset inputs

Defaults use the canonical corpus files:

- `T2KNOWcorpus/trainData.json`
- `T2KNOWcorpus/evalData.json`
- `T2KNOWcorpus/testData.json`
- `T2KNOWcode/listaCategorias.txt`

To benchmark a different split package, set `DATA_DIR`. In the public release, the document-disjoint hybrid benchmark files live in:

- `data/t2know-core-v1.0/document_disjoint_hybrid/`

## Local training example

```bash
python3 code/flat_baselines/train.py \
  --model-name microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext \
  --train-file data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json \
  --eval-file data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json \
  --labels-file T2KNOWcode/listaCategorias.txt \
  --output-dir runs/biomedbert_canonical
```

## Local evaluation example

```bash
python3 code/flat_baselines/evaluate.py \
  --model-dir runs/biomedbert_canonical/model \
  --test-file data/t2know-core-v1.0/document_disjoint_hybrid/testData.json \
  --labels-file T2KNOWcode/listaCategorias.txt \
  --output-dir runs/biomedbert_canonical/eval_test
```

## Slurm

Submit one of:

```bash
sbatch code/flat_baselines/slurm/biomedbert.sbatch
sbatch code/flat_baselines/slurm/biobert.sbatch
```

The launcher checks for `ROOT/.venv` by default. If it does not exist, it creates it and installs `code/flat_baselines/requirements.txt` before training starts.
The default benchmark `.sbatch` files target `postiguet1` for the first controlled runs. If you later want to move to `varadero`, do it explicitly rather than relying on scheduler defaults.

Both scripts accept environment overrides, for example:

```bash
sbatch --export=ALL,NUM_EPOCHS=20,BATCH_SIZE=16 code/flat_baselines/slurm/biomedbert.sbatch
```

Useful overrides:

- `DATA_DIR` (directory containing `trainData.json`, `evalData.json`, and `testData.json`)
- `LEARNING_RATE`
- `BATCH_SIZE`
- `NUM_EPOCHS`
- `GRAD_ACCUM_STEPS`
- `PROB_THRESHOLD` (logit cutoff during decoding, current default `0.5`)
- `START_CONFIDENCE` (extra gate for `B-` tags, current default `0.9`)

Current benchmark defaults in `run_benchmark.sh`:

- `MAX_LENGTH=256`
- `BATCH_SIZE=32`
- `NUM_EPOCHS=30`
- `WEIGHT_DECAY=0.2`
- `PROB_THRESHOLD=0.5`
- `START_CONFIDENCE=0.9`

## Threshold sweep for an existing checkpoint

Before scaling to more seeds or another model, run an evaluation-only decoding sweep on the validation split using the current best checkpoint.

Release-local example:

```bash
sbatch --export=ALL,MODEL_DIR=$PWD/runs/biomedbert_seed12345/model,OUTPUT_ROOT=$PWD/runs/biomedbert_seed12345/threshold_sweep_eval,MAX_LENGTH=256 code/flat_baselines/slurm/sweep_thresholds.sbatch
```

Using the document-disjoint split package:

```bash
sbatch --export=ALL,DATA_DIR=$PWD/data/t2know-core-v1.0/document_disjoint_hybrid,MODEL_DIR=$PWD/runs/biomedbert_seed12345/model,OUTPUT_ROOT=$PWD/runs/biomedbert_seed12345/threshold_sweep_eval,MAX_LENGTH=256 code/flat_baselines/slurm/sweep_thresholds.sbatch
```

This writes:

- `threshold_sweep_summary.csv`
- `threshold_sweep_summary.json`

sorted by the best F1 on the validation split.

Default sweep grid:

- logit thresholds: `0.0,0.1,0.2,0.3,0.4,0.5`
- start-confidence thresholds: `0.5,0.6,0.7,0.8,0.9`

The manuscript results use the validation-selected configuration `PROB_THRESHOLD=0.5` and `START_CONFIDENCE=0.9`.

## Notes

- The new runner keeps the historical flat multilabel-token formulation so results remain comparable to prior runs.
- Decoding uses `sigmoid` confidences, which is consistent with the multilabel BCE training objective.
- The trainer masks special/padding tokens out of the loss and applies capped positive-class weighting to reduce collapse to the all-negative solution.
- Final benchmark numbers for the paper should come from the outputs in `runs/<run_name>/eval_test/`.
- Evaluation uses the existing `t2know_eval` metric implementation.
