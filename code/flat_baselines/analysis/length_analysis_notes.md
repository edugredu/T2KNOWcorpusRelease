# Length Analysis Notes

## Job 43021

- Slurm job: `43021`
- Script: `code/flat_baselines/slurm/analyze_lengths_postiguet.sbatch`
- Node: `postiguet1.iuii.ua.es`
- Model tokenizer: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`
- Source artifact: `code/flat_baselines/analysis/length_summary_BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext.json`
- Status: `COMPLETED`
- Elapsed: `00:01:58`

## Overall token-length summary

- count: `7967`
- min: `4`
- mean: `32.6301`
- p50: `30`
- p90: `51`
- p95: `60`
- p99: `86`
- max: `508`

## Coverage by candidate max_length

- `128`: `0.9988703401531317`
- `256`: `0.9998744822392368`
- `384`: `0.9998744822392368`
- `512`: `1.0`

## Per-split maxima

- `trainData.json`: max `508`
- `evalData.json`: max `163`
- `testData.json`: max `208`

## Decision for first benchmark runs

- Use `max_length=256` for the first monitored training runs.
- Rationale:
  - `256` covers `99.987%` of the canonical examples.
  - The corpus is short in practice (`p99=86`).
  - `256` is a better first-run tradeoff than `512` for memory and throughput.
- Keep `512` available only if strict no-truncation becomes necessary for a later comparison run.

## What this analysis does not tell us

- It does not justify packing multiple full training jobs onto the same GPU.
- That decision should only be made after one monitored training run has produced actual GPU memory and utilization traces.
