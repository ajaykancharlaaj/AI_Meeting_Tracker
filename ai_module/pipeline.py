"""
Multi-Agent Meeting Intelligence Pipeline with Cross-Meeting Entity Resolution,
Temporal State Reconstruction, and Dependency-Aware Risk Assessment.

Supports:
- End-to-end full meeting batch processing
- Real-time incremental streaming of transcript chunks
- Structured backend JSON API output contract
"""

from __future__ import annotations
import json
import logging
import os
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_module.extraction.task_extractor import extract_meeting_items
from ai_module.entity_resolution.semantic_matcher import (
    find_best_semantic_match,
    resolve_task_identity,
    get_embedding,
)
from ai_module.risk.dependency_extractor import (
    extract_dependency_statement,
    link_dependency_semantically,
)
from ai_module.risk.dependency_analyzer import (
    build_dependency_graph,
    get_downstream_tasks,
)
from ai_module.risk.risk_analyzer import analyze_dependency_risk
from ai_module.state_reconstruction.state_reconstructor import (
    reconstruct_task_state,
    detect_contradictions,
    detect_state_contradictions_rich,
    format_evidence_timeline,
)
from ai_module.memory.task_memory import TaskMemory
from ai_module.memory.meeting_memory import MeetingMemory

# Configure structured logging
logger = logging.getLogger("ai_meeting_action_tracker")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MeetingIntelligenceEngine:
    """
    Core orchestrator managing persistent cross-meeting intelligence.
    Preserves task identity, state history, dependencies, and risk across meetings.
    Supports real-time incremental transcript chunk streaming and batch processing.
    """

    def __init__(
        self,
        task_memory: Optional[TaskMemory] = None,
        meeting_memory: Optional[MeetingMemory] = None,
    ):
        self.task_memory = task_memory or TaskMemory()
        self.meeting_memory = meeting_memory or MeetingMemory()
        self._active_chunks: Dict[str, List[Dict[str, Any]]] = {}
        self._active_metadata: Dict[str, Dict[str, Any]] = {}

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
        Incrementally process a single transcript chunk in real time.
        Does NOT rebuild historical memory from scratch.
        """
        if not meeting_id:
            return {
                "status": "error",
                "error_code": "MISSING_MEETING_ID",
                "message": "meeting_id is required."
            }

        if not text or not text.strip():
            return {
                "status": "error",
                "error_code": "INVALID_TRANSCRIPT",
                "message": "Transcript text is empty."
            }

        ref_date = reference_date or self._active_metadata.get(meeting_id, {}).get("reference_date", "2026-09-17")
        seg_id = segment_id or f"chunk-{len(self._active_chunks.get(meeting_id, [])) + 1:03d}"

        chunk = {
            "segment_id": seg_id,
            "speaker": speaker or "Unknown",
            "timestamp": timestamp or "00:00:00",
            "text": text.strip(),
        }

        self._active_chunks.setdefault(meeting_id, []).append(chunk)

        # Extract items from this single chunk
        extracted = extract_meeting_items([chunk], meeting_id=meeting_id, reference_date=ref_date)
        extracted_tasks = extracted["tasks"]
        extracted_decisions = extracted["decisions"]

        resolved_tasks = []
        existing_tasks = self.task_memory.get_all_tasks()

        for item in extracted_tasks:
            # Match against persistent cross-meeting task memory
            match = resolve_task_identity(item, existing_tasks, threshold=0.50)
            matched_id = match["matched_existing_task_id"]

            if matched_id:
                # Update existing canonical task in persistent memory
                self.task_memory.add_task_update(
                    task_id=matched_id,
                    task=item,
                    meeting_id=meeting_id,
                    meeting_date=ref_date,
                    evidence_text=text,
                    speaker=speaker,
                    timestamp=timestamp,
                )
                item["task_id"] = matched_id
                item["matched_existing_task_id"] = matched_id
                item["match_confidence"] = match["match_confidence"]
                item["match_reason"] = match["match_reason"]
            else:
                # Register new task in persistent memory if it's an assignment or action item
                new_id = self.task_memory.add_new_task(item)
                item["task_id"] = new_id
                item["matched_existing_task_id"] = None
                item["match_confidence"] = match["match_confidence"]
                item["match_reason"] = match["match_reason"]

            resolved_tasks.append(item)

        # Check for dependency statements in this chunk
        dep_statement = extract_dependency_statement(text)
        linked_dep = None
        if dep_statement:
            all_known = self.task_memory.get_all_tasks()
            linked_dep = link_dependency_semantically(dep_statement, all_known, threshold=0.50)
            if linked_dep.get("task_id") and linked_dep.get("depends_on"):
                t = self.task_memory.get_task(linked_dep["task_id"])
                if t:
                    self.task_memory.add_task_update(
                        task_id=linked_dep["task_id"],
                        task={"depends_on": [linked_dep["depends_on"]]},
                        meeting_id=meeting_id,
                        meeting_date=ref_date,
                        evidence_text=text,
                        speaker=speaker,
                        timestamp=timestamp,
                    )

        return {
            "status": "success",
            "meeting_id": meeting_id,
            "segment_id": seg_id,
            "extracted_tasks": resolved_tasks,
            "extracted_decisions": extracted_decisions,
            "detected_dependency": linked_dep,
        }

    def finalize_meeting(
        self,
        meeting_id: str,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Finalize a meeting after all chunks have been streamed.
        Reconciles global dependency graphs, contradictions, risk, and timeline.
        Returns the structured backend JSON contract.
        """
        chunks = self._active_chunks.get(meeting_id, [])
        ref_date = reference_date or self._active_metadata.get(meeting_id, {}).get("reference_date", "2026-09-17")

        all_tasks = self.task_memory.get_all_tasks()
        all_graph = build_dependency_graph(all_tasks)
        risk_map = analyze_dependency_risk(all_tasks, all_graph, current_date=ref_date)

        # Detect cross-meeting contradictions for tasks discussed in this meeting
        all_contradictions = []
        for task in all_tasks:
            updates = task.get("state_history") or task.get("history") or []
            if len(updates) > 1:
                rich_contras = detect_state_contradictions_rich(task["task_id"], updates)
                all_contradictions.extend(rich_contras)

        # Build backend contract tasks list
        contract_tasks = []
        for task in all_tasks:
            tid = task["task_id"]
            risk_info = risk_map.get(tid, {})

            # Clean evidence list for contract
            evidence_list = []
            for ev in task.get("evidence", []):
                evidence_list.append({
                    "meeting_id": ev.get("meeting_id"),
                    "speaker": ev.get("speaker"),
                    "timestamp": ev.get("timestamp", "00:00:00"),
                    "text": ev.get("text") or ev.get("evidence", ""),
                })

            # Clean state history
            state_history_list = []
            for h in task.get("state_history") or task.get("history") or []:
                state_history_list.append({
                    "state": (h.get("state") or "").upper().replace(" ", "_"),
                    "meeting_id": h.get("meeting_id"),
                    "timestamp": h.get("timestamp", "00:00:00"),
                    "speaker": h.get("speaker", ""),
                })

            progress_val = task.get("progress")
            if progress_val is None and (task.get("current_state") or "").upper() == "COMPLETED":
                progress_val = 100

            contract_tasks.append({
                "task_id": tid,
                "description": task.get("canonical_description") or task.get("description"),
                "aliases": task.get("aliases", []),
                "owner": task.get("owner"),
                "current_state": (task.get("current_state") or task.get("state") or "ASSIGNED").upper().replace(" ", "_"),
                "progress": progress_val,
                "deadline": task.get("current_deadline") or task.get("deadline"),
                "risk_level": risk_info.get("risk_level", "LOW"),
                "risk_reasons": risk_info.get("risk_reasons", []),
                "match_confidence": task.get("confidence", 0.90),
                "evidence": evidence_list,
                "state_history": state_history_list,
                "deadline_history": task.get("deadline_history", []),
                "repeated_unresolved_task": task.get("repeated_unresolved_task", False),
            })

        # Record into Meeting Memory
        meeting_record = self.meeting_memory.record_meeting(
            meeting_id=meeting_id,
            reference_date=ref_date,
            transcript=chunks,
            extracted_tasks=contract_tasks,
            extracted_decisions=[],
            dependencies=[
                {"source_task_id": k, "target_task_id": dep, "relationship": "depends_on"}
                for k, v in all_graph.items() for dep in v
            ],
            processing_status="completed",
        )

        return {
            "meeting_id": meeting_id,
            "processing_status": "completed",
            "tasks": contract_tasks,
            "dependencies": [
                {"source_task_id": k, "target_task_id": dep, "relationship": "depends_on"}
                for k, v in all_graph.items() for dep in v
            ],
            "contradictions": all_contradictions,
            "risks": [
                {
                    "task_id": tid,
                    "risk_level": r.get("risk_level", "LOW"),
                    "risk_reasons": r.get("risk_reasons", []),
                    "dependency_blocked": r.get("dependency_blocked", False),
                    "overdue": r.get("overdue", False),
                    "at_risk": r.get("at_risk", False),
                }
                for tid, r in risk_map.items()
            ],
        }

    def process_meeting(
        self,
        meeting_id: str,
        transcript: List[Dict[str, Any]],
        reference_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process an entire meeting batch and return structured output.
        """
        if not meeting_id:
            return {"status": "error", "error_code": "MISSING_MEETING_ID", "message": "meeting_id required."}

        if not transcript:
            return {"status": "error", "error_code": "INVALID_TRANSCRIPT", "message": "Transcript is empty."}

        ref_date = reference_date or (metadata or {}).get("reference_date", "2026-09-17")
        self._active_metadata[meeting_id] = {"reference_date": ref_date, **(metadata or {})}

        # Stream chunks through the incremental processor
        for seg in transcript:
            self.process_transcript_chunk(
                meeting_id=meeting_id,
                speaker=seg.get("speaker", "Unknown"),
                timestamp=seg.get("timestamp") or seg.get("start_time", "00:00:00"),
                text=seg.get("text", ""),
                segment_id=seg.get("segment_id"),
                reference_date=ref_date,
            )

        return self.finalize_meeting(meeting_id=meeting_id, reference_date=ref_date)


# Global singleton engine for shared memory
_GLOBAL_ENGINE = MeetingIntelligenceEngine()


def run_pipeline(
    transcript: list[dict[str, str]],
    meeting_id: str,
    reference_date: str,
    existing_tasks: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Run pipeline. Maintains exact backward-compatible signature and output shape.
    """
    # 1. Task and decision extraction
    extracted = extract_meeting_items(
        transcript,
        meeting_id,
        reference_date
    )
    tasks = extracted["tasks"]
    decisions = extracted["decisions"]

    # Clean up extracted tasks
    for task in tasks:
        if task["state"]:
            task["state"] = task["state"].capitalize()
        task["depends_on"] = []

    # 2. Entity Resolution (Match only against PREVIOUS meetings)
    if existing_tasks:
        for task in tasks:
            match = find_best_semantic_match(
                task,
                existing_tasks,
                threshold=0.50
            )
            task["matched_existing_task_id"] = match["matched_existing_task_id"]
            task["match_confidence"] = match["match_confidence"]

    # 3. Dependency extraction and linking
    dependencies = []
    for segment in transcript:
        dependency = extract_dependency_statement(segment["text"])
        if dependency:
            linked = link_dependency_semantically(
                dependency,
                tasks,
                threshold=0.50
            )
            dependencies.append({
                "source_segment_id": segment["segment_id"],
                **linked
            })

    # 4. Build dependency graph strictly from resolved IDs
    graph = {task["task_id"]: [] for task in tasks if task.get("task_id")}

    for dependency in dependencies:
        task_id = dependency["task_id"]
        depends_on = dependency["depends_on"]
        if task_id and depends_on:
            if task_id not in graph:
                graph[task_id] = []
            if depends_on not in graph[task_id]:
                graph[task_id].append(depends_on)

    for task in tasks:
        task["depends_on"] = graph.get(task["task_id"], [])
        if task.get("state"):
            task["state"] = task["state"].capitalize()

    # 5. State Reconstruction
    state_results = {}
    for task in tasks:
        if task["state"] is not None:
            update = {
                "state": task["state"],
                "meeting_id": task["meeting_id"],
                "meeting_date": reference_date,
                "source_segment_id": task["source_segment_id"],
                "text": next(
                    (
                        segment["text"]
                        for segment in transcript
                        if segment["segment_id"] == task["source_segment_id"]
                    ),
                    ""
                )
            }
            state_results[task["task_id"]] = reconstruct_task_state([update])

    # 6. Risk Analysis
    risk_results = analyze_dependency_risk(
        tasks,
        graph,
        current_date=reference_date
    )

    return {
        "meeting_id": meeting_id,
        "tasks": tasks,
        "decisions": decisions,
        "dependencies": dependencies,
        "dependency_graph": graph,
        "state_reconstruction": state_results,
        "risk_analysis": risk_results
    }


def process_transcript_chunk(
    meeting_id: str,
    speaker: str,
    timestamp: str,
    text: str,
    segment_id: Optional[str] = None,
    reference_date: Optional[str] = None,
) -> Dict[str, Any]:
    return _GLOBAL_ENGINE.process_transcript_chunk(
        meeting_id=meeting_id,
        speaker=speaker,
        timestamp=timestamp,
        text=text,
        segment_id=segment_id,
        reference_date=reference_date,
    )


def finalize_meeting(
    meeting_id: str,
    reference_date: Optional[str] = None,
) -> Dict[str, Any]:
    return _GLOBAL_ENGINE.finalize_meeting(
        meeting_id=meeting_id,
        reference_date=reference_date,
    )


def process_meeting(
    meeting_id: str,
    transcript: List[Dict[str, Any]],
    reference_date: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _GLOBAL_ENGINE.process_meeting(
        meeting_id=meeting_id,
        transcript=transcript,
        reference_date=reference_date,
        metadata=metadata,
    )


if __name__ == "__main__":
    with open(
        "ai_module/tests/sample_transcript.json",
        "r",
        encoding="utf-8"
    ) as file:
        sample_transcript = json.load(file)

    result = run_pipeline(
        sample_transcript,
        meeting_id="M1",
        reference_date="2026-09-17"
    )

    print(json.dumps(result, indent=2))