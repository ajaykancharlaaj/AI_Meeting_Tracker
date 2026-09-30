# AI Meeting Action Tracker
### Multi-Agent Meeting Intelligence System  
### with Cross-Meeting Task Entity Resolution and Dependency-Aware Risk Assessment

---

## 1. Research Problem Statement

> **"Evidence-Aware Temporal Reconstruction of Project Task State from Multi-Meeting Conversations."**

This is **not** a meeting summarizer, speech-to-text tool, simple task extractor, reminder app, or CRUD task manager.

The core engineering challenge is: given a series of project meetings where the same task is discussed repeatedly over weeks — under different names, with changing owners, shifting deadlines, and evolving states — reconstruct the **true current state** of every task, with full historical evidence and traceable reasoning.

### The Multi-Meeting Identity Problem

The same task can appear across meetings under many surface forms:

| Meeting | Speaker Says | System Must Infer |
|---------|-------------|-------------------|
| M1 | *"We need to develop the login module."* | → **T001** created, state = ASSIGNED |
| M2 | *"I've implemented most of the authentication functionality."* | → **T001** resolved, state = IN_PROGRESS (70%) |
| M3 | *"The login work is blocked — the auth API isn't ready."* | → **T001** updated, state = BLOCKED |
| M4 | *"The login module is completed."* | → **T001** updated, state = COMPLETED |
| M5 | *"We found another issue in login, we need to fix it."* | → **T001** updated, state = REOPENED |

The system must **not** create T002, T003, T004, T005. It must recognize all of these as the same task entity and maintain its complete history.

---

## 2. System Architecture

```
Meeting Transcript (multi-speaker, timestamped)
            │
            ▼
 ┌─────────────────────────────────────┐
 │      Information Extraction          │
 │  task_extractor.py                   │
 │  progress_extractor.py               │
 │  deadline_normalizer.py              │
 └─────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────┐
 │    Cross-Meeting Entity Resolution   │
 │  semantic_matcher.py                 │
 │  (Sentence-Transformers + cosine)    │
 │  Multi-factor: semantic + action +   │
 │  owner + context + keywords          │
 └─────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────┐
 │      Persistent Task Memory          │
 │  memory/task_memory.py               │
 │  Stable T001/T002 IDs                │
 │  State history, deadline history,    │
 │  owner history, alias tracking       │
 └─────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────┐
 │    Temporal State Reconstruction     │
 │  state_reconstructor.py              │
 │  Contradiction detection             │
 │  Uncertainty analysis                │
 │  Evidence-aware state transitions    │
 └─────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────┐
 │    Dependency Graph + Risk           │
 │  dependency_extractor.py             │
 │  dependency_analyzer.py              │
 │  risk_analyzer.py                    │
 │  Propagation-aware risk scores       │
 └─────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────┐
 │     Structured JSON API Output       │
 │  pipeline.py / service.py            │
 │  Tasks + Dependencies + Risks +      │
 │  Contradictions + Evidence Timeline  │
 └─────────────────────────────────────┘
```

---

## 3. Module Structure

```
ai_module/
├── pipeline.py                    # MeetingIntelligenceEngine + run_pipeline() (compat)
├── service.py                     # MeetingTrackerService — clean backend API facade
├── demo.py                        # 4-meeting end-to-end demo
├── main.py                        # Entry point (extendable)
│
├── extraction/
│   ├── task_extractor.py          # Rule-based extraction: tasks, decisions, blockers,
│   │                              #   progress, uncertainty, speaker, timestamp
│   ├── deadline_normalizer.py     # NL deadline → YYYY-MM-DD (weekdays, relative dates,
│   │                              #   deadline change detection)
│   └── progress_extractor.py     # Explicit % and qualitative progress labeling
│
├── entity_resolution/
│   ├── semantic_matcher.py        # Sentence-Transformers all-MiniLM-L6-v2 + embedding
│   │                              #   cache + multi-factor resolve_task_identity()
│   └── task_matcher.py            # Legacy Jaccard matcher (preserved for compat)
│
├── state_reconstruction/
│   ├── state_reconstructor.py     # reconstruct_task_state(), analyze_uncertainty(),
│   │                              #   detect_state_contradictions_rich(),
│   │                              #   format_evidence_timeline()
│   └── task_memory.py             # Re-exports TaskMemory from memory package
│
├── memory/
│   ├── task_memory.py             # Canonical TaskMemory with stable T001 IDs,
│   │                              #   state/deadline/owner history, alias tracking
│   ├── meeting_memory.py          # Per-meeting record storage
│   └── repository.py              # Abstract + InMemory + JsonFile repositories
│
├── risk/
│   ├── dependency_extractor.py    # Dependency pattern extraction
│   ├── dependency_analyzer.py     # DAG builder + downstream task traversal
│   └── risk_analyzer.py           # Risk scoring with propagation, deadlines,
│                                  #   repeated-unresolved factor, risk_reasons
│
├── schemas/
│   ├── models.py                  # All data models: TaskState, EvidenceRecord,
│   │                              #   ProgressInfo, ContradictionRecord, RiskRecord, etc.
│   └── __init__.py                # Public exports
│
└── evaluation/
    ├── eval_dataset.py            # 5-meeting simulated dataset + GROUND_TRUTH
    └── evaluator.py               # 11-metric automated evaluator → evaluation_report.json

tests/
├── test_suite_16.py               # 16 required test cases (ALL PASS)
├── test_task_extractor.py
├── test_entity_resolution.py
├── test_state_reconstruction.py
├── test_contradictions.py
├── test_uncertainty.py
├── test_dependency_extraction.py
├── test_dependency_analysis.py
├── test_deadline_normalizer.py
├── test_deadline_risk.py
├── test_risk_analysis.py
├── test_task_memory.py
├── test_multi_meeting_intelligence.py
├── test_multi_meeting_state.py
├── test_combined_state.py
└── test_combined_risk.py
```

---

## 4. Key Features

### 4.1 Cross-Meeting Task Entity Resolution
- **Semantic similarity** via `sentence-transformers/all-MiniLM-L6-v2`
- **Multi-factor scoring**: semantic + action compatibility + keyword overlap + owner + project context
- **Confidence-based matching** — never forces a match below threshold
- **Alias tracking** — all surface forms of a task are stored

```json
{
  "matched_existing_task_id": "T001",
  "match_confidence": 0.91,
  "match_reason": ["high semantic similarity", "same owner", "compatible action"],
  "requires_review": false
}
```

### 4.2 Task State Machine

Supported states and transitions:

```
ASSIGNED ──► IN_PROGRESS ──► COMPLETED ──► REOPENED
                │                              │
                ▼                              ▼
             BLOCKED ──────────────► IN_PROGRESS
                │
                ▼
            CANCELLED
```

All state transitions are stored with evidence (meeting ID, speaker, timestamp, transcript text, confidence).

### 4.3 Evidence-Aware Processing

Every fact is traceable:

```json
{
  "meeting_id": "M4",
  "speaker": "Rahul",
  "timestamp": "00:32:15",
  "text": "The login module is completed.",
  "evidence_type": "state_update",
  "confidence": 0.96
}
```

### 4.4 Progress Extraction

| Input | Extracted |
|-------|-----------|
| `"50% completed"` | `{progress_value: 50, progress_type: "explicit_percentage", confidence: 0.98}` |
| `"almost finished"` | `{progress_label: "almost_complete", progress_type: "qualitative"}` |
| `"mostly done"` | `{progress_label: "mostly_done", progress_type: "qualitative"}` |

Explicit percentages are **never invented** for qualitative statements.

### 4.5 Deadline Intelligence

- Extracts explicit dates, weekday references, relative expressions
- Detects deadline changes: `"deadline moved to Monday"` → `change_type: "deadline_changed"`
- Stores full `deadline_history` without losing prior deadlines

### 4.6 Contradiction Detection

```json
{
  "type": "state_contradiction",
  "task_id": "T001",
  "claims": [
    {"meeting_id": "M4", "state": "COMPLETED"},
    {"meeting_id": "M5", "state": "IN_PROGRESS"}
  ],
  "requires_review": true
}
```

### 4.7 Uncertainty Modelling

| Statement | Certainty |
|-----------|-----------|
| `"The login module is completed."` | `certain` (confidence: 0.95+) |
| `"I think it's almost done."` | `uncertain` (confidence: 0.65) |
| `"It might be completed by Friday."` | `speculative` (confidence: 0.4) |

### 4.8 Dependency Graph + Risk Analysis

- Extracts directed dependency relationships from natural language
- Builds a DAG with topological risk propagation
- Computes risk scores factoring: deadline proximity, blockers, repeated unresolved status, downstream impact

---

## 5. Quickstart

### Prerequisites

```bash
# Python 3.11 in .venv
.venv\Scripts\activate

# Install dependencies
pip install sentence-transformers scipy
```

> **Note:** The sentence-transformers model (`all-MiniLM-L6-v2`) must be cached locally.  
> Set `HF_HUB_OFFLINE=1` to prevent unnecessary network requests.

### Run the Demo

```powershell
$env:PYTHONPATH = "."; $env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe ai_module/demo.py
```

The demo simulates 4 meetings following T001 (Login Module) through:  
**ASSIGNED → IN_PROGRESS (50%) → BLOCKED → COMPLETED**

### Run the Full Pipeline (Programmatic)

```python
from ai_module.pipeline import MeetingIntelligenceEngine

engine = MeetingIntelligenceEngine()

transcript_m1 = [
    {"speaker": "Rahul", "text": "We need to develop the login module.", "segment_id": "M1-S01"},
]
result_m1 = engine.process_meeting("M1", transcript_m1, reference_date="2026-09-01")
print(result_m1["tasks"])

transcript_m2 = [
    {"speaker": "Rahul", "text": "I've implemented most of the authentication functionality.", "segment_id": "M2-S01"},
]
result_m2 = engine.process_meeting("M2", transcript_m2, reference_date="2026-09-05")
# T001 state: IN_PROGRESS — recognized as same task
```

### Use the Backend Service Layer

```python
from ai_module.service import MeetingTrackerService

svc = MeetingTrackerService()
result = svc.process_meeting("M1", transcript, reference_date="2026-09-01")

tasks     = svc.get_current_tasks()
risks     = svc.get_risks()
deps      = svc.get_dependencies()
conflicts = svc.get_contradictions()
summary   = svc.get_manager_summary()
```

### Incremental (Real-Time) Chunk Processing

```python
from ai_module.pipeline import process_transcript_chunk, finalize_meeting

# Stream chunks as transcript arrives
process_transcript_chunk("M1", "Rahul", "00:01:00",
                          "We need to develop the login module.", "M1-S01", "2026-09-01")
process_transcript_chunk("M1", "Priya", "00:02:00",
                          "Agreed. Rahul, deadline is Friday.", "M1-S02", "2026-09-01")

# Finalize when meeting ends
result = finalize_meeting("M1", "2026-09-01")
```

---

## 6. API Output Contract

Each `process_meeting()` call returns a structured JSON object:

```json
{
  "meeting_id": "M1",
  "reference_date": "2026-09-01",
  "tasks": [
    {
      "task_id": "T001",
      "description": "develop login module",
      "canonical_description": "develop login module",
      "aliases": ["authentication functionality", "login work"],
      "owner": "Rahul",
      "state": "In Progress",
      "progress": { "progress_value": 50, "progress_type": "explicit_percentage" },
      "deadline": "2026-09-05",
      "deadline_history": [
        { "deadline": "2026-09-05", "meeting_id": "M1", "change_type": "initial" },
        { "deadline": "2026-09-08", "meeting_id": "M2", "change_type": "deadline_changed" }
      ],
      "dependencies": ["T002"],
      "state_history": [
        { "state": "Assigned", "meeting_id": "M1", "speaker": "Rahul", "evidence_text": "We need to develop the login module." },
        { "state": "In Progress", "meeting_id": "M2", "speaker": "Rahul", "evidence_text": "I've implemented most of the authentication functionality." }
      ],
      "evidence": [
        { "meeting_id": "M1", "speaker": "Rahul", "timestamp": "00:00:00", "text": "...", "confidence": 0.9 }
      ],
      "confidence": 0.91,
      "is_uncertain": false,
      "certainty": "certain",
      "created_meeting_id": "M1",
      "last_updated_meeting": "M2"
    }
  ],
  "decisions": [],
  "blockers": [],
  "dependencies": [
    { "from_task": "T002", "to_task": "T001", "dependency_text": "Login depends on auth API" }
  ],
  "risks": [
    {
      "task_id": "T001",
      "description": "develop login module",
      "risk_level": "HIGH",
      "risk_score": 0.75,
      "risk_reasons": ["blocked", "dependency on unresolved task"],
      "deadline_status": "overdue"
    }
  ],
  "contradictions": [],
  "evidence_timeline": "...",
  "meeting_count": 2,
  "status": "ok"
}
```

---

## 7. Running Tests

```powershell
# Set required env vars
$env:PYTHONPATH = "."
$env:HF_HUB_OFFLINE = "1"

# Run all 16 required test cases
.\.venv\Scripts\python.exe ai_module/tests/test_suite_16.py -v

# Run all original test files
Get-ChildItem ai_module/tests/ -Filter test_*.py | ForEach-Object {
    & .\.venv\Scripts\python.exe $_.FullName
}
```

### Test Coverage (31 tests total — ALL PASS)

| Suite | Count | Status |
|-------|-------|--------|
| Core pipeline tests (original) | 15 | ✅ PASS |
| Required 16-test suite | 16 | ✅ PASS |
| **Total** | **31** | ✅ **ALL PASS** |

#### Test Suite 16 — Required Cases

| # | Test | Status |
|---|------|--------|
| 1 | Same task, different wording → entity resolved | ✅ |
| 2 | Different tasks, similar wording → NOT merged | ✅ |
| 3 | State transition: ASSIGNED → IN_PROGRESS | ✅ |
| 4 | State transition: IN_PROGRESS → BLOCKED | ✅ |
| 5 | State transition: BLOCKED → IN_PROGRESS | ✅ |
| 6 | State transition: IN_PROGRESS → COMPLETED | ✅ |
| 7 | State transition: COMPLETED → REOPENED | ✅ |
| 8 | Deadline changed — history preserved | ✅ |
| 9 | Contradictory statements detected | ✅ |
| 10 | Uncertain statement → lower confidence | ✅ |
| 11 | Dependency propagation (T1 → T2 → T3 → T4) | ✅ |
| 12 | Repeated unresolved task detected | ✅ |
| 13 | Low-confidence match → not forced | ✅ |
| 14 | Missing owner handled gracefully | ✅ |
| 15 | Missing deadline handled gracefully | ✅ |
| 16 | Incremental transcript chunk streaming | ✅ |

---

## 8. Automated Evaluation

```powershell
$env:PYTHONPATH = "."; $env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe ai_module/evaluation/evaluator.py
```

### Evaluation Results (5-Meeting Dataset, 9+ Metrics)

| Metric | Score | Status |
|--------|-------|--------|
| task_identity_f1 | 100.0% | ✅ PASSED |
| task_identity_precision | 100.0% | ✅ PASSED |
| task_identity_recall | 100.0% | ✅ PASSED |
| state_accuracy | 100.0% | ✅ PASSED |
| state_transition_f1 | 80.0% | ✅ PASSED |
| deadline_accuracy | 100.0% | ✅ PASSED |
| evidence_f1 | 100.0% | ✅ PASSED |
| dependency_f1 | 100.0% | ✅ PASSED |
| contradiction_detection_f1 | 100.0% | ✅ PASSED |
| current_state_accuracy | 100.0% | ✅ PASSED |
| timeline_accuracy | 100.0% | ✅ PASSED |

> Machine-readable results saved to `evaluation_report.json` after each run.

---

## 9. Core Interfaces Reference

### `run_pipeline()` — Backward-Compatible Single-Meeting

```python
from ai_module.pipeline import run_pipeline

result = run_pipeline(
    transcript=[{"speaker": "...", "text": "...", "segment_id": "..."}],
    meeting_id="M1",
    reference_date="2026-09-01",
    existing_tasks=[]   # optional: carry over tasks from previous meeting
)
```

### `find_best_semantic_match()` — Legacy Entity Matcher

```python
from ai_module.entity_resolution.semantic_matcher import find_best_semantic_match

match = find_best_semantic_match(new_task, existing_tasks, threshold=0.72)
# Returns: {"matched_existing_task_id": "T001", "match_confidence": 0.91}
```

### `resolve_task_identity()` — Full Multi-Factor Matcher

```python
from ai_module.entity_resolution.semantic_matcher import resolve_task_identity

result = resolve_task_identity(new_task, existing_tasks, threshold=0.72)
# Returns: {"matched_existing_task_id": "T001", "match_confidence": 0.91,
#           "match_reason": [...], "requires_review": False}
```

### `reconstruct_task_state()` — State Reconstruction

```python
from ai_module.state_reconstruction.state_reconstructor import reconstruct_task_state

state_info = reconstruct_task_state(task_items)
# Returns: {"current_state": "IN_PROGRESS", "is_blocked": False, ...}
```

### `extract_meeting_items()` — Information Extraction

```python
from ai_module.extraction.task_extractor import extract_meeting_items

items = extract_meeting_items(segments, meeting_id, reference_date)
# Returns: {"tasks": [...], "decisions": [...], "blockers": [...]}
```

---

## 10. Technical Stack

| Component | Technology |
|-----------|-----------|
| Semantic Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Similarity | Cosine similarity (scipy / numpy) |
| NLP Extraction | Rule-based regex + semantic scoring |
| State Machine | Custom Python dataclasses + enum |
| Persistence | In-memory + JSON file repository |
| Language | Python 3.11 |
| Testing | `unittest` (standard library) |

---

## 11. Design Principles

1. **Evidence-first**: Every state change, deadline update, and owner assignment is stored with its source (meeting ID, speaker, timestamp, transcript text).
2. **No forced matches**: Entity resolution uses confidence thresholds. Low-confidence matches are flagged for review rather than silently merged.
3. **No silent choices**: Contradictions between speakers/meetings are surfaced explicitly, not resolved by picking one silently.
4. **No invented facts**: Uncertainty is preserved. `"I think it's almost done"` does not become `progress_value: 90, confidence: 0.99`.
5. **Non-destructive updates**: Every meeting update appends to history. Previous states, deadlines, and owners are never deleted.
6. **Backward compatibility**: All original module interfaces (`run_pipeline`, `find_best_semantic_match`, `extract_dependency_statement`, etc.) are fully preserved.

---

## 12. SIH / Final-Year Project Context

This system demonstrates the following research contributions:

- **Cross-document entity resolution** applied to multi-meeting project conversations
- **Temporal state machine** with evidence-aware transitions and contradiction handling
- **Dependency-aware risk propagation** in a project knowledge graph
- **Uncertainty quantification** in natural language understanding
- **Incremental streaming inference** for real-time meeting processing
- **Structured JSON API** suitable for integration with backend dashboards

The architecture is designed to be extended with:
- Real speech-to-text input (STT module placeholder exists in `stt/`)
- LLM-enhanced entity resolution (current rule-based + semantic approach is backend-agnostic)
- REST API wrapper (Django / FastAPI) consuming `MeetingTrackerService`
- Frontend dashboard consuming the structured JSON output contract
