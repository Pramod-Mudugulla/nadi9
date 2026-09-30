import json
import sqlite3
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.nadi9.models.evidence import EvidenceItem, EvidenceConflict, SourceType


class EvidenceRetriever:
    """
    Evidence Store backed by SQLite.
    Implements source-precedence weighting, conflict detection, and prompt injection defense.
    """

    # Hierarchy of trust weights
    SOURCE_PRIORS = {
        SourceType.LINGUIST_CORRECTION: 0.99,
        SourceType.APPROVED_EXAMPLE: 0.95,
        SourceType.COMMUNITY_DICTIONARY: 0.92,
        SourceType.EXPERT_NOTE: 0.90,
        SourceType.NATIVE_INTERVIEW: 0.88,
        SourceType.GRAMMAR_NOTE: 0.85,
        SourceType.VENDOR_DICTIONARY: 0.65,
        SourceType.VIEWER_FEEDBACK: 0.40,
    }

    ADVERSARIAL_PATTERNS = [
        r"ignore\s+all\s+previous",
        r"ignore\s+the\s+assignment",
        r"override\s+system",
        r"output\s+pass",
        r"bypass\s+verification",
    ]

    def __init__(self, db_path: str = "data/processed/evidence_store.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_items (
                    evidence_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    author TEXT,
                    date TEXT,
                    reliability_weight REAL NOT NULL,
                    source_text TEXT,
                    nadi_9_text TEXT,
                    raw_json TEXT NOT NULL,
                    is_adversarial INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    concept TEXT NOT NULL,
                    source_a_ref TEXT NOT NULL,
                    claim_a TEXT NOT NULL,
                    source_b_ref TEXT NOT NULL,
                    claim_b TEXT NOT NULL,
                    confidence_delta REAL,
                    resolution TEXT DEFAULT 'UNRESOLVED',
                    rationale TEXT
                )
            """)
            conn.commit()

    def sanitize_text(self, text: Optional[str]) -> tuple[str, bool]:
        """Detect and defang potential prompt injection attacks in untrusted inputs."""
        if not text:
            return "", False
        is_attack = False
        for pat in self.ADVERSARIAL_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                is_attack = True
                text = re.sub(pat, "[FILTERED_ADVERSARIAL_INJECTION]", text, flags=re.IGNORECASE)
        return text, is_attack

    def store_item(self, item: EvidenceItem) -> None:
        raw_str = json.dumps(item.raw_payload)
        cleaned_source, adv1 = self.sanitize_text(item.source_text)
        cleaned_target, adv2 = self.sanitize_text(item.nadi_9_text)
        is_adv = 1 if (adv1 or adv2 or item.is_adversarial()) else 0

        # Adjust reliability by source precedence prior
        prior = self.SOURCE_PRIORS.get(item.source_type, 0.70)
        calibrated_weight = round((item.reliability_weight * 0.6) + (prior * 0.4), 2)
        if is_adv:
            calibrated_weight = 0.05  # heavily discount adversarial inputs

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evidence_items
                (evidence_id, source_type, source_name, author, date, reliability_weight, source_text, nadi_9_text, raw_json, is_adversarial)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.evidence_id,
                item.source_type.value,
                item.source_name,
                item.author,
                item.date,
                calibrated_weight,
                cleaned_source,
                cleaned_target,
                raw_str,
                is_adv
            ))
            conn.commit()

    def store_conflict(self, conflict: EvidenceConflict) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evidence_conflicts
                (conflict_id, concept, source_a_ref, claim_a, source_b_ref, claim_b, confidence_delta, resolution, rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict.conflict_id,
                conflict.concept,
                conflict.source_a_ref,
                conflict.claim_a,
                conflict.source_b_ref,
                conflict.claim_b,
                conflict.confidence_delta,
                conflict.resolution,
                conflict.rationale
            ))
            conn.commit()

    def get_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM evidence_items WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return None
            return self._row_to_item(row)

    def search(
        self,
        query: str,
        limit: int = 6,
        source_type: Optional[SourceType] = None,
        exclude_adversarial: bool = True,
    ) -> List[EvidenceItem]:
        """
        Retrieves matching evidence ranked by textual match and reliability weight.
        """
        words = re.findall(r"\w+", query.lower())
        if not words:
            return []

        cleaned_words = [w for w in words if len(w) > 2]
        if not cleaned_words:
            cleaned_words = words

        # Build parameterized SQL search
        conditions = []
        params: List[Any] = []

        if exclude_adversarial:
            conditions.append("is_adversarial = 0")

        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type.value)

        word_clauses = []
        for w in cleaned_words[:5]:
            word_clauses.append("(LOWER(source_text) LIKE ? OR LOWER(nadi_9_text) LIKE ? OR LOWER(raw_json) LIKE ?)")
            pat = f"%{w}%"
            params.extend([pat, pat, pat])

        if word_clauses:
            conditions.append(f"({' OR '.join(word_clauses)})")

        where_stmt = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM evidence_items
            {where_stmt}
            ORDER BY reliability_weight DESC
            LIMIT ?
        """
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_item(r) for r in rows]

    def get_all_conflicts(self) -> List[EvidenceConflict]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM evidence_conflicts").fetchall()
            return [
                EvidenceConflict(
                    conflict_id=r["conflict_id"],
                    concept=r["concept"],
                    source_a_ref=r["source_a_ref"],
                    claim_a=r["claim_a"],
                    source_b_ref=r["source_b_ref"],
                    claim_b=r["claim_b"],
                    confidence_delta=r["confidence_delta"],
                    resolution=r["resolution"],
                    rationale=r["rationale"],
                )
                for r in rows
            ]

    def _row_to_item(self, row: sqlite3.Row) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=row["evidence_id"],
            source_type=SourceType(row["source_type"]),
            source_name=row["source_name"],
            author=row["author"],
            date=row["date"],
            reliability_weight=row["reliability_weight"],
            source_text=row["source_text"],
            nadi_9_text=row["nadi_9_text"],
            raw_payload=json.loads(row["raw_json"]),
        )
