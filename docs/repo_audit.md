# Repository Audit — Release Candidate

Audit date: 2026-05-31 · Branch: release-candidate mode

---

## Summary

The codebase is **functional and benchmark-validated** for RC. No blocking dead code paths in the main RAG pipeline. Cleanup opportunities are **documentation consolidation** and **verification code deduplication** — not architectural changes.

---

## Dead code / duplication

| Item | Location | Severity | Recommendation |
|------|----------|----------|----------------|
| Duplicate verification parse/enrich | `app/services/rag.py` (`_parse_verification`, `_enrich_verification_metrics`) vs `answer_verification.py` | Low | Remove from `rag.py`; use `AnswerVerificationService` only |
| Legacy `VERIFY_SYSTEM_PROMPT` alias | `app/services/rag.py` | Low | Remove comment block; single source in `answer_verification.py` |
| Thin benchmark wrapper | `app/services/benchmark.py` | Info | Not dead — API facade over `BenchmarkFramework`; keep |
| `is_abstention` imported unused | `benchmark/definition_failure_analysis.py` | Low | Remove unused import |

---

## Unused / disabled features

| Feature | Status | Notes |
|---------|--------|-------|
| LLM query rewrite | `ENABLE_QUERY_REWRITE_LM=false` | Rule-based expansion active; LLM path exists but off by default |
| Answer rewrite | Enabled | Only triggers when verification finds unsupported claims |
| Procedural LLM fallback | Active | Used when template extraction fails |

No experimental agent architectures or unused retrieval modes in RC scope.

---

## Benchmark scripts

| Script | Status |
|--------|--------|
| `benchmark_runner.py` | **Primary CLI** — use this |
| `benchmark/generate_report.py` | **RC** — generates `benchmark/reports/benchmark_report.md` |
| `benchmark/definition_failure_analysis.py` | **RC** — definition failure report |
| `benchmark/citation_audit.py` | **RC** — citation audit report |
| `benchmark/generate_cases.py` | **Maintainer** — regenerates `benchmark_cases.json`; not run in CI |
| `benchmark/visualize.py` | Used by framework + `generate_report.py` |

**Not obsolete:** All benchmark modules serve RC reporting or case generation.

---

## TODOs / FIXMEs

Ripgrep scan: **no `TODO` / `FIXME` comments** in Python/TS source.

---

## Missing persistence (non-blocking)

| Field | Issue | Impact |
|-------|-------|--------|
| `merged_retrieved_chunks` | Computed at eval time but not stored in JSON results | Definition analysis uses selected chunks only; reranking failures may be under-counted |

**RC action:** Document limitation in definition failure report (done).

---

## Test coverage

| Suite | Path | Status |
|-------|------|--------|
| NDCG + citation + definition funnel | `tests/test_metrics.py` | 10 tests passing |
| Integration / E2E | — | Manual via `benchmark_runner.py` |

---

## Dependencies

- `pytest` listed in `requirements.txt` but optional for RC; `unittest` works out of the box.
- Chroma telemetry errors in logs are benign (library version mismatch).

---

## Recommended pre-release checklist

- [x] Run full 516 benchmark (`sprint3_full_516`)
- [x] Generate RC reports (`generate_report.py`, failure analysis, citation audit)
- [x] README + architecture + release notes
- [ ] Add UI screenshots to README (placeholder present)
- [ ] Remove duplicate verification helpers from `rag.py` (optional polish)
- [ ] Tag release after final review

---

## Files added in RC documentation pass

```
benchmark/definition_failure_analysis.py
benchmark/citation_audit.py
benchmark/generate_report.py
benchmark/reports/benchmark_report.md
benchmark/reports/definition_failures.md
benchmark/reports/citation_audit.md
benchmark/reports/plots/
docs/architecture.md
docs/resume_bullets.md
docs/linkedin_post.md
docs/repo_audit.md
RELEASE_NOTES.md
README.md (overhauled)
```
