"""
Temporal State Reconstruction and Contradiction / Uncertainty Analysis.

Reconstructs the chronological progression of task state across multi-meeting dialogues,
detects state contradictions (e.g. Completed -> Incomplete without resolution),
quantifies linguistic uncertainty, and builds evidence-backed transition timelines.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


def detect_uncertainty(text: str) -> bool:
    """
    Detect whether a task-state statement contains uncertainty.
    Uses word boundaries (\\b) to prevent matching 'may' inside 'Maya'.
    """
    if not text:
        return False
    pattern = r"\b(maybe|may|probably|possibly|might|likely|i think|i believe|not sure|perhaps)\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def analyze_uncertainty(text: str) -> Dict[str, Any]:
    """
    Distinguish between Certain, Uncertain, and Speculative claims.
    """
    if not text:
        return {"certainty": "certain", "confidence": 1.0, "marker": None}

    speculative_pattern = r"\b(might|could be|perhaps|maybe)\b"
    uncertain_pattern = r"\b(may|probably|possibly|likely|i think|i believe|not sure|seems like)\b"

    spec_match = re.search(speculative_pattern, text, re.IGNORECASE)
    if spec_match:
        return {
            "certainty": "speculative",
            "confidence": 0.50,
            "marker": spec_match.group(1).lower(),
        }

    unc_match = re.search(uncertain_pattern, text, re.IGNORECASE)
    if unc_match:
        return {
            "certainty": "uncertain",
            "confidence": 0.65,
            "marker": unc_match.group(1).lower(),
        }

    return {"certainty": "certain", "confidence": 0.95, "marker": None}


def detect_contradictions(task_updates: list[dict]) -> list[dict]:
    """
    Detect contradictory or reversed task states across meetings.
    Maintains exact backward compatibility with test_contradictions.py.
    """
    sorted_updates = sorted(
        task_updates,
        key=lambda update: update.get("meeting_date") or update.get("meeting_id") or ""
    )

    contradictions = []

    normal_transitions = {
        ("Assigned", "In Progress"),
        ("Assigned", "Completed"),
        ("In Progress", "Completed"),
        ("In Progress", "Blocked"),
        ("Blocked", "In Progress"),
        ("Blocked", "Completed"),
        ("Not Started", "Assigned"),
        ("Not Started", "In Progress"),
        ("Reopened", "In Progress"),
        ("Reopened", "Completed"),
        ("Reopened", "Blocked"),
    }

    reversal_transitions = {
        ("Completed", "Incomplete"),
        ("Completed", "In Progress"),
        ("Completed", "Blocked"),
        ("Completed", "Reopened"),
        ("Incomplete", "Completed"),
        ("Reopened", "Completed"),
    }

    for index in range(1, len(sorted_updates)):
        previous = sorted_updates[index - 1]
        current = sorted_updates[index]

        previous_state = previous["state"]
        current_state = current["state"]
        transition = (previous_state, current_state)

        if transition in normal_transitions:
            continue

        if transition in reversal_transitions:
            contradictions.append({
                "from_state": previous_state,
                "to_state": current_state,
                "previous_meeting_id": previous.get("meeting_id"),
                "current_meeting_id": current.get("meeting_id"),
                "previous_source_segment_id": previous.get("source_segment_id"),
                "current_source_segment_id": current.get("source_segment_id"),
            })

    return contradictions


def detect_state_contradictions_rich(
    task_id: str,
    task_updates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Structured contradiction detection matching Section 10 contract.
    Detects when speakers or meetings make conflicting claims about task status.
    """
    sorted_updates = sorted(
        task_updates,
        key=lambda u: u.get("meeting_date") or u.get("meeting_id") or ""
    )
    rich_contradictions = []

    for i in range(1, len(sorted_updates)):
        prev = sorted_updates[i - 1]
        curr = sorted_updates[i]

        prev_state = prev.get("state")
        curr_state = curr.get("state")

        # Conflict check: Completed -> Incomplete or Completed -> In Progress
        if prev_state == "Completed" and curr_state in ("Incomplete", "In Progress"):
            rich_contradictions.append({
                "type": "state_contradiction",
                "task_id": task_id,
                "claims": [
                    {
                        "meeting_id": prev.get("meeting_id"),
                        "speaker": prev.get("speaker", "Unknown"),
                        "state": prev_state,
                        "text": prev.get("text") or prev.get("evidence", ""),
                        "timestamp": prev.get("timestamp", "00:00:00"),
                    },
                    {
                        "meeting_id": curr.get("meeting_id"),
                        "speaker": curr.get("speaker", "Unknown"),
                        "state": curr_state,
                        "text": curr.get("text") or curr.get("evidence", ""),
                        "timestamp": curr.get("timestamp", "00:00:00"),
                    },
                ],
                "requires_review": True,
                "explanation": f"Conflicting state claims between Meeting {prev.get('meeting_id')} ({prev_state}) and Meeting {curr.get('meeting_id')} ({curr_state}).",
            })

    return rich_contradictions


def reconstruct_task_state(task_updates: list[dict]) -> dict:
    """
    Reconstruct the chronological state of a task.
    Preserves exact backward-compatible structure while enriching history entries.
    """
    sorted_updates = sorted(
        task_updates,
        key=lambda update: update.get("meeting_date") or update.get("meeting_id") or ""
    )

    history = []
    transitions = []

    for index, update in enumerate(sorted_updates):
        text = update.get("text") or update.get("evidence") or ""
        uncertain = detect_uncertainty(text)

        history.append({
            "state": update["state"],
            "meeting_id": update["meeting_id"],
            "meeting_date": update.get("meeting_date", ""),
            "source_segment_id": update.get("source_segment_id"),
            "uncertain": uncertain,
            "speaker": update.get("speaker", ""),
            "timestamp": update.get("timestamp", "00:00:00"),
            "text": text,
        })

        if index > 0:
            previous_state = sorted_updates[index - 1]["state"]
            current_state = update["state"]

            if previous_state != current_state:
                transitions.append({
                    "from_state": previous_state,
                    "to_state": current_state,
                    "meeting_id": update["meeting_id"],
                    "meeting_date": update.get("meeting_date", ""),
                    "source_segment_id": update.get("source_segment_id"),
                    "speaker": update.get("speaker", ""),
                    "timestamp": update.get("timestamp", "00:00:00"),
                    "evidence": text,
                })

    contradictions = detect_contradictions(sorted_updates)
    current_state = history[-1]["state"] if history else None

    return {
        "history": history,
        "transitions": transitions,
        "contradictions": contradictions,
        "current_state": current_state,
    }


def format_evidence_timeline(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build a clean human-readable and API-friendly timeline of evidence
    showing: State Transition -> Speaker -> Meeting -> Timestamp -> Exact Quote.
    """
    timeline = []
    history = task.get("state_history") or task.get("history") or []

    for entry in history:
        timeline.append({
            "meeting_id": entry.get("meeting_id"),
            "meeting_date": entry.get("meeting_date"),
            "timestamp": entry.get("timestamp", "00:00:00"),
            "speaker": entry.get("speaker", task.get("owner", "Team")),
            "state": entry.get("state"),
            "quote": entry.get("evidence") or entry.get("text", ""),
            "uncertain": entry.get("uncertain", False),
        })

    return timeline