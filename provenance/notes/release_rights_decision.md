# Release Rights Decision

The T2KNOW authors own the annotation layer, code, documentation, validation scripts, evaluation scripts, and release metadata generated for this project. Third-party scholarly abstract text has a separate rights status.

At the current revision stage, article-level redistribution licences have been audited through automated source matching plus a manual resolution pass for the remaining unresolved records. The manuscript and release documentation therefore must not claim that all source abstract text is covered by a blanket open data licence.

An automated source-licence audit was run after source matching through Europe PMC, Crossref, and OpenAlex. Remaining unresolved rows were reviewed using the supplied source-link intake file and supported candidate-search evidence. The final audit table is stored at `provenance/reports/source_license_audit_v6.tsv`; decision-specific subsets are stored at `provenance/reports/source_license_v6_include_text.tsv` and `provenance/reports/source_license_v6_exclude_text.tsv`. The final audit resolved all 821 records: 432 include-text candidates and 389 exclude-text rows. These results are metadata evidence, not a legal opinion.

Pre-submission decision: the final public release should use the conservative/hybrid route.

1. Include source text only for records with verified permissive redistribution evidence.
2. Release project-generated annotations, source identifiers where available, checksums, split assignments, provenance, validation outputs, and reconstruction instructions for all records.
3. Do not redistribute third-party source text for records listed in `provenance/reports/source_license_v6_exclude_text.tsv` unless later rightsholder permission or permissive licence evidence is obtained.

Current recommendation: use the conservative/hybrid route. Public text redistribution should be limited to the 432 rows in `source_license_v6_include_text.tsv` unless later legal review clears additional records. Rows in `source_license_v6_exclude_text.tsv` should not be redistributed as source text by default.

The API cache under `provenance/cache/` is a working audit artefact and may contain API-returned abstract text. If the final Zenodo deposit follows the conservative or hybrid route, this cache should be excluded or regenerated outside the public archive unless its contents are separately cleared for redistribution.

No file has been removed as part of this planning note. The current staged package remains a working release candidate, not the final legal deposit.
