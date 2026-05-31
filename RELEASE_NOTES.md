# Release Notes

DocIntel release-candidate summary across three development sprints.

**Latest benchmark:** `benchmark/results/sprint3_full_516/` · 516 cases · Intel SDM–style manual

---

## Sprint 3 — Evaluation correctness & latency

**Focus:** Fix benchmark metrics, citation auditing, selective verification, definition funnel metrics, release documentation.

### Changes

- **NDCG@K fix** — each expected pattern credited once at first rank; scores capped at 1.0 (previously inflated above 100%)
- **Citation metrics** — sentence coverage, valid source indices, claim-to-chunk alignment
- **Selective verification** — skip low-risk and authoritative-definition answers; LRU cache; lightweight claim-list verify for medium risk
- **Definition funnel** — `definition_retrieved`, `definition_selected`, `definition_used`, `definition_correct`
- **Release reports** — `benchmark/reports/`, analysis scripts, documentation overhaul

### Metrics (516 cases)

| Metric | Sprint 2 filtered | Sprint 3 |
|--------|------------------:|---------:|
| Recall@K | 95.1% | **95.1%** |
| MRR | 0.848 | **0.848** |
| NDCG@K | 141.5% (bug) | **94.8%** |
| Hallucination rate | 13.2% | **4.5%** |
| Citation accuracy | 60.5% | **70.3%** |
| Verification latency | 1930 ms | **424 ms** |
| Total latency | 3424 ms | **1854 ms** |
| Verification skipped | 0% | **50.2%** |

---

## Sprint 2 — Procedural reasoning & step filtering

**Focus:** Ordered procedural answers, query-aware step filtering, procedural benchmark metrics.

### Changes

- Procedural query detection and step extraction from evidence
- Dependency-aware step ordering with `Step N: … [Source N]` template
- Query-aware relevance scoring (intent boost/penalty, top-N filtering)
- Benchmark metrics: `ordered_step_accuracy`, `missing_step_rate`, `extra_step_rate`, `step_precision`, `step_recall`

### Metrics (procedural category, 37 cases)

| Metric | Before | After filtering |
|--------|-------:|----------------:|
| Ordered step accuracy | 59.4% | 51.3% |
| Extra step rate | ~76%+ | 63.5% |
| Avg steps per answer | ~35 | ~8 |

Filtering reduced noise substantially; ordered accuracy trade-off documented in benchmark reports.

---

## Sprint 1 — Evidence sufficiency calibration

**Focus:** Weighted coverage gate, confidence thresholds, definition strictness.

### Changes

- Weighted evidence coverage (definition / behavior / exceptions / interactions)
- Configurable confidence thresholds (`COVERAGE_CONFIDENCE_HIGH`, `COVERAGE_CONFIDENCE_MEDIUM`)
- Evidence gate integrated before LLM generation
- Full 516-case calibrated benchmark baseline

### Metrics (516 cases, calibrated run)

| Metric | Value |
|--------|------:|
| Recall@K | 95.1% |
| Hallucination rate | 13.0% |
| Abstention precision / recall | 49.7% / 61.7% |
| Citation accuracy | 53.3% |
| Total latency | 3749 ms |

---

## Known limitations (RC)

1. **Definition accuracy metric (34.5%)** understates quality — `must_contain_score` is 61.9% for the same category; see [benchmark/reports/definition_failures.md](benchmark/reports/definition_failures.md).
2. **Citation coverage** — definition answers cite poorly (12.2% claim coverage); procedural templates cite well (98.7%).
3. **Entity collision** — must-contain score 40.0%; disambiguation prompts need tuning.
4. **Abstention precision** — 38.7% (high recall 95.8%): system abstains aggressively on insufficient-evidence cases.
5. **Local LLM dependency** — benchmark numbers reflect Ollama `qwen2.5:7b`; results vary by model and hardware.

---

## Upgrade notes

```bash
cp .env.example .env   # New Sprint 3 keys: VERIFICATION_CACHE_SIZE, SKIP_VERIFICATION_AUTHORITATIVE_DEFINITIONS
pip install -r requirements.txt
python -m unittest tests.test_metrics -v
```
