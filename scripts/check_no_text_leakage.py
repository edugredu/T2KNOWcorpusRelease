#!/usr/bin/env python3
"""Schema/path-level text-leakage checks for the public T2KNOW release."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "provenance/reports/source_license_audit_v6.tsv"


def load_excluded_docs() -> set[str]:
    with AUDIT.open(newline="", encoding="utf-8") as handle:
        return {
            row["doc_id"]
            for row in csv.DictReader(handle, delimiter="\t")
            if row["source_text_decision"] == "exclude_text"
        }


def doc_id_from_name(path: Path) -> str | None:
    match = re.search(r"text(\d+)\.(?:txt|ann)$", path.name)
    return match.group(1) if match else None


def iter_json_records(path: Path):
    if path.is_file():
        candidates = [path]
    else:
        candidates = list(path.rglob("*.jsonl")) + [
            item for item in path.rglob("*.json") if item.name.endswith("Data.json")
        ]
    for candidate in candidates:
        with candidate.open(encoding="utf-8") as handle:
            for line_num, line in enumerate(handle, 1):
                if line.strip():
                    yield candidate, line_num, json.loads(line)


def check_json(path: Path, excluded_docs: set[str]) -> list[str]:
    errors: list[str] = []
    for source, line_num, record in iter_json_records(path):
        meta = record.get("meta", {})
        doc_id = str(meta.get("doc_id") or record.get("id", "").split("_")[0])
        if doc_id not in excluded_docs:
            continue
        status = meta.get("text_redistribution_status") or meta.get("source_text_decision")
        if status not in {"excluded", "exclude_text"}:
            errors.append(f"{source}:{line_num}: excluded doc {doc_id} missing excluded status")
        if record.get("text") is not None:
            errors.append(f"{source}:{line_num}: excluded doc {doc_id} contains sentence text")
        for ent in record.get("entities", []):
            if ent.get("text") is not None:
                errors.append(f"{source}:{line_num}: excluded doc {doc_id} contains entity text")
        for key in ("brat_txt_path", "brat_ann_path"):
            if meta.get(key):
                errors.append(f"{source}:{line_num}: excluded doc {doc_id} retains {key}")
    return errors


def check_brat(path: Path, excluded_docs: set[str]) -> list[str]:
    errors: list[str] = []
    for brat_file in path.rglob("*"):
        if brat_file.suffix not in {".txt", ".ann"}:
            continue
        doc_id = doc_id_from_name(brat_file)
        if doc_id in excluded_docs:
            errors.append(f"{brat_file}: BRAT file exists for text-excluded doc {doc_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public T2KNOW data for schema/path-level text leakage.")
    parser.add_argument("path", help="Release data path to check.")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    excluded_docs = load_excluded_docs()
    errors = check_json(path, excluded_docs) + check_brat(path, excluded_docs)
    if errors:
        for error in errors[:200]:
            print(error)
        if len(errors) > 200:
            print(f"... {len(errors) - 200} additional errors")
        print(f"FAILURE: detected {len(errors)} public leakage issue(s).")
        return 1
    print("SUCCESS: no schema/path-level text leakage detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
