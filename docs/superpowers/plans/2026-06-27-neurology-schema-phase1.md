# Neurology Schema Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and freeze `neurology_schema_v1`, a lightweight domain schema for Hyper-RAG entity and hyperedge extraction on the Neurology dataset.

**Architecture:** This phase does not modify runtime code. It creates a dataset-matched schema that later phases will inject into prompts, parsers, vector-db metadata, schema validation, and query-time weighting. The schema acts like a lightweight Neo4j-style ontology: entity types, relation types, allowed type patterns, high-order hyperedge rules, field names, alias normalization, and validation policy.

**Tech Stack:** Markdown documentation, YAML schema configuration, existing Hyper-RAG dataset files under `datasets/neurology/`, later integration points in `hyperrag/prompt.py`, `hyperrag/operate.py`, and `hyperrag/hyperrag.py`.

---

## Scope

Phase 1 only defines and validates the domain schema. It must not change extraction code, query code, storage code, or caches.

The schema is designed for:

- `datasets/neurology/neurology.jsonl`
- domain RAG over neurology textbook-like content
- later type-aware entity and relation extraction
- later query-aware retrieval and adaptive hypergraph diffusion

The schema is not intended to be:

- a complete medical ontology
- a UMLS replacement
- a strict clinical decision system
- a hard database constraint that rejects every schema mismatch

---

## Deliverables

Create these files:

- `docs/schema/neurology_schema.md`
  - Human-readable schema explanation.
  - Defines entity types, relation types, high-order hyperedge types, allowed patterns, field names, validation policy, and known limitations.

- `docs/schema/neurology_schema.yaml`
  - Machine-readable schema configuration.
  - Later phases should load or mirror this structure into prompt construction and schema validation.

- `docs/schema/neurology_schema_calibration.md`
  - Sampling notes from the Neurology dataset.
  - Records high-frequency entity candidates, relation candidates, confusing cases, and schema adjustment decisions.

No code files should be modified in this phase.

---

## File Responsibilities

`docs/schema/neurology_schema.md`

- Explains what the schema is and is not.
- Gives definitions and examples for every entity type and relation type.
- Explains allowed patterns and validation labels in Chinese.
- Helps later AI agents understand the research intent quickly.

`docs/schema/neurology_schema.yaml`

- Stores the canonical schema.
- Uses stable uppercase type labels.
- Includes aliases for normalization.
- Includes relation allowed patterns.
- Includes high-order relation types.
- Includes validation policy.

`docs/schema/neurology_schema_calibration.md`

- Captures evidence from sampled dataset contexts.
- Lists what appeared frequently.
- Records why certain types were kept, merged, or excluded.
- Records expected thresholds for `OTHER`, `weak_valid`, and `invalid`.

---

## Task 1: Create Schema Directory

**Files:**

- Create directory: `docs/schema/`

- [ ] **Step 1: Create the directory**

Run:

```powershell
New-Item -ItemType Directory -Force docs\schema
```

Expected:

```text
docs/schema exists.
```

- [ ] **Step 2: Confirm no code files changed**

Run:

```powershell
git status --short
```

Expected:

```text
Only docs/superpowers/plans/... may already be present from plan persistence.
No hyperrag/*.py files are changed by this phase.
```

---

## Task 2: Sample Neurology Dataset

**Files:**

- Read: `datasets/neurology/neurology.jsonl`
- Create: `docs/schema/neurology_schema_calibration.md`

- [ ] **Step 1: Inspect sample records**

Read the dataset structure and sample several records.

Run:

```powershell
Get-Content -Path datasets\neurology\neurology.jsonl -TotalCount 5
```

Expected:

```text
Each line is JSONL with fields such as id, title, context, contexts.
The content field contains the main source text used by current Step_0.
```

- [ ] **Step 2: Sample 50-100 contexts manually or semi-automatically**

Collect examples that reveal common Neurology entities and relationships.

Focus on:

- diseases
- symptoms
- clinical signs
- drugs
- treatments
- examinations
- anatomical structures
- mechanisms
- physiological functions
- risk factors
- diagnostic criteria

- [ ] **Step 3: Record calibration notes**

Create `docs/schema/neurology_schema_calibration.md` with this structure:

```markdown
# Neurology Schema Calibration Notes

## Sampling Scope

- Dataset: `datasets/neurology/neurology.jsonl`
- Sample size: 50-100 contexts
- Purpose: identify stable entity types, relation types, and high-order relation patterns for Hyper-RAG extraction.

## Frequent Entity Candidates

| Candidate | Likely Type | Example Mentions | Notes |
| --- | --- | --- | --- |
| Alzheimer disease | DISEASE |  |  |
| tremor | SIGN |  |  |
| headache | SYMPTOM |  |  |

## Frequent Relation Candidates

| Relation Expression | Likely Relation Type | Example Entity Types | Notes |
| --- | --- | --- | --- |
| X treats Y | TREATS | DRUG -> DISEASE |  |
| X indicates Y | INDICATES | SIGN -> DISEASE |  |

## Confusing Cases

| Case | Options | Decision |
| --- | --- | --- |
| symptom vs sign | SYMPTOM / SIGN |  |
| drug vs treatment | DRUG / TREATMENT |  |

## Schema Adjustment Decisions

| Decision | Reason |
| --- | --- |
| Keep SYMPTOM and SIGN separate | They play different roles in clinical reasoning. |
| Use OTHER as fallback | Avoid forcing incorrect labels. |
```

Expected:

```text
The calibration file explains why the schema matches this dataset.
```

---

## Task 3: Define Entity Types

**Files:**

- Create/modify: `docs/schema/neurology_schema.md`
- Create/modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Define the first stable entity type set**

Use this first version unless calibration strongly shows a type is unnecessary:

```text
DISEASE
SYMPTOM
SIGN
DRUG
TREATMENT
EXAMINATION
ANATOMICAL_STRUCTURE
PHYSIOLOGICAL_FUNCTION
PATHOLOGICAL_MECHANISM
GENE
PROTEIN
PATHWAY
RISK_FACTOR
DIAGNOSTIC_CRITERION
OTHER
```

- [ ] **Step 2: Document each entity type**

In `docs/schema/neurology_schema.md`, include this table:

```markdown
## Entity Types

| Type | Meaning | Examples | Boundary Notes |
| --- | --- | --- | --- |
| DISEASE | A named neurological or medical disease/disorder. | Alzheimer disease, stroke, multiple sclerosis | Use DISEASE for diagnosed conditions, not single symptoms. |
| SYMPTOM | Subjective patient-reported abnormal experience. | headache, dizziness, memory loss | Use SIGN for objective clinician-observed findings. |
| SIGN | Objective clinical finding observed or measured by clinicians. | tremor, Babinski sign, nystagmus | Use SYMPTOM when the text describes patient experience. |
| DRUG | A medication or chemical therapeutic agent. | levodopa, aspirin, dopamine agonist | Use TREATMENT for non-drug interventions. |
| TREATMENT | A therapeutic intervention, procedure, or management strategy. | surgery, rehabilitation, deep brain stimulation | Use DRUG for specific medications. |
| EXAMINATION | A diagnostic test, imaging, lab, or clinical examination. | MRI, EEG, lumbar puncture | Use DIAGNOSTIC_CRITERION for named diagnostic criteria. |
| ANATOMICAL_STRUCTURE | A body, nervous system, brain, nerve, or tissue structure. | basal ganglia, cortex, spinal cord | Use PHYSIOLOGICAL_FUNCTION for functions, not structures. |
| PHYSIOLOGICAL_FUNCTION | Normal biological or neurological function. | memory, motor control, consciousness | Use PATHOLOGICAL_MECHANISM for abnormal disease processes. |
| PATHOLOGICAL_MECHANISM | Disease mechanism or abnormal biological process. | demyelination, ischemia, neurodegeneration | Use CAUSES/MECHANISM_OF relations to connect it to disease. |
| GENE | A gene or genetic locus. | APOE, HTT | If rare in sampled data, keep but avoid over-emphasizing in analysis. |
| PROTEIN | A protein or molecular product. | tau, amyloid beta | Use GENE for gene names. |
| PATHWAY | Biological, molecular, or signaling pathway. | dopamine pathway, inflammatory pathway | Use PATHOLOGICAL_MECHANISM if text describes a disease process rather than named pathway. |
| RISK_FACTOR | A factor that increases disease likelihood or severity. | age, hypertension, family history | Use CAUSES only when text states direct causation. |
| DIAGNOSTIC_CRITERION | A named criterion, threshold, or diagnostic rule. | diagnostic criteria, clinical criteria | Use EXAMINATION for tests. |
| OTHER | Fallback type when no schema type fits. |  | Should be low-frequency. High OTHER ratio means schema is too narrow. |
```

- [ ] **Step 3: Add entity types to YAML**

In `docs/schema/neurology_schema.yaml`, add:

```yaml
domain: neurology
version: neurology_schema_v1

entity_types:
  DISEASE:
    description: A named neurological or medical disease/disorder.
    examples: ["Alzheimer disease", "stroke", "multiple sclerosis"]
    aliases: ["disorder", "illness", "condition"]
  SYMPTOM:
    description: Subjective patient-reported abnormal experience.
    examples: ["headache", "dizziness", "memory loss"]
    aliases: ["complaint", "subjective symptom"]
  SIGN:
    description: Objective clinical finding observed or measured by clinicians.
    examples: ["tremor", "Babinski sign", "nystagmus"]
    aliases: ["clinical sign", "physical sign"]
  DRUG:
    description: A medication or chemical therapeutic agent.
    examples: ["levodopa", "aspirin", "dopamine agonist"]
    aliases: ["medicine", "medication", "pharmacologic agent"]
  TREATMENT:
    description: A therapeutic intervention, procedure, or management strategy.
    examples: ["surgery", "rehabilitation", "deep brain stimulation"]
    aliases: ["therapy", "management", "intervention"]
  EXAMINATION:
    description: A diagnostic test, imaging, lab, or clinical examination.
    examples: ["MRI", "EEG", "lumbar puncture"]
    aliases: ["test", "scan", "imaging", "clinical examination"]
  ANATOMICAL_STRUCTURE:
    description: A body, nervous system, brain, nerve, or tissue structure.
    examples: ["basal ganglia", "cortex", "spinal cord"]
    aliases: ["brain region", "nerve structure", "tissue"]
  PHYSIOLOGICAL_FUNCTION:
    description: Normal biological or neurological function.
    examples: ["memory", "motor control", "consciousness"]
    aliases: ["function", "normal function"]
  PATHOLOGICAL_MECHANISM:
    description: Disease mechanism or abnormal biological process.
    examples: ["demyelination", "ischemia", "neurodegeneration"]
    aliases: ["pathogenesis", "mechanism", "disease process"]
  GENE:
    description: A gene or genetic locus.
    examples: ["APOE", "HTT"]
    aliases: ["genetic locus"]
  PROTEIN:
    description: A protein or molecular product.
    examples: ["tau", "amyloid beta"]
    aliases: ["peptide", "molecular product"]
  PATHWAY:
    description: Biological, molecular, or signaling pathway.
    examples: ["dopamine pathway", "inflammatory pathway"]
    aliases: ["signaling pathway", "biological pathway"]
  RISK_FACTOR:
    description: A factor that increases disease likelihood or severity.
    examples: ["age", "hypertension", "family history"]
    aliases: ["predisposing factor", "risk"]
  DIAGNOSTIC_CRITERION:
    description: A named criterion, threshold, or diagnostic rule.
    examples: ["diagnostic criteria", "clinical criteria"]
    aliases: ["criterion", "criteria", "diagnostic rule"]
  OTHER:
    description: Fallback type when no schema type fits.
    examples: []
    aliases: ["unknown", "misc"]
```

Expected:

```text
Entity types are stable, uppercase, and include aliases.
```

---

## Task 4: Define Relation Types

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Define first relation type set**

Use this first version:

```text
CAUSES
ASSOCIATED_WITH
INDICATES
DIAGNOSES
TREATS
PREVENTS
COMPLICATES
LOCATED_IN
AFFECTS
REGULATES
PART_OF
INTERACTS_WITH
MECHANISM_OF
RISK_FACTOR_FOR
DIFFERENTIAL_DIAGNOSIS
CO_OCCURS_WITH
OTHER
```

- [ ] **Step 2: Document relation types**

In `docs/schema/neurology_schema.md`, include:

```markdown
## Relation Types

| Type | Meaning | Boundary Notes |
| --- | --- | --- |
| CAUSES | One entity directly causes another. | Use ASSOCIATED_WITH if causality is not explicit. |
| ASSOCIATED_WITH | General association without clear direction or causality. | Use this when the text is weaker than CAUSES. |
| INDICATES | One finding suggests or points to another. | Often symptom/sign/exam -> disease. |
| DIAGNOSES | One test, criterion, or process is used to diagnose another. | Stronger and more procedural than INDICATES. |
| TREATS | One drug or treatment improves or manages another entity. | Use PREVENTS for prevention. |
| PREVENTS | One intervention reduces likelihood of another. | Do not use for treatment after disease onset. |
| COMPLICATES | One disease/event worsens, complicates, or results as complication of another. | Use CO_OCCURS_WITH when no complication is stated. |
| LOCATED_IN | One entity is anatomically located in another. | Usually disease/process -> structure. |
| AFFECTS | One entity changes or impacts another. | Broader than REGULATES. |
| REGULATES | One entity modulates or controls another biological process. | Usually molecular/pathway/function relation. |
| PART_OF | One entity is a component of another. | Use LOCATED_IN for spatial location. |
| INTERACTS_WITH | Two drugs, proteins, pathways, or entities interact. | Use REGULATES for directional control. |
| MECHANISM_OF | One mechanism explains another entity. | Usually mechanism/pathway/function -> disease. |
| RISK_FACTOR_FOR | One entity increases risk of another. | Use CAUSES only for direct causality. |
| DIFFERENTIAL_DIAGNOSIS | Diseases or syndromes that must be distinguished. | Usually disease -> disease. |
| CO_OCCURS_WITH | Entities appear together without a stronger relation. | Weaker than COMPLICATES or ASSOCIATED_WITH. |
| OTHER | Fallback relation type. | High OTHER ratio means relation schema is too narrow. |
```

- [ ] **Step 3: Add relation types and aliases to YAML**

In `docs/schema/neurology_schema.yaml`, append:

```yaml
relation_types:
  CAUSES:
    description: One entity directly causes another.
    aliases: ["causal", "leads_to", "results_in"]
  ASSOCIATED_WITH:
    description: General association without clear direction or causality.
    aliases: ["associated", "related_to", "linked_to"]
  INDICATES:
    description: One finding suggests or points to another.
    aliases: ["suggests", "points_to", "marker_of"]
  DIAGNOSES:
    description: One test, criterion, or process is used to diagnose another.
    aliases: ["diagnostic", "confirms", "used_to_diagnose"]
  TREATS:
    description: One drug or treatment improves or manages another entity.
    aliases: ["treatment", "therapy", "therapeutic"]
  PREVENTS:
    description: One intervention reduces likelihood of another.
    aliases: ["prevention", "protects_against"]
  COMPLICATES:
    description: One disease/event worsens, complicates, or is a complication of another.
    aliases: ["complication", "worsens"]
  LOCATED_IN:
    description: One entity is anatomically located in another.
    aliases: ["located", "site_of", "localizes_to"]
  AFFECTS:
    description: One entity changes or impacts another.
    aliases: ["impacts", "influences", "changes"]
  REGULATES:
    description: One entity modulates or controls another biological process.
    aliases: ["modulates", "controls"]
  PART_OF:
    description: One entity is a component of another.
    aliases: ["component_of", "belongs_to"]
  INTERACTS_WITH:
    description: Two drugs, proteins, pathways, or entities interact.
    aliases: ["interaction", "interacts"]
  MECHANISM_OF:
    description: One mechanism explains another entity.
    aliases: ["pathogenesis_of", "explains", "underlies"]
  RISK_FACTOR_FOR:
    description: One entity increases risk of another.
    aliases: ["risk", "predisposes_to"]
  DIFFERENTIAL_DIAGNOSIS:
    description: Diseases or syndromes that must be distinguished.
    aliases: ["differential", "distinguish_from"]
  CO_OCCURS_WITH:
    description: Entities appear together without a stronger relation.
    aliases: ["co_occurs", "coexists_with"]
  OTHER:
    description: Fallback relation type.
    aliases: ["unknown", "misc"]
```

Expected:

```text
Relation labels are stable and not overly fine-grained.
```

---

## Task 5: Define Allowed Patterns

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Document allowed-pattern semantics**

Add this explanation to `docs/schema/neurology_schema.md`:

```markdown
## Allowed Patterns

Allowed patterns define medically plausible type combinations for relation labels. They are not strict database constraints in phase 1. Later phases can use them for `schema_validity` and soft ranking.

- `valid`: entity types and relation type match a known pattern.
- `weak_valid`: entity and relation types are known, but the exact pattern is not listed.
- `invalid`: unknown type or clearly implausible pattern.

Phase 1 policy: do not hard-delete weak or invalid edges. Mark them for later weighting.
```

- [ ] **Step 2: Add allowed patterns to YAML**

Append:

```yaml
allowed_patterns:
  TREATS:
    - ["DRUG", "DISEASE"]
    - ["DRUG", "SYMPTOM"]
    - ["TREATMENT", "DISEASE"]
    - ["TREATMENT", "SYMPTOM"]
  PREVENTS:
    - ["DRUG", "DISEASE"]
    - ["TREATMENT", "DISEASE"]
    - ["RISK_FACTOR", "DISEASE"]
  DIAGNOSES:
    - ["EXAMINATION", "DISEASE"]
    - ["DIAGNOSTIC_CRITERION", "DISEASE"]
  INDICATES:
    - ["SYMPTOM", "DISEASE"]
    - ["SIGN", "DISEASE"]
    - ["EXAMINATION", "DISEASE"]
  MECHANISM_OF:
    - ["PATHOLOGICAL_MECHANISM", "DISEASE"]
    - ["PATHWAY", "DISEASE"]
    - ["PHYSIOLOGICAL_FUNCTION", "DISEASE"]
  LOCATED_IN:
    - ["DISEASE", "ANATOMICAL_STRUCTURE"]
    - ["PATHOLOGICAL_MECHANISM", "ANATOMICAL_STRUCTURE"]
    - ["SIGN", "ANATOMICAL_STRUCTURE"]
  RISK_FACTOR_FOR:
    - ["RISK_FACTOR", "DISEASE"]
  DIFFERENTIAL_DIAGNOSIS:
    - ["DISEASE", "DISEASE"]
  PART_OF:
    - ["PROTEIN", "PATHWAY"]
    - ["ANATOMICAL_STRUCTURE", "ANATOMICAL_STRUCTURE"]
  REGULATES:
    - ["PROTEIN", "PATHWAY"]
    - ["GENE", "PROTEIN"]
    - ["PATHWAY", "PHYSIOLOGICAL_FUNCTION"]
  INTERACTS_WITH:
    - ["DRUG", "DRUG"]
    - ["PROTEIN", "PROTEIN"]
    - ["PATHWAY", "PATHWAY"]
  COMPLICATES:
    - ["DISEASE", "DISEASE"]
    - ["DISEASE", "SYMPTOM"]
  AFFECTS:
    - ["DISEASE", "PHYSIOLOGICAL_FUNCTION"]
    - ["PATHOLOGICAL_MECHANISM", "PHYSIOLOGICAL_FUNCTION"]
    - ["DISEASE", "ANATOMICAL_STRUCTURE"]
  ASSOCIATED_WITH:
    - ["DISEASE", "DISEASE"]
    - ["GENE", "DISEASE"]
    - ["PROTEIN", "DISEASE"]
    - ["SYMPTOM", "DISEASE"]
  CO_OCCURS_WITH:
    - ["SYMPTOM", "SYMPTOM"]
    - ["SYMPTOM", "SIGN"]
    - ["DISEASE", "DISEASE"]
```

Expected:

```text
Allowed patterns cover common neurology relations while staying permissive enough for discovery.
```

---

## Task 6: Define High-Order Hyperedge Rules

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Add high-order relation type definitions**

Use:

```text
MULTI_FACTOR_MECHANISM
CLINICAL_SYNDROME
DIAGNOSTIC_PATTERN
THERAPEUTIC_STRATEGY
COMORBIDITY_PATTERN
PATHWAY_PROCESS
DIFFERENTIAL_GROUP
OTHER
```

- [ ] **Step 2: Document high-order edge criteria**

Add this to `docs/schema/neurology_schema.md`:

```markdown
## High-Order Hyperedge Rules

A high-order hyperedge should connect at least three entities and express a shared medical pattern, mechanism, diagnostic constellation, treatment strategy, comorbidity pattern, or pathway process.

Do not create high-order hyperedges by simply grouping every entity in the same chunk. A valid high-order hyperedge needs a meaningful shared relation.

Preferred patterns:

- DISEASE + SYMPTOM + SIGN
- DISEASE + EXAMINATION + DIAGNOSTIC_CRITERION
- DISEASE + DRUG + TREATMENT
- DISEASE + PATHOLOGICAL_MECHANISM + ANATOMICAL_STRUCTURE
- GENE + PROTEIN + PATHWAY + DISEASE
```

- [ ] **Step 3: Add high-order types to YAML**

Append:

```yaml
high_order_relation_types:
  MULTI_FACTOR_MECHANISM:
    description: Multiple entities jointly describe a disease mechanism.
  CLINICAL_SYNDROME:
    description: Multiple symptoms or signs jointly describe a clinical syndrome.
  DIAGNOSTIC_PATTERN:
    description: Multiple findings, tests, or criteria jointly support diagnosis.
  THERAPEUTIC_STRATEGY:
    description: Multiple treatments, drugs, or management factors form a treatment strategy.
  COMORBIDITY_PATTERN:
    description: Multiple diseases or risk factors form a comorbidity pattern.
  PATHWAY_PROCESS:
    description: Multiple genes, proteins, pathways, or mechanisms form a biological process.
  DIFFERENTIAL_GROUP:
    description: Multiple diseases or syndromes should be distinguished from each other.
  OTHER:
    description: Fallback high-order relation type.
```

Expected:

```text
High-order edges have a clear purpose beyond grouping nearby entities.
```

---

## Task 7: Define Field Contract

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Document canonical field names**

Add to Markdown:

```markdown
## Field Contract

Entity fields:

- `entity_name`
- `entity_type`
- `description`
- `additional_properties`
- `source_id`

Hyperedge fields:

- `entity_set`
- `edge_type`
- `description`
- `generalization`
- `keywords`
- `weight`
- `source_id`
- `level_hg`
- `schema_validity`

Use `edge_type` consistently for relation type. Do not mix `relationship_type`, `relation_type`, and `edge_type` in code or data.
```

- [ ] **Step 2: Add field contract to YAML**

Append:

```yaml
field_contract:
  entity:
    - entity_name
    - entity_type
    - description
    - additional_properties
    - source_id
  hyperedge:
    - entity_set
    - edge_type
    - description
    - generalization
    - keywords
    - weight
    - source_id
    - level_hg
    - schema_validity
```

Expected:

```text
Later implementation uses the same field names everywhere.
```

---

## Task 8: Define Normalization and Validation Policy

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Document alias normalization**

Add:

```markdown
## Normalization Policy

LLM outputs should prefer canonical uppercase labels from this schema. If the LLM emits an alias, later parsing should normalize it to the canonical label.

Examples:

- disorder, illness, condition -> DISEASE
- medication, medicine -> DRUG
- test, scan, imaging -> EXAMINATION
- pathogenesis, mechanism -> PATHOLOGICAL_MECHANISM
- treatment, therapy, therapeutic -> TREATS
- diagnostic, used_to_diagnose -> DIAGNOSES
- suggests, marker_of -> INDICATES
```

- [ ] **Step 2: Document validation policy**

Add:

```markdown
## Validation Policy

Schema validation should be soft in the first implementation.

- `valid`: entity types and edge type match an allowed pattern.
- `weak_valid`: entity types and edge type are known, but the pattern is not listed.
- `invalid`: unknown type or clearly implausible pattern.

Recommended phase-2 behavior:

- keep `valid` edges normally
- keep `weak_valid` edges but allow slight ranking penalty
- keep `invalid` edges as `OTHER` or apply stronger ranking penalty
- do not hard-delete edges in the first implementation
```

- [ ] **Step 3: Add validation policy to YAML**

Append:

```yaml
validation:
  unknown_entity_type: OTHER
  unknown_relation_type: OTHER
  unknown_high_order_relation_type: OTHER
  pattern_policy:
    valid: keep
    weak_valid: keep_with_soft_penalty
    invalid: keep_as_other_or_penalize
  target_thresholds:
    max_other_ratio: 0.20
    max_invalid_ratio: 0.10
```

Expected:

```text
The schema supports both extraction control and later retrieval weighting.
```

---

## Task 9: Self-Review the Schema

**Files:**

- Review: `docs/schema/neurology_schema.md`
- Review: `docs/schema/neurology_schema.yaml`
- Review: `docs/schema/neurology_schema_calibration.md`

- [ ] **Step 1: Check schema consistency**

Verify:

- every type in `allowed_patterns` exists under `entity_types`
- every relation in `allowed_patterns` exists under `relation_types`
- every high-order type is documented in Markdown
- all canonical labels are uppercase
- fallback type `OTHER` exists in entity, relation, and high-order sections

- [ ] **Step 2: Check field-name consistency**

Verify:

- use `edge_type`, not mixed names
- use `schema_validity`, not mixed names
- use `entity_set` in docs for hyperedge connected entities

- [ ] **Step 3: Check calibration grounding**

Verify:

- schema decisions cite sampled Neurology data patterns
- confusing cases have decisions
- `OTHER` and `invalid` thresholds are recorded

Expected:

```text
The schema is internally consistent and grounded in dataset observations.
```

---

## Task 10: Freeze `neurology_schema_v1`

**Files:**

- Modify: `docs/schema/neurology_schema.md`
- Modify: `docs/schema/neurology_schema.yaml`

- [ ] **Step 1: Add version note**

Add to Markdown:

```markdown
## Version

- Schema version: `neurology_schema_v1`
- Dataset: `datasets/neurology/neurology.jsonl`
- Purpose: Domain-aware typed hypergraph indexing for Hyper-RAG.
- Status: Frozen for phase-2 prompt and parser integration.
```

- [ ] **Step 2: Confirm YAML version**

Ensure YAML contains:

```yaml
domain: neurology
version: neurology_schema_v1
```

- [ ] **Step 3: Record phase-2 integration points**

Add to Markdown:

```markdown
## Phase-2 Integration Points

The next phase should wire this schema into:

- `hyperrag/prompt.py`: prompt type lists, relation type lists, allowed-pattern guidance, examples.
- `hyperrag/operate.py`: edge type parsing, high-order generalization retention, schema validity field, VDB content construction.
- `hyperrag/hyperrag.py`: VDB `meta_fields` for `entity_type` and `edge_type`.

Phase 2 must rebuild the knowledge base after code integration.
```

Expected:

```text
Phase 1 has a stable schema artifact ready for code integration.
```

---

## Acceptance Criteria

Phase 1 is complete when all are true:

- `docs/schema/neurology_schema.md` exists.
- `docs/schema/neurology_schema.yaml` exists.
- `docs/schema/neurology_schema_calibration.md` exists.
- Entity types are defined with meanings, examples, and boundary notes.
- Relation types are defined with meanings and boundary notes.
- High-order hyperedge types and preferred patterns are defined.
- Allowed relation/entity type patterns are defined.
- Field contract is defined.
- Alias normalization policy is defined.
- Schema validation policy is defined.
- `neurology_schema_v1` is marked frozen for phase-2 integration.
- No `hyperrag/*.py` code files are changed in this phase.

---

## Phase-1 Summary for Future Agents

This phase creates the domain schema that turns Hyper-RAG's free-form extraction into domain-aware typed hypergraph indexing. The schema should be specific enough to match the Neurology dataset, but not so strict that it blocks useful medical knowledge. Later phases should use this schema to guide prompt extraction, normalize labels, validate hyperedges, enrich vector-db embedding content, and provide type signals for query routing and adaptive diffusion.
