from ai_module.state_reconstruction.state_reconstructor import (
    detect_contradictions
)


def test_true_contradiction():

    task_updates = [
        {
            "state": "Completed",
            "meeting_id": "M1",
            "meeting_date": "2026-09-01",
            "source_segment_id": "seg-101",
            "text": "The login module is completed."
        },
        {
            "state": "Incomplete",
            "meeting_id": "M2",
            "meeting_date": "2026-09-05",
            "source_segment_id": "seg-205",
            "text": "The login module is still incomplete."
        }
    ]

    contradictions = detect_contradictions(
        task_updates
    )

    print("True Contradiction Detection:")
    print()

    for contradiction in contradictions:

        print(
            f"{contradiction['from_state']} "
            f"-> "
            f"{contradiction['to_state']}"
        )

        print(
            f"Previous Meeting: "
            f"{contradiction['previous_meeting_id']}"
        )

        print(
            f"Current Meeting: "
            f"{contradiction['current_meeting_id']}"
        )

        print(
            f"Previous Evidence: "
            f"{contradiction['previous_source_segment_id']}"
        )

        print(
            f"Current Evidence: "
            f"{contradiction['current_source_segment_id']}"
        )

        print()

    assert len(contradictions) == 1

    assert contradictions[0]["from_state"] == "Completed"
    assert contradictions[0]["to_state"] == "Incomplete"

    assert (
        contradictions[0]["previous_source_segment_id"]
        == "seg-101"
    )

    assert (
        contradictions[0]["current_source_segment_id"]
        == "seg-205"
    )

    print("True Contradiction Test Passed!")


if __name__ == "__main__":
    test_true_contradiction()