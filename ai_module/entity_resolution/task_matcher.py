import re


def normalize_text(text: str) -> str:
    """
    Convert task text into a normalized form.

    Steps:
    1. Convert to lowercase.
    2. Remove punctuation.
    3. Remove extra whitespace.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def jaccard_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two task descriptions.
    """

    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())

    if not words1 and not words2:
        return 1.0

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


def find_best_match(
    new_task: dict,
    existing_tasks: list[dict],
    threshold: float = 0.70
) -> dict:
    """
    Find the existing task that is most similar to a new task.
    """

    best_task_id = None
    best_confidence = 0.0

    for task in existing_tasks:
        similarity = jaccard_similarity(
            new_task["description"],
            task["description"]
        )

        if similarity > best_confidence:
            best_confidence = similarity
            best_task_id = task["task_id"]

    if best_confidence >= threshold:
        return {
            "matched_existing_task_id": best_task_id,
            "match_confidence": round(best_confidence, 2)
        }

    return {
        "matched_existing_task_id": None,
        "match_confidence": round(best_confidence, 2)
    }