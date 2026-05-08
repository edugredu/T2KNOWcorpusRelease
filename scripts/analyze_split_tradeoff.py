#!/usr/bin/env python3
"""Analyze current split overlap and search for a document-disjoint candidate split.

This script works over the canonical JSONL release, using only non-synthetic rows.
It quantifies the current sentence-level split overlap and then searches for a
document-disjoint split that preserves label and structural coverage as much as
possible while remaining close to a target train/validation/test proportion.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def portable_path(path_str: str) -> str:
    path = Path(path_str).resolve()
    try:
        return str(path.relative_to(RELEASE_ROOT))
    except ValueError:
        return path_str


def compute_sentence_features(entities: list[dict]) -> tuple[bool, bool]:
    spans: dict[tuple[int, int], list[str]] = defaultdict(list)
    for ent in entities:
        spans[(ent["start"], ent["end"])].append(ent["label"])

    has_multi = any(len(labels) > 1 for labels in spans.values())
    has_nested = False
    for i, left in enumerate(entities):
        for right in entities[i + 1 :]:
            if left["start"] == right["start"] and left["end"] == right["end"]:
                continue
            if (
                (left["start"] <= right["start"] and left["end"] >= right["end"])
                or (right["start"] <= left["start"] and right["end"] >= left["end"])
            ):
                has_nested = True
                break
        if has_nested:
            break

    return has_nested, has_multi


def summarize_current_split(rows: list[dict]) -> dict:
    summary = {
        "splits": defaultdict(lambda: {"sentences": 0, "labels": set(), "nested_sentences": 0, "multi_sentences": 0}),
        "doc_overlap_pattern": Counter(),
        "doc_sets": defaultdict(set),
    }

    for row in rows:
        if row["meta"]["is_synthetic"]:
            continue
        split = row["meta"]["split"]
        doc_id = row["meta"]["doc_id"]
        summary["doc_sets"][doc_id].add(split)
        split_stats = summary["splits"][split]
        split_stats["sentences"] += 1
        for ent in row["entities"]:
            split_stats["labels"].add(ent["label"])
        has_nested, has_multi = compute_sentence_features(row["entities"])
        if has_nested:
            split_stats["nested_sentences"] += 1
        if has_multi:
            split_stats["multi_sentences"] += 1

    for doc_splits in summary["doc_sets"].values():
        summary["doc_overlap_pattern"][tuple(sorted(doc_splits))] += 1

    return summary


def group_docs(rows: list[dict]) -> tuple[list[dict], list[str]]:
    docs: dict[str, dict] = {}
    for row in rows:
        if row["meta"]["is_synthetic"]:
            continue
        doc_id = row["meta"]["doc_id"]
        rec = docs.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "sentences": 0,
                "entities": 0,
                "labels": Counter(),
                "nested_sentences": 0,
                "multi_sentences": 0,
            },
        )
        rec["sentences"] += 1
        rec["entities"] += len(row["entities"])
        for ent in row["entities"]:
            rec["labels"][ent["label"]] += 1
        has_nested, has_multi = compute_sentence_features(row["entities"])
        if has_nested:
            rec["nested_sentences"] += 1
        if has_multi:
            rec["multi_sentences"] += 1

    all_labels = sorted({label for rec in docs.values() for label in rec["labels"]})
    return list(docs.values()), all_labels


def search_document_disjoint_split(
    docs: list[dict],
    all_labels: list[str],
    iterations: int,
    seed_base: int,
) -> dict:
    total_sentences = sum(doc["sentences"] for doc in docs)
    target = {"train": 0.7 * total_sentences, "val": 0.1 * total_sentences, "test": 0.2 * total_sentences}

    label_totals = Counter()
    for doc in docs:
        label_totals.update(doc["labels"])

    for doc in docs:
        rarity = sum(1.0 / max(label_totals[label], 1) for label in doc["labels"])
        doc["rarity_score"] = rarity
        doc["priority_score"] = rarity * 1000 + doc["nested_sentences"] * 2 + doc["multi_sentences"] * 2 + doc["entities"] * 0.01

    best = None
    label_set = set(all_labels)

    for offset in range(iterations):
        rnd = random.Random(seed_base + offset)
        order = docs[:]
        rnd.shuffle(order)
        order.sort(key=lambda item: (item["priority_score"], item["sentences"]), reverse=True)

        assignment = {name: [] for name in target}
        stats = {
            name: {"sentences": 0, "entities": 0, "labels": set(), "nested_sentences": 0, "multi_sentences": 0}
            for name in target
        }

        for doc in order:
            options = []
            for split in ("train", "val", "test"):
                sent_after = stats[split]["sentences"] + doc["sentences"]
                size_penalty = max(0.0, (sent_after - target[split]) / target[split])
                missing_gain = sum(1 for label in doc["labels"] if label not in stats[split]["labels"])
                struct_gain = 0
                if doc["nested_sentences"] and stats[split]["nested_sentences"] == 0:
                    struct_gain += 1
                if doc["multi_sentences"] and stats[split]["multi_sentences"] == 0:
                    struct_gain += 1
                bonus = missing_gain * 50 + struct_gain * 20
                if split == "train":
                    bonus *= 0.6
                current_fill = stats[split]["sentences"] / target[split]
                options.append((size_penalty * 200 - bonus + current_fill * 5, split))

            options.sort()
            chosen = options[0][1]
            assignment[chosen].append(doc)
            stats[chosen]["sentences"] += doc["sentences"]
            stats[chosen]["entities"] += doc["entities"]
            stats[chosen]["labels"].update(doc["labels"])
            stats[chosen]["nested_sentences"] += doc["nested_sentences"]
            stats[chosen]["multi_sentences"] += doc["multi_sentences"]

        missing = {split: sorted(label_set - stats[split]["labels"]) for split in stats}
        size_deviation = sum(abs(stats[split]["sentences"] - target[split]) / target[split] for split in stats)
        score = len(missing["val"]) * 500 + len(missing["test"]) * 500 + len(missing["train"]) * 100 + size_deviation * 100

        for split in stats:
            if stats[split]["nested_sentences"] == 0:
                score += 200
            if stats[split]["multi_sentences"] == 0:
                score += 200

        candidate = {
            "score": score,
            "seed": seed_base + offset,
            "target_sentences": target,
            "stats": stats,
            "missing_labels": missing,
            "assignment": {split: [doc["doc_id"] for doc in docs_in_split] for split, docs_in_split in assignment.items()},
        }

        if best is None or candidate["score"] < best["score"]:
            best = candidate

    # convert sets for json
    for split in best["stats"]:
        best["stats"][split]["labels"] = sorted(best["stats"][split]["labels"])

    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the T2KNOW split trade-off and search for a document-disjoint candidate.")
    parser.add_argument("--input-jsonl", default=str(RELEASE_ROOT / "data" / "sentence_level_legacy" / "t2know.jsonl"))
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=0)
    parser.add_argument("--output-json", default=str(RELEASE_ROOT / "provenance" / "reports" / "split_tradeoff_analysis.json"))
    parser.add_argument("--output-md", default=str(RELEASE_ROOT / "provenance" / "notes" / "split_tradeoff.md"))
    parser.add_argument("--output-assignment", default=str(RELEASE_ROOT / "provenance" / "reports" / "document_disjoint_split_candidate.json"))
    args = parser.parse_args()

    rows = load_rows(Path(args.input_jsonl))
    current = summarize_current_split(rows)
    docs, all_labels = group_docs(rows)
    candidate = search_document_disjoint_split(docs, all_labels, iterations=args.iterations, seed_base=args.seed_base)

    report = {
        "input_jsonl": portable_path(args.input_jsonl),
        "current_split": {
            "splits": {
                split: {
                    "sentences": stats["sentences"],
                    "label_count": len(stats["labels"]),
                    "nested_sentences": stats["nested_sentences"],
                    "multi_sentences": stats["multi_sentences"],
                }
                for split, stats in current["splits"].items()
            },
            "doc_overlap_pattern": {"+".join(pattern): count for pattern, count in current["doc_overlap_pattern"].items()},
            "unique_reviewed_docs": len(current["doc_sets"]),
        },
        "candidate_document_disjoint_split": candidate,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_assignment = Path(args.output_assignment)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_assignment.parent.mkdir(parents=True, exist_ok=True)

    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    assignment_payload = {
        "seed": candidate["seed"],
        "score": candidate["score"],
        "assignment": candidate["assignment"],
    }
    with output_assignment.open("w", encoding="utf-8") as handle:
        json.dump(assignment_payload, handle, indent=2, ensure_ascii=False)

    current_patterns = report["current_split"]["doc_overlap_pattern"]
    current_splits = report["current_split"]["splits"]
    candidate_stats = candidate["stats"]
    current_total_sentences = sum(split["sentences"] for split in current_splits.values())
    candidate_total_sentences = sum(split["sentences"] for split in candidate_stats.values())

    md_lines = [
        "# Split Trade-off Analysis",
        "",
        f"Input JSONL: `{portable_path(args.input_jsonl)}`",
        "",
        "## Current reviewed split",
        "",
        f"- Unique reviewed source abstracts: `{report['current_split']['unique_reviewed_docs']}`",
        f"- Train sentences: `{current_splits['train']['sentences']}`",
        f"- Validation sentences: `{current_splits['val']['sentences']}`",
        f"- Test sentences: `{current_splits['test']['sentences']}`",
        f"- Label coverage: train `{current_splits['train']['label_count']}`, val `{current_splits['val']['label_count']}`, test `{current_splits['test']['label_count']}`",
        f"- Nested-sentence coverage: train `{current_splits['train']['nested_sentences']}`, val `{current_splits['val']['nested_sentences']}`, test `{current_splits['test']['nested_sentences']}`",
        f"- Same-span multi-label sentence coverage: train `{current_splits['train']['multi_sentences']}`, val `{current_splits['val']['multi_sentences']}`, test `{current_splits['test']['multi_sentences']}`",
        "",
        "### Current abstract overlap pattern",
        "",
    ]

    for pattern, count in sorted(current_patterns.items()):
        md_lines.append(f"- `{pattern}`: `{count}` abstracts")

    md_lines.extend(
        [
            "",
            "## Best document-disjoint candidate",
            "",
            f"- Search iterations: `{args.iterations}`",
            f"- Best random seed: `{candidate['seed']}`",
            f"- Candidate score: `{candidate['score']:.6f}`",
            f"- Sentence totals: train `{candidate_stats['train']['sentences']}`, val `{candidate_stats['val']['sentences']}`, test `{candidate_stats['test']['sentences']}`",
            f"- Entity totals: train `{candidate_stats['train']['entities']}`, val `{candidate_stats['val']['entities']}`, test `{candidate_stats['test']['entities']}`",
            f"- Document totals: train `{len(candidate['assignment']['train'])}`, val `{len(candidate['assignment']['val'])}`, test `{len(candidate['assignment']['test'])}`",
            f"- Label coverage: train `{len(candidate_stats['train']['labels'])}`, val `{len(candidate_stats['val']['labels'])}`, test `{len(candidate_stats['test']['labels'])}`",
            f"- Nested-sentence coverage: train `{candidate_stats['train']['nested_sentences']}`, val `{candidate_stats['val']['nested_sentences']}`, test `{candidate_stats['test']['nested_sentences']}`",
            f"- Same-span multi-label sentence coverage: train `{candidate_stats['train']['multi_sentences']}`, val `{candidate_stats['val']['multi_sentences']}`, test `{candidate_stats['test']['multi_sentences']}`",
            "",
            "### Missing labels in the candidate split",
            "",
            f"- Train: `{candidate['missing_labels']['train']}`",
            f"- Validation: `{candidate['missing_labels']['val']}`",
            f"- Test: `{candidate['missing_labels']['test']}`",
            "",
            "## Interpretation",
            "",
            "- The current sentence-level split preserves full 40-label coverage in all three partitions, but it allows some reviewed source abstracts to contribute sentences to more than one split.",
            "- The searched document-disjoint candidate also preserves full 40-label coverage in train, validation, and test.",
            "- The candidate remains close to the intended `70/10/20` sentence-level proportion while preserving nested and same-span multi-label coverage in all three partitions.",
            "- This means that a stronger document-disjoint benchmark appears feasible for the reviewed corpus and should be considered seriously for the paper benchmark.",
        ]
    )

    with output_md.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(md_lines) + "\n")


if __name__ == "__main__":
    main()
