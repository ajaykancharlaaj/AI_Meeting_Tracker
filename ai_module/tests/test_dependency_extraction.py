from ai_module.risk.dependency_extractor import (
    extract_dependency_statement,
    link_dependency_to_tasks,
    link_dependency_semantically
)   

def test_semantic_dependency_linking():

    dependency = {
        "task_description": "Login testing",
        "dependency_description": "the backend API"
    }

    tasks = [
        {
            "task_id": "T1",
            "description": "Develop backend API"
        },
        {
            "task_id": "T2",
            "description": "Test login module"
        },
        {
            "task_id": "T3",
            "description": "Design dashboard"
        }
    ]

    result = link_dependency_semantically(
        dependency,
        tasks,
        threshold=0.50
    )

    print()
    print("Semantic Dependency Linking:")
    print(result)

    assert result["task_id"] == "T2"
    assert result["depends_on"] == "T1"

    print()
    print("Semantic Dependency Linking Test Passed!")


def test_dependency_patterns():

    test_cases = [

        {
            "text": "The final design depends on the updated brand assets.",
            "task": "The final design",
            "dependency": "the updated brand assets"
        },

        {
            "text": "Login testing cannot start until the API is completed.",
            "task": "Login testing",
            "dependency": "the API is completed"
        },

        {
            "text": "The dashboard is waiting for the brand assets.",
            "task": "The dashboard",
            "dependency": "the brand assets"
        },

        {
            "text": "The release is blocked because of the database migration.",
            "task": "The release",
            "dependency": "the database migration"
        }
    ]

    print("Dependency Pattern Tests:")
    print()

    for index, case in enumerate(test_cases, start=1):

        result = extract_dependency_statement(
            case["text"]
        )

        print(f"{index}. {case['text']}")
        print(f"   Extracted: {result}")

        assert result is not None

        assert (
            result["task_description"]
            == case["task"]
        )

        assert (
            result["dependency_description"]
            == case["dependency"]
        )

    print()
    print("All Dependency Pattern Tests Passed!")


def test_dependency_linking():

    dependency = {
        "task_description": "Login testing",
        "dependency_description": "the API"
    }

    tasks = [
        {
            "task_id": "T1",
            "description": "Payment API"
        },
        {
            "task_id": "T2",
            "description": "Login testing"
        }
    ]

    result = link_dependency_to_tasks(
        dependency,
        tasks
    )

    print()
    print("Dependency Linking:")
    print(result)

    assert result is not None
    assert result["task_id"] == "T2"
    assert result["depends_on"] == "T1"

    print()
    print("Dependency Linking Test Passed!")


if __name__ == "__main__":

    
    test_dependency_patterns()
    test_dependency_linking()
    test_semantic_dependency_linking()
    print()
    print("All Dependency Tests Passed!")