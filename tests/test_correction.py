import pytest
from src.nadi9.graph.workflow import NadiWorkflow
from src.nadi9.providers.mock import MockLLMProvider
from src.nadi9.retrieval.retriever import EvidenceRetriever


def test_selective_replanning_on_linguist_correction(tmp_path):
    """
    Test that when Dr. Sen's correction arrives halfway through:
    1. It updates only affected rules (RULE-KIN-03).
    2. Only impacted subtitle lines (S014) are rerun, not the entire episode.
    3. The updated line passes verification with the new reconciliation honorific 'toran-ya'.
    """
    db_file = str(tmp_path / "test_evidence.db")
    retriever = EvidenceRetriever(db_path=db_file)
    provider = MockLLMProvider()
    workflow = NadiWorkflow(provider=provider, retriever=retriever, raw_data_dir="data/raw")

    # Initial pipeline run
    state = workflow.run_pipeline()

    # Prior to correction, S014 was flagged for HUMAN_REVIEW due to kinship conflict
    pre_corr_s014 = state.subtitle_decisions["S014"]
    assert pre_corr_s014.decision == "HUMAN_REVIEW"
    assert "reconciliation" in (pre_corr_s014.review_question or "").lower()

    # Record which items were touched
    call_count_before = state.budget.model_calls_used

    # Apply correction scenario
    reprocessed = workflow.apply_correction(
        correction_path="data/scenarios/linguist_correction.json",
        state=state,
        episode_path="data/raw/episode_transcript.json",
    )

    # Selective invalidation check: only S014 was rerun!
    assert reprocessed == ["S014"]
    # We did NOT rerun all lines (call count increased by 2: 1 model call for translation, 1 for verification)
    assert state.budget.model_calls_used - call_count_before <= 2

    # Post-correction check
    post_corr_s014 = state.subtitle_decisions["S014"]
    assert post_corr_s014.decision == "PASS"
    assert "toran-ya" in post_corr_s014.nadi_9_text.lower()
    assert post_corr_s014.confidence >= 0.85
    assert "S014" not in [q.subtitle_id for q in state.review_queue]
