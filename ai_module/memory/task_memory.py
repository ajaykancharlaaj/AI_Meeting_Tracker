"""
Persistent Task Memory Layer.

Maintains canonical task entities across multi-meeting timelines with:
- Stable task IDs (e.g. T001, T002...)
- Canonical descriptions and cross-meeting aliases
- Multi-meeting state history and transition evidence
- Deadline change tracking (deadline_history)
- Owner tracking (owner_history)
- Explicit and qualitative progress tracking
- Repeated discussion and unresolved stagnation detection
"""

from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional
from ai_module.memory.repository import TaskRepository, InMemoryTaskRepository
from ai_module.schemas.models import TaskState, TaskEntity


class TaskMemory:
    """Manages persistent task state and cross-meeting memory."""

    def __init__(self, repository: Optional[TaskRepository] = None):
        self.repository = repository or InMemoryTaskRepository()
        self._next_id_counter = 1

    def _generate_task_id(self) -> str:
        """Generate a stable canonical task ID like T001, T002."""
        existing_ids = {t["task_id"] for t in self.repository.get_all()}
        while True:
            tid = f"T{self._next_id_counter:03d}"
            self._next_id_counter += 1
            if tid not in existing_ids:
                return tid

    def add_new_task(self, task: Dict[str, Any]) -> str:
        """Create and store a new canonical task."""
        task_id = task.get("task_id")
        # If task_id is a temporary segment ID or missing, allocate a stable ID
        if not task_id or task_id.startswith("task-") or task_id.startswith("TEMP-"):
            task_id = self._generate_task_id()

        description = (task.get("description") or task.get("canonical_description") or "").strip()
        state = task.get("state") or TaskState.ASSIGNED.value
        if state:
            state = state.capitalize() if state.islower() else state

        deadline = task.get("deadline")
        owner = task.get("owner")
        meeting_id = task.get("meeting_id", "")
        now_iso = datetime.now().isoformat()

        stored_task: Dict[str, Any] = {
            "task_id": task_id,
            "canonical_description": description,
            "description": description,  # Backward compatibility
            "aliases": [description] if description else [],
            "owner": owner,
            "project": task.get("project", "Default"),
            "created_meeting_id": meeting_id,
            "current_state": state,
            "state": state,  # Backward compatibility
            "current_progress": task.get("progress"),
            "progress": task.get("progress", {}).get("progress_value") if isinstance(task.get("progress"), dict) else task.get("progress"),
            "current_deadline": deadline,
            "deadline": deadline,  # Backward compatibility
            "priority": task.get("priority", "MEDIUM"),
            "dependencies": list(task.get("depends_on", [])),
            "depends_on": list(task.get("depends_on", [])),  # Backward compatibility
            "dependent_tasks": [],
            "evidence": [],
            "state_history": [],
            "history": [],  # Backward compatibility
            "deadline_history": [],
            "owner_history": [{"owner": owner, "meeting_id": meeting_id}] if owner else [],
            "confidence": task.get("confidence", 0.90),
            "last_updated_meeting": meeting_id,
            "created_at": now_iso,
            "updated_at": now_iso,
            "discussion_count": 1,
            "unresolved_discussion_count": 0,
            "repeated_unresolved_task": False,
        }

        # Initial deadline history
        if deadline:
            stored_task["deadline_history"].append({
                "deadline": deadline,
                "meeting_id": meeting_id,
                "change_type": "initial",
                "evidence": task.get("evidence_text", ""),
            })

        # Initial state history if present
        if state:
            history_entry = {
                "meeting_id": meeting_id,
                "meeting_date": task.get("meeting_date", ""),
                "state": state,
                "source_segment_id": task.get("source_segment_id"),
                "evidence": task.get("evidence_text", "") or description,
                "speaker": owner or task.get("speaker", ""),
                "timestamp": task.get("timestamp", "00:00:00"),
                "uncertain": task.get("uncertain", False),
            }
            stored_task["history"].append(history_entry)
            stored_task["state_history"].append(history_entry)

        if task.get("evidence_text"):
            stored_task["evidence"].append({
                "meeting_id": meeting_id,
                "speaker": owner or task.get("speaker", ""),
                "timestamp": task.get("timestamp", "00:00:00"),
                "text": task.get("evidence_text", ""),
                "evidence_type": "assignment",
                "source_segment_id": task.get("source_segment_id"),
                "confidence": task.get("confidence", 0.90),
            })

        self.repository.save(stored_task)
        return task_id

    def add_task_update(
        self,
        task_id: str,
        task: Dict[str, Any],
        meeting_id: str,
        meeting_date: str,
        evidence_text: str = "",
        speaker: str = "",
        timestamp: str = "00:00:00",
    ) -> None:
        """Update an existing task with evidence from a meeting."""
        stored = self.repository.get(task_id)
        if not stored:
            task["task_id"] = task_id
            task["meeting_id"] = meeting_id
            task["meeting_date"] = meeting_date
            task["evidence_text"] = evidence_text
            task["speaker"] = speaker
            task["timestamp"] = timestamp
            self.add_new_task(task)
            return

        now_iso = datetime.now().isoformat()
        stored["updated_at"] = now_iso
        stored["last_updated_meeting"] = meeting_id
        stored["discussion_count"] = stored.get("discussion_count", 0) + 1

        # Track aliases
        new_desc = (task.get("description") or "").strip()
        if new_desc and new_desc not in stored.get("aliases", []):
            stored.setdefault("aliases", []).append(new_desc)

        # Update owner if newly available
        new_owner = task.get("owner")
        if new_owner and new_owner != stored.get("owner"):
            stored["owner"] = new_owner
            stored.setdefault("owner_history", []).append({
                "owner": new_owner,
                "meeting_id": meeting_id,
                "meeting_date": meeting_date,
            })

        # Update deadline if changed or newly provided
        new_deadline = task.get("deadline")
        old_deadline = stored.get("current_deadline") or stored.get("deadline")
        if new_deadline and new_deadline != old_deadline:
            change_type = "deadline_changed" if old_deadline else "initial"
            stored["current_deadline"] = new_deadline
            stored["deadline"] = new_deadline
            stored.setdefault("deadline_history", []).append({
                "deadline": new_deadline,
                "meeting_id": meeting_id,
                "meeting_date": meeting_date,
                "change_type": change_type,
                "evidence": evidence_text,
            })

        # Update dependencies
        new_deps = task.get("depends_on", []) or task.get("dependencies", [])
        for dep in new_deps:
            if dep not in stored.setdefault("dependencies", []):
                stored["dependencies"].append(dep)
            if dep not in stored.setdefault("depends_on", []):
                stored["depends_on"].append(dep)

        # Update progress
        new_progress = task.get("progress")
        if new_progress:
            stored["current_progress"] = new_progress
            if isinstance(new_progress, dict):
                stored["progress"] = new_progress.get("progress_value")
            else:
                stored["progress"] = new_progress

        # Update state and history
        new_state = task.get("state")
        if new_state:
            # Normalize state casing: "in_progress" or "In Progress" -> "In Progress"
            words = new_state.replace("_", " ").split()
            formatted_state = " ".join(w.capitalize() for w in words)

            old_state = stored.get("current_state") or stored.get("state")
            stored["current_state"] = formatted_state
            stored["state"] = formatted_state

            segment_id = task.get("source_segment_id", "")
            spk = speaker or task.get("speaker", "")
            ts = timestamp or task.get("timestamp", "00:00:00")

            # Check if this exact meeting update is already recorded
            existing_records = [
                h for h in stored.get("history", [])
                if h.get("meeting_id") == meeting_id and h.get("state") == formatted_state
            ]
            if not existing_records:
                history_entry = {
                    "meeting_id": meeting_id,
                    "meeting_date": meeting_date,
                    "state": formatted_state,
                    "source_segment_id": segment_id,
                    "evidence": evidence_text,
                    "speaker": spk,
                    "timestamp": ts,
                    "uncertain": task.get("uncertain", False),
                }
                stored.setdefault("history", []).append(history_entry)
                stored.setdefault("state_history", []).append(history_entry)

            # Evidence list
            if evidence_text:
                stored.setdefault("evidence", []).append({
                    "meeting_id": meeting_id,
                    "speaker": spk,
                    "timestamp": ts,
                    "text": evidence_text,
                    "evidence_type": "state_update",
                    "source_segment_id": segment_id,
                    "confidence": task.get("confidence", 0.95),
                })

            # Check unresolved stagnation
            if old_state == formatted_state and formatted_state not in ("Completed", "Cancelled"):
                stored["unresolved_discussion_count"] = stored.get("unresolved_discussion_count", 0) + 1
            else:
                stored["unresolved_discussion_count"] = 0

            # Repeated discussion without progress flag
            if stored.get("unresolved_discussion_count", 0) >= 2 or stored.get("discussion_count", 0) >= 3:
                if stored.get("current_state") not in ("Completed", "Cancelled"):
                    stored["repeated_unresolved_task"] = True
                else:
                    stored["repeated_unresolved_task"] = False

        self.repository.save(stored)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task by task_id."""
        return self.repository.get(task_id)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Retrieve deepcopy of all stored tasks."""
        return self.repository.get_all()

    def get_task_evidence(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieve evidence log for a specific task."""
        task = self.repository.get(task_id)
        return task.get("evidence", []) if task else []

    def get_task_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieve state timeline history for a task."""
        task = self.repository.get(task_id)
        return task.get("state_history", []) or task.get("history", []) if task else []
