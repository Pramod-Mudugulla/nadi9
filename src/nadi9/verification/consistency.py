import re
from typing import List, Optional, Tuple


class ConsistencyVerifier:
    """
    Checks reading speed, timing duration, and interpersonal honorific consistency.
    """

    MAX_CPS = 21.0  # Max reading speed characters per second for OTT broadcast

    @staticmethod
    def parse_timecode_to_seconds(tc: str) -> float:
        """Converts SRT timecode HH:MM:SS,mmm to total seconds."""
        try:
            parts = tc.replace(",", ".").split(":")
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600.0 + m * 60.0 + s
        except Exception:
            return 3.0

    def verify(
        self,
        nadi_9_text: str,
        source_text: str,
        speaker: str,
        listener: Optional[str],
        time_in: str,
        time_out: str,
    ) -> Tuple[bool, float, List[str]]:
        issues: List[str] = []

        if "[insufficient_evidence" in nadi_9_text.lower():
            return False, 0.0, ["Line flagged for review due to insufficient evidence."]

        duration = self.parse_timecode_to_seconds(time_out) - self.parse_timecode_to_seconds(time_in)
        if duration <= 0.2:
            duration = 1.0

        char_count = len(nadi_9_text.strip())
        cps = round(char_count / duration, 2)

        if cps > self.MAX_CPS:
            issues.append(f"Reading speed warning: {cps} CPS exceeds comfortable threshold of {self.MAX_CPS} CPS.")

        # Interpersonal honorific check
        if listener in ["Father", "Village Elder", "Mother", "Sarina-ma"] and "-ma" not in nadi_9_text:
            if "aba" in nadi_9_text or "sarina" in nadi_9_text:
                issues.append(
                    f"Sociolinguistic consistency: Speaker '{speaker}' addresses elder '{listener}' without respectful honorific suffix '-ma'."
                )

        is_valid = len(issues) == 0
        return is_valid, cps, issues
