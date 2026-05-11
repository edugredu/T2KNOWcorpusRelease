# T2KNOW Data Format

Canonical new-user entry point: `data/t2know-core-v1.0/`. The official benchmark entry point is `data/t2know-core-v1.0/document_disjoint_hybrid/`; here, `hybrid` means text-included plus text-excluded/reconstructable records in the same document-disjoint split representation, not synthetic mixing.


This document defines the released data artefacts and the current record formats used by the `T2KNOW-Core v1.0` corpus.

It is release-facing and normative for the public data format.

## Release Artefacts

### Manuscript benchmark release files

The recommended benchmark release is **T2KNOW-Core v1.0**, the reviewed-only document-disjoint package:

- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json`
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`
- `data/t2know-core-v1.0/text_included/brat_core/`

Interpretation:

- `data/t2know-core-v1.0/document_disjoint_hybrid/trainData.json`, `data/t2know-core-v1.0/document_disjoint_hybrid/evalData.json`, and `data/t2know-core-v1.0/document_disjoint_hybrid/testData.json` are the recommended benchmark split files.
- `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl` is the consolidated reviewed JSONL benchmark release with normalized entity objects and metadata.
- `data/t2know-core-v1.0/text_included/brat_core/` is the public BRAT standoff inspection export for text-included records only; reconstructed full BRAT is generated locally after reconstruction.
- each reviewed source abstract belongs to exactly one split.

### Supporting compatibility files

The earlier sentence-level corpus files remain available for provenance and compatibility:

- `data/sentence_level_legacy/trainData.json`
- `data/sentence_level_legacy/evalData.json`
- `data/sentence_level_legacy/testData.json`
- `data/sentence_level_legacy/t2know.jsonl`

### Auxiliary training artefact

- `data/auxiliary/trainBalanced.json`
- `data/brat_auxiliary/trainBalanced/`

These files are auxiliary balanced training artefacts. They are not part of the core resource claim.

### Legacy mixed BRAT compatibility export

- `data/brat/`

This path retains the older mixed BRAT layout with reviewed train/eval/test folders and the auxiliary `trainBalanced` folder together. It is kept for compatibility. New users should prefer `data/t2know-core-v1.0/text_included/brat_core/` for the text-included public BRAT inspection export of T2KNOW-Core v1.0 and `data/brat_auxiliary/` for auxiliary BRAT files.

## Reviewed JSONL Format

`data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl` stores one JSON object per line.

Each record contains the following top-level fields:

- `text`: sentence text for text-included records; `null` for text-excluded records
- `entities`: list of entity objects
- `meta`: record metadata

Example:

```json
{
  "text": null,
  "entities": [
    {
      "start": 0,
      "end": 20,
      "label": "DiseaseOrSyndrome",
      "text": null,
      "spans": [[0, 20]]
    }
  ],
  "meta": {
    "doc_id": "0",
    "split": "test",
    "source_file": "0text0.txt",
    "is_synthetic": false,
    "sentence_id": "0_0",
    "sentence_index": 0,
    "document_start": 0,
    "document_end": 137,
    "text_available_in_archive": false,
    "requires_reconstruction": true,
    "text_redistribution_status": "excluded",
    "offset_basis": "reconstructed_sentence_text",
    "brat_available_in_archive": false,
    "source_text_policy": "user_reconstruction_required",
    "sentence_sha256": "...",
    "normalized_document_sha256": "..."
  }
}
```

### `entities` objects

Each entity object currently contains:

- `start`: integer start offset
- `end`: integer end offset
- `label`: one of the corpus labels
- `text`: surface form string for text-included records; `null` for text-excluded records
- `spans`: list of span pairs

Notes:

- In the current release, simple entities use `spans` with a single pair mirroring `start` and `end`.
- Same-span multi-label annotation is represented as multiple entity objects sharing the same `start` and `end` values but carrying different `label` values.

### `meta` object

The public JSONL metadata contract requires all of the following fields:

- `doc_id`: stable record identifier
- `split`: one of the released split labels
- `source_file`: provenance field pointing to the original source filename
- `is_synthetic`: boolean flag indicating whether the record is synthetic
- `sentence_id`: stable sentence identifier using the `doc_id_sentenceIndex` convention
- `sentence_index`: zero-based sentence index within the source abstract
- `document_start`: sentence start offset in the linked BRAT `.txt` file
- `document_end`: sentence end offset in the linked BRAT `.txt` file
- `brat_txt_path`: concrete BRAT `.txt` file selected for document inspection, present only when `brat_available_in_archive = true`
- `brat_ann_path`: concrete BRAT `.ann` file selected for standoff annotation inspection, present only when `brat_available_in_archive = true`

All reviewed document-disjoint JSONL records are expected to contain these fields. Legacy JSONL files may contain only the older four-field metadata contract (`doc_id`, `split`, `source_file`, `is_synthetic`).

## Offset Conventions

All JSONL entity offsets are zero-based, half-open character offsets over the exact sentence string. For text-included records this is the released `text` string. For text-excluded records, offsets are over the reconstructed sentence text verified by `sentence_sha256`.

Important rules:

- offsets are character positions in decoded UTF-8 text, not byte offsets;
- no Unicode normalization is assumed or applied by the release format;
- offsets are stable only over the released files as-is;
- do not rewrite newlines, normalize whitespace, or canonicalize Unicode before applying offsets;
- JSONL and split-file offsets are sentence-relative;
- BRAT offsets are document-relative over the linked `.txt` file;
- `document_start + entity.start` and `document_start + entity.end` reconstruct document-relative JSONL entity offsets;
- newlines in BRAT `.txt` files count as characters;
- the released sentence records define the fixed sentence segmentation used for corpus statistics and benchmarks.

## Document Context and Provenance

The JSONL files are sentence-level convenience views. They preserve provenance through `meta.doc_id`, `meta.source_file`, `meta.brat_txt_path`, and `meta.brat_ann_path`. Their entity offsets are sentence-relative, while `meta.document_start` and `meta.document_end` store the corresponding sentence boundary in the linked BRAT document.

Full-document inspection of T2KNOW-Core should use the concrete BRAT paths stored in each JSONL record. The matching `.txt` file contains the source abstract text and the matching `.ann` file contains standoff annotations with document-relative offsets. Benchmark split membership is defined by `meta.split` and the split JSON files, not by the BRAT folder path. This avoids ambiguity when the reviewed BRAT export retains compatibility folders from earlier corpus layouts.

Document context was used during manual review when needed for abbreviation resolution and context-sensitive label decisions. The current release does not store a decision-level flag identifying which annotations required document context.

## Split JSON Format

The split files `trainData.json`, `evalData.json`, `testData.json`, and `trainBalanced.json` use line-oriented JSON records despite the `.json` extension.

Each record contains:

- `id`: record identifier
- `text`: text content
- `tags`: list of entity tags
- `meta`: document, split, source-file, sentence-index, and document-offset metadata
- `sentences`: present in some files, used for sentence boundary information

Observed structure:

- `trainData.json`: `id`, `text`, `tags`, `meta`
- `evalData.json`: `id`, `text`, `tags`, `meta`
- `testData.json`: `id`, `text`, `tags`, `meta`
- `trainBalanced.json`: `id`, `text`, `tags`, `sentences`

`evalData.json` is the validation split used for model selection and decoder calibration.

Example:

```json
{
  "id": "1_0",
  "text": null,
  "tags": [
    {
      "start": 0,
      "end": 6,
      "tag": "SignOrSymptom"
    }
  ],
  "meta": {
    "doc_id": "1",
    "split": "train",
    "source_file": "0text1.txt",
    "sentence_index": 0,
    "document_start": 94,
    "document_end": 181,
    "text_available_in_archive": false,
    "requires_reconstruction": true,
    "text_redistribution_status": "excluded",
    "offset_basis": "reconstructed_sentence_text",
    "brat_available_in_archive": false,
    "source_text_policy": "user_reconstruction_required"
  }
}
```

### `tags` objects

Each tag currently contains:

- `start`: integer start offset
- `end`: integer end offset
- `tag`: label name

Notes:

- The split JSON files do not store entity surface text directly.
- The current validator therefore cannot perform deep text-surface consistency checks for this format.
- Split JSON tag offsets follow the same sentence-relative character-offset convention as JSONL entity offsets.

## Structural Validation Status

The current release artefacts have been validated with `scripts/validate_corpus.py`.

### JSONL validation

Command:

```bash
python3 scripts/validate_corpus.py data/sentence_level_legacy/t2know.jsonl --format jsonl
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl --format jsonl --mode public-redacted
```

Observed result for `data/sentence_level_legacy/t2know.jsonl`:

- total sentences: `15625`
- total entities: `135065`
- synthetic sentences: `1269`
- splits: `train=11758`, `val=1311`, `test=2556`
- errors: `0`

Observed result for `data/t2know-core-v1.0/document_disjoint_hybrid/t2know_document_disjoint_hybrid.jsonl`:

- total sentences: `14356`
- total entities: `125703`
- synthetic sentences: `0`
- splits: `train=10052`, `val=1435`, `test=2869`
- errors: `0`

Current validator coverage for reviewed JSONL:

- required top-level fields: `text`, `entities`, `meta`
- required metadata fields:
  - `meta.doc_id`
  - `meta.split`
  - `meta.source_file`
  - `meta.is_synthetic`
- optional enriched metadata checks when present:
  - `meta.sentence_id`
  - `meta.sentence_index`
  - `meta.document_start`
  - `meta.document_end`
- allowed split values: `train`, `val`, `test`
- required entity fields:
  - `start`
  - `end`
  - `label`
  - `text`
  - `spans`
- label membership in the frozen 40-label inventory
- offset and reconstructed-text consistency checks
- document-relative sentence-boundary consistency checks for enriched document-disjoint JSONL metadata

### Split JSON validation

Command:

```bash
python3 scripts/validate_corpus.py data/sentence_level_legacy --format json
python3 scripts/validate_corpus.py data/auxiliary --format json
python3 scripts/validate_corpus.py data/t2know-core-v1.0/document_disjoint_hybrid --format json --mode public-redacted
python3 scripts/validate_corpus.py data/t2know-core-v1.0/text_included/brat_core --format brat --mode public-redacted --scope text-included
python3 scripts/validate_corpus.py data/brat_auxiliary --format brat
```

Observed result for `data/sentence_level_legacy`:

- total sentences: `7967`
- total entities: `70069`
- split counts:
  - `trainData=5578`
  - `evalData=795`
  - `testData=1594`
- errors: `0`

Observed result for `data/auxiliary`:

- total sentences: `7154`
- total entities: `39271`
- split counts:
  - `trainBalanced=7154`
- errors: `0`

Observed result for `data/t2know-core-v1.0/document_disjoint_hybrid`:

- total sentences: `14356`
- total entities: `125703`
- split counts:
  - `trainData=10052`
  - `evalData=1435`
  - `testData=2869`
- errors: `0`

Observed result for `data/t2know-core-v1.0/text_included/brat_core`:

- total documents: `432`
- errors: `0`

Observed result for `data/brat_auxiliary`:

- total documents: `1029`
- total entities: `50704`
- split counts:
  - `trainBalanced=1029`
- errors: `0`

Validator note:

- The JSON split validator reports that deep entity-text mismatch checking is not possible for the split JSON format because entity surface text is not stored there.
- The split JSON validator is therefore a structural validator, not a full contract validator for the reviewed JSONL release.

## Metadata Contract

For the reviewed JSONL release, the following metadata fields are required:

- `meta.doc_id`
- `meta.split`
- `meta.source_file`
- `meta.is_synthetic`

This requirement is part of the public release format and should be preserved in future future public releases.

## Interpretation for the Paper

- The paper should treat `data/t2know-core-v1.0/document_disjoint_hybrid/` as the T2KNOW-Core v1.0 recommended benchmark representation used for headline corpus statistics and benchmark results.
- The paper should treat `data/t2know-core-v1.0/text_included/brat_core/` as the text-included public BRAT inspection export, not as an independently complete benchmark split.
- The older sentence-level split files under `data/sentence_level_legacy/` should be described as supporting compatibility/provenance artefacts unless the manuscript benchmark policy changes.
- The paper should treat `data/auxiliary/trainBalanced.json` as an auxiliary training artefact.
- The paper should treat `data/brat_auxiliary/` and the mixed `data/brat/` compatibility export as auxiliary or compatibility material.
- Structural validity is currently supported by deterministic corpus validation with zero reported errors on the checked release files.


## Sentence segmentation status

Sentence-level records are fixed release units. The current archive does not preserve the original sentence-segmentation tool or a decision-level log of manual sentence-boundary correction. The released sentence strings and their linked BRAT document offsets are therefore the authority for segmentation. Validation aligns each sentence record back to the released BRAT text; no cross-sentence entity spans are included in T2KNOW-Core.
