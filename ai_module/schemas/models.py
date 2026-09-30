"""
Data models and schema definitions for the AI Meeting Action Tracker.
Supports cross-meeting task entity resolution, temporal state reconstruction,
dependency graphs, risk analysis, and evidence-aware timelines.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, List, Dict


class TaskState(str, Enum):
    ASSIGNED = "ASSIGNED"
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REOPENED = "REOPENED"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def normalize(cls, state_str: Optional[str]) -> "TaskState":
        if not state_str:
            return cls.UNKNOWN
        cleaned = state_str.strip().upper().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == cleaned:
                return member
        # Common aliases
        if cleaned in ("DONE", "FINISHED", "RESOLVED"):
            return cls.COMPLETED
        if cleaned in ("WAITING", "STUCK", "HOLD", "ON_HOLD"):
            return cls.BLOCKED
        if cleaned in ("DOING", "WORKING", "ACTIVE", "WIP", "PROGRESS"):
            return cls.IN_PROGRESS
        if cleaned in ("OPEN", "NEW", "TODO"):
            return cls.ASSIGNED
        return cls.UNKNOWN


class CertaintyLevel(str, Enum):
    CERTAIN = "certain"
    UNCERTAIN = "uncertain"
    SPECULATIVE = "speculative"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class EvidenceRecord:
    """Traceable evidence for any extracted fact or state transition."""
    meeting_id: str
    speaker: str
    timestamp: str = "00:00:00"
    text: str = ""
    evidence_type: str = "state_update"  # state_update, assignment, deadline, progress, dependency, blocker
    source_segment_id: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressInfo:
    """Structured progress representation."""
    progress_value: Optional[int] = None  # 0 to 100 if explicit
    progress_label: Optional[str] = None  # e.g., 'started', 'half_done', 'almost_complete', 'completed'
    progress_type: str = "qualitative"     # 'explicit_percentage' or 'qualitative'
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateHistoryRecord:
    """Historical state record for a task at a given meeting."""
    state: str
    meeting_id: str
    meeting_date: str = ""
    timestamp: str = "00:00:00"
    source_segment_id: Optional[str] = None
    speaker: str = ""
    text: str = ""
    uncertain: bool = False
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeadlineHistoryRecord:
    """History of deadlines assigned and changed across meetings."""
    deadline: Optional[str]
    meeting_id: str
    meeting_date: str = ""
    change_type: str = "initial"  # initial, deadline_changed, confirmed
    source_segment_id: Optional[str] = None
    evidence_text: str = ""
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DependencyRecord:
    """Directed dependency relationship between tasks."""
    source_task_id: str
    target_task_id: str
    relationship: str = "depends_on"  # depends_on, blocked_by, waiting_for
    evidence: Optional[EvidenceRecord] = None
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.evidence:
            d["evidence"] = self.evidence.to_dict()
        return d


@dataclass
class ContradictionRecord:
    """Contradiction or conflicting status claims across meetings or speakers."""
    type: str  # state_contradiction, deadline_contradiction, owner_contradiction
    task_id: str
    claims: List[Dict[str, Any]]
    requires_review: bool = True
    explanation: str = ""
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskRecord:
    """Calculated risk assessment for a task."""
    task_id: str
    risk_level: str = "LOW"
    risk_reasons: List[str] = field(default_factory=list)
    dependency_blocked: bool = False
    overdue: bool = False
    at_risk: bool = False
    deadline_status: str = "No Deadline"
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskEntity:
    """Persistent task memory entity with full historical evolution."""
    task_id: str
    canonical_description: str
    aliases: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    project: Optional[str] = "Default"
    created_meeting_id: str = ""
    current_state: str = TaskState.ASSIGNED.value
    current_progress: Optional[Dict[str, Any]] = None
    current_deadline: Optional[str] = None
    priority: str = "MEDIUM"
    dependencies: List[str] = field(default_factory=list)
    dependent_tasks: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    deadline_history: List[Dict[str, Any]] = field(default_factory=list)
    owner_history: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.9
    last_updated_meeting: str = ""
    created_at: str = ""
    updated_at: str = ""
    discussion_count: int = 1
    unresolved_discussion_count: int = 0
    repeated_unresolved_task: bool = False

    def to_contract_dict(self) -> Dict[str, Any]:
        """Convert to the backend JSON API output contract format."""
        progress_val = None
        if self.current_progress:
            progress_val = self.current_progress.get("progress_value")
            if progress_val is None and self.current_state == TaskState.COMPLETED.value:
                progress_val = 100

        return {
            "task_id": self.task_id,
            "description": self.canonical_description,
            "aliases": self.aliases,
            "owner": self.owner,
            "project": self.project,
            "current_state": self.current_state,
            "progress": progress_val,
            "progress_details": self.current_progress,
            "deadline": self.current_deadline,
            "priority": self.priority,
            "risk_level": "LOW",  # Will be populated by risk analyzer
            "match_confidence": self.confidence,
            "dependencies": self.dependencies,
            "evidence": self.evidence,
            "state_history": self.state_history,
            "deadline_history": self.deadline_history,
            "repeated_unresolved_task": self.repeated_unresolved_task,
            "last_updated_meeting": self.last_updated_meeting,
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
