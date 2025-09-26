#!/usr/bin/env python3
"""Test script for the question generator API endpoint"""

import json
import requests
import asyncio
import sys


def test_question_generator():
    """Test the question generator endpoint with sample data from output/question_input.json"""

    # Read the sample input file
    try:
        with open("output/question_input.json", "r") as f:
            sample_data = json.load(f)
    except FileNotFoundError:
        print("❌ Sample input file not found: output/question_input.json")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in sample file: {str(e)}")
        return False

    # Extract the first item from the array
    if not sample_data or not isinstance(sample_data, list):
        print("❌ Sample data should be an array with at least one item")
        return False

    input_data = sample_data[0]

    print("🚀 Testing Question Generator API")
    print(f"📋 Job Description: {input_data['job_description'][:100]}...")
    print(f"🎯 Skills: {len(input_data['skills'])} skill areas")

    # Test the API endpoint
    api_url = "http://localhost:8000/api/v1/generate-questions"

    try:
        print(f"\n📡 Sending request to {api_url}")

        response = requests.post(
            api_url,
            json=input_data,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minute timeout for LLM generation
        )

        if response.status_code == 200:
            result = response.json()

            print(f"✅ Request successful!")
            print(f"📊 Generated {len(result['questions'])} questions")
            print(f"🕒 Generated at: {result['metadata']['generated_at']}")
            print(f"🤖 Model used: {result['metadata']['model_used']}")

            # Show sample questions
            if result['questions']:
                print(f"\n📝 Sample Questions:")
                for i, question in enumerate(result['questions'][:3]):
                    print(f"{i+1}. [{question['questionType']}] {question['question'][:80]}...")
                    print(f"   Skill: {question['linkedSkillArea']} -> {question['linkedSubSkillArea']}")
                    print(f"   Difficulty: {question['difficultyLevel']}, Time: {question['timeToAnswer']}s")
                    print()

            # Save the result
            output_file = "output/generated_questions.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"💾 Results saved to: {output_file}")

            return True

        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"❌ Error: {error_detail}")
            except:
                print(f"❌ Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the server running on localhost:8000?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_question_generator()
    sys.exit(0 if success else 1)