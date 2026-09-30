"""
Dependency extraction and linking module.

Extracts directed dependency statements from natural language meeting conversations
and semantically links both sides to existing canonical task entities.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from ai_module.entity_resolution.semantic_matcher import semantic_similarity


def extract_dependency_statement(text: str) -> dict | None:
    """
    Extract a dependency relationship from natural language.

    Supported patterns:
    1. X depends on Y
    2. X cannot start until Y
    3. X is waiting for Y
    4. X is blocked because of Y
    5. X is blocked by Y
    6. cannot proceed with X until Y
    """
    if not text:
        return None

    patterns = [
        # X depends on Y
        r"(.+?)\s+depends on\s+(.+?)(?:\s+first)?[.!?]?$",
        # X cannot start until Y
        r"(.+?)\s+cannot\s+(?:start|begin)\s+until\s+(.+?)[.!?]?$",
        # X is waiting for Y
        r"(.+?)\s+is\s+waiting\s+(?:for|on)\s+(.+?)[.!?]?$",
        # X is blocked because of Y
        r"(.+?)\s+is\s+blocked\s+because\s+of\s+(.+?)[.!?]?$",
        # X is blocked by Y
        r"(.+?)\s+is\s+blocked\s+by\s+(.+?)[.!?]?$",
        # cannot proceed with X until Y
        r"cannot\s+proceed\s+with\s+(.+?)\s+until\s+(.+?)[.!?]?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                "task_description": match.group(1).strip(),
                "dependency_description": match.group(2).strip(),
            }

    return None


def normalize_text(text: str) -> str:
    """Normalize text for dependency keyword matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "to",
        "for", "of", "on", "in", "with", "first", "completed"
    }

    words = [word for word in text.split() if word not in stop_words]
    return " ".join(words)


def link_dependency_to_tasks(
    dependency: dict,
    tasks: list[dict]
) -> dict | None:
    """
    Link a dependency statement to existing task IDs using normalized keyword matching.
    """
    task_description = normalize_text(dependency["task_description"])
    dependency_description = normalize_text(dependency["dependency_description"])

    dependent_task_id = None
    dependency_task_id = None

    task_words = set(task_description.split())
    dependency_words = set(dependency_description.split())

    for task in tasks:
        desc_text = task.get("description") or task.get("canonical_description") or ""
        description = normalize_text(desc_text)
        description_words = set(description.split())

        # Match the task that depends on another task
        if task_words and task_words.issubset(description_words):
            dependent_task_id = task["task_id"]

        # Match the dependency task
        if dependency_words and dependency_words.issubset(description_words):
            dependency_task_id = task["task_id"]

    if not dependent_task_id or not dependency_task_id:
        return None

    return {
        "task_id": dependent_task_id,
        "depends_on": dependency_task_id,
    }


def find_best_semantic_task_match(
    description: str,
    tasks: list[dict],
    threshold: float = 0.50
) -> dict:
    """
    Find the existing task that is semantically most similar to a given description.
    """
    best_task_id = None
    best_confidence = 0.0

    for task in tasks:
        task_desc = task.get("description") or task.get("canonical_description") or ""
        score = semantic_similarity(description, task_desc)

        if score > best_confidence:
            best_confidence = score
            best_task_id = task["task_id"]

    if best_confidence >= threshold:
        return {
            "task_id": best_task_id,
            "confidence": round(best_confidence, 2),
        }

    return {
        "task_id": None,
        "confidence": round(best_confidence, 2),
    }


def link_dependency_semantically(
    dependency: dict,
    tasks: list[dict],
    threshold: float = 0.50
) -> dict:
    """
    Link both sides of a dependency statement to existing task IDs using semantic similarity.
    """
    dependent_task = find_best_semantic_task_match(
        dependency["task_description"],
        tasks,
        threshold,
    )

    dependency_task = find_best_semantic_task_match(
        dependency["dependency_description"],
        tasks,
        threshold,
    )

    # Prevent a task from depending on itself
    if (
        dependent_task["task_id"] is not None
        and dependent_task["task_id"] == dependency_task["task_id"]
    ):
        return {
            "task_id": dependent_task["task_id"],
            "depends_on": None,
            "task_confidence": dependent_task["confidence"],
            "dependency_confidence": dependency_task["confidence"],
        }

    return {
        "task_id": dependent_task["task_id"],
        "depends_on": dependency_task["task_id"],
        "task_confidence": dependent_task["confidence"],
        "dependency_confidence": dependency_task["confidence"],
    }