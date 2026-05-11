import argparse
import json
import sys
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoConfig, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import build_bio_label_maps, json_sample_to_eval_record, load_json_dataset, load_label_list, write_jsonl_records
from modeling import BertForSpanClassification
from t2know_eval.metrics import compute_metrics


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained T2KNOW flat biomedical baseline")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--test-file", default="T2KNOWcorpus/testData.json")
    parser.add_argument("--labels-file", default="code/flat_baselines/labels.txt")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--logit-threshold", type=float, default=0.0)
    parser.add_argument("--start-confidence", type=float, default=0.5)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def decode_entities(token_results, id2label, start_confidence):
    predicted_offsets = {}
    deleted_tags = set()
    last_token_tags = set()

    for item in token_results:
        start, end = item["offset"]
        tags = item["tags"]
        probs = item["probs"]
        if end <= start:
            last_token_tags = set(tags)
            continue

        for tag in list(deleted_tags):
            if item["i_tag_ids"].get(tag) not in tags:
                deleted_tags.remove(tag)

        for label_id in tags:
            label_name = id2label[label_id]
            if label_name == "O":
                continue
            prefix, base_tag = label_name.split("-", 1)
            predicted_offsets.setdefault(base_tag, [])
            if prefix == "B":
                if probs[label_id] >= start_confidence:
                    predicted_offsets[base_tag].append({"start": start, "end": end, "label": base_tag})
                else:
                    deleted_tags.add(base_tag)
            elif prefix == "I":
                if base_tag in deleted_tags:
                    continue
                b_id = item["b_tag_ids"].get(base_tag)
                if label_id not in last_token_tags and b_id not in last_token_tags:
                    predicted_offsets[base_tag].append({"start": start, "end": end, "label": base_tag})
                elif predicted_offsets[base_tag]:
                    predicted_offsets[base_tag][-1]["end"] = end
                else:
                    predicted_offsets[base_tag].append({"start": start, "end": end, "label": base_tag})
        last_token_tags = set(tags)

    entities = []
    for base_tag, spans in predicted_offsets.items():
        for span in spans:
            if span["end"] - span["start"] < 1:
                continue
            entities.append(span)
    entities.sort(key=lambda row: (row["start"], row["end"], row["label"]))
    return entities


def predict_entities(model, tokenizer, sample, id2label, logit_threshold, start_confidence, max_length, device):
    encoded = tokenizer(
        sample["text"],
        return_offsets_mapping=True,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    offset_mapping = encoded.pop("offset_mapping")[0].tolist()
    encoded = {k: v.to(device) for k, v in encoded.items()}

    with torch.no_grad():
        logits = model(**encoded).logits[0]
    raw_logits = logits.detach().cpu()
    confidences = torch.sigmoid(raw_logits)
    predicted_tags = [[idx for idx, score in enumerate(row.tolist()) if score > logit_threshold] for row in raw_logits]

    b_tag_ids = {}
    i_tag_ids = {}
    for idx, label in id2label.items():
        if label.startswith("B-"):
            b_tag_ids[label[2:]] = idx
        elif label.startswith("I-"):
            i_tag_ids[label[2:]] = idx

    token_results = []
    for offset, tags, row_probs in zip(offset_mapping, predicted_tags, confidences.tolist()):
        token_results.append(
            {
                "offset": offset,
                "tags": tags,
                "probs": row_probs,
                "b_tag_ids": b_tag_ids,
                "i_tag_ids": i_tag_ids,
            }
        )
    return decode_entities(token_results, id2label, start_confidence)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = load_label_list(args.labels_file)
    _, id2label, _ = build_bio_label_maps(labels)

    config = AutoConfig.from_pretrained(args.model_dir)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = BertForSpanClassification.from_pretrained(args.model_dir, config=config).to(args.device)
    model.eval()

    test_ds = load_json_dataset(args.test_file)
    test_records = [dict(row) for row in test_ds]

    pred_records = []
    gold_records = []
    for sample in tqdm(test_records, desc="Evaluating"):
        entities = predict_entities(
            model,
            tokenizer,
            sample,
            id2label,
            args.logit_threshold,
            args.start_confidence,
            args.max_length,
            args.device,
        )
        pred_records.append(json_sample_to_eval_record(sample, entities=entities))
        gold_records.append(json_sample_to_eval_record(sample))

    pred_path = output_dir / "pred.jsonl"
    gold_path = output_dir / "gold.jsonl"
    write_jsonl_records(pred_path, pred_records)
    write_jsonl_records(gold_path, gold_records)

    df_metrics, global_metrics = compute_metrics(gold_records, pred_records)
    df_metrics.to_csv(output_dir / "per_label_metrics.csv")
    with open(output_dir / "global_metrics.json", "w", encoding="utf-8") as f:
        json.dump(global_metrics, f, indent=2, sort_keys=True)

    summary = {
        "test_file": args.test_file,
        "model_dir": args.model_dir,
        "logit_threshold": args.logit_threshold,
        "start_confidence": args.start_confidence,
        "global_metrics": global_metrics,
        "prediction_count": len(pred_records),
    }
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print("Global metrics")
    for key in ["Precision", "Recall", "F1", "Accuracy"]:
        print(f"{key}: {global_metrics[key]:.4f}")


if __name__ == "__main__":
    main()
