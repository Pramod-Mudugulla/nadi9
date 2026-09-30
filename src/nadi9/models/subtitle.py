from typing import List, Optional
from pydantic import BaseModel, Field


class SubtitleItem(BaseModel):
    """Raw subtitle source line from episode transcript."""
    subtitle_id: str
    scene_id: str
    speaker: str
    listener: Optional[str] = None
    time_in: str
    time_out: str
    source_text: str
    notes: Optional[str] = None


class SubtitleDecision(BaseModel):
    """
    Standard decision output for every subtitle line.
    Matches Section 4 specification of the candidate brief.
    """
    subtitle_id: str
    source_text: str
    nadi_9_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    decision: str = Field(description="PASS or HUMAN_REVIEW")
    evidence: List[str] = Field(default_factory=list, description="IDs of backing evidence")
    assumptions: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    review_question: Optional[str] = None

    # Extended operational fields
    confidence_reason: Optional[str] = None
    time_in: Optional[str] = "00:00:00,000"
    time_out: Optional[str] = "00:00:03,000"
    reading_speed_cps: Optional[float] = None
    verification_notes: Optional[str] = None

    def to_brief_dict(self) -> dict:
        """Returns the exact JSON shape required by Section 4."""
        return {
            "subtitle_id": self.subtitle_id,
            "source_text": self.source_text,
            "nadi_9_text": self.nadi_9_text,
            "confidence": self.confidence,
            "decision": self.decision,
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "conflicts": self.conflicts,
            "review_question": self.review_question,
        }
