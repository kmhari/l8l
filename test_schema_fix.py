#!/usr/bin/env python3
"""
Test script to verify the Cerebras provider schema fix.
This tests the /gather endpoint which uses the fixed schema without minimum/maximum fields.
"""

import json
import requests

def test_schema_fix():
    """Test that the Cerebras provider works with the fixed schema"""

    # Minimal test data for /gather endpoint
    test_data = {
        "transcript": {
            "messages": [
                {
                    "role": "agent",
                    "time": 1758186131517,
                    "endTime": 1758186149916,
                    "message": "Hi, can you tell me about your Node.js experience?",
                    "duration": 18400,
                    "secondsFromStart": 0.0
                },
                {
                    "role": "user",
                    "time": 1758186149916,
                    "endTime": 1758186157156,
                    "message": "I have 3 years of Node.js experience.",
                    "duration": 7240,
                    "secondsFromStart": 18.4
                }
            ]
        },
        "technical_questions": "Node.js experience questions",
        "key_skill_areas": [
            {
                "skill_area": "Node.js Development",
                "sub_skills": ["Event Loop", "Async Programming"]
            }
        ],
        "llm_settings": {
            "provider": "openrouter",
            "model": "openai/gpt-oss-120b:nitro"
        }
    }

    print("🧪 Testing schema fix with /gather endpoint...")
    print(f"📊 Using Cerebras provider via OpenRouter")

    try:
        response = requests.post(
            "http://localhost:8000/gather",
            json=test_data,
            timeout=120
        )

        print(f"📈 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Schema fix working! No minimum/maximum field errors.")
            print(f"📝 Found {len(result.get('groups', []))} conversation groups")
            return True
        else:
            print(f"❌ FAILED: {response.status_code}")
            try:
                error_data = response.json()
                error_text = json.dumps(error_data, indent=2)
                print(f"Error details: {error_text}")

                # Check if it's still the schema error we're trying to fix
                if "minimum" in error_text or "maximum" in error_text:
                    print("🔍 Still seeing minimum/maximum field errors - fix not complete")
                    return False
                else:
                    print("🔍 Different error - schema fix may be working")

            except:
                print(f"Raw error: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure the server is running with: uv run python main.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_schema_fix()
    if success:
        print("\n🎉 Schema fix test PASSED")
        exit(0)
    else:
        print("\n💥 Schema fix test FAILED")
        exit(1)