#!/usr/bin/env python3
"""Test the improved JSON parsing for truncated evaluation responses."""

import json
from main import parse_structured_output, repair_incomplete_json

def test_json_parsing():
    """Test JSON parsing with various malformed inputs."""
    print("🧪 Testing improved JSON parsing...")

    # Test case 1: The actual truncated response from the error
    truncated_response = '''{"overall_assessment": {"recommendation": "Hire", "confidence": "Medium", "overall_score": 65, "summary": "Candidate demonstrates basic understanding of Node.js asynchronous model and event loop concepts but shows confusion about execution order and specific phases. Has awareness of key components like libuv and microtask queue but lacks precise, detailed knowledge expected for a senior role."}, "competency_mapping": [{"skill_area": "Programming & Development", "overall_assessment": "Intermediate", "meets_requirements": true, "confidence": "Medium", "assessment_notes": ["Understands Node.js is single-threaded and uses event loop for async operations", "Aware of key concepts like microtask queue, promises, and libuv", "Confused about actual execution order and phases of the event loop", "Limited ability to explain libuv implementation details", "Shows foundational knowledge but needs deeper understanding for senior role"], "sub_skills": [{"name": "Node.js Runtime", "proficiency": "Inter'''

    expected_keys = ["overall_assessment", "competency_mapping", "question_analysis"]

    try:
        result = parse_structured_output(truncated_response, expected_keys)
        print("❌ Should have failed but didn't - response is incomplete")
        return False
    except Exception as e:
        print(f"✅ Correctly failed to parse incomplete response: {str(e)}")

    # Test case 2: Try to repair the truncated response
    try:
        repaired = repair_incomplete_json(truncated_response)
        print(f"🔧 Repaired JSON length: {len(repaired)} chars (original: {len(truncated_response)})")

        # Try to parse the repaired JSON
        parsed = json.loads(repaired)
        print("✅ Successfully parsed repaired JSON")
        print(f"   - Has overall_assessment: {'overall_assessment' in parsed}")
        print(f"   - Has competency_mapping: {'competency_mapping' in parsed}")
        print(f"   - Missing question_analysis: {'question_analysis' not in parsed}")

        return True
    except Exception as e:
        print(f"❌ Failed to repair JSON: {str(e)}")
        return False

def test_various_incomplete_json():
    """Test various types of incomplete JSON."""
    print("\n🧪 Testing various incomplete JSON scenarios...")

    test_cases = [
        # Incomplete object
        ('{"name": "test", "value":', '{"name": "test"}'),

        # Incomplete array
        ('{"items": [1, 2, 3', '{"items": [1, 2, 3]}'),

        # Incomplete string
        ('{"message": "hello world', '{"message": "hello world"}'),

        # Nested incomplete
        ('{"outer": {"inner": "value"', '{"outer": {"inner": "value"}}'),

        # Trailing comma
        ('{"a": 1, "b": 2,}', '{"a": 1, "b": 2}'),
    ]

    all_passed = True
    for incomplete, description in test_cases:
        try:
            repaired = repair_incomplete_json(incomplete)
            parsed = json.loads(repaired)
            print(f"✅ {description}: {repaired}")
        except Exception as e:
            print(f"❌ {description}: Failed - {str(e)}")
            all_passed = False

    return all_passed

def test_complete_evaluation_structure():
    """Test with a complete evaluation structure."""
    print("\n🧪 Testing complete evaluation structure...")

    # Create a minimal but complete evaluation response
    complete_response = {
        "overall_assessment": {
            "recommendation": "Hire",
            "confidence": "Medium",
            "overall_score": 70,
            "summary": "Good candidate"
        },
        "competency_mapping": [
            {
                "skill_area": "Programming & Development",
                "overall_assessment": "Intermediate",
                "meets_requirements": True,
                "confidence": "Medium",
                "assessment_notes": ["Shows good understanding"],
                "sub_skills": [
                    {
                        "name": "Node.js Runtime",
                        "proficiency": "Intermediate",
                        "demonstrated": True,
                        "confidence": "Medium"
                    }
                ]
            }
        ],
        "question_analysis": [
            {
                "question_id": "Q1",
                "question_text": "Test question",
                "answer_quality": {
                    "relevance_score": 75,
                    "completeness": "Partial",
                    "clarity": "Good",
                    "depth": "Moderate",
                    "evidence_provided": True
                },
                "strengths": ["Good explanation"],
                "concerns": ["Could be more detailed"],
                "green_flags": ["Shows understanding"],
                "red_flags": [],
                "conversation": []
            }
        ],
        "communication_assessment": {
            "verbal_articulation": "Good",
            "logical_flow": "Good",
            "professional_vocabulary": "Good",
            "cultural_fit_indicators": []
        },
        "critical_analysis": {
            "red_flags": [],
            "exceptional_responses": [],
            "inconsistencies": [],
            "problem_solving_approach": "Methodical"
        },
        "improvement_recommendations": []
    }

    try:
        json_str = json.dumps(complete_response)
        expected_keys = ["overall_assessment", "competency_mapping", "question_analysis"]
        parsed = parse_structured_output(json_str, expected_keys)

        if all(key in parsed for key in expected_keys):
            print("✅ Complete evaluation structure parses correctly")
            print(f"   - Overall score: {parsed['overall_assessment']['overall_score']}")
            print(f"   - Skill areas: {len(parsed['competency_mapping'])}")
            print(f"   - Questions analyzed: {len(parsed['question_analysis'])}")
            return True
        else:
            print("❌ Complete structure missing expected keys")
            return False

    except Exception as e:
        print(f"❌ Failed to parse complete structure: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing JSON parsing improvements...\n")

    test1 = test_json_parsing()
    test2 = test_various_incomplete_json()
    test3 = test_complete_evaluation_structure()

    if test1 and test2 and test3:
        print("\n🎉 All JSON parsing tests passed!")
        exit(0)
    else:
        print("\n❌ Some JSON parsing tests failed!")
        exit(1)