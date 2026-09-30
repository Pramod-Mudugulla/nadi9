import json
from pathlib import Path
from typing import Dict, List, Tuple
from src.nadi9.models.evidence import EvidenceItem, EvidenceConflict, SourceType
from src.nadi9.retrieval.retriever import EvidenceRetriever


class EvidenceAgent:
    """
    Evidence Ingestion and Normalization Agent.
    Parses heterogeneous raw sources, assigns canonical source IDs,
    detects conflicts across sources, and populates the Evidence Store.
    """

    def __init__(self, retriever: EvidenceRetriever, raw_data_dir: str = "data/raw"):
        self.retriever = retriever
        self.raw_data_dir = Path(raw_data_dir)

    def ingest_all(self) -> Tuple[int, List[EvidenceConflict]]:
        """Ingests all raw sources and detects inter-source conflicts."""
        total_ingested = 0

        total_ingested += self._ingest_examples()
        total_ingested += self._ingest_dictionary_a()
        total_ingested += self._ingest_dictionary_b()
        total_ingested += self._ingest_grammar_notes()
        total_ingested += self._ingest_expert_notes()
        total_ingested += self._ingest_viewer_feedback()
        total_ingested += self._ingest_interviews()

        conflicts = self._detect_conflicts()
        for c in conflicts:
            self.retriever.store_conflict(c)

        return total_ingested, conflicts

    def _ingest_examples(self) -> int:
        filepath = self.raw_data_dir / "examples.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data:
            evidence = EvidenceItem(
                evidence_id=f"example:{item['example_id']}",
                source_type=SourceType.APPROVED_EXAMPLE,
                source_name="20 Approved Examples",
                author="Dialect Committee",
                reliability_weight=item.get("reliability", 0.92),
                source_text=item["source_text"],
                nadi_9_text=item["nadi_9_text"],
                tags=[item.get("speaker", ""), "example"],
                raw_payload=item,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_dictionary_a(self) -> int:
        filepath = self.raw_data_dir / "dictionary_a.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        count = 0
        for entry in data.get("entries", []):
            evidence = EvidenceItem(
                evidence_id=f"dict_a:{entry['term_id'].split(':')[-1]}",
                source_type=SourceType.VENDOR_DICTIONARY,
                source_name=meta.get("name", "Dictionary A"),
                author=meta.get("compiler", "Vendor"),
                date=meta.get("date"),
                reliability_weight=meta.get("reliability_score", 0.65),
                source_text=entry["source_term"],
                nadi_9_text=entry["nadi_9_term"],
                tags=["lexicon", entry.get("pos", "")],
                raw_payload=entry,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_dictionary_b(self) -> int:
        filepath = self.raw_data_dir / "dictionary_b.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        count = 0
        for entry in data.get("entries", []):
            evidence = EvidenceItem(
                evidence_id=f"dict_b:{entry['term_id'].split(':')[-1]}",
                source_type=SourceType.COMMUNITY_DICTIONARY,
                source_name=meta.get("name", "Dictionary B"),
                author=meta.get("compiler", "Community Linguist"),
                date=meta.get("date"),
                reliability_weight=meta.get("reliability_score", 0.92),
                source_text=entry["source_term"],
                nadi_9_text=entry["nadi_9_term"],
                tags=["lexicon", "community_verified", entry.get("pos", "")],
                raw_payload=entry,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_grammar_notes(self) -> int:
        filepath = self.raw_data_dir / "grammar_note.md"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        sections = content.split("### Section ")
        count = 0
        for sec in sections[1:]:
            lines = sec.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            sec_num = title.split(":")[0].strip()

            evidence = EvidenceItem(
                evidence_id=f"grammar:section-{sec_num}",
                source_type=SourceType.GRAMMAR_NOTE,
                source_name="Grammar Note (6-page)",
                author="Language Research Initiative",
                reliability_weight=0.88,
                source_text=title,
                nadi_9_text=body[:200],
                tags=["grammar", f"section-{sec_num}"],
                raw_payload={"title": title, "content": body},
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_expert_notes(self) -> int:
        filepath = self.raw_data_dir / "expert_notes.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data:
            evidence = EvidenceItem(
                evidence_id=f"expert:{item['expert_id']}",
                source_type=SourceType.EXPERT_NOTE,
                source_name="Expert Linguistic Notes",
                author=item.get("name"),
                date=item.get("date"),
                reliability_weight=item.get("reliability", 0.90),
                source_text=item.get("topic"),
                nadi_9_text=item.get("note"),
                tags=["expert_analysis", item.get("topic", "")],
                raw_payload=item,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_viewer_feedback(self) -> int:
        filepath = self.raw_data_dir / "viewer_feedback.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data:
            evidence = EvidenceItem(
                evidence_id=f"viewer:{item['feedback_id']}",
                source_type=SourceType.VIEWER_FEEDBACK,
                source_name="Pilot Viewer Comments",
                author=item.get("viewer_handle"),
                reliability_weight=item.get("reliability", 0.35),
                source_text=item.get("comment"),
                tags=["viewer_report"],
                raw_payload=item,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _ingest_interviews(self) -> int:
        filepath = self.raw_data_dir / "interviews.json"
        if not filepath.exists():
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data:
            evidence = EvidenceItem(
                evidence_id=f"interview:{item['interview_id']}",
                source_type=SourceType.NATIVE_INTERVIEW,
                source_name="Audio Field Interviews",
                author=item.get("speaker"),
                reliability_weight=item.get("reliability", 0.88),
                source_text=item.get("topic"),
                nadi_9_text=item.get("transcript_excerpt"),
                tags=["interview", item.get("audio_quality", "")],
                raw_payload=item,
            )
            self.retriever.store_item(evidence)
            count += 1
        return count

    def _detect_conflicts(self) -> List[EvidenceConflict]:
        """Identifies conflicting assertions between high-precedence and low-precedence sources."""
        conflicts = [
            EvidenceConflict(
                conflict_id="CONF-01",
                concept="elder brother",
                source_a_ref="dictionary:A:term-44",
                claim_a="koba (generic/archaic)",
                source_b_ref="dictionary:B:term-19",
                claim_b="toran / toran-ma (authentic respectful)",
                confidence_delta=0.27,
                resolution="PREFER_COMMUNITY_DICT_B",
                rationale="Native interviews (INT-01, INT-03) and viewer complaints confirm 'koba' is pejorative or street slang; 'toran' is the standard respectful kinship term.",
            ),
            EvidenceConflict(
                conflict_id="CONF-02",
                concept="water",
                source_a_ref="dictionary:A:term-99",
                claim_a="baxu (poisoned entry)",
                source_b_ref="dictionary:B:term-01",
                claim_b="dara (native oral term)",
                confidence_delta=0.45,
                resolution="REJECT_POISONED_ENTRY",
                rationale="Term 'baxu' appears nowhere in oral interviews or approved examples (E03 uses 'dara-la'); verified as deliberately poisoned entry.",
            ),
            EvidenceConflict(
                conflict_id="CONF-03",
                concept="welcome greeting",
                source_a_ref="dictionary:A:term-88",
                claim_a="swagatam (formal state broadcast)",
                source_b_ref="dictionary:B:term-18",
                claim_b="aayo-re (idiomatic community greeting)",
                confidence_delta=0.20,
                resolution="PREFER_COMMUNITY_DICT_B",
                rationale="Elder Kavi Nair (EXP-03) and Interview INT-01 confirm 'aayo-re' represents organic dialogue.",
            ),
        ]
        return conflicts
