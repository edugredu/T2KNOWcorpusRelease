# Benchmark Log

This file records benchmark decisions, completed runs, and the next intended experiments for the new paper-facing training pipeline in `code/flat_baselines/`.

It is the canonical human-readable log for:
- benchmark configuration decisions,
- important run outcomes,
- decoding choices,
- and the next experiments to launch.

Raw artifacts remain under `code/flat_baselines/runs/`.

## Current benchmark objective

Minimum benchmark package for the paper:
- `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`
- `dmis-lab/biobert-base-cased-v1.1`

Preferred stretch benchmark:
- `W2NER`

Not on the critical path:
- `NuNER`
- more LLM checker experiments
- broad model-zoo exploration

## Frozen benchmark decisions so far

### Corpus and evaluation policy

- Use the canonical reviewed corpus:
  - `T2KNOWcorpus/trainData.json`
  - `T2KNOWcorpus/evalData.json`
  - `T2KNOWcorpus/testData.json`
- Tune decoding thresholds on the validation split only.
- Use the held-out test split only for the final chosen configuration.

### Current decoding policy

Current best decoding settings for the flat BiomedBERT baseline:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

These settings were selected by validation-split sweep and then confirmed on the held-out test split.

### Current training policy

Current working BiomedBERT training configuration:
- `seed = 12345`
- `max_length = 256`
- `batch_size = 32`
- `num_epochs = 30`
- `weight_decay = 0.2`

Current training objective / decoding notes:
- masked multilabel BCE-with-logits
- positive-class weighting enabled
- sigmoid-based decoding

## Length analysis

Reference job:
- Slurm job `43021`

Artifact:
- `code/flat_baselines/analysis/length_summary_BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext.json`

Decision note:
- `code/flat_baselines/analysis/length_analysis_notes.md`

Key result:
- `max_length = 256` was chosen as the first practical benchmark setting.

Summary:
- `128` covers `99.887%`
- `256` covers `99.987%`
- `512` covers `100%`

Interpretation:
- `256` preserves almost all examples while reducing memory and runtime relative to `512`.

## Important run history

### Failed engineering setup runs

#### Job `43024`

Status:
- failed before training

Cause:
- `TrainingArguments.__init__()` API mismatch (`evaluation_strategy` vs `eval_strategy`)

Action taken:
- patched `code/flat_baselines/train.py`

#### Jobs `43027` and `43028`

Status:
- failed before training

Cause:
- missing `accelerate`

Action taken:
- added `accelerate>=0.26.0` to `code/flat_baselines/requirements.txt`
- improved Slurm bootstrap dependency checks

### First complete but degenerate benchmark run

#### Run `biomedbert_seed12345_len256_r4`

Status:
- completed end to end

Test result:
- `Precision = 0.0000`
- `Recall = 0.0000`
- `F1 = 0.0000`
- `Accuracy = 0.0000`

Diagnosis:
- zero predicted entities
- decoding/training formulation was still collapsing

Action taken:
- masked loss introduced
- positive-class weighting introduced
- evaluation decoding changed to sigmoid-consistent logic
- `START_CONFIDENCE` lowered from `0.99` to `0.5`

### First successful meaningful BiomedBERT run

#### Slurm job `43075`

Run:
- `biomedbert_seed12345_len256_r5`

Status:
- completed successfully

Test result with untuned decoding:
- `Precision = 0.3302`
- `Recall = 0.8100`
- `F1 = 0.4692`
- `Accuracy = 0.3249`

Interpretation:
- training pipeline is working
- result is recall-heavy and precision-poor
- model checkpoint is usable, but decoding needed tuning before scaling

Artifacts:
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/eval_test/global_metrics.json`
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/eval_test/per_label_metrics.csv`

### Validation threshold sweep

#### Slurm job `43085`

Output root:
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/threshold_sweep_eval`

Purpose:
- tune decoding on `T2KNOWcorpus/evalData.json`

Best validation configuration:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Best validation metrics:
- `Precision = 0.5206`
- `Recall = 0.7164`
- `F1 = 0.6030`
- `Accuracy = 0.4745`

Interpretation:
- decoding, not only training, was responsible for the weak first result
- threshold tuning was large enough to freeze as the current decoding choice

Artifacts:
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/threshold_sweep_eval/threshold_sweep_summary.csv`
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/threshold_sweep_eval/threshold_sweep_summary.json`

### Held-out test evaluation with tuned decoding

#### Slurm job `43089`

Output root:
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/test_eval_best_thresholds`

Purpose:
- test the validation-selected decoding configuration on the held-out test split

Chosen configuration:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Test result:
- `Precision = 0.5359`
- `Recall = 0.7218`
- `F1 = 0.6151`
- `Accuracy = 0.4868`

Comparison against untuned test decoding:
- previous F1: `0.4692`
- tuned F1: `0.6151`
- absolute improvement: `+0.1459`

Interpretation:
- the current BiomedBERT checkpoint is now a credible baseline
- no immediate retraining ablation is required before scaling to more seeds

Artifacts:
- `code/flat_baselines/runs/biomedbert_seed12345_len256_r5/test_eval_best_thresholds/threshold_sweep_summary.json`

## Current best flat baseline result

Model:
- `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`

Configuration:
- `seed = 12345`
- `max_length = 256`
- `batch_size = 32`
- `num_epochs = 30`
- `weight_decay = 0.2`
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Held-out test result:
- `Precision = 0.5359`
- `Recall = 0.7218`
- `F1 = 0.6151`
- `Accuracy = 0.4868`

## BiomedBERT three-seed summary

Comparable three-seed test results use the same decoding configuration for all seeds:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Runs:
- `biomedbert_seed12345_len256_r5` with tuned held-out test evaluation from `43089`
- `biomedbert_seed23456_len256`
- `biomedbert_seed34567_len256`

Per-seed test results:

- `seed = 12345`
  - `Precision = 0.5359`
  - `Recall = 0.7218`
  - `F1 = 0.6151`
  - `Accuracy = 0.4868`

- `seed = 23456`
  - `Precision = 0.5437`
  - `Recall = 0.7169`
  - `F1 = 0.6184`
  - `Accuracy = 0.4886`

- `seed = 34567`
  - `Precision = 0.5224`
  - `Recall = 0.7148`
  - `F1 = 0.6037`
  - `Accuracy = 0.4728`

Mean +- standard deviation across the three seeds:
- `Precision = 0.5340 +- 0.0107`
- `Recall = 0.7178 +- 0.0036`
- `F1 = 0.6124 +- 0.0077`
- `Accuracy = 0.4828 +- 0.0087`

Interpretation:
- the BiomedBERT configuration is stable across seeds
- variance is low enough to treat this as the current reference flat baseline
- no immediate retraining ablation is required before running BioBERT

## BioBERT threshold sweep

Reference job:
- Slurm job `43162`

Output root:
- `code/flat_baselines/runs/biobert_seed12345_len256/threshold_sweep_eval`

Best validation configuration:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Best validation metrics:
- `Precision = 0.4815`
- `Recall = 0.6777`
- `F1 = 0.5630`
- `Accuracy = 0.4346`

Interpretation:
- BioBERT prefers the same decoding settings as BiomedBERT
- no separate decoding policy is needed for the two flat baselines

## BioBERT three-seed summary

Comparable three-seed test results use:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

Runs:
- `biobert_seed12345_len256`
- `biobert_seed23456_len256`
- `biobert_seed34567_len256`

Per-seed test results:

- `seed = 12345`
  - `Precision = 0.4881`
  - `Recall = 0.6912`
  - `F1 = 0.5721`
  - `Accuracy = 0.4410`

- `seed = 23456`
  - `Precision = 0.4775`
  - `Recall = 0.7020`
  - `F1 = 0.5683`
  - `Accuracy = 0.4362`

- `seed = 34567`
  - `Precision = 0.4680`
  - `Recall = 0.6935`
  - `F1 = 0.5589`
  - `Accuracy = 0.4266`

Mean +- standard deviation across the three seeds:
- `Precision = 0.4778 +- 0.0100`
- `Recall = 0.6956 +- 0.0057`
- `F1 = 0.5665 +- 0.0068`
- `Accuracy = 0.4346 +- 0.0073`

Interpretation:
- BioBERT is stable across seeds
- BioBERT is weaker than BiomedBERT under the same benchmark setup

## Flat baseline comparison

Three-seed comparison under the same decoding policy:
- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

BiomedBERT:
- `Precision = 0.5340 +- 0.0107`
- `Recall = 0.7178 +- 0.0036`
- `F1 = 0.6124 +- 0.0077`
- `Accuracy = 0.4828 +- 0.0087`

BioBERT:
- `Precision = 0.4778 +- 0.0100`
- `Recall = 0.6956 +- 0.0057`
- `F1 = 0.5665 +- 0.0068`
- `Accuracy = 0.4346 +- 0.0073`

Interpretation:
- BiomedBERT is the stronger flat biomedical baseline
- BioBERT remains a valid second flat biomedical baseline for the paper
- the flat benchmark package is now stable enough to support the manuscript benchmark section

## Document-disjoint benchmark upgrade

The reviewed benchmark was strengthened by generating a document-disjoint split package under:

- `T2KNOWcorpus/document_disjoint/`

Supporting artefacts:

- `paper/notes/split_tradeoff.md`
- `annotationValidation/reports/split_tradeoff_analysis.json`
- `annotationValidation/reports/document_disjoint_split_candidate.json`

The first seed on the document-disjoint benchmark produced:

- BiomedBERT:
  - `Precision = 0.5687`
  - `Recall = 0.7449`
  - `F1 = 0.6450`
  - `Accuracy = 0.5187`
- BioBERT:
  - `Precision = 0.5180`
  - `Recall = 0.7339`
  - `F1 = 0.6073`
  - `Accuracy = 0.4761`

Validation sweeps on the document-disjoint split confirmed that both model families still prefer:

- `LOGIT_THRESHOLD = 0.5`
- `START_CONFIDENCE = 0.9`

So no decoder change was needed before scaling to the remaining seeds.

## Document-disjoint three-seed summary

BiomedBERT:

- `Precision = 0.5756 +- 0.0069`
- `Recall = 0.7461 +- 0.0037`
- `F1 = 0.6498 +- 0.0038`
- `Accuracy = 0.5240 +- 0.0045`
- `Macro-F1 = 0.4945 +- 0.0048`
- `Head-label mean F1 = 0.6759 +- 0.0037`
- `Tail-label mean F1 = 0.1712 +- 0.0146`

BioBERT:

- `Precision = 0.5239 +- 0.0042`
- `Recall = 0.7306 +- 0.0045`
- `F1 = 0.6102 +- 0.0023`
- `Accuracy = 0.4791 +- 0.0023`
- `Macro-F1 = 0.4542 +- 0.0010`
- `Head-label mean F1 = 0.6427 +- 0.0046`
- `Tail-label mean F1 = 0.1425 +- 0.0092`

Interpretation:
- the document-disjoint benchmark is stable across seeds,
- BiomedBERT remains the stronger flat biomedical baseline,
- the stronger benchmark design does not collapse label coverage,
- and the document-disjoint path should now replace the earlier sentence-level benchmark path in the paper unless a new issue emerges.

## Next experiments

### Immediate next step

Start manuscript writing for corpus statistics and benchmark reporting using the completed flat baseline package.

## Nested baseline: W2NER

The preferred nested baseline was completed in the separate workspace:
- `code/w2ner_baseline/`

Configuration:
- encoder: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`
- benchmark split: `T2KNOWcorpus/document_disjoint/`
- seeds: `12345`, `23456`, `34567`

Important implementation note:
- the stock `W2NER` formulation was adapted so that same-span multi-label mentions can be exported back into the T2KNOW evaluation format instead of being collapsed into a single label per span

Decoder calibration:
- validation sweep selected:
  - `NNW_THRESHOLD = 0.7`
  - `THW_THRESHOLD = 0.7`

Final three-seed document-disjoint summary:
- `Precision = 0.5973 +- 0.0012`
- `Recall = 0.9079 +- 0.0008`
- `F1 = 0.7206 +- 0.0010`
- `Accuracy = 0.5806 +- 0.0010`
- `Macro-F1 = 0.6332 +- 0.0041`
- `Head-label mean F1 = 0.7372 +- 0.0007`
- `Tail-label mean F1 = 0.4720 +- 0.0168`

Interpretation:
- the nested baseline is stable across seeds,
- it outperforms the flat BiomedBERT baseline by about `+0.0708` absolute F1 on the same document-disjoint benchmark,
- and it provides direct modelling evidence that structurally appropriate architectures benefit from the released corpus.

## Updated reporting policy for the paper

- The main benchmark section should now report:
  - flat BiomedBERT
  - flat BioBERT
  - BiomedBERT-backed `W2NER`
- Flat transformer baselines should still be described as lower-bound reference points.
- `W2NER` should be described as the first structurally appropriate nested baseline in the paper, not as an exhaustive upper bound on the task.

## Next experiments

### Immediate next step

Patch the manuscript so the benchmark section reflects:
- the document-disjoint benchmark split,
- the final flat baseline summaries,
- and the completed nested `W2NER` baseline.

### Deferred unless needed

- additional nested model families
- retraining ablation over:
  - `bert_learning_rate`
  - `learning_rate`
  - `nnw_threshold`
  - `thw_threshold`
- only if the manuscript review reveals a strong need for further modelling evidence
## Reporting policy for the paper

- Final benchmark reporting should use mean and standard deviation across 3 seeds for all model families.
- Flat baselines should be interpreted as lower-bound reference systems.
- `W2NER` should be used as the main evidence that the resource supports structurally richer modelling than flat BIO decoding alone.
