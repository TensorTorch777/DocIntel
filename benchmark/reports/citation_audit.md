# Citation Coverage Audit

**Source:** `benchmark/results/sprint3_full_516/benchmark_results.json`  
**Cases audited:** 384 (excluding gated)

## Summary

| Metric | Value |
|--------|------:|
| Total factual claims | 1491 |
| Cited claims | 855 |
| Uncited claims | 636 |
| Claim-level coverage | 57.3% |
| Benchmark citation_accuracy | 70.3% |
| Benchmark citation_coverage_per_sentence | 68.4% |

## Why citation accuracy is ~70%

Citation accuracy combines **sentence coverage**, **valid source indices**, and **lexical alignment** with retrieved chunks. The ~70% headline reflects:

1. **Uncited factual sentences** — especially in definition answers without per-sentence `[Source N]` tags.
2. **Low definition_queries coverage** — procedural step templates cite better than free-form definitions.
3. **Alignment penalty** — cited claims with weak token overlap to the referenced chunk reduce the composite score.

## Coverage by category

| Category | Cases | Claims | Cited | Coverage |
|----------|------:|-------:|------:|---------:|
| adversarial_queries | 54 | 160 | 160 | 100.0% |
| definition_queries | 114 | 482 | 59 | 12.2% |
| entity_collision_queries | 60 | 216 | 146 | 67.6% |
| insufficient_evidence_queries | 46 | 5 | 5 | 100.0% |
| multihop_queries | 80 | 398 | 258 | 64.8% |
| procedural_queries | 30 | 230 | 227 | 98.7% |

## Worst coverage cases

### `mhop_gen_29` (multihop_queries) — 0%

Claims: 23 | Cited: 0 | Uncited: 23

- _Uncited:_ CR4.OSFXSR, CR4.SMAP, and CR0.PG are related to the enabling of various features that affect paging behavior on Intel 64 processors.
- _Uncited:_ **CR0.PG (Paging)**
- _Uncited:_ The PG flag in control register CR0 (bit 31) enables or disables paging.

### `def_msr_ia32_apic_v1` (definition_queries) — 0%

Claims: 15 | Cited: 0 | Uncited: 15

- _Uncited:_ IA32_APIC_BASE is a Model Specific Register (MSR) that provides information about the local Advanced Programmable Interrupt Controller (APIC) on Intel processors.
- _Uncited:_ Specifically, variant 1 of this MSR contains:
- _Uncited:_ Bit 11: Enables/disables the APIC globally for the processor.

### `def_cr3_v2` (definition_queries) — 0%

Claims: 14 | Cited: 0 | Uncited: 14

- _Uncited:_ CR3 serves as a control register in x86 processors, specifically for managing paging and virtual memory.
- _Uncited:_ Its primary purposes include:
- _Uncited:_ Locating the page directory:

### `def_dr0_v2` (definition_queries) — 0%

Claims: 13 | Cited: 0 | Uncited: 13

- _Uncited:_ Based on the provided sources, there is no specific "DR0 (variant 2)" definition given.
- _Uncited:_ However, I can provide information about DR0 from the available context:
- _Uncited:_ The debug registers (DR0-DR7) are described as follows:

### `mhop_3_v2` (multihop_queries) — 0%

Claims: 13 | Cited: 0 | Uncited: 13

- _Uncited:_ SMEP (Supervisor-mode Execution Prevention) and SMAP (Supervisor-mode Access Prevention) complement CR0.WP (Write Protect) in the following ways:
- _Uncited:_ **CR0.WP** controls whether supervisor-level procedures can write into read-only pages.
- _Uncited:_ When set, it inhibits such writes; when clear, it allows them.

### `def_msr_ia32_apic_v2` (definition_queries) — 0%

Claims: 12 | Cited: 0 | Uncited: 12

- _Uncited:_ IA32_APIC_BASE (variant 2) is a Model Specific Register (MSR) that controls the configuration and enablement of the Local Advanced Programmable Interrupt Controller (Local APIC).
- _Uncited:_ Specifically, it allows setting up the base address for accessing the APIC registers in memory-mapped I/O space.
- _Uncited:_ Key aspects of IA32_APIC_BASE (variant 2):

### `def_dr0_v1` (definition_queries) — 0%

Claims: 11 | Cited: 0 | Uncited: 11

- _Uncited:_ Based on the provided sources, there is no specific "DR0 (variant 1)" definition given.
- _Uncited:_ However, I can provide information about DR0 from the available context:
- _Uncited:_ According to Source 2 and Source 3:

### `def_dr0_v3` (definition_queries) — 0%

Claims: 11 | Cited: 0 | Uncited: 11

- _Uncited:_ Based on the information provided in the instruction set summary, DR0 (variant 3) is defined as follows:
- _Uncited:_ DR0 (variant 3): Debug register 0.
- _Uncited:_ This is a 64-bit register used for debugging purposes.

### `def_msr_pat_v3` (definition_queries) — 0%

Claims: 10 | Cited: 0 | Uncited: 10

- _Uncited:_ Based on the information provided, IA32_PAT (variant 3) refers to the encoding for the full version of the Host IA32_PAT field in the VMCS.
- _Uncited:_ Specifically:
- _Uncited:_ IA32_PAT (variant 3) is encoded as:

### `collision_6_v3` (entity_collision_queries) — 0%

Claims: 10 | Cited: 0 | Uncited: 10

- _Uncited:_ SMEP (Supervisor-mode Execution Prevention) and CR0.WP (Write Protect) serve different purposes in controlling access to memory but operate at different levels of privilege.
- _Uncited:_ When set, it inhibits supervisor-level procedures from writing into read-only pages.
- _Uncited:_ This means that if CR0.WP is enabled, supervisor-mode processes cannot write to linear addresses with read-only access rights.

### `def_cr4_osfxsr_v2` (definition_queries) — 0%

Claims: 9 | Cited: 0 | Uncited: 9

- _Uncited:_ CR4.OSFXSR serves two main purposes related to handling SIMD (Single Instruction, Multiple Data) floating-point operations:
- _Uncited:_ It enables support for the FXSAVE and FXRSTOR instructions.
- _Uncited:_ When this bit is set in CR4, it indicates that the operating system provides support for saving and restoring state of SIMD registers using these instructions.

### `def_cr4_osfxsr_v3` (definition_queries) — 0%

Claims: 9 | Cited: 0 | Uncited: 9

- _Uncited:_ According to the manual, CR4.OSFXSR (FXSAVE/FXRSTOR support) is a flag in the CR4 control register that:
- _Uncited:_ Enables FXSAVE and FXRSTOR instructions to save/restore the X87 FPU, XMM, and MXCSR registers.
- _Uncited:_ Indicates that the operating system provides context switch support for SSE/SSE2/SSE3/SSSE3/SSE4.

### `def_cr4_osxmmexcpt_v2` (definition_queries) — 0%

Claims: 9 | Cited: 0 | Uncited: 9

- _Uncited:_ CR4.OSXMMEXCPT is a flag in control register CR4 that controls how the processor handles unmasked SIMD floating-point exceptions.
- _Uncited:_ Specifically:
- _Uncited:_ It allows the operating system to indicate support for unmasked SIMD floating-point exceptions.

### `def_cr4_osfxsr` (definition_queries) — 0%

Claims: 8 | Cited: 0 | Uncited: 8

- _Uncited:_ CR4.OSFXSR indicates that the operating system supports saving and restoring the Pentium III processor state during context switches, as well as enabling the FXSAVE and FXRSTOR instructions to save an
- _Uncited:_ Additionally, it enables the processor to execute SSE/SSE2/SSE3/SSSE3/SSE4 instructions except for PAUSE, PREFETCHh, SFENCE, LFENCE, MFENCE, MOVNTI, CLFLUSH, CRC32, and POPCNT.
- _Uncited:_ When set, this flag indicates to software that the operating system supports the use of the FXSAVE and FXRSTOR instructions.

### `def_cr2_v3` (definition_queries) — 0%

Claims: 7 | Cited: 0 | Uncited: 7

- _Uncited:_ CR2 control register is associated with storing the linear address that generated a page-fault exception.
- _Uncited:_ When a page fault occurs, the processor loads the CR2 register with this linear address.
- _Uncited:_ If linear-address masking had been in effect, the recorded address reflects the result of that masking and does not contain any masked metadata.

## Recommendations

- Enforce **one citation per factual sentence** in QA prompts (already in conservative mode; extend to default QA).
- Post-process answers to flag uncited sentences before returning.
- Weight **citation_coverage_per_sentence** separately from alignment in dashboards for clearer tracking.
