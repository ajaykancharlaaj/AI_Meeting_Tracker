"""
Comprehensive Automated Test Suite covering all 16 Required Core Test Cases.

TEST 1: Same task, different wording.
TEST 2: Different tasks, similar wording.
TEST 3: Assigned -> In Progress.
TEST 4: In Progress -> Blocked.
TEST 5: Blocked -> In Progress.
TEST 6: In Progress -> Completed.
TEST 7: Completed -> Reopened.
TEST 8: Deadline changed.
TEST 9: Contradictory statements.
TEST 10: Uncertain statement.
TEST 11: Dependency propagation.
TEST 12: Repeated unresolved task.
TEST 13: Low-confidence entity match.
TEST 14: Missing owner.
TEST 15: Missing deadline.
TEST 16: Incremental transcript chunks.
"""

import sys
import unittest
from ai_module.entity_resolution.semantic_matcher import (
    find_best_semantic_match,
    resolve_task_identity,
    actions_compatible,
)
from ai_module.extraction.deadline_normalizer import (
    normalize_deadline,
    detect_deadline_change,
    extract_deadline_info,
)
from ai_module.extraction.progress_extractor import extract_progress
from ai_module.state_reconstruction.state_reconstructor import (
    detect_uncertainty,
    analyze_uncertainty,
    reconstruct_task_state,
    detect_contradictions,
    detect_state_contradictions_rich,
)
from ai_module.risk.dependency_analyzer import (
    build_dependency_graph,
    get_downstream_tasks,
)
from ai_module.risk.risk_analyzer import (
    analyze_dependency_risk,
    calculate_task_risk,
)
from ai_module.memory.task_memory import TaskMemory
from ai_module.pipeline import MeetingIntelligenceEngine


class TestMeetingTracker16(unittest.TestCase):

    def test_01_same_task_different_wording(self):
        """TEST 1: Same task, different wording."""
        existing_tasks = [
            {"task_id": "T001", "description": "Implement login module", "owner": "Rahul"},
            {"task_id": "T002", "description": "Create payment gateway", "owner": "Priya"},
        ]
        new_task = {
            "description": "Complete authentication functionality",
            "owner": "Rahul",
        }
        result = resolve_task_identity(new_task, existing_tasks, threshold=0.50)
        self.assertEqual(result["matched_existing_task_id"], "T001")
        self.assertGreaterEqual(result["match_confidence"], 0.50)
        self.assertTrue(any("semantic" in r for r in result["match_reason"]))

    def test_02_different_tasks_similar_wording(self):
        """TEST 2: Different tasks, similar wording with incompatible actions."""
        existing_tasks = [
            {"task_id": "T001", "description": "Design dashboard wireframes"},
        ]
        new_task = {
            "description": "Fix dashboard UI bug",
        }
        # Incompatible action: 'design' vs 'fixing'
        self.assertFalse(actions_compatible(new_task["description"], existing_tasks[0]["description"]))
        result = resolve_task_identity(new_task, existing_tasks, threshold=0.50)
        self.assertIsNone(result["matched_existing_task_id"])

    def test_03_assigned_to_in_progress(self):
        """TEST 3: Assigned -> In Progress."""
        memory = TaskMemory()
        task_id = memory.add_new_task({
            "task_id": "T001",
            "description": "Develop login module",
            "state": "Assigned",
            "meeting_id": "M001",
        })
        memory.add_task_update(
            task_id=task_id,
            task={"state": "In Progress"},
            meeting_id="M002",
            meeting_date="2026-09-05",
            evidence_text="Rahul is currently working on the login module.",
        )
        task = memory.get_task(task_id)
        self.assertEqual(task["current_state"], "In Progress")
        history_states = [h["state"] for h in task["history"]]
        self.assertEqual(history_states, ["Assigned", "In Progress"])

    def test_04_in_progress_to_blocked(self):
        """TEST 4: In Progress -> Blocked."""
        memory = TaskMemory()
        task_id = "T001"
        memory.add_task_update(
            task_id=task_id,
            task={"description": "Login module", "state": "In Progress"},
            meeting_id="M001",
            meeting_date="2026-09-01",
            evidence_text="Working on login.",
        )
        memory.add_task_update(
            task_id=task_id,
            task={"state": "Blocked"},
            meeting_id="M002",
            meeting_date="2026-09-05",
            evidence_text="Login module is blocked by the API.",
        )
        task = memory.get_task(task_id)
        self.assertEqual(task["current_state"], "Blocked")
        self.assertEqual(len(task["history"]), 2)
        self.assertEqual(task["history"][0]["state"], "In Progress")
        self.assertEqual(task["history"][1]["state"], "Blocked")

    def test_05_blocked_to_in_progress(self):
        """TEST 5: Blocked -> In Progress."""
        updates = [
            {"state": "Blocked", "meeting_id": "M1", "meeting_date": "2026-09-01", "text": "Blocked by auth API"},
            {"state": "In Progress", "meeting_id": "M2", "meeting_date": "2026-09-05", "text": "Unblocked and resumed"},
        ]
        reconstruction = reconstruct_task_state(updates)
        self.assertEqual(reconstruction["current_state"], "In Progress")
        self.assertEqual(len(reconstruction["transitions"]), 1)
        self.assertEqual(reconstruction["transitions"][0]["from_state"], "Blocked")
        self.assertEqual(reconstruction["transitions"][0]["to_state"], "In Progress")

    def test_06_in_progress_to_completed(self):
        """TEST 6: In Progress -> Completed."""
        updates = [
            {"state": "In Progress", "meeting_id": "M1", "meeting_date": "2026-09-01", "text": "Working on it"},
            {"state": "Completed", "meeting_id": "M2", "meeting_date": "2026-09-05", "text": "Completed the task"},
        ]
        reconstruction = reconstruct_task_state(updates)
        self.assertEqual(reconstruction["current_state"], "Completed")
        self.assertEqual(reconstruction["transitions"][0]["from_state"], "In Progress")
        self.assertEqual(reconstruction["transitions"][0]["to_state"], "Completed")

    def test_07_completed_to_reopened(self):
        """TEST 7: Completed -> Reopened."""
        updates = [
            {"state": "Completed", "meeting_id": "M1", "meeting_date": "2026-09-01", "text": "Task was completed"},
            {"state": "Reopened", "meeting_id": "M2", "meeting_date": "2026-09-05", "text": "Found a bug, reopened"},
        ]
        reconstruction = reconstruct_task_state(updates)
        self.assertEqual(reconstruction["current_state"], "Reopened")
        self.assertEqual(reconstruction["transitions"][0]["from_state"], "Completed")
        self.assertEqual(reconstruction["transitions"][0]["to_state"], "Reopened")

    def test_08_deadline_changed(self):
        """TEST 8: Deadline changed."""
        ref_date = "2026-09-17"
        initial_deadline = normalize_deadline("Friday, September 18", ref_date)
        self.assertEqual(initial_deadline, "2026-09-18")

        change_text = "The deadline moved to Monday"
        is_change = detect_deadline_change(change_text)
        self.assertTrue(is_change)
        new_deadline = normalize_deadline("Monday", ref_date)
        self.assertIsNotNone(new_deadline)

        memory = TaskMemory()
        task_id = "T001"
        memory.add_new_task({"task_id": task_id, "description": "Design dashboard", "deadline": initial_deadline})
        memory.add_task_update(
            task_id=task_id,
            task={"deadline": new_deadline},
            meeting_id="M2",
            meeting_date="2026-09-20",
            evidence_text=change_text,
        )
        task = memory.get_task(task_id)
        self.assertEqual(task["current_deadline"], new_deadline)
        self.assertEqual(len(task["deadline_history"]), 2)
        self.assertEqual(task["deadline_history"][1]["change_type"], "deadline_changed")

    def test_09_contradictory_statements(self):
        """TEST 9: Contradictory statements."""
        updates = [
            {"meeting_id": "M1", "speaker": "Rahul", "state": "Completed", "text": "The payment service is completed.", "meeting_date": "2026-09-01"},
            {"meeting_id": "M2", "speaker": "Priya", "state": "Incomplete", "text": "The payment service is still incomplete.", "meeting_date": "2026-09-05"},
        ]
        rich_contras = detect_state_contradictions_rich("T001", updates)
        self.assertEqual(len(rich_contras), 1)
        contra = rich_contras[0]
        self.assertEqual(contra["type"], "state_contradiction")
        self.assertEqual(contra["task_id"], "T001")
        self.assertTrue(contra["requires_review"])
        self.assertEqual(len(contra["claims"]), 2)
        self.assertEqual(contra["claims"][0]["state"], "Completed")
        self.assertEqual(contra["claims"][1]["state"], "Incomplete")

    def test_10_uncertain_statement(self):
        """TEST 10: Uncertain statement."""
        text = "I think the login module is probably completed."
        is_uncertain = detect_uncertainty(text)
        self.assertTrue(is_uncertain)

        analysis = analyze_uncertainty(text)
        self.assertEqual(analysis["certainty"], "uncertain")
        self.assertLess(analysis["confidence"], 0.90)

    def test_11_dependency_propagation(self):
        """TEST 11: Dependency propagation (T1 -> T2 -> T3 -> T4)."""
        tasks = [
            {"task_id": "T1", "state": "Blocked", "depends_on": []},
            {"task_id": "T2", "state": "In Progress", "depends_on": ["T1"]},
            {"task_id": "T3", "state": "In Progress", "depends_on": ["T2"]},
            {"task_id": "T4", "state": "In Progress", "depends_on": ["T3"]},
        ]
        graph = build_dependency_graph(tasks)
        # Downstream of T1 should be T2, T3, T4
        downstream = get_downstream_tasks("T1", graph)
        self.assertIn("T2", downstream)
        self.assertIn("T3", downstream)
        self.assertIn("T4", downstream)

        risk_results = analyze_dependency_risk(tasks, graph)
        self.assertEqual(risk_results["T1"]["risk"], "High")
        self.assertEqual(risk_results["T2"]["risk"], "High")
        self.assertTrue(risk_results["T2"]["dependency_blocked"])
        self.assertEqual(risk_results["T3"]["risk"], "High")
        self.assertTrue(risk_results["T3"]["dependency_blocked"])
        self.assertEqual(risk_results["T4"]["risk"], "High")
        self.assertTrue(risk_results["T4"]["dependency_blocked"])

    def test_12_repeated_unresolved_task(self):
        """TEST 12: Repeated unresolved task detection."""
        memory = TaskMemory()
        task_id = "T001"
        # Discussed in M1, M2, M3 with same incomplete state
        memory.add_task_update(task_id, {"description": "API Integration", "state": "In Progress"}, "M1", "2026-09-01", "Pending API integration")
        memory.add_task_update(task_id, {"description": "API Integration", "state": "In Progress"}, "M2", "2026-09-05", "API integration pending")
        memory.add_task_update(task_id, {"description": "API Integration", "state": "In Progress"}, "M3", "2026-09-10", "API integration still pending")

        task = memory.get_task(task_id)
        self.assertTrue(task["repeated_unresolved_task"])

    def test_13_low_confidence_entity_match(self):
        """TEST 13: Low-confidence entity match (do not force false match)."""
        existing_tasks = [
            {"task_id": "T001", "description": "Implement authentication microservice", "owner": "Rahul"},
        ]
        new_task = {
            "description": "Order team lunch for Friday",
            "owner": "Sarah",
        }
        result = resolve_task_identity(new_task, existing_tasks, threshold=0.50)
        self.assertIsNone(result["matched_existing_task_id"])
        self.assertLess(result["match_confidence"], 0.50)

    def test_14_missing_owner(self):
        """TEST 14: Missing owner handling."""
        memory = TaskMemory()
        task_id = memory.add_new_task({
            "task_id": "T001",
            "description": "Prepare production deployment checklist",
            "owner": None,
        })
        task = memory.get_task(task_id)
        self.assertIsNone(task["owner"])

        # Owner later assigned in M2
        memory.add_task_update(task_id, {"owner": "Daniel"}, "M2", "2026-09-05", "Daniel will own the checklist")
        updated_task = memory.get_task(task_id)
        self.assertEqual(updated_task["owner"], "Daniel")

    def test_15_missing_deadline(self):
        """TEST 15: Missing deadline handling."""
        memory = TaskMemory()
        task_id = memory.add_new_task({
            "task_id": "T001",
            "description": "Investigate memory leak",
            "deadline": None,
        })
        task = memory.get_task(task_id)
        self.assertIsNone(task["current_deadline"])
        risk = analyze_dependency_risk([task], {task_id: []})
        self.assertEqual(risk[task_id]["deadline_status"], "No Deadline")

    def test_16_incremental_transcript_chunks(self):
        """TEST 16: Incremental transcript chunk streaming."""
        engine = MeetingIntelligenceEngine()
        meeting_id = "M_STREAM_01"

        # Chunk 1
        res1 = engine.process_transcript_chunk(
            meeting_id=meeting_id,
            speaker="Rahul",
            timestamp="00:01:10",
            text="I will implement the login module by next Friday.",
        )
        self.assertEqual(res1["status"], "success")
        self.assertEqual(len(res1["extracted_tasks"]), 1)
        created_task_id = res1["extracted_tasks"][0]["task_id"]

        # Chunk 2
        res2 = engine.process_transcript_chunk(
            meeting_id=meeting_id,
            speaker="Rahul",
            timestamp="00:05:30",
            text="The authentication functionality is around 50 percent done.",
        )
        self.assertEqual(res2["status"], "success")
        self.assertEqual(res2["extracted_tasks"][0]["matched_existing_task_id"], created_task_id)

        # Finalize meeting
        final_summary = engine.finalize_meeting(meeting_id)
        self.assertEqual(final_summary["meeting_id"], meeting_id)
        self.assertEqual(final_summary["processing_status"], "completed")
        self.assertEqual(len(final_summary["tasks"]), 1)
        self.assertEqual(final_summary["tasks"][0]["task_id"], created_task_id)
        self.assertEqual(final_summary["tasks"][0]["progress"], 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
