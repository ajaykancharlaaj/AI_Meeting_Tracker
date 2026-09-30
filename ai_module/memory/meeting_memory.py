"""
Meeting Memory Layer.

Stores meeting-level metadata, participant rosters, raw and segmented transcripts,
extracted decisions, detected contradictions, and processing status.
"""

from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional
from ai_module.memory.repository import MeetingRepository, InMemoryMeetingRepository


class MeetingMemory:
    """Manages meeting-level records and chronological storage."""

    def __init__(self, repository: Optional[MeetingRepository] = None):
        self.repository = repository or InMemoryMeetingRepository()

    def record_meeting(
        self,
        meeting_id: str,
        reference_date: str = "",
        participants: Optional[List[str]] = None,
        transcript: Optional[List[Dict[str, Any]]] = None,
        extracted_tasks: Optional[List[Dict[str, Any]]] = None,
        extracted_decisions: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        state_updates: Optional[List[Dict[str, Any]]] = None,
        processing_status: str = "completed",
    ) -> Dict[str, Any]:
        """Record complete meeting information."""
        now_iso = datetime.now().isoformat()

        # Extract participants from transcript if not explicitly provided
        inferred_participants = set(participants or [])
        if transcript:
            for seg in transcript:
                speaker = seg.get("speaker")
                if speaker and speaker.lower() not in ("unknown", "speaker"):
                    inferred_participants.add(speaker)

        meeting_record: Dict[str, Any] = {
            "meeting_id": meeting_id,
            "reference_date": reference_date or now_iso.split("T")[0],
            "recorded_at": now_iso,
            "participants": sorted(list(inferred_participants)),
            "transcript_segment_count": len(transcript) if transcript else 0,
            "transcript": transcript or [],
            "extracted_tasks": extracted_tasks or [],
            "extracted_decisions": extracted_decisions or [],
            "dependencies": dependencies or [],
            "state_updates": state_updates or [],
            "processing_status": processing_status,
        }

        self.repository.save(meeting_record)
        return meeting_record

    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve meeting record by meeting_id."""
        return self.repository.get(meeting_id)

    def get_all_meetings(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded meetings sorted chronologically."""
        meetings = self.repository.get_all()
        return sorted(meetings, key=lambda m: m.get("reference_date", ""))
