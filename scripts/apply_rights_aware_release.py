#!/usr/bin/env python3
"""Apply rights-aware public metadata and redaction to T2KNOW-Core.

This script is intended to be run from a staged release that still has the
reviewed full-text records available. It rewrites the canonical JSON/JSONL
benchmark files so text-excluded records retain offsets, labels, split
membership, source identifiers, and checksums, but no sentence text or entity
surface strings.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "provenance/reports/source_license_audit_v6.tsv"
CORE = ROOT / "data/t2know-core-v1.0"
DOC_DIR = CORE / "document_disjoint"
TOP_DOC_DIR = ROOT / "data/t2know-core-v1.0/document_disjoint"
BRAT_DIR = CORE / "brat_core"
TOP_BRAT_DIR = ROOT / "data/brat_core"
REPORT_DIR = ROOT / "provenance/reports"
SCHEMA_DIR = ROOT / "schemas"

SPLIT_FILES = ("trainData.json", "evalData.json", "testData.json")
PUBLIC_META_INCLUDED = {
    "text_available_in_archive": True,
    "requires_reconstruction": False,
    "text_redistribution_status": "included",
    "brat_available_in_archive": True,
    "source_text_policy": "redistributed",
    "offset_basis": "sentence_text",
}
PUBLIC_META_EXCLUDED = {
    "text_available_in_archive": False,
    "requires_reconstruction": True,
    "text_redistribution_status": "excluded",
    "brat_available_in_archive": False,
    "source_text_policy": "user_reconstruction_required",
    "offset_basis": "reconstructed_sentence_text",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def annotation_checksum(entities: list[dict[str, Any]] | list[dict[str, Any]]) -> str:
    normalized = []
    for ent in entities:
        if "tag" in ent:
            normalized.append({"start": ent["start"], "end": ent["end"], "label": ent["tag"]})
        else:
            normalized.append(
                {
                    "start": ent["start"],
                    "end": ent["end"],
                    "label": ent["label"],
                    "spans": ent.get("spans", [[ent["start"], ent["end"]]]),
                }
            )
    normalized.sort(key=lambda item: (item["start"], item["end"], item["label"]))
    return sha256_text(json.dumps(normalized, sort_keys=True, separators=(",", ":")))


def read_audit() -> dict[str, dict[str, str]]:
    with AUDIT_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    by_doc = {row["doc_id"]: row for row in rows}
    counts = Counter(row["source_text_decision"] for row in rows)
    if len(by_doc) != 821 or counts != {"include_text": 432, "exclude_text": 389}:
        raise RuntimeError(f"Unexpected audit shape: rows={len(by_doc)} decisions={dict(counts)}")
    return by_doc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_brat_documents(brat_dir: Path) -> dict[str, dict[str, Path | str]]:
    docs: dict[str, dict[str, Path | str]] = {}
    for folder in ("train", "eval", "test"):
        base = brat_dir / folder
        if not base.exists():
            continue
        for txt_path in sorted(base.glob("*.txt")):
            ann_path = txt_path.with_suffix(".ann")
            source_file = txt_path.name
            text = txt_path.read_text(encoding="utf-8")
            if source_file in docs:
                if docs[source_file]["text"] != text:
                    raise RuntimeError(f"Conflicting BRAT text for {source_file}")
                continue
            docs[source_file] = {"txt_path": txt_path, "ann_path": ann_path, "text": text}
    return docs


def source_info(audit: dict[str, dict[str, str]], doc_id: str) -> dict[str, str | None]:
    row = audit[doc_id]
    return {
        "doi": row.get("doi") or None,
        "pmid": row.get("pmid") or None,
        "pmcid": row.get("pmcid") or None,
        "year": row.get("publication_year") or None,
        "journal": row.get("journal") or None,
        "source_url": row.get("doi") and f"https://doi.org/{row['doi']}" or None,
        "license_evidence": row.get("epmc_license")
        or row.get("openalex_licenses")
        or row.get("unpaywall_licenses")
        or row.get("crossref_license_urls")
        or None,
        "source_match_confidence": row.get("match_confidence") or None,
        "metadata_source": "source_license_audit_v6",
        "metadata_license_evidence": "unresolved_pre_submission_gate",
    }


def metadata_for_record(
    record: dict[str, Any],
    audit: dict[str, dict[str, str]],
    brat_docs: dict[str, dict[str, Path | str]],
) -> dict[str, Any]:
    meta = dict(record.get("meta", {}))
    doc_id = str(meta.get("doc_id") or record.get("id", "").split("_")[0])
    decision = audit[doc_id]["source_text_decision"]
    text = record.get("text") or ""
    source_file = meta.get("source_file") or audit[doc_id].get("source_file")
    doc_text = str(brat_docs.get(source_file, {}).get("text", ""))
    normalized_document_sha256 = sha256_text(doc_text) if doc_text else None

    meta.update(source_info(audit, doc_id))
    meta.update(PUBLIC_META_INCLUDED if decision == "include_text" else PUBLIC_META_EXCLUDED)
    meta["source_text_decision"] = decision
    meta["sentence_sha256"] = meta.get("sentence_sha256") or sha256_text(text)
    meta["sentence_char_length"] = meta.get("sentence_char_length") or len(text)
    meta["normalized_document_sha256"] = normalized_document_sha256
    meta["annotation_checksum"] = annotation_checksum(record.get("entities") or record.get("tags") or [])
    meta["normalization_policy"] = "reviewed_release_text_utf8"
    meta["newline_policy"] = "preserve_reviewed_brat_newlines"

    if decision == "include_text":
        document_path = f"data/t2know-core-v1.0/brat_core/documents/{source_file}"
        meta["brat_txt_path"] = document_path
        meta["brat_ann_path"] = document_path.replace(".txt", ".ann")
    else:
        meta.pop("brat_txt_path", None)
        meta.pop("brat_ann_path", None)
    return meta


def redact_jsonl_record(
    record: dict[str, Any],
    audit: dict[str, dict[str, str]],
    brat_docs: dict[str, dict[str, Path | str]],
) -> dict[str, Any]:
    doc_id = str(record["meta"]["doc_id"])
    decision = audit[doc_id]["source_text_decision"]
    out = json.loads(json.dumps(record))
    out["meta"] = metadata_for_record(out, audit, brat_docs)
    if decision == "exclude_text":
        out["text"] = None
        for ent in out.get("entities", []):
            ent["text"] = None
    return out


def redact_split_record(
    record: dict[str, Any],
    audit: dict[str, dict[str, str]],
    brat_docs: dict[str, dict[str, Path | str]],
) -> dict[str, Any]:
    doc_id = str(record["meta"]["doc_id"])
    decision = audit[doc_id]["source_text_decision"]
    out = json.loads(json.dumps(record))
    out["meta"] = metadata_for_record(out, audit, brat_docs)
    if decision == "exclude_text":
        out["text"] = None
    return out


def write_redacted_document_disjoint(audit: dict[str, dict[str, str]], brat_docs: dict[str, dict[str, Path | str]]) -> None:
    jsonl_records = load_jsonl(DOC_DIR / "t2know_document_disjoint.jsonl")
    redacted_jsonl = [redact_jsonl_record(row, audit, brat_docs) for row in jsonl_records]
    write_jsonl(DOC_DIR / "t2know_document_disjoint.jsonl", redacted_jsonl)
    write_jsonl(TOP_DOC_DIR / "t2know_document_disjoint.jsonl", redacted_jsonl)

    for split_file in SPLIT_FILES:
        rows = load_jsonl(DOC_DIR / split_file)
        redacted = [redact_split_record(row, audit, brat_docs) for row in rows]
        write_jsonl(DOC_DIR / split_file, redacted)
        write_jsonl(TOP_DOC_DIR / split_file, redacted)


def build_split_neutral_brat(audit: dict[str, dict[str, str]], brat_docs: dict[str, dict[str, Path | str]]) -> None:
    """Create split-neutral BRAT inspection copies for text-included records.

    Existing split-named folders are left untouched by design; this script is
    non-destructive. Deposit packaging must exclude those legacy folders.
    """
    documents_dir = BRAT_DIR / "documents"
    top_documents_dir = TOP_BRAT_DIR / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    top_documents_dir.mkdir(parents=True, exist_ok=True)
    for doc_id, row in sorted(audit.items(), key=lambda item: int(item[0])):
        if row["source_text_decision"] != "include_text":
            continue
        source_file = row["source_file"]
        brat_record = brat_docs.get(source_file)
        if not brat_record:
            continue
        for out_dir in (documents_dir, top_documents_dir):
            shutil.copy2(brat_record["txt_path"], out_dir / source_file)
            ann_path = Path(brat_record["ann_path"])
            if ann_path.exists():
                shutil.copy2(ann_path, out_dir / ann_path.name)


def write_reconstruction_manifests(
    audit: dict[str, dict[str, str]],
    jsonl_records: list[dict[str, Any]],
    brat_docs: dict[str, dict[str, Path | str]],
) -> None:
    doc_rows: dict[str, dict[str, Any]] = {}
    sent_rows: list[dict[str, Any]] = []
    by_doc_annotations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in jsonl_records:
        doc_id = str(record["meta"]["doc_id"])
        by_doc_annotations[doc_id].extend(record.get("entities", []))

    for record in jsonl_records:
        meta = record["meta"]
        doc_id = str(meta["doc_id"])
        audit_row = audit[doc_id]
        original_text_hash = meta["sentence_sha256"]
        source_file = meta.get("source_file") or audit_row.get("source_file")
        doc_text = str(brat_docs.get(source_file, {}).get("text", ""))
        normalized_document_sha256 = sha256_text(doc_text) if doc_text else ""
        text_status = "included" if audit_row["source_text_decision"] == "include_text" else "excluded"
        if doc_id not in doc_rows:
            title = audit_row.get("source_title") or ""
            title_status = "excluded" if title else "not_available"
            doc_rows[doc_id] = {
                "doc_id": doc_id,
                "split": meta.get("split", ""),
                "text_redistribution_status": text_status,
                "title": "",
                "title_sha256": sha256_text(title) if title else "",
                "title_redistribution_status": title_status,
                "year": audit_row.get("publication_year", ""),
                "journal": audit_row.get("journal", ""),
                "doi": audit_row.get("doi", ""),
                "pmid": audit_row.get("pmid", ""),
                "source_url": audit_row.get("doi") and f"https://doi.org/{audit_row['doi']}" or "",
                "metadata_source": "source_license_audit_v6",
                "metadata_license_evidence": "unresolved_pre_submission_gate",
                "license_evidence": source_info(audit, doc_id)["license_evidence"] or "",
                "source_match_confidence": audit_row.get("match_confidence", ""),
                "normalized_document_sha256": normalized_document_sha256,
                "annotation_checksum": annotation_checksum(by_doc_annotations[doc_id]),
                "normalization_policy": "reviewed_release_text_utf8",
                "newline_policy": "preserve_reviewed_brat_newlines",
                "reconstruction_note": (
                    "source text redistributed"
                    if text_status == "included"
                    else "user reconstruction required; source text not redistributed"
                ),
            }
        sent_rows.append(
            {
                "doc_id": doc_id,
                "sentence_id": meta.get("sentence_id", ""),
                "split": meta.get("split", ""),
                "sentence_index": meta.get("sentence_index", ""),
                "document_start": meta.get("document_start", ""),
                "document_end": meta.get("document_end", ""),
                "sentence_char_length": meta.get("sentence_char_length", ""),
                "sentence_sha256": original_text_hash,
                "normalized_document_sha256": normalized_document_sha256,
                "normalization_policy": "reviewed_release_text_utf8",
                "newline_policy": "preserve_reviewed_brat_newlines",
                "text_status": text_status,
            }
        )

    write_tsv(REPORT_DIR / "reconstruction_manifest.tsv", list(doc_rows.values()))
    write_tsv(REPORT_DIR / "reconstruction_sentence_manifest.tsv", sent_rows)


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def public_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "mode": "public-redacted",
        "documents": 0,
        "sentences": len(records),
        "entities": 0,
        "text_status": defaultdict(lambda: {"documents": set(), "sentences": 0, "entities": 0}),
        "splits": defaultdict(lambda: {"documents": set(), "sentences": 0, "entities": 0}),
        "labels": Counter(),
        "same_span_multilabel_unique_spans": 0,
        "unique_spans": 0,
        "nested_or_overlapping_entities": 0,
    }
    docs = set()
    for record in records:
        meta = record["meta"]
        doc_id = str(meta["doc_id"])
        split = meta.get("split", "unknown")
        status = meta["text_redistribution_status"]
        entities = record.get("entities", [])
        docs.add(doc_id)
        stats["entities"] += len(entities)
        stats["text_status"][status]["documents"].add(doc_id)
        stats["text_status"][status]["sentences"] += 1
        stats["text_status"][status]["entities"] += len(entities)
        stats["splits"][split]["documents"].add(doc_id)
        stats["splits"][split]["sentences"] += 1
        stats["splits"][split]["entities"] += len(entities)
        span_to_labels: dict[tuple[tuple[int, int], ...], set[str]] = defaultdict(set)
        for ent in entities:
            stats["labels"][ent["label"]] += 1
            spans = tuple(tuple(span) for span in ent.get("spans", [[ent["start"], ent["end"]]]))
            span_to_labels[spans].add(ent["label"])
        stats["unique_spans"] += len(span_to_labels)
        stats["same_span_multilabel_unique_spans"] += sum(1 for labels in span_to_labels.values() if len(labels) > 1)
        spans_list = [
            tuple(tuple(span) for span in ent.get("spans", [[ent["start"], ent["end"]]]))
            for ent in entities
        ]
        for i, spans_a in enumerate(spans_list):
            for j, spans_b in enumerate(spans_list):
                if i >= j or spans_a == spans_b:
                    continue
                if any(max(a[0], b[0]) < min(a[1], b[1]) for a in spans_a for b in spans_b):
                    stats["nested_or_overlapping_entities"] += 1
                    break
    stats["documents"] = len(docs)
    stats["labels"] = dict(stats["labels"].most_common())
    for section in ("text_status", "splits"):
        stats[section] = {
            key: {**value, "documents": len(value["documents"])}
            for key, value in sorted(stats[section].items())
        }
    return stats


def write_stats_and_reports(audit: dict[str, dict[str, str]], records: list[dict[str, Any]]) -> None:
    stats = public_stats(records)
    stats["token_counts_available"] = False
    stats["token_count_verification_note"] = (
        "Public-redacted users can verify document, sentence, entity, label, split, "
        "same-span, and structural counts without source-text reconstruction. Full-core "
        "token counts and token-based sentence-length statistics for text-excluded records "
        "require the staged full abstract text or checksum-validated reconstructed abstract text."
    )
    (REPORT_DIR / "corpus_stats_public_verifiable.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    reconstructed_stats = dict(stats)
    reconstructed_stats["mode"] = "reconstructed-full"
    reconstructed_stats["requires_local_source_text"] = True
    reconstructed_stats["token_counts_available_after_reconstruction"] = True
    reconstructed_stats["token_counts_available"] = True
    reconstructed_stats["token_count_method"] = "Python str.split() over fixed reviewed sentence strings."
    reconstructed_stats["token_count_verification_note"] = (
        "Token counts are computed from the staged full abstract text or from user-side "
        "reconstructed abstract text after checksum validation of text-excluded records."
    )
    (REPORT_DIR / "corpus_stats_reconstructed_full.json").write_text(
        json.dumps(reconstructed_stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    split_rows = []
    split_counts: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"documents": set(), "sentences": 0, "entities": 0})
    for record in records:
        meta = record["meta"]
        key = (meta.get("split", ""), meta["text_redistribution_status"])
        split_counts[key]["documents"].add(str(meta["doc_id"]))
        split_counts[key]["sentences"] += 1
        split_counts[key]["entities"] += len(record.get("entities", []))
    for (split, status), value in sorted(split_counts.items()):
        split_rows.append(
            {
                "split": split,
                "text_redistribution_status": status,
                "documents": len(value["documents"]),
                "sentences": value["sentences"],
                "entities": value["entities"],
            }
        )
    write_tsv(REPORT_DIR / "split_by_text_status.tsv", split_rows)

    source_rows = []
    include_docs = {doc_id for doc_id, row in audit.items() if row["source_text_decision"] == "include_text"}
    exclude_docs = set(audit) - include_docs
    total = len(audit)
    properties = [
        ("DOI available", lambda row: bool(row.get("doi"))),
        ("PMID available", lambda row: bool(row.get("pmid"))),
        ("source URL available", lambda row: bool(row.get("doi"))),
        ("title available", lambda row: bool(row.get("source_title"))),
        ("year available", lambda row: bool(row.get("publication_year"))),
        ("journal available", lambda row: bool(row.get("journal"))),
        ("text included", lambda row: row.get("source_text_decision") == "include_text"),
        ("text excluded", lambda row: row.get("source_text_decision") == "exclude_text"),
        ("exact/high-confidence source match", lambda row: row.get("match_confidence") in {"exact", "high"}),
        ("reconstruction metadata available", lambda row: bool(row.get("sha256_txt"))),
        ("no recoverable source identifier", lambda row: not (row.get("doi") or row.get("pmid"))),
    ]
    for prop, predicate in properties:
        count = sum(1 for row in audit.values() if predicate(row))
        source_rows.append(
            {
                "Property": prop,
                "Count": count,
                "Percentage": f"{count / total * 100:.2f}",
                "Available in release field/report": "provenance/reports/reconstruction_manifest.tsv",
            }
        )
    write_tsv(REPORT_DIR / "source_composition_summary.tsv", source_rows)
    paper_notes = ROOT.parent.parent / "paper/notes/source_composition_summary.csv"
    paper_notes.parent.mkdir(parents=True, exist_ok=True)
    with paper_notes.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=source_rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(source_rows)

    (REPORT_DIR / "text_included_doc_ids.txt").write_text("\n".join(sorted(include_docs, key=int)) + "\n", encoding="utf-8")
    (REPORT_DIR / "text_excluded_doc_ids.txt").write_text("\n".join(sorted(exclude_docs, key=int)) + "\n", encoding="utf-8")


def write_official_manifest() -> None:
    rows = []
    paths = [
        "data/t2know-core-v1.0/document_disjoint/trainData.json",
        "data/t2know-core-v1.0/document_disjoint/evalData.json",
        "data/t2know-core-v1.0/document_disjoint/testData.json",
        "data/t2know-core-v1.0/document_disjoint/t2know_document_disjoint.jsonl",
        "data/t2know-core-v1.0/brat_core/documents",
        "data/t2know-core-v1.0/metadata/validation_report.json",
        "provenance/reports/reconstruction_manifest.tsv",
        "provenance/reports/reconstruction_sentence_manifest.tsv",
        "provenance/reports/corpus_stats_public_verifiable.json",
        "provenance/reports/split_by_text_status.tsv",
    ]
    for rel in paths:
        path = ROOT / rel
        if path.is_dir():
            sha = ""
            n_records = sum(1 for item in path.glob("*") if item.is_file())
        elif path.exists():
            sha = sha256_file(path)
            n_records = sum(1 for line in path.open(encoding="utf-8", errors="ignore") if line.strip()) - (
                1 if path.suffix == ".tsv" else 0
            )
        else:
            sha = ""
            n_records = 0
        rows.append(
            {
                "path": rel,
                "role": "official" if "document_disjoint" in rel or "brat_core/documents" in rel else "provenance",
                "official_benchmark": "yes" if "document_disjoint" in rel else "no",
                "headline_statistics": "yes" if "document_disjoint" in rel or "corpus_stats" in rel else "no",
                "contains_source_text": "mixed" if "document_disjoint" in rel else ("yes_text_included_only" if "brat_core/documents" in rel else "no"),
                "contains_synthetic": "no",
                "sha256": sha,
                "n_records": n_records,
                "n_documents": "",
                "notes": "T2KNOW-Core v1.0 public-redacted Option B release model",
            }
        )
    write_tsv(ROOT / "MANIFEST.official.tsv", rows)


def write_schemas() -> None:
    SCHEMA_DIR.mkdir(exist_ok=True)
    (SCHEMA_DIR / "t2know_public_redacted.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "T2KNOW public redacted JSONL record",
                "type": "object",
                "required": ["text", "entities", "meta"],
                "properties": {
                    "text": {"type": ["string", "null"]},
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["start", "end", "label", "text", "spans"],
                            "properties": {
                                "start": {"type": "integer", "minimum": 0},
                                "end": {"type": "integer", "minimum": 0},
                                "label": {"type": "string"},
                                "text": {"type": ["string", "null"]},
                                "spans": {"type": "array"},
                            },
                        },
                    },
                    "meta": {"type": "object"},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (SCHEMA_DIR / "t2know_predictions.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "T2KNOW annotation-only prediction record",
                "type": "object",
                "required": ["doc_id", "sentence_id", "split", "start", "end", "label", "seed", "model"],
                "properties": {
                    "doc_id": {"type": "string"},
                    "sentence_id": {"type": "string"},
                    "split": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                    "label": {"type": "string"},
                    "score": {"type": ["number", "null"]},
                    "seed": {"type": ["integer", "string"]},
                    "model": {"type": "string"},
                },
                "not": {"anyOf": [{"required": ["text"]}, {"required": ["entity_text"]}, {"required": ["surface"]}]},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (SCHEMA_DIR / "t2know_reconstructed_full.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "T2KNOW reconstructed full JSONL record",
                "type": "object",
                "required": ["text", "entities", "meta"],
                "properties": {"text": {"type": "string"}, "entities": {"type": "array"}, "meta": {"type": "object"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_checksums_public() -> None:
    excluded_parts = {
        "__pycache__",
        ".pytest_cache",
    }
    legacy_brat_prefixes = tuple(f"data/brat_core/{split}/" for split in ("train", "eval", "test"))
    legacy_core_brat_prefixes = tuple(f"data/t2know-core-v1.0/brat_core/{split}/" for split in ("train", "eval", "test"))
    skipped_prefixes = legacy_brat_prefixes + legacy_core_brat_prefixes + ("provenance/cache/",)
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(part in excluded_parts for part in path.parts):
            continue
        if rel == "checksums_public.sha256":
            continue
        if any(rel.startswith(prefix) for prefix in skipped_prefixes):
            continue
        rows.append(f"{sha256_file(path)}  {rel}")
    (ROOT / "checksums_public.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    audit = read_audit()
    brat_docs = read_brat_documents(BRAT_DIR)
    write_redacted_document_disjoint(audit, brat_docs)
    redacted_records = load_jsonl(DOC_DIR / "t2know_document_disjoint.jsonl")
    build_split_neutral_brat(audit, brat_docs)
    write_reconstruction_manifests(audit, redacted_records, brat_docs)
    write_stats_and_reports(audit, redacted_records)
    write_official_manifest()
    write_schemas()
    write_checksums_public()
    print("Applied rights-aware release metadata/redaction.")
    print("Note: legacy split-named BRAT folders were not removed by this non-destructive script.")


if __name__ == "__main__":
    main()
