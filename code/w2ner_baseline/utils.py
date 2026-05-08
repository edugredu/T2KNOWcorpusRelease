import json
import logging
import os
import pickle
import time
from collections import defaultdict, deque


def get_logger(output_dir, dataset):
    os.makedirs(output_dir, exist_ok=True)
    pathname = os.path.join(output_dir, f"{dataset}_{time.strftime('%m-%d_%H-%M-%S')}.log")
    logger = logging.getLogger(f"w2ner_{dataset}_{time.time()}")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(pathname)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def save_file(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


def load_file(path):
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data


def convert_index_to_text(index, type_id):
    return "-".join(str(i) for i in index) + f"-#-{type_id}"


def convert_text_to_index(text):
    index, type_id = text.split("-#-")
    return [int(x) for x in index.split("-")], int(type_id)


def decode(prob_outputs, entities, length, nnw_threshold=0.5, thw_threshold=0.5):
    class Node:
        def __init__(self):
            self.THW = []
            self.NNW = defaultdict(set)

    ent_r, ent_p, ent_c = 0, 0, 0
    decode_entities = []
    q = deque()

    for instance, ent_set, l in zip(prob_outputs, entities, length):
        predicts = []
        nodes = [Node() for _ in range(l)]
        for cur in reversed(range(l)):
            heads = []
            for pre in range(cur + 1):
                thw_types = [i for i, score in enumerate(instance[cur, pre]) if i > 1 and score > thw_threshold]
                if thw_types:
                    heads.append(pre)
                    for type_id in thw_types:
                        nodes[pre].THW.append((cur, type_id))

                if pre < cur and instance[pre, cur, 1] > nnw_threshold:
                    for head in heads:
                        nodes[pre].NNW[(head, cur)].add(cur)
                    for head, tail in list(nodes[cur].NNW.keys()):
                        if tail >= cur and head <= pre:
                            nodes[pre].NNW[(head, tail)].add(cur)

            for tail, type_id in nodes[cur].THW:
                if cur == tail:
                    predicts.append(([cur], type_id))
                    continue
                q.clear()
                q.append([cur])
                while q:
                    chains = q.pop()
                    for idx in nodes[chains[-1]].NNW[(cur, tail)]:
                        if idx == tail:
                            predicts.append((chains + [idx], type_id))
                        else:
                            q.append(chains + [idx])

        predicts = set(convert_index_to_text(x[0], x[1]) for x in predicts)
        decode_entities.append([convert_text_to_index(x) for x in predicts])
        ent_r += len(ent_set)
        ent_p += len(predicts)
        ent_c += len(predicts.intersection(ent_set))
    return ent_c, ent_p, ent_r, decode_entities


def cal_f1(c, p, r):
    if r == 0 or p == 0:
        return 0.0, 0.0, 0.0
    recall = c / r if r else 0.0
    precision = c / p if p else 0.0
    if recall and precision:
        return 2 * precision * recall / (precision + recall), precision, recall
    return 0.0, precision, recall


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
