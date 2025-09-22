#!/usr/bin/env python3
"""
Simple test script for quick API testing
"""

import json
import requests

def test_api():
    """Simple API test"""
    print("🚀 Testing API with sample data...")

    # Load sample data
    with open("sample/gather.json", 'r') as f:
        data = json.load(f)

    # Add LLM settings
    data["llm_settings"] = {
        "provider": "openrouter",
        "model": "openai/gpt-oss-120b:nitro"
    }

    # Make request
    response = requests.post(
        "http://localhost:8000/generate-report",
        json=data,
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(f"Messages: {len(result['messages'])}")
        print(f"Questions: {len(result['questions'])}")

        if result.get('llm_output') and 'groups' in result['llm_output']:
            print(f"Groups: {len(result['llm_output']['groups'])}")

        # Save result
        with open("test_output.json", 'w') as f:
            json.dump(result, f, indent=2)
        print("💾 Result saved to test_output.json")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api()