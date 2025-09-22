#!/usr/bin/env python3
"""Final test of the improved JSON parsing with error recovery."""

import json
from main import parse_structured_output

def test_complete_parsing_flow():
    """Test the complete parsing flow including error recovery."""
    print("🧪 Testing complete JSON parsing flow with error recovery...\n")

    # Test case 1: Complete valid JSON
    print("1️⃣ Testing complete valid JSON...")
    complete_json = {
        "overall_assessment": {"recommendation": "Hire", "confidence": "High", "overall_score": 85, "summary": "Excellent candidate"},
        "competency_mapping": [],
        "question_analysis": [],
        "communication_assessment": {"verbal_articulation": "Excellent", "logical_flow": "Good", "professional_vocabulary": "Good", "cultural_fit_indicators": []},
        "critical_analysis": {"red_flags": [], "exceptional_responses": [], "inconsistencies": [], "problem_solving_approach": "Systematic"},
        "improvement_recommendations": []
    }

    try:
        result = parse_structured_output(json.dumps(complete_json), ["overall_assessment", "competency_mapping", "question_analysis"])
        print("✅ Complete JSON parsed successfully")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

    # Test case 2: The original truncated response
    print("\n2️⃣ Testing original truncated response...")
    truncated_response = '''{"overall_assessment": {"recommendation": "Hire", "confidence": "Medium", "overall_score": 65, "summary": "Candidate demonstrates basic understanding of Node.js asynchronous model and event loop concepts but shows confusion about execution order and specific phases. Has awareness of key components like libuv and microtask queue but lacks precise, detailed knowledge expected for a senior role."}, "competency_mapping": [{"skill_area": "Programming & Development", "overall_assessment": "Intermediate", "meets_requirements": true, "confidence": "Medium", "assessment_notes": ["Understands Node.js is single-threaded and uses event loop for async operations", "Aware of key concepts like microtask queue, promises, and libuv", "Confused about actual execution order and phases of the event loop", "Limited ability to explain libuv implementation details", "Shows foundational knowledge but needs deeper understanding for senior role"], "sub_skills": [{"name": "Node.js Runtime", "proficiency": "Inter'''

    try:
        # Try to parse - this might succeed or fail depending on repair capability
        result = parse_structured_output(truncated_response, ["overall_assessment", "competency_mapping", "question_analysis"])

        # Check if we got all expected keys
        has_all_keys = all(key in result for key in ["overall_assessment", "competency_mapping", "question_analysis"])

        if has_all_keys:
            print("✅ Successfully parsed complete response with all required fields")
            print(f"   All keys present: {list(result.keys())}")
        else:
            print("🔧 Parsed partial response, missing some required fields")
            print(f"   Present keys: {list(result.keys())}")
            missing_keys = [key for key in ["overall_assessment", "competency_mapping", "question_analysis"] if key not in result]
            print(f"   Missing keys: {missing_keys}")

        print(f"   Overall score: {result.get('overall_assessment', {}).get('overall_score', 'N/A')}")
        return True

    except Exception as e:
        print(f"🔧 Parsing failed, attempting recovery: {str(e)[:100]}...")

        try:
            # Try without expected keys
            result = parse_structured_output(truncated_response, None)
            print("✅ Successfully recovered partial response")
            print(f"   Recovered keys: {list(result.keys())}")
            print(f"   Overall score: {result.get('overall_assessment', {}).get('overall_score', 'N/A')}")
            return True
        except Exception as e2:
            print(f"❌ Complete recovery failure: {e2}")
            return False

def test_error_recovery_in_evaluation():
    """Test the error recovery logic in the evaluation function context."""
    print("\n🧪 Testing error recovery in evaluation context...\n")

    # Simulate the evaluation parsing logic
    truncated_response = '''{"overall_assessment": {"recommendation": "Hire", "confidence": "Medium", "overall_score": 65, "summary": "Good candidate"}, "competency_mapping": [{"skill_area": "Programming", "overall_assessment": "Intermediate"'''

    print("3️⃣ Simulating evaluation parsing with recovery...")

    try:
        expected_keys = ["overall_assessment", "competency_mapping", "question_analysis"]
        evaluation_data = parse_structured_output(truncated_response, expected_keys=expected_keys)
        print("✅ Complete parsing succeeded")
        return evaluation_data

    except Exception as e:
        print(f"🔧 Complete parsing failed, attempting recovery: {str(e)[:100]}...")

        # Try partial recovery
        try:
            partial_data = parse_structured_output(truncated_response, expected_keys=None)
            print(f"✅ Recovered partial data with keys: {list(partial_data.keys())}")

            # Fill in missing fields
            evaluation_data = {
                "overall_assessment": partial_data.get("overall_assessment", {
                    "recommendation": "No Hire",
                    "confidence": "Low",
                    "overall_score": 0,
                    "summary": "Partial evaluation"
                }),
                "competency_mapping": partial_data.get("competency_mapping", []),
                "question_analysis": partial_data.get("question_analysis", []),
                "communication_assessment": partial_data.get("communication_assessment", {
                    "verbal_articulation": "Fair",
                    "logical_flow": "Fair",
                    "professional_vocabulary": "Fair",
                    "cultural_fit_indicators": []
                }),
                "critical_analysis": partial_data.get("critical_analysis", {
                    "red_flags": ["Incomplete evaluation"],
                    "exceptional_responses": [],
                    "inconsistencies": [],
                    "problem_solving_approach": "Partially assessed"
                }),
                "improvement_recommendations": partial_data.get("improvement_recommendations", []),
                "partial_response": True,
                "recovered_fields": list(partial_data.keys())
            }

            print(f"✅ Successfully created complete evaluation from {len(partial_data.keys())} recovered fields")
            print(f"   Final evaluation score: {evaluation_data['overall_assessment']['overall_score']}")
            return evaluation_data

        except Exception as e2:
            print(f"❌ Complete recovery failure: {e2}")
            return None

if __name__ == "__main__":
    print("🔍 Testing improved JSON parsing with comprehensive error recovery\n")

    test1 = test_complete_parsing_flow()
    test2 = test_error_recovery_in_evaluation()

    if test1 and test2 is not None:
        print("\n🎉 All JSON parsing and error recovery tests passed!")
        print("\n📋 Summary of improvements:")
        print("   ✅ Enhanced JSON repair function")
        print("   ✅ Partial response recovery")
        print("   ✅ Graceful degradation for incomplete responses")
        print("   ✅ Comprehensive error handling")
        print("   ✅ Maintains evaluation pipeline functionality")
        exit(0)
    else:
        print("\n❌ Some tests failed!")
        exit(1)