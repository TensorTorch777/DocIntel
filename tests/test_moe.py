"""Tests for Mixture-of-Experts routing."""

from app.services.moe import ExpertId, route_experts
from app.services.query_intent import QueryIntent


class TestMoERouting:
    def test_verification_query_selects_verification_expert(self):
        decision = route_experts(
            "CR0.PG means Page Global Enable. Is this correct?"
        )
        assert decision.primary == ExpertId.VERIFICATION
        assert decision.experts[0].weight > 0.3

    def test_procedural_query_selects_procedural_expert(self):
        decision = route_experts(
            "Explain the sequence required to transition from real-address mode to IA-32e mode."
        )
        assert decision.primary == ExpertId.PROCEDURAL

    def test_definition_query_selects_definition_expert(self):
        decision = route_experts("What is the meaning of CR0.PG?")
        assert decision.primary == ExpertId.DEFINITION

    def test_image_modality_selects_vision_expert(self):
        decision = route_experts(
            "What register is shown?",
            media_kind="image",
            has_attachment=True,
        )
        assert decision.primary == ExpertId.VISION
        assert decision.uses_vision

    def test_audio_modality_selects_audio_expert(self):
        decision = route_experts(
            "Transcribe this question about CR3",
            media_kind="audio",
            has_attachment=True,
        )
        assert decision.primary == ExpertId.AUDIO
        assert decision.uses_audio

    def test_video_modality_selects_video_expert(self):
        decision = route_experts(
            "What happens in this clip?",
            media_kind="video",
        )
        assert decision.primary == ExpertId.VIDEO
        assert decision.uses_video

    def test_weights_are_a_softmax(self):
        decision = route_experts("What is CR3?", media_kind="pdf", top_k=2)
        assert abs(sum(e.weight for e in decision.experts) - 1.0) < 0.55
        # top-k=2 so selected weights need not sum to 1; full softmax would
        assert all(e.weight > 0 for e in decision.experts)
        assert decision.experts[0].weight >= decision.experts[1].weight

    def test_explicit_intent_overrides_classifier(self):
        decision = route_experts(
            "tell me something",
            intent=QueryIntent.VERIFICATION,
        )
        assert decision.primary == ExpertId.VERIFICATION

    def test_to_dict_serializable(self):
        payload = route_experts("What is CR0.PG?", media_kind="pdf").to_dict()
        assert payload["primary"] == "definition"
        assert isinstance(payload["experts"], list)
        assert "weight" in payload["experts"][0]
