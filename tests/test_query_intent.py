"""Tests for query intent classification and routing."""

import pytest

from app.services.evidence_sufficiency import _required_categories
from app.services.procedural_reasoning import is_procedural_query
from app.services.query_intent import (
    AnswerTemplate,
    PipelineMode,
    QueryIntent,
    classify_query_intent,
)


DEFINITION_VALIDATION = (
    "CR0.PG means Page Global Enable. Is this correct?"
)

PROCEDURAL_SEQUENCE = (
    "Explain the sequence required to transition from real-address mode to IA-32e mode."
)

COMPARE_ENTITIES = (
    "Differentiate CR0.PG and CR4.PGE — what does each bit enable?"
)

HALLUCINATION_BAIT = (
    "Does setting NXE always cause a #GP fault regardless of paging mode?"
)

LOOKUP_QUERY = "What is the default value of CR0 when the processor is reset?"

DEFINITION_QUERY = "What is the meaning of CR0.PG?"


class TestQueryIntentClassification:
    def test_definition_validation_not_procedural(self):
        result = classify_query_intent(DEFINITION_VALIDATION)
        assert result.intent == QueryIntent.VERIFICATION
        assert result.answer_template == AnswerTemplate.VERIFICATION
        assert result.pipeline == PipelineMode.VERIFICATION_QA
        assert is_procedural_query(DEFINITION_VALIDATION) is False

    def test_procedural_sequence_intent(self):
        result = classify_query_intent(PROCEDURAL_SEQUENCE)
        assert result.intent == QueryIntent.PROCEDURAL
        assert result.pipeline == PipelineMode.PROCEDURAL_EXTRACTION
        assert is_procedural_query(PROCEDURAL_SEQUENCE) is True

    def test_procedural_evidence_categories_not_definition_only(self):
        required = _required_categories(PROCEDURAL_SEQUENCE)
        assert "procedural" in required
        assert "definition" not in required

    def test_verification_evidence_categories(self):
        required = _required_categories(DEFINITION_VALIDATION)
        assert "behavior" in required or "exceptions" in required
        assert "procedural" not in required

    def test_comparison_intent(self):
        result = classify_query_intent(COMPARE_ENTITIES)
        assert result.intent == QueryIntent.COMPARISON
        assert "definition" in result.evidence_categories

    def test_hallucination_resistance_intent(self):
        result = classify_query_intent(HALLUCINATION_BAIT)
        assert result.intent in (QueryIntent.VERIFICATION, QueryIntent.GENERAL)

    def test_lookup_intent(self):
        result = classify_query_intent(LOOKUP_QUERY)
        assert result.intent == QueryIntent.LOOKUP

    def test_definition_intent(self):
        result = classify_query_intent(DEFINITION_QUERY)
        assert result.intent == QueryIntent.DEFINITION


@pytest.mark.parametrize(
    "query,expected_intent,expected_pipeline,expected_template",
    [
        (
            DEFINITION_VALIDATION,
            QueryIntent.VERIFICATION,
            PipelineMode.VERIFICATION_QA,
            AnswerTemplate.VERIFICATION,
        ),
        (
            PROCEDURAL_SEQUENCE,
            QueryIntent.PROCEDURAL,
            PipelineMode.PROCEDURAL_EXTRACTION,
            AnswerTemplate.PROCEDURAL,
        ),
        (
            COMPARE_ENTITIES,
            QueryIntent.COMPARISON,
            PipelineMode.COMPARISON_QA,
            AnswerTemplate.COMPARISON,
        ),
        (
            HALLUCINATION_BAIT,
            QueryIntent.VERIFICATION,
            PipelineMode.VERIFICATION_QA,
            AnswerTemplate.VERIFICATION,
        ),
    ],
)
def test_routing_matrix(query, expected_intent, expected_pipeline, expected_template):
    result = classify_query_intent(query)
    assert result.intent == expected_intent
    assert result.pipeline == expected_pipeline
    assert result.answer_template == expected_template
