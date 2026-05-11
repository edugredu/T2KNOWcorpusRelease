#!/bin/bash
#SBATCH --job-name=t2k_lengths
#SBATCH --partition=postiguet1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err

set -euo pipefail

ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
VENV_DIR=${VENV_DIR:-$ROOT/.venv}
PYTHON_BIN=${PYTHON_BIN:-}
MODEL_NAME=${MODEL_NAME:-microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext}
DATA_DIR=${DATA_DIR:-$ROOT/data/t2know-core-v1.0/text_included/document_disjoint}
FILES=${FILES:-$DATA_DIR/trainData.json $DATA_DIR/evalData.json $DATA_DIR/testData.json}
OUTPUT=${OUTPUT:-$ROOT/code/flat_baselines/analysis/length_summary_$(basename "$MODEL_NAME" | tr '/:' '__').json}

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "[venv] creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import accelerate, datasets, numpy, transformers" >/dev/null 2>&1; then
  echo "[venv] installing or refreshing dependencies in $VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$ROOT/code/flat_baselines/requirements.txt"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "[info] model=$MODEL_NAME"
echo "[info] files=$FILES"
echo "[info] output=$OUTPUT"

echo "[gpu] snapshot before run"
nvidia-smi || true

$PYTHON_BIN "$ROOT/code/flat_baselines/tools/analyze_lengths.py" \
  --model-name "$MODEL_NAME" \
  --files $FILES \
  --output "$OUTPUT"

echo "[gpu] snapshot after run"
nvidia-smi || true
