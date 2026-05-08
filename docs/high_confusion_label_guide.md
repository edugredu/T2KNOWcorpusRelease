# T2KNOW High-Confusion Label Guide

This guide provides operational decision rules for label pairs and generic terms that showed the weakest annotator agreement in the duplicate-review diagnostic study. It is designed for users who want to apply the T2KNOW label schema to their own biomedical text or train new annotators.

All examples are drawn from text-included T2KNOW-Core records (source text cleared for redistribution). Each example cites its `doc_id`.

## 1. Finding vs ClinicalAttribute

**Definitions (from annotation guidelines):**

- `Finding`: an observed biomedical phenomenon, result, or evidence statement, typically tied to a specific measurement or assay.
- `ClinicalAttribute`: a measurable characteristic, biomarker, or clinical variable used to describe or stratify patients or disease states.

**Decision rule:** If the span names a *specific assay result, observed effect, or evidence statement* ("significant differences," "neuroprotective effects," "reduction of X"), label it `Finding`. If the span names a *measurable trait, biomarker, or clinical variable used for patient characterisation* ("biomarker," "stage," "level of X"), label it `ClinicalAttribute`.

**Positive examples (text-included records):**

> doc_1543: "We found significant differences in JPE(inv) between subjects with subjective cognitive decline and MCI, primarily in the theta band."
>
> `Finding`: "significant differences" (specific observed result)

> doc_1543: "Increasing evidence suggests that measures of signal variability and complexity could present promising biomarkers for Alzheimer's disease (AD)."
>
> `Finding`: "evidence," "signal variability" (evidence statements and measured phenomena)
> `ClinicalAttribute`: "promising biomarkers" (a measurable trait used for disease characterisation)

> doc_1543: "We aimed to detect neuronal dysfunction at a predementia (mild cognitive impairment, MCI) stage of Alzheimer's disease, by applying a network-level neural variability measure to magnetoencephalography data: the inverted joint permutation entropy (JPE(inv))."
>
> `Finding`: "detect" (observation act), "mild" (qualitative observation), "variability" (measured phenomenon)
> `ClinicalAttribute`: "stage" (clinical stratifier), "inverted joint permutation entropy," "JPE(inv)" (named biomarkers)

**Negative examples (text-included records):**

> doc_1543: "The JPE(inv) showed a reduction of nonlinear connectivity in MCI subjects in the theta and alpha band."
>
> `ClinicalAttribute`: "JPE(inv)" — a named biomarker, not a finding.
> `Finding`: "reduction" — the observed result, not the biomarker itself.

Generic nouns such as "evidence," "effects," and "results" are typically labelled `Finding` when they refer to specific observed phenomena, but are left unlabelled when used as discourse markers without a concrete observable referent.

---

## 2. HealthCareActivity vs ResearchActivity

**Definitions:**

- `HealthCareActivity`: a clinical intervention, therapy, diagnostic procedure, or patient-care action.
- `ResearchActivity`: an experimental method, study design, laboratory technique, or research-level investigation.

**Decision rule:** If the span describes an *action performed on a patient for therapeutic or diagnostic purposes* ("cell therapy," "treatment," "diagnosis," "intramedullary injection"), label it `HealthCareActivity`. If the span describes an *experimental technique, research design, or laboratory method* ("clinical translation," "study," "hippocampal administration," "event-based model"), label it `ResearchActivity`.

**Positive examples:**

> doc_10: "Here we set out the challenges associated with the clinical translation of cell therapy, using Huntington's disease as a specific example, and suggest potential strategies to address these challenges."
>
> `HealthCareActivity`: "cell therapy" (a therapeutic intervention)
> `ResearchActivity`: "clinical translation" (a research process, not a patient-care action)

> doc_1009: "In the hippocampal administration of A beta 40 induced young AD model mice, the intramedullary injection of Rab27a-shRNA adenovirus inhibits OCYYoung-EVs secretion from bone and aggravates cognitive impairment."
>
> `HealthCareActivity`: "intramedullary injection" (an administration route used therapeutically)
> `ResearchActivity`: "hippocampal administration" (an experimental procedure)

> doc_1542: "The identification of reliable biomarkers in biological fluids is paramount to optimizing the diagnosis of Alzheimer's disease (AD)."
>
> `HealthCareActivity`: "diagnosis" (a clinical-care action)

**Negative examples (same-span multi-label cases):**

> doc_101: "Polyphenolic compounds such as flavonols have shown therapeutic potential and can contribute to the treatment of these diseases."
>
> `HealthCareActivity`: "treatment" — patient-care sense
> `ResearchActivity`: "treatment" — same span, research-level sense
>
> Both labels apply to the same span because the sentence describes treatment both as a clinical act and as an object of research investigation. Same-span multi-labeling is admissible here because the two roles are non-redundant and context-supported.

> doc_107: "In this review, we summarize the studies in modelling human neurodegenerative diseases in zebrafish and medaka in recent years."
>
> `HealthCareActivity`: "review" — clinical synthesis sense
> `ResearchActivity`: "review" — same span, research publication sense

Generic terms such as "study" and "review" are normally labelled `ResearchActivity`, but may also carry `HealthCareActivity` when the text emphasises clinical-synthesis or patient-care dimensions.

---

## 3. Eukaryote vs Organism vs ExperimentalModelOfDisease

**Definitions:**

- `Eukaryote`: a specific eukaryotic species or strain name used as the subject of a biomedical statement.
- `Organism`: a broader taxonomic or ecological reference to organisms, including prokaryotes, when the text discusses organisms in general or in an ecological/community context.
- `ExperimentalModelOfDisease`: a named disease model system, including transgenic constructs, induced models, and cell-line-based disease models.

**Decision rule:**
- If the span is a *specific species name, strain designation, or individual organism reference* used as an experimental subject ("mice," "human," "wild-type mice," "zebrafish"), label it `Eukaryote`.
- If the span refers to *organisms in a taxonomic, ecological, or community-level sense* ("plants," "microbial community," "pathogens," "bacterium"), label it `Organism`.
- If the span names a *constructed or induced disease model* that includes a transgenic identifier, chemical induction, or model designation ("APP/PS1 mice," "5xFAD mouse model," "PDGFB-APP(Sw.Ind) transgenic mice"), label it `ExperimentalModelOfDisease`. These spans may overlap with or subsume `Eukaryote` spans.

**Positive examples:**

> doc_107: "Animal models of human neurodegenerative disease have been investigated for several decades."
>
> `Eukaryote`: "human" (species reference)
> `ExperimentalModelOfDisease`: "Animal models of human neurodegenerative disease" (the full model system designation)

> doc_76: "In Huntington's disease male mice, we revealed an inefficiency of FMT engraftment, which is potentially due to the more pronounced changes in the structure, composition and instability of the gut microbial community, and the imbalance in acetate and gut immune profiles found in these mice."
>
> `Eukaryote`: "mice" (specific experimental subject, both occurrences)
> `Organism`: "microbial community" (ecological/community-level organism reference)

> doc_1595: "In this study, we evaluated the intracerebral localization of p-tau in App knock-in mice with amyloid-beta plaques without neurofibrillary tangle pathology (App(NLGF)), in App knock-in mice with increased amyloid-beta levels without amyloid-beta plaques (App(NL)) and in wild-type mice."
>
> `Eukaryote`: "wild-type mice," "mice" (both occurrences; specific experimental subjects)
> `ExperimentalModelOfDisease`: "App(NLGF)," "App(NL)" (named transgenic constructs)

> doc_1081: "Most of them, including NAD(P)H-quinone oxidored ucta se, were enriched in the oxidative phosphorylation pathway in plants and humans, and Alzheimer's disease, Huntington's disease, and Parkinson's disease, which are associated with oxidative stress in humans."
>
> `Eukaryote`: "humans" (both occurrences; species reference)
> `Organism`: "plants" (broad taxonomic reference, not a specific experimental subject)

**Negative example:**

> doc_1010: "Recently, extracellular vesicles (EVs) derived from MSCs have been studied as a therapeutic candidate, as they exhibit similar immunoprotective and immunomodulatory abilities as the host human MSCs."
>
> `Eukaryote`: "human" — species modifier of MSCs
> `Organism`: "host" — ecological/relational term applied to the organism context
>
> "Host" is labelled `Organism` rather than `Eukaryote` because it describes a relational/ecological role rather than naming a specific eukaryotic species.

---

## 4. PathologicFunction vs DiseaseOrSyndrome

**Definitions:**

- `PathologicFunction`: a pathological mechanism, dysfunction process, or disease-associated molecular event at the cellular or subcellular level.
- `DiseaseOrSyndrome`: a named disease, syndrome, or clinically diagnosed condition.

**Decision rule:** If the span names a *mechanism, process, or dysfunction event* that contributes to disease ("pathogenesis," "pathophysiological changes," "oxidative stress," "apoptosis," "death" in the pathological sense), label it `PathologicFunction`. If the span names a *clinically recognised disease entity or syndrome* ("Alzheimer's disease," "Huntington's disease," "CNS disorders," "cognitive impairment"), label it `DiseaseOrSyndrome`.

**Positive examples:**

> doc_101: "An aging brain causes many pathophysiological changes and is the major risk factor for most of the neurodegenerative disorders."
>
> `PathologicFunction`: "pathophysiological changes" (mechanism/process, not a disease name)
> `DiseaseOrSyndrome`: "neurodegenerative disorders" (clinically recognised disease category)

> doc_1009: "Here, it is found that young osteocyte, the most abundant cells in bone, secretes extracellular vesicles (OCYYoung-EVs) to ameliorate cognitive impairment and the pathogenesis of AD in APP/PS1 mice and model cells."
>
> `PathologicFunction`: "pathogenesis" (disease mechanism)
> `DiseaseOrSyndrome`: "AD," "cognitive impairment" (clinically recognised conditions)

> doc_107: "Therefore, fish are a suitable model for the investigation of pathologic mechanisms of neurodegenerative diseases and for the large-scale screening of drugs for potential therapy."
>
> `PathologicFunction`: "pathologic mechanisms" (mechanism, not disease name)
> `DiseaseOrSyndrome`: "neurodegenerative diseases" (disease category)

**Negative example:**

> doc_10: "There has been substantial progress in the development of regenerative medicine strategies for CNS disorders over the last decade, with progression to early clinical studies for some conditions."
>
> `PathologicFunction`: "progression" — in this context, clinical trial progression sense; labelled `PathologicFunction` because the annotation treats the clinical progression of CNS disorders as a pathological process. This is a borderline case. When "progression" describes clinical advancement rather than disease worsening, consider whether `TemporalConcept` (also applied here as same-span) or no label is more appropriate.

---

## 5. GeneOrGenome vs AminoAcidPeptideOrProtein

**Definitions:**

- `GeneOrGenome`: a gene, allele, genomic locus, or nucleotide-level genetic element.
- `AminoAcidPeptideOrProtein`: a protein, peptide, amino acid sequence, or transcription factor product.

**Decision rule:** If the span refers to the *genetic entity at the DNA/RNA level* ("allele," "HTT gene," "CAG repeat," "locus"), label it `GeneOrGenome`. If the span refers to the *protein product or amino-acid-level entity* ("huntingtin protein," "transcription factor," "APOE," "STAT3 protein"), label it `AminoAcidPeptideOrProtein`. When a span refers to an entity that is conventionally understood at both the gene and protein level (common for gene/protein symbols like HTT, STAT3, CEBPB, SPI1), same-span multi-labeling is applied.

**Positive examples:**

> doc_13: "There are currently still no treatments available for HD, but approaches targeting the HTT levels offer systematic, mechanism-driven routes towards curing HD and other neurodegenerative diseases."
>
> `GeneOrGenome`: "HTT" (gene symbol)
> `AminoAcidPeptideOrProtein`: "HTT" (same span; protein product)
>
> This is a same-span multi-label case: the symbol "HTT" refers to both the gene and its protein product in biomedical usage.

> doc_1533: "In our approach, not only were central transcription factors (TF) STAT3, CEBPB, SPI1, and regulatory mechanisms identified more accurately than with single-omics but also immunotherapy targeting central TFs to drugs was found to be significantly different between patients."
>
> `GeneOrGenome`: "STAT3," "CEBPB," "SPI1" (gene symbols)
> `AminoAcidPeptideOrProtein`: "TF," "STAT3," "CEBPB," "SPI1," "TFs" (protein-level: transcription factors and their gene products)

> doc_1573: "Previous studies have suggested that the APOE epsilon 4 allele plays a role in the risk and age at onset of dementia in DS; however, data on in vivo biomarkers remain scarce."
>
> `GeneOrGenome`: "allele" (genetic element)
> `AminoAcidPeptideOrProtein`: "APOE epsilon 4," "APOE" (protein isoform designation)

**Negative example:**

> doc_1573: "Age at symptom onset was compared between APOE epsilon 4 allele carriers and noncarriers, and within-group local regression models were used to compare the association of biomarkers with age."
>
> `GeneOrGenome`: "allele" — refers specifically to the genetic variant, not the protein.
> `AminoAcidPeptideOrProtein`: "APOE epsilon 4," "APOE" — the protein isoform.
>
> "Carriers" describes individuals who carry the allele and is labelled `PatientOrDisabledGroup` (not shown above).

---

## 6. Generic Terms: Operational Rules

Several high-frequency generic terms caused annotator disagreement. The following decision rules are recommended for new users of the T2KNOW schema.

### evidence

Label as `Finding` when it refers to *concrete observed evidence for a specific biomedical claim*. Do not label when used as a discourse connector ("Evidence suggests that..." where "evidence" is a rhetorical placeholder).

> doc_101: "In this review, evidence for the beneficial neuroprotective effect of multiple flavonols is discussed..."
>
> `Finding`: "evidence" (concrete observed support for a specific claim)

### effects

Label as `Finding` when referring to *specific observed biological effects of a named agent*. Label as `PathologicFunction` when referring to *disease-associated functional consequences*.

> doc_1388: "Ginkgolide B (GB), a major terpene lactone and active component of Ginkgo biloba, has neuroprotective effects in several models of neurological diseases."
>
> `Finding`: "neuroprotective effects" (specific observed biological effect)

> doc_1592: "Background Intranasally administered insulin has shown promise in both rodent and human studies in Alzheimer's disease; however, both effects and mechanisms require elucidation."
>
> `PathologicFunction`: "effects" (disease-associated consequences, not a specific finding)

### study

Label as `ResearchActivity` when referring to *a named research investigation or experimental study*. Do not label in phrases like "studies have shown" where it is a citation rhetorical device without a concrete study design referent.

> doc_1009: "The study uncovers the role of OCY-EV as a regulator of brain health..."
>
> `ResearchActivity`: "study" (named research investigation)

### diagnosis

Label as `HealthCareActivity` when referring to the *clinical act of diagnosing a patient*. Do not label when used as part of a disease name ("diagnosis of AD" where the focus is the disease, not the diagnostic act).

> doc_1542: "The identification of reliable biomarkers in biological fluids is paramount to optimizing the diagnosis of Alzheimer's disease (AD)."
>
> `HealthCareActivity`: "diagnosis" (clinical diagnostic act)

> doc_1588: "Conclusions These findings support use of U-p53(AZ) as blood-based biomarker predicting whether individuals would reach neuropsychologically-defined AD within six years prior to AD diagnosis."
>
> `HealthCareActivity`: "diagnosis" (clinical diagnostic endpoint)

### model

Label as `ResearchActivity` when referring to *a statistical, computational, or conceptual model*. Label as `ExperimentalModelOfDisease` when referring to *an animal or cellular disease model system*. Do not label the generic noun "model" when it appears as a vague descriptor.

> doc_1570: "To explore the relationship between cognitive performance and relevant factors, a linear model was set up."
>
> `ResearchActivity`: "linear model" (statistical model)

> doc_1009: "In the hippocampal administration of A beta 40 induced young AD model mice..."
>
> `ExperimentalModelOfDisease`: "induced young AD model mice" (disease model system)

### mouse / mice

Label as `Eukaryote` when referring to *the species/strain as an experimental subject*. Label as `ExperimentalModelOfDisease` when the span includes a *disease-model designation* (transgenic identifier, induction method, or disease phenotype qualifier).

> doc_1394: "The aim of this study was to examine the alterations in astrocyte and related oligodendrocyte GJs in association with A beta plaques in the spinal cord of the 5xFAD mouse model of AD."
>
> `ExperimentalModelOfDisease`: "5xFAD mouse model of AD" (full model designation including transgenic identifier)

> doc_1396: "Here, the authors show that INs myelination shapes feedforward inhibition of mouse cortical sensory circuits and impacts whisker-mediated behaviour."
>
> `Eukaryote`: "mouse" (species reference as experimental subject)

### Gene/protein symbols (e.g., HTT, APOE, STAT3, TP53)

Apply same-span multi-labeling (`GeneOrGenome` + `AminoAcidPeptideOrProtein`) when the symbol conventionally refers to both the gene and its protein product in biomedical usage. This is the default rule for most human gene/protein symbols in biomedical abstracts. Do not apply both labels when the context makes it explicit that only one level is intended (e.g., "...the HTT gene promoter..." → `GeneOrGenome` only; "...huntingtin protein aggregates..." → `AminoAcidPeptideOrProtein` only). Not all gene/protein/substance ontology relations are multi-labeled: same-span multi-labeling requires non-redundant, context-supported roles, and the local context must support each role independently. When in doubt, prefer the narrower context-supported label and avoid adding a second label solely from source-ontology layering.

---

## Summary Table

| Term / Pair | Primary Label | Secondary / Same-Span Label | Key Distinction |
|---|---|---|---|
| `Finding` vs `ClinicalAttribute` | Assay result, observed effect | Measurable trait, biomarker | Observation vs patient characteristic |
| `HealthCareActivity` vs `ResearchActivity` | Clinical intervention, therapy | Experimental method, study design | Patient-care action vs research technique |
| `Eukaryote` | Specific species/strain | — | Named experimental subject |
| `Organism` | Broad taxonomic/ecological reference | — | Community-level organism mention |
| `ExperimentalModelOfDisease` | Constructed disease model system | May overlap `Eukaryote` | Includes transgenic/induced designation |
| `PathologicFunction` | Disease mechanism, dysfunction | — | Cellular/molecular process |
| `DiseaseOrSyndrome` | Clinically diagnosed condition | — | Named disease entity |
| `GeneOrGenome` | DNA/RNA-level genetic entity | Same-span with `AminoAcidPeptideOrProtein` | Gene symbol convention |
| `AminoAcidPeptideOrProtein` | Protein product, amino acid entity | Same-span with `GeneOrGenome` | Protein symbol convention |
| `evidence` | `Finding` (concrete observed evidence) | — | Concrete vs rhetorical |
| `effects` | `Finding` (biological) or `PathologicFunction` (disease) | — | Observed biology vs disease consequence |
| `study` | `ResearchActivity` (named investigation) | — | Named investigation vs rhetorical device |
| `diagnosis` | `HealthCareActivity` (clinical act) | — | Clinical act vs disease name component |
| `model` | `ResearchActivity` (statistical) or `ExperimentalModelOfDisease` (disease system) | — | Statistical/computational vs biological disease model |
| `mouse` / `mice` | `Eukaryote` (species) or `ExperimentalModelOfDisease` (model) | — | Subject vs constructed disease model |
