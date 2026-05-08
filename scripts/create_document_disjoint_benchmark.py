#!/usr/bin/env python3
"""Create a document-disjoint reviewed benchmark package from a split assignment."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def portable_path(path_str: str) -> str:
    path = Path(path_str).resolve()
    try:
        return str(path.relative_to(RELEASE_ROOT))
    except ValueError:
        return path_str


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_brat_texts(brat_core_dir: Path) -> dict[str, dict[str, str]]:
    """Load released BRAT texts keyed by source file.

    The reviewed BRAT export may contain the same reviewed source file in more
    than one folder for compatibility with earlier layouts. The JSONL split is
    the benchmark authority, so linkage stores the concrete BRAT path selected
    here instead of requiring users to infer it from the JSONL split.
    """
    texts: dict[str, dict[str, str]] = {}
    if not brat_core_dir.exists():
        return texts
    for split_dir in ("train", "eval", "test"):
        folder = brat_core_dir / split_dir
        if not folder.exists():
            continue
        for txt_path in sorted(folder.glob("*.txt")):
            text = txt_path.read_text(encoding="utf-8")
            ann_path = txt_path.with_suffix(".ann")
            if txt_path.name in texts:
                if texts[txt_path.name]["text"] != text:
                    raise RuntimeError(f"Conflicting BRAT text content for {txt_path.name}")
                continue
            texts[txt_path.name] = {
                "text": text,
                "txt_path": portable_path(str(txt_path)),
                "ann_path": portable_path(str(ann_path)),
            }
    return texts


def locate_sentence(
    row: dict,
    split: str,
    brat_texts: dict[str, dict[str, str]],
    search_positions: dict[str, int],
) -> dict[str, int | str]:
    """Return document-relative sentence offsets when the matching BRAT text is available."""
    source_file = row["meta"].get("source_file")
    brat_record = brat_texts.get(source_file)
    if brat_record is None:
        return {}

    doc_text = brat_record["text"]
    sent_text = row["text"]
    start = doc_text.find(sent_text, search_positions.get(source_file, 0))
    if start == -1:
        start = doc_text.find(sent_text)
    if start == -1:
        raise RuntimeError(f"Could not align sentence for {source_file}: {sent_text[:80]!r}")

    end = start + len(sent_text)
    search_positions[source_file] = end
    return {
        "document_start": start,
        "document_end": end,
        "brat_txt_path": brat_record["txt_path"],
        "brat_ann_path": brat_record["ann_path"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create document-disjoint benchmark split files for T2KNOW.")
    parser.add_argument(
        "--input-jsonl",
        default=str(RELEASE_ROOT / "data" / "sentence_level_legacy" / "t2know.jsonl"),
        help="Canonical consolidated JSONL release.",
    )
    parser.add_argument(
        "--assignment-json",
        default=str(RELEASE_ROOT / "provenance" / "reports" / "document_disjoint_split_candidate.json"),
        help="Document-to-split assignment produced by analyze_split_tradeoff.py.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(RELEASE_ROOT / "data" / "document_disjoint"),
        help="Output directory for the document-disjoint benchmark package.",
    )
    parser.add_argument(
        "--brat-core-dir",
        default=str(RELEASE_ROOT / "data" / "brat_core"),
        help="Reviewed BRAT core directory used to add document-relative sentence offsets when available.",
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input_jsonl))
    brat_texts = load_brat_texts(Path(args.brat_core_dir))
    search_positions: dict[str, int] = {}
    assignment_payload = json.loads(Path(args.assignment_json).read_text(encoding="utf-8"))
    assignment = {}
    for split, doc_ids in assignment_payload["assignment"].items():
        for doc_id in doc_ids:
            assignment[doc_id] = split

    filtered_rows = []
    split_json_records = {"train": [], "val": [], "test": []}
    split_doc_sentence_index: dict[str, defaultdict[str, int]] = {
        "train": defaultdict(int),
        "val": defaultdict(int),
        "test": defaultdict(int),
    }
    stats = {
        "train": {"docs": set(), "sentences": 0, "entities": 0},
        "val": {"docs": set(), "sentences": 0, "entities": 0},
        "test": {"docs": set(), "sentences": 0, "entities": 0},
    }

    for row in rows:
        if row["meta"]["is_synthetic"]:
            continue
        doc_id = row["meta"]["doc_id"]
        split = assignment.get(doc_id)
        if split is None:
            continue

        sentence_idx = split_doc_sentence_index[split][doc_id]
        split_doc_sentence_index[split][doc_id] += 1
        sentence_id = f"{doc_id}_{sentence_idx}"
        sentence_location = locate_sentence(row, split, brat_texts, search_positions)

        updated = {
            "text": row["text"],
            "entities": row["entities"],
            "meta": {
                **row["meta"],
                "split": split,
                "sentence_id": sentence_id,
                "sentence_index": sentence_idx,
                **sentence_location,
            },
        }
        filtered_rows.append(updated)

        json_record = {
            "id": sentence_id,
            "text": row["text"],
            "tags": [
                {"start": ent["start"], "end": ent["end"], "tag": ent["label"]}
                for ent in row["entities"]
            ],
            "meta": {
                "doc_id": doc_id,
                "split": split,
                "source_file": row["meta"].get("source_file"),
                "sentence_index": sentence_idx,
                **sentence_location,
            },
        }
        split_json_records[split].append(json_record)

        stats[split]["docs"].add(doc_id)
        stats[split]["sentences"] += 1
        stats[split]["entities"] += len(row["entities"])

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "t2know_document_disjoint.jsonl", filtered_rows)
    write_jsonl(out_dir / "trainData.json", split_json_records["train"])
    write_jsonl(out_dir / "evalData.json", split_json_records["val"])
    write_jsonl(out_dir / "testData.json", split_json_records["test"])

    summary = {
        "source_jsonl": portable_path(args.input_jsonl),
        "assignment_json": portable_path(args.assignment_json),
        "seed": assignment_payload.get("seed"),
        "score": assignment_payload.get("score"),
        "splits": {
            split: {
                "docs": len(stats[split]["docs"]),
                "sentences": stats[split]["sentences"],
                "entities": stats[split]["entities"],
            }
            for split in ("train", "val", "test")
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = "\n".join(
        [
            "# Document-disjoint benchmark package",
            "",
            "This directory contains a reviewed-only, document-disjoint benchmark variant derived from the canonical T2KNOW JSONL release.",
            "",
            "Files:",
            "- `trainData.json`: line-oriented JSON records for training.",
            "- `evalData.json`: line-oriented JSON records for validation.",
            "- `testData.json`: line-oriented JSON records for test.",
            "- `t2know_document_disjoint.jsonl`: consolidated JSONL with updated split metadata.",
            "- `summary.json`: split counts and provenance.",
            "",
            "Offset and linkage metadata:",
            "- JSONL entity offsets are sentence-relative character offsets over the released `text` string.",
            "- split-file tag offsets are also sentence-relative character offsets over the released `text` string.",
            "- JSONL `meta.sentence_id` and split-file `id` use the same `doc_id_sentenceIndex` convention.",
            "- JSONL `meta.sentence_index` is zero-based within each source abstract.",
            "- JSONL `meta.document_start` and `meta.document_end` give the sentence boundary in the matching BRAT `.txt` file when `data/brat_core/` is available during generation.",
            "- JSONL `meta.brat_txt_path` and `meta.brat_ann_path` provide the concrete BRAT files selected for inspection.",
            "- Benchmark split membership is defined by `meta.split` and the split JSON files, not by inferring a split from the BRAT folder path.",
            "",
            "Design properties:",
            "- only non-synthetic reviewed sentences are included,",
            "- each reviewed source abstract belongs to exactly one split,",
            "- split membership follows the assignment stored in",
            f"  `{portable_path(args.assignment_json)}`.",
            "",
            "## Split Construction Recipe",
            "",
            "The split was generated at the source-abstract level. Candidate assignments were searched with a fixed seed of `0` over `500` randomized iterations. The search balances closeness to the `70/10/20` train/validation/test sentence ratio with full label coverage and retention of nested and same-span multi-label evidence in every split.",
            "",
            "The release-local scripts are:",
            "",
            "```bash",
            "python3 T2KNOW-release/scripts/analyze_split_tradeoff.py",
            "python3 T2KNOW-release/scripts/create_document_disjoint_benchmark.py",
            "```",
            "",
            "The default paths inside those scripts resolve relative to the release root, so the commands above regenerate the provenance reports and benchmark package without referring back to the source repository.",
            "",
            "In this release package, the selected assignment and validation artefacts are stored under `provenance/reports/`:",
            "",
            "- `document_disjoint_split_candidate.json`: selected document-to-split assignment.",
            "- `document_disjoint_doc_ids.csv`: compact `doc_id,split` manifest.",
            "- `document_disjoint_doc_ids_train.txt`: training document IDs.",
            "- `document_disjoint_doc_ids_val.txt`: validation document IDs.",
            "- `document_disjoint_doc_ids_test.txt`: test document IDs.",
            "- `document_disjoint_label_counts.csv`: per-label train/validation/test counts.",
            "- `document_disjoint_split_validation.json`: validation report confirming document disjointness, all-label coverage in each split, zero synthetic records, and consistency with the label-count table.",
            "",
            "The per-label count table should be interpreted conservatively: the minimum per-label count across partitions is `2` and the median of the per-label partition minima is `166`, so the split preserves label availability rather than balanced support for every tail label.",
        ]
    )
    (out_dir / "README.md").write_text(readme + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
