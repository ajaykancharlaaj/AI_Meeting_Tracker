"""
Semantic Matcher & Multi-Factor Entity Resolution Engine.

Implements cross-meeting task identity resolution using:
- SentenceTransformer ('all-MiniLM-L6-v2') embeddings with cosine similarity
- In-memory embedding caching to eliminate redundant computations
- Action category compatibility checks
- Keyword & entity token overlap
- Owner compatibility & project context bonuses
- Detailed match explanations (match_reason) and review flagging (requires_review)
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure offline hub operation if possible to avoid network latency/certificate issues
os.environ.setdefault("HF_HUB_OFFLINE", "1")

try:
    model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
except Exception:
    model = SentenceTransformer("all-MiniLM-L6-v2")

# Global embedding cache: string -> numpy.ndarray
_EMBEDDING_CACHE: Dict[str, np.ndarray] = {}
# Task ID to embedding cache
_TASK_EMBEDDING_CACHE: Dict[str, np.ndarray] = {}


def get_embedding(text: str) -> np.ndarray:
    """
    Convert text into a semantic embedding with in-memory caching.
    """
    if not text or not text.strip():
        # Return zeros vector of correct dimension (384 for all-MiniLM-L6-v2)
        return np.zeros(384, dtype=np.float32)

    cleaned = text.strip()
    if cleaned in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cleaned]

    emb = model.encode(cleaned)
    _EMBEDDING_CACHE[cleaned] = emb
    return emb


def cache_task_embedding(task_id: str, text: str) -> np.ndarray:
    """Cache embedding for an existing canonical task ID."""
    emb = get_embedding(text)
    _TASK_EMBEDDING_CACHE[task_id] = emb
    return emb


def get_cached_task_embedding(task_id: str, text: Optional[str] = None) -> np.ndarray:
    """Retrieve or compute cached embedding for a task."""
    if task_id in _TASK_EMBEDDING_CACHE:
        return _TASK_EMBEDDING_CACHE[task_id]
    if text:
        return cache_task_embedding(task_id, text)
    return np.zeros(384, dtype=np.float32)


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts using cosine similarity.
    """
    if not text1 or not text2:
        return 0.0

    embedding1 = get_embedding(text1)
    embedding2 = get_embedding(text2)

    score = cosine_similarity([embedding1], [embedding2])[0][0]
    return float(max(0.0, min(1.0, score)))


def extract_action(text: str) -> str:
    """
    Identify the action category of a task.
    """
    if not text:
        return ""
    text_lower = text.lower()

    action_groups = {
        "development": ["implement", "develop", "build", "create", "construct", "code"],
        "testing": ["test", "verify", "validate", "qa", "check"],
        "fixing": ["fix", "debug", "resolve", "patch", "repair"],
        "design": ["design", "redesign", "mockup", "wireframe", "prototype"],
        "deployment": ["deploy", "release", "publish", "rollout", "host"],
        "update": ["update", "modify", "change", "refactor", "revamp"],
    }

    for category, actions in action_groups.items():
        for action in actions:
            if re.search(r"\b" + action + r"\b", text_lower):
                return category

    return ""


def action_similarity(text1: str, text2: str) -> float:
    """
    Compare the main actions of two task descriptions.
    """
    action1 = extract_action(text1)
    action2 = extract_action(text2)

    if action1 and action1 == action2:
        return 1.0
    if action1 and action2:
        return 0.0
    return 0.5


def actions_compatible(text1: str, text2: str) -> bool:
    """
    Determine whether two task descriptions have compatible action categories.
    If both actions are known and different, they are treated as different work items.
    """
    action1 = extract_action(text1)
    action2 = extract_action(text2)

    if not action1 or not action2:
        return True
    if action1 != action2:
        return False
    return True


def extract_keywords(text: str) -> Set[str]:
    """
    Extract important content words from a task description.
    """
    if not text:
        return set()

    text_clean = text.lower()
    text_clean = re.sub(r"[^\w\s]", "", text_clean)
    words = text_clean.split()

    stop_words = {
        "the", "a", "an", "to", "of", "for", "and", "is", "are", "was", "were",
        "be", "by", "with", "on", "in", "this", "that", "will", "almost", "finish",
        "complete", "completed", "implement", "develop", "build", "create",
        "test", "verify", "validate", "fix", "debug", "resolve", "design",
        "redesign", "deploy", "release", "publish", "update", "modify", "change"
    }

    return {word for word in words if word not in stop_words and len(word) > 2}


def keyword_similarity(text1: str, text2: str) -> float:
    """
    Compare important task-related words between two task descriptions.
    """
    k1 = extract_keywords(text1)
    k2 = extract_keywords(text2)

    if not k1 and not k2:
        return 1.0
    if not k1 or not k2:
        return 0.0

    intersection = k1.intersection(k2)
    union = k1.union(k2)
    return len(intersection) / len(union)


def hybrid_similarity(text1: str, text2: str) -> float:
    """
    Legacy hybrid similarity combining semantic similarity and action similarity.
    Maintained for backward compatibility.
    """
    semantic_score = semantic_similarity(text1, text2)
    action_score = action_similarity(text1, text2)
    final_score = (semantic_score * 0.70) + (action_score * 0.30)
    return round(final_score, 2)


def resolve_task_identity(
    new_task: Dict[str, Any],
    existing_tasks: List[Dict[str, Any]],
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Full multi-factor cross-meeting task entity resolution.

    Evaluates:
    1. Semantic similarity (embedding cosine)
    2. Action category compatibility
    3. Keyword / entity overlap
    4. Owner compatibility
    5. Project / module context
    6. Historical aliases matching
    """
    new_desc = (new_task.get("description") or "").strip()
    if not new_desc or not existing_tasks:
        return {
            "matched_existing_task_id": None,
            "match_confidence": 0.0,
            "match_reason": ["empty description or no existing tasks"],
            "requires_review": False,
        }

    new_owner = (new_task.get("owner") or "").strip().lower()
    new_project = (new_task.get("project") or "").strip().lower()

    best_task_id = None
    best_confidence = 0.0
    best_reasons: List[str] = []

    for task in existing_tasks:
        existing_id = task["task_id"]
        existing_desc = (task.get("description") or task.get("canonical_description") or "").strip()
        existing_aliases = task.get("aliases", [])
        existing_owner = (task.get("owner") or "").strip().lower()
        existing_project = (task.get("project") or "").strip().lower()

        # Incompatible action safety check
        if not actions_compatible(new_desc, existing_desc):
            continue

        # 1. Base semantic score with canonical description & aliases
        sem_score = semantic_similarity(new_desc, existing_desc)
        for alias in existing_aliases:
            alias_sem = semantic_similarity(new_desc, alias)
            if alias_sem > sem_score:
                sem_score = alias_sem

        act_score = action_similarity(new_desc, existing_desc)
        kw_score = keyword_similarity(new_desc, existing_desc)

        # 2. Multi-factor weighted score
        # 0.65 Semantic + 0.25 Action + 0.10 Keywords
        composite_score = (sem_score * 0.65) + (act_score * 0.25) + (kw_score * 0.10)

        # 3. Owner compatibility bonus / penalty
        reasons = []
        if sem_score >= 0.60:
            reasons.append("high semantic similarity")
        elif sem_score >= 0.45:
            reasons.append("moderate semantic similarity")

        if act_score == 1.0:
            reasons.append("compatible action")

        if kw_score > 0.3:
            reasons.append("matching key entities")

        # In same meeting, different owners indicate separate tasks
        same_meeting = (
            new_task.get("meeting_id")
            and task.get("created_meeting_id")
            and new_task["meeting_id"] == task["created_meeting_id"]
        )

        if new_owner and existing_owner:
            if new_owner == existing_owner:
                composite_score += 0.08
                reasons.append("same owner")
            else:
                # Strong signal: different owners indicates distinct tasks
                composite_score -= 0.15
                if same_meeting:
                    continue  # Distinct owners in same meeting are distinct tasks

        if new_project and existing_project and new_project == existing_project and new_project != "default":
            composite_score += 0.05
            reasons.append("same project context")

        composite_score = max(0.0, min(1.0, composite_score))

        if composite_score > best_confidence:
            best_confidence = composite_score
            best_task_id = existing_id
            best_reasons = reasons

    rounded_conf = round(best_confidence, 2)

    if rounded_conf >= threshold and best_task_id is not None:
        return {
            "matched_existing_task_id": best_task_id,
            "match_confidence": rounded_conf,
            "match_reason": best_reasons,
            "requires_review": rounded_conf < 0.65,
        }

    return {
        "matched_existing_task_id": None,
        "match_confidence": rounded_conf,
        "match_reason": ["confidence below threshold" if best_task_id else "no compatible candidates"],
        "requires_review": (0.35 <= rounded_conf < threshold),
    }


def find_best_semantic_match(
    new_task: Dict[str, Any],
    existing_tasks: List[Dict[str, Any]],
    threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Find the best matching existing task.
    Preserves exact backward-compatible interface and scoring behavior.
    """
    best_task_id = None
    best_confidence = 0.0

    for task in existing_tasks:
        task_desc = task.get("description") or task.get("canonical_description") or ""
        new_desc = new_task.get("description") or ""

        # Check whether the actions are compatible.
        if not actions_compatible(new_desc, task_desc):
            continue

        # Calculate the hybrid similarity score.
        similarity = hybrid_similarity(new_desc, task_desc)

        if similarity > best_confidence:
            best_confidence = similarity
            best_task_id = task["task_id"]

    rounded_conf = round(best_confidence, 2)

    if rounded_conf >= threshold:
        return {
            "matched_existing_task_id": best_task_id,
            "match_confidence": rounded_conf,
        }

    return {
        "matched_existing_task_id": None,
        "match_confidence": rounded_conf,
    }