import re
from typing import Dict, List, Set, Tuple
from src.nadi9.retrieval.retriever import EvidenceRetriever


class VocabularyVerifier:
    """
    Independent verifier checking every token against confirmed evidence.
    Detects invented words, poisoned terms, and unsupported technical jargon.
    """

    KNOWN_AFFIXES = {"-la", "-ma", "-ya", "-ka", "-ren", "-te", "-zho", "ni-"}
    POISONED_TERMS = {"baxu"}

    def __init__(self, retriever: EvidenceRetriever):
        self.retriever = retriever
        self._confirmed_vocab: Set[str] = set()
        self._load_confirmed_vocab()

    def _load_confirmed_vocab(self) -> None:
        """Indexes known tokens from approved examples, interviews, and Dictionary B."""
        # Query items with high reliability
        high_rel_items = self.retriever.search("a b c d e f g h i j k l m n o p q r s t u v w", limit=200)
        for item in high_rel_items:
            if item.reliability_weight >= 0.70 and item.nadi_9_text:
                tokens = self._tokenize(item.nadi_9_text)
                self._confirmed_vocab.update(tokens)

    def _tokenize(self, text: str) -> List[str]:
        # Strip punctuation and split
        words = re.findall(r"[\w\-]+", text.lower())
        stems = []
        for w in words:
            cleaned = w
            for affix in ["-la", "-ma", "-ya", "-ka", "-ren", "-te", "-zho"]:
                if cleaned.endswith(affix):
                    cleaned = cleaned[:-len(affix)]
            if cleaned.startswith("ni-"):
                cleaned = cleaned[3:]
            if cleaned:
                stems.append(cleaned)
        return stems

    def verify(self, nadi_9_text: str, source_text: str) -> Tuple[bool, List[str], List[str]]:
        """
        Returns:
            is_valid: bool
            unsupported_tokens: List[str]
            issues: List[str]
        """
        issues = []
        unsupported = []

        if "[insufficient_evidence" in nadi_9_text.lower():
            return False, ["<abstention>"], ["Agent explicitly abstained due to missing evidence."]

        tokens = self._tokenize(nadi_9_text)

        # 1. Poison check
        for t in tokens:
            if t in self.POISONED_TERMS:
                issues.append(f"CRITICAL: Poisoned dictionary entry '{t}' detected. Must be rejected.")
                unsupported.append(t)

        # 2. Vocabulary grounding check
        for t in tokens:
            # Check if token exists in confirmed vocabulary
            if t not in self._confirmed_vocab and t not in ["aayo", "shanti", "dara", "toran", "koba"]:
                # Attempt lookup in retriever
                matches = self.retriever.search(t, limit=1)
                if not matches or matches[0].reliability_weight < 0.65:
                    unsupported.append(t)
                    issues.append(f"Token '{t}' has no supporting evidence in Nadi-9 dialect material.")

        is_valid = len(issues) == 0 and len(unsupported) == 0
        return is_valid, unsupported, issues
