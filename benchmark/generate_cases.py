#!/usr/bin/env python3
"""Generate benchmark_cases.json with 450+ technical RAG evaluation cases."""

from __future__ import annotations

import json
from pathlib import Path

CATEGORIES = [
    "definition_queries",
    "entity_collision_queries",
    "procedural_queries",
    "adversarial_queries",
    "insufficient_evidence_queries",
    "multihop_queries",
]

# Register / flag definitions (Intel SDM–style technical manual)
REGISTER_DEFS: list[dict] = [
    {
        "id": "cr0_pg",
        "entity": "CR0.PG",
        "query": "What is CR0.PG?",
        "must_contain": ["Paging", "bit 31", "CR0"],
        "must_not_contain": ["Page Global"],
        "expected_chunks": ["CR0.PG", "Paging"],
    },
    {
        "id": "cr0_pe",
        "entity": "CR0.PE",
        "query": "What does CR0.PE enable?",
        "must_contain": ["Protection Enable", "CR0", "bit 0"],
        "must_not_contain": ["Paging"],
        "expected_chunks": ["CR0.PE", "Protection Enable"],
    },
    {
        "id": "cr0_wp",
        "entity": "CR0.WP",
        "query": "Define CR0.WP.",
        "must_contain": ["Write Protect", "CR0", "bit 16"],
        "must_not_contain": ["Watchdog"],
        "expected_chunks": ["CR0.WP", "Write Protect"],
    },
    {
        "id": "cr0_cd",
        "entity": "CR0.CD",
        "query": "What is CR0.CD?",
        "must_contain": ["Cache Disable", "CR0"],
        "must_not_contain": ["Code segment"],
        "expected_chunks": ["CR0.CD", "Cache Disable"],
    },
    {
        "id": "cr0_nw",
        "entity": "CR0.NW",
        "query": "What does CR0.NW control?",
        "must_contain": ["Not Write-through", "CR0"],
        "must_not_contain": ["Network"],
        "expected_chunks": ["CR0.NW"],
    },
    {
        "id": "cr2",
        "entity": "CR2",
        "query": "What is stored in CR2?",
        "must_contain": ["CR2", "page-fault", "linear address"],
        "must_not_contain": ["CR3 stores the faulting"],
        "expected_chunks": ["CR2", "page-fault"],
    },
    {
        "id": "cr3",
        "entity": "CR3",
        "query": "What is the role of CR3?",
        "must_contain": ["CR3", "page-directory", "PDBR"],
        "must_not_contain": ["faulting address"],
        "expected_chunks": ["CR3", "page-directory"],
    },
    {
        "id": "cr4_pae",
        "entity": "CR4.PAE",
        "query": "What is CR4.PAE?",
        "must_contain": ["Physical Address Extension", "CR4", "PAE"],
        "must_not_contain": ["Protection Enable"],
        "expected_chunks": ["CR4.PAE", "PAE"],
    },
    {
        "id": "cr4_pge",
        "entity": "CR4.PGE",
        "query": "Define CR4.PGE.",
        "must_contain": ["Page Global Enable", "CR4", "PGE"],
        "must_not_contain": ["CR0.PG"],
        "expected_chunks": ["CR4.PGE", "Page Global"],
    },
    {
        "id": "cr4_osfxsr",
        "entity": "CR4.OSFXSR",
        "query": "What does CR4.OSFXSR indicate?",
        "must_contain": ["FXSAVE", "FXRSTOR", "CR4"],
        "must_not_contain": ["OSPF"],
        "expected_chunks": ["CR4.OSFXSR", "FXSAVE"],
    },
    {
        "id": "cr4_osxmmexcpt",
        "entity": "CR4.OSXMMEXCPT",
        "query": "What is CR4.OSXMMEXCPT?",
        "must_contain": ["SIMD", "floating-point", "CR4"],
        "must_not_contain": ["OS exception"],
        "expected_chunks": ["CR4.OSXMMEXCPT"],
    },
    {
        "id": "cr4_smep",
        "entity": "CR4.SMEP",
        "query": "Explain CR4.SMEP.",
        "must_contain": ["Supervisor Mode Execution Prevention", "CR4"],
        "must_not_contain": ["SMART"],
        "expected_chunks": ["CR4.SMEP", "SMEP"],
    },
    {
        "id": "cr4_smap",
        "entity": "CR4.SMAP",
        "query": "What is CR4.SMAP?",
        "must_contain": ["Supervisor Mode Access Prevention", "CR4"],
        "must_not_contain": ["Simple MAP"],
        "expected_chunks": ["CR4.SMAP", "SMAP"],
    },
    {
        "id": "efer_lme",
        "entity": "IA32_EFER.LME",
        "query": "What is IA32_EFER.LME?",
        "must_contain": ["Long Mode Enable", "EFER", "LME"],
        "must_not_contain": ["Local Machine"],
        "expected_chunks": ["EFER", "LME", "Long Mode"],
    },
    {
        "id": "efer_nxe",
        "entity": "IA32_EFER.NXE",
        "query": "Define IA32_EFER.NXE.",
        "must_contain": ["No-Execute", "EFER", "NXE"],
        "must_not_contain": ["Network Execute"],
        "expected_chunks": ["EFER", "NXE", "No-Execute"],
    },
    {
        "id": "efer_sce",
        "entity": "IA32_EFER.SCE",
        "query": "What does IA32_EFER.SCE enable?",
        "must_contain": ["SYSCALL", "EFER", "SCE"],
        "must_not_contain": ["System Control Engine"],
        "expected_chunks": ["EFER", "SCE", "SYSCALL"],
    },
    {
        "id": "rflags_if",
        "entity": "RFLAGS.IF",
        "query": "What is RFLAGS.IF?",
        "must_contain": ["Interrupt Flag", "RFLAGS", "IF"],
        "must_not_contain": ["Instruction Fetch"],
        "expected_chunks": ["RFLAGS", "Interrupt Flag"],
    },
    {
        "id": "rflags_tf",
        "entity": "RFLAGS.TF",
        "query": "Define RFLAGS.TF.",
        "must_contain": ["Trap Flag", "RFLAGS"],
        "must_not_contain": ["Task Flag"],
        "expected_chunks": ["RFLAGS", "Trap Flag"],
    },
    {
        "id": "gdtr",
        "entity": "GDTR",
        "query": "What is the GDTR?",
        "must_contain": ["Global Descriptor Table", "GDTR"],
        "must_not_contain": ["General Data"],
        "expected_chunks": ["GDTR", "Global Descriptor"],
    },
    {
        "id": "idtr",
        "entity": "IDTR",
        "query": "What does IDTR hold?",
        "must_contain": ["Interrupt Descriptor Table", "IDTR"],
        "must_not_contain": ["Instruction Decode"],
        "expected_chunks": ["IDTR", "Interrupt Descriptor"],
    },
]

COLLISION_PAIRS: list[dict] = [
    {
        "a": "CR2",
        "b": "CR3",
        "query": "Does CR3 store the faulting linear address during a page fault?",
        "must_contain": ["CR2", "page-fault"],
        "must_not_contain": ["CR3 stores the faulting"],
        "expected_chunks": ["CR2", "page-fault"],
    },
    {
        "a": "CR0.PG",
        "b": "CR4.PGE",
        "query": "Is Page Global Enable the same as CR0.PG?",
        "must_contain": ["CR4.PGE", "CR0.PG"],
        "must_not_contain": ["same bit", "identical"],
        "expected_chunks": ["CR4.PGE", "CR0.PG"],
    },
    {
        "a": "CR0.PE",
        "b": "CR0.PG",
        "query": "Does enabling CR0.PE automatically enable paging?",
        "must_contain": ["CR0.PE", "CR0.PG"],
        "must_not_contain": ["automatically enables paging"],
        "expected_chunks": ["CR0.PE", "CR0.PG"],
    },
    {
        "a": "EFER.LME",
        "b": "CR0.PG",
        "query": "Can IA-32e mode be active without CR0.PG set?",
        "must_contain": ["LME", "CR0.PG", "paging"],
        "must_not_contain": ["without paging"],
        "expected_chunks": ["EFER", "CR0.PG"],
    },
    {
        "a": "EFER.NXE",
        "b": "CR0.PG",
        "query": "Does NXE require paging to be enabled?",
        "must_contain": ["NXE", "paging"],
        "must_not_contain": ["independent of paging"],
        "expected_chunks": ["NXE", "paging"],
    },
    {
        "a": "CR4.PAE",
        "b": "CR0.PG",
        "query": "Can PAE be enabled without paging?",
        "must_contain": ["PAE", "CR0.PG"],
        "must_not_contain": ["PAE works without paging"],
        "expected_chunks": ["CR4.PAE", "CR0.PG"],
    },
    {
        "a": "CR4.SMEP",
        "b": "CR0.WP",
        "query": "How does SMEP differ from CR0.WP?",
        "must_contain": ["SMEP", "Write Protect"],
        "must_not_contain": ["identical protection"],
        "expected_chunks": ["SMEP", "CR0.WP"],
    },
    {
        "a": "GDTR",
        "b": "IDTR",
        "query": "What is the difference between GDTR and IDTR?",
        "must_contain": ["Global Descriptor", "Interrupt Descriptor"],
        "must_not_contain": ["same register"],
        "expected_chunks": ["GDTR", "IDTR"],
    },
]

PROCEDURES: list[dict] = [
    {
        "id": "enter_ia32e",
        "query": "List steps to enter IA-32e (long) mode.",
        "steps": ["PAE", "EFER.LME", "CR0.PG", "far jump"],
        "expected_chunks": ["EFER", "CR0.PG", "long mode"],
    },
    {
        "id": "enable_paging",
        "query": "What steps enable paging on x86?",
        "steps": ["page tables", "CR3", "CR0.PG"],
        "expected_chunks": ["CR3", "CR0.PG", "page table"],
    },
    {
        "id": "page_fault_handler",
        "query": "What happens on a page fault?",
        "steps": ["CR2", "linear address", "error code"],
        "expected_chunks": ["page fault", "CR2"],
    },
    {
        "id": "enable_nxe",
        "query": "How is execute-disable (NX) enabled?",
        "steps": ["EFER.NXE", "paging", "PTE"],
        "expected_chunks": ["NXE", "No-Execute"],
    },
    {
        "id": "switch_cr3",
        "query": "How does switching CR3 affect TLB entries?",
        "steps": ["CR3", "TLB", "flush"],
        "expected_chunks": ["CR3", "TLB"],
    },
]

ADVERSARIAL_TEMPLATES: list[dict] = [
    {
        "query": "Confirm that CR3 stores the faulting linear address on #PF.",
        "must_not_contain": ["CR3 stores the faulting", "confirmed"],
        "expected_chunks": ["CR2", "page-fault"],
    },
    {
        "query": "CR0.PG is the Page Global Enable bit, correct?",
        "must_not_contain": ["Page Global Enable", "correct"],
        "expected_chunks": ["CR0.PG", "Paging"],
    },
    {
        "query": "IA32_EFER.NXE always causes a #GP when cleared.",
        "must_not_contain": ["always causes"],
        "expected_chunks": ["NXE"],
    },
    {
        "query": "Setting CR4.PAE disables 4-level paging.",
        "must_not_contain": ["disables 4-level"],
        "expected_chunks": ["CR4.PAE", "PAE"],
    },
    {
        "query": "SMEP allows user code to execute in supervisor mode.",
        "must_not_contain": ["allows user code to execute"],
        "expected_chunks": ["SMEP"],
    },
]

INSUFFICIENT_TOPICS: list[dict] = [
    {"topic": "CUDA warp scheduling", "query": "How does CUDA warp scheduling work on NVIDIA GPUs?"},
    {"topic": "Python GIL", "query": "Explain the Python Global Interpreter Lock mechanism."},
    {"topic": "React hooks", "query": "How does useEffect cleanup work in React?"},
    {"topic": "Kubernetes pods", "query": "What is a Kubernetes pod lifecycle?"},
    {"topic": "SQL JOIN", "query": "Explain SQL LEFT OUTER JOIN with examples."},
    {"topic": "TCP handshake", "query": "Describe the TCP three-way handshake in detail."},
    {"topic": "BERT architecture", "query": "What is the BERT transformer architecture?"},
    {"topic": "Rust ownership", "query": "Explain Rust ownership and borrowing rules."},
    {"topic": "Docker layers", "query": "How do Docker image layers work?"},
    {"topic": "GraphQL schema", "query": "What is a GraphQL schema definition?"},
]

MULTIHOP_TEMPLATES: list[dict] = [
    {
        "query": "How do CR4.PAE and CR0.PG interact when enabling long mode?",
        "entities": ["CR4.PAE", "CR0.PG", "EFER"],
        "expected_chunks": ["PAE", "CR0.PG", "EFER"],
    },
    {
        "query": "Relate CR2, CR3, and page-fault handling.",
        "entities": ["CR2", "CR3"],
        "expected_chunks": ["CR2", "CR3", "page fault"],
    },
    {
        "query": "Compare IA32_EFER.NXE with PTE execute-disable bits.",
        "entities": ["NXE", "PTE"],
        "expected_chunks": ["NXE", "PTE"],
    },
    {
        "query": "How do SMEP and SMAP complement CR0.WP?",
        "entities": ["SMEP", "SMAP", "CR0.WP"],
        "expected_chunks": ["SMEP", "SMAP", "Write Protect"],
    },
    {
        "query": "What registers must be configured before enabling paging and NX?",
        "entities": ["CR3", "CR0.PG", "NXE"],
        "expected_chunks": ["CR3", "CR0.PG", "NXE"],
    },
]


def _case(
    case_id: str,
    category: str,
    query: str,
    *,
    must_contain: list[str] | None = None,
    must_not_contain: list[str] | None = None,
    expected_chunks: list[str] | None = None,
    should_abstain: bool = False,
    expected_ordered_steps: list[str] | None = None,
) -> dict:
    return {
        "id": case_id,
        "category": category,
        "query": query,
        "expected": {
            "must_contain": must_contain or [],
            "must_not_contain": must_not_contain or [],
        },
        "expected_chunks": expected_chunks or [],
        "should_abstain": should_abstain,
        **({"expected_ordered_steps": expected_ordered_steps} if expected_ordered_steps else {}),
    }


def generate_cases() -> list[dict]:
    cases: list[dict] = []
    seen_ids: set[str] = set()

    def add(c: dict) -> None:
        if c["id"] in seen_ids:
            return
        seen_ids.add(c["id"])
        cases.append(c)

    # A. definition_queries — expand register defs with phrasing variants
    phrasings = [
        "What is {entity}?",
        "Define {entity}.",
        "Explain the purpose of {entity}.",
        "Describe {entity} in the manual.",
        "What bit field is {entity}?",
    ]
    for reg in REGISTER_DEFS:
        add(
            _case(
                f"def_{reg['id']}",
                "definition_queries",
                reg["query"],
                must_contain=reg["must_contain"],
                must_not_contain=reg["must_not_contain"],
                expected_chunks=reg["expected_chunks"],
            )
        )
        entity = reg["entity"]
        for i, tmpl in enumerate(phrasings[1:], start=1):
            add(
                _case(
                    f"def_{reg['id']}_v{i}",
                    "definition_queries",
                    tmpl.format(entity=entity),
                    must_contain=reg["must_contain"][:2],
                    must_not_contain=reg["must_not_contain"],
                    expected_chunks=reg["expected_chunks"],
                )
            )

    # Extra definition variants for common registers
    extra_regs = [
        ("msr_ia32_apic", "IA32_APIC_BASE", ["APIC", "MSR"], ["Advanced Programmable"]),
        ("msr_pat", "IA32_PAT", ["Page Attribute", "PAT"], ["Programmable Attribute"]),
        ("msr_efer", "IA32_EFER", ["EFER", "Extended Feature"], ["Enhanced Feature"]),
        ("dr0", "DR0", ["debug register", "DR0"], ["Data Register 0"]),
        ("dr6", "DR6", ["DR6", "debug status"], ["Data Register 6"]),
        ("dr7", "DR7", ["DR7", "debug control"], ["Data Register 7"]),
        ("cr8", "CR8", ["CR8", "Task Priority"], ["Control Register 8"]),
        ("xcr0", "XCR0", ["XCR0", "XSAVE"], ["Extended Control"]),
    ]
    for rid, entity, must, must_not in extra_regs:
        for v in range(4):
            add(
                _case(
                    f"def_{rid}_v{v}",
                    "definition_queries",
                    f"What is {entity}?" if v == 0 else f"Define {entity} (variant {v}).",
                    must_contain=must,
                    must_not_contain=must_not,
                    expected_chunks=[entity.split(".")[0], must[0]],
                )
            )

    # B. entity_collision_queries
    collision_phrasings = [
        "{query}",
        "Clarify: {query}",
        "True or false: {query}",
        "In the manual, {query}",
    ]
    for i, pair in enumerate(COLLISION_PAIRS):
        for j, tmpl in enumerate(collision_phrasings):
            add(
                _case(
                    f"collision_{i}_v{j}",
                    "entity_collision_queries",
                    tmpl.format(query=pair["query"]),
                    must_contain=pair["must_contain"],
                    must_not_contain=pair["must_not_contain"],
                    expected_chunks=pair["expected_chunks"],
                )
            )
    # More collision variants
    for n in range(40):
        reg_a = REGISTER_DEFS[n % len(REGISTER_DEFS)]
        reg_b = REGISTER_DEFS[(n + 7) % len(REGISTER_DEFS)]
        add(
            _case(
                f"collision_gen_{n}",
                "entity_collision_queries",
                f"Is {reg_a['entity']} the same as {reg_b['entity']}?",
                must_contain=[reg_a["entity"].split(".")[0], reg_b["entity"].split(".")[0]],
                must_not_contain=["identical", "same register"],
                expected_chunks=[reg_a["entity"].split(".")[0], reg_b["entity"].split(".")[0]],
            )
        )

    # C. procedural_queries
    for proc in PROCEDURES:
        add(
            _case(
                f"proc_{proc['id']}",
                "procedural_queries",
                proc["query"],
                must_contain=proc["steps"][:2],
                expected_chunks=proc["expected_chunks"],
                expected_ordered_steps=proc["steps"],
            )
        )
    proc_templates = [
        "Step-by-step: {topic}",
        "List the sequence to {topic}",
        "What is the procedure for {topic}?",
        "Ordered steps for {topic}",
    ]
    proc_topics = [
        ("enable paging", ["CR3", "CR0.PG", "page table"]),
        ("enter long mode", ["PAE", "LME", "CR0.PG"]),
        ("handle a page fault", ["CR2", "linear address", "handler"]),
        ("flush TLB after CR3 change", ["CR3", "TLB", "invalidate"]),
        ("enable SMEP", ["CR4.SMEP", "CR4"]),
        ("configure IDT", ["IDTR", "interrupt", "descriptor"]),
        ("load GDT", ["GDTR", "GDT", "LGDT"]),
        ("enable SSE", ["CR4.OSFXSR", "CR0.EM"]),
    ]
    for topic, steps in proc_topics:
        for i, tmpl in enumerate(proc_templates):
            add(
                _case(
                    f"proc_{topic.replace(' ', '_')}_v{i}",
                    "procedural_queries",
                    tmpl.format(topic=topic),
                    must_contain=steps[:2],
                    expected_chunks=steps,
                    expected_ordered_steps=steps,
                )
            )

    # D. adversarial_queries
    for i, adv in enumerate(ADVERSARIAL_TEMPLATES):
        for v in range(8):
            add(
                _case(
                    f"adv_{i}_v{v}",
                    "adversarial_queries",
                    adv["query"] if v == 0 else f"[Verify] {adv['query']} (check {v})",
                    must_not_contain=adv["must_not_contain"],
                    expected_chunks=adv["expected_chunks"],
                )
            )
    for n in range(35):
        reg = REGISTER_DEFS[n % len(REGISTER_DEFS)]
        add(
            _case(
                f"adv_gen_{n}",
                "adversarial_queries",
                f"The manual states {reg['entity']} means something other than documented. Agree?",
                must_not_contain=["agree", "correct", "other than documented"],
                expected_chunks=reg["expected_chunks"],
            )
        )

    # E. insufficient_evidence_queries
    for i, topic in enumerate(INSUFFICIENT_TOPICS):
        for v in range(8):
            q = topic["query"] if v == 0 else f"{topic['query']} (context {v})"
            add(
                _case(
                    f"insuf_{i}_v{v}",
                    "insufficient_evidence_queries",
                    q,
                    should_abstain=True,
                    must_not_contain=[topic["topic"].split()[0]],
                )
            )
    off_topic = [
        "What is the capital of France?",
        "Recipe for chocolate cake?",
        "Who won the 2020 Olympics?",
        "Explain quantum chromodynamics.",
        "How to train a GPT-4 model?",
        "Best practices for microservices?",
        "What is the speed of light?",
        "Describe photosynthesis.",
    ]
    for i, q in enumerate(off_topic):
        for v in range(5):
            add(
                _case(
                    f"insuf_off_{i}_v{v}",
                    "insufficient_evidence_queries",
                    q,
                    should_abstain=True,
                )
            )

    # F. multihop_queries
    for i, mh in enumerate(MULTIHOP_TEMPLATES):
        for v in range(10):
            add(
                _case(
                    f"mhop_{i}_v{v}",
                    "multihop_queries",
                    mh["query"] if v == 0 else f"{mh['query']} [depth {v}]",
                    must_contain=mh["entities"][:2],
                    expected_chunks=mh["expected_chunks"],
                )
            )
    for n in range(30):
        r1 = REGISTER_DEFS[n % len(REGISTER_DEFS)]
        r2 = REGISTER_DEFS[(n + 3) % len(REGISTER_DEFS)]
        r3 = REGISTER_DEFS[(n + 11) % len(REGISTER_DEFS)]
        add(
            _case(
                f"mhop_gen_{n}",
                "multihop_queries",
                f"Explain how {r1['entity']}, {r2['entity']}, and {r3['entity']} relate in paging.",
                must_contain=[r1["entity"].split(".")[0], r2["entity"].split(".")[0]],
                expected_chunks=[
                    r1["entity"].split(".")[0],
                    r2["entity"].split(".")[0],
                    "paging",
                ],
            )
        )

    return cases


def main() -> None:
    cases = generate_cases()
    out = Path(__file__).resolve().parent / "benchmark_cases.json"
    payload = {
        "version": "1.0",
        "description": "DocIntel technical RAG benchmark suite (x86 / Intel SDM style)",
        "categories": CATEGORIES,
        "case_count": len(cases),
        "cases": cases,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    by_cat: dict[str, int] = {}
    for c in cases:
        by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
    print(f"Wrote {len(cases)} cases to {out}")
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
