# T2KNOW-Core Reconstruction

This is the authoritative reconstruction workflow for text-excluded T2KNOW-Core records.

The official benchmark contains 821 reviewed source documents. The public archive is immediately usable for the text-included subset. For the 389 text-excluded records, the public archive releases annotations, offsets, split assignments, source identifiers, provenance, and checksums, but not third-party source text. Users may reconstruct those reviewed abstract records locally only when they can lawfully access the source publications and can pass checksum validation.

Records that cannot be lawfully accessed or checksum-validated remain usable as annotation/provenance metadata, but they cannot be used for local full-text training or full offset validation over all 821 reviewed documents.

Source-licence tables are metadata and licence-evidence audits, not legal advice. Users are responsible for ensuring that reconstruction and use of third-party source text complies with their access rights and publisher terms.

## Public-Archive Fields

For text-excluded records, the public JSON/JSONL records contain:

- `text = null`.
- `entities[].text = null` or entity surface text omitted.
- sentence-relative offsets, labels, spans, split assignments, and document identifiers.
- `text_sha256` and `meta.sentence_sha256`: SHA-256 checksum of the reviewed sentence string.
- `text_length` and `meta.sentence_char_length`: reviewed sentence length in characters.
- `meta.normalized_document_sha256`: SHA-256 checksum of the reviewed document/abstract string.
- `meta.normalization_policy = reviewed_release_text_utf8`.
- `meta.newline_policy = preserve_reviewed_brat_newlines`.
- `meta.source_text_policy = user_reconstruction_required`.

The source reconstruction table is `provenance/reports/reconstruction_sources.tsv`. Its reconstruction-facing fields are:

- `doi`
- `doi_url`
- `pmid`
- `pubmed_url`
- `pmcid`
- `pmc_url`
- `europe_pmc_url`
- `source_url`
- `source_title`
- `normalized_document_sha256`

The sentence checksum table is `provenance/reports/reconstruction_sentence_manifest.tsv`.

## Source Lookup Order

For each text-excluded `doc_id`, use `provenance/reports/reconstruction_sources.tsv` and try sources in this order:

1. DOI landing page or DOI-linked abstract/full abstract page, using `doi` and `doi_url`.
2. PubMed, using `pmid` and `pubmed_url`.
3. PMC or Europe PMC, using `pmcid`, `pmc_url`, and `europe_pmc_url`.
4. Publisher or other recorded source page, using `source_url`.

Use these sources to reconstruct only the reviewed abstract/document text represented by the record checksums. Do not reconstruct the full article body. Do not use generated, paraphrased, translated, summarised, or otherwise rewritten text. Preserve the reviewed sentence order implied by `document_start` and `document_end` in `reconstruction_sentence_manifest.tsv`.

If multiple lawful source pages differ, keep the version that exactly matches `normalized_document_sha256` after applying the policy below. If no lawful source produces the checksum, the record remains annotation/provenance-only for that user.

## Normalization Policy

The released checksums define the accepted normalization.

- Unicode: the user-supplied file must be UTF-8 text matching the reviewed release text. The reconstruction script does not apply Unicode normalization such as NFC, NFD, NFKC, or NFKD. Do not replace Greek letters, accents, punctuation, mathematical symbols, or biomedical notation with approximations unless the final checksum matches.
- Line endings: `preserve_reviewed_brat_newlines` means line breaks must match the reviewed BRAT text basis. Do not wrap, unwrap, or reorder lines. The script reads the input with newline preservation.
- Whitespace: do not collapse internal whitespace. Do not normalise tabs/spaces. Do not remove or add leading/trailing whitespace. Sentence offsets and checksums are the authority.
- Checksum algorithm: SHA-256 over the exact UTF-8 bytes of the reconstructed reviewed document string, equivalent to:

```python
hashlib.sha256(text.encode("utf-8")).hexdigest()
```

Sentence checksums use the same algorithm over each sentence slice defined by `document_start` and `document_end`.

## Source Text Input

Prepare one local UTF-8 text file per reconstructed text-excluded document. Preferred filenames for `--source-text-root` are:

- `<doc_id>.txt`
- `<doc_id>.abstract.txt`
- `<doc_id>.text`

Alternatively, prepare a source map TSV with these columns:

```text
doc_id
source_text_path
raw_source_sha256
normalization_policy
newline_policy
source_text_unit
```

Rules:

- `source_text_path` is a local path to the reconstructed reviewed abstract/document text.
- `raw_source_sha256` may be blank. If present, it must match the raw file bytes.
- `normalization_policy` must be `reviewed_release_text_utf8`.
- `newline_policy` must be `preserve_reviewed_brat_newlines`.
- `source_text_unit` must be `abstract` or `sentence_bundle`; `abstract` is preferred.

## Commands

Run from the public release root:

```bash
python3 scripts/build_reconstructed_core.py \
  --manifest provenance/reports/reconstruction_manifest.tsv \
  --sentence-manifest provenance/reports/reconstruction_sentence_manifest.tsv \
  --source-text-root /path/to/local/reconstructed_abstracts \
  --out work/reconstructed/t2know-core-v1.0
```

or:

```bash
python3 scripts/build_reconstructed_core.py \
  --manifest provenance/reports/reconstruction_manifest.tsv \
  --sentence-manifest provenance/reports/reconstruction_sentence_manifest.tsv \
  --source-map user_supplied_source_text_map.tsv \
  --out work/reconstructed/t2know-core-v1.0
```

Then validate:

```bash
python3 scripts/validate_reconstructed_core.py \
  work/reconstructed/t2know-core-v1.0
```

Use `--validate-brat` only if you also generated or supplied reconstructed BRAT files locally.

The `work/reconstructed/` directory is a local working directory and is not part of the public archive.

## Failure Handling

The builder writes `metadata/reconstruction_report.json` in the output directory. A successful full reconstruction has zero failures. Common failure statuses are:

- `missing_source_text`: no local reconstructed source text was supplied for that `doc_id`.
- `source_text_path_not_found`: the path in the source map does not exist.
- `raw_source_sha256_mismatch`: the optional raw-file checksum does not match.
- `normalized_document_sha256_mismatch`: the supplied reconstructed document does not match the reviewed document checksum.
- `sentence_sha256_mismatch`: a sentence slice does not match the released sentence checksum.
- `normalization_policy_mismatch` or `newline_policy_mismatch`: the source map does not declare the released reconstruction policy.

If a text-excluded record fails access or checksum validation, do not substitute another version and do not train on generated or paraphrased text. Treat that record as annotation/provenance metadata only. Full benchmark training over all 821 reviewed documents requires successful local reconstruction of every text-excluded record used for training, validation, or testing.
