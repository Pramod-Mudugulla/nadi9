# AI Collaboration Log

This log documents how AI engineering tools were utilized during the design and implementation of the **Nadi-9 Dialect Agent**, the audit procedures applied to verify code correctness, and specific AI suggestions that were consciously rejected.

---

## 1. AI Assistance Breakdown

| Phase | Tool Used | Purpose / Assistance |
| :--- | :--- | :--- |
| **Linguistic Schema Design** | Claude / LLM | Drafting realistic dialect vocabulary entries and plausible grammatical variations for Nadi-9. |
| **Boilerplate & Models** | Codex / Copilot | Accelerating Pydantic model scaffolding and SQLite database table definitions. |
| **Verification Algorithms** | Assistant Pair-Programming | Developing regex tokenizers and characters-per-second (CPS) subtitle reading speed calculators. |
| **Test Suite Generation** | Assistant Pair-Programming | Scaffolding Pytest test cases for conflict detection, failure modes, and budget assertions. |

---

## 2. Verification and Quality Audits

All AI-generated code was treated as unverified candidate input. The following validation checks were systematically applied:

1. **Independent Verification of Business Logic:**
   - AI-suggested regex patterns for Nadi-9 affixes were tested against edge cases (e.g. nested prefixes like `ni-` combined with suffixes like `-ren` or `-ka`).
   - We verified that the mock provider never leaked future knowledge (e.g. ensuring `toran-ya` was not exposed prior to Dr. Sen's correction).

2. **Budget and Resource Auditing:**
   - An early AI iteration placed redundant LLM calls on every line during verification. We audited the call graph and restricted LLM auditor invocations to lines with uncertainty or detected issues, conserving budget.

3. **Runtime Execution & Test Suite:**
   - 100% of test suites (`pytest tests/ -v`) were executed locally on Python 3.13 to confirm passing status before commit.

---

## 3. AI Suggestions Specifically Rejected

### Suggestion 1: Single-Prompt Monolithic Translation
- **What the AI Suggested:**  
  *“Just put all dictionaries, grammar notes, and transcript lines into one big prompt with GPT-4o and ask it to translate the whole episode at once. It's much simpler and requires no database.”*
- **Why We Rejected It:**  
  - It creates an **opaque, un-auditable black box** with no machine-readable provenance.
  - When evidence is missing, LLMs naturally fill gaps with convincing hallucinations rather than abstaining.
  - Selective replanning becomes impossible: correcting one rule would require re-running the entire episode at full cost.

### Suggestion 2: Blindly Trusting Dictionary A Due to Size
- **What the AI Suggested:**  
  *“Dictionary A has 100+ entries while Dictionary B has only 20. We should treat Dictionary A as primary and use Dictionary B only as a fallback.”*
- **Why We Rejected It:**  
  - Large vendor-scraped glossaries often contain uncurated noise and deliberate poison traps (e.g. `baxu`).
  - Native speaker interviews (INT-01 to INT-05) and community glossaries (Dictionary B) represent living oral speech and must take precedence over unvetted vendor text dumps.

### Suggestion 3: Inventing Plausible Fictional Words for Technical Terms
- **What the AI Suggested:**  
  *“For 'pneumatic gearbox', we can generate a cool sounding Nadi-9 word like 'vayu-chakka' so all subtitles pass verification.”*
- **Why We Rejected It:**  
  - This directly violates the core evaluation criteria of the assignment: **Reasoning under uncertainty, not translation fluency.**
  - Inventing words pretends knowledge that does not exist in the evidence pack. The agent must honestly output `[INSUFFICIENT_EVIDENCE]` and formulate a human review question.
