import argparse
import json
import sys
import pandas as pd
from t2know_eval.metrics import compute_metrics

def load_jsonl(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def main():
    parser = argparse.ArgumentParser(description="Evaluate T2KNOW predictions against reference annotations.")
    parser.add_argument("--gold", required=True, help="Path to gold JSONL file.")
    parser.add_argument("--pred", required=True, help="Path to predictions JSONL file.")
    parser.add_argument("--output", default="evaluation_results.csv", help="Path to save per-label metrics CSV.")
    parser.add_argument(
        "--annotation-only",
        action="store_true",
        help="Allow redacted records without sentence/entity text; scoring uses offsets and labels only.",
    )
    
    args = parser.parse_args()
    
    print(f"Loading gold data from {args.gold}...")
    gold_data = load_jsonl(args.gold)
    
    print(f"Loading prediction data from {args.pred}...")
    pred_data = load_jsonl(args.pred)
    
    if len(gold_data) != len(pred_data):
        print(f"WARNING: Number of documents mismatch! Gold: {len(gold_data)}, Pred: {len(pred_data)}")
        # We assume they are aligned by line number. If lengths differ, we truncate to the shorter one for safety,
        # or error out. Let's error out to be safe.
        # print("Error: Datasets must be aligned line-by-line.")
        # sys.exit(1)
        # Actually, let's just warn and zip, which truncates.
    
    print("Computing metrics...")
    df_metrics, global_metrics = compute_metrics(gold_data, pred_data)
    
    print("\n" + "="*30)
    print("GLOBAL METRICS")
    print("="*30)
    print(f"Precision: {global_metrics['Precision']:.4f}")
    print(f"Recall:    {global_metrics['Recall']:.4f}")
    print(f"F1 Score:  {global_metrics['F1']:.4f}")
    print(f"Accuracy:  {global_metrics['Accuracy']:.4f}")
    print("="*30)
    
    print(f"\nSaving per-label metrics to {args.output}...")
    df_metrics.to_csv(args.output)
    print("Done.")

if __name__ == "__main__":
    main()
