# Source Metadata

`source_metadata.tsv` is a document-level internal provenance table for T2KNOW-Core. It is generated from the reviewed document-disjoint JSONL release and linked BRAT files.

Recoverable fields include `doc_id`, split assignment, source file name, linked BRAT paths, sentence count, entity count, released-text flag, and SHA-256 checksums for linked BRAT files.

External bibliographic fields such as title, DOI, PMID, PMCID, publication year, journal, and article-level licence status were reconstructed where source matching supported them. Web of Science accessions were not preserved in the current archive and remain `not_available_in_current_archive`.

This table should not be interpreted as a legal opinion. Article-level text redistribution decisions are metadata-evidence decisions derived from `provenance/reports/source_license_audit_v6.tsv`: `include_text` means the row has a high-confidence source match and clear permissive licence evidence; `exclude_text` means source text should not be redistributed by default.
