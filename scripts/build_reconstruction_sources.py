#!/usr/bin/env python3
"""Build public source-resolution metadata for T2KNOW reconstruction."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "provenance/reports/source_license_audit_v6.tsv"
SENTENCE_MANIFEST = ROOT / "provenance/reports/reconstruction_sentence_manifest.tsv"
OUT = ROOT / "provenance/reports/reconstruction_sources.tsv"


def doi_url(doi: str) -> str:
    return f"https://doi.org/{doi}" if doi else ""


def pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""


def pmc_url(pmcid: str) -> str:
    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""


def europe_pmc_url(row: dict[str, str]) -> str:
    if row.get("pmid"):
        return f"https://europepmc.org/article/MED/{row['pmid']}"
    if row.get("pmcid"):
        return f"https://europepmc.org/article/PMC/{row['pmcid'].removeprefix('PMC')}"
    if row.get("doi"):
        return f"https://europepmc.org/search?query=DOI:{row['doi']}"
    return ""


def sentence_counts() -> dict[str, int]:
    counts: Counter[str] = Counter()
    with SENTENCE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            counts[row["doc_id"]] += 1
    return dict(counts)


def main() -> None:
    counts = sentence_counts()
    with AUDIT.open(newline="", encoding="utf-8") as src, OUT.open("w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src, delimiter="\t")
        fields = [
            "doc_id",
            "split",
            "source_file",
            "source_text_decision",
            "source_title",
            "doi",
            "doi_url",
            "pmid",
            "pubmed_url",
            "pmcid",
            "pmc_url",
            "europe_pmc_url",
            "source_url",
            "publication_year",
            "journal",
            "publisher",
            "license_evidence",
            "match_confidence",
            "match_reason",
            "normalized_document_sha256",
            "sentence_count",
            "reconstruction_note",
        ]
        writer = csv.DictWriter(dst, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in reader:
            doc_id = row["doc_id"]
            writer.writerow(
                {
                    "doc_id": doc_id,
                    "split": row["split"],
                    "source_file": row["source_file"],
                    "source_text_decision": row["source_text_decision"],
                    "source_title": row["source_title"],
                    "doi": row["doi"],
                    "doi_url": doi_url(row["doi"]),
                    "pmid": row["pmid"],
                    "pubmed_url": pubmed_url(row["pmid"]),
                    "pmcid": row["pmcid"],
                    "pmc_url": pmc_url(row["pmcid"]),
                    "europe_pmc_url": europe_pmc_url(row),
                    "source_url": row.get("source_url") or doi_url(row["doi"]) or pmc_url(row["pmcid"]) or pubmed_url(row["pmid"]),
                    "publication_year": row["publication_year"],
                    "journal": row["journal"],
                    "publisher": row["publisher"],
                    "license_evidence": row["epmc_license"]
                    or row["openalex_licenses"]
                    or row["unpaywall_licenses"]
                    or row["crossref_license_urls"],
                    "match_confidence": row["match_confidence"],
                    "match_reason": row["match_reason"],
                    "normalized_document_sha256": row["sha256_txt"],
                    "sentence_count": counts.get(doc_id, 0),
                    "reconstruction_note": "source text redistributed"
                    if row["source_text_decision"] == "include_text"
                    else "retrieve source text from the linked publication under your own access rights; verify normalized text against checksums",
                }
            )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
