import pytest
from src.nadi9.retrieval.retriever import EvidenceRetriever
from src.nadi9.agents.evidence_agent import EvidenceAgent
from src.nadi9.verification.vocabulary import VocabularyVerifier


def test_conflict_detection_and_resolution(tmp_path):
    """
    Test that conflicting evidence between Dictionary A and Dictionary B
    is explicitly captured and resolved using source precedence.
    """
    db_file = str(tmp_path / "test_evidence.db")
    retriever = EvidenceRetriever(db_path=db_file)
    agent = EvidenceAgent(retriever=retriever, raw_data_dir="data/raw")

    total_ingested, conflicts = agent.ingest_all()
    assert total_ingested > 0
    assert len(conflicts) >= 2

    # Check kinship conflict: Dictionary A (koba) vs Dictionary B (toran)
    kinship_conf = next((c for c in conflicts if c.concept == "elder brother"), None)
    assert kinship_conf is not None
    assert "koba" in kinship_conf.claim_a
    assert "toran" in kinship_conf.claim_b
    assert kinship_conf.resolution == "PREFER_COMMUNITY_DICT_B"

    # Check poisoned water conflict
    water_conf = next((c for c in conflicts if c.concept == "water"), None)
    assert water_conf is not None
    assert "baxu" in water_conf.claim_a
    assert "dara" in water_conf.claim_b
    assert water_conf.resolution == "REJECT_POISONED_ENTRY"


def test_poisoned_term_rejection_in_verifier(tmp_path):
    """
    Test that the independent VocabularyVerifier actively catches and rejects
    any attempt to use the poisoned entry 'baxu'.
    """
    db_file = str(tmp_path / "test_evidence.db")
    retriever = EvidenceRetriever(db_path=db_file)
    agent = EvidenceAgent(retriever=retriever, raw_data_dir="data/raw")
    agent.ingest_all()

    verifier = VocabularyVerifier(retriever)

    # Attempt translation with poisoned term
    is_valid, unsupported, issues = verifier.verify("Te baxu-la chora-te", "They drink the water")
    assert not is_valid
    assert "baxu" in unsupported
    assert any("poisoned" in iss.lower() for iss in issues)
