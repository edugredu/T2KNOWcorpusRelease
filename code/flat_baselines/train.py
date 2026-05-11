import argparse
import json
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer, DefaultDataCollator, Trainer, TrainingArguments

from common import build_bio_label_maps, load_json_dataset, load_label_list, set_seed, tokenize_and_adjust_labels_builder
from modeling import build_model


def compute_pos_weight(tokenized_dataset, id2label: dict[int, str], cap: float = 50.0):
    total_valid_tokens = 0.0
    positive_counts = np.zeros(len(id2label), dtype=np.float64)
    for row in tokenized_dataset:
        labels = np.asarray(row["labels"], dtype=np.float64)
        mask = np.asarray(row["loss_mask"], dtype=np.float64)
        total_valid_tokens += mask.sum()
        positive_counts += (labels * mask[:, None]).sum(axis=0)

    pos_weight = np.ones(len(id2label), dtype=np.float32)
    stats = {
        "total_valid_tokens": float(total_valid_tokens),
        "per_label_positive_counts": {},
        "per_label_pos_weight": {},
    }
    for idx in range(1, len(id2label)):
        label_name = id2label[idx]
        positives = float(positive_counts[idx])
        stats["per_label_positive_counts"][label_name] = positives
        if positives > 0:
            negatives = total_valid_tokens - positives
            weight = max(1.0, min(cap, negatives / positives))
        else:
            weight = 1.0
        pos_weight[idx] = weight
        stats["per_label_pos_weight"][label_name] = float(weight)
    return pos_weight, stats


def parse_args():
    parser = argparse.ArgumentParser(description="Train a flat biomedical multilabel token classifier for T2KNOW")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--train-file", default="T2KNOWcorpus/trainData.json")
    parser.add_argument("--eval-file", default="T2KNOWcorpus/evalData.json")
    parser.add_argument("--labels-file", default="code/flat_baselines/labels.txt")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-epochs", type=int, default=10)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--logging-steps", type=int, default=100)
    parser.add_argument("--save-total-limit", type=int, default=2)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--save-strategy", default="epoch", choices=["no", "epoch", "steps"])
    parser.add_argument("--eval-strategy", default="epoch", choices=["no", "epoch", "steps"])
    parser.add_argument("--pos-weight-cap", type=float, default=50.0)
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)
    with open(out_dir / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=2, sort_keys=True)

    labels = load_label_list(args.labels_file)
    _, id2label, label2id = build_bio_label_maps(labels)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenize = tokenize_and_adjust_labels_builder(tokenizer, label2id, args.max_length)

    train_ds = load_json_dataset(args.train_file)
    eval_ds = load_json_dataset(args.eval_file)
    tokenized_train = train_ds.map(tokenize, remove_columns=train_ds.column_names)
    tokenized_eval = eval_ds.map(tokenize, remove_columns=eval_ds.column_names)

    model = build_model(args.model_name, id2label=id2label, label2id=label2id)
    pos_weight, pos_weight_stats = compute_pos_weight(tokenized_train, id2label, cap=args.pos_weight_cap)
    model.set_pos_weight(np.asarray(pos_weight))
    with open(out_dir / "label_balance.json", "w", encoding="utf-8") as f:
        json.dump(pos_weight_stats, f, indent=2, sort_keys=True)

    data_collator = DefaultDataCollator()
    training_args = TrainingArguments(
        output_dir=str(out_dir / "checkpoints"),
        eval_strategy=args.eval_strategy,
        save_strategy=args.save_strategy,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.num_epochs,
        weight_decay=args.weight_decay,
        logging_steps=args.logging_steps,
        save_total_limit=args.save_total_limit,
        load_best_model_at_end=args.eval_strategy != "no" and args.save_strategy != "no",
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        seed=args.seed,
        fp16=args.fp16,
        bf16=args.bf16,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    train_result = trainer.train()
    trainer.save_model(str(out_dir / "model"))
    tokenizer.save_pretrained(str(out_dir / "model"))

    metrics = {f"train_{k}": v for k, v in train_result.metrics.items()}
    if args.eval_strategy != "no":
        eval_metrics = trainer.evaluate()
        metrics.update({f"eval_{k}": v for k, v in eval_metrics.items()})

    with open(out_dir / "train_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
    trainer.state.save_to_json(str(out_dir / "trainer_state.json"))


if __name__ == "__main__":
    main()
