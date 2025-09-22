#!/usr/bin/env python3
"""
Test script for the Interview Report Generator API
"""

import json
import requests
import time
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000"
SAMPLE_DATA_PATH = "sample/gather.json"

def load_sample_data():
    """Load sample data from gather.json"""
    try:
        with open(SAMPLE_DATA_PATH, 'r') as f:
            data = json.load(f)
        print(f"✅ Loaded sample data from {SAMPLE_DATA_PATH}")
        return data
    except FileNotFoundError:
        print(f"❌ Sample data file not found: {SAMPLE_DATA_PATH}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return None

def test_api_health():
    """Test if API is running"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to API. Make sure it's running on http://localhost:8000")
        return False

def test_sample_endpoint():
    """Test the /sample endpoint"""
    try:
        print("\n📋 Testing /sample endpoint...")
        response = requests.get(f"{BASE_URL}/sample")

        if response.status_code == 200:
            print("✅ Sample endpoint working")
            return response.json()
        else:
            print(f"❌ Sample endpoint failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error testing sample endpoint: {e}")
        return None

def test_gather(sample_data, provider="openrouter", model="openai/gpt-oss-120b:nitro"):
    """Test the /gather endpoint"""
    print(f"\n🤖 Testing /gather endpoint...")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")

    # Add LLM settings to sample data
    test_data = sample_data.copy()
    test_data["llm_settings"] = {
        "provider": provider,
        "model": model
        # API key will be loaded from environment
    }

    try:
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/gather",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minute timeout for LLM processing
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"⏱️  Request completed in {duration:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ Report generation successful!")

            # Print summary
            print(f"\n📊 Results Summary:")
            print(f"   Messages: {len(result.get('messages', []))}")
            print(f"   Questions: {len(result.get('questions', []))}")
            print(f"   Skill Areas: {len(result.get('key_skill_areas', []))}")

            if result.get('llm_output'):
                llm_output = result['llm_output']
                if 'groups' in llm_output:
                    print(f"   Conversation Groups: {len(llm_output['groups'])}")
                if 'pre_inferred_facts_global' in llm_output:
                    facts = llm_output['pre_inferred_facts_global']
                    print(f"   Global Facts: {len(facts)} items")

            return result

        else:
            print(f"❌ Gather endpoint failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text[:500]}...")
            return None

    except requests.Timeout:
        print("❌ Request timed out (>2 minutes)")
        return None
    except Exception as e:
        print(f"❌ Error testing gather endpoint: {e}")
        return None

def save_results(results, filename="test_results.json"):
    """Save test results to file"""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def main():
    """Main test function"""
    print("🚀 Starting API Test Suite")
    print("=" * 50)

    # Test API health
    if not test_api_health():
        return

    # Load sample data
    sample_data = load_sample_data()
    if not sample_data:
        return

    # Test sample endpoint
    sample_response = test_sample_endpoint()

    # Test different providers/models
    test_configs = [
        {"provider": "openrouter", "model": "openai/gpt-oss-120b:nitro"},
        {"provider": "openrouter", "model": "qwen/qwen3-235b-a22b-thinking-2507:nitro"},
        {"provider": "openrouter", "model": "qwen/qwen3-32b:nitro"},
        # Add more configurations as needed
    ]

    results = {}

    for config in test_configs:
        provider = config["provider"]
        model = config["model"]

        print(f"\n🔄 Testing {provider} with {model}")
        result = test_gather(sample_data, provider, model)

        if result:
            results[f"{provider}_{model}"] = {
                "success": True,
                "result": result
            }
        else:
            results[f"{provider}_{model}"] = {
                "success": False,
                "result": None
            }

        # Small delay between requests
        time.sleep(1)

    # Save results
    save_results(results)

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    print(f"   Successful: {successful}/{total}")
    print(f"   Failed: {total - successful}/{total}")

    if successful > 0:
        print("✅ At least one test passed!")
    else:
        print("❌ All tests failed. Check API configuration and environment variables.")

if __name__ == "__main__":
    main()