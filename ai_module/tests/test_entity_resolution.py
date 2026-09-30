import json

from ai_module.entity_resolution.semantic_matcher import (
    find_best_semantic_match
)


def load_test_cases():
    with open(
        "ai_module/tests/entity_resolution_test_cases.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def run_evaluation():
    test_cases = load_test_cases()

    correct = 0
    threshold = 0.50

    for index, case in enumerate(test_cases, start=1):

        existing_tasks = case["existing_tasks"]

        new_task = {
            "description": case["new_task"]
        }

        result = find_best_semantic_match(
            new_task,
            existing_tasks,
            threshold=threshold
        )

        predicted_task_id = result["matched_existing_task_id"]
        expected_task_id = case["expected_task_id"]

        if predicted_task_id == expected_task_id:
            correct += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"{index}. "
            f"{status} | "
            f"New Task: {case['new_task']} | "
            f"Matched: {predicted_task_id} | "
            f"Expected: {expected_task_id} | "
            f"Score: {result['match_confidence']}"
        )

    accuracy = correct / len(test_cases)

    print()
    print(f"Correct: {correct}/{len(test_cases)}")
    print(f"Multi-Task Accuracy: {accuracy:.2%}")


if __name__ == "__main__":
    run_evaluation()