#!/usr/bin/env python3
"""Test script to validate the /generate-report API changes."""

import json
import time
from pathlib import Path

def test_api_changes():
    """Test the updated API structure."""
    print("🧪 Testing updated /generate-report API changes...")

    # Load sample data
    sample_data = json.loads(Path("sample/evaluate.json").read_text())

    # Create new request format (only transcript and llm_settings)
    new_request = {
        "transcript": sample_data["transcript"],
        "llm_settings": {
            "provider": "openrouter",
            "model": "qwen/qwen3-235b-a22b-2507"
        }
    }

    print("✅ Created new request format")
    print(f"   - Transcript messages: {len(new_request['transcript']['messages'])}")
    print(f"   - Model: {new_request['llm_settings']['model']}")

    # Test sample-evaluate endpoint structure
    try:
        from main import EvaluateRequest
        request_obj = EvaluateRequest(**new_request)
        print("✅ EvaluateRequest model validation passed")
    except Exception as e:
        print(f"❌ EvaluateRequest model validation failed: {e}")
        return False

    # Test evaluation config loading
    try:
        import asyncio
        from main import load_evaluation_config

        async def test_config():
            config = await load_evaluation_config()
            return config

        eval_config = asyncio.run(test_config())
        print("✅ Evaluation config loading works")
        print(f"   - Resume candidate: {eval_config['resume'].get('candidate_name', 'Unknown')}")
        print(f"   - Key skill areas: {len(eval_config['key_skill_areas'])}")

    except Exception as e:
        print(f"❌ Evaluation config loading failed: {e}")
        return False

    # Test prompt template replacement
    try:
        prompt = Path("prompts/evaluate.md").read_text()
        populated_prompt = prompt.replace(
            "{{RESUME_CONTENT}}", json.dumps(eval_config["resume"], indent=2)
        ).replace(
            "{{JOB_REQUIREMENTS}}", eval_config["job_requirements"]
        ).replace(
            "{{KEY_SKILL_AREAS}}", json.dumps(eval_config["key_skill_areas"], indent=2)
        )

        # Check that all placeholders were replaced
        if all(placeholder not in populated_prompt for placeholder in ["{{RESUME_CONTENT}}", "{{JOB_REQUIREMENTS}}", "{{KEY_SKILL_AREAS}}"]):
            print("✅ Prompt template replacement works")
            print(f"   - Original length: {len(prompt)} chars")
            print(f"   - Populated length: {len(populated_prompt)} chars")
        else:
            print("❌ Some prompt placeholders were not replaced")
            return False

    except Exception as e:
        print(f"❌ Prompt template replacement failed: {e}")
        return False

    print("🎉 All tests passed! The API changes are working correctly.")
    print("\n📋 Summary of changes:")
    print("   - Resume, job requirements, and key skill areas moved to system prompt")
    print("   - EvaluateRequest now only requires transcript and llm_settings")
    print("   - Configuration is loaded from sample data automatically")
    print("   - Prompt template replacement is working correctly")

    return True

if __name__ == "__main__":
    success = test_api_changes()
    exit(0 if success else 1)