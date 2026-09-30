from ai_module.risk.dependency_analyzer import (
    build_dependency_graph,
    get_direct_dependencies,
    get_downstream_tasks
)


def test_dependency_graph():

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

    print("Dependency Graph:")

    for task_id, dependencies in graph.items():
        print(
            f"{task_id} depends on: "
            f"{dependencies}"
        )

    print()

    print(
        "T1 Downstream Tasks:",
        get_downstream_tasks("T1", graph)
    )

    print(
        "T2 Downstream Tasks:",
        get_downstream_tasks("T2", graph)
    )

    print(
        "T3 Downstream Tasks:",
        get_downstream_tasks("T3", graph)
    )

    print()

    # Verify direct dependencies
    assert get_direct_dependencies("T1", graph) == []
    assert get_direct_dependencies("T2", graph) == ["T1"]
    assert get_direct_dependencies("T3", graph) == ["T2"]
    assert get_direct_dependencies("T4", graph) == ["T3"]

    # Verify downstream dependencies
    assert get_downstream_tasks("T1", graph) == ["T2", "T3", "T4"]
    assert get_downstream_tasks("T2", graph) == ["T3", "T4"]
    assert get_downstream_tasks("T3", graph) == ["T4"]


if __name__ == "__main__":
    test_dependency_graph()
    print()
    print("Test Passed!")