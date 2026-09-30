# Known Limitations & Intentional Trade-offs

This document outlines architectural scope bounds and features intentionally left incomplete within the recommended 10–12 hour implementation window.

---

## 1. Intentionally Incomplete Areas

### A. Raw Audio Transcription & Acoustic Modeling
- **Current State:** The system accepts structured transcript excerpts from native speaker interviews (`interviews.json`) rather than raw WAV/MP3 files.
- **Rationale:** The assignment brief emphasizes *reasoning under uncertainty, conflict resolution, and evidence tracking*, not acoustic signal processing or Whisper fine-tuning. Adding real-time speech-to-text models would introduce large binary dependencies (e.g. PyTorch, ffmpeg) without testing agentic reasoning.

### B. Dense Neural Embeddings & Vector Indexing
- **Current State:** The `EvidenceRetriever` uses SQLite with parameter-ranked lexical querying and Bayesian source-precedence weighting.
- **Rationale:** For an episode-sized corpus (under 500 total evidence tokens), lexical querying combined with metadata filters provides **100% deterministic reproducibility**, instant zero-dependency execution, and zero embedding API cost. In production with 50,000 lines, a vector database (e.g., pgvector) would be integrated.

### C. Web-Based User Interface
- **Current State:** Complete terminal CLI with rich formatted tables and machine-readable JSONL/SRT artifact exports.
- **Rationale:** As stated in Section 7 of the candidate brief: *"A working subtitle decision pipeline matters more than a polished user interface."*

### D. Complex Morphological Inflection Engine
- **Current State:** Morphological parsing handles prefixes (`ni-`), common tense markers (`-ka`, `-ren`, `-te`), and honorifics (`-ma`, `-ya`) using rule-based stemmers.
- **Rationale:** A full finite-state transducer (FST) or formal morphological analyzer (such as HFST) would require extensive linguist specification beyond the 6-page grammar note provided.

---

## 2. Production Scaling Roadmap (5,000 Episodes & 40 Dialects)

To transition this proof-of-concept into enterprise OTT infrastructure:
1. **Namespace Partitioning:** Partition the SQLite store into a distributed vector/relational database (e.g. PostgreSQL with pgvector) keyed by `(dialect_id, episode_id)`.
2. **Distributed Asynchronous Worker Graph:** Migrate `workflow.py` to an asynchronous orchestrator (Temporal or Celery) to support concurrent episode processing.
3. **Active Learning Feedback Loop:** When language experts resolve items in `review_queue.json`, human answers are automatically committed as `SourceType.LINGUIST_CORRECTION`, continuously enriching dialect memory.
