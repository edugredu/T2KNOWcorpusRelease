# Public Hybrid Data Files

This directory contains public, rights-aware T2KNOW-Core data.

## Files

- `document_disjoint_hybrid/`: all reviewed sentence records. Records with `meta.source_text_decision = include_text` retain sentence text. Records with `meta.source_text_decision = exclude_text` have `text = null`, `text_redacted = true`, `text_sha256`, and `text_length`.
- `text_included/`: only records cleared for source-text redistribution.
- `text_excluded/annotations_only/`: records whose source text is not redistributed. Entity surface strings are removed, but labels, offsets, spans, document IDs, split assignments, and checksums are retained.
- `metadata/source_metadata.tsv`: document-level source metadata and audited redistribution status.

Offsets for redacted records refer to the original reviewed sentence strings. Reconstruct those strings from the original source publications using the source metadata and verify with the provided SHA-256 values.
