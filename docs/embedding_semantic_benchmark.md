# Semantic Embedding Benchmark

**Model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Metric:** cosine similarity (L2-normalized (production — matches Chroma hnsw:space=cosine))  
**Cases:** 8

## Aggregate metrics

| Metric | Value |
|--------|-------|
| Recall@1 | 87.5% |
| Recall@3 | 100.0% |
| MRR | 0.9167 |
| Mean gold cosine | 0.5728 |
| Mean distractor cosine | 0.3992 |
| Mean gold − distractor margin | 0.1735 |

## Per-case results

| Case | Best gold rank | R@1 | R@3 | Gold cos | Dist cos | Margin |
|------|----------------|-----|-----|----------|----------|--------|
| cr3_fault_address | 3 | ✗ | ✓ | 0.514 | 0.512 | +0.002 |
| cr0_pg_validation | 1 | ✓ | ✓ | 0.648 | 0.431 | +0.217 |
| cr2_pdbr_role | 1 | ✓ | ✓ | 0.691 | 0.416 | +0.275 |
| compare_pg_pge | 1 | ✓ | ✓ | 0.545 | 0.359 | +0.186 |
| cr0_pg_definition | 1 | ✓ | ✓ | 0.550 | 0.406 | +0.145 |
| nxe_gp_hallucination | 1 | ✓ | ✓ | 0.467 | 0.318 | +0.149 |
| ia32e_transition | 1 | ✓ | ✓ | 0.629 | 0.375 | +0.254 |
| cr0_reset_lookup | 1 | ✓ | ✓ | 0.538 | 0.378 | +0.160 |

## Rankings

### cr3_fault_address
**Query:** Does CR3 store the faulting address during a page fault?
- `paging-overview` — cosine 0.5564
- `pf-generic` — cosine 0.5172
- `cr2-fault` — cosine 0.5141 **GOLD**
- `cr3-pdbr` — cosine 0.4626

### cr0_pg_validation
**Query:** CR0.PG means Page Global Enable. Is this correct?
- `cr4-pge` — cosine 0.8133 **GOLD**
- `paging-overview` — cosine 0.5314
- `cr0-pg` — cosine 0.4830 **GOLD**
- `cr4-pae` — cosine 0.3316

### cr2_pdbr_role
**Query:** Is CR2 the page-directory base register?
- `cr3-pdbr` — cosine 0.6909 **GOLD**
- `cr2-fault` — cosine 0.4561
- `paging-overview` — cosine 0.4255
- `cr0-pg` — cosine 0.3656

### compare_pg_pge
**Query:** Differentiate CR0.PG and CR4.PGE — what does each bit enable?
- `cr4-pge` — cosine 0.5594 **GOLD**
- `cr4-pae` — cosine 0.5341
- `cr0-pg` — cosine 0.5309 **GOLD**
- `paging-overview` — cosine 0.3927
- `gp-generic` — cosine 0.1492

### cr0_pg_definition
**Query:** What is the meaning of CR0.PG?
- `cr0-pg` — cosine 0.5505 **GOLD**
- `cr4-pge` — cosine 0.4616
- `paging-overview` — cosine 0.4278
- `cr4-pae` — cosine 0.3275

### nxe_gp_hallucination
**Query:** Does setting NXE always cause a #GP fault regardless of paging mode?
- `nxe-def` — cosine 0.4670 **GOLD**
- `pf-generic` — cosine 0.3632
- `paging-overview` — cosine 0.3470
- `gp-generic` — cosine 0.2439

### ia32e_transition
**Query:** Explain the sequence required to transition from real-address mode to IA-32e mode.
- `ia32e-procedure` — cosine 0.6289 **GOLD**
- `cr4-pae` — cosine 0.4597
- `real-mode-intro` — cosine 0.4061
- `paging-overview` — cosine 0.3627
- `cr0-reset` — cosine 0.2698

### cr0_reset_lookup
**Query:** What is the default value of CR0 when the processor is reset?
- `cr0-reset` — cosine 0.5376 **GOLD**
- `real-mode-intro` — cosine 0.5369
- `cr0-pg` — cosine 0.3351
- `paging-overview` — cosine 0.2612
