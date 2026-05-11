import argparse
import json
from pathlib import Path

import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze tokenized length distribution for T2KNOW datasets.')
    parser.add_argument('--model-name', required=True)
    parser.add_argument('--files', nargs='+', required=True)
    parser.add_argument('--thresholds', nargs='*', type=int, default=[128, 256, 384, 512])
    parser.add_argument('--output', default='code/flat_baselines/analysis/length_summary.json')
    return parser.parse_args()


def summarize_lengths(tokenizer, dataset_path):
    ds = Dataset.from_json(dataset_path)
    lengths = []
    for sample in ds:
        encoded = tokenizer(sample['text'], truncation=False)
        lengths.append(len(encoded['input_ids']))
    arr = np.array(lengths, dtype=np.int32)
    return {
        'count': int(arr.size),
        'min': int(arr.min()) if arr.size else 0,
        'max': int(arr.max()) if arr.size else 0,
        'mean': float(arr.mean()) if arr.size else 0.0,
        'p50': int(np.percentile(arr, 50)) if arr.size else 0,
        'p90': int(np.percentile(arr, 90)) if arr.size else 0,
        'p95': int(np.percentile(arr, 95)) if arr.size else 0,
        'p99': int(np.percentile(arr, 99)) if arr.size else 0,
        'lengths': lengths,
    }


def main():
    args = parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    output = {'model_name': args.model_name, 'files': {}}
    all_lengths = []
    for path in args.files:
        summary = summarize_lengths(tokenizer, path)
        output['files'][path] = {k: v for k, v in summary.items() if k != 'lengths'}
        all_lengths.extend(summary['lengths'])

    all_arr = np.array(all_lengths, dtype=np.int32)
    overall = {
        'count': int(all_arr.size),
        'min': int(all_arr.min()) if all_arr.size else 0,
        'max': int(all_arr.max()) if all_arr.size else 0,
        'mean': float(all_arr.mean()) if all_arr.size else 0.0,
        'p50': int(np.percentile(all_arr, 50)) if all_arr.size else 0,
        'p90': int(np.percentile(all_arr, 90)) if all_arr.size else 0,
        'p95': int(np.percentile(all_arr, 95)) if all_arr.size else 0,
        'p99': int(np.percentile(all_arr, 99)) if all_arr.size else 0,
        'coverage': {},
    }
    for threshold in args.thresholds:
        overall['coverage'][str(threshold)] = float((all_arr <= threshold).mean()) if all_arr.size else 0.0
    output['overall'] = overall

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, sort_keys=True)

    print(json.dumps(output['overall'], indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
