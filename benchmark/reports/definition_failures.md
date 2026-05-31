# Definition Failure Analysis

**Source:** `benchmark/results/sprint3_full_516/benchmark_results.json`  
**Cases analyzed:** 132 definition queries  
**Passed (`definition_correct`):** 34 (25.8%)  
**Failed:** 98 (74.2%)

## Executive finding

The headline **definition_accuracy (34.5%)** understates answer quality. **must_contain_score** for the same category is **61.9%**, and **definition_used_rate** is **67.4%**. Many failures are **evaluator strictness** (partial phrasing, synonym mismatch) rather than missing retrieval.

## Funnel summary (definition_queries)

| Stage | Rate |
|-------|------|
| Authoritative retrieved | 43.2% |
| Authoritative selected (top-k) | 72.7% |
| Definition used in answer | 67.4% |
| Definition correct (strict) | 25.8% |
| Legacy must_contain score | 61.9% |

## Failure classification

| Reason | Count | Share of failures |
|--------|------:|------------------:|
| grounding failure | 66 | 67.3% |
| retrieval failure | 29 | 29.6% |
| prompt failure | 3 | 3.1% |

## Interpretation by class

- **retrieval failure** — authoritative definition not in retrieved context; expected chunk patterns missed.
- **reranking failure** — definition found in pool but not promoted to top-k.
- **prompt failure** — authoritative chunk selected but answer omits key terms.
- **evaluator failure** — answer largely correct; strict `must_contain` / funnel logic marks it wrong.
- **grounding failure** — abstention, must_not violation, or hallucination flag.

## Failed cases (sample)

### `def_cr0_pg_v2` — grounding failure

- **Query:** Explain the purpose of CR0.PG.
- **Expected:** Must contain: Paging, bit 31 | Must NOT contain: Page Global
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** The purpose of CR0.PG is to enable paging when set; disables paging when clear. When paging is disabled, all linear addresses are treated as physical addresses.

[Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216]

### `def_cr0_pg_v4` — prompt failure

- **Query:** What bit field is CR0.PG?
- **Expected:** Must contain: Paging, bit 31 | Must NOT contain: Page Global
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** - CR0.PG corresponds to bit 31 of CR0. [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216]

### `def_cr0_pe` — grounding failure

- **Query:** What does CR0.PE enable?
- **Expected:** Must contain: Protection Enable, CR0, bit 0 | Must NOT contain: Paging
- **Must-contain score:** 1.0
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** Step 1: Execute a MOV CR0 instruction that sets the PE flag (and optionally the PG flag) in control register CR0. [Source 3]

Step 2: Execute the STI instruction to enable maskable hardware interrupts and perform the necessary hardware [Source 5]

Step 3: If paging is enabled, the code for the MOV CR0 instruction and the JMP or CALL instruction must come from a page that is identity mapped (that is, the linear address before the jump is the same as the physical address [Source 3]

Step 4: The PG flag has no effect if the PE flag (bit 0 of register CR0) is not also set; [Source 1]

Step 5: See 

### `def_cr0_pe_v1` — grounding failure

- **Query:** Define CR0.PE.
- **Expected:** Must contain: Protection Enable, CR0 | Must NOT contain: Paging
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.PE enables protected mode when set; enables real-address mode when clear. This flag does not enable paging directly. It only enables segment-level protection. To enable paging, both the PE and PG flags must be set.

[Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216]

### `def_cr0_pe_v2` — grounding failure

- **Query:** Explain the purpose of CR0.PE.
- **Expected:** Must contain: Protection Enable, CR0 | Must NOT contain: Paging
- **Must-contain score:** 1.0
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** The Protection Enable (PE) flag in control register CR0 enables protected mode when set; it enables real-address mode when clear.

- [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216] states: "CR0.PE — Protection Enable (bit 0 of CR0) — Enables protected mode when set; enables real-address mode when clear. This flag does not enable paging directly. It only enables segment-level protection."

This explanation is consistent across the provided sources, confirming that setting CR0.PE to 1 enables protected mode, while clearing it allows operation in real-address mode.

### `def_cr0_pe_v3` — grounding failure

- **Query:** Describe CR0.PE in the manual.
- **Expected:** Must contain: Protection Enable, CR0 | Must NOT contain: Paging
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** The PE flag in CR0 (bit 0) enables protected mode when set. When clear, it disables paging and treats all linear addresses as physical addresses.

- "PE (Protected Mode Enable) — Enables protected mode when set; disables paging when clear." [Source 1]

This description is consistent across the provided sources without any conflicting information.

### `def_cr0_pe_v4` — grounding failure

- **Query:** What bit field is CR0.PE?
- **Expected:** Must contain: Protection Enable, CR0 | Must NOT contain: Paging
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.PE corresponds to bit 0 of register CR0. [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216]

### `def_cr0_wp_v2` — retrieval failure

- **Query:** Explain the purpose of CR0.WP.
- **Expected:** Must contain: Write Protect, CR0 | Must NOT contain: Watchdog
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.WP allows pages to be protected from supervisor-mode writes. If CR0.WP = 0, supervisor-mode write accesses are allowed to linear addresses with read-only access rights; if CR0.WP = 1, such accesses are not permitted.

[Source N] Citation: [Source 4 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4905 | Page 3259 | vector=0.592 | rerank=0.168]

### `def_cr0_wp_v3` — retrieval failure

- **Query:** Describe CR0.WP in the manual.
- **Expected:** Must contain: Write Protect, CR0 | Must NOT contain: Watchdog
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.WP allows pages to be protected from supervisor-mode writes. If CR0.WP = 0, supervisor-mode write accesses are allowed to linear addresses with read-only access rights; if CR0.WP = 1, they are not. (User-mode write accesses are never allowed to linear addresses with read-only access rights, regardless of the value of CR0.WP.) [Source 5 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4905 | Page 3259 | vector=0.558 | rerank=0.217]

### `def_cr0_wp_v4` — retrieval failure

- **Query:** What bit field is CR0.WP?
- **Expected:** Must contain: Write Protect, CR0 | Must NOT contain: Watchdog
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** - CR0.WP corresponds to bit 16 of CR0. [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216 | vector=0.000 | rerank=1.000]

### `def_cr0_cd_v2` — grounding failure

- **Query:** Explain the purpose of CR0.CD.
- **Expected:** Must contain: Cache Disable, CR0 | Must NOT contain: Code segment
- **Must-contain score:** 1.0
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.CD, Cache Disable (bit 30 of CR0), controls caching of memory locations for the whole of physical memory in the processor’s internal (and external) caches when both the CD and NW flags are clear. When the CD flag is set, caching is restricted as described in Table 14-5. To prevent the processor from accessing and updating its caches, the CD flag must be set and the caches must be invalidated so that no cache hits can occur [Source 1].

Insufficient retrieved evidence to provide exact states or detailed interactions with other flags beyond what was stated.

### `def_cr0_cd_v4` — prompt failure

- **Query:** What bit field is CR0.CD?
- **Expected:** Must contain: Cache Disable, CR0 | Must NOT contain: Code segment
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.CD is bit 30 of control register CR0. [Source 1]

### `def_cr0_nw_v4` — grounding failure

- **Query:** What bit field is CR0.NW?
- **Expected:** Must contain: Not Write-through, CR0 | Must NOT contain: Network
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Selected excerpt:** 2-16 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW The flags in control registers are: CR0.PG Paging (bit 31 of CR0) — Enables paging when set; disables paging when clear. When paging is  disabled, all linear addresses are treated as physical addresses. The PG flag has no effect if the PE flag (bit  0 of register CR0) is not also set; setting the PG flag when the PE flag is clear causes a general-protection  exception (#GP). See also: Chapter 5, “Paging.” On Intel 64 processors, enabling and disabling IA
- **Generated answer:** CR0.NW corresponds to bit 29 of control register CR0. [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4827 | Page 3216]

### `def_cr2` — grounding failure

- **Query:** What is stored in CR2?
- **Expected:** Must contain: CR2, page-fault, linear address | Must NOT contain: CR3 stores the faulting
- **Must-contain score:** 0.6666666666666666
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Selected excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Generated answer:** According to the sources, CR2 contains different information depending on the context:

- In the case of a page fault, the linear address that caused the page fault is stored in CR2 [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_7037 | Page 4468 | vector=0.000 | rerank=1.000].

- Additionally, CR2 can be loaded with a non-canonical address using the MOV to CR instruction [Source 4 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4894 | Page 3252 | vector=0.000 | rerank=0.054].

Insufficient retrieved evidence to state definitively what CR2 always contains without context.

### `def_cr2_v1` — retrieval failure

- **Query:** Define CR2.
- **Expected:** Must contain: CR2, page-fault | Must NOT contain: CR3 stores the faulting
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Selected excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Generated answer:** CR2 control register describes the linear address causing a page fault [Source 5 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4892 | Page 3251].

### `def_cr2_v2` — grounding failure

- **Query:** Explain the purpose of CR2.
- **Expected:** Must contain: CR2, page-fault | Must NOT contain: CR3 stores the faulting
- **Must-contain score:** 1.0
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Selected excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Generated answer:** CR2 contains the page-fault linear address (the linear address that caused a page fault). [Source 1] Specifically, if linear-address masking had been in effect, the address recorded reflects the result of that masking and does not contain any masked metadata. If the page-fault exception occurred during execution of an instruction in enclave mode, bits 11:0 of the address are cleared. The page-fault handler can use this address to locate the corresponding paging-structure entries. [Source 5]

Insufficient retrieved evidence for additional details on CR2's purpose beyond its role in handling and

### `def_cr2_v4` — grounding failure

- **Query:** What bit field is CR2?
- **Expected:** Must contain: CR2, page-fault | Must NOT contain: CR3 stores the faulting
- **Must-contain score:** 0.0
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Selected excerpt:** 36-68 Vol. 3C INTEL® PROCESSOR TRACE 36.5  TRACING IN VMX OPERATION On processors that IA32_VMX_MISC[bit 14] reports 1, TraceEn can be set in VMX operation. The VMM can  configure specific VMX controls to control what virtualization-specific data is included within the trace packets (see  Section 36.5.1 for details). The VMM can also configure the VMCS to limit tracing to non-root operation, or to trace  across both root and non-root operation. The VMCS controls exist to simplify virtualization 
- **Generated answer:** Insufficient retrieved evidence.

### `def_cr3_v1` — grounding failure

- **Query:** Define CR3.
- **Expected:** Must contain: CR3, page-directory | Must NOT contain: faulting address
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Selected excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Generated answer:** CR3 is a system register used for 32-bit paging and 5-level paging. It contains the base physical address of the first paging structure, which can be either a page directory (for 32-bit paging) or a PML5 table (for 5-level paging).

- For **32-bit paging**, CR3 points to the page directory.
- For **5-level paging**, CR3 points to the PML5 table.

[Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4831 | Page 3218 | vector=0.000 | rerank=1.000]

### `def_cr3_v4` — grounding failure

- **Query:** What bit field is CR3?
- **Expected:** Must contain: CR3, page-directory | Must NOT contain: faulting address
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Selected excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Generated answer:** CR3 has 64 bits on processors supporting the Intel-64 architecture. These bits are ignored with 32-bit paging.

- [Source 3](https://www.intel.com/content/dam/develop/external/us/en/documents/vol3a.pdf)

### `def_cr4_pae` — grounding failure

- **Query:** What is CR4.PAE?
- **Expected:** Must contain: Physical Address Extension, CR4, PAE | Must NOT contain: Protection Enable
- **Must-contain score:** 0.6666666666666666
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Selected excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Generated answer:** CR4.PAE is a flag in control register CR4 that enables paging to produce physical addresses with more than 32 bits when set. When clear, it restricts physical addresses to 32 bits. PAE must be set before entering IA-32e mode.

[Source 1] [Source 2] [Source 4]

### `def_cr4_pae_v1` — grounding failure

- **Query:** Define CR4.PAE.
- **Expected:** Must contain: Physical Address Extension, CR4 | Must NOT contain: Protection Enable
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Selected excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Generated answer:** CR4.PAE enables paging mechanism to reference extended physical addresses when set; restricts physical addresses to 32 bits when clear (see also: Section 25.22.1.1, “Physical Memory Addressing Extension”).

- [Source 4 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_6423 | Page 4130 | vector=0.401 | rerank=0.708]
- [Source 3 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_6425 | Page 4131 | vector=0.000 | rerank=0.734]
- [Source 1 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4837 | Page 3221 | vector=0.554 | rerank=0.804]

### `def_cr4_pae_v4` — prompt failure

- **Query:** What bit field is CR4.PAE?
- **Expected:** Must contain: Physical Address Extension, CR4 | Must NOT contain: Protection Enable
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Selected excerpt:** 2-18 Vol. 3A SYSTEM ARCHITECTURE OVERVIEW Table 16-1). If an IA-32 or Intel 64 processor incorporates the SSE/SSE2/SSE3/SSSE3/SSE4 extensions,  the EM flag must be set to 0 to enable execution of these extensions. SSE/SSE2/SSE3/SSSE3/SSE4  instructions not affected by the EM flag include: PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI,  CLFLUSH, CRC32, and POPCNT. CR0.MP Monitor Coprocessor (bit 1 of CR0) — Controls the interaction of the WAIT (or FWAIT) instruction with  the TS flag (bit 3 of
- **Generated answer:** CR4.PAE is bit 5 of CR4. [Source 1] [Source 4]

### `def_cr4_pge_v2` — grounding failure

- **Query:** Explain the purpose of CR4.PGE.
- **Expected:** Must contain: Page Global Enable, CR4 | Must NOT contain: CR0.PG
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Selected excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Generated answer:** CR4.PGE enables global pages. If CR4.PGE = 0, no translations are shared across address spaces; if CR4.PGE = 1, specified translations may be shared across address spaces.

- [Source 5 | id=2d2e04e8-44bb-4f38-bbe7-6095909541de_chunk_4905 | Page 3259 | vector=0.497 | rerank=0.515]

### `def_cr4_pge_v3` — grounding failure

- **Query:** Describe CR4.PGE in the manual.
- **Expected:** Must contain: Page Global Enable, CR4 | Must NOT contain: CR0.PG
- **Must-contain score:** 1.0
- **Funnel:** retrieved=True → selected=True → used=True
- **Authoritative excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Selected excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Generated answer:** CR4.PGE enables global pages. If CR4.PGE = 0, no translations are shared across address spaces; if CR4.PGE = 1, specified translations may be shared across address spaces.

- [Source 1](#source1): "The global page feature allows frequently used or shared pages to be marked as global to all users (done with the global flag, bit 8, in a page-directory-pointer-table entry, a page-directory entry, or a page-table entry). Global pages are not flushed from the translation-lookaside buffer (TLB) on a task switch or a write to register CR3."
- [Source 2](#source2): "The new PGE (page global enable) fl

### `def_cr4_pge_v4` — retrieval failure

- **Query:** What bit field is CR4.PGE?
- **Expected:** Must contain: Page Global Enable, CR4 | Must NOT contain: CR0.PG
- **Must-contain score:** 0.5
- **Funnel:** retrieved=True → selected=True → used=False
- **Authoritative excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Selected excerpt:** PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.  If this flag is clear, the FXSAVE and FXRSTOR instructions will save and restore the contents of the x87 FPU  and MMX registers, but they may not save and restore the contents of the XMM and MXCSR registers. Also,  the processor will generate an invalid opcode exception (#UD) if it attempts to execute any  SSE/SSE2/SSE3 instruction, with the exception of PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE,  MOVNTI, CLFLUSH, CRC32, and 
- **Generated answer:** CR4.PGE is bit 7 of CR4. [Source 1] [Source 2] [Source 3] [Source 4] [Source 5]

_… and 73 additional failures._

## Conclusion

- **System failures** (retrieval + reranking + prompt + grounding): 98 cases
- **Metric / evaluator issues:** 0 cases

Recommendation: treat **must_contain_score** and manual review as primary definition quality signals until benchmark labels support synonym-aware matching.
