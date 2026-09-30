import json
from typing import Optional
from src.nadi9.models.subtitle import SubtitleItem, SubtitleDecision
from src.nadi9.models.state import RunState
from src.nadi9.providers.base import BaseLLMProvider
from src.nadi9.retrieval.retriever import EvidenceRetriever
from src.nadi9.verification.vocabulary import VocabularyVerifier
from src.nadi9.verification.grammar import GrammarVerifier
from src.nadi9.verification.consistency import ConsistencyVerifier


class VerificationAgent:
    """
    Independent Verification Layer.
    Executes adversarial checks completely separate from translation prompt.
    Checks vocabulary grounding, syntax conformity, reading speed, and kinship etiquette.
    """

    def __init__(
        self,
        provider: BaseLLMProvider,
        retriever: EvidenceRetriever,
    ):
        self.provider = provider
        self.retriever = retriever
        self.vocab_verifier = VocabularyVerifier(retriever)
        self.grammar_verifier = GrammarVerifier()
        self.consistency_verifier = ConsistencyVerifier()

    def verify_proposal(
        self,
        proposal: SubtitleDecision,
        source_line: SubtitleItem,
        state: RunState,
    ) -> SubtitleDecision:
        """
        Independently audits a translation proposal.
        Can disagree with and overturn the translator's decision.
        """
        issues = []
        is_human_review = (proposal.decision == "HUMAN_REVIEW")
        review_q = proposal.review_question

        # Consolidate deterministic verification into one validation tool invocation
        state.budget.record_tool_call()

        # 1. Deterministic Vocabulary Check
        vocab_ok, unsupported_tokens, vocab_issues = self.vocab_verifier.verify(
            proposal.nadi_9_text, proposal.source_text
        )
        if not vocab_ok:
            issues.extend(vocab_issues)
            is_human_review = True
            if not review_q:
                review_q = f"Unsupported vocabulary: {', '.join(unsupported_tokens)}. Require expert lexical decision."

        # 2. Deterministic Grammar Check
        grammar_ok, grammar_issues = self.grammar_verifier.verify(
            proposal.nadi_9_text, proposal.source_text
        )
        if not grammar_ok:
            issues.extend(grammar_issues)
            is_human_review = True
            if not review_q:
                review_q = "Grammar violation detected. Confirm word order and affix attachment."

        # 3. Reading Speed & Social Consistency Check
        consistency_ok, cps, consistency_issues = self.consistency_verifier.verify(
            nadi_9_text=proposal.nadi_9_text,
            source_text=proposal.source_text,
            speaker=source_line.speaker,
            listener=source_line.listener,
            time_in=source_line.time_in,
            time_out=source_line.time_out,
        )
        if not consistency_ok:
            issues.extend(consistency_issues)
            # If reading speed is too high or honorific missing
            if any("honorific" in iss.lower() for iss in consistency_issues):
                is_human_review = True
                if not review_q:
                    review_q = f"Address etiquette to '{source_line.listener}' may require honorific '-ma'."

        # 4. Independent Provider Review Call (Verification LLM pass)
        # Invoked selectively when there are conflicts, flagged issues, or low translator confidence
        needs_model_audit = is_human_review or issues or proposal.conflicts or (proposal.confidence < 0.90)
        if needs_model_audit:
            state.budget.record_model_call()
            verif_prompt = {
                "task": "independent_verification_layer",
                "subtitle_id": proposal.subtitle_id,
                "source_text": proposal.source_text,
                "candidate_translation": proposal.nadi_9_text,
                "translator_confidence": proposal.confidence,
                "deterministic_issues": issues,
                "cps": cps,
            }

            verif_resp = self.provider.generate(
                prompt=json.dumps(verif_prompt),
                system_instruction=(
                    "You are an adversarial linguistic auditor. Your job is to catch errors, "
                    "unsupported terms, and ungrounded inventions. Be strict."
                ),
            )

            try:
                parsed_v = json.loads(verif_resp)
                if parsed_v.get("verdict") == "HUMAN_REVIEW":
                    is_human_review = True
                    if parsed_v.get("review_question"):
                        review_q = parsed_v["review_question"]
                    issues.extend(parsed_v.get("issues", []))
                elif parsed_v.get("verdict") == "PASS" and not issues:
                    is_human_review = False
                    review_q = None
            except Exception:
                pass

        # Calculate final calibrated confidence
        final_confidence = proposal.confidence
        if is_human_review:
            final_confidence = min(final_confidence, 0.75)
            if "[insufficient_evidence" in proposal.nadi_9_text.lower():
                final_confidence = 0.15
        else:
            final_confidence = max(final_confidence, 0.85)

        final_decision = SubtitleDecision(
            subtitle_id=proposal.subtitle_id,
            source_text=proposal.source_text,
            nadi_9_text=proposal.nadi_9_text,
            confidence=round(final_confidence, 2),
            decision="HUMAN_REVIEW" if is_human_review else "PASS",
            evidence=proposal.evidence,
            assumptions=proposal.assumptions,
            conflicts=proposal.conflicts,
            review_question=review_q if is_human_review else None,
            confidence_reason=proposal.confidence_reason or (
                "Verified against grammar rules, vocabulary store, and reading speed constraints."
                if not is_human_review
                else f"Flagged: {'; '.join(issues)}"
            ),
            time_in=proposal.time_in,
            time_out=proposal.time_out,
            reading_speed_cps=cps,
            verification_notes="; ".join(issues) if issues else "All verification checks passed.",
        )
        return final_decision
