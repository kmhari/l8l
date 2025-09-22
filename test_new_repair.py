#!/usr/bin/env python3
"""Test the new JSON repair function."""

import json
from main import repair_incomplete_json

def test_new_repair():
    """Test the improved repair function."""
    truncated_response = '''{"overall_assessment": {"recommendation": "Hire", "confidence": "Medium", "overall_score": 65, "summary": "Candidate demonstrates basic understanding of Node.js asynchronous model and event loop concepts but shows confusion about execution order and specific phases. Has awareness of key components like libuv and microtask queue but lacks precise, detailed knowledge expected for a senior role."}, "competency_mapping": [{"skill_area": "Programming & Development", "overall_assessment": "Intermediate", "meets_requirements": true, "confidence": "Medium", "assessment_notes": ["Understands Node.js is single-threaded and uses event loop for async operations", "Aware of key concepts like microtask queue, promises, and libuv", "Confused about actual execution order and phases of the event loop", "Limited ability to explain libuv implementation details", "Shows foundational knowledge but needs deeper understanding for senior role"], "sub_skills": [{"name": "Node.js Runtime", "proficiency": "Inter'''

    print("🔧 Testing new repair function...")
    print(f"📄 Original length: {len(truncated_response)} chars")

    try:
        repaired = repair_incomplete_json(truncated_response)
        print(f"🔧 Repaired length: {len(repaired)} chars")

        # Try to parse
        parsed = json.loads(repaired)
        print("✅ Successfully parsed repaired JSON!")
        print(f"   Keys: {list(parsed.keys())}")

        # Check what we got
        if 'overall_assessment' in parsed:
            print(f"   Overall score: {parsed['overall_assessment']['overall_score']}")

        if 'competency_mapping' in parsed:
            comp_map = parsed['competency_mapping']
            print(f"   Competency mapping items: {len(comp_map)}")

        return True

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_new_repair()