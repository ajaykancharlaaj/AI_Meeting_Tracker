from ai_module.risk.risk_analyzer import (
    calculate_deadline_status
)


def test_deadline_status():

    # Overdue
    result = calculate_deadline_status(
        "2026-09-15",
        "2026-09-17"
    )

    print("Overdue Test:")
    print(result)

    assert result["overdue"] is True
    assert result["at_risk"] is False
    assert result["deadline_status"] == "Overdue"

    # Due tomorrow
    result = calculate_deadline_status(
        "2026-09-18",
        "2026-09-17"
    )

    print()
    print("Due Soon Test:")
    print(result)

    assert result["overdue"] is False
    assert result["at_risk"] is True
    assert result["deadline_status"] == "Due Soon"

    # On track
    result = calculate_deadline_status(
        "2026-09-25",
        "2026-09-17"
    )

    print()
    print("On Track Test:")
    print(result)

    assert result["overdue"] is False
    assert result["at_risk"] is False
    assert result["deadline_status"] == "On Track"

    # No deadline
    result = calculate_deadline_status(
        None,
        "2026-09-17"
    )

    print()
    print("No Deadline Test:")
    print(result)

    assert result["overdue"] is False
    assert result["at_risk"] is False
    assert result["deadline_status"] == "No Deadline"


if __name__ == "__main__":
    test_deadline_status()
    print()
    print("Deadline Risk Test Passed!")