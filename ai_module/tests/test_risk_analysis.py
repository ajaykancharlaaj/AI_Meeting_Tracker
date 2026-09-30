from ai_module.risk.risk_analyzer import (
    calculate_task_risk,
    analyze_dependency_risk
)

from ai_module.risk.dependency_analyzer import (
    build_dependency_graph
)


def test_dependency_aware_risk():

    tasks = [
        {
            "task_id": "T1",
            "description": "Develop payment API",
            "state": "Blocked",
            "depends_on": []
        },
        {
            "task_id": "T2",
            "description": "Implement login module",
            "state": "In Progress",
            "depends_on": ["T1"]
        },
        {
            "task_id": "T3",
            "description": "Test login module",
            "state": "In Progress",
            "depends_on": ["T2"]
        },
        {
            "task_id": "T4",
            "description": "Release application",
            "state": "In Progress",
            "depends_on": ["T3"]
        }
    ]

    graph = build_dependency_graph(tasks)

    results = analyze_dependency_risk(
        tasks,
        graph
    )

    print("Dependency-Aware Risk Results:")

    for task_id, result in results.items():
        print(
            f"{task_id} | "
            f"Risk: {result['risk']} | "
            f"Dependency Blocked: "
            f"{result['dependency_blocked']}"
        )

    print()

    # Verify risk levels
    assert results["T1"]["risk"] == "High"
    assert results["T2"]["risk"] == "High"
    assert results["T3"]["risk"] == "High"
    assert results["T4"]["risk"] == "High"

    # Verify dependency propagation
    assert results["T1"]["dependency_blocked"] is False
    assert results["T2"]["dependency_blocked"] is True
    assert results["T3"]["dependency_blocked"] is True
    assert results["T4"]["dependency_blocked"] is True


if __name__ == "__main__":
    test_dependency_aware_risk()
    print("Test Passed!")