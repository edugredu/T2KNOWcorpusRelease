#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str, tags):
    boundaries = {0, len(text)}
    for m in TOKEN_RE.finditer(text):
        boundaries.add(m.start())
        boundaries.add(m.end())
    for tag in tags:
        boundaries.add(tag["start"])
        boundaries.add(tag["end"])

    sorted_bounds = sorted(boundaries)
    tokens = []
    for start, end in zip(sorted_bounds, sorted_bounds[1:]):
        chunk = text[start:end]
        if chunk and not chunk.isspace():
            tokens.append({"text": chunk, "start": start, "end": end})
    return tokens


def convert_split(input_path: Path, output_path: Path):
    stats = Counter()
    converted = []
    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            item = json.loads(line)
            stats["sentences"] += 1
            text = item["text"]
            tokens = tokenize(text, item["tags"])
            sentence = [tok["text"] for tok in tokens]
            token_offsets = [[tok["start"], tok["end"]] for tok in tokens]
            ner = []
            for tag in item["tags"]:
                start, end, label = tag["start"], tag["end"], tag["tag"]
                idx = [i for i, tok in enumerate(tokens) if tok["start"] >= start and tok["end"] <= end]
                if not idx:
                    raise ValueError(f"No tokens aligned to span {start}-{end} in {input_path}:{line_no}")
                if tokens[idx[0]]["start"] != start or tokens[idx[-1]]["end"] != end:
                    snippet = text[start:end]
                    raise ValueError(
                        f"Span alignment failed for {input_path}:{line_no} span {start}-{end} text={snippet!r}"
                    )
                ner.append({"index": idx, "type": label})
                stats["entities"] += 1
            span_counter = Counter((tag["start"], tag["end"]) for tag in item["tags"])
            if any(v > 1 for v in span_counter.values()):
                stats["sentences_with_same_span_multilabel"] += 1
                for count in span_counter.values():
                    if count > 1:
                        stats["same_span_groups"] += 1
                        stats["same_span_extra_labels"] += count - 1
            converted.append(
                {
                    "id": item["id"],
                    "text": text,
                    "sentence": sentence,
                    "token_offsets": token_offsets,
                    "ner": ner,
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False)
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    mapping = {
        "trainData.json": "train.json",
        "evalData.json": "dev.json",
        "testData.json": "test.json",
    }
    summary = {}
    for src, dst in mapping.items():
        stats = convert_split(input_dir / src, output_dir / dst)
        summary[dst] = dict(stats)

    with (output_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
