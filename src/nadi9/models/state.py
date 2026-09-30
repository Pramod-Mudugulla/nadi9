from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.nadi9.models.evidence import EvidenceItem, EvidenceConflict
from src.nadi9.models.hypothesis import LanguageHypothesis
from src.nadi9.models.subtitle import SubtitleDecision


import os


class BudgetTracker(BaseModel):
    """Enforces constraint limits: max 25-30 model calls, 50 tool calls per episode."""
    max_model_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_MODEL_CALLS", "30")))
    max_tool_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "50")))
    model_calls_used: int = 0
    tool_calls_used: int = 0

    def record_model_call(self) -> None:
        self.model_calls_used += 1
        if self.model_calls_used > self.max_model_calls:
            raise RuntimeError(
                f"Budget exceeded: Model calls limit of {self.max_model_calls} reached ({self.model_calls_used})."
            )

    def record_tool_call(self) -> None:
        self.tool_calls_used += 1
        if self.tool_calls_used > self.max_tool_calls:
            raise RuntimeError(
                f"Budget exceeded: Tool calls limit of {self.max_tool_calls} reached ({self.tool_calls_used})."
            )


class RunState(BaseModel):
    """Structured run state supporting auditability and selective replanning."""
    episode_id: str = "EP01"
    budget: BudgetTracker = Field(default_factory=BudgetTracker)
    evidence_items: Dict[str, EvidenceItem] = Field(default_factory=dict)
    conflicts: List[EvidenceConflict] = Field(default_factory=list)
    learned_rules: Dict[str, LanguageHypothesis] = Field(default_factory=dict)
    subtitle_decisions: Dict[str, SubtitleDecision] = Field(default_factory=dict)
    review_queue: List[SubtitleDecision] = Field(default_factory=list)
    invalidation_history: List[Dict[str, str]] = Field(default_factory=list)
    audit_log: List[str] = Field(default_factory=list)

    def log(self, message: str) -> None:
        self.audit_log.append(message)
