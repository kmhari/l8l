#!/usr/bin/env python3
"""Test script to validate the sample response structure integration."""

import json
import asyncio
from pathlib import Path

async def test_sample_structure_integration():
    """Test that the sample response structure is properly integrated into the prompt."""
    print("🧪 Testing sample response structure integration...")

    # Test loading sample response structure
    try:
        sample_response = json.loads(Path("prompts/sample_evaluation_response.json").read_text())
        print("✅ Sample response structure loaded successfully")
        print(f"   - Contains {len(sample_response.keys())} main sections")
        print(f"   - Question analysis has {len(sample_response['question_analysis'])} examples")
        print(f"   - Competency mapping has {len(sample_response['competency_mapping'])} skill areas")
    except Exception as e:
        print(f"❌ Failed to load sample response structure: {e}")
        return False

    # Test prompt template replacement
    try:
        from main import load_evaluation_config

        # Load evaluation config
        eval_config = await load_evaluation_config()

        # Load prompt template
        prompt = Path("prompts/evaluate.md").read_text()
        sample_response_str = json.dumps(sample_response, indent=2)

        # Test all template replacements
        populated_prompt = prompt.replace(
            "{{RESUME_CONTENT}}", json.dumps(eval_config["resume"], indent=2)
        ).replace(
            "{{JOB_REQUIREMENTS}}", eval_config["job_requirements"]
        ).replace(
            "{{KEY_SKILL_AREAS}}", json.dumps(eval_config["key_skill_areas"], indent=2)
        ).replace(
            "{{SAMPLE_RESPONSE_STRUCTURE}}", sample_response_str
        )

        # Check that all placeholders were replaced
        placeholders = ["{{RESUME_CONTENT}}", "{{JOB_REQUIREMENTS}}", "{{KEY_SKILL_AREAS}}", "{{SAMPLE_RESPONSE_STRUCTURE}}"]
        remaining_placeholders = [p for p in placeholders if p in populated_prompt]

        if not remaining_placeholders:
            print("✅ All template placeholders replaced successfully")
            print(f"   - Original prompt length: {len(prompt)} chars")
            print(f"   - Populated prompt length: {len(populated_prompt)} chars")
            print(f"   - Sample structure length: {len(sample_response_str)} chars")
        else:
            print(f"❌ Some placeholders not replaced: {remaining_placeholders}")
            return False

    except Exception as e:
        print(f"❌ Template replacement failed: {e}")
        return False

    # Test JSON schema validation of sample
    try:
        schema = json.loads(Path("prompts/evaluation.schema.json").read_text())

        # Basic schema validation (check required fields)
        required_fields = schema.get("required", [])
        sample_fields = list(sample_response.keys())

        missing_fields = [field for field in required_fields if field not in sample_fields]
        if not missing_fields:
            print("✅ Sample response matches schema requirements")
            print(f"   - All {len(required_fields)} required fields present")
        else:
            print(f"❌ Missing required fields in sample: {missing_fields}")
            return False

    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

    # Test question analysis structure
    try:
        question_analysis = sample_response["question_analysis"]
        if len(question_analysis) > 0:
            example_qa = question_analysis[0]
            required_qa_fields = ["question_id", "question_text", "answer_quality", "strengths", "concerns", "green_flags", "red_flags", "conversation"]

            missing_qa_fields = [field for field in required_qa_fields if field not in example_qa]
            if not missing_qa_fields:
                print("✅ Question analysis structure is complete")
                print(f"   - Example has conversation with {len(example_qa['conversation'])} turns")
                print(f"   - Answer quality score: {example_qa['answer_quality']['relevance_score']}")
            else:
                print(f"❌ Missing fields in question analysis: {missing_qa_fields}")
                return False
        else:
            print("❌ No question analysis examples in sample")
            return False

    except Exception as e:
        print(f"❌ Question analysis validation failed: {e}")
        return False

    print("🎉 All sample structure integration tests passed!")
    print("\n📋 Summary:")
    print("   - Sample response structure loaded and validated")
    print("   - Template replacement working for all placeholders")
    print("   - JSON schema compatibility confirmed")
    print("   - Question analysis structure properly formatted")
    print("   - Ready for use in evaluation prompts")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_sample_structure_integration())
    exit(0 if success else 1)