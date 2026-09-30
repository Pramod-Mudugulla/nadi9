import re
from typing import List, Tuple


class GrammarVerifier:
    """
    Independent syntax and morphosyntactic verification.
    Verifies SOV ordering, object markers (-la), and negation structure.
    """

    KNOWN_VERB_ROOTS = {"doti", "chora", "fala", "zhe", "basha", "duva", "le", "suna", "bisra", "jwala", "dekha"}
    TENSE_SUFFIXES = {"-ka", "-ren", "-te", "-zho"}

    def verify(self, nadi_9_text: str, source_text: str) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        if "[insufficient_evidence" in nadi_9_text.lower():
            return False, ["Translation was aborted due to missing evidence."]

        words = [w.strip(".,?!;:") for w in nadi_9_text.split() if w.strip(".,?!;:")]
        if not words:
            return False, ["Empty translation string."]

        # Check for double negation
        negation_count = 0
        for w in words:
            if w.lower().startswith("ni-") or w.lower() == "nira":
                negation_count += 1
        if negation_count > 1:
            issues.append("Grammar violation: Double negation detected (ungrammatical in Nadi-9).")

        # SOV structural heuristic check for declarative sentences with an object marker (-la)
        # In SOV, the word with '-la' should precede the main verb.
        has_object_marker = False
        obj_index = -1
        verb_index = -1

        for idx, w in enumerate(words):
            if "-la" in w.lower():
                has_object_marker = True
                obj_index = idx

            # Detect verb root or verb suffix
            cleaned = w.lower()
            for sfx in self.TENSE_SUFFIXES:
                if cleaned.endswith(sfx):
                    verb_index = idx
                    break
            for root in self.KNOWN_VERB_ROOTS:
                if root in cleaned:
                    verb_index = idx
                    break

        if has_object_marker and verb_index != -1:
            if obj_index > verb_index:
                # The object appears after the verb: classic SVO violation
                issues.append(
                    f"Grammar violation: Inverted word order detected. Object marker '{words[obj_index]}' appears after verb '{words[verb_index]}' (violates standard SOV)."
                )

        is_valid = len(issues) == 0
        return is_valid, issues
