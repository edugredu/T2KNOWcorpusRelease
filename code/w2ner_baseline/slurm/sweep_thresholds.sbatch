#!/bin/bash
#SBATCH --job-name=t2k_w2ner_sweep
#SBATCH --output=slurm-t2k_w2ner_sweep-%j.out
#SBATCH --error=slurm-t2k_w2ner_sweep-%j.err
#SBATCH --partition=gplsi,dgx
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=06:00:00

set -euo pipefail

ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
VENV_DIR=${VENV_DIR:-$ROOT/.venv}
PYTHON_BIN=${PYTHON_BIN:-}
CONFIG_PATH=${CONFIG_PATH:?CONFIG_PATH is required}
MODEL_PATH=${MODEL_PATH:?MODEL_PATH is required}
DATA_DIR=${DATA_DIR:-$ROOT/code/w2ner_baseline/data/t2know_disjoint}
OUTPUT_ROOT=${OUTPUT_ROOT:?OUTPUT_ROOT is required}
NNW_THRESHOLDS=${NNW_THRESHOLDS:-0.3,0.4,0.5,0.6,0.7}
THW_THRESHOLDS=${THW_THRESHOLDS:-0.3,0.4,0.5,0.6,0.7}
EVAL_SPLIT=${EVAL_SPLIT:-dev}
DEVICE=${DEVICE:-0}

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

nvidia-smi || true

$PYTHON_BIN "$ROOT/code/w2ner_baseline/tools/sweep_thresholds.py" \
  --python-bin "$PYTHON_BIN" \
  --config "$CONFIG_PATH" \
  --model-path "$MODEL_PATH" \
  --data-dir "$DATA_DIR" \
  --output-root "$OUTPUT_ROOT" \
  --nnw-thresholds "$NNW_THRESHOLDS" \
  --thw-thresholds "$THW_THRESHOLDS" \
  --eval-split "$EVAL_SPLIT" \
  --device "$DEVICE"
