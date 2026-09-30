from ai_module.state_reconstruction.state_reconstructor import (
    reconstruct_task_state
)


def test_combined_state_reconstruction():

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
            "text": "Rahul is probably working on the login module."
        },
        {
            "state": "Completed",
            "meeting_id": "M3",
            "meeting_date": "2026-09-10",
            "source_segment_id": "seg-309",
            "text": "The login module is completed."
        },
        {
            "state": "Incomplete",
            "meeting_id": "M4",
            "meeting_date": "2026-09-15",
            "source_segment_id": "seg-412",
            "text": "The login module is still incomplete."
        }
    ]

    result = reconstruct_task_state(
        task_updates
    )

    print("Combined State Reconstruction:")
    print()

    print("History:")
    for item in result["history"]:
        print(
            f"{item['meeting_date']} | "
            f"{item['meeting_id']} | "
            f"{item['state']} | "
            f"Uncertain: {item['uncertain']} | "
            f"Evidence: {item['source_segment_id']}"
        )

    print()
    print("Transitions:")

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

    # -----------------------------------------
    # Assertions
    # -----------------------------------------

    assert len(result["history"]) == 4

    # M2 contains "probably"
    assert result["history"][1]["uncertain"] is True

    # Other statements are certain
    assert result["history"][0]["uncertain"] is False
    assert result["history"][2]["uncertain"] is False
    assert result["history"][3]["uncertain"] is False

    # Four states produce three transitions
    assert len(result["transitions"]) == 3

    # Completed -> Incomplete is a true contradiction
    assert len(result["contradictions"]) == 1

    assert (
        result["contradictions"][0]["from_state"]
        == "Completed"
    )

    assert (
        result["contradictions"][0]["to_state"]
        == "Incomplete"
    )

    assert (
        result["contradictions"][0]["previous_source_segment_id"]
        == "seg-309"
    )

    assert (
        result["contradictions"][0]["current_source_segment_id"]
        == "seg-412"
    )

    # Latest state
    assert result["current_state"] == "Incomplete"

    print()
    print("Combined State Reconstruction Test Passed!")


if __name__ == "__main__":
    test_combined_state_reconstruction()