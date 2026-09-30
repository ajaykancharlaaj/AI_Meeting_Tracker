"""A robust information extraction module for meeting tasks, decisions, progress, and dependencies.

Extracts explicit tasks, owner commitments, deadlines, progress indicators,
uncertainty flags, and traceable evidence from transcript segments.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, List, Dict, Optional

from ai_module.extraction.deadline_normalizer import normalize_deadline, detect_deadline_change
from ai_module.extraction.progress_extractor import extract_progress
from ai_module.state_reconstruction.state_reconstructor import detect_uncertainty

# Core regex patterns for explicit task assignments and commitments
ASSIGNMENT_PATTERN = re.compile(
    r"(?P<owner>[A-Z][a-z]+),\s*please\s+(?P<description>.+?)(?:\.\s*You will own|\.)",
    re.IGNORECASE,
)
THIRD_PERSON_ASSIGNMENT = re.compile(
    r"\b(?P<owner>[A-Z][a-z]+)\s+(?:will|is going to|shall)\s+(?P<description>[^.]+)",
    re.IGNORECASE,
)
PASSIVE_ASSIGNMENT = re.compile(
    r"\b(?P<description>[^.]+?)\s+(?:has been|is)\s+assigned to\s+(?P<owner>[A-Z][a-z]+)",
    re.IGNORECASE,
)
DEADLINE_PATTERN = re.compile(r"\b(?:due by|due on|due|by)\s+(?P<deadline>[^.]+)", re.IGNORECASE)
COMMITMENT_PATTERN = re.compile(r"\bI will\s+(?P<description>[^.]+)", re.IGNORECASE)
COMMITMENT_DEADLINE_PATTERN = re.compile(r"\bby\s+(?P<deadline>[^.]+)", re.IGNORECASE)
DEPENDENCY_PATTERN = re.compile(
    r"(?:the\s+)?(?P<task>.+?)\s+depends on\s+(?P<dependency>[^.]+)",
    re.IGNORECASE,
)


def _new_task(
    task_id: str,
    description: str,
    segment_id: str,
    meeting_id: str,
    *,
    owner: str | None = None,
    deadline: str | None = None,
    state: str | None = None,
    depends_on: list[str] | None = None,
    speaker: str | None = None,
    timestamp: str = "00:00:00",
    text: str = "",
    progress: dict | None = None,
    uncertain: bool = False,
    confidence: float = 0.90,
) -> dict[str, Any]:
    """Build one task in the AI-to-backend contract shape."""
    return {
        "task_id": task_id,
        "matched_existing_task_id": None,
        "match_confidence": 0.0,
        "description": description.strip(),
        "owner": owner,
        "deadline": deadline,
        "state": state,
        "progress": progress,
        "depends_on": depends_on or [],
        "source_segment_id": segment_id,
        "meeting_id": meeting_id,
        "speaker": speaker,
        "timestamp": timestamp,
        "evidence_text": text,
        "uncertain": uncertain,
        "confidence": confidence,
    }


def extract_meeting_items(
    transcript: list[dict[str, Any]],
    meeting_id: str,
    reference_date: str,
) -> dict[str, list[dict[str, Any]]]:
    """Extract explicit tasks and decisions from chronological transcript segments.

    ``meeting_id`` is supplied by the caller because it belongs to the meeting
    record, rather than to an individual transcript segment.
    """
    tasks: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for idx, segment in enumerate(transcript):
        text = segment.get("text", "").strip()
        segment_id = segment.get("segment_id", f"seg-{idx+1:03d}")
        speaker = segment.get("speaker", "Unknown")
        timestamp = segment.get("timestamp") or segment.get("start_time", "00:00:00")
        text_lower = text.lower()

        task_counter = 1
        progress_info = extract_progress(text)
        uncertain = detect_uncertainty(text)

        # 1. Assignment: "Maya, please turn those wireframes... due by..."
        assignment = ASSIGNMENT_PATTERN.search(text)
        if assignment:
            deadline_match = DEADLINE_PATTERN.search(text)
            desc = assignment.group("description")
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    desc,
                    segment_id,
                    meeting_id,
                    owner=assignment.group("owner"),
                    deadline=(
                        normalize_deadline(
                            deadline_match.group("deadline").strip(),
                            reference_date,
                        )
                        if deadline_match
                        else None
                    ),
                    state="assigned",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress=progress_info.to_dict() if progress_info else None,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 2. Third-person assignment: "Rahul will develop the login module."
        third_person = THIRD_PERSON_ASSIGNMENT.search(text)
        if third_person and not assignment and "i will" not in text_lower:
            owner_candidate = third_person.group("owner")
            # Avoid matching day names or common words as owner
            if owner_candidate.lower() not in ("today", "tomorrow", "monday", "friday", "this", "that"):
                deadline_match = DEADLINE_PATTERN.search(text)
                desc = third_person.group("description")
                if deadline_match:
                    desc = re.sub(r"\s+by\s+[^.]+$", "", desc, flags=re.IGNORECASE)
                tasks.append(
                    _new_task(
                        f"task-{segment_id}-{task_counter}",
                        desc,
                        segment_id,
                        meeting_id,
                        owner=owner_candidate,
                        deadline=(
                            normalize_deadline(
                                deadline_match.group("deadline").strip(),
                                reference_date,
                            )
                            if deadline_match
                            else None
                        ),
                        state="assigned",
                        speaker=speaker,
                        timestamp=timestamp,
                        text=text,
                        progress=progress_info.to_dict() if progress_info else None,
                        uncertain=uncertain,
                    )
                )
                task_counter += 1

        # 3. Passive assignment: "The login module has been assigned to Rahul."
        passive = PASSIVE_ASSIGNMENT.search(text)
        if passive and not assignment and not third_person:
            desc = re.sub(r"^the\s+", "", passive.group("description"), flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    desc,
                    segment_id,
                    meeting_id,
                    owner=passive.group("owner"),
                    state="assigned",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress=progress_info.to_dict() if progress_info else None,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 4. Explicit completion
        if " are complete" in text_lower or " is complete" in text_lower or " has been completed" in text_lower or " is completed" in text_lower:
            description = re.sub(r"^(quick update:\s*)?(the\s+)?", "", text, flags=re.IGNORECASE)
            description = re.sub(r"\s+(?:are|is|has been)\s+complete.*$", "", description, flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    description,
                    segment_id,
                    meeting_id,
                    state="completed",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress={"progress_value": 100, "progress_label": "completed", "progress_type": "explicit_percentage", "confidence": 0.95},
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 5. Explicit blockers
        if " are blocked" in text_lower or " is blocked" in text_lower:
            description = re.split(r"\s+(?:are|is)\s+blocked", text, flags=re.IGNORECASE)[0]
            description = re.sub(r"^the\s+", "", description, flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    description,
                    segment_id,
                    meeting_id,
                    state="blocked",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress=progress_info.to_dict() if progress_info else None,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 6. Reopened tasks: "The dashboard design was reopened because...", "reopened the login module"
        if "reopened" in text_lower or ("bug in" in text_lower and "fix" in text_lower) or "another issue in" in text_lower:
            match_passive = re.search(r"(?:the\s+)?([a-z0-9\s]+?)\s+(?:was|is|has been)\s+reopened", text, re.IGNORECASE)
            match_active = re.search(r"reopened\s+(?:the\s+)?([a-z0-9\s]+?)(?:because|\.|$|,)", text, re.IGNORECASE)
            if match_passive:
                desc = match_passive.group(1).strip()
            elif match_active:
                desc = match_active.group(1).strip()
            else:
                desc = text
            desc = re.sub(r"^(the|we)\s+", "", desc, flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    desc,
                    segment_id,
                    meeting_id,
                    state="reopened",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress=progress_info.to_dict() if progress_info else None,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 7. In-progress status updates: "is currently in progress", "working on", "implemented most of", "done"
        if ("in progress" in text_lower or "working on" in text_lower or "implemented most of" in text_lower or "% done" in text_lower or "percent done" in text_lower) and not assignment and not third_person:
            # Check if not already extracted as completed or blocked
            if not any(t["source_segment_id"] == segment_id for t in tasks):
                # Extract task mention
                match_wip = re.search(r"(?:working on|progress on|implemented most of|the)?\s*([a-z0-9\s]+?)\s+(?:is|are|is around|is currently)", text, re.IGNORECASE)
                desc = match_wip.group(1).strip() if match_wip else text
                desc = re.sub(r"^(the|we|i)\s+", "", desc, flags=re.IGNORECASE)
                tasks.append(
                    _new_task(
                        f"task-{segment_id}-{task_counter}",
                        desc,
                        segment_id,
                        meeting_id,
                        state="in_progress",
                        speaker=speaker,
                        timestamp=timestamp,
                        text=text,
                        progress=progress_info.to_dict() if progress_info else None,
                        uncertain=uncertain,
                    )
                )
                task_counter += 1

        # 8. Dependency pattern
        dependency = DEPENDENCY_PATTERN.search(text)
        if dependency:
            dependent_task = dependency.group("task").rsplit(".", 1)[-1].strip()
            dependent_task = re.sub(r"^the\s+", "", dependent_task, flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    dependent_task,
                    segment_id,
                    meeting_id,
                    depends_on=[dependency.group("dependency").strip()],
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 9. First-person commitment: "I will send Maya the existing asset package by noon today."
        commitment = COMMITMENT_PATTERN.search(text)
        if commitment and not assignment:
            description = commitment.group("description")
            deadline_match = COMMITMENT_DEADLINE_PATTERN.search(description)
            if deadline_match:
                description = re.sub(r"\s+by\s+[^.]+$", "", description, flags=re.IGNORECASE)
            tasks.append(
                _new_task(
                    f"task-{segment_id}-{task_counter}",
                    description,
                    segment_id,
                    meeting_id,
                    owner=speaker,
                    deadline=(
                        normalize_deadline(
                            deadline_match.group("deadline").strip(),
                            reference_date,
                        )
                        if deadline_match
                        else None
                    ),
                    state="assigned",
                    speaker=speaker,
                    timestamp=timestamp,
                    text=text,
                    progress=progress_info.to_dict() if progress_info else None,
                    uncertain=uncertain,
                )
            )
            task_counter += 1

        # 10. Decision extraction: "That is our decision" or "We agreed to"
        if "that is our decision" in text_lower or "we decided to" in text_lower or "we agreed to" in text_lower:
            description = re.split(r"\.\s*(?:That is our decision|we decided|we agreed)", text, flags=re.IGNORECASE)[0]
            decisions.append(
                {
                    "decision_id": f"decision-{segment_id}-1",
                    "description": description.strip(),
                    "source_segment_id": segment_id,
                    "meeting_id": meeting_id,
                    "speaker": speaker,
                    "timestamp": timestamp,
                }
            )

    return {"tasks": tasks, "decisions": decisions}


def extract_from_file(
    transcript_path: str | Path,
    meeting_id: str,
    reference_date: str,
) -> dict[str, list[dict[str, Any]]]:
    """Load a transcript JSON array and return its extracted meeting items."""
    with Path(transcript_path).open(encoding="utf-8") as transcript_file:
        return extract_meeting_items(
            json.load(transcript_file),
            meeting_id,
            reference_date,
        )
