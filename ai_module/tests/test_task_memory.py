from ai_module.state_reconstruction.task_memory import TaskMemory


def test_multi_meeting_task_memory():

    memory = TaskMemory()

    task = {
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
        task=task,
        meeting_id="M1",
        meeting_date="2026-09-01",
        evidence_text="Rahul will implement the login module."
    )

    task["state"] = "In Progress"

    memory.add_task_update(
        task_id="T1",
        task=task,
        meeting_id="M2",
        meeting_date="2026-09-05",
        evidence_text="The login module is currently in progress."
    )

    task["state"] = "Blocked"

    memory.add_task_update(
        task_id="T1",
        task=task,
        meeting_id="M3",
        meeting_date="2026-09-10",
        evidence_text="The login module is blocked by the API."
    )

    task["state"] = "Completed"

    memory.add_task_update(
        task_id="T1",
        task=task,
        meeting_id="M4",
        meeting_date="2026-09-15",
        evidence_text="The login module has been completed."
    )

    result = memory.get_task("T1")

    print("Task:", result["description"])
    print("Owner:", result["owner"])
    print("Deadline:", result["deadline"])
    print()

    print("History:")

    for update in result["history"]:
        print(
            update["meeting_id"],
            "|",
            update["meeting_date"],
            "|",
            update["state"],
            "|",
            update["source_segment_id"]
        )

    assert len(result["history"]) == 4
    assert result["history"][0]["state"] == "Assigned"
    assert result["history"][1]["state"] == "In Progress"
    assert result["history"][2]["state"] == "Blocked"
    assert result["history"][3]["state"] == "Completed"

    print()
    print("Multi-Meeting Task Memory Test Passed!")


if __name__ == "__main__":
    test_multi_meeting_task_memory()