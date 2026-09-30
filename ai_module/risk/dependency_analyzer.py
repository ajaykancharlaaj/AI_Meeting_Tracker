def build_dependency_graph(tasks: list[dict]) -> dict:
    """
    Build a dependency graph from task data.

    Each task can contain a list of task IDs
    that it depends on.
    """

    graph = {}

    for task in tasks:
        task_id = task["task_id"]
        dependencies = task.get("depends_on", [])

        graph[task_id] = dependencies

    return graph


def get_direct_dependencies(
    task_id: str,
    graph: dict
) -> list[str]:
    """
    Return the tasks that the given task directly depends on.
    """

    return graph.get(task_id, [])


def get_downstream_tasks(
    task_id: str,
    graph: dict
) -> list[str]:
    """
    Find all tasks that are directly or indirectly
    affected by the given task.

    Example:

        T1 -> T2 -> T3 -> T4

    If T1 is blocked, the downstream tasks are:

        T2, T3, T4
    """

    downstream = []

    # Find tasks that directly depend on task_id
    for current_task, dependencies in graph.items():

        if task_id in dependencies:
            downstream.append(current_task)

            # Recursively find tasks depending on this task
            downstream.extend(
                get_downstream_tasks(
                    current_task,
                    graph
                )
            )

    return downstream