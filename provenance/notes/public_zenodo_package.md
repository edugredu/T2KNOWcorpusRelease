# Public Zenodo Package

The rights-aware public Zenodo package was generated as a separate directory and ZIP file rather than by modifying or deleting files from the staged release candidate.

Final package:

- Directory: `release/T2KNOW-zenodo-public-v1.0.0-20260505-final/`
- ZIP: `release/T2KNOW-zenodo-public-v1.0.0-20260505-final.zip`

The package follows the audited hybrid release model:

- 821 reviewed source documents represented in the public annotation/provenance layer.
- 432 documents include source text because `source_license_audit_v6.tsv` marks them as `include_text`.
- 389 documents exclude source text because `source_license_audit_v6.tsv` marks them as `exclude_text`.
- Text-excluded sentence records retain labels, offsets, spans, split assignments, checksums, and source metadata, but have `text = null` and entity surface strings removed.
- BRAT `.txt` and `.ann` files are included only for the 432 text-included documents.
- API caches and source-link intake files are not included in the public ZIP.

Validation performed:

- Public package checksum manifest validates with `sha256sum -c checksums.sha256`.
- Public hybrid JSONL contains 14,356 sentence records: 7,665 text-included and 6,691 text-excluded.
- Text-included subset contains 432 BRAT `.txt` files and 432 BRAT `.ann` files.
- Text-excluded JSONL records have no sentence text and no entity surface text.
- Grep checks found no full excluded-source sentence strings in the public package.

A first failed build directory, `release/T2KNOW-zenodo-public-v1.0.0-20260505/`, was left in place because repository instructions prohibit deleting files without explicit confirmation. It should not be uploaded.
