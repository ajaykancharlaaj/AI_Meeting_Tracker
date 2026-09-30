"""
Service Layer for AI Meeting Action Tracker.

Provides a clean, unified API service layer for backend consumption,
interactive CLI demos, and REST framework integration.

Methods:
- process_meeting(meeting_id, transcript, metadata)
- process_transcript_chunk(meeting_id, speaker, timestamp, text, segment_id)
- finalize_meeting(meeting_id)
- get_current_tasks()
- get_task(task_id)
- get_task_history(task_id)
- get_task_evidence(task_id)
- get_dependencies()
- get_risks()
- get_contradictions()
- get_manager_summary()
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from ai_module.pipeline import (
    MeetingIntelligenceEngine,
    _GLOBAL_ENGINE,
)
from ai_module.risk.dependency_analyzer import build_dependency_graph
from ai_module.risk.risk_analyzer import analyze_dependency_risk
from ai_module.state_reconstruction.state_reconstructor import (
    format_evidence_timeline,
    detect_state_contradictions_rich,
)

logger = logging.getLogger("ai_meeting_action_tracker.service")


class MeetingTrackerService:
    """Service facade exposing clean AI/ML operations to backend applications."""

    def __init__(self, engine: Optional[MeetingIntelligenceEngine] = None):
        self.engine = engine or _GLOBAL_ENGINE

    def process_meeting(
        self,
        meeting_id: str,
        transcript: List[Dict[str, Any]],
        reference_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a complete meeting transcript.
        Returns the structured JSON API output contract.
        """
        if not meeting_id or not meeting_id.strip():
            return {
                "status": "error",
                "error_code": "INVALID_MEETING_ID",
                "message": "Meeting ID cannot be empty."
            }

        if not transcript or not isinstance(transcript, list):
            return {
                "status": "error",
                "error_code": "INVALID_TRANSCRIPT",
                "message": "Transcript text is empty or invalid format."
            }

        try:
            logger.info("Processing meeting %s with %d segments", meeting_id, len(transcript))
            return self.engine.process_meeting(
                meeting_id=meeting_id,
                transcript=transcript,
                reference_date=reference_date,
                metadata=metadata,
            )
        except Exception as exc:
            logger.error("Error processing meeting %s: %s", meeting_id, exc, exc_info=True)
            return {
                "status": "error",
                "error_code": "PROCESSING_ERROR",
                "message": str(exc),
            }

    def process_transcript_chunk(
        self,
        meeting_id: str,
        speaker: str,
        timestamp: str,
        text: str,
        segment_id: Optional[str] = None,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Incrementally stream one chunk during a live meeting.
        """
        if not text or not text.strip():
            return {
                "status": "error",
                "error_code": "EMPTY_CHUNK",
                "message": "Transcript chunk text cannot be empty."
            }

        return self.engine.process_transcript_chunk(
            meeting_id=meeting_id,
            speaker=speaker,
            timestamp=timestamp,
            text=text,
            segment_id=segment_id,
            reference_date=reference_date,
        )

    def finalize_meeting(
        self,
        meeting_id: str,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Finalize a meeting once streaming ends.
        """
        return self.engine.finalize_meeting(
            meeting_id=meeting_id,
            reference_date=reference_date,
        )

    def get_current_tasks(self) -> List[Dict[str, Any]]:
        """
        Retrieve all current canonical tasks across all meetings.
        """
        tasks = self.engine.task_memory.get_all_tasks()
        graph = build_dependency_graph(tasks)
        risk_map = analyze_dependency_risk(tasks, graph)

        results = []
        for t in tasks:
            tid = t["task_id"]
            r_info = risk_map.get(tid, {})
            results.append({
                "task_id": tid,
                "description": t.get("canonical_description") or t.get("description"),
                "aliases": t.get("aliases", []),
                "owner": t.get("owner"),
                "current_state": (t.get("current_state") or t.get("state") or "ASSIGNED").upper().replace(" ", "_"),
                "progress": t.get("progress"),
                "deadline": t.get("current_deadline") or t.get("deadline"),
                "risk_level": r_info.get("risk_level", "LOW"),
                "risk_reasons": r_info.get("risk_reasons", []),
                "dependencies": t.get("dependencies", []),
                "repeated_unresolved_task": t.get("repeated_unresolved_task", False),
            })
        return results

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full details for a single task.
        """
        t = self.engine.task_memory.get_task(task_id)
        if not t:
            return None
        return t

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve state history and evidence timeline for a task.
        """
        t = self.engine.task_memory.get_task(task_id)
        if not t:
            return []
        return format_evidence_timeline(t)

    def get_task_evidence(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve raw evidence records backing a task.
        """
        return self.engine.task_memory.get_task_evidence(task_id)

    def get_dependencies(self) -> Dict[str, Any]:
        """
        Retrieve global dependency graph and direct relationships.
        """
        tasks = self.engine.task_memory.get_all_tasks()
        graph = build_dependency_graph(tasks)
        links = []
        for src, deps in graph.items():
            for target in deps:
                links.append({"source": src, "target": target, "relationship": "depends_on"})
        return {"graph": graph, "dependencies": links}

    def get_risks(self, current_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve calculated risks for all active tasks.
        """
        tasks = self.engine.task_memory.get_all_tasks()
        graph = build_dependency_graph(tasks)
        risk_map = analyze_dependency_risk(tasks, graph, current_date=current_date)
        return [
            {
                "task_id": tid,
                "risk_level": r["risk_level"],
                "risk_reasons": r["risk_reasons"],
                "dependency_blocked": r["dependency_blocked"],
                "overdue": r["overdue"],
                "at_risk": r["at_risk"],
            }
            for tid, r in risk_map.items()
        ]

    def get_contradictions(self) -> List[Dict[str, Any]]:
        """
        Retrieve detected cross-meeting state contradictions requiring human review.
        """
        tasks = self.engine.task_memory.get_all_tasks()
        contradictions = []
        for t in tasks:
            updates = t.get("state_history") or t.get("history") or []
            if len(updates) > 1:
                contradictions.extend(detect_state_contradictions_rich(t["task_id"], updates))
        return contradictions

    def get_manager_summary(self) -> Dict[str, Any]:
        """
        Executive-level summary of tasks, blockers, stagnations, and high risks.
        """
        tasks = self.get_current_tasks()
        risks = self.get_risks()
        contradictions = self.get_contradictions()

        high_risk_tasks = [t for t in tasks if t.get("risk_level") in ("HIGH", "CRITICAL")]
        blocked_tasks = [t for t in tasks if t.get("current_state") == "BLOCKED"]
        stalled_tasks = [t for t in tasks if t.get("repeated_unresolved_task")]

        return {
            "total_tasks": len(tasks),
            "blocked_tasks_count": len(blocked_tasks),
            "high_risk_tasks_count": len(high_risk_tasks),
            "stalled_tasks_count": len(stalled_tasks),
            "contradictions_count": len(contradictions),
            "high_risk_tasks": high_risk_tasks,
            "stalled_tasks": stalled_tasks,
            "contradictions": contradictions,
        }
