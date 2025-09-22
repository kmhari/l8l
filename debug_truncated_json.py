#!/usr/bin/env python3
"""Debug the specific truncated JSON response."""

import json

def analyze_truncated_response():
    """Analyze the specific truncated response to understand the issue."""
    truncated_response = '''{"overall_assessment": {"recommendation": "Hire", "confidence": "Medium", "overall_score": 65, "summary": "Candidate demonstrates basic understanding of Node.js asynchronous model and event loop concepts but shows confusion about execution order and specific phases. Has awareness of key components like libuv and microtask queue but lacks precise, detailed knowledge expected for a senior role."}, "competency_mapping": [{"skill_area": "Programming & Development", "overall_assessment": "Intermediate", "meets_requirements": true, "confidence": "Medium", "assessment_notes": ["Understands Node.js is single-threaded and uses event loop for async operations", "Aware of key concepts like microtask queue, promises, and libuv", "Confused about actual execution order and phases of the event loop", "Limited ability to explain libuv implementation details", "Shows foundational knowledge but needs deeper understanding for senior role"], "sub_skills": [{"name": "Node.js Runtime", "proficiency": "Inter'''

    print(f"📄 Response length: {len(truncated_response)} chars")
    print(f"🔚 Last 50 chars: {repr(truncated_response[-50:])}")

    # Let's see where it breaks
    print("\n🔍 Analyzing structure:")

    # Find where we are in the structure
    brace_count = 0
    bracket_count = 0
    in_string = False
    last_quote_pos = -1

    for i, char in enumerate(truncated_response):
        if char == '"' and (i == 0 or truncated_response[i-1] != '\\'):
            in_string = not in_string
            if in_string:
                last_quote_pos = i
        elif not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1

    print(f"   Open braces: {brace_count}")
    print(f"   Open brackets: {bracket_count}")
    print(f"   In string: {in_string}")
    print(f"   Last quote at: {last_quote_pos}")

    # Try a simple completion strategy
    print("\n🔧 Attempting simple repair...")

    repaired = truncated_response

    # If we're in a string, close it
    if in_string:
        repaired += '"'
        print("   ✅ Closed unterminated string")

    # Close any open arrays
    while bracket_count > 0:
        repaired += ']'
        bracket_count -= 1
        print("   ✅ Closed array")

    # Close any open objects
    while brace_count > 0:
        repaired += '}'
        brace_count -= 1
        print("   ✅ Closed object")

    print(f"\n📏 Repaired length: {len(repaired)} chars")

    # Try to parse
    try:
        parsed = json.loads(repaired)
        print("✅ Successfully parsed repaired JSON!")
        print(f"   Keys: {list(parsed.keys())}")

        # Check the competency mapping
        if 'competency_mapping' in parsed:
            comp_map = parsed['competency_mapping']
            print(f"   Competency mapping has {len(comp_map)} items")
            if len(comp_map) > 0 and 'sub_skills' in comp_map[0]:
                sub_skills = comp_map[0]['sub_skills']
                print(f"   Sub-skills: {len(sub_skills)} items")
                if len(sub_skills) > 0:
                    print(f"   First sub-skill: {sub_skills[0]}")

        return repaired, parsed

    except json.JSONDecodeError as e:
        print(f"❌ Still failed: {str(e)}")
        print(f"   Error at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")

        # Show the area around the error
        if hasattr(e, 'pos') and e.pos < len(repaired):
            start = max(0, e.pos - 20)
            end = min(len(repaired), e.pos + 20)
            print(f"   Context: {repr(repaired[start:end])}")

        return None, None

if __name__ == "__main__":
    analyze_truncated_response()