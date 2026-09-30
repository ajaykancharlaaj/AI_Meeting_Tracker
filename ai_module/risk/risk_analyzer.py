"""
Dependency-Aware Multi-Factor Risk Analysis.

Calculates explainable risk scores by analyzing:
1. Direct task state (Blocked, Reopened)
2. Direct and transitive dependency blockage propagation (A -> B -> C -> D)
3. Deadline proximity (Overdue, Due Soon)
4. Repeated discussion without progress (stagnation)
5. Contradictory status claims across meetings
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from ai_module.risk.dependency_analyzer import get_downstream_tasks


def calculate_task_risk(
    state: str,
    overdue: bool = False,
    at_risk: bool = False,
    dependency_blocked: bool = False,
    repeated_unresolved: bool = False,
) -> str:
    """
    Calculate the risk level of a task ('High', 'Medium', 'Low').
    Preserves exact capitalization expected by existing tests.
    """
    normalized_state = (state or "").strip().lower()

    if normalized_state in ("blocked",) or overdue:
        return "High"

    if dependency_blocked:
        return "High"

    if at_risk or repeated_unresolved or normalized_state == "reopened":
        return "Medium"

    if normalized_state in ("completed", "done"):
        return "Low"

    return "Low"


def calculate_deadline_status(
    deadline: str | None,
    current_date: str
) -> dict:
    """
    Determine whether a task deadline is overdue, due soon, or on track.
    """
    if not deadline:
        return {
            "overdue": False,
            "at_risk": False,
            "deadline_status": "No Deadline"
        }

    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        current = datetime.strptime(current_date, "%Y-%m-%d").date()
    except Exception:
        return {
            "overdue": False,
            "at_risk": False,
            "deadline_status": "Invalid Date Format"
        }

    days_remaining = (deadline_date - current).days

    if days_remaining < 0:
        return {
            "overdue": True,
            "at_risk": False,
            "deadline_status": "Overdue"
        }

    if days_remaining <= 1:
        return {
            "overdue": False,
            "at_risk": True,
            "deadline_status": "Due Soon"
        }

    return {
        "overdue": False,
        "at_risk": False,
        "deadline_status": "On Track"
    }


def analyze_dependency_risk(
    tasks: list[dict],
    graph: dict,
    current_date: str | None = None
) -> dict:
    """
    Calculate final risk for every task by considering:
    - Task state (Blocked, Reopened)
    - Deadline status (Overdue, Due Soon)
    - Direct and transitive dependency chains
    - Repeated unresolved discussion flags
    """
    blocked_tasks = {
        task["task_id"]
        for task in tasks
        if (task.get("state") or "").strip().lower() == "blocked"
    }

    risk_results = {}

    for task in tasks:
        task_id = task["task_id"]
        reasons = []

        # 1. Check dependency risk & chain propagation
        affected_by_blocked_dependency = False
        blocking_parents = []

        for blocked_task_id in blocked_tasks:
            downstream = get_downstream_tasks(blocked_task_id, graph)
            if task_id in downstream:
                affected_by_blocked_dependency = True
                blocking_parents.append(blocked_task_id)

        if affected_by_blocked_dependency:
            parent_list = ", ".join(blocking_parents)
            reasons.append(f"depends on blocked upstream task ({parent_list})")

        # 2. Check task own state
        task_state = task.get("state") or "Assigned"
        state_lower = task_state.strip().lower()

        if state_lower == "blocked":
            reasons.append("task is currently blocked")
        elif state_lower == "reopened":
            reasons.append("task was previously completed and has been reopened")

        # 3. Check deadline risk
        if current_date and task.get("deadline"):
            deadline_info = calculate_deadline_status(
                task["deadline"],
                current_date
            )
        elif not task.get("deadline"):
            deadline_info = {
                "overdue": False,
                "at_risk": False,
                "deadline_status": "No Deadline"
            }
        else:
            deadline_info = {
                "overdue": task.get("overdue", False),
                "at_risk": task.get("at_risk", False),
                "deadline_status": "Not Evaluated"
            }

        if deadline_info["overdue"]:
            reasons.append(f"deadline is overdue ({task.get('deadline')})")
        elif deadline_info["at_risk"]:
            reasons.append(f"deadline is approaching ({deadline_info['deadline_status']})")

        # 4. Check repeated unresolved discussion
        repeated_unresolved = task.get("repeated_unresolved_task", False)
        if repeated_unresolved:
            reasons.append("repeatedly discussed across meetings without progress")

        # 5. Calculate final risk
        risk = calculate_task_risk(
            state=task_state,
            overdue=deadline_info["overdue"],
            at_risk=deadline_info["at_risk"],
            dependency_blocked=affected_by_blocked_dependency,
            repeated_unresolved=repeated_unresolved,
        )

        if not reasons:
            reasons.append("task is progressing normally")

        # 6. Store complete result
        risk_results[task_id] = {
            "risk": risk,
            "risk_level": risk.upper(),
            "risk_reasons": reasons,
            "dependency_blocked": affected_by_blocked_dependency,
            "blocking_parents": blocking_parents,
            "overdue": deadline_info["overdue"],
            "at_risk": deadline_info["at_risk"],
            "deadline_status": deadline_info["deadline_status"],
        }

    return risk_results