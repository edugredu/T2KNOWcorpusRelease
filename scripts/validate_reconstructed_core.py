#!/usr/bin/env python3
"""Validate a locally reconstructed T2KNOW-Core directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

LAYOUTS = [
    ("document_disjoint_hybrid", "t2know_document_disjoint_hybrid.jsonl"),
    ("document_disjoint", "t2know_document_disjoint.jsonl"),
]
SPLIT_FILES = ["trainData.json", "evalData.json", "testData.json"]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_layout(root: Path) -> tuple[Path, str, Path]:
    for directory, jsonl_name in LAYOUTS:
        candidate = root / directory / jsonl_name
        if candidate.exists():
            return root / directory, directory, candidate
    expected = " or ".join(f"{directory}/{jsonl}" for directory, jsonl in LAYOUTS)
    raise FileNotFoundError(f"Missing reconstructed JSONL under {root}: expected {expected}")


def iter_records(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, 1):
            if not line.strip():
                continue
            yield line_num, json.loads(line)


def validate_record(path: Path, line_num: int, record: dict) -> int:
    errors = 0
    text = record.get("text")
    if not isinstance(text, str):
        print(f"{path}:{line_num}: text is not reconstructed")
        return 1
    expected_sha = record.get("text_sha256") or record.get("meta", {}).get("sentence_sha256")
    if expected_sha and sha256_text(text) != expected_sha:
        print(f"{path}:{line_num}: text_sha256 mismatch")
        errors += 1
    expected_length = record.get("text_length") or record.get("meta", {}).get("sentence_char_length")
    if expected_length not in (None, "") and len(text) != int(expected_length):
        print(f"{path}:{line_num}: text_length mismatch")
        errors += 1

    annotations = record.get("entities")
    if annotations is None:
        annotations = [
            {"start": tag["start"], "end": tag["end"], "text": tag.get("text")}
            for tag in record.get("tags", [])
        ]
    for ent in annotations:
        start = ent["start"]
        end = ent["end"]
        if start < 0 or end > len(text) or start > end:
            print(f"{path}:{line_num}: invalid entity offsets {start}-{end}")
            errors += 1
        elif "text" in ent and ent.get("text") is not None and ent.get("text") != text[start:end]:
            spans = ent.get("spans", [[start, end]])
            expected = " ".join(text[s:e] for s, e in spans)
            if ent.get("text") != expected:
                print(f"{path}:{line_num}: entity text mismatch")
                errors += 1
    return errors


def validate_file(path: Path) -> int:
    errors = 0
    for line_num, record in iter_records(path):
        errors += validate_record(path, line_num, record)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate reconstructed T2KNOW-Core files.")
    parser.add_argument("path")
    parser.add_argument("--validate-brat", action="store_true")
    args = parser.parse_args()

    root = Path(args.path)
    try:
        layout_dir, _layout_name, jsonl = detect_layout(root)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    errors = 0
    errors += validate_file(jsonl)
    for split_file in SPLIT_FILES:
        path = layout_dir / split_file
        if path.exists():
            errors += validate_file(path)
    if args.validate_brat:
        brat_dir = root / "brat_core"
        if not brat_dir.exists():
            brat_dir = root / "text_included/brat_core"
        if not brat_dir.exists():
            print(f"Missing reconstructed BRAT directory: {brat_dir}")
            errors += 1
    if errors:
        print(f"FAILURE: reconstructed validation found {errors} error(s).")
        return 1
    print("SUCCESS: reconstructed core is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
