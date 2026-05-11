#!/usr/bin/env python3
"""Create the rights-aware public Zenodo package for T2KNOW.

The staged release contains full text for inspection. This builder creates a
separate public package that keeps source text only for records cleared by the
v6 source-licence audit and redacts source text for excluded records.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PARENT = ROOT.parent
PACKAGE_NAME = "T2KNOW-public-upload-v1.0.0-20260511-r22"
OUT_DIR = OUT_PARENT / PACKAGE_NAME
ZIP_PATH = OUT_PARENT / f"{PACKAGE_NAME}.zip"

AUDIT = ROOT / "provenance/reports/source_license_audit_v6.tsv"
DOC_DIR = ROOT / "data/document_disjoint"
JSONL = DOC_DIR / "t2know_document_disjoint.jsonl"
BRAT_CORE = ROOT / "data/brat_core"

SENSITIVE_AUDIT_COLUMNS = {"query_used", "decision_rationale"}
SENSITIVE_OVERRIDE_COLUMNS = {"notes", "decision_rationale"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_audit() -> dict[str, dict[str, str]]:
    rows = list(csv.DictReader(AUDIT.open(newline=""), delimiter="\t"))
    by_doc = {row["doc_id"]: row for row in rows}
    counts = Counter(row["source_text_decision"] for row in rows)
    if len(by_doc) != 821 or counts != {"include_text": 432, "exclude_text": 389}:
        raise RuntimeError(f"Unexpected audit counts: rows={len(by_doc)} counts={counts}")
    return by_doc


def ensure_new_output() -> None:
    if OUT_DIR.exists():
        raise SystemExit(f"Refusing to overwrite existing package directory: {OUT_DIR}")
    if ZIP_PATH.exists():
        raise SystemExit(f"Refusing to overwrite existing package zip: {ZIP_PATH}")
    OUT_DIR.mkdir(parents=True)


def copy_tree(src: Path, dst: Path, ignore_dirs: set[str] | None = None) -> None:
    ignore_dirs = ignore_dirs or set()

    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in ignore_dirs}
        ignored |= {name for name in names if name == "__pycache__" or name.endswith(".pyc")}
        return ignored

    shutil.copytree(src, dst, ignore=ignore)


def copy_static_files() -> None:
    for name in ["LICENSE", "CITATION.cff", "OFFICIAL_BENCHMARK.md", "MANIFEST.official.tsv", "REPRODUCIBILITY.md"]:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUT_DIR / name)
    for dirname in ["docs", "code"]:
        copy_tree(ROOT / dirname, OUT_DIR / dirname, ignore_dirs={"__pycache__", ".pytest_cache"})
    scripts_out = OUT_DIR / "scripts"
    scripts_out.mkdir()
    excluded_scripts = {
        "audit_source_licenses.py",
        "resolve_manual_source_links.py",
        "create_public_zenodo_package.py",
    }
    for script in sorted((ROOT / "scripts").glob("*.py")):
        if script.name in excluded_scripts:
            continue
        shutil.copy2(script, scripts_out / script.name)
    sanitize_public_docs()



def sanitize_public_docs() -> None:
    """Remove source-text examples and legacy/auxiliary path references from copied documentation."""
    data_format_md = OUT_DIR / "docs/data_format.md"
    release_manifest_md = OUT_DIR / "docs/RELEASE_MANIFEST.md"
    dataset_policy_md = OUT_DIR / "docs/dataset_policy.md"
    path_replacements = {
        "data/t2know-core-v1.0/document_disjoint/t2know_document_disjoint.jsonl": "data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl",
        "data/t2know-core-v1.0/document_disjoint/": "data/t2know-core-v1.0/document_disjoint_hybrid/",
        "data/t2know-core-v1.0/document_disjoint": "data/t2know-core-v1.0/document_disjoint_hybrid",
        "data/t2know-core-v1.0/brat_core/documents/": "data/t2know-core-v1.0/text_included/brat_core/",
        "data/t2know-core-v1.0/brat_core/": "data/t2know-core-v1.0/text_included/brat_core/",
        "data/t2know-core-v1.0/brat_core": "data/t2know-core-v1.0/text_included/brat_core",
    }
    for doc in sorted((OUT_DIR / "docs").glob("*.md")):
        text = doc.read_text(encoding="utf-8")
        for old, new in path_replacements.items():
            text = text.replace(old, new)
        text = text.replace("document_disjoint_hybrid_hybrid", "document_disjoint_hybrid")
        # Strip stale archive-level commit/checksum/DOI claims so the public
        # package does not embed self-referential metadata that is only true
        # after upload.
        text = re.sub(
            r"- Release commit: `[^`]+`\n- Release asset: `[^`]+`\n- Release asset SHA-256: `[^`]+`",
            "- Release commit: recorded on the GitHub release page after upload.\n"
            "- Release asset: recorded on the GitHub release page after upload.\n"
            "- Release asset SHA-256: recorded externally after upload; file-level checksums are in `checksums.sha256`.",
            text,
        )
        # Strip archive-level commit/asset/checksum claims (these change per package).
        # Keep the permanent repository URL and DOI.
        text = re.sub(
            r", commit `[^`]+`\. The release asset is `[^`]+`, with SHA-256 checksum `[^`]+`",
            "",
            text,
        )
        text = re.sub(
            r"The release commit is `[^`]+`, and the attached archive `[^`]+` has SHA-256 checksum `[^`]+`\. File-level checksums are provided in `[^`]+`\. ",
            "The final release commit and archive-level checksum are recorded on the GitHub release page. File-level checksums are provided in `checksums.sha256`. ",
            text,
        )
        doc.write_text(text, encoding="utf-8")

    # --- data_format.md: strip legacy sections, source-text examples, stale paths ---
    if data_format_md.exists():
        text = data_format_md.read_text(encoding="utf-8")
        # Remove "Supporting compatibility files" through "Legacy mixed BRAT compatibility export" sections
        text = re.sub(
            r'### Supporting compatibility files\n\n.*?(?=## Reviewed JSONL Format)',
            '',
            text,
            flags=re.DOTALL,
        )
        # Remove legacy validation block: sentence_level_legacy JSONL + split JSON + aux + brat_auxiliary
        text = re.sub(
            r'(Command:\n\n```bash\n)python3 scripts/validate_corpus\.py data/sentence_level_legacy/t2know\.jsonl --format jsonl\n',
            r'\1',
            text,
        )
        text = re.sub(
            r'python3 scripts/validate_corpus\.py data/t2know-core-v1\.0/document_disjoint/t2know_document_disjoint\.jsonl --format jsonl\n',
            'python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl\n',
            text,
        )
        # Remove sentence_level_legacy observed-result block
        text = re.sub(
            r'Observed result for `data/sentence_level_legacy/t2know\.jsonl`:\n\n(?:.*\n)*?(?=Observed result for `data/t2know-core)',
            '',
            text,
        )
        # Update observed result header for document_disjoint
        text = text.replace(
            'Observed result for `data/t2know-core-v1.0/document_disjoint/t2know_document_disjoint.jsonl`:',
            'Observed result for `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`:',
        )
        # Remove split JSON legacy commands and results
        text = re.sub(
            r'(Command:\n\n```bash\n)python3 scripts/validate_corpus\.py data/sentence_level_legacy --format json\n',
            r'\1',
            text,
        )
        text = re.sub(
            r'python3 scripts/validate_corpus\.py data/auxiliary --format json\n',
            '',
            text,
        )
        text = re.sub(
            r'python3 scripts/validate_corpus\.py data/brat_auxiliary --format brat\n',
            '',
            text,
        )
        text = re.sub(
            r'Observed result for `data/sentence_level_legacy`:\n\n(?:.*\n)*?(?=Observed result for `data/auxiliary`)',
            '',
            text,
        )
        text = re.sub(
            r'Observed result for `data/auxiliary`:\n\n(?:.*\n)*?(?=Observed result for `data/t2know-core)',
            '',
            text,
        )
        text = re.sub(
            r'Observed result for `data/brat_auxiliary`:\n\n(?:.*\n)*?(?=Validator note:)',
            '',
            text,
        )
        # Update brat_core observed result header
        text = text.replace(
            'Observed result for `data/t2know-core-v1.0/brat_core`:',
            'Observed result for `data/t2know-core-v1.0/text_included/brat_core`:',
        )
        # Strip legacy interpretation lines
        text = re.sub(
            r'- The older sentence-level split files under `data/sentence_level_legacy/`.*\n',
            '',
            text,
        )
        text = re.sub(
            r'- The paper should treat `data/auxiliary/trainBalanced\.json` as an auxiliary training artefact\.\n',
            '',
            text,
        )
        text = re.sub(
            r'- The paper should treat `data/brat_auxiliary/` and the mixed `data/brat/`.*\n',
            '',
            text,
        )
        # Replace source-text examples with redacted forms
        replacements = {
            "`data/document_disjoint/t2know_document_disjoint.jsonl` and `data/sentence_level_legacy/t2know.jsonl` store one JSON object per line.":
                "`data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl` stores one JSON object per line. In the public package, source text is present only for records marked `include_text`; records marked `exclude_text` use redacted text fields and reconstruction metadata.",
            "\"text\": \"Huntington's disease is a neurodegenerative autosomal disease results due to expansion of polymorphic CAG repeats in the huntingtin gene.\",":
                '"text": null,',
            "\"text\": \"Huntington's disease\",":
                '"surface_text_redacted": true,',
            '"doc_id": "0",':
                '"doc_id": "0",',
            "\"text\": \"Tremor, muscle stiffness, and slowness of movement are symptoms of Parkinson's disease.\",":
                '"text": null,',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.replace('    "brat_txt_path": "data/brat_core/train/0text0.txt",\n    "brat_ann_path": "data/brat_core/train/0text0.ann"',
                            '    "source_text_decision": "exclude_text",\n    "public_text_included": false')
        text = text.replace('    "brat_txt_path": "data/brat_core/train/0text1.txt",\n    "brat_ann_path": "data/brat_core/train/0text1.ann"',
                            '    "source_text_decision": "exclude_text",\n    "public_text_included": false')
        # Remove "and `trainBalanced.json`" from split JSON format section
        text = text.replace(
            "The split files `trainData.json`, `evalData.json`, `testData.json`, and `trainBalanced.json` use",
            "The split files `trainData.json`, `evalData.json`, and `testData.json` use",
        )
        text = text.replace(
            "- `trainBalanced.json`: `id`, `text`, `tags`, `sentences`\n",
            "",
        )
        if "## Public hybrid note" not in text:
            text += """

## Public hybrid note

The public Zenodo package intentionally redacts `text` and entity surface strings for records marked `exclude_text` in `provenance/reports/source_license_audit_v6.tsv`. Offsets, spans, labels, checksums, source identifiers, and reconstruction metadata are retained.
"""
        data_format_md.write_text(text, encoding="utf-8")

    # --- RELEASE_MANIFEST.md: strip Supporting Corpus Artefacts section ---
    if release_manifest_md.exists():
        text = release_manifest_md.read_text(encoding="utf-8")
        text = re.sub(
            r'## Supporting Corpus Artefacts\n\n.*?(?=## Commit and Tag Recommendation)',
            '',
            text,
            flags=re.DOTALL,
        )
        # Strip legacy paths from Commit and Tag Recommendation
        text = re.sub(
            r'- `data/sentence_level_legacy/` for compatibility/provenance files,\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/auxiliary/` for balanced or other auxiliary training artefacts,\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/brat_auxiliary/` for auxiliary BRAT artefacts,\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/brat/` for legacy mixed BRAT compatibility only,\n',
            '',
            text,
        )
        release_manifest_md.write_text(text, encoding="utf-8")

    # --- dataset_policy.md: strip legacy/auxiliary path references ---
    if dataset_policy_md.exists():
        text = dataset_policy_md.read_text(encoding="utf-8")
        # Remove sentence_level_legacy file list
        text = re.sub(
            r'- `data/sentence_level_legacy/trainData\.json`\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/evalData\.json`\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/testData\.json`\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/t2know\.jsonl`\n',
            '',
            text,
        )
        text = re.sub(
            r'`data/auxiliary/trainBalanced\.json` and `data/brat_auxiliary/` are \*\*auxiliary training artefacts\*\*\.\n',
            '',
            text,
        )
        # Remove legacy sentence counts
        text = re.sub(
            r'- `data/sentence_level_legacy/trainData\.json`: `\d+` lines\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/auxiliary/trainBalanced\.json`: `\d+` lines\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/evalData\.json`: `\d+` lines\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/testData\.json`: `\d+` lines\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/sentence_level_legacy/t2know\.jsonl`: `\d+` records\n',
            '',
            text,
        )
        text = re.sub(
            r'Current split counts observed in `data/sentence_level_legacy/t2know\.jsonl`:\n(?:- `[^`]+`: `\d+`\n)*',
            '',
            text,
        )
        # Remove Legacy mixed BRAT compatibility path section
        text = re.sub(
            r'### Legacy mixed BRAT compatibility path\n\n`data/brat/` is retained.*?(?=\n## Manuscript policy)',
            '',
            text,
            flags=re.DOTALL,
        )
        # Remove Repository facts section (legacy/auxiliary counts not in public package)
        text = re.sub(
            r'## Repository facts used for this policy\n\nCurrent file counts:\n(?:- `data/sentence_level.*\n)*',
            '',
            text,
        )
        text = re.sub(
            r'- `data/brat_auxiliary/`:.*\n',
            '',
            text,
        )
        text = re.sub(
            r'- `data/t2know-core-v1\.0/brat_core/`:.*\n',
            '- `data/t2know-core-v1.0/text_included/brat_core/`: 432 `.txt` files and 432 `.ann` files (text-included only)\n',
            text,
        )
        text = re.sub(
            r"Current split counts observed in `data/t2know-core-v1\.0/document_disjoint/t2know_document_disjoint\.jsonl`:",
            "Current split counts observed in `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`:",
            text,
        )
        dataset_policy_md.write_text(text, encoding="utf-8")

def public_root_readme() -> str:
    return """# T2KNOW-Core Public Release

This repository contains the rights-aware public release package for T2KNOW-Core v1.0.0, a biomedical nested named entity recognition resource focused on Huntington's disease literature.

## Repository, Licence, and Citation

- Public repository: <https://github.com/edugredu/T2KNOWcorpusRelease>
- Version tag: `t2know-core-v1.0.0`
- Licence: MIT for project-generated annotations, metadata, documentation, validation scripts, evaluation scripts, and benchmark code.
- Third-party scholarly abstract text remains governed by the original publication licences and publisher terms. Source text is redistributed only for records cleared by the source-licence audit.

Citation metadata is provided in `CITATION.cff`. Use the immutable Zenodo version DOI shown on the final Zenodo record and in the accompanying paper.

## Release Model

The package follows a hybrid release model. The complete project-generated annotation, metadata, provenance, validation, evaluation, and benchmark layers are provided for all 821 reviewed source documents. Third-party source text is redistributed only where the source-licence audit found high-confidence source matches and permissive redistribution evidence.

- Total reviewed source documents: 821
- Source-text included records: 432
- Source-text excluded records: 389
- Final audit: `provenance/reports/source_license_audit_v6.tsv`
- Text-included subset: `provenance/reports/source_license_v6_include_text.tsv`
- Text-excluded subset: `provenance/reports/source_license_v6_exclude_text.tsv`
- Manual resolution evidence: `provenance/reports/source_license_manual_overrides.tsv`

The audit is metadata/licence evidence, not legal advice. Source text for records marked `exclude_text` is not redistributed in this public package.

## Data Layout

- `data/t2know-core-v1.0/document_disjoint_hybrid/`: all 821 reviewed documents at sentence level. Text is present for `include_text` records and redacted for `exclude_text` records.
- `data/t2know-core-v1.0/text_included/`: full-text JSON/JSONL and BRAT files for the 432 records cleared for redistribution.
- `data/t2know-core-v1.0/text_excluded/annotations_only/`: annotation-only JSON/JSONL for the 389 records whose source text is not redistributed.
- `data/t2know-core-v1.0/metadata/`: label schema, source metadata, source-selection provenance, and validation metadata.
- `docs/`: data format, reconstruction, policy, evaluation, and annotation guidance.
- `provenance/`: source-selection, release-decision, validation, statistics, and benchmark provenance.
- `scripts/` and `code/`: validation, reconstruction, evaluation, and benchmark reproduction support.
- `predictions/`: archived annotation-only benchmark predictions for reproducing the reported public metrics.

For text-excluded records, users should reconstruct source text from the original publications according to their own access rights and publisher terms. The operational workflow, source lookup order, normalization policy, checksum algorithm, validation command, and failure handling are specified in `docs/reconstruction.md`. Offsets and checksums are provided to support reconstruction and verification.

## Recommended Entry Points

- **Official benchmark specification: `OFFICIAL_BENCHMARK.md`** — defines the official benchmark files, split unit, evaluation commands, and excluded artefacts
- Main benchmark data: `data/t2know-core-v1.0/document_disjoint_hybrid/`
- Text-included BRAT inspection export: `data/t2know-core-v1.0/text_included/brat_core/`
- Reconstruction instructions: `docs/reconstruction.md`
- Release policy and licence boundary: `docs/dataset_policy.md`
- Corpus statistics verification notes: `provenance/reports/corpus_stats_public_verifiable.json`
- Reconstructed-full statistics notes: `provenance/reports/corpus_stats_reconstructed_full.json`

## Checksums

Run from this directory:

```bash
sha256sum -c checksums.sha256
```

## Benchmark Table Reproduction

The archived prediction files under `predictions/` are annotation-only public artifacts. Run from this directory:

```bash
python3 scripts/reproduce_benchmark_tables.py \
  --prediction-root predictions \
  --out provenance/reports/reproduced_benchmark_tables_public_redacted \
  --annotation-only
```

The rounded overlap-aware F1 means should be `0.6498` for BiomedBERT, `0.6102` for BioBERT, and `0.7206` for W2NER + BiomedBERT. Encoder model identifiers and recoverable revision status are recorded in `provenance/reports/model_revision_metadata.tsv`; exact Hugging Face revision hashes were not recoverable from archived local evidence.
"""


def public_data_readme() -> str:
    return """# Public Hybrid Data Files

This directory contains public, rights-aware T2KNOW-Core data.

## Files

- `document_disjoint_hybrid/`: all reviewed sentence records. Records with `meta.source_text_decision = include_text` retain sentence text. Records with `meta.source_text_decision = exclude_text` have `text = null`, `text_redacted = true`, `text_sha256`, and `text_length`.
- `text_included/`: only records cleared for source-text redistribution.
- `text_excluded/annotations_only/`: records whose source text is not redistributed. Entity surface strings are removed, but labels, offsets, spans, document IDs, split assignments, and checksums are retained.
- `metadata/source_metadata.tsv`: document-level source metadata and audited redistribution status.

Offsets for redacted records refer to the original reviewed sentence strings. Reconstruct those strings from the original source publications using the source metadata and verify with the provided SHA-256 values.
"""


def sanitize_split_record(record: dict[str, Any], audit: dict[str, dict[str, str]]) -> dict[str, Any]:
    doc_id = str(record["meta"]["doc_id"])
    decision = audit[doc_id]["source_text_decision"]
    out = json.loads(json.dumps(record))
    text = out.get("text", "")
    out["meta"]["source_text_decision"] = decision
    out["meta"]["public_text_included"] = decision == "include_text"
    out["meta"]["source_title"] = audit[doc_id].get("source_title") or None
    out["meta"]["doi"] = audit[doc_id].get("doi") or None
    out["meta"]["pmid"] = audit[doc_id].get("pmid") or None
    out["meta"]["pmcid"] = audit[doc_id].get("pmcid") or None
    if decision == "exclude_text":
        out["text_sha256"] = out["meta"].get("sentence_sha256") or sha256_text(text or "")
        out["text_length"] = out["meta"].get("sentence_char_length") or len(text or "")
        out["text_redacted"] = True
        out["text"] = None
        for key in ("brat_txt_path", "brat_ann_path"):
            out["meta"].pop(key, None)
    else:
        out["text_redacted"] = False
    return out


def sanitize_jsonl_record(record: dict[str, Any], audit: dict[str, dict[str, str]]) -> dict[str, Any]:
    doc_id = str(record["meta"]["doc_id"])
    decision = audit[doc_id]["source_text_decision"]
    out = json.loads(json.dumps(record))
    text = out.get("text", "")
    out["meta"]["source_text_decision"] = decision
    out["meta"]["public_text_included"] = decision == "include_text"
    out["meta"]["source_title"] = audit[doc_id].get("source_title") or None
    out["meta"]["doi"] = audit[doc_id].get("doi") or None
    out["meta"]["pmid"] = audit[doc_id].get("pmid") or None
    out["meta"]["pmcid"] = audit[doc_id].get("pmcid") or None
    if decision == "exclude_text":
        out["text_sha256"] = out["meta"].get("sentence_sha256") or sha256_text(text or "")
        out["text_length"] = out["meta"].get("sentence_char_length") or len(text or "")
        out["text_redacted"] = True
        out["text"] = None
        for key in ("brat_txt_path", "brat_ann_path"):
            out["meta"].pop(key, None)
        for ent in out.get("entities", []):
            ent.pop("text", None)
            ent["surface_text_redacted"] = True
    else:
        out["text_redacted"] = False
    return out


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_public_source_metadata(src: Path, dst: Path) -> None:
    rows = list(csv.DictReader(src.open(newline="", encoding="utf-8"), delimiter="\t"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        for row in rows:
            if row.get("abstract_licence_status") == "include_text":
                source_file = row.get("source_file") or ""
                row["brat_txt_path"] = f"data/t2know-core-v1.0/text_included/brat_core/{row.get('split')}/{source_file}"
                row["brat_ann_path"] = row["brat_txt_path"].replace(".txt", ".ann")
            else:
                row["brat_txt_path"] = "not_redistributed_in_public_package"
                row["brat_ann_path"] = "not_redistributed_in_public_package"
            writer.writerow(row)


def build_document_data(audit: dict[str, dict[str, str]]) -> None:
    core = OUT_DIR / "data/t2know-core-v1.0"
    (core / "document_disjoint_hybrid").mkdir(parents=True)
    (core / "text_included/document_disjoint").mkdir(parents=True)
    (core / "text_excluded/annotations_only").mkdir(parents=True)
    (core / "metadata").mkdir(parents=True)
    (core / "README_PUBLIC_HYBRID.md").write_text(public_data_readme(), encoding="utf-8")

    sentence_counts = Counter()
    entity_counts = Counter()
    doc_sets = defaultdict(set)

    for split_file in ["trainData.json", "evalData.json", "testData.json"]:
        hybrid_records = []
        include_records = []
        exclude_records = []
        for line in (DOC_DIR / split_file).open(encoding="utf-8"):
            original = json.loads(line)
            doc_id = str(original["meta"]["doc_id"])
            decision = audit[doc_id]["source_text_decision"]
            hybrid = sanitize_split_record(original, audit)
            hybrid_records.append(hybrid)
            sentence_counts[("hybrid", decision)] += 1
            entity_counts[("hybrid", decision)] += len(original.get("tags", []))
            doc_sets[("hybrid", decision)].add(doc_id)
            if decision == "include_text":
                include_records.append(hybrid)
            else:
                exclude_records.append(hybrid)
        write_jsonl(core / "document_disjoint_hybrid" / split_file, hybrid_records)
        write_jsonl(core / "text_included/document_disjoint" / split_file, include_records)
        write_jsonl(core / "text_excluded/annotations_only" / split_file, exclude_records)

    hybrid_jsonl = []
    include_jsonl = []
    exclude_jsonl = []
    for line in JSONL.open(encoding="utf-8"):
        original = json.loads(line)
        doc_id = str(original["meta"]["doc_id"])
        decision = audit[doc_id]["source_text_decision"]
        hybrid = sanitize_jsonl_record(original, audit)
        hybrid_jsonl.append(hybrid)
        if decision == "include_text":
            include_jsonl.append(hybrid)
        else:
            exclude_jsonl.append(hybrid)
    write_jsonl(core / "document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl", hybrid_jsonl)
    write_jsonl(core / "text_included/document_disjoint/t2know_document_disjoint_text_included.jsonl", include_jsonl)
    write_jsonl(core / "text_excluded/annotations_only/t2know_document_disjoint_annotations_only.jsonl", exclude_jsonl)

    # Copy metadata files; these contain no source abstract text beyond bibliographic titles and decisions.
    for src in sorted((ROOT / "data/t2know-core-v1.0/metadata").glob("*")):
        if src.is_file():
            dst = core / "metadata" / src.name
            if src.name == "source_metadata.tsv":
                write_public_source_metadata(src, dst)
            else:
                shutil.copy2(src, dst)

    summary = {
        "release_model": "rights-aware hybrid",
        "documents_total": 821,
        "documents_text_included": len({r["doc_id"] for r in audit.values() if r["source_text_decision"] == "include_text"}),
        "documents_text_excluded": len({r["doc_id"] for r in audit.values() if r["source_text_decision"] == "exclude_text"}),
        "sentences_total": len(hybrid_jsonl),
        "sentences_text_included": len(include_jsonl),
        "sentences_text_excluded": len(exclude_jsonl),
        "entities_total": sum(len(r.get("entities", [])) for r in hybrid_jsonl),
        "entities_text_included": sum(len(r.get("entities", [])) for r in include_jsonl),
        "entities_text_excluded": sum(len(r.get("entities", [])) for r in exclude_jsonl),
        "source_text_rule": "Source text is present only for include_text records. For exclude_text records, text and entity surface strings are redacted.",
    }
    (core / "public_hybrid_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def find_brat_pair(source_file: str) -> tuple[Path, Path]:
    for split in ["train", "eval", "test", "val"]:
        txt = BRAT_CORE / split / source_file
        ann = txt.with_suffix(".ann")
        if txt.exists() and ann.exists():
            return txt, ann
    raise FileNotFoundError(source_file)


def copy_included_brat(audit: dict[str, dict[str, str]]) -> None:
    out_root = OUT_DIR / "data/t2know-core-v1.0/text_included/brat_core"
    copied = set()
    for row in audit.values():
        if row["source_text_decision"] != "include_text":
            continue
        txt, ann = find_brat_pair(row["source_file"])
        rel_split = txt.parent.name
        dst_dir = out_root / rel_split
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(txt, dst_dir / txt.name)
        shutil.copy2(ann, dst_dir / ann.name)
        copied.add(row["doc_id"])
    if len(copied) != 432:
        raise RuntimeError(f"Expected 432 included BRAT documents, copied {len(copied)}")
    (out_root / "README.md").write_text(
        "# Text-Included BRAT Core\n\nThis directory contains BRAT `.txt` and `.ann` files only for source documents marked `include_text` in `provenance/reports/source_license_audit_v6.tsv`. Source text for `exclude_text` records is not redistributed in this public package.\n",
        encoding="utf-8",
    )


def sanitize_tsv(src: Path, dst: Path, remove_columns: set[str]) -> None:
    rows = list(csv.DictReader(src.open(newline=""), delimiter="\t"))
    fields = [f for f in rows[0].keys() if f not in remove_columns]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, delimiter="\t", fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def copy_public_provenance() -> None:
    prov = OUT_DIR / "provenance"
    (prov / "notes").mkdir(parents=True)
    (prov / "reports").mkdir(parents=True)
    shutil.copy2(ROOT / "provenance/source_selection_queries.tsv", prov / "source_selection_queries.tsv")
    for name in ["release_rights_decision.md", "source_selection.md", "split_tradeoff.md", "document_disjoint_label_coverage.md"]:
        src = ROOT / "provenance/notes" / name
        if src.exists():
            shutil.copy2(src, prov / "notes" / name)
    for name in [
        "source_license_audit_summary.md",
        "document_disjoint_doc_ids.csv",
        "document_disjoint_doc_ids_train.txt",
        "document_disjoint_doc_ids_val.txt",
        "document_disjoint_doc_ids_test.txt",
        "document_disjoint_label_counts.csv",
        "document_disjoint_split_candidate.json",
        "document_disjoint_split_validation.json",
        "original_11_doc_iaa_legacy_table.json",
        "original_11_doc_iaa_summary.json",
        "split_tradeoff_analysis.json",
        "reconstruction_sources.tsv",
        "reconstruction_manifest.tsv",
        "reconstruction_sentence_manifest.tsv",
        "benchmark_raw_counts.tsv",
        "benchmark_summary.tsv",
        "model_revision_metadata.tsv",
        "corpus_stats_public_verifiable.json",
        "corpus_stats_reconstructed_full.json",
    ]:
        src = ROOT / "provenance/reports" / name
        if src.exists():
            shutil.copy2(src, prov / "reports" / name)
    for name in ["source_license_audit_v6.tsv", "source_license_v6_include_text.tsv", "source_license_v6_exclude_text.tsv"]:
        sanitize_tsv(ROOT / "provenance/reports" / name, prov / "reports" / name, SENSITIVE_AUDIT_COLUMNS)
    sanitize_tsv(
        ROOT / "provenance/reports/source_license_manual_overrides.tsv",
        prov / "reports/source_license_manual_overrides.tsv",
        SENSITIVE_OVERRIDE_COLUMNS,
    )
    reproduced = ROOT / "provenance/reports/reproduced_benchmark_tables_public_redacted"
    if reproduced.exists():
        copy_tree(reproduced, prov / "reports/reproduced_benchmark_tables_public_redacted", ignore_dirs={"__pycache__", ".pytest_cache"})


def copy_public_benchmark_artifacts() -> None:
    src = ROOT / "predictions"
    if not src.exists():
        return
    dst = OUT_DIR / "predictions"
    copy_tree(src, dst, ignore_dirs={"__pycache__", ".pytest_cache"})


def write_checksums() -> None:
    files = sorted(p for p in OUT_DIR.rglob("*") if p.is_file() and p.name != "checksums.sha256")
    with (OUT_DIR / "checksums.sha256").open("w", encoding="utf-8") as f:
        for p in files:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            f.write(f"{h}  {p.relative_to(OUT_DIR).as_posix()}\n")


def zip_package() -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(Path(PACKAGE_NAME) / p.relative_to(OUT_DIR)))


def leakage_checks(audit: dict[str, dict[str, str]]) -> None:
    # Ensure excluded text is redacted in the public JSON files and excluded BRAT text files are absent.
    excluded = {doc_id for doc_id, row in audit.items() if row["source_text_decision"] == "exclude_text"}
    included = {doc_id for doc_id, row in audit.items() if row["source_text_decision"] == "include_text"}
    hybrid = OUT_DIR / "data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl"
    counts = Counter()
    for line in hybrid.open(encoding="utf-8"):
        obj = json.loads(line)
        doc_id = str(obj["meta"]["doc_id"])
        if doc_id in excluded:
            if obj.get("text") is not None or not obj.get("text_redacted"):
                raise RuntimeError(f"Excluded record leaked text: {doc_id}")
            for ent in obj.get("entities", []):
                if "text" in ent:
                    raise RuntimeError(f"Excluded entity leaked surface text: {doc_id}")
        if doc_id in included and obj.get("text") is None:
            raise RuntimeError(f"Included record missing text: {doc_id}")
        counts[obj["meta"]["source_text_decision"]] += 1
    if not counts["include_text"] or not counts["exclude_text"]:
        raise RuntimeError(f"Unexpected hybrid counts: {counts}")

    brat_files = list((OUT_DIR / "data/t2know-core-v1.0/text_included/brat_core").rglob("*.txt"))
    if len(brat_files) != 432:
        raise RuntimeError(f"Expected 432 included .txt files, found {len(brat_files)}")

    # Probe known excluded snippets that previously appeared in source text or matching queries.
    forbidden = [
        "Huntington's disease is a neurodegenerative autosomal disease results due to expansion",
        "Tremor, muscle stiffness, and slowness of movement are symptoms of Parkinson's disease",
        "We examined longitudinal cerebrospinal fluid (CSF) Alzheimer's disease",
    ]
    text_files = [p for p in OUT_DIR.rglob("*") if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".tsv", ".md", ".txt", ".cff"}]
    for p in text_files:
        data = p.read_text(encoding="utf-8", errors="ignore")
        for snippet in forbidden:
            if snippet in data:
                raise RuntimeError(f"Forbidden excluded-source snippet found in {p.relative_to(OUT_DIR)}")


def main() -> None:
    ensure_new_output()
    audit = read_audit()
    (OUT_DIR / "README.md").write_text(public_root_readme(), encoding="utf-8")
    copy_static_files()
    build_document_data(audit)
    copy_included_brat(audit)
    copy_public_provenance()
    copy_public_benchmark_artifacts()
    leakage_checks(audit)
    write_checksums()
    zip_package()
    print(json.dumps({
        "package_dir": str(OUT_DIR),
        "zip": str(ZIP_PATH),
        "documents": 821,
        "text_included_documents": 432,
        "text_excluded_documents": 389,
    }, indent=2))


if __name__ == "__main__":
    main()
