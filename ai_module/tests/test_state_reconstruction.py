from ai_module.state_reconstruction.state_reconstructor import (
    reconstruct_task_state
)


def test_state_reconstruction():

    task_updates = [
        {
            "state": "Assigned",
            "meeting_id": "M1",
            "meeting_date": "2026-09-01",
            "source_segment_id": "seg-101",
            "text": "The login module has been assigned to Rahul."
        },
        {
            "state": "In Progress",
            "meeting_id": "M2",
            "meeting_date": "2026-09-05",
            "source_segment_id": "seg-205",
            "text": "Rahul is working on the login module."
        },
        {
            "state": "Blocked",
            "meeting_id": "M3",
            "meeting_date": "2026-09-10",
            "source_segment_id": "seg-309",
            "text": "The login module is blocked because the API is not ready."
        },
        {
            "state": "Completed",
            "meeting_id": "M4",
            "meeting_date": "2026-09-15",
            "source_segment_id": "seg-412",
            "text": "The login module is completed."
        },
        {
            "state": "Reopened",
            "meeting_id": "M5",
            "meeting_date": "2026-09-18",
            "source_segment_id": "seg-518",
            "text": "The login module was reopened because of a bug."
        }
    ]

    result = reconstruct_task_state(
        task_updates
    )

    print("Task State History:")
    print()

    for item in result["history"]:
        print(
            f"{item['meeting_date']} | "
            f"{item['meeting_id']} | "
            f"{item['state']} | "
            f"Evidence: {item['source_segment_id']} | "
            f"Uncertain: {item['uncertain']}"
        )

    print()
    print("State Transitions:")
    print()

    for transition in result["transitions"]:
        print(
            f"{transition['from_state']} "
            f"-> "
            f"{transition['to_state']} | "
            f"Meeting: {transition['meeting_id']} | "
            f"Evidence: {transition['source_segment_id']}"
        )

    print()
    print("Contradictions:")
    print()

    for contradiction in result["contradictions"]:
        print(
            f"{contradiction['from_state']} "
            f"-> "
            f"{contradiction['to_state']} | "
            f"Previous Evidence: "
            f"{contradiction['previous_source_segment_id']} | "
            f"Current Evidence: "
            f"{contradiction['current_source_segment_id']}"
        )

    print()
    print(
        f"Current State: "
        f"{result['current_state']}"
    )

    # Basic reconstruction checks
    assert len(result["history"]) == 5
    assert len(result["transitions"]) == 4
    assert result["current_state"] == "Reopened"

    # Uncertainty checks
    assert all(
        item["uncertain"] is False
        for item in result["history"]
    )

    # Combined contradiction check
    assert "contradictions" in result
    assert len(result["contradictions"]) == 1

    print()
    print("Combined State Reconstruction Test Passed!")


if __name__ == "__main__":
    test_state_reconstruction()