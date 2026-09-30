from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RuleCategory(str, Enum):
    WORD_ORDER = "word_order"
    TENSE = "tense"
    NEGATION = "negation"
    KINSHIP_HONORIFIC = "kinship_honorific"
    CODE_SWITCH = "code_switch"
    VOCABULARY = "vocabulary"


class LanguageHypothesis(BaseModel):
    """
    A testable linguistic claim derived from empirical evidence.
    Tracks supporting evidence references and counterexamples.
    """
    rule_id: str
    category: RuleCategory
    name: str
    pattern_rule: str
    description: str
    supporting_evidence: List[str] = Field(default_factory=list)
    counterexamples: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    status: str = "TESTED"  # "TESTED", "DISPUTED", "SUPERSEDED", "PROVISIONAL"
    rationale: Optional[str] = None

    def calculate_calibrated_confidence(self) -> float:
        """
        Derive calibrated confidence:
        High support boosts score; each counterexample heavily penalizes confidence.
        """
        base = 0.5
        support_boost = min(len(self.supporting_evidence) * 0.1, 0.45)
        penalty = len(self.counterexamples) * 0.25
        return round(max(0.05, min(0.99, base + support_boost - penalty)), 2)
