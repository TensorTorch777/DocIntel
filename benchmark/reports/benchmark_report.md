# DocIntel Benchmark Report

**Document ID:** `2d2e04e8-44bb-4f38-bbe7-6095909541de`  
**Timestamp:** 20260531_151927  
**Cases:** 516  
**Pipeline:** Full (hybrid + rerank + definition resolver + evidence gate + verification)

## Executive Summary

DocIntel was evaluated on **516** technical RAG cases derived from Intel SDM–style register, procedure, adversarial, and abstention scenarios.

| Metric | Result |
|--------|-------:|
| Recall@K | 95.1% |
| MRR | 0.848 |
| NDCG@K | 94.8% |
| Hallucination rate | 4.5% |
| Citation accuracy | 70.3% |
| Citation coverage / sentence | 68.4% |
| Abstention precision / recall | 38.7% / 95.8% |
| Avg latency | 1854 ms |

### Latency breakdown

- Retrieval: 186 ms
- Rerank: 558 ms
- Generation: 682 ms
- Verification: 424 ms

## Category Breakdown

| Category | Recall@K | Must-contain | Hallucination | Citations |
|----------|---------:|-------------:|--------------:|----------:|
| adversarial_queries | 90.9% | 100.0% | 10.7% | 84.3% |
| definition_queries | 95.6% | 61.9% | 6.8% | 24.2% |
| entity_collision_queries | 95.8% | 40.0% | 0.0% | 72.4% |
| insufficient_evidence_queries | 100.0% | 100.0% | 0.0% | 99.0% |
| multihop_queries | 97.5% | 62.5% | 0.0% | 81.9% |
| procedural_queries | 79.3% | 63.5% | 16.2% | 84.4% |

## Best Performing Categories

- **insufficient_evidence_queries** — composite 99.8% (recall 100.0%, must-contain 100.0%)
- **adversarial_queries** — composite 93.1% (recall 90.9%, must-contain 100.0%)
- **multihop_queries** — composite 80.6% (recall 97.5%, must-contain 62.5%)

## Weakest Categories

- **definition_queries** — composite 67.6% (recall 95.6%, must-contain 61.9%)
- **entity_collision_queries** — composite 69.3% (recall 95.8%, must-contain 40.0%)
- **procedural_queries** — composite 74.4% (recall 79.3%, must-contain 63.5%)

## Recommendations

1. **Definition queries** — improve per-sentence citations; relax evaluator synonyms or expand gold labels (see `definition_failures.md`).
2. **Entity collision** — must-contain score is low; strengthen disambiguation prompts when multiple registers appear.
3. **Procedural queries** — extra_step_rate remains high; continue query-aware step filtering tuning.
4. **Citations** — target >85% sentence coverage (see `citation_audit.md`).
5. **Latency** — verification skip rate ~50%; maintain selective verification for release.

## Plots

![category_accuracy.png](plots/category_accuracy.png)
![hallucination_reduction.png](plots/hallucination_reduction.png)
![pipeline_comparison.png](plots/pipeline_comparison.png)
![latency_breakdown.png](plots/latency_breakdown.png)
![abstention_accuracy.png](plots/abstention_accuracy.png)
![retrieval_recall_at_k.png](plots/retrieval_recall_at_k.png)
![confidence_distribution.png](plots/confidence_distribution.png)
