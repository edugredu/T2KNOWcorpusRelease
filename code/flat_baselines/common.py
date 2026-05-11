import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from datasets import Dataset

MAX_LENGTH_DEFAULT = 512


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_label_list(labels_path: str) -> List[str]:
    with open(labels_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def build_bio_label_maps(base_labels: List[str]) -> Tuple[Dict[str, int], Dict[int, str], Dict[str, int]]:
    id2label = {0: "O"}
    idx = 1
    for label in base_labels:
        id2label[idx] = f"B-{label}"
        id2label[idx + 1] = f"I-{label}"
        idx += 2
    label2id = {label: idx for idx, label in id2label.items()}
    base_tag_to_id = {"O": 0}
    for idx, label in enumerate(base_labels, start=1):
        base_tag_to_id[label] = idx
    return base_tag_to_id, id2label, label2id


def load_json_dataset(path: str) -> Dataset:
    return Dataset.from_json(path)


def read_jsonl_records(path: str) -> List[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl_records(path: str, records: List[dict]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_token_role_in_span(token_start: int, token_end: int, span_start: int, span_end: int) -> str:
    if token_end <= token_start:
        return "N"
    if token_start < span_start or token_end > span_end:
        return "O"
    if token_start > span_start:
        return "I"
    return "B"


def tokenize_and_adjust_labels_builder(tokenizer, label2id: Dict[str, int], max_length: int = MAX_LENGTH_DEFAULT):
    def tokenize_and_adjust_labels(sample: dict) -> dict:
        tokenized = tokenizer(
            sample["text"],
            return_offsets_mapping=True,
            padding="max_length",
            truncation=True,
            max_length=max_length,
        )

        labels = [[0 for _ in range(len(label2id))] for _ in range(max_length)]
        loss_mask = []
        for (token_start, token_end), token_labels in zip(tokenized["offset_mapping"], labels):
            loss_mask.append(1 if token_end > token_start else 0)
            for span in sample["tags"]:
                role = get_token_role_in_span(token_start, token_end, span["start"], span["end"])
                if role == "B":
                    token_labels[label2id[f"B-{span['tag']}"]] = 1
                elif role == "I":
                    token_labels[label2id[f"I-{span['tag']}"]] = 1
        tokenized["labels"] = labels
        tokenized["loss_mask"] = loss_mask
        tokenized.pop("offset_mapping", None)
        return tokenized

    return tokenize_and_adjust_labels


def json_sample_to_eval_record(sample: dict, entities: List[dict] | None = None) -> dict:
    if entities is None:
        entities = [{"start": tag["start"], "end": tag["end"], "label": tag["tag"]} for tag in sample.get("tags", [])]
    return {
        "id": sample["id"],
        "text": sample["text"],
        "entities": entities,
    }
