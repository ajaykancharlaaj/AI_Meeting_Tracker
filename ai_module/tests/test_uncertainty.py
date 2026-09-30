from ai_module.state_reconstruction.state_reconstructor import (
    detect_uncertainty
)


def test_uncertainty_detection():

    test_cases = [
        ("The login module is completed.", False),
        ("The login module is probably completed.", True),
        ("The login module may be completed.", True),
        ("I think the login module is completed.", True),
        ("The login module is still incomplete.", False),
        ("Perhaps the API is ready.", True)
    ]

    print("Uncertainty Detection Tests:")
    print()

    for text, expected in test_cases:

        result = detect_uncertainty(text)

        print(
            f"Text: {text}"
        )
        print(
            f"Uncertain: {result}"
        )
        print()

        assert result == expected

    print("Uncertainty Detection Test Passed!")


if __name__ == "__main__":
    test_uncertainty_detection()