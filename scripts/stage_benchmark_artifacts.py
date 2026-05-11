#!/usr/bin/env python3
"""Stage public annotation-only benchmark prediction artifacts."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent.parent
OUT = ROOT / "predictions"
REPORTS = ROOT / "provenance/reports"
TEST_DATA = ROOT / "data/t2know-core-v1.0/document_disjoint/testData.json"
AUDIT = ROOT / "provenance/reports/source_license_audit_v6.tsv"

RUNS = [
    ("BiomedBERT", "biomedbert", "12345", WORKSPACE / "code/flat_baselines/runs/biomedbert_disjoint_seed12345/eval_test"),
    ("BiomedBERT", "biomedbert", "23456", WORKSPACE / "code/flat_baselines/runs/biomedbert_disjoint_seed23456/eval_test"),
    ("BiomedBERT", "biomedbert", "34567", WORKSPACE / "code/flat_baselines/runs/biomedbert_disjoint_seed34567/eval_test"),
    ("BioBERT", "biobert", "12345", WORKSPACE / "code/flat_baselines/runs/biobert_disjoint_seed12345/eval_test"),
    ("BioBERT", "biobert", "23456", WORKSPACE / "code/flat_baselines/runs/biobert_disjoint_seed23456/eval_test"),
    ("BioBERT", "biobert", "34567", WORKSPACE / "code/flat_baselines/runs/biobert_disjoint_seed34567/eval_test"),
    (
        "W2NER + BiomedBERT",
        "w2ner_biomedbert",
        "12345",
        WORKSPACE
        / "code/w2ner_baseline/runs/w2ner_biomedbert_disjoint_seed12345_threshold_sweep_test_best/nnw_0.70_thw_0.70/eval_test",
    ),
    (
        "W2NER + BiomedBERT",
        "w2ner_biomedbert",
        "23456",
        WORKSPACE
        / "code/w2ner_baseline/runs/w2ner_biomedbert_disjoint_seed23456_threshold_sweep_test_best/nnw_0.70_thw_0.70/eval_test",
    ),
    (
        "W2NER + BiomedBERT",
        "w2ner_biomedbert",
        "34567",
        WORKSPACE
        / "code/w2ner_baseline/runs/w2ner_biomedbert_disjoint_seed34567_threshold_sweep_test_best/nnw_0.70_thw_0.70/eval_test",
    ),
]


def load_test_ids() -> list[str]:
    ids = []
    with TEST_DATA.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                ids.append(json.loads(line)["id"])
    return ids


def load_doc_status() -> dict[str, str]:
    with AUDIT.open(newline="", encoding="utf-8") as handle:
        return {row["doc_id"]: row["source_text_decision"] for row in csv.DictReader(handle, delimiter="\t")}


def annotation_only_record(record: dict, fallback_id: str, doc_status: dict[str, str]) -> dict:
    record_id = record.get("id", fallback_id)
    doc_id = str(record_id).split("_", 1)[0]
    out = {
        "id": record_id,
        "entities": [],
        "meta": {
            "doc_id": doc_id,
            "source_text_decision": doc_status.get(doc_id, "unknown"),
        },
    }
    if "meta" in record:
        out["meta"].update(record["meta"])
        out["meta"]["source_text_decision"] = doc_status.get(str(out["meta"].get("doc_id", doc_id)), "unknown")
    for ent in record.get("entities", []):
        clean = {
            "start": ent["start"],
            "end": ent["end"],
            "label": ent["label"],
        }
        if "spans" in ent:
            clean["spans"] = ent["spans"]
        out["entities"].append(clean)
    return out


def write_annotation_only(src: Path, dst: Path, fallback_ids: list[str], doc_status: dict[str, str]) -> int:
    count = 0
    with src.open(encoding="utf-8") as handle, dst.open("w", encoding="utf-8") as out:
        for line in handle:
            if not line.strip():
                continue
            fallback_id = fallback_ids[count] if count < len(fallback_ids) else str(count)
            out.write(json.dumps(annotation_only_record(json.loads(line), fallback_id, doc_status), ensure_ascii=False) + "\n")
            count += 1
    return count


def read_global(path: Path) -> dict[str, float]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_public_summary(src: Path, dst: Path) -> None:
    data = json.loads(src.read_text(encoding="utf-8"))
    model_dir = data.get("model_dir", "")
    run_name = None
    if "/runs/" in model_dir:
        run_name = model_dir.split("/runs/", 1)[1].split("/model", 1)[0]
    if "model_dir" in data:
        data["archived_run_name"] = run_name
        data["model_dir"] = "model checkpoints not distributed in the public release"
    if "test_file" in data:
        data["test_file"] = "data/t2know-core-v1.0/document_disjoint_hybrid/testData.json"
    dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def raw_counts(path: Path) -> dict[str, float]:
    totals = {"Ca": 0.0, "Ia": 0.0, "Pa": 0.0, "Ma": 0.0, "Sa": 0.0}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for key in totals:
                totals[key] += float(row[key])
    return totals


def write_readme() -> None:
    (OUT / "README.md").write_text(
        """# Benchmark Predictions

Public benchmark artifacts for the document-disjoint T2KNOW-Core benchmark.

Files are annotation-only: sentence text and entity surface strings are omitted. Evaluation uses sentence IDs, offsets, spans, and labels.

Layout:

- `<model>/seed_<seed>/test_gold.jsonl`
- `<model>/seed_<seed>/test_predictions.jsonl`
- `<model>/seed_<seed>/global_metrics.json`
- `<model>/seed_<seed>/per_label_metrics.csv`
- `<model>/seed_<seed>/summary.json`

Reproduce the summary tables from the release root:

```bash
python3 scripts/reproduce_benchmark_tables.py \\
  --prediction-root predictions \\
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \\
  --annotation-only
```

The command writes per-seed metrics plus manuscript-style aggregate tables:

- `benchmark_reproduction_summary.tsv`
- `manuscript_overlap_aware_summary.tsv`
- `manuscript_exact_match_summary.tsv`
- `manuscript_structural_recovery_summary.tsv`
- `manuscript_benchmark_values.md`
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fallback_ids = load_test_ids()
    doc_status = load_doc_status()
    rows = []
    raw_rows = []
    for model_name, slug, seed, run_dir in RUNS:
        if not run_dir.exists():
            raise FileNotFoundError(run_dir)
        dst = OUT / slug / f"seed_{seed}"
        dst.mkdir(parents=True, exist_ok=True)
        n_gold = write_annotation_only(run_dir / "gold.jsonl", dst / "test_gold.jsonl", fallback_ids, doc_status)
        n_pred = write_annotation_only(run_dir / "pred.jsonl", dst / "test_predictions.jsonl", fallback_ids, doc_status)
        if n_gold != n_pred:
            raise RuntimeError(f"Record count mismatch for {slug} seed {seed}: gold={n_gold}, pred={n_pred}")
        shutil.copy2(run_dir / "global_metrics.json", dst / "global_metrics.json")
        shutil.copy2(run_dir / "per_label_metrics.csv", dst / "per_label_metrics.csv")
        write_public_summary(run_dir / "summary.json", dst / "summary.json")
        metrics = read_global(run_dir / "global_metrics.json")
        counts = raw_counts(run_dir / "per_label_metrics.csv")
        rows.append(
            {
                "model": model_name,
                "model_slug": slug,
                "seed": seed,
                "split": "test",
                "precision": metrics["Precision"],
                "recall": metrics["Recall"],
                "F1": metrics["F1"],
                "accuracy": metrics["Accuracy"],
                "records": n_gold,
                "prediction_path": f"predictions/{slug}/seed_{seed}/test_predictions.jsonl",
            }
        )
        raw_rows.append(
            {
                "model": model_name,
                "seed": seed,
                "split": "test",
                "metric_variant": "overlap-aware",
                **counts,
                "partial_weight": 0.5,
                "precision": metrics["Precision"],
                "recall": metrics["Recall"],
                "F1": metrics["F1"],
                "accuracy": metrics["Accuracy"],
                "status": "reproduced_from_archived_per_label_counts",
            }
        )
    write_readme()
    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "benchmark_summary.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with (REPORTS / "benchmark_raw_counts.tsv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "model",
            "seed",
            "split",
            "metric_variant",
            "Ca",
            "Ia",
            "Pa",
            "Ma",
            "Sa",
            "partial_weight",
            "precision",
            "recall",
            "F1",
            "accuracy",
            "status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw_rows)
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORTS / 'benchmark_summary.tsv'}")
    print(f"Wrote {REPORTS / 'benchmark_raw_counts.tsv'}")


if __name__ == "__main__":
    main()
