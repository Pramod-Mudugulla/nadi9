# Nadi-9 Dialect Agent
> **"Learn a Dialect That Does Not Exist"**  
> An evidence-grounded agentic system that learns a fictional language from limited, conflicting references, translating subtitles with verifiable provenance without hallucinating missing knowledge.

---

## 1. Overview & Architecture

When translating a dialect that exists nowhere on the internet, an AI model cannot rely on pre-trained knowledge. It must act like a **cautious junior field linguist**:
1. It must never invent words when evidence is lacking.
2. It must explicitly track evidence and source conflicts.
3. It must allow an independent verification layer to disagree with its translations.
4. When new evidence or corrections arrive, it must selectively replan only the affected lines.

```text
                         ┌──────────────────────┐
                         │     Evidence Pack    │
                         │                      │
                         │ • examples           │
                         │ • dictionaries       │
                         │ • grammar            │
                         │ • expert notes       │
                         │ • interviews         │
                         │ • episode transcript │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Evidence Ingestion │
                         │                      │
                         │ parse / normalize    │
                         │ assign source IDs    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Evidence Store    │
                         │                      │
                         │ SQLite + metadata    │
                         │ precedence scoring   │
                         │ conflict detection   │
                         └──────────┬───────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
            ┌─────────────────┐          ┌─────────────────┐
            │ Hypothesis      │          │ Episode         │
            │ Builder         │          │ Analyzer        │
            └────────┬────────┘          └────────┬────────┘
                     │                            │
                     └─────────────┬──────────────┘
                                   ▼
                         ┌──────────────────────┐
                         │   Translation Agent  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Independent         │
                         │  Verification Layer  │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                       PASS              HUMAN_REVIEW
                         │                     │
                         ▼                     ▼
                    subtitles.srt         review_queue.json
```

---

## 2. Quickstart & Installation

### Requirements
- Python 3.10+
- Dependencies: `pydantic`, `pytest`, `rich`, `python-dotenv`

```bash
# 1. Clone repository and navigate to directory
git clone <repo-url>
cd nadi9-agent

# 2. Install dependencies
pip install -r requirements.txt
```

### Run Full Pipeline (Zero Configuration / Offline Mode)
The project includes a **deterministic mock provider** by default. Evaluators can run the entire pipeline immediately without needing personal API keys:

```bash
python -m src.nadi9.cli run
```

### Run Automated Test Suite
Runs tests for conflict detection, poisoned term rejection, mechanical term abstention, selective correction replanning, provider recovery, and prompt injection defense:

```bash
python -m pytest tests/ -v
```

### Test Selective Replanning On Live Correction
Simulates a field linguist submitting a correction halfway through the run:

```bash
python -m src.nadi9.cli correct
```

### Inspect Audit Trail for a Subtitle
Demonstrate exactly what evidence, assumptions, and verification notes backed any subtitle:

```bash
python -m src.nadi9.cli inspect S014
```

---

## 3. How the Pipeline Works (Beginner to Intermediate Explanation)

If you're explaining this architecture in an interview, here is the clear 5-step narrative:

### Step 1: Ingestion & Source Precedence (`EvidenceAgent` & `EvidenceRetriever`)
- Raw materials (field interviews, vendor dictionaries, community glossaries, grammar notes) are ingested and assigned unique inspectable IDs (e.g. `example:E07`, `dict_b:term-19`).
- We assign **source precedence priors**:
  - Community Linguist / Living Interviews: **0.88 - 0.92**
  - Vendor Dictionary A (automated scrape): **0.65**
- Conflicting claims are flagged immediately. For instance:
  - *Elder brother:* Dictionary A says `koba` (vendor slang), while Dictionary B and interviews say `toran` (respectful kinship).
  - *Water:* Dictionary A has poisoned entry `baxu`, while interviews and examples use `dara`.

### Step 2: Hypothesis Formation & Counterexample Tracking (`HypothesisAgent`)
- Instead of treating language rules as universal truths, the agent generates testable hypotheses (e.g. *Subject-Object-Verb* syntax, preverbal `ni-` negation).
- It verifies these rules against all 20 approved examples.
- **Critical behavior:** When an example disagrees (such as `E20` using inverted word order), the agent **does not ignore it**. It records `E20` as a counterexample and lowers the rule's calibrated confidence.

### Step 3: Evidence-Bounded Translation (`TranslationAgent`)
- When translating lines from `episode_transcript.json`, the translator queries the Evidence Store.
- If terms are missing (such as *"pneumatic gearbox"* in S008), the translator **abstains**:
  - Outputs `[INSUFFICIENT_EVIDENCE]`
  - Sets confidence to `0.15`
  - Routes directly to human review with an actionable question for the dialect expert.

### Step 4: Independent Verification Layer (`VerificationAgent`)
- **Anti-confirmation bias rule:** The verification layer is completely separate from the translation prompt.
- It runs three deterministic checks:
  1. *Vocabulary Check:* Verifies every word stem against known oral tokens; catches poisoned terms like `baxu`.
  2. *Grammar Check:* Enforces SOV object positioning and checks for illegal double negations.
  3. *Consistency & Speed:* Checks characters-per-second (CPS < 20) for broadcast readability and enforces generational honorifics (`-ma`).
- Only lines with uncertainty or detected conflicts invoke the auditor LLM.

### Step 5: Selective Replanning on Correction
- When Dr. Sen's correction (`CORR-2024-09`) arrives for reconciliation kinship:
  - The system updates rule `RULE-KIN-03`.
  - It uses an invalidation map to identify that **only S014** is affected.
  - It reruns translation and verification **only for S014**, saving computational budget and avoiding unnecessary reprocessing.

---

## 4. Key Interview Questions & Talking Points

During your interview discussion (Section 10 of the assignment brief), use these concise answers:

### Q1: How does your agent decide that a source is trustworthy?
> **Answer:** *"We apply an explicit Bayesian-style source precedence hierarchy rather than trusting file size or recency. Living native speaker audio interviews (INT-01 to INT-05) and community linguist field notes (Dictionary B) receive high baseline priors (0.88-0.92). Broad vendor dictionaries (Dictionary A) receive a discounted prior (0.65) because vendor harvesters frequently include archaic forms or poisoned entries. When two sources disagree, empirical oral evidence overrides static glossaries."*

### Q2: How would you detect that the verifier is repeating the translator's mistake?
> **Answer:** *"First, we enforce cognitive diversity: the verifier does not receive the translator's chain-of-thought, preventing confirmation bias. Second, the verifier runs deterministic code assertions (token whitelisting, SOV syntax parsing, and CPS reading speed) before any LLM is called. Third, we measure agreement rates across diverse test sets—if an LLM verifier approves lines that violate deterministic lexical or syntactic constraints, we flag verifier failure and trigger human escalation."*

### Q3: What changes when a linguist corrects one grammar rule?
> **Answer:** *"We implement dependency-aware selective invalidation. Each subtitle decision records which rules and evidence IDs it depended on. When a rule is modified, our workflow queries the dependency graph and reruns translation and verification strictly for affected lines (e.g. S014). Unaffected lines remain untouched, preserving execution state and keeping budget consumption well below our 25-call ceiling."*

### Q4: Which decisions should never be automated?
> **Answer:** *"Three decisions must always remain with human experts:
> 1. Resolving unresolved sociolinguistic disputes between community elders and external vendors.
> 2. Introducing novel loanwords or technical neologisms where no cultural precedent exists in the dialect.
> 3. Final broadcast approval for scenes involving sacred ceremonies, legal terms, or intense emotional conflict."*

### Q5: How would the system work for 5,000 episodes and 40 dialects?
> **Answer:** *"We would transition our SQLite Evidence Store to a partitioned vector database (e.g. pgvector or Qdrant) with dialect namespaces. Rule dependency graphs would be maintained in an asynchronous task queue (such as Celery or Temporal). Once a dialect's confidence matrix stabilizes across the first 50 episodes, the system shifts into a high-throughput mode where only anomalous or low-confidence lines (>95th percentile CPS or new lexemes) are routed to human linguists, achieving massive cost and latency efficiency."*

### Q6: What did an AI coding assistant suggest that you chose not to accept?
> **Answer:** *"An AI assistant initially suggested running a single massive prompt that ingested all raw materials and translated the episode in one shot, claiming it would be 'fast and simple'. We rejected that approach because it creates an un-auditable black box, hallucinated plausible-sounding Nadi-9 words when evidence was missing, and could not selectively replan when a single rule changed. Instead, we insisted on an inspectable multi-agent architecture with deterministic verification."*

---

## 5. Repository Structure

```text
nadi9-agent/
│
├── README.md                 # Project guide & interview explanation
├── ARCHITECTURE.md           # System design & trust boundaries
├── AI_COLLABORATION.md       # AI assistant audit log & rejected suggestions
├── KNOWN_LIMITATIONS.md      # Deliberate design bounds & future work
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables
│
├── data/
│   ├── raw/                  # Evidence pack (examples, dictionaries, grammar, interviews)
│   ├── processed/            # SQLite evidence store & indexed entries
│   └── scenarios/            # Test scenarios (linguist correction, prompt injection)
│
├── src/
│   └── nadi9/
│       ├── agents/           # Evidence, Hypothesis, Translation, Verification agents
│       ├── graph/            # Workflow orchestrator & replanning engine
│       ├── models/           # Domain data models (Evidence, Hypothesis, Subtitle, State)
│       ├── retrieval/        # SQLite store & prompt injection defense
│       ├── verification/     # Deterministic vocabulary, grammar & consistency checkers
│       ├── providers/        # LLM provider abstraction (Mock & Live)
│       └── cli.py            # Command-line interface
│
├── tests/
│   ├── test_conflict.py      # Verifies conflict detection & poisoned term rejection
│   ├── test_unsupported_term.py # Verifies abstention on unseen machine terms
│   ├── test_correction.py    # Verifies selective replanning on linguist correction
│   └── test_tool_failure.py  # Verifies retry resilience & prompt injection defense
│
└── sample_run/
    ├── subtitles.srt         # Broadcast-ready SubRip subtitle file
    ├── subtitle_decisions.jsonl # Section 4 machine-readable audit logs
    ├── learned_rules.json    # Extracted linguistic hypotheses & counterexamples
    ├── review_queue.json     # Escalated questions for language experts
    └── final_report.md       # Release recommendation report
```
