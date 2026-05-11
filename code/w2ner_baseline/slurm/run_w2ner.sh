#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
VENV_DIR=${VENV_DIR:-$ROOT/.venv}
PYTHON_BIN=${PYTHON_BIN:-}
RUN_NAME=${RUN_NAME:?RUN_NAME is required}
MODEL_NAME=${MODEL_NAME:?MODEL_NAME is required}
DATA_DIR=${DATA_DIR:-$ROOT/data/t2know-core-v1.0/text_included/document_disjoint}
PROCESSED_DATA_DIR=${PROCESSED_DATA_DIR:-$ROOT/code/w2ner_baseline/data/t2know_disjoint}
OUTPUT_DIR=${OUTPUT_DIR:-$ROOT/code/w2ner_baseline/runs/$RUN_NAME}
CONFIG_PATH=${CONFIG_PATH:?CONFIG_PATH is required}
SEED=${SEED:-12345}
EPOCHS=${EPOCHS:-30}
BATCH_SIZE=${BATCH_SIZE:-8}
NNW_THRESHOLD=${NNW_THRESHOLD:-0.5}
THW_THRESHOLD=${THW_THRESHOLD:-0.5}
GPU_MONITOR_INTERVAL=${GPU_MONITOR_INTERVAL:-0}
EXTRA_FLAGS=${EXTRA_FLAGS:-}

mkdir -p "$OUTPUT_DIR"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
if ! "$VENV_DIR/bin/python" -c "import numpy, pandas, torch, transformers" >/dev/null 2>&1; then
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$ROOT/code/w2ner_baseline/requirements.txt"
fi
source "$VENV_DIR/bin/activate"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

$PYTHON_BIN "$ROOT/code/w2ner_baseline/tools/prepare_t2know_w2ner.py" \
  --input-dir "$DATA_DIR" \
  --output-dir "$PROCESSED_DATA_DIR"

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
fi

$PYTHON_BIN "$ROOT/code/w2ner_baseline/main.py" \
  --config "$CONFIG_PATH" \
  --data_dir "$PROCESSED_DATA_DIR" \
  --output_dir "$OUTPUT_DIR" \
  --bert_name "$MODEL_NAME" \
  --seed "$SEED" \
  --epochs "$EPOCHS" \
  --batch_size "$BATCH_SIZE" \
  --nnw_threshold "$NNW_THRESHOLD" \
  --thw_threshold "$THW_THRESHOLD" \
  $EXTRA_FLAGS
