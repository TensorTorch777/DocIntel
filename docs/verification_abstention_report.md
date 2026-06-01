# Verification & Abstention Report

| Case | Intent | Abstain? | Confidence | Refutation | Final answer |
|------|--------|----------|------------|------------|--------------|
| cr3_fault_address | verification | no | high | yes | NO. The processor loads CR2 (not CR3) with the linear address that generated the |
| cr0_pg_validation | verification | no | high | yes | NO. CR0.PG is Paging Enable, not Page Global Enable (Page Global Enable is CR4.P |
| cr2_pdbr_role | verification | no | high | yes | NO. Sources assign page-directory base to CR3, not CR2: CR3 — Page-Directory-Bas |

## Details

### cr3_fault_address
**Query:** Does CR3 store the faulting address during a page fault?
**Detected intent:** verification → verification_qa
**Evidence required:** behavior, exceptions
**Coverage:** {"definition": 0.0, "behavior": 0.25, "exceptions": 1.0, "interactions": 0.5, "procedural": 0.25, "query_relevance": 0.5, "total_weighted": 0.5833333333333334, "missing_categories": ["behavior"]}
**Abstention decision:** PROCEED
**Answer template:** verification
**Final answer:** NO. The processor loads CR2 (not CR3) with the linear address that generated the exception [Source 1, p. 3390]

### cr0_pg_validation
**Query:** CR0.PG means Page Global Enable. Is this correct?
**Detected intent:** verification → verification_qa
**Evidence required:** behavior, exceptions
**Coverage:** {"definition": 0.7, "behavior": 0.5, "exceptions": 0.25, "interactions": 1.0, "procedural": 0.25, "query_relevance": 0.6, "total_weighted": 0.38888888888888884, "missing_categories": ["exceptions"]}
**Abstention decision:** PROCEED
**Answer template:** verification
**Final answer:** NO. CR0.PG is Paging Enable, not Page Global Enable (Page Global Enable is CR4.PGE) [Source 1, p. 2100]

### cr2_pdbr_role
**Query:** Is CR2 the page-directory base register?
**Detected intent:** verification → verification_qa
**Evidence required:** behavior, exceptions
**Coverage:** {"definition": 0.2333333333333333, "behavior": 0.25, "exceptions": 0.25, "interactions": 0.5, "procedural": 0.25, "query_relevance": 1.0, "total_weighted": 0.25, "missing_categories": ["exceptions", "behavior"]}
**Abstention decision:** PROCEED
**Answer template:** verification
**Final answer:** NO. Sources assign page-directory base to CR3, not CR2: CR3 — Page-Directory-Base Register (PDBR) [Source 1, p. 2500]
