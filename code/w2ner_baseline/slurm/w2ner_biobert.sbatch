#!/bin/bash
#SBATCH --job-name=t2k_w2ner_biobert
#SBATCH --partition=gplsi,dgx
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=36:00:00
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err

set -euo pipefail
ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
export ROOT
export RUN_NAME=${RUN_NAME:-w2ner_biobert_disjoint_seed12345}
export MODEL_NAME=${MODEL_NAME:-dmis-lab/biobert-base-cased-v1.1}
export CONFIG_PATH=${CONFIG_PATH:-$ROOT/code/w2ner_baseline/config/t2know_biobert.json}

bash "$ROOT/code/w2ner_baseline/slurm/run_w2ner.sh"
