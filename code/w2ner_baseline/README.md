# T2KNOW W2NER benchmark workspace

This directory vendors the official W2NER implementation and adapts it to the T2KNOW document-disjoint benchmark.

## Important adaptation

The original W2NER code assumes a single label per tail-head relation. T2KNOW contains frequent same-span multi-label mentions, so this workspace changes the grid supervision from single-class classification to multi-label binary classification over relation channels. In practical terms:

- channel `1` remains the NNW relation;
- channels `2..N` are entity type channels;
- the decoder can emit multiple entity types for the same head-tail span.

This is necessary to avoid discarding a large fraction of same-span multi-label supervision.

## Data preparation

The launcher converts the T2KNOW JSONL split files into W2NER JSON format automatically:

```bash
python3 code/w2ner_baseline/tools/prepare_t2know_w2ner.py \
  --input-dir data/t2know-core-v1.0/document_disjoint_hybrid \
  --output-dir runs/w2ner_data/t2know_disjoint
```

Full training over all 821 documents requires local reconstruction of text-excluded records before training. The public hybrid files are enough to reproduce archived prediction metrics, but records with redacted text cannot be used directly for full-text retraining.

## Release-Local Benchmark Command

Run from the release root after installing `code/w2ner_baseline/requirements.txt`:

```bash
RELEASE_ROOT=$(pwd)

PYTHONPATH="$RELEASE_ROOT/code" python3 code/w2ner_baseline/main.py \
  --config code/w2ner_baseline/config/t2know_biomedbert.json \
  --data_dir runs/w2ner_data/t2know_disjoint \
  --output_dir runs/w2ner_biomedbert_seed12345 \
  --bert_name microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext \
  --seed 12345 \
  --epochs 30 \
  --batch_size 8 \
  --nnw_threshold 0.7 \
  --thw_threshold 0.7
```

Repeat with seeds `12345`, `23456`, and `34567` to match the manuscript protocol.

## First run

```bash
sbatch code/w2ner_baseline/slurm/w2ner_biomedbert.sbatch
```

Useful overrides:

```bash
sbatch --export=ALL,RUN_NAME=w2ner_biomedbert_seed12345,SEED=12345,GPU_MONITOR_INTERVAL=30 code/w2ner_baseline/slurm/w2ner_biomedbert.sbatch
```

Outputs go to:

- `runs/<run_name>/train_history.json`
- `runs/<run_name>/eval_test/pred.jsonl`
- `runs/<run_name>/eval_test/gold.jsonl`
- `runs/<run_name>/eval_test/per_label_metrics.csv`
- `runs/<run_name>/eval_test/global_metrics.json`

The final evaluation uses `t2know_eval` so the numbers are comparable to the flat baselines reported in the manuscript.

## Threshold sweep

Decoder thresholds are calibrated on the validation split before final test evaluation.

Default sweep grid:

- NNW/neighbourhood thresholds: `0.3,0.4,0.5,0.6,0.7`
- THW/tail-head thresholds: `0.3,0.4,0.5,0.6,0.7`

Run the sweep for an existing checkpoint with:

```bash
sbatch code/w2ner_baseline/slurm/sweep_thresholds.sbatch
```

The manuscript results use the validation-selected configuration `NNW_THRESHOLD=0.7` and `THW_THRESHOLD=0.7`.
