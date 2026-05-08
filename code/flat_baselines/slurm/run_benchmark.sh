#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
VENV_DIR=${VENV_DIR:-$ROOT/.venv}
PYTHON_BIN=${PYTHON_BIN:-}
RUN_NAME=${RUN_NAME:?RUN_NAME is required}
MODEL_NAME=${MODEL_NAME:?MODEL_NAME is required}
DATA_DIR=${DATA_DIR:-$ROOT/data/t2know-core-v1.0/text_included/document_disjoint}
TRAIN_FILE=${TRAIN_FILE:-$DATA_DIR/trainData.json}
EVAL_FILE=${EVAL_FILE:-$DATA_DIR/evalData.json}
TEST_FILE=${TEST_FILE:-$DATA_DIR/testData.json}
LABELS_FILE=${LABELS_FILE:-$ROOT/code/flat_baselines/labels.txt}
OUTPUT_DIR=${OUTPUT_DIR:-$ROOT/code/flat_baselines/runs/$RUN_NAME}
MAX_LENGTH=${MAX_LENGTH:-256}
LEARNING_RATE=${LEARNING_RATE:-1e-5}
BATCH_SIZE=${BATCH_SIZE:-32}
NUM_EPOCHS=${NUM_EPOCHS:-30}
WEIGHT_DECAY=${WEIGHT_DECAY:-0.2}
SEED=${SEED:-12345}
PROB_THRESHOLD=${PROB_THRESHOLD:-0.5}
START_CONFIDENCE=${START_CONFIDENCE:-0.9}
GRAD_ACCUM_STEPS=${GRAD_ACCUM_STEPS:-1}
GPU_MONITOR_INTERVAL=${GPU_MONITOR_INTERVAL:-0}
EXTRA_TRAIN_FLAGS=${EXTRA_TRAIN_FLAGS:-}
EXTRA_EVAL_FLAGS=${EXTRA_EVAL_FLAGS:-}

mkdir -p "$OUTPUT_DIR"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "[venv] creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import accelerate, datasets, numpy, torch, transformers, tqdm" >/dev/null 2>&1; then
  echo "[venv] installing or refreshing dependencies in $VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$ROOT/code/flat_baselines/requirements.txt"
fi

echo "[venv] using virtualenv at $VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

MONITOR_PID=""
if [[ "$GPU_MONITOR_INTERVAL" != "0" ]]; then
  MONITOR_LOG="$OUTPUT_DIR/gpu_monitor.csv"
  echo "timestamp,index,name,memory.used,memory.total,utilization.gpu,utilization.memory" > "$MONITOR_LOG"
  (
    while true; do
      nvidia-smi --query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,utilization.memory \
        --format=csv,noheader,nounits >> "$MONITOR_LOG" || true
      sleep "$GPU_MONITOR_INTERVAL"
    done
  ) &
  MONITOR_PID=$!
  trap 'if [[ -n "$MONITOR_PID" ]]; then kill "$MONITOR_PID" 2>/dev/null || true; fi' EXIT
  echo "[gpu] logging GPU usage every ${GPU_MONITOR_INTERVAL}s to $MONITOR_LOG"
fi

echo "[train] run=$RUN_NAME model=$MODEL_NAME output=$OUTPUT_DIR"
$PYTHON_BIN "$ROOT/code/flat_baselines/train.py" \
  --model-name "$MODEL_NAME" \
  --train-file "$TRAIN_FILE" \
  --eval-file "$EVAL_FILE" \
  --labels-file "$LABELS_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --max-length "$MAX_LENGTH" \
  --learning-rate "$LEARNING_RATE" \
  --batch-size "$BATCH_SIZE" \
  --num-epochs "$NUM_EPOCHS" \
  --weight-decay "$WEIGHT_DECAY" \
  --seed "$SEED" \
  --gradient-accumulation-steps "$GRAD_ACCUM_STEPS" \
  $EXTRA_TRAIN_FLAGS

echo "[eval] run=$RUN_NAME"
$PYTHON_BIN "$ROOT/code/flat_baselines/evaluate.py" \
  --model-dir "$OUTPUT_DIR/model" \
  --test-file "$TEST_FILE" \
  --labels-file "$LABELS_FILE" \
  --output-dir "$OUTPUT_DIR/eval_test" \
  --max-length "$MAX_LENGTH" \
  --logit-threshold "$PROB_THRESHOLD" \
  --start-confidence "$START_CONFIDENCE" \
  $EXTRA_EVAL_FLAGS
