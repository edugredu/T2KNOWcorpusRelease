#!/bin/bash
#SBATCH --job-name=t2k_biomedbert
#SBATCH --partition=gplsi,dgx
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err

set -euo pipefail
ROOT=${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
export ROOT
export RUN_NAME=${RUN_NAME:-biomedbert_canonical}
export MODEL_NAME=${MODEL_NAME:-microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext}

bash "$ROOT/code/flat_baselines/slurm/run_benchmark.sh"
