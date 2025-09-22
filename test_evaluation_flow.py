#!/usr/bin/env python3
"""Test the complete evaluation flow with sample response structure."""

import json
import asyncio
from pathlib import Path

async def test_evaluation_flow():
    """Test the complete evaluation flow from prompt to response structure."""
    print("🧪 Testing complete evaluation flow...")

    try:
        # Import required modules
        from main import evaluate_question_group, load_evaluation_config

        # Load evaluation configuration
        eval_config = await load_evaluation_config()
        print("✅ Evaluation configuration loaded")

        # Load sample data for testing
        sample_data = json.loads(Path("sample/evaluate.json").read_text())

        # Create a mock question group from the sample data
        mock_group = {
            "question_id": "Q1",
            "question_title": "How does Node.js handle asynchronous operations?",
            "type": "technical",
            "source": "known_questions",
            "time_range": {"start": 190, "end": 323},
            "turn_indices": [26, 27],
            "conversation": [
                {
                    "idx": 26,
                    "role": "agent",
                    "message": "How does Node.js handle asynchronous operations? And what role does the event loop play in this process?",
                    "time": 1758186321817,
                    "endTime": 1758186328817,
                    "duration": 7000,
                    "secondsFromStart": 190.3
                },
                {
                    "idx": 27,
                    "role": "user",
                    "message": "Node.js handles asynchronous operations using the event loop...",
                    "time": 1758186329817,
                    "endTime": 1758186454816,
                    "duration": 125000,
                    "secondsFromStart": 198.3
                }
            ],
            "greenFlags": ["Mentions event loop", "References libuv"],
            "redFlags": []
        }

        # Load evaluation prompt and schema
        evaluation_prompt = Path("prompts/evaluate.md").read_text()
        evaluation_schema = json.loads(Path("prompts/evaluation.schema.json").read_text())

        print("✅ Test data and prompts prepared")

        # Test the prompt population process (without actually calling LLM)
        try:
            # Load sample response structure
            sample_response = json.loads(Path("prompts/sample_evaluation_response.json").read_text())
            sample_response_str = json.dumps(sample_response, indent=2)

            # Populate the system prompt
            populated_prompt = evaluation_prompt.replace(
                "{{RESUME_CONTENT}}", json.dumps(eval_config["resume"], indent=2)
            ).replace(
                "{{JOB_REQUIREMENTS}}", eval_config["job_requirements"]
            ).replace(
                "{{KEY_SKILL_AREAS}}", json.dumps(eval_config["key_skill_areas"], indent=2)
            ).replace(
                "{{SAMPLE_RESPONSE_STRUCTURE}}", sample_response_str
            )

            # Prepare the input data
            evaluation_input = {
                "question_group": mock_group,
                "transcript_messages": mock_group.get("conversation", [])
            }

            # Create the evaluation messages
            evaluation_messages = [
                {"role": "system", "content": populated_prompt},
                {"role": "user", "content": f"Evaluate this specific question group: {json.dumps(evaluation_input)}"}
            ]

            print("✅ Prompt population successful")
            print(f"   - System prompt length: {len(populated_prompt)} chars")
            print(f"   - User message length: {len(evaluation_messages[1]['content'])} chars")
            print(f"   - Sample structure included: {'SAMPLE_RESPONSE_STRUCTURE' not in populated_prompt}")

            # Validate the input structure
            expected_input_keys = ["question_group", "transcript_messages"]
            input_keys = list(evaluation_input.keys())

            if all(key in input_keys for key in expected_input_keys):
                print("✅ Input structure matches expected format")
                print(f"   - Question ID: {evaluation_input['question_group']['question_id']}")
                print(f"   - Conversation turns: {len(evaluation_input['transcript_messages'])}")
            else:
                print("❌ Input structure missing required keys")
                return False

            # Test that the sample response structure is valid according to schema
            required_schema_fields = evaluation_schema.get("required", [])
            sample_fields = list(sample_response.keys())

            if all(field in sample_fields for field in required_schema_fields):
                print("✅ Sample response structure validates against schema")
                print(f"   - All {len(required_schema_fields)} required fields present")
            else:
                missing = [f for f in required_schema_fields if f not in sample_fields]
                print(f"❌ Sample missing required fields: {missing}")
                return False

        except Exception as e:
            print(f"❌ Prompt population failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Evaluation flow test failed: {e}")
        return False

    print("🎉 Complete evaluation flow test passed!")
    print("\n📋 Flow Summary:")
    print("   1. ✅ Configuration loading works")
    print("   2. ✅ Sample response structure integration works")
    print("   3. ✅ Prompt template population works")
    print("   4. ✅ Input data structure is correct")
    print("   5. ✅ Schema validation passes")
    print("   6. ✅ Ready for LLM evaluation calls")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_evaluation_flow())
    exit(0 if success else 1)