import pytest
from src.nadi9.graph.workflow import NadiWorkflow
from src.nadi9.providers.mock import MockLLMProvider
from src.nadi9.retrieval.retriever import EvidenceRetriever
from src.nadi9.models.subtitle import SubtitleItem
from src.nadi9.models.state import RunState


def test_unsupported_mechanical_term_abstention(tmp_path):
    """
    Test that when an unseen modern term ('pneumatic gearbox') arrives,
    the agent abstains from hallucinating, keeps confidence low,
    marks decision as HUMAN_REVIEW, and attaches an actionable review question.
    """
    db_file = str(tmp_path / "test_evidence.db")
    retriever = EvidenceRetriever(db_path=db_file)
    provider = MockLLMProvider()
    workflow = NadiWorkflow(provider=provider, retriever=retriever, raw_data_dir="data/raw")

    state = workflow.run_pipeline()

    # Line S008 contains: "The pneumatic gearbox began spinning rapidly."
    s008 = state.subtitle_decisions.get("S008")
    assert s008 is not None
    assert s008.decision == "HUMAN_REVIEW"
    assert s008.confidence <= 0.40
    assert "[INSUFFICIENT_EVIDENCE" in s008.nadi_9_text
    assert s008.review_question is not None
    assert "pneumatic gearbox" in s008.review_question.lower()

    # Must be in the review queue
    review_ids = [q.subtitle_id for q in state.review_queue]
    assert "S008" in review_ids
