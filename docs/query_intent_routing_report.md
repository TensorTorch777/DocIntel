# Query Intent Routing Report

| Case | Detected intent | Pipeline | Evidence required | Answer template | Match |
|------|-----------------|----------|-------------------|-----------------|-------|
| definition_validation | verification | verification_qa | definition | verification | ✓ |
| compare_entities | comparison | comparison_qa | behavior, definition | comparison | ✓ |
| procedural_sequence | procedural | procedural_extraction | behavior, procedural | procedural | ✓ |
| hallucination_resistance | verification | verification_qa | definition, exceptions, interactions | verification | ✓ |

## Details

### definition_validation
**Query:** CR0.PG means Page Global Enable. Is this correct?
**Expected:** verification → verification_qa
**Detected:** verification → verification_qa
**Evidence categories:** definition
**Answer template:** verification
**Reasons:** validation phrasing (e.g. 'is this correct')
**Notes:** Should answer NO: CR0.PG=Paging Enable; CR4.PGE=Page Global Enable

### compare_entities
**Query:** Differentiate CR0.PG and CR4.PGE — what does each bit enable?
**Expected:** comparison → comparison_qa
**Detected:** comparison → comparison_qa
**Evidence categories:** behavior, definition
**Answer template:** comparison
**Reasons:** comparison/differentiation phrasing
**Notes:** One definition per bit with citations

### procedural_sequence
**Query:** Explain the sequence required to transition from real-address mode to IA-32e mode.
**Expected:** procedural → procedural_extraction
**Detected:** procedural → procedural_extraction
**Evidence categories:** behavior, procedural
**Answer template:** procedural
**Reasons:** sequence/step/transition request
**Notes:** Gate on procedural+behavior evidence, not definition-only

### hallucination_resistance
**Query:** Does setting NXE always cause a #GP fault regardless of paging mode?
**Expected:** verification → verification_qa
**Detected:** verification → verification_qa
**Evidence categories:** definition, exceptions, interactions
**Answer template:** verification
**Reasons:** no specialized intent markers, exception/claim language — prefer conservative QA
**Notes:** Conservative yes/no with source-backed exception behavior
