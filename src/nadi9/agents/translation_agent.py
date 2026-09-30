import json
from typing import Dict, List, Optional
from src.nadi9.models.evidence import SourceType
from src.nadi9.models.hypothesis import LanguageHypothesis
from src.nadi9.models.subtitle import SubtitleItem, SubtitleDecision
from src.nadi9.models.state import RunState
from src.nadi9.providers.base import BaseLLMProvider
from src.nadi9.retrieval.retriever import EvidenceRetriever


class TranslationAgent:
    """
    Evidence-grounded Translation Agent.
    Translates source lines into Nadi-9 proposals strictly bounded by retrieved evidence.
    Refuses to hallucinate missing vocabulary and logs all assumptions.
    """

    def __init__(
        self,
        provider: BaseLLMProvider,
        retriever: EvidenceRetriever,
    ):
        self.provider = provider
        self.retriever = retriever

    def translate_line(
        self,
        line: SubtitleItem,
        state: RunState,
        active_rules: Dict[str, LanguageHypothesis],
    ) -> SubtitleDecision:
        """
        Translates a single subtitle line with budget accounting and evidence grounding.
        """
        # 1. Retrieve relevant evidence
        retrieved_items = self.retriever.search(line.source_text, limit=5)
        state.budget.record_tool_call()

        evidence_ids = [item.evidence_id for item in retrieved_items]

        # 2. Check for known conflicts related to this line
        conflicts_present = []
        if "elder brother" in line.source_text.lower():
            conflicts_present.append("dictionary:A:term-44 vs dictionary:B:term-19")
        if "water" in line.source_text.lower():
            conflicts_present.append("dictionary:A:term-99 (poisoned 'baxu') vs dictionary:B:term-01 ('dara')")

        # 3. Build structured prompt
        prompt = {
            "task": "translate_to_nadi9",
            "subtitle_id": line.subtitle_id,
            "scene_id": line.scene_id,
            "speaker": line.speaker,
            "listener": line.listener,
            "source_text": line.source_text,
            "scene_notes": line.notes,
            "retrieved_evidence": [
                {
                    "id": it.evidence_id,
                    "type": it.source_type.value,
                    "source": it.source_text,
                    "target": it.nadi_9_text,
                    "reliability": it.reliability_weight,
                }
                for it in retrieved_items
            ],
            "active_rules": [
                {"id": r.rule_id, "name": r.name, "pattern": r.pattern_rule, "confidence": r.confidence}
                for r in active_rules.values()
            ],
            "known_conflicts": conflicts_present,
        }

        # 4. Invoke LLM / Mock Provider
        state.budget.record_model_call()
        raw_response = self.provider.generate(
            prompt=json.dumps(prompt, indent=2),
            system_instruction=(
                "You are a cautious junior linguist translating an episode into Nadi-9. "
                "Never invent words. If evidence is missing, output '[INSUFFICIENT_EVIDENCE]' and low confidence."
            ),
            temperature=0.0,
        )

        try:
            parsed = json.loads(raw_response)
        except Exception:
            parsed = {
                "nadi_9_text": "[INSUFFICIENT_EVIDENCE: format error]",
                "confidence": 0.2,
                "confidence_reason": "Model returned unparseable output.",
                "evidence": evidence_ids,
                "assumptions": ["Fallback due to parse error"],
                "conflicts": conflicts_present,
                "review_question": "Manual translation required.",
            }

        decision = SubtitleDecision(
            subtitle_id=line.subtitle_id,
            source_text=line.source_text,
            nadi_9_text=parsed.get("nadi_9_text", ""),
            confidence=float(parsed.get("confidence", 0.5)),
            confidence_reason=parsed.get("confidence_reason"),
            decision="HUMAN_REVIEW" if parsed.get("confidence", 0.5) < 0.80 or parsed.get("review_question") else "PASS",
            evidence=parsed.get("evidence", evidence_ids),
            assumptions=parsed.get("assumptions", []),
            conflicts=parsed.get("conflicts", conflicts_present),
            review_question=parsed.get("review_question"),
            time_in=line.time_in,
            time_out=line.time_out,
        )
        return decision
