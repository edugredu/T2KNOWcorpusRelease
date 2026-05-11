# Reproduced Manuscript Benchmark Values

Values are means +/- population standard deviations over seeds 12345, 23456, and 34567.

## Overlap-Aware Entity Metrics

| Model | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|
| BiomedBERT | 0.5756 +/- 0.0069 | 0.7461 +/- 0.0037 | 0.6498 +/- 0.0038 | 0.5240 +/- 0.0045 |
| BioBERT | 0.5239 +/- 0.0042 | 0.7306 +/- 0.0045 | 0.6102 +/- 0.0023 | 0.4791 +/- 0.0023 |
| W2NER + BiomedBERT | 0.5973 +/- 0.0012 | 0.9079 +/- 0.0008 | 0.7206 +/- 0.0010 | 0.5806 +/- 0.0010 |

## Exact-Match Metrics

| Model | Exact precision | Exact recall | Exact micro-F1 | Exact macro-F1 |
|---|---:|---:|---:|---:|
| BiomedBERT | 0.5158 +/- 0.0070 | 0.6686 +/- 0.0035 | 0.5823 +/- 0.0045 | 0.4380 +/- 0.0030 |
| BioBERT | 0.4663 +/- 0.0043 | 0.6504 +/- 0.0061 | 0.5432 +/- 0.0038 | 0.3966 +/- 0.0029 |
| W2NER + BiomedBERT | 0.5888 +/- 0.0013 | 0.8950 +/- 0.0008 | 0.7103 +/- 0.0012 | 0.6268 +/- 0.0032 |

## Gold-Side Structural Recovery

| Model | Flat mentions | Nested mentions | Same-span multi-label mentions |
|---|---:|---:|---:|
| BiomedBERT | 0.8616 +/- 0.0027 | 0.6701 +/- 0.0123 | 0.8069 +/- 0.0048 |
| BioBERT | 0.8507 +/- 0.0032 | 0.6689 +/- 0.0029 | 0.7845 +/- 0.0070 |
| W2NER + BiomedBERT | 0.9313 +/- 0.0005 | 0.8686 +/- 0.0029 | 0.9234 +/- 0.0022 |
