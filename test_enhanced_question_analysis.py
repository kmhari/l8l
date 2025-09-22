#!/usr/bin/env python3
"""
Test the enhanced question analysis with green flags, red flags, and conversation
"""

import requests
import json
import time
from pathlib import Path

def test_enhanced_question_analysis():
    """Test that question_analysis includes the new fields"""

    base_url = "http://localhost:8000"

    # Simple test data with clear green/red flag scenarios
    test_data = {
        "resume": {
            "candidate_name": "Test Candidate",
            "skills": ["Python", "Node.js"],
            "experience": "3 years"
        },
        "transcript": {
            "messages": [
                {"turn": 0, "role": "agent", "message": "Can you explain how Node.js handles asynchronous operations?", "time": 0.0, "endTime": 5.0, "duration": 5000, "secondsFromStart": 0.0},
                {"turn": 1, "role": "user", "message": "Node.js uses the event loop to handle async operations. The event loop has different phases like timers, poll, and check phases. It uses libuv for I/O operations.", "time": 5.0, "endTime": 25.0, "duration": 20000, "secondsFromStart": 5.0},
                {"turn": 2, "role": "agent", "message": "What about error handling in async functions?", "time": 25.0, "endTime": 30.0, "duration": 5000, "secondsFromStart": 25.0},
                {"turn": 3, "role": "user", "message": "Um, I'm not sure about that specific topic.", "time": 30.0, "endTime": 35.0, "duration": 5000, "secondsFromStart": 30.0}
            ]
        },
        "technical_questions": "Q1: Node.js async operations\nGreen flags:\n- Mentions event loop\n- Discusses libuv\n- Explains phases\nRed flags:\n- Vague explanations\n- Avoids follow-up questions",
        "key_skill_areas": [
            {"name": "Node.js", "level": "Advanced", "required": True}
        ],
        "llm_settings": {
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "api_key": None
        }
    }

    print("🧪 Testing enhanced question analysis...")

    try:
        # Call the generate-report endpoint
        response = requests.post(
            f"{base_url}/generate-report",
            json=test_data,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful")

            # Check if question_analysis exists and has the new fields
            question_analysis = result.get('evaluation_report', {}).get('question_analysis', [])

            if question_analysis:
                print(f"✅ Found {len(question_analysis)} question analyses")

                for i, qa in enumerate(question_analysis):
                    print(f"\n📋 Question Analysis {i+1}:")
                    print(f"   Question ID: {qa.get('question_id', 'Not found')}")
                    print(f"   Question Text: {qa.get('question_text', 'Not found')}")

                    # Check for new fields
                    green_flags = qa.get('green_flags', [])
                    red_flags = qa.get('red_flags', [])
                    conversation = qa.get('conversation', [])

                    print(f"   Green Flags: {len(green_flags)} found")
                    if green_flags:
                        for flag in green_flags[:2]:  # Show first 2
                            print(f"     • {flag}")

                    print(f"   Red Flags: {len(red_flags)} found")
                    if red_flags:
                        for flag in red_flags[:2]:  # Show first 2
                            print(f"     • {flag}")

                    print(f"   Conversation Turns: {len(conversation)} found")
                    if conversation:
                        print(f"     First turn: {conversation[0].get('role', 'Unknown')} - {conversation[0].get('message', 'No message')[:50]}...")

                # Verify all required fields are present
                if all('green_flags' in qa and 'red_flags' in qa and 'conversation' in qa for qa in question_analysis):
                    print("\n✅ All question analyses include the new fields!")
                else:
                    print("\n❌ Some question analyses are missing the new fields")

            else:
                print("❌ No question analysis found in response")

        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_enhanced_question_analysis()