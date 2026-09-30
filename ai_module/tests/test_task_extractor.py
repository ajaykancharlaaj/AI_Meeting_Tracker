import json

from ai_module.extraction.task_extractor import extract_meeting_items


def test_task_extraction_with_deadlines():

    with open(
        "ai_module/tests/sample_transcript.json",
        "r",
        encoding="utf-8"
    ) as file:
        transcript = json.load(file)

    result = extract_meeting_items(
        transcript,
        meeting_id="M1",
        reference_date="2026-09-17"
    )

    print("Extracted Tasks:")
    print()

    for task in result["tasks"]:
        print(
            f"Task: {task['description']} | "
            f"Owner: {task['owner']} | "
            f"Deadline: {task['deadline']} | "
            f"State: {task['state']}"
        )

    print()
    print("Extracted Decisions:")
    print()

    for decision in result["decisions"]:
        print(
            f"Decision: {decision['description']}"
        )

    print()

    dashboard_task = next(
        task for task in result["tasks"]
        if task["owner"] == "Maya"
    )

    assert dashboard_task["deadline"] == "2026-09-18"

    leo_task = next(
        task for task in result["tasks"]
        if task["owner"] == "Leo Martin"
    )

    assert leo_task["deadline"] == "2026-09-17"

    print("Task Extraction + Deadline Normalization Test Passed!")


if __name__ == "__main__":
    test_task_extraction_with_deadlines()