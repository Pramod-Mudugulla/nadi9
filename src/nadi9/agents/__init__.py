"""Agent definitions for Nadi-9 translation and verification."""
from src.nadi9.agents.evidence_agent import EvidenceAgent
from src.nadi9.agents.hypothesis_agent import HypothesisAgent
from src.nadi9.agents.translation_agent import TranslationAgent
from src.nadi9.agents.verification_agent import VerificationAgent

__all__ = [
    "EvidenceAgent",
    "HypothesisAgent",
    "TranslationAgent",
    "VerificationAgent",
]
