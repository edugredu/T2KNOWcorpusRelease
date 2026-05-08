#!/usr/bin/env python3
"""Build a local reconstructed T2KNOW-Core directory from user-supplied texts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NORMALIZATION_POLICY = "reviewed_release_text_utf8"
EXPECTED_NEWLINE_POLICY = "preserve_reviewed_brat_newlines"
ALLOWED_SOURCE_TEXT_UNITS = {"abstract", "sentence_bundle"}
CORE_REL = Path("data/t2know-core-v1.0")
LAYOUTS = [
    ("document_disjoint_hybrid", "t2know_document_disjoint_hybrid.jsonl"),
    ("document_disjoint", "t2know_document_disjoint.jsonl"),
]
SPLIT_FILES = ["trainData.json", "evalData.json", "testData.json"]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text_exact(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_source_map(path: Path) -> dict[str, dict[str, str]]:
    rows = read_tsv(path)
    required = {"doc_id", "source_text_path", "raw_source_sha256", "normalization_policy", "newline_policy", "source_text_unit"}
    if rows and not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0]))
        raise SystemExit(f"source map is missing required columns: {missing}")
    return {row["doc_id"]: row for row in rows}


def source_map_from_root(root: Path, manifest: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    source_map: dict[str, dict[str, str]] = {}
    for doc_id, row in manifest.items():
        if row["text_redistribution_status"] == "included":
            continue
        candidates = [
            root / f"{doc_id}.txt",
            root / f"{doc_id}.abstract.txt",
            root / f"{doc_id}.text",
        ]
        existing = next((path for path in candidates if path.exists()), None)
        if existing is None:
            continue
        source_map[doc_id] = {
            "doc_id": doc_id,
            "source_text_path": str(existing),
            "raw_source_sha256": "",
            "normalization_policy": row["normalization_policy"],
            "newline_policy": row["newline_policy"],
            "source_text_unit": "abstract",
        }
    return source_map


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def detect_layout(root: Path) -> tuple[Path, str, Path]:
    core = root / CORE_REL
    if not core.exists() and root.name == "t2know-core-v1.0":
        core = root
    for directory, jsonl_name in LAYOUTS:
        candidate_dir = core / directory
        candidate_jsonl = candidate_dir / jsonl_name
        if candidate_jsonl.exists():
            return core, directory, candidate_jsonl
    expected = " or ".join(f"{directory}/{jsonl}" for directory, jsonl in LAYOUTS)
    raise SystemExit(f"Could not find supported benchmark layout under {core}: expected {expected}")


def record_is_excluded(record: dict) -> bool:
    meta = record.get("meta", {})
    return meta.get("text_redistribution_status") == "excluded" or meta.get("source_text_decision") == "exclude_text"


def redacted_record(record: dict) -> dict:
    out = json.loads(json.dumps(record))
    meta = out.get("meta", {})
    out["text"] = None
    out["text_sha256"] = out.get("text_sha256") or meta.get("sentence_sha256")
    out["text_length"] = out.get("text_length") or meta.get("sentence_char_length")
    out["text_redacted"] = True
    meta["text_available_in_archive"] = False
    meta["requires_reconstruction"] = True
    meta["text_redistribution_status"] = "excluded"
    meta["source_text_policy"] = "user_reconstruction_required"
    for ent in out.get("entities", []):
        ent["text"] = None
        ent["surface_text_redacted"] = True
    return out


def reconstruct_record(record: dict, source_texts: dict[str, str], sent_by_doc: dict[tuple[str, str], dict[str, str]]) -> tuple[dict, dict | None]:
    meta = record.get("meta", {})
    doc_id = str(meta.get("doc_id"))
    sentence_id = str(meta.get("sentence_id") or record.get("id"))
    if not record_is_excluded(record):
        return record, None
    if doc_id not in source_texts:
        return redacted_record(record), None
    sent = sent_by_doc.get((doc_id, sentence_id))
    if sent is None:
        return record, {"doc_id": doc_id, "sentence_id": sentence_id, "status": "missing_sentence_manifest_row"}
    start = int(sent["document_start"])
    end = int(sent["document_end"])
    text = source_texts[doc_id][start:end]
    if sha256_text(text) != sent["sentence_sha256"]:
        return record, {"doc_id": doc_id, "sentence_id": sentence_id, "status": "sentence_sha256_mismatch"}

    out = json.loads(json.dumps(record))
    out["text"] = text
    out["text_sha256"] = sha256_text(text)
    out["text_length"] = len(text)
    out["text_redacted"] = False
    out.setdefault("meta", {})
    out["meta"]["text_available_in_archive"] = True
    out["meta"]["requires_reconstruction"] = False
    out["meta"]["text_redistribution_status"] = "reconstructed"
    out["meta"]["source_text_policy"] = "locally_reconstructed_user_copy"
    for ent in out.get("entities", []):
        spans = ent.get("spans", [[ent["start"], ent["end"]]])
        ent["text"] = " ".join(text[s:e] for s, e in spans)
        ent.pop("surface_text_redacted", None)
    return out, None


def reconstruct_file(path: Path, out_path: Path, source_texts: dict[str, str], sent_by_doc: dict[tuple[str, str], dict[str, str]]) -> list[dict]:
    reconstructed = []
    failures = []
    for record in load_jsonl(path):
        out, failure = reconstruct_record(record, source_texts, sent_by_doc)
        reconstructed.append(out)
        if failure:
            failures.append(failure)
    write_jsonl(out_path, reconstructed)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build locally reconstructed T2KNOW-Core files.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sentence-manifest", required=True)
    parser.add_argument(
        "--source-text-root",
        help="Directory containing normalized reconstructed abstracts named <doc_id>.txt, <doc_id>.abstract.txt, or <doc_id>.text.",
    )
    parser.add_argument(
        "--source-map",
        help="TSV mapping doc_id to normalized reconstructed abstract paths and declared reconstruction policies.",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if not args.source_map and not args.source_text_root:
        raise SystemExit("Provide --source-map or --source-text-root.")
    if args.source_map and not Path(args.source_map).exists():
        raise SystemExit(f"Source map not found: {args.source_map}")

    manifest = {row["doc_id"]: row for row in read_tsv(Path(args.manifest))}
    sentence_manifest = read_tsv(Path(args.sentence_manifest))
    source_map = source_map_from_root(Path(args.source_text_root), manifest) if args.source_text_root else {}
    if args.source_map:
        source_map.update(read_source_map(Path(args.source_map)))
    input_core, layout_dir, input_jsonl = detect_layout(ROOT)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    source_texts: dict[str, str] = {}
    failures = []
    for doc_id, row in manifest.items():
        if row["text_redistribution_status"] == "included":
            continue
        source_row = source_map.get(doc_id)
        if not source_row:
            failures.append({"doc_id": doc_id, "status": "missing_source_text"})
            continue
        source_path = Path(source_row["source_text_path"])
        if not source_path.exists():
            failures.append({"doc_id": doc_id, "status": "source_text_path_not_found"})
            continue
        if row["normalization_policy"] != EXPECTED_NORMALIZATION_POLICY:
            failures.append({"doc_id": doc_id, "status": "unsupported_manifest_normalization_policy"})
            continue
        if row["newline_policy"] != EXPECTED_NEWLINE_POLICY:
            failures.append({"doc_id": doc_id, "status": "unsupported_manifest_newline_policy"})
            continue
        if source_row.get("normalization_policy") != row["normalization_policy"]:
            failures.append({"doc_id": doc_id, "status": "normalization_policy_mismatch"})
            continue
        if source_row.get("newline_policy") != row["newline_policy"]:
            failures.append({"doc_id": doc_id, "status": "newline_policy_mismatch"})
            continue
        if source_row.get("source_text_unit") not in ALLOWED_SOURCE_TEXT_UNITS:
            failures.append({"doc_id": doc_id, "status": "invalid_source_text_unit"})
            continue
        expected_raw_sha = source_row.get("raw_source_sha256", "").strip()
        if expected_raw_sha and sha256_bytes(source_path) != expected_raw_sha:
            failures.append({"doc_id": doc_id, "status": "raw_source_sha256_mismatch"})
            continue
        text = read_text_exact(source_path)
        expected_doc_sha = row["normalized_document_sha256"]
        if expected_doc_sha and sha256_text(text) != expected_doc_sha:
            failures.append({"doc_id": doc_id, "status": "normalized_document_sha256_mismatch"})
            continue
        source_texts[doc_id] = text

    shutil.copytree(input_core, out, dirs_exist_ok=True)
    sent_by_doc = {}
    for row in sentence_manifest:
        sent_by_doc[(row["doc_id"], row["sentence_id"])] = row

    layout_out = out / layout_dir
    failures.extend(reconstruct_file(input_jsonl, layout_out / input_jsonl.name, source_texts, sent_by_doc))
    for split_file in SPLIT_FILES:
        split_path = input_jsonl.parent / split_file
        if split_path.exists():
            failures.extend(reconstruct_file(split_path, layout_out / split_file, source_texts, sent_by_doc))

    report_path = out / "metadata/reconstruction_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "input_core": str(input_core),
        "layout": layout_dir,
        "reconstructed_documents": len(source_texts),
        "failures": failures,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote reconstructed directory: {out}")
    print(f"Reconstruction failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
