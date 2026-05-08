# Source Licence Audit Summary

Generated from `source_license_audit_v6.tsv` using `scripts/audit_source_licenses.py`, `scripts/resolve_manual_source_links.py`, and the manually supplied source-link intake file.

This is a metadata and licence-evidence audit, not a legal opinion. Rows marked `include_text` are candidates for text redistribution because the recovered source match is high confidence and the licence evidence contains a clear permissive licence. Rows marked `exclude_text` should not be redistributed as source text by default.

## Counts

- Total audited rows: 821
- Include-text candidates: 432
- Exclude-text rows: 389
- Manual-review rows: 0

## Manual Resolution Pass

- Previously unresolved rows reviewed: 32
- Resolved as include-text: 7
- Resolved as exclude-text: 25
- Manual override table: `source_license_manual_overrides.tsv`
- Final audit table: `source_license_audit_v6.tsv`

## Match Confidence

| Confidence | Count |
|---|---:|
| high | 821 |

## Redistribution Decisions

| Decision | Count |
|---|---:|
| include_text | 432 |
| exclude_text | 389 |

## Most Common Decision Rationales

| Rationale | Count |
|---|---:|
| clear_permissive_licence:cc-by | 260 |
| clear_permissive_licence:cc-by\|cc-by-sa | 158 |
| restrictive_cc_licence:cc-by-nc-nd | 103 |
| restrictive_cc_licence:cc-by-nc | 60 |
| oa_status_not_redistributable:closed | 56 |
| oa_status_not_redistributable:bronze | 33 |
| tdm_licence_only | 20 |
| no_clear_redistribution_licence | 14 |
| restrictive_cc_licence:cc-by-nc-sa | 10 |
| unclassified_licence:http://onlinelibrary.wiley.com/termsandconditions#vor | 9 |
| unclassified_licence:https://www.elsevier.com/legal/tdmrep-license\|https://www.elsevier.com/tdm/userlicense/1.0 | 9 |
| unclassified_licence:http://onlinelibrary.wiley.com/termsandconditions#vor\|other-oa | 9 |
| unclassified_licence:https://doi.org/10.15223/policy-004\|https://doi.org/10.15223/policy-012\|https://doi.org/10.15223/policy-017\|https://doi.org/10.15223/policy-029\|https://doi.org/10.15223/policy-037\|https://www.elsevier.com/legal/tdmrep-license\|https://www.elsevier.com/tdm/userlicense/1.0 | 8 |
| manual_resolution:supported_candidate_search; candidate_source_oa_status:closed; no permissive redistribution licence identified; provider=openalex; candidate_rank=1 | 7 |
| manual_resolution:manual_link_intake_pubmed; restrictive_or_noncommercial_source_licence:cc-by-nc-nd;  | 7 |
| unclassified_licence:https://doi.org/10.15223/policy-029\|https://doi.org/10.15223/policy-037\|https://doi.org/10.15223/policy-045 | 4 |
| manual_resolution:manual_link_intake_pubmed; permissive_source_licence:cc-by;  | 4 |
| unclassified_licence:https://journals.sagepub.com/page/policies/text-and-data-mining-license | 4 |
| manual_resolution:manual_link_intake_pubmed; no_permissive_redistribution_licence_identified;  | 3 |
| unclassified_licence:http://www.elsevier.com/open-access/userlicense/1.0\|https://doi.org/10.15223/policy-004\|https://doi.org/10.15223/policy-012\|https://doi.org/10.15223/policy-017\|https://doi.org/10.15223/policy-029\|https://doi.org/10.15223/policy-037\|https://www.elsevier.com/legal/tdmrep-license\|https://www.elsevier.com/tdm/userlicense/1.0 | 3 |

## Recommendation

- Public text redistribution should be limited to rows in `source_license_v6_include_text.tsv` unless later legal review clears additional records.
- Rows in `source_license_v6_exclude_text.tsv` have closed access, no clear permissive licence, TDM-only licence evidence, or restrictive Creative Commons terms such as NC or ND.
- The release can still distribute project-generated annotations, source identifiers, checksums, metadata, and reconstruction instructions for rows not cleared for text redistribution.
- API caches under `provenance/cache/` are working audit artefacts and should not be included in a public conservative/hybrid deposit unless separately cleared.
