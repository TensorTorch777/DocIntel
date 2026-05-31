"""Unit tests for benchmark metrics (Sprint 3)."""

from __future__ import annotations

import unittest

from benchmark.metrics import (
    citation_accuracy,
    compute_definition_funnel,
    ndcg_at_k,
)
from app.services.citation_support import citation_coverage_per_sentence


class NdcgTests(unittest.TestCase):
    def test_perfect_ranking_is_one(self) -> None:
        retrieved = [
            "CR0.PG paging bit 31 of CR0",
            "unrelated chunk",
            "another chunk",
        ]
        expected = ["CR0.PG"]
        self.assertAlmostEqual(ndcg_at_k(retrieved, expected, k=3), 1.0)

    def test_never_exceeds_one_with_duplicate_hits(self) -> None:
        """Old bug: same pattern matching multiple ranks inflated DCG > 1."""
        retrieved = [
            "CR0.PG paging bit 31",
            "CR0.PG paging bit 31 duplicate",
            "CR0.PG paging bit 31 again",
        ]
        expected = ["CR0.PG"]
        score = ndcg_at_k(retrieved, expected, k=3)
        self.assertLessEqual(score, 1.0)
        self.assertAlmostEqual(score, 1.0)

    def test_multiple_patterns_first_rank(self) -> None:
        retrieved = [
            "CR0.PG paging bit 31",
            "CR3 page directory base",
            "noise",
        ]
        expected = ["CR0.PG", "CR3"]
        score = ndcg_at_k(retrieved, expected, k=3)
        self.assertAlmostEqual(score, 1.0)

    def test_partial_ranking_below_one(self) -> None:
        retrieved = ["noise", "CR0.PG paging bit 31", "more noise"]
        expected = ["CR0.PG"]
        score = ndcg_at_k(retrieved, expected, k=3)
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.0)

    def test_no_relevant_is_zero(self) -> None:
        retrieved = ["a", "b", "c"]
        expected = ["CR0.PG"]
        self.assertAlmostEqual(ndcg_at_k(retrieved, expected, k=3), 0.0)

    def test_empty_expected_is_one(self) -> None:
        self.assertAlmostEqual(ndcg_at_k(["a"], [], k=3), 1.0)


class CitationTests(unittest.TestCase):
    def test_coverage_per_sentence(self) -> None:
        answer = (
            "CR0.PG enables paging. [Source 1]\n"
            "This sentence has no citation."
        )
        cov = citation_coverage_per_sentence(answer)
        self.assertAlmostEqual(cov, 0.5)

    def test_full_coverage_scores_high(self) -> None:
        answer = "Paging is controlled by CR0.PG (bit 31). [Source 1]"
        score = citation_accuracy(
            answer,
            should_abstain=False,
            has_sources=True,
            num_sources=3,
            retrieved_texts=["CR0.PG paging bit 31 of CR0"],
        )
        self.assertGreaterEqual(score, 0.7)

    def test_abstention_without_citations(self) -> None:
        score = citation_accuracy(
            "Insufficient retrieved evidence.",
            should_abstain=True,
            has_sources=True,
            num_sources=3,
        )
        self.assertAlmostEqual(score, 1.0)


class DefinitionFunnelTests(unittest.TestCase):
    def test_funnel_all_true_when_used(self) -> None:
        auth = "PG — Paging (bit 31 of CR0)"
        result = compute_definition_funnel(
            query="What is CR0.PG?",
            answer="CR0.PG is Paging (bit 31 of CR0). [Source 1]",
            selected_texts=[auth],
            merged_texts=[auth, "other"],
            must_contain=["bit 31"],
            must_not=[],
        )
        self.assertTrue(result["definition_retrieved"])
        self.assertTrue(result["definition_selected"])
        self.assertTrue(result["definition_used"])
        self.assertTrue(result["definition_correct"])


if __name__ == "__main__":
    unittest.main()
