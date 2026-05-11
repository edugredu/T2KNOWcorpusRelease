# Zenodo Upload Checklist

Use this checklist before creating the final Zenodo DOI.

## Required Before Upload

- Confirm final author list and update `CITATION.cff`.
- Confirm the final licence boundary: MIT can cover project-generated code/documentation/metadata/annotations, while third-party abstract text remains governed by the original article licences.
- Use the rights-aware hybrid release model documented in `provenance/reports/source_license_audit_v6.tsv`.
- Publicly redistribute source text only for the 432 records in `provenance/reports/source_license_v6_include_text.tsv`.
- Do not publicly redistribute source text for the 389 records in `provenance/reports/source_license_v6_exclude_text.tsv`; provide source identifiers, checksums, split assignments, and reconstruction metadata instead.
- Keep `provenance/reports/source_license_manual_overrides.tsv` in the deposit as manual resolution evidence.
- `data/brat_auxiliary/` and the compatibility `data/brat/` path have been reviewed for inclusion in the full archive; keep their auxiliary/compatibility status aligned with the manuscript and release docs.
- Exclude `provenance/cache/` from the public Zenodo deposit unless the API-returned cache contents are separately cleared for redistribution.
- Use corpus package version `1.0.0`.
- Use GitHub release tag `t2know-core-v1.0.0` to avoid conflict with the legacy July 2024 `v1.0.0` release.
- Use GitHub release <https://github.com/edugredu/T2KNOWcorpusRelease/releases/tag/t2know-core-v1.0.0>, commit `ea99f2a433751a0e33ec0abdfa19b3bc6cb38f41`.
- Verify release asset `T2KNOW-public-upload-v1.0.0-20260508-r20.zip` with SHA-256 `fa4facb865398ca188bdb479671a4ffe68d08a53eeb6138397004bdb13a7055a`.
- Mint one Zenodo DOI for the corpus public package. The included scripts and benchmark code are reproducibility support inside the corpus package unless a separate code archive is deliberately created later.
- Archive this staged public package directly, or attach the same generated zip to the tagged GitHub release before Zenodo DOI creation.

## Hard Blockers Before Submission

- Replace all manuscript placeholders for repository URL, release tag, DOI, and final access metadata.
- Confirm that the Zenodo package contents match the `include_text`/`exclude_text` decisions in `source_license_audit_v6.tsv`.
- Keep the rights-aware hybrid release model aligned across `README.md`, `CITATION.cff`, `LICENSE`, source metadata, and the manuscript availability statements.
- Record the final Zenodo DOI and update the manuscript and release metadata before submission.

## Recommended Zenodo Metadata

- Title: `T2KNOW: A Biomedical Nested Named Entity Recognition Resource for Huntington's Disease Literature`
- Resource type: `Dataset`
- Version: `1.0.0`
- Keywords: `biomedical NLP`, `named entity recognition`, `nested NER`, `Huntington's disease`, `language resource`
- Related identifiers: add the paper DOI after publication, or mark it as pending if unavailable.

## Files That Should Stay Excluded

- virtual environments such as `.venv/`
- Git metadata directories
- `__pycache__/` and `.pytest_cache/`
- Slurm logs
- model checkpoints and training run directories
- paper build files such as `.aux`, `.bbl`, `.log`, `.out`

## Post-Upload Actions

- Record the Zenodo DOI.
- Update manuscript data availability and code availability statements.
- Add the DOI to `CITATION.cff` if desired.
- Tag the corresponding source repository state with the same version.
