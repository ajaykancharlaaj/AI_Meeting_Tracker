from ai_module.extraction.deadline_normalizer import (
    normalize_deadline
)


def test_deadline_normalization():

    reference_date = "2026-09-17"

    test_cases = [
        {
            "input": "today",
            "expected": "2026-09-17"
        },
        {
            "input": "tomorrow",
            "expected": "2026-09-18"
        },
        {
            "input": "day after tomorrow",
            "expected": "2026-09-19"
        },
        {
            "input": "Friday, September 18",
            "expected": "2026-09-18"
        },
        {
            "input": "September 25",
            "expected": "2026-09-25"
        },
        {
            "input": None,
            "expected": None
        }
    ]

    print("Deadline Normalization Tests:")
    print()

    for case in test_cases:

        result = normalize_deadline(
            case["input"],
            reference_date
        )

        print(
            f"Input: {case['input']} "
            f"-> "
            f"Normalized: {result}"
        )

        assert result == case["expected"]

    print()
    print("Deadline Normalization Test Passed!")


if __name__ == "__main__":
    test_deadline_normalization()