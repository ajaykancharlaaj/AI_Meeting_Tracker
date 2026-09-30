from ai_module.state_reconstruction.task_memory import TaskMemory
from ai_module.state_reconstruction.state_reconstructor import (
    reconstruct_task_state
)


def test_multi_meeting_state_reconstruction():

    memory = TaskMemory()

    states = [
        ("M1", "2026-09-01", "Assigned", "seg-101",
         "Rahul was assigned the login module."),

        ("M2", "2026-09-05", "In Progress", "seg-205",
         "The login module is in progress."),

        ("M3", "2026-09-10", "Blocked", "seg-309",
         "The login module is blocked by the API."),

        ("M4", "2026-09-15", "Completed", "seg-412",
         "The login module has been completed.")
    ]

    for meeting_id, date, state, segment_id, evidence in states:

        task = {
            "task_id": "T1",
            "description": "Implement login module",
            "owner": "Rahul",
            "deadline": "2026-09-20",
            "state": state,
            "source_segment_id": segment_id,
            "depends_on": []
        }

        memory.add_task_update(
            task_id="T1",
            task=task,
            meeting_id=meeting_id,
            meeting_date=date,
            evidence_text=evidence
        )

    stored_task = memory.get_task("T1")

    updates = [
        {
            "state": item["state"],
            "meeting_id": item["meeting_id"],
            "meeting_date": item["meeting_date"],
            "source_segment_id": item["source_segment_id"],
            "text": item["evidence"]
        }
        for item in stored_task["history"]
    ]

    result = reconstruct_task_state(updates)

    print("Task:", stored_task["description"])
    print()

    print("History:")
    for item in result["history"]:
        print(
            item["meeting_id"],
            "|",
            item["state"],
            "|",
            item["source_segment_id"]
        )

    print()
    print("Transitions:")
    for transition in result["transitions"]:
        print(
            transition["from_state"],
            "->",
            transition["to_state"]
        )

    print()
    print("Current State:", result["current_state"])
    print("Contradictions:", result["contradictions"])

    assert len(result["history"]) == 4
    assert len(result["transitions"]) == 3
    assert result["current_state"] == "Completed"
    assert len(result["contradictions"]) == 0

    print()
    print("Multi-Meeting State Reconstruction Test Passed!")


if __name__ == "__main__":
    test_multi_meeting_state_reconstruction()