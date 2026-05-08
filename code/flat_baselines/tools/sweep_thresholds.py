import argparse
import csv
import itertools
import json
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Sweep decoding thresholds for an existing T2KNOW checkpoint")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--test-file", default="T2KNOWcorpus/evalData.json")
    parser.add_argument("--labels-file", default="code/flat_baselines/labels.txt")
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument(
        "--logit-thresholds",
        default="0.0,0.1,0.2,0.3,0.4,0.5",
        help="Comma-separated logit threshold values",
    )
    parser.add_argument(
        "--start-confidences",
        default="0.5,0.6,0.7,0.8,0.9",
        help="Comma-separated start-confidence values",
    )
    parser.add_argument("--device", default="cuda")
    return parser.parse_args()


def parse_float_list(raw_value: str):
    values = []
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        values.append(float(item))
    if not values:
        raise ValueError("At least one numeric threshold value is required")
    return values


def main():
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    logit_thresholds = parse_float_list(args.logit_thresholds)
    start_confidences = parse_float_list(args.start_confidences)

    evaluate_py = Path(__file__).resolve().parents[1] / "evaluate.py"
    results = []

    for logit_threshold, start_confidence in itertools.product(logit_thresholds, start_confidences):
        run_name = f"logit_{logit_threshold:.2f}_start_{start_confidence:.2f}"
        run_dir = output_root / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            args.python_bin,
            str(evaluate_py),
            "--model-dir",
            args.model_dir,
            "--test-file",
            args.test_file,
            "--labels-file",
            args.labels_file,
            "--output-dir",
            str(run_dir),
            "--max-length",
            str(args.max_length),
            "--logit-threshold",
            str(logit_threshold),
            "--start-confidence",
            str(start_confidence),
            "--device",
            args.device,
        ]
        print(f"[sweep] evaluating logit_threshold={logit_threshold} start_confidence={start_confidence}")
        subprocess.run(cmd, check=True)

        with open(run_dir / "global_metrics.json", "r", encoding="utf-8") as f:
            metrics = json.load(f)
        results.append(
            {
                "logit_threshold": logit_threshold,
                "start_confidence": start_confidence,
                "Precision": metrics["Precision"],
                "Recall": metrics["Recall"],
                "F1": metrics["F1"],
                "Accuracy": metrics["Accuracy"],
                "run_dir": str(run_dir),
            }
        )

    results.sort(key=lambda row: (-row["F1"], -row["Precision"], -row["Recall"]))

    summary_csv = output_root / "threshold_sweep_summary.csv"
    with open(summary_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "logit_threshold",
                "start_confidence",
                "Precision",
                "Recall",
                "F1",
                "Accuracy",
                "run_dir",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    summary_json = output_root / "threshold_sweep_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    if results:
        best = results[0]
        print("[sweep] best configuration")
        print(json.dumps(best, indent=2))
        print(f"[sweep] summary_csv={summary_csv}")
        print(f"[sweep] summary_json={summary_json}")


if __name__ == "__main__":
    main()
