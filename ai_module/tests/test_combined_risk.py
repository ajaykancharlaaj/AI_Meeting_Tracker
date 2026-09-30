from ai_module.risk.risk_analyzer import (
    analyze_dependency_risk
)

from ai_module.risk.dependency_analyzer import (
    build_dependency_graph
)


def test_combined_risk():

    tasks = [

        {
            "task_id": "T1",
            "description": "Develop payment API",
            "state": "Blocked",
            "deadline": "2026-09-15",
            "depends_on": []
        },

        {
            "task_id": "T2",
            "description": "Implement login module",
            "state": "In Progress",
            "deadline": "2026-09-18",
            "depends_on": ["T1"]
        },

        {
            "task_id": "T3",
            "description": "Test login module",
            "state": "In Progress",
            "deadline": "2026-09-25",
            "depends_on": ["T2"]
        },

        {
            "task_id": "T4",
            "description": "Release application",
            "state": "In Progress",
            "deadline": "2026-09-25",
            "depends_on": ["T3"]
        }
    ]

    current_date = "2026-09-17"

    graph = build_dependency_graph(tasks)

    results = analyze_dependency_risk(
        tasks,
        graph,
        current_date=current_date
    )

    print("Combined Risk Analysis:")
    print()

    for task_id, result in results.items():

        print(
            f"{task_id} | "
            f"Risk: {result['risk']} | "
            f"Deadline: {result['deadline_status']} | "
            f"Overdue: {result['overdue']} | "
            f"At Risk: {result['at_risk']} | "
            f"Dependency Blocked: "
            f"{result['dependency_blocked']}"
        )

    print()

    # T1: Blocked + overdue
    assert results["T1"]["risk"] == "High"
    assert results["T1"]["overdue"] is True
    assert results["T1"]["dependency_blocked"] is False

    # T2: Due tomorrow + blocked dependency
    assert results["T2"]["risk"] == "High"
    assert results["T2"]["at_risk"] is True
    assert results["T2"]["dependency_blocked"] is True

    # T3: Dependency chain is affected
    assert results["T3"]["risk"] == "High"
    assert results["T3"]["dependency_blocked"] is True

    # T4: Indirect dependency risk
    assert results["T4"]["risk"] == "High"
    assert results["T4"]["dependency_blocked"] is True

    print("Combined Risk Test Passed!")


if __name__ == "__main__":
    test_combined_risk()