# T2KNOW Annotation Guidelines

## Purpose and scope

These guidelines define the annotation policy for the `T2KNOW` resource.

`T2KNOW` is an HD-focused biomedical literature corpus for nested and same-span multi-label named entity recognition. The resource was created within the T2KNOW project, but the guidelines below describe the corpus annotation policy itself, not the behavior of any checker or validator.

The original annotation workflow started from spaCy/scispaCy pre-annotations linked to UMLS concepts and semantic types. Those pre-annotations were candidate suggestions for human review, not final labels. The reviewed core resource follows the manually checked annotations after correction, deletion, addition, boundary adjustment, and normalization to the final 40-label inventory.

These guidelines are the release reference for:
- label semantics,
- span boundaries,
- nested entities,
- same-span multi-label entities,
- abbreviation handling,
- exclusion rules,
- and corpus release consistency.

## Corpus focus and annotation unit

- Domain focus: Huntington's disease literature with related biomedical concepts.
- Annotation context: decisions should be made using the full sentence and, when needed, the surrounding document context.
- Annotation workflow assumption: the resource may be reviewed sentence by sentence in release files, but annotation decisions are made with document context whenever needed for disambiguation.
- Release representation:
  - the resource is released in structured JSON/JSONL,
  - reviewed JSONL records use top-level keys `text`, `entities`, and `meta`,
  - reviewed-release `meta` fields include `doc_id`, `split`, `source_file`, and `is_synthetic`,
  - entities are represented with character offsets over `text`,
  - reviewed-release entity records use at least `start`, `end`, and `label`,
  - the current release also stores `text` and `spans` inside each entity record,
  - same-span multi-label annotation is represented as repeated entity objects with the same `start` and `end` but different `label` values,
  - overlapping spans are allowed only when they encode distinct concepts.

## Final label inventory

The final resource uses exactly these 40 labels:

- `AminoAcidPeptideOrProtein`
- `AnatomicalAbnormality`
- `Bacterium`
- `BiologicFunction`
- `BiologicallyActiveSubstance`
- `BiomedicalOccupationOrDiscipline`
- `BodyPartOrganOrOrganComponent`
- `Cell`
- `CellComponent`
- `CellFunction`
- `CellOrMolecularDysfunction`
- `Chemical`
- `ClinicalAttribute`
- `DiseaseOrSyndrome`
- `EmbryonicStructure`
- `EnvironmentalEffectOfHumans`
- `Eukaryote`
- `ExperimentalModelOfDisease`
- `Finding`
- `GeneOrGenome`
- `HealthCareActivity`
- `HealthCareRelatedOrganization`
- `IndividualBehavior`
- `InjuryOrPoisoning`
- `MachineActivity`
- `ManufacturedObject`
- `MolecularSequence`
- `NaturalPhenomenonOrProcess`
- `NucleicAcidNucleosideOrNucleotide`
- `Organism`
- `OrganismAttribute`
- `PathologicFunction`
- `PatientOrDisabledGroup`
- `PharmacologicSubstance`
- `PopulationGroup`
- `ResearchActivity`
- `SignOrSymptom`
- `Substance`
- `TemporalConcept`
- `Virus`

Deprecated or legacy labels must not appear in the final reviewed core resource.

## Global annotation decision order

Apply this decision order for each candidate mention:

1. Is the text span a complete semantic concept?
   - If no, do not annotate it.
2. Does it denote a domain-relevant biomedical concept?
   - If no, do not annotate it.
3. Is the candidate a generic stand-in or incomplete fragment?
   - If yes, do not annotate it.
4. Determine the most specific valid label.
   - Prefer the most specific semantically correct label over broader labels.
5. Check whether the final span should be:
   - a single entity,
   - multiple separate entities,
   - nested entities,
   - or a same-span multi-label entity.
6. Verify boundary precision.
   - Keep the minimal semantically complete span.

## Core principles

### Semantic completeness

Annotate complete concepts, not fragments.

Annotate:
- `age of onset`
- `inherited neurodegenerative disorder`
- `western blot`
- `severe reduction in muscle control`

Do not annotate:
- `age` alone when it is only part of `age of onset`
- `neurodegenerative` alone when the intended concept is a disorder
- `reduction` alone when the full concept is a larger clinical phrase

### Domain specificity

Annotate domain-specific biomedical concepts.

Annotate:
- `Huntington's disease`
- `CAG repeats`
- `striatum`

Do not annotate:
- `results`
- `data`
- `parameters`
- `important`
- `significant`

### Specificity over generality

Use the most specific valid label.

Examples:
- `tremor` -> `SignOrSymptom`, not `Finding`
- `Huntington's disease` -> `DiseaseOrSyndrome`, not a broader functional label

### Context sensitivity

Use context when label choice depends on function or discourse role.

Example:
- `genetic testing` in clinical care -> `HealthCareActivity`
- `genetic testing` in experimental methods -> `ResearchActivity`

## Single entities, separate entities, and nested entities

### Single entity

Use one span when the phrase denotes one unified concept.

Examples:
- `Huntington's disease` -> one `DiseaseOrSyndrome`
- `huntingtin gene` -> one `GeneOrGenome`
- `HD patients` -> one `PatientOrDisabledGroup`
- `western blot` -> one `ResearchActivity`
- `age of onset` -> one `TemporalConcept`

### Separate entities

Use separate non-overlapping spans when the phrase refers to multiple distinct concepts.

Examples:
- `Huntington's disease patients`
  - `Huntington's disease` -> `DiseaseOrSyndrome`
  - `patients` -> `PatientOrDisabledGroup`
- `juvenile HD`
  - `juvenile` -> `PopulationGroup`
  - `HD` -> `DiseaseOrSyndrome`

### Nested entities

Nested or overlapping spans are allowed only when the overlapping spans encode distinct concepts.

Keep nested spans when:
- the meanings are genuinely different,
- both spans are semantically complete,
- and the overlap is not redundant.

Do not keep overlapping spans when one is just a redundant fragment of the other.

Redundant overlap example:
- `Huntington's disease` -> annotate the full disease mention
- do not separately annotate `disease` with the same meaning

## Multi-label policy

Same-span multi-label annotation is allowed, but only when both labels add non-redundant semantic information.

Use multiple labels for the same span only when:
- the exact same span truly carries multiple semantic roles,
- both labels are justified by context,
- and removing one label would lose information.
- the reviewed context supports independently useful label readings under the released guideline.

Same-span multi-label annotation is not used merely because a UMLS concept can belong to multiple semantic types. In particular, not all gene/protein/substance ontology relations are multi-labeled: same-span multi-labeling requires non-redundant, context-supported roles, and the local context must support each role independently.

Examples:
- `pathological disorders` -> `PathologicFunction` + `DiseaseOrSyndrome`
- `genetic testing` -> `HealthCareActivity` + `ResearchActivity` when the context supports both

Do not use multiple labels when:
- one label is only a broader version of the other,
- context clearly supports one primary label,
- or the second label adds no real information.

In the reviewed public release, same-span multi-label entities are stored as separate entity records sharing the same offsets.

Examples seen in the reviewed core resource include:
- `translation initiation factor` -> `AminoAcidPeptideOrProtein` + `GeneOrGenome`
- `4E-BP` -> `AminoAcidPeptideOrProtein` + `GeneOrGenome`
- `genetic modifiers` -> `GeneOrGenome` + `CellFunction`

Decision guide:

| Family | Admissible condition | Non-admissible condition | Carryover risk |
|---|---|---|---|
| `AminoAcidPeptideOrProtein` + `BiologicallyActiveSubstance` | protein role and active-substance role are both context-relevant | broad activity is not locally meaningful | medium |
| `AminoAcidPeptideOrProtein` + `GeneOrGenome` | span is used in a gene/protein ambiguous way | context clearly denotes only gene or only protein | high |
| `BiologicallyActiveSubstance` + `GeneOrGenome` | regulatory or biomarker role is explicit and gene reading remains supported | gene label is inherited only from ontology | high |
| `HealthCareActivity` + `ResearchActivity` | procedure is both clinical and study method in context | purely clinical care or purely experiment method | medium |
| `Chemical` + `PharmacologicSubstance` | chemical identity and drug role are both relevant | substance is only a reagent or only a drug mention | medium |
| `BiologicallyActiveSubstance` + `NucleicAcidNucleosideOrNucleotide` | nucleotide is discussed as active molecule | ontology-derived broad activity only | high |

When context is insufficient, prefer the narrower context-supported label and avoid adding a second label solely from source-ontology layering.

## Confusable label guidance

### Finding vs ClinicalAttribute vs SignOrSymptom

Positive examples:
- `reduced motor score` -> `ClinicalAttribute` when it is a measured attribute.
- `tremor` -> `SignOrSymptom` when it is a clinical manifestation.
- `abnormal finding` -> `Finding` when the text reports an observed result.

Negative examples:
- Do not label `score` alone without the measured attribute.
- Do not label generic `effect` as `Finding` without local biomedical content.
- Do not label a laboratory method as `SignOrSymptom`.

### HealthCareActivity vs ResearchActivity

Positive examples:
- `clinical genetic testing` -> `HealthCareActivity` in patient-care context.
- `western blot assay` -> `ResearchActivity` in experimental-method context.
- `screening in the cohort study` -> `ResearchActivity` when it denotes study procedure.

Negative examples:
- Do not label generic `study` without a concrete research activity.
- Do not label routine treatment as `ResearchActivity`.
- Do not label a research assay as `HealthCareActivity` unless clinical care is explicit.

### Eukaryote vs Organism vs ExperimentalModelOfDisease

Positive examples:
- `mouse model of disease` -> `ExperimentalModelOfDisease`.
- `yeast cells` -> `Eukaryote` when the organism type is the referent.
- `organisms` -> `Organism` only when a broad organism mention is explicit.

Negative examples:
- Do not label a disease model as only `Organism` when the modelling role is explicit.
- Do not label human patient groups as `Eukaryote`.
- Do not label a cell line as `Organism` unless the organism is mentioned.

### BiologicallyActiveSubstance vs PharmacologicSubstance

Positive examples:
- `dopamine` -> `BiologicallyActiveSubstance` when discussed as endogenous biology.
- `administered dopamine agonist` -> `PharmacologicSubstance` when used as treatment.
- `therapeutic compound` -> `PharmacologicSubstance` when drug role is explicit.

Negative examples:
- Do not label every biochemical molecule as `PharmacologicSubstance`.
- Do not label a drug vehicle as `BiologicallyActiveSubstance` without biological activity.
- Do not add both labels when only one role is expressed.

### GeneOrGenome vs AminoAcidPeptideOrProtein

Positive examples:
- `HTT gene` -> `GeneOrGenome`.
- `huntingtin protein` -> `AminoAcidPeptideOrProtein`.
- ambiguous gene/protein symbols may carry both labels only when local context supports both readings.

Negative examples:
- Do not label a protein complex as `GeneOrGenome` solely because its name derives from a gene.
- Do not label DNA sequence mentions as protein.
- Do not preserve both labels when the sentence clearly resolves the mention.

## Boundary rules

### General rule

Annotate the minimal semantically complete span.

### Articles

Exclude definite and indefinite articles unless they are part of a fixed proper name.

Examples:
- `the brain` -> annotate `brain`
- `a tremor` -> annotate `tremor`

### Possessives

Include possessives when they are part of a fixed technical term.

Examples:
- `Huntington's disease` -> include the possessive
- `Parkinson's disease` -> include the possessive

Exclude possessives when they mark ownership rather than term identity.

Examples:
- `patient's symptoms` -> annotate `symptoms`
- `gene's expression` -> annotate `expression`

### Prepositions

Include prepositions when they are required for a complete technical concept.

Examples:
- `age of onset`
- `loss of function`
- `reduction in muscle control`

Exclude prepositions when they simply connect separate concepts.

Examples:
- `cells in the brain` -> annotate `cells` and `brain` separately
- `proteins in neurons` -> annotate `proteins` and `neurons` separately

### Coordination

Annotate coordinated concepts separately and exclude the conjunction.

Examples:
- `genes and proteins`
  - `genes` -> `GeneOrGenome`
  - `proteins` -> `AminoAcidPeptideOrProtein`
- `Huntington and Parkinson patients`
  - `Huntington` -> `DiseaseOrSyndrome`
  - `Parkinson` -> `DiseaseOrSyndrome`
  - `patients` -> `PatientOrDisabledGroup`

## Abbreviations and acronyms

Annotate abbreviations according to what they denote in context.

Examples:
- `HD` -> `DiseaseOrSyndrome`
- `CNS` -> `BodyPartOrganOrOrganComponent`
- `HTT` -> `GeneOrGenome`
- `mhtt` -> usually `GeneOrGenome`, unless context clearly indicates a different semantic role

### Parenthetical definitions

Annotate the full form and the abbreviation separately, excluding parentheses.

Example:
- `Huntington's disease (HD)`
  - `Huntington's disease` -> `DiseaseOrSyndrome`
  - `HD` -> `DiseaseOrSyndrome`

### Ambiguous abbreviations

If an abbreviation is ambiguous, use context.

Example:
- `MS` may mean `Multiple Sclerosis` or `Mass Spectrometry`

If the surrounding context is insufficient, do not annotate.

## What is not annotated

Do not annotate:
- generic stand-ins such as `results`, `data`, `parameters`, `factors`, `findings` alone,
- incomplete fragments,
- adjectives without standalone biomedical referents,
- person names when they are author or discoverer names rather than disease mentions,
- redundant subspans of a larger same-meaning entity,
- unresolved ambiguous abbreviations,
- vague mentions that cannot be interpreted as a stable biomedical concept.

Key rule:
- If the span would be meaningless or underspecified without surrounding context, do not annotate it.

## High-value label guidance

### Disease and pathology

Use `DiseaseOrSyndrome` for named diseases and clinically recognized disease states.

Examples:
- `Huntington's disease`
- `Huntington's chorea`
- `neurodegenerative disorders`
- `cognitive disturbance`
- `neuropsychiatric disturbance`

Use `CellOrMolecularDysfunction` for molecular or cellular dysfunction states.

Examples:
- `mutant huntingtin` when describing dysfunction
- `mitochondrial dysfunction`

Use `PathologicFunction` for disease processes and mechanisms.

Examples:
- `pathogenesis`
- `disease progression`
- `molecular pathogenesis`

Use `SignOrSymptom` for observable manifestations.

Examples:
- `tremor`
- `muscle stiffness`

Special case:
- `Huntington` alone usually refers to the disease in medical context,
- but person names such as `George Huntington` are not annotated.

### Genes, proteins, and related molecular entities

Use `GeneOrGenome` when the mention clearly refers to a gene, locus, or gene symbol.

Examples:
- `huntingtin gene`
- `HTT locus`
- `HTT`
- `mhtt` in gene-symbol context

Use `AminoAcidPeptideOrProtein` when the mention clearly refers to a protein.

Examples:
- `huntingtin protein`
- `4E-BP`

Use `BiologicallyActiveSubstance` when the focus is biological activity, targetability, or functional role rather than explicit gene/protein identity.

Examples:
- `huntingtin` in therapeutic target context
- `HTT` in aggregation or toxicity context

Use `MolecularSequence` for sequence-level mentions.

Examples:
- `CAG repeats`
- `polyglutamine tract`
- `trinucleotide repeat`

### Clinical versus research activities

Use `HealthCareActivity` in clinical, diagnostic, therapeutic, or patient-care contexts.

Examples:
- `diagnosis`
- `screening`
- `clinical assessment`
- `genetic testing` in patient-care context
- `MRI scan` used for diagnosis

Use `ResearchActivity` in experimental, methodological, or investigational contexts.

Examples:
- `western blot`
- `immunohistochemistry`
- `PCR`
- `cell culture`
- `genetic testing` in experimental context

Legacy procedure labels from pre-annotation or upstream schemas must not appear in the final reviewed core resource.

Use:
- `HealthCareActivity` instead of deprecated clinical procedure labels
- `ResearchActivity` instead of deprecated laboratory or research-procedure labels when the context is experimental

### Findings and clinical attributes

Use `Finding` only for semantically complete observed outcomes or reportable observations.

Keep:
- `clinical findings`
- `pathological findings`
- `research findings` when the phrase is semantically complete

Do not keep:
- `findings` alone
- `results`
- `data`

Use `ClinicalAttribute` for measurable or clinically interpretive indicators.

Examples:
- `huntingtin levels` as a biomarker
- `CAG repeat length` when used as a predictor

When a biologically active substance is discussed primarily as a biomarker, indicator, predictor, or clinical parameter, prefer `ClinicalAttribute` over `BiologicallyActiveSubstance`.

### Anatomy, cells, and cellular components

Use `BodyPartOrganOrOrganComponent` for organs, tissues, and anatomical structures.

Examples:
- `brain`
- `CNS`
- `striatum`
- `basal ganglia`

Use `Cell` for cell-level mentions.

Examples:
- `neurons`
- `brain cells`

Use `CellComponent` for subcellular structures.

Examples:
- `mitochondria`
- `nucleus`
- `cell membrane`

### Temporal concepts

Annotate complete temporal concepts, not generic temporal words.

Keep:
- `age of onset`
- `last decade`
- `early stage`
- `disease duration`

Do not annotate:
- `age` alone
- `time` alone
- `early` alone

Context tie-break:
- `disease progression` -> `TemporalConcept` when timing or staging is central
- `disease progression` -> `PathologicFunction` when mechanism or process is central

### Chemicals and therapeutic substances

Use `PharmacologicSubstance` for drugs and therapeutic agents.

Examples:
- `therapeutic compounds`
- `drug candidates`
- `neuroprotective agents`

Use `Chemical` for generic chemical references.

Use `BiologicallyActiveSubstance` when biological activity is central.

## Legacy label normalization

The reviewed core resource uses only the final 40-label inventory.

If an upstream or pre-annotation schema uses legacy labels, normalize them into the final inventory before release.

High-priority normalization decisions include:
- clinical diagnostic and therapeutic procedures -> `HealthCareActivity`
- laboratory and experimental procedures -> `ResearchActivity`
- generic biomarker-like substance mentions in indicator context -> `ClinicalAttribute`
- generic stand-ins such as `results`, `data`, `parameters`, or `findings` alone -> do not annotate

These normalization rules are part of the corpus annotation policy because the released dataset reflects corrected annotations in the final schema rather than raw upstream labels.

## Compact exclusion checklist

Before keeping an entity, check:

- Is it a complete semantic concept?
- Is it domain-specific?
- Is it non-generic?
- Is the span minimal and precise?
- Is any overlap non-redundant?
- Is multi-label truly necessary?

If the answer to any of the first three is no, do not annotate it.

## Quality assurance note

These guidelines define the intended annotation policy for the reviewed core resource.

They should be interpreted together with:
- the reviewed core resource policy in [dataset_policy.md](dataset_policy.md),
- the reviewed core resource files,
- and the evaluation definitions used for the paper.

The existence of these guidelines does not imply exhaustive human adjudication of the full corpus. They define the target annotation policy and release semantics for an HD-focused biomedical resource created within the T2KNOW project.
