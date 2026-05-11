#!/usr/bin/env python3
"""Reproduce benchmark tables from archived annotation-only prediction files."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from t2know_eval.metrics import compute_metrics  # noqa: E402

MODEL_DISPLAY = {
    "biomedbert": "BiomedBERT",
    "biobert": "BioBERT",
    "w2ner_biomedbert": "W2NER + BiomedBERT",
}
MODEL_ORDER = ["biomedbert", "biobert", "w2ner_biomedbert"]
SEED_ORDER = ["12345", "23456", "34567"]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def model_seed_from_path(path: Path, pred_root: Path) -> tuple[str, str]:
    rel = path.relative_to(pred_root)
    model = rel.parts[0]
    seed = rel.parts[1].removeprefix("seed_")
    return model, seed


def entity_key(entity: dict) -> tuple[int, int, str]:
    return int(entity["start"]), int(entity["end"]), entity["label"]


def as_metric_entity(entity: dict) -> dict:
    start, end, label = entity_key(entity)
    return {"start": start, "end": end, "tag": label}


def overlap(a: dict, b: dict) -> bool:
    return (
        (b["start"] >= a["start"] and b["end"] <= a["end"])
        or (b["start"] <= a["start"] and b["end"] >= a["start"] and b["end"] <= a["end"])
        or (b["start"] >= a["start"] and b["start"] <= a["end"] and b["end"] >= a["end"])
        or (b["start"] <= a["start"] and b["end"] >= a["end"])
    )


def mean_std(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def exact_scores(gold_data: list[dict], pred_data: list[dict]) -> dict[str, float]:
    labels = sorted({entity["label"] for item in gold_data for entity in item["entities"]})
    tp = Counter()
    fp = Counter()
    fn = Counter()
    for gold_item, pred_item in zip(gold_data, pred_data):
        gold_counter = Counter(entity_key(entity) for entity in gold_item["entities"])
        pred_counter = Counter(entity_key(entity) for entity in pred_item["entities"])
        for key in set(gold_counter) | set(pred_counter):
            matched = min(gold_counter[key], pred_counter[key])
            label = key[2]
            tp[label] += matched
            fn[label] += gold_counter[key] - matched
            fp[label] += pred_counter[key] - matched
    total_tp = sum(tp.values())
    total_fp = sum(fp.values())
    total_fn = sum(fn.values())
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    micro_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    label_f1 = []
    for label in labels:
        p = tp[label] / (tp[label] + fp[label]) if tp[label] + fp[label] else 0.0
        r = tp[label] / (tp[label] + fn[label]) if tp[label] + fn[label] else 0.0
        label_f1.append(2 * p * r / (p + r) if p + r else 0.0)
    return {
        "exact_precision": precision,
        "exact_recall": recall,
        "exact_micro_f1": micro_f1,
        "exact_macro_f1": sum(label_f1) / len(label_f1),
    }


def gold_groups(real: list[dict]) -> dict[tuple[int, int, str], str]:
    spans: dict[tuple[int, int], set[str]] = defaultdict(set)
    for entity in real:
        spans[(entity["start"], entity["end"])].add(entity["tag"])
    groups = {}
    for i, entity in enumerate(real):
        same_span = len(spans[(entity["start"], entity["end"])]) > 1
        nested = any(
            i != j
            and (entity["start"], entity["end"]) != (other["start"], other["end"])
            and overlap(entity, other)
            for j, other in enumerate(real)
        )
        if same_span:
            group = "same_span"
        elif nested:
            group = "nested"
        else:
            group = "flat"
        groups[(entity["start"], entity["end"], entity["tag"])] = group
    return groups


def matched_gold_entities(real_entities: list[dict], pred_entities: list[dict]) -> set[tuple[int, int, str]]:
    real = sorted(real_entities, key=lambda row: (row["start"], row["tag"]))
    predicted = sorted(pred_entities, key=lambda row: (row["start"], row["tag"]))
    matched = []
    for gold in real.copy():
        for pred in predicted.copy():
            if gold["start"] == pred["start"] and gold["end"] == pred["end"] and gold["tag"] == pred["tag"]:
                matched.append((gold["start"], gold["end"], gold["tag"]))
                real.remove(gold)
                predicted.remove(pred)
                break
    for gold in real.copy():
        partial = [pred for pred in predicted.copy() if overlap(gold, pred)]
        partial = sorted(partial, key=lambda row: row["end"] - row["start"])
        for pred in partial:
            if pred["tag"] == gold["tag"]:
                matched.append((gold["start"], gold["end"], gold["tag"]))
                real.remove(gold)
                predicted.remove(pred)
                break
    return set(matched)


def recovery_scores(gold_data: list[dict], pred_data: list[dict]) -> dict[str, float]:
    counts = {"flat": [0, 0], "nested": [0, 0], "same_span": [0, 0]}
    for gold_item, pred_item in zip(gold_data, pred_data):
        real = [as_metric_entity(entity) for entity in gold_item["entities"]]
        predicted = [as_metric_entity(entity) for entity in pred_item["entities"]]
        groups = gold_groups(real)
        matched = matched_gold_entities(real, predicted)
        for key, group in groups.items():
            counts[group][1] += 1
            if key in matched:
                counts[group][0] += 1
    return {group: matched / total for group, (matched, total) in counts.items()}


def fmt(mean: float, std: float) -> str:
    return f"{mean:.4f} +/- {std:.4f}"


def write_aggregate_tsv(path: Path, rows: list[dict], metrics: list[str]) -> None:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_model[row["model_slug"]].append(row)
    fields = ["model", "model_slug", *[f"{metric}_mean" for metric in metrics], *[f"{metric}_std" for metric in metrics]]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for slug in MODEL_ORDER:
            values = by_model.get(slug, [])
            if not values:
                continue
            out = {"model": MODEL_DISPLAY.get(slug, slug), "model_slug": slug}
            for metric in metrics:
                mean, std = mean_std([float(row[metric]) for row in values])
                out[f"{metric}_mean"] = f"{mean:.10f}"
                out[f"{metric}_std"] = f"{std:.10f}"
            writer.writerow(out)


def write_manuscript_markdown(path: Path, rows: list[dict]) -> None:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_model[row["model_slug"]].append(row)
    lines = [
        "# Reproduced Manuscript Benchmark Values",
        "",
        "Values are means +/- population standard deviations over seeds 12345, 23456, and 34567.",
        "",
        "## Overlap-Aware Entity Metrics",
        "",
        "| Model | Precision | Recall | F1 | Accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for slug in MODEL_ORDER:
        values = by_model.get(slug, [])
        if not values:
            continue
        lines.append(
            "| {model} | {precision} | {recall} | {F1} | {accuracy} |".format(
                model=MODEL_DISPLAY.get(slug, slug),
                precision=fmt(*mean_std([float(row["precision"]) for row in values])),
                recall=fmt(*mean_std([float(row["recall"]) for row in values])),
                F1=fmt(*mean_std([float(row["F1"]) for row in values])),
                accuracy=fmt(*mean_std([float(row["accuracy"]) for row in values])),
            )
        )
    lines.extend(
        [
            "",
            "## Exact-Match Metrics",
            "",
            "| Model | Exact precision | Exact recall | Exact micro-F1 | Exact macro-F1 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for slug in MODEL_ORDER:
        values = by_model.get(slug, [])
        if not values:
            continue
        lines.append(
            "| {model} | {precision} | {recall} | {micro} | {macro} |".format(
                model=MODEL_DISPLAY.get(slug, slug),
                precision=fmt(*mean_std([float(row["exact_precision"]) for row in values])),
                recall=fmt(*mean_std([float(row["exact_recall"]) for row in values])),
                micro=fmt(*mean_std([float(row["exact_micro_f1"]) for row in values])),
                macro=fmt(*mean_std([float(row["exact_macro_f1"]) for row in values])),
            )
        )
    lines.extend(
        [
            "",
            "## Gold-Side Structural Recovery",
            "",
            "| Model | Flat mentions | Nested mentions | Same-span multi-label mentions |",
            "|---|---:|---:|---:|",
        ]
    )
    for slug in MODEL_ORDER:
        values = by_model.get(slug, [])
        if not values:
            continue
        lines.append(
            "| {model} | {flat} | {nested} | {same_span} |".format(
                model=MODEL_DISPLAY.get(slug, slug),
                flat=fmt(*mean_std([float(row["flat_recovery"]) for row in values])),
                nested=fmt(*mean_std([float(row["nested_recovery"]) for row in values])),
                same_span=fmt(*mean_std([float(row["same_span_recovery"]) for row in values])),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce T2KNOW benchmark tables from archived predictions.")
    parser.add_argument("--prediction-root", required=True)
    parser.add_argument("--gold")
    parser.add_argument("--annotation-only", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    pred_root = Path(args.prediction_root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    predictions = sorted(pred_root.glob("*/seed_*/test_predictions.jsonl"))
    if not predictions:
        (out / "README.md").write_text(
            "No archived prediction files were found. Benchmark reproduction requires `predictions/*/seed_*/test_predictions.jsonl`.\n",
            encoding="utf-8",
        )
        print("FAILURE: no archived prediction files found.")
        return 1
    rows = []
    for pred in predictions:
        gold = pred.parent / "test_gold.jsonl"
        if args.gold:
            gold = Path(args.gold)
        if not gold.exists():
            raise FileNotFoundError(f"Missing gold file for {pred}: {gold}")
        gold_data = load_jsonl(gold)
        pred_data = load_jsonl(pred)
        per_label, global_metrics = compute_metrics(gold_data, pred_data)
        model, seed = model_seed_from_path(pred, pred_root)
        per_label_path = out / f"{model}_seed_{seed}_per_label_metrics.csv"
        per_label.to_csv(per_label_path)
        exact = exact_scores(gold_data, pred_data)
        recovery = recovery_scores(gold_data, pred_data)
        rows.append(
            {
                "model": MODEL_DISPLAY.get(model, model),
                "model_slug": model,
                "seed": seed,
                "gold": gold.as_posix(),
                "pred": pred.as_posix(),
                "precision": global_metrics["Precision"],
                "recall": global_metrics["Recall"],
                "F1": global_metrics["F1"],
                "accuracy": global_metrics["Accuracy"],
                **exact,
                "flat_recovery": recovery["flat"],
                "nested_recovery": recovery["nested"],
                "same_span_recovery": recovery["same_span"],
                "per_label_metrics": per_label_path.as_posix(),
            }
        )
    with (out / "benchmark_reproduction_summary.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_aggregate_tsv(out / "manuscript_overlap_aware_summary.tsv", rows, ["precision", "recall", "F1", "accuracy"])
    write_aggregate_tsv(
        out / "manuscript_exact_match_summary.tsv",
        rows,
        ["exact_precision", "exact_recall", "exact_micro_f1", "exact_macro_f1"],
    )
    write_aggregate_tsv(
        out / "manuscript_structural_recovery_summary.tsv",
        rows,
        ["flat_recovery", "nested_recovery", "same_span_recovery"],
    )
    write_manuscript_markdown(out / "manuscript_benchmark_values.md", rows)
    print(f"Reproduced benchmark metrics for {len(rows)} prediction files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
