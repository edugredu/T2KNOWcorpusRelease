import argparse
import csv
import itertools
import json
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Sweep W2NER decoding thresholds for an existing checkpoint')
    parser.add_argument('--python-bin', default=sys.executable)
    parser.add_argument('--config', required=True)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--nnw-thresholds', default='0.3,0.4,0.5,0.6,0.7')
    parser.add_argument('--thw-thresholds', default='0.3,0.4,0.5,0.6,0.7')
    parser.add_argument('--eval-split', choices=['dev', 'test'], default='dev')
    parser.add_argument('--device', default='0')
    return parser.parse_args()


def parse_float_list(raw_value: str):
    values = []
    for item in raw_value.split(','):
        item = item.strip()
        if item:
            values.append(float(item))
    if not values:
        raise ValueError('At least one numeric threshold value is required')
    return values


def main():
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    nnw_thresholds = parse_float_list(args.nnw_thresholds)
    thw_thresholds = parse_float_list(args.thw_thresholds)

    main_py = Path(__file__).resolve().parents[1] / 'main.py'
    results = []

    for nnw_threshold, thw_threshold in itertools.product(nnw_thresholds, thw_thresholds):
        run_name = f'nnw_{nnw_threshold:.2f}_thw_{thw_threshold:.2f}'
        run_dir = output_root / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            args.python_bin,
            str(main_py),
            '--config',
            args.config,
            '--eval_only',
            '--model_path',
            args.model_path,
            '--data_dir',
            args.data_dir,
            '--output_dir',
            str(run_dir),
            '--eval_split',
            args.eval_split,
            '--nnw_threshold',
            str(nnw_threshold),
            '--thw_threshold',
            str(thw_threshold),
            '--device',
            args.device,
        ]
        print(f'[sweep] evaluating nnw_threshold={nnw_threshold} thw_threshold={thw_threshold}')
        subprocess.run(cmd, check=True)

        with open(run_dir / 'eval_test' / 'global_metrics.json', 'r', encoding='utf-8') as f:
            metrics = json.load(f)
        results.append(
            {
                'nnw_threshold': nnw_threshold,
                'thw_threshold': thw_threshold,
                'Precision': metrics['Precision'],
                'Recall': metrics['Recall'],
                'F1': metrics['F1'],
                'Accuracy': metrics['Accuracy'],
                'run_dir': str(run_dir),
            }
        )

    results.sort(key=lambda row: (-row['F1'], -row['Precision'], -row['Recall']))

    summary_csv = output_root / 'threshold_sweep_summary.csv'
    with open(summary_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['nnw_threshold', 'thw_threshold', 'Precision', 'Recall', 'F1', 'Accuracy', 'run_dir'],
        )
        writer.writeheader()
        writer.writerows(results)

    summary_json = output_root / 'threshold_sweep_summary.json'
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    if results:
        best = results[0]
        print('[sweep] best configuration')
        print(json.dumps(best, indent=2))
        print(f'[sweep] summary_csv={summary_csv}')
        print(f'[sweep] summary_json={summary_json}')


if __name__ == '__main__':
    main()
