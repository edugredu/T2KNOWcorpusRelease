import json
import os
from typing import List

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
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset
from transformers import AutoTokenizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

dis2idx = np.zeros((1000), dtype="int64")
dis2idx[1] = 1
dis2idx[2:] = 2
dis2idx[4:] = 3
dis2idx[8:] = 4
dis2idx[16:] = 5
dis2idx[32:] = 6
dis2idx[64:] = 7
dis2idx[128:] = 8
dis2idx[256:] = 9


class Vocabulary:
    PAD = "<pad>"
    SUC = "<suc>"

    def __init__(self):
        self.label2id = {self.PAD: 0, self.SUC: 1}
        self.id2label = {0: self.PAD, 1: self.SUC}

    def add_label(self, label: str):
        key = label.lower()
        if key not in self.label2id:
            idx = len(self.label2id)
            self.label2id[key] = idx
            self.id2label[idx] = label

    def label_to_id(self, label: str) -> int:
        return self.label2id[label.lower()]

    def id_to_label(self, idx: int) -> str:
        return self.id2label[idx]


def collate_fn(data):
    bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length, entity_text = map(list, zip(*data))

    max_tok = int(np.max(sent_length))
    sent_length = torch.LongTensor(sent_length)
    max_pie = int(np.max([x.shape[0] for x in bert_inputs]))
    max_cls = grid_labels[0].shape[-1]
    bert_inputs = pad_sequence(bert_inputs, True)
    batch_size = bert_inputs.size(0)

    def fill_2d(source, target):
        for j, x in enumerate(source):
            target[j, : x.shape[0], : x.shape[1]] = x
        return target

    def fill_3d(source, target):
        for j, x in enumerate(source):
            target[j, : x.shape[0], : x.shape[1], : x.shape[2]] = x
        return target

    dis_mat = torch.zeros((batch_size, max_tok, max_tok), dtype=torch.long)
    dist_inputs = fill_2d(dist_inputs, dis_mat)

    labels_mat = torch.zeros((batch_size, max_tok, max_tok, max_cls), dtype=torch.float)
    grid_labels = fill_3d(grid_labels, labels_mat)

    mask2d_mat = torch.zeros((batch_size, max_tok, max_tok), dtype=torch.bool)
    grid_mask2d = fill_2d(grid_mask2d, mask2d_mat)

    sub_mat = torch.zeros((batch_size, max_tok, max_pie), dtype=torch.bool)
    pieces2word = fill_2d(pieces2word, sub_mat)

    return bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length, entity_text


class RelationDataset(Dataset):
    def __init__(self, bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length, entity_text):
        self.bert_inputs = bert_inputs
        self.grid_labels = grid_labels
        self.grid_mask2d = grid_mask2d
        self.pieces2word = pieces2word
        self.dist_inputs = dist_inputs
        self.sent_length = sent_length
        self.entity_text = entity_text

    def __getitem__(self, item):
        return (
            torch.LongTensor(self.bert_inputs[item]),
            torch.FloatTensor(self.grid_labels[item]),
            torch.BoolTensor(self.grid_mask2d[item]),
            torch.BoolTensor(self.pieces2word[item]),
            torch.LongTensor(self.dist_inputs[item]),
            self.sent_length[item],
            self.entity_text[item],
        )

    def __len__(self):
        return len(self.bert_inputs)


def process_bert(data: List[dict], tokenizer, vocab):
    bert_inputs = []
    grid_labels = []
    grid_mask2d = []
    dist_inputs = []
    entity_text = []
    pieces2word = []
    sent_length = []

    label_num = len(vocab.label2id)

    for instance in data:
        if not instance["sentence"]:
            continue

        tokens = [tokenizer.tokenize(word) for word in instance["sentence"]]
        pieces = [piece for token_pieces in tokens for piece in token_pieces]
        bert_ids = tokenizer.convert_tokens_to_ids(pieces)
        bert_ids = np.array([tokenizer.cls_token_id] + bert_ids + [tokenizer.sep_token_id])

        length = len(instance["sentence"])
        grid = np.zeros((length, length, label_num), dtype=np.float32)
        p2w = np.zeros((length, len(bert_ids)), dtype=bool)
        dist = np.zeros((length, length), dtype=np.int64)
        mask = np.ones((length, length), dtype=bool)

        start = 0
        for i, token_pieces in enumerate(tokens):
            if not token_pieces:
                continue
            piece_range = list(range(start, start + len(token_pieces)))
            p2w[i, piece_range[0] + 1 : piece_range[-1] + 2] = True
            start += len(piece_range)

        for k in range(length):
            dist[k, :] += k
            dist[:, k] -= k

        for i in range(length):
            for j in range(length):
                idx = abs(dist[i, j])
                idx = idx if idx < len(dis2idx) else len(dis2idx) - 1
                if dist[i, j] < 0:
                    dist[i, j] = dis2idx[idx] + 9
                else:
                    dist[i, j] = dis2idx[idx]
        dist[dist == 0] = 19

        for entity in instance["ner"]:
            index = entity["index"]
            for i in range(len(index) - 1):
                grid[index[i], index[i + 1], 1] = 1.0
            grid[index[-1], index[0], vocab.label_to_id(entity["type"])] = 1.0

        entity_repr = {
            f"{'-'.join(str(i) for i in e['index'])}-#-{vocab.label_to_id(e['type'])}"
            for e in instance["ner"]
        }

        sent_length.append(length)
        bert_inputs.append(bert_ids)
        grid_labels.append(grid)
        grid_mask2d.append(mask)
        dist_inputs.append(dist)
        pieces2word.append(p2w)
        entity_text.append(entity_repr)

    return bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length, entity_text


def fill_vocab(vocab, dataset):
    entity_num = 0
    for instance in dataset:
        for entity in instance["ner"]:
            vocab.add_label(entity["type"])
        entity_num += len(instance["ner"])
    return entity_num


def _compute_pos_weight(grid_labels, sent_length, label_num, max_pos_weight):
    positives = np.zeros(label_num, dtype=np.float64)
    valid_cells = 0
    for grid, length in zip(grid_labels, sent_length):
        positives += grid.sum(axis=(0, 1))
        valid_cells += int(length) * int(length)
    negatives = valid_cells - positives
    pos_weight = np.ones(label_num, dtype=np.float32)
    mask = positives > 0
    pos_weight[mask] = np.minimum(negatives[mask] / positives[mask], max_pos_weight)
    pos_weight[0] = 1.0
    return pos_weight


def load_data_bert(config):
    with open(os.path.join(config.data_dir, "train.json"), "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(os.path.join(config.data_dir, "dev.json"), "r", encoding="utf-8") as f:
        dev_data = json.load(f)
    with open(os.path.join(config.data_dir, "test.json"), "r", encoding="utf-8") as f:
        test_data = json.load(f)

    tokenizer = AutoTokenizer.from_pretrained(config.bert_name, cache_dir="./cache/")

    vocab = Vocabulary()
    train_ent_num = fill_vocab(vocab, train_data)
    dev_ent_num = fill_vocab(vocab, dev_data)
    test_ent_num = fill_vocab(vocab, test_data)

    table = pt.PrettyTable([config.dataset, "sentences", "entities"])
    table.add_row(["train", len(train_data), train_ent_num])
    table.add_row(["dev", len(dev_data), dev_ent_num])
    table.add_row(["test", len(test_data), test_ent_num])
    config.logger.info("\n%s", table)

    config.label_num = len(vocab.label2id)
    config.vocab = vocab

    train_processed = process_bert(train_data, tokenizer, vocab)
    dev_processed = process_bert(dev_data, tokenizer, vocab)
    test_processed = process_bert(test_data, tokenizer, vocab)

    config.pos_weight = _compute_pos_weight(train_processed[1], train_processed[5], config.label_num, config.max_pos_weight)

    train_dataset = RelationDataset(*train_processed)
    dev_dataset = RelationDataset(*dev_processed)
    test_dataset = RelationDataset(*test_processed)
    return (train_dataset, dev_dataset, test_dataset), (train_data, dev_data, test_data)
