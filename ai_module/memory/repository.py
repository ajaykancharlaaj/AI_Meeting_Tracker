"""
Persistence abstraction for tasks, meetings, and relationships.
Provides an interface-based repository pattern allowing in-memory,
JSON file, or future Neo4j / PostgreSQL storage backends.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskRepository(ABC):
    """Abstract interface for task storage and graph querying."""

    @abstractmethod
    def save(self, task: Dict[str, Any]) -> None:
        """Save or update a task entity."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by task_id."""
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all stored tasks."""
        pass

    @abstractmethod
    def delete(self, task_id: str) -> bool:
        """Delete task by task_id."""
        pass

    @abstractmethod
    def export_graph(self) -> Dict[str, Any]:
        """Export nodes and edges compatible with Neo4j / Graph visualization."""
        pass


class InMemoryTaskRepository(TaskRepository):
    """Fast, thread-safe in-memory task repository."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def save(self, task: Dict[str, Any]) -> None:
        self._tasks[task["task_id"]] = deepcopy(task)

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        return deepcopy(task) if task else None

    def get_all(self) -> List[Dict[str, Any]]:
        return deepcopy(list(self._tasks.values()))

    def delete(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def export_graph(self) -> Dict[str, Any]:
        """Export (:Task), (:Person), (:Meeting) nodes and relationships."""
        nodes = []
        edges = []
        persons = set()
        meetings = set()

        for task_id, task in self._tasks.items():
            nodes.append({
                "id": task_id,
                "label": "Task",
                "properties": {
                    "task_id": task_id,
                    "description": task.get("canonical_description") or task.get("description"),
                    "state": task.get("current_state") or task.get("state"),
                    "owner": task.get("owner"),
                    "deadline": task.get("current_deadline") or task.get("deadline"),
                }
            })

            # Person relationship (:Person)-[:OWNS]->(:Task)
            owner = task.get("owner")
            if owner:
                if owner not in persons:
                    persons.add(owner)
                    nodes.append({
                        "id": f"person-{owner}",
                        "label": "Person",
                        "properties": {"name": owner}
                    })
                edges.append({
                    "source": f"person-{owner}",
                    "target": task_id,
                    "type": "OWNS",
                })

            # Task dependencies (:Task)-[:DEPENDS_ON]->(:Task)
            for dep in task.get("dependencies", []):
                edges.append({
                    "source": task_id,
                    "target": dep,
                    "type": "DEPENDS_ON",
                })

            # Meeting mentions (:Meeting)-[:CONTAINS]->(:Task)
            for update in task.get("state_history", []):
                m_id = update.get("meeting_id")
                if m_id:
                    if m_id not in meetings:
                        meetings.add(m_id)
                        nodes.append({
                            "id": f"meeting-{m_id}",
                            "label": "Meeting",
                            "properties": {"meeting_id": m_id}
                        })
                    edges.append({
                        "source": f"meeting-{m_id}",
                        "target": task_id,
                        "type": "DISCUSSED_IN",
                        "properties": {"state": update.get("state")}
                    })

        return {"nodes": nodes, "edges": edges}


class JsonFileTaskRepository(InMemoryTaskRepository):
    """File-backed persistence repository that syncs with a JSON file."""

    def __init__(self, file_path: str = "tasks_memory.json"):
        super().__init__()
        self.file_path = Path(file_path)
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tasks = {t["task_id"]: t for t in data}
            except Exception:
                self._tasks = {}

    def save(self, task: Dict[str, Any]) -> None:
        super().save(task)
        self._flush()

    def delete(self, task_id: str) -> bool:
        res = super().delete(task_id)
        if res:
            self._flush()
        return res

    def _flush(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(list(self._tasks.values()), f, indent=2)
        except Exception:
            pass


class MeetingRepository(ABC):
    """Abstract interface for meeting storage."""

    @abstractmethod
    def save(self, meeting: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        pass


class InMemoryMeetingRepository(MeetingRepository):
    def __init__(self):
        self._meetings: Dict[str, Dict[str, Any]] = {}

    def save(self, meeting: Dict[str, Any]) -> None:
        self._meetings[meeting["meeting_id"]] = deepcopy(meeting)

    def get(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        m = self._meetings.get(meeting_id)
        return deepcopy(m) if m else None

    def get_all(self) -> List[Dict[str, Any]]:
        return deepcopy(list(self._meetings.values()))
