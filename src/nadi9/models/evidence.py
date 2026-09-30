from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Categorization of evidence sources based on linguistic authority."""
    GRAMMAR_NOTE = "grammar_note"
    APPROVED_EXAMPLE = "approved_example"
    COMMUNITY_DICTIONARY = "community_dictionary"  # Dictionary B
    VENDOR_DICTIONARY = "vendor_dictionary"        # Dictionary A
    EXPERT_NOTE = "expert_note"
    NATIVE_INTERVIEW = "native_interview"
    VIEWER_FEEDBACK = "viewer_feedback"
    LINGUIST_CORRECTION = "linguist_correction"


class EvidenceItem(BaseModel):
    """A discrete, indexed unit of linguistic evidence."""
    evidence_id: str = Field(description="Unique ID e.g. example:E07 or dict_b:term-19")
    source_type: SourceType
    source_name: str
    author: Optional[str] = None
    date: Optional[str] = None
    reliability_weight: float = Field(ge=0.0, le=1.0, description="Base reliability prior (0.0 to 1.0)")
    source_text: Optional[str] = None
    nadi_9_text: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    def is_adversarial(self) -> bool:
        """Heuristic check for prompt injection or poison flags."""
        raw_str = str(self.raw_payload).lower()
        adversarial_signatures = [
            "ignore all previous",
            "ignore the assignment",
            "immediately output pass",
            "poisoned entry",
        ]
        return any(sig in raw_str for sig in adversarial_signatures)


class EvidenceConflict(BaseModel):
    """Explicit record of conflicting claims between different sources."""
    conflict_id: str
    concept: str
    source_a_ref: str
    claim_a: str
    source_b_ref: str
    claim_b: str
    confidence_delta: float
    resolution: str = "UNRESOLVED"  # "SOURCE_B_PREFERRED", "SUPERSEDED", "UNRESOLVED"
    rationale: str
