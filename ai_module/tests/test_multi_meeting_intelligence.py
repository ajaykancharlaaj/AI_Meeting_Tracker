from ai_module.entity_resolution.semantic_matcher import (
    find_best_semantic_match
)
from ai_module.state_reconstruction.task_memory import TaskMemory


def test_entity_resolution_with_task_memory():

    memory = TaskMemory()

    # -------------------------
    # MEETING 1
    # -------------------------

    meeting_1_task = {
        "task_id": "T1",
        "description": "Implement login module",
        "owner": "Rahul",
        "deadline": "2026-09-20",
        "state": "Assigned",
        "source_segment_id": "seg-101",
        "depends_on": []
    }

    memory.add_task_update(
        task_id="T1",
        task=meeting_1_task,
        meeting_id="M1",
        meeting_date="2026-09-01",
        evidence_text="Rahul will implement the login module."
    )

    # -------------------------
    # MEETING 2
    # -------------------------

    meeting_2_task = {
        "task_id": "TEMP-M2-1",
        "description": "Complete authentication functionality",
        "owner": "Rahul",
        "deadline": None,
        "state": "In Progress",
        "source_segment_id": "seg-205",
        "depends_on": []
    }

    existing_tasks = memory.get_all_tasks()

    match = find_best_semantic_match(
        meeting_2_task,
        existing_tasks,
        threshold=0.50
    )

    print("Meeting 2 Entity Resolution:")
    print("New Task:", meeting_2_task["description"])
    print("Matched Task:", match["matched_existing_task_id"])
    print("Confidence:", match["match_confidence"])

    assert match["matched_existing_task_id"] == "T1"

    # Add Meeting 2 update to the matched task
    matched_task_id = match["matched_existing_task_id"]

    memory.add_task_update(
        task_id=matched_task_id,
        task=meeting_2_task,
        meeting_id="M2",
        meeting_date="2026-09-05",
        evidence_text="The authentication functionality is currently in progress."
    )

    # -------------------------
    # VERIFY FINAL TASK
    # -------------------------

    result = memory.get_task("T1")

    print()
    print("Final Task:")
    print("Task ID:", result["task_id"])
    print("Description:", result["description"])
    print("Owner:", result["owner"])
    print("History:")

    for update in result["history"]:
        print(
            update["meeting_id"],
            "|",
            update["state"],
            "|",
            update["evidence"]
        )

    assert len(result["history"]) == 2
    assert result["history"][0]["state"] == "Assigned"
    assert result["history"][1]["state"] == "In Progress"

    print()
    print("Multi-Meeting Entity Resolution Test Passed!")


if __name__ == "__main__":
    test_entity_resolution_with_task_memory()