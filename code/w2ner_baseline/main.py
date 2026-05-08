import argparse
import json
import os
import random

import numpy as np
try:
    import prettytable as pt
except ImportError:  # pragma: no cover
    class _SimpleTable:
        def __init__(self, fields):
            self.fields = fields
            self.rows = []

        def add_row(self, row):
            self.rows.append(row)

        def __str__(self):
            lines = [" | ".join(map(str, self.fields))]
            lines.extend(" | ".join(map(str, row)) for row in self.rows)
            return "\n".join(lines)

    class pt:  # type: ignore
        PrettyTable = _SimpleTable
import torch
import torch.nn as nn
import torch.optim as optim
import transformers
from torch.utils.data import DataLoader

import config
import data_loader
import utils
from model import Model
from t2know_eval.metrics import compute_metrics


class Trainer:
    def __init__(self, model, cfg, updates_total):
        self.model = model
        self.cfg = cfg
        pos_weight = torch.tensor(cfg.pos_weight, dtype=torch.float32, device="cuda" if torch.cuda.is_available() else "cpu")
        self.criterion = nn.BCEWithLogitsLoss(reduction="none", pos_weight=pos_weight)

        bert_params = set(self.model.bert.parameters())
        other_params = list(set(self.model.parameters()) - bert_params)
        no_decay = ["bias", "LayerNorm.weight"]
        params = [
            {
                "params": [p for n, p in model.bert.named_parameters() if not any(nd in n for nd in no_decay)],
                "lr": cfg.bert_learning_rate,
                "weight_decay": cfg.weight_decay,
            },
            {
                "params": [p for n, p in model.bert.named_parameters() if any(nd in n for nd in no_decay)],
                "lr": cfg.bert_learning_rate,
                "weight_decay": 0.0,
            },
            {"params": other_params, "lr": cfg.learning_rate, "weight_decay": cfg.weight_decay},
        ]
        self.optimizer = optim.AdamW(params, lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
        self.scheduler = transformers.get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=max(1, int(cfg.warm_factor * updates_total)),
            num_training_steps=max(1, updates_total),
        )

    def _forward_loss(self, batch):
        bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length = batch
        outputs = self.model(bert_inputs, grid_mask2d, dist_inputs, pieces2word, sent_length)
        mask = grid_mask2d.unsqueeze(-1).expand_as(grid_labels)
        loss = self.criterion(outputs, grid_labels)
        loss = loss.masked_select(mask).mean()
        return outputs, loss

    def train_epoch(self, epoch, loader):
        self.model.train()
        loss_list = []
        for data_batch in loader:
            entity_text = data_batch[-1]
            del entity_text
            tensors = [x.cuda() if torch.cuda.is_available() else x for x in data_batch[:-1]]
            _, loss = self._forward_loss(tensors)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.clip_grad_norm)
            self.optimizer.step()
            self.scheduler.step()
            self.optimizer.zero_grad()
            loss_list.append(float(loss.detach().cpu()))
        table = pt.PrettyTable([f"Train {epoch}", "Loss"])
        table.add_row(["Grid", f"{np.mean(loss_list):.4f}"])
        self.cfg.logger.info("\n%s", table)
        return float(np.mean(loss_list))

    def eval_epoch(self, epoch, loader, split_name="DEV"):
        self.model.eval()
        losses = []
        total_ent_r = total_ent_p = total_ent_c = 0
        with torch.no_grad():
            for data_batch in loader:
                entity_text = data_batch[-1]
                tensors = [x.cuda() if torch.cuda.is_available() else x for x in data_batch[:-1]]
                outputs, loss = self._forward_loss(tensors)
                losses.append(float(loss.detach().cpu()))
                probs = torch.sigmoid(outputs).detach().cpu().numpy()
                length = tensors[5].detach().cpu().numpy()
                ent_c, ent_p, ent_r, _ = utils.decode(
                    probs,
                    entity_text,
                    length,
                    nnw_threshold=self.cfg.nnw_threshold,
                    thw_threshold=self.cfg.thw_threshold,
                )
                total_ent_r += ent_r
                total_ent_p += ent_p
                total_ent_c += ent_c
        e_f1, e_p, e_r = utils.cal_f1(total_ent_c, total_ent_p, total_ent_r)
        table = pt.PrettyTable([f"{split_name} {epoch}", "Loss", "F1", "Precision", "Recall"])
        table.add_row(["Entity", f"{np.mean(losses):.4f}", f"{e_f1:.4f}", f"{e_p:.4f}", f"{e_r:.4f}"])
        self.cfg.logger.info("\n%s", table)
        return {"loss": float(np.mean(losses)), "f1": e_f1, "precision": e_p, "recall": e_r}

    def save(self, path):
        torch.save(self.model.state_dict(), path)

    def load(self, path):
        self.model.load_state_dict(torch.load(path, map_location="cuda" if torch.cuda.is_available() else "cpu"))


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def build_t2know_rows(decoded_entities, raw_batch, vocab):
    pred_rows = []
    gold_rows = []
    for decoded, raw in zip(decoded_entities, raw_batch):
        pred_entities = []
        for indices, type_id in decoded:
            offsets = raw["token_offsets"]
            start = offsets[indices[0]][0]
            end = offsets[indices[-1]][1]
            pred_entities.append({"start": start, "end": end, "label": vocab.id_to_label(type_id)})
        gold_entities = []
        for ent in raw.get("ner", []):
            offsets = raw["token_offsets"]
            start = offsets[ent["index"][0]][0]
            end = offsets[ent["index"][-1]][1]
            gold_entities.append({"start": start, "end": end, "label": ent["type"]})
        pred_rows.append({"text": raw["text"], "entities": pred_entities})
        gold_rows.append({"text": raw["text"], "entities": gold_entities})
    return pred_rows, gold_rows


def evaluate_and_export(model, cfg, loader, raw_data):
    os.makedirs(cfg.eval_dir, exist_ok=True)
    model.eval()
    pred_rows = []
    gold_rows = []
    offset = 0
    with torch.no_grad():
        for data_batch in loader:
            batch_size = len(data_batch[-1])
            raw_batch = raw_data[offset: offset + batch_size]
            offset += batch_size
            entity_text = data_batch[-1]
            tensors = [x.cuda() if torch.cuda.is_available() else x for x in data_batch[:-1]]
            bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length = tensors
            del grid_labels
            outputs = model(bert_inputs, grid_mask2d, dist_inputs, pieces2word, sent_length)
            probs = torch.sigmoid(outputs).detach().cpu().numpy()
            length = sent_length.detach().cpu().numpy()
            _, _, _, decoded = utils.decode(
                probs,
                entity_text,
                length,
                nnw_threshold=cfg.nnw_threshold,
                thw_threshold=cfg.thw_threshold,
            )
            batch_pred, batch_gold = build_t2know_rows(decoded, raw_batch, cfg.vocab)
            pred_rows.extend(batch_pred)
            gold_rows.extend(batch_gold)

    utils.write_jsonl(cfg.predict_path, pred_rows)
    utils.write_jsonl(cfg.gold_path, gold_rows)

    labels = [cfg.vocab.id_to_label(i) for i in sorted(cfg.vocab.id2label) if i > 1]
    df_metrics, global_metrics = compute_metrics(gold_rows, pred_rows, labels=labels)
    df_metrics.to_csv(cfg.metrics_csv)
    with open(cfg.global_metrics_path, "w", encoding="utf-8") as f:
        json.dump(global_metrics, f, indent=2)
    with open(cfg.summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model": cfg.bert_name,
                "dataset": cfg.dataset,
                "nnw_threshold": cfg.nnw_threshold,
                "thw_threshold": cfg.thw_threshold,
                "global_metrics": global_metrics,
            },
            f,
            indent=2,
        )
    cfg.logger.info("Final t2know_eval metrics: %s", global_metrics)
    return global_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--eval_only", action="store_true")
    parser.add_argument("--model_path", type=str)
    parser.add_argument("--eval_split", choices=["dev", "test"], default="test")
    parser.add_argument("--output_dir", type=str)
    parser.add_argument("--data_dir", type=str)
    parser.add_argument("--bert_name", type=str)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch_size", type=int)
    parser.add_argument("--learning_rate", type=float)
    parser.add_argument("--weight_decay", type=float)
    parser.add_argument("--bert_learning_rate", type=float)
    parser.add_argument("--warm_factor", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--nnw_threshold", type=float)
    parser.add_argument("--thw_threshold", type=float)
    parser.add_argument("--num_workers", type=int)
    args = parser.parse_args()

    cfg = config.Config(args)
    os.makedirs(cfg.output_dir, exist_ok=True)
    os.makedirs(cfg.eval_dir, exist_ok=True)
    logger = utils.get_logger(cfg.output_dir, cfg.dataset)
    cfg.logger = logger
    logger.info(cfg)

    if torch.cuda.is_available():
        torch.cuda.set_device(args.device)
    set_seed(cfg.seed)

    logger.info("Loading data")
    datasets, raw_data = data_loader.load_data_bert(cfg)
    train_loader, dev_loader, test_loader = (
        DataLoader(
            dataset=dataset,
            batch_size=cfg.batch_size,
            collate_fn=data_loader.collate_fn,
            shuffle=i == 0,
            num_workers=cfg.num_workers,
            drop_last=i == 0,
        )
        for i, dataset in enumerate(datasets)
    )

    updates_total = max(1, len(train_loader) * cfg.epochs)
    logger.info("Building model")
    model = Model(cfg)
    if torch.cuda.is_available():
        model = model.cuda()

    if args.eval_only:
        model_path = args.model_path or cfg.save_path
        logger.info("Eval-only mode using checkpoint: %s", model_path)
        state = torch.load(model_path, map_location="cuda" if torch.cuda.is_available() else "cpu")
        model.load_state_dict(state)
        if args.eval_split == "dev":
            eval_loader = dev_loader
            eval_raw = raw_data[1]
        else:
            eval_loader = test_loader
            eval_raw = raw_data[2]
        completed_metrics = evaluate_and_export(model, cfg, eval_loader, eval_raw)
        logger.info("Saved final metrics to %s", cfg.global_metrics_path)
        logger.info("Done: %s", completed_metrics)
        return

    trainer = Trainer(model, cfg, updates_total)

    best_dev_f1 = -1.0
    best_test = None
    history = []
    for epoch in range(cfg.epochs):
        logger.info("Epoch: %s", epoch)
        train_loss = trainer.train_epoch(epoch, train_loader)
        dev_metrics = trainer.eval_epoch(epoch, dev_loader, split_name="DEV")
        test_metrics = trainer.eval_epoch(epoch, test_loader, split_name="TEST")
        history.append({"epoch": epoch, "train_loss": train_loss, "dev": dev_metrics, "test": test_metrics})
        if dev_metrics["f1"] > best_dev_f1:
            best_dev_f1 = dev_metrics["f1"]
            best_test = test_metrics
            trainer.save(cfg.save_path)

    logger.info("Best DEV F1: %.4f", best_dev_f1)
    logger.info("Best TEST F1 at best DEV checkpoint: %s", best_test)

    with open(os.path.join(cfg.output_dir, "train_history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    trainer.load(cfg.save_path)
    completed_metrics = evaluate_and_export(model, cfg, test_loader, raw_data[-1])
    logger.info("Saved final metrics to %s", cfg.global_metrics_path)
    logger.info("Done: %s", completed_metrics)


if __name__ == "__main__":
    main()
