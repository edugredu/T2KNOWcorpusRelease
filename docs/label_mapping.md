# T2KNOW Label Mapping

This document records the provenance and verification status of the semantic-type to label mapping used by the reviewed `T2KNOW` release.

## Purpose

The reviewed core resource uses a frozen 40-label inventory documented in:

- `T2KNOWcode/listaCategorias.txt`
- `docs/annotation_guidelines.md`

The label inventory is not arbitrary. It is derived from an explicit mapping layer from source semantic types into the final `T2KNOW` labels.

## Candidate-Generation Provenance

The original corpus construction used spaCy/scispaCy biomedical pre-annotation with a UMLS-configured entity linker. The linker produced candidate spans and Concept Unique Identifiers (CUIs), and a project conversion step mapped CUIs to UMLS Semantic Types before exporting candidate annotations to BRAT standoff format.

The exact spaCy package version, scispaCy model name, linker configuration, and UMLS release used for that initial pre-annotation run are not preserved in this release. The automatic layer should therefore be interpreted as construction provenance and candidate-generation support only. The reviewed core resource is defined by the manually checked annotations, the frozen 40-label inventory, the source-to-target semantic-type mapping below, and the released validation checks.

## Primary Mapping Artifacts

The main mapping evidence currently present in the repository is:

- `Anotaciones base/Tarea EDU/Mapping UMLS-T2KNOW.xlsx`
- `old/UMLS CATEGORIAS_v2.csv`

Interpretation:

- `Mapping UMLS-T2KNOW.xlsx` is the primary semantic-type to target-label mapping table.
- `UMLS CATEGORIAS_v2.csv` is the semantic-type reference table used as supporting provenance.

## Verified Mapping Properties

The spreadsheet mapping was checked against the frozen 40-label inventory.

Observed verification results:

- mapping rows: `128`
- unique targets: `41`
- target labels consist of:
  - the frozen 40-label inventory, and
  - the sentinel value `0.0` for dropped or unmapped source categories
- drop rows (`0.0`): `44`
- invalid target labels relative to the frozen inventory: `0`
- frozen labels unused by the mapping: `0`

This means:

- every kept mapping target lands in the frozen 40-label schema,
- no extra target labels are introduced by the mapping table,
- all frozen labels are represented in the mapping table.

## Reproducible Verification

The repository now includes a small verification script:

```bash
python3 scripts/verify_label_mapping.py
```

The script checks:

- that all non-drop targets in `Mapping UMLS-T2KNOW.xlsx` belong to the frozen 40-label inventory,
- that all frozen labels are used by the mapping,
- and that the mapping artefacts can be read reproducibly from the repository.

## Interpretation for the Paper

- The paper can describe the final 40-label schema as the result of an explicit semantic-type normalization step.
- The mapping verification supports schema cleanliness and reproducibility.
- This does not replace annotation validation. It only supports that the released label inventory and its normalization layer are internally consistent.
