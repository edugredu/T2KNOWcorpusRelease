#!/bin/bash
#SBATCH --job-name=t2k_sweep
#SBATCH --output=slurm-t2k_sweep-%j.out
#SBATCH --error=slurm-t2k_sweep-%j.err
#SBATCH --partition=gplsi,dgx
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=04:00:00

set -euo pipefail

ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
VENV_DIR=${VENV_DIR:-$ROOT/.venv}
PYTHON_BIN=${PYTHON_BIN:-}
MODEL_DIR=${MODEL_DIR:?MODEL_DIR is required}
OUTPUT_ROOT=${OUTPUT_ROOT:?OUTPUT_ROOT is required}
DATA_DIR=${DATA_DIR:-$ROOT/data/t2know-core-v1.0/text_included/document_disjoint}
TEST_FILE=${TEST_FILE:-$DATA_DIR/evalData.json}
LABELS_FILE=${LABELS_FILE:-$ROOT/code/flat_baselines/labels.txt}
MAX_LENGTH=${MAX_LENGTH:-256}
LOGIT_THRESHOLDS=${LOGIT_THRESHOLDS:-0.0,0.1,0.2,0.3,0.4,0.5}
START_CONFIDENCES=${START_CONFIDENCES:-0.5,0.6,0.7,0.8,0.9}
DEVICE=${DEVICE:-cuda}

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
source "$VENV_DIR/bin/activate"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

nvidia-smi || true

$PYTHON_BIN "$ROOT/code/flat_baselines/tools/sweep_thresholds.py" \
  --python-bin "$PYTHON_BIN" \
  --model-dir "$MODEL_DIR" \
  --output-root "$OUTPUT_ROOT" \
  --test-file "$TEST_FILE" \
  --labels-file "$LABELS_FILE" \
  --max-length "$MAX_LENGTH" \
  --logit-thresholds "$LOGIT_THRESHOLDS" \
  --start-confidences "$START_CONFIDENCES" \
  --device "$DEVICE"
