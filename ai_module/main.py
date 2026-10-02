"""
FastAPI REST API Server for AI Meeting Action Tracker.

Provides backend-friendly endpoints for:
- Full meeting batch processing
- Real-time incremental transcript chunk streaming
- Finalizing meetings
- Task management and details
- Evidence-aware timelines
- Dependency graphs and risk analysis
- Contradiction detection
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path as APIPath, Query, status
from pydantic import BaseModel, Field

from ai_module.service import MeetingTrackerService

logger = logging.getLogger("ai_meeting_action_tracker.api")

app = FastAPI(
    title="AI Meeting Action Tracker API",
    description="Multi-Agent Meeting Intelligence System with Cross-Meeting Task Entity Resolution and Dependency-Aware Risk Assessment",
    version="1.0.0",
)

service = MeetingTrackerService()


# --- Request Schemas ---

class TranscriptChunkRequest(BaseModel):
    speaker: str = Field(..., example="Rahul")
    timestamp: str = Field("00:00:00", example="00:15:30")
    text: str = Field(..., example="The login module is around 50 percent completed.")
    segment_id: Optional[str] = Field(None, example="seg-001")
    reference_date: Optional[str] = Field(None, example="2026-09-17")


class TranscriptSegment(BaseModel):
    segment_id: Optional[str] = Field(None, example="seg-001")
    speaker: str = Field("Unknown", example="Rahul")
    start_time: Optional[str] = Field("00:00:00", example="00:02:15")
    timestamp: Optional[str] = Field("00:00:00", example="00:02:15")
    text: str = Field(..., example="Rahul will develop the login module.")


class FullMeetingRequest(BaseModel):
    meeting_id: str = Field(..., example="M001")
    reference_date: str = Field("2026-09-17", example="2026-09-17")
    transcript: List[TranscriptSegment]
    metadata: Optional[Dict[str, Any]] = None


class FinalizeMeetingRequest(BaseModel):
    reference_date: Optional[str] = Field(None, example="2026-09-17")


# --- REST API Endpoints ---

@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "AI Meeting Action Tracker Engine"}


@app.post("/ai/meetings/process", tags=["Meetings"])
def process_full_meeting(req: FullMeetingRequest) -> Dict[str, Any]:
    """Process an entire meeting transcript in batch mode."""
    transcript_dicts = [seg.dict() for seg in req.transcript]
    result = service.process_meeting(
        meeting_id=req.meeting_id,
        transcript=transcript_dicts,
        reference_date=req.reference_date,
        metadata=req.metadata,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/ai/meetings/{meeting_id}/chunks", tags=["Streaming"])
def stream_transcript_chunk(
    meeting_id: str = APIPath(..., description="Unique meeting ID"),
    chunk: TranscriptChunkRequest = ...,
) -> Dict[str, Any]:
    """Stream a single transcript chunk incrementally during a live meeting."""
    result = service.process_transcript_chunk(
        meeting_id=meeting_id,
        speaker=chunk.speaker,
        timestamp=chunk.timestamp,
        text=chunk.text,
        segment_id=chunk.segment_id,
        reference_date=chunk.reference_date,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/ai/meetings/{meeting_id}/finalize", tags=["Streaming"])
def finalize_meeting(
    meeting_id: str = APIPath(..., description="Unique meeting ID"),
    req: Optional[FinalizeMeetingRequest] = None,
) -> Dict[str, Any]:
    """Finalize meeting after streaming chunks to build global graph and risks."""
    ref_date = req.reference_date if req else None
    return service.finalize_meeting(meeting_id=meeting_id, reference_date=ref_date)


@app.get("/ai/tasks", tags=["Tasks"])
def get_all_tasks() -> List[Dict[str, Any]]:
    """Retrieve all current persistent task entities across all meetings."""
    return service.get_current_tasks()


@app.get("/ai/tasks/{task_id}", tags=["Tasks"])
def get_task_by_id(task_id: str = APIPath(..., description="Task ID (e.g., T001)")) -> Dict[str, Any]:
    """Retrieve full details of a specific canonical task entity."""
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task


@app.get("/ai/tasks/{task_id}/timeline", tags=["Tasks"])
def get_task_timeline(task_id: str = APIPath(..., description="Task ID")) -> List[Dict[str, Any]]:
    """Retrieve chronological evidence-aware state transition timeline for a task."""
    timeline = service.get_task_history(task_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"No timeline history found for task '{task_id}'.")
    return timeline


@app.get("/ai/tasks/{task_id}/evidence", tags=["Tasks"])
def get_task_evidence(task_id: str = APIPath(..., description="Task ID")) -> List[Dict[str, Any]]:
    """Retrieve raw evidence records backing a task's state changes."""
    return service.get_task_evidence(task_id)


@app.get("/ai/dependencies", tags=["Graph & Risk"])
def get_dependencies() -> Dict[str, Any]:
    """Retrieve the directed dependency graph of all tasks."""
    return service.get_dependencies()


@app.get("/ai/risks", tags=["Graph & Risk"])
def get_risks(current_date: Optional[str] = Query(None, example="2026-09-17")) -> List[Dict[str, Any]]:
    """Retrieve dependency risk assessment and overdue task flags."""
    return service.get_risks(current_date=current_date)


@app.get("/ai/contradictions", tags=["Intelligence"])
def get_contradictions() -> List[Dict[str, Any]]:
    """Retrieve cross-meeting state contradictions requiring manager review."""
    return service.get_contradictions()


@app.get("/ai/summary", tags=["Intelligence"])
def get_manager_summary() -> Dict[str, Any]:
    """Retrieve executive summary of risks, stalled tasks, and blockers."""
    return service.get_manager_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai_module.main:app", host="0.0.0.0", port=8000, reload=True)
