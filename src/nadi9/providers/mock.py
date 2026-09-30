import json
import re
from typing import Any, Optional
from src.nadi9.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock provider for offline execution, evaluation, and test suites.
    Simulates dialect translation, independent verification, and failure scenarios.
    """

    def __init__(self, simulate_failure: bool = False, fail_count: int = 0):
        self.simulate_failure = simulate_failure
        self.fail_count = fail_count
        self.calls_count = 0

    def is_available(self) -> bool:
        return True

    def trigger_temporary_failure(self, times: int = 1) -> None:
        """Sets up a temporary failure for N calls to test retry/recovery."""
        self.simulate_failure = True
        self.fail_count = times

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        self.calls_count += 1

        if self.simulate_failure and self.fail_count > 0:
            self.fail_count -= 1
            raise ConnectionError("MockLLMProvider: 503 Service Temporarily Unavailable")

        prompt_lower = prompt.lower()

        # Handle Verification Mode
        sys_lower = (system_instruction or "").lower()
        if "verification" in sys_lower or "auditor" in sys_lower or "verification" in prompt_lower or "verify" in prompt_lower:
            return self._handle_mock_verification(prompt)

        # Handle Translation / Inference Mode
        return self._handle_mock_translation(prompt)

    def _handle_mock_translation(self, prompt: str) -> str:
        try:
            parsed = json.loads(prompt)
            target_source = parsed.get("source_text", "").lower()
            sub_id = parsed.get("subtitle_id", "")
        except Exception:
            target_source = prompt.lower()
            sub_id = ""

        # Check for unsupported modern machine term
        if "pneumatic gearbox" in target_source or sub_id == "S008":
            return json.dumps({
                "nadi_9_text": "[INSUFFICIENT_EVIDENCE: unsupported mechanical terminology]",
                "confidence": 0.15,
                "confidence_reason": "No evidence for pneumatic gearbox in Nadi-9 dialect pack.",
                "evidence": [],
                "assumptions": ["Modern trade mechanism not present in local lexicon"],
                "conflicts": [],
                "review_question": "Does a loanword or descriptive compounding exist for 'pneumatic gearbox'?"
            })

        # Check for S014: elder brother reunion
        if "you came back, elder brother?" in target_source or sub_id == "S014":
            # Check if Dr. Sen's correction is active in the prompt
            if "rule-kin-03" in prompt.lower() or "corr-2024-09" in prompt.lower() or "linguist_correction" in prompt.lower():
                return json.dumps({
                    "nadi_9_text": "Toran-ya, fala-zho-ka?",
                    "confidence": 0.94,
                    "confidence_reason": "Updated per Dr. Alok Sen's linguist correction CORR-2024-09.",
                    "evidence": ["linguist_correction:CORR-2024-09", "example:E07", "dict_b:term-19"],
                    "assumptions": ["Reconciliation honorific confirmed by field linguist"],
                    "conflicts": ["Resolved: Dict A 'koba' rejected in favor of 'toran-ya'"],
                    "review_question": None
                })
            else:
                return json.dumps({
                    "nadi_9_text": "Toran, fala-zho-ka?",
                    "confidence": 0.72,
                    "confidence_reason": "Kinship term is contested between Dictionary A ('koba') and Dictionary B ('toran'). Suffix depends on reconciliation status.",
                    "evidence": ["example:E07", "grammar:respect-2", "dict_b:term-19"],
                    "assumptions": ["speaker addresses an older sibling"],
                    "conflicts": ["dictionary:A:term-44 vs dictionary:B:term-19"],
                    "review_question": "Which kinship form applies after reconciliation?"
                })

        # S001: Morning greeting
        if "good morning" in target_source:
            return json.dumps({
                "nadi_9_text": "Sula boro, aba-ma.",
                "confidence": 0.96,
                "confidence_reason": "Direct 1:1 match in approved example E01 with generational honorific -ma.",
                "evidence": ["example:E01", "grammar:respect-1", "dict_b:term-11"],
                "assumptions": ["Respectful morning address to parent"],
                "conflicts": [],
                "review_question": None
            })

        # S002: Peace greeting
        if "peace to your house" in target_source:
            return json.dumps({
                "nadi_9_text": "Shanti tuya griha-la.",
                "confidence": 0.95,
                "confidence_reason": "Direct match in approved example E09.",
                "evidence": ["example:E09", "dict_b:term-06", "dict_b:term-17"],
                "assumptions": ["Formal parental blessing"],
                "conflicts": [],
                "review_question": None
            })

        # S003: Mountain
        if "mountain" in target_source:
            return json.dumps({
                "nadi_9_text": "Koa giri-la doti-te.",
                "confidence": 0.94,
                "confidence_reason": "Direct match in approved example E02 with SOV ordering.",
                "evidence": ["example:E02", "grammar:word_order-1", "dict_b:term-03"],
                "assumptions": ["Declarative SOV clause"],
                "conflicts": [],
                "review_question": None
            })

        # S004: Water line (avoiding poisoned baxu)
        if "water" in target_source or "drink" in target_source:
            return json.dumps({
                "nadi_9_text": "Te dara-la ni-chora-te.",
                "confidence": 0.95,
                "confidence_reason": "SOV sentence, authentic term 'dara' verified against oral interviews over poisoned 'baxu'.",
                "evidence": ["example:E03", "dict_b:term-01", "interview:INT-02", "expert:EXP-02"],
                "assumptions": ["Standard declarative negation"],
                "conflicts": ["dictionary:A:term-99 (baxu) rejected as poisoned entry"],
                "review_question": None
            })

        # S005: Wind cold
        if "wind" in target_source or "cold" in target_source:
            return json.dumps({
                "nadi_9_text": "Nokta bayu sidi esa.",
                "confidence": 0.92,
                "confidence_reason": "Direct match in approved example E05.",
                "evidence": ["example:E05", "dict_b:term-13", "dict_b:term-14"],
                "assumptions": ["Descriptive climate remark"],
                "conflicts": [],
                "review_question": None
            })

        # S006: Bridge broken
        if "bridge" in target_source or "broken" in target_source:
            return json.dumps({
                "nadi_9_text": "Setu tutta esa.",
                "confidence": 0.93,
                "confidence_reason": "Direct match in approved example E15 and interview INT-05.",
                "evidence": ["example:E15", "interview:INT-05", "dict_a:term-14"],
                "assumptions": ["Scout observation"],
                "conflicts": [],
                "review_question": None
            })

        # S007: Secret path
        if "secret path" in target_source or "guide" in target_source:
            return json.dumps({
                "nadi_9_text": "Koa-la gupt rasta dekha-te.",
                "confidence": 0.92,
                "confidence_reason": "Direct match in approved example E17.",
                "evidence": ["example:E17", "dict_b:term-08", "dict_b:term-09"],
                "assumptions": ["Imperative instruction to guide"],
                "conflicts": [],
                "review_question": None
            })

        # S009: Kindness
        if "kindness" in target_source or "forget" in target_source:
            return json.dumps({
                "nadi_9_text": "Nu ye krupa-la ni-bisra-ren.",
                "confidence": 0.94,
                "confidence_reason": "Direct match in approved example E16 with future negative -ren.",
                "evidence": ["example:E16", "grammar:negation-1", "dict_b:term-07"],
                "assumptions": ["Formal parting gratitude"],
                "conflicts": [],
                "review_question": None
            })

        # S010: Speak loudly
        if "speak" in target_source or "loudly" in target_source:
            return json.dumps({
                "nadi_9_text": "Buland ni-basha-te.",
                "confidence": 0.91,
                "confidence_reason": "Direct match in approved example E11.",
                "evidence": ["example:E11", "grammar:negation-1", "dict_a:term-08"],
                "assumptions": ["Warning register"],
                "conflicts": [],
                "review_question": None
            })

        # S011: Welcome home
        if "welcome" in target_source:
            return json.dumps({
                "nadi_9_text": "Aayo-re, anjan manush.",
                "confidence": 0.90,
                "confidence_reason": "Uses authentic oral greeting 'aayo-re' per Dict B and INT-01 over formal 'swagatam'.",
                "evidence": ["dict_b:term-18", "interview:INT-01", "expert:EXP-03"],
                "assumptions": ["Welcoming greeting to stranger/traveler"],
                "conflicts": ["dictionary:A:term-88 (swagatam) avoided as unnatural"],
                "review_question": None
            })

        # Default fallback translation template
        return json.dumps({
            "nadi_9_text": "Koa giri-la doti-te.",
            "confidence": 0.88,
            "confidence_reason": "Grounded in approved examples and SOV grammar rule.",
            "evidence": ["example:E02", "grammar:word_order-1"],
            "assumptions": ["Standard SOV word order"],
            "conflicts": [],
            "review_question": None
        })

    def _handle_mock_verification(self, prompt: str) -> str:
        # If candidate text contains unsupported marker or low confidence
        if "[insufficient_evidence" in prompt.lower() or "pneumatic gearbox" in prompt.lower():
            return json.dumps({
                "verdict": "HUMAN_REVIEW",
                "vocabulary_supported": False,
                "grammar_supported": False,
                "unsupported_tokens": ["pneumatic", "gearbox"],
                "reading_speed_cps": 8.0,
                "issues": ["No evidence in Nadi-9 lexicon for mechanical loanwords."],
                "review_question": "Does a loanword or descriptive compounding exist for 'pneumatic gearbox'?"
            })

        # S014 check
        if "toran-ya" in prompt.lower():
            return json.dumps({
                "verdict": "PASS",
                "vocabulary_supported": True,
                "grammar_supported": True,
                "unsupported_tokens": [],
                "reading_speed_cps": 5.2,
                "issues": [],
                "review_question": None
            })
        elif "s014" in prompt.lower() or "which kinship form applies" in prompt.lower():
            return json.dumps({
                "verdict": "HUMAN_REVIEW",
                "vocabulary_supported": True,
                "grammar_supported": True,
                "unsupported_tokens": [],
                "reading_speed_cps": 5.0,
                "issues": ["Kinship conflict unresolved between Dict A and Dict B; reconciliation register unconfirmed."],
                "review_question": "Which kinship form applies after reconciliation?"
            })

        # Poisoned entry check: if someone translated with baxu
        if "baxu" in prompt.lower():
            return json.dumps({
                "verdict": "HUMAN_REVIEW",
                "vocabulary_supported": False,
                "grammar_supported": True,
                "unsupported_tokens": ["baxu"],
                "issues": ["Term 'baxu' identified as poisoned entry in Dictionary A; oral evidence requires 'dara'."],
                "review_question": "Confirm rejection of vendor poisoned entry 'baxu' in favor of 'dara'."
            })

        # Standard verified line
        return json.dumps({
            "verdict": "PASS",
            "vocabulary_supported": True,
            "grammar_supported": True,
            "unsupported_tokens": [],
            "reading_speed_cps": 4.8,
            "issues": [],
            "review_question": None
        })
