#!/usr/bin/env python3
"""
Test script for the new gather and generate-report endpoints
"""

import json
import requests
import time
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000"

def test_gather_endpoint():
    """Test the /gather endpoint with sample data"""
    print("\n" + "="*60)
    print("🧪 Testing /gather endpoint")
    print("="*60)

    try:
        # Get sample data
        print("📋 Loading sample data...")
        response = requests.get(f"{BASE_URL}/sample")
        if response.status_code != 200:
            print(f"❌ Failed to get sample data: {response.status_code}")
            return None

        sample_data = response.json()
        print("✅ Sample data loaded")

        # Test gather endpoint
        print("🔄 Testing /gather endpoint...")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/gather",
            json=sample_data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        duration = time.time() - start_time
        print(f"⏱️  Request completed in {duration:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ /gather endpoint working!")

            # Print summary
            llm_output = result.get('llm_output', {})
            groups = llm_output.get('groups', [])
            facts = llm_output.get('pre_inferred_facts_global', {})

            print(f"📊 Results:")
            print(f"   Question Groups: {len(groups)}")
            print(f"   Global Facts: {len(facts)} items")

            # Show group details
            for i, group in enumerate(groups[:3]):  # Show first 3 groups
                print(f"   Group {i+1}: {group.get('question_id', 'N/A')} - {group.get('question_title', 'N/A')}")

            if len(groups) > 3:
                print(f"   ... and {len(groups)-3} more groups")

            return result
        else:
            print(f"❌ /gather endpoint failed: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            return None

    except Exception as e:
        print(f"❌ Error testing /gather endpoint: {e}")
        return None

def test_generate_report_endpoint():
    """Test the /generate-report endpoint with sample data"""
    print("\n" + "="*60)
    print("🧪 Testing /generate-report endpoint")
    print("="*60)

    try:
        # Get sample data for evaluation
        print("📋 Loading evaluation sample data...")
        response = requests.get(f"{BASE_URL}/sample-evaluate")
        if response.status_code != 200:
            print(f"❌ Failed to get evaluation sample data: {response.status_code}")
            return None

        sample_data = response.json()
        print("✅ Evaluation sample data loaded")

        # Test generate-report endpoint
        print("🔄 Testing /generate-report endpoint...")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/generate-report",
            json=sample_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes for comprehensive evaluation
        )

        duration = time.time() - start_time
        print(f"⏱️  Request completed in {duration:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ /generate-report endpoint working!")

            # Print summary
            evaluation_report = result.get('evaluation_report', {})
            question_groups = result.get('question_groups', {})

            print(f"📊 Results:")

            # Overall assessment
            overall = evaluation_report.get('overall_assessment', {})
            print(f"   Overall Score: {overall.get('overall_score', 'N/A')}")
            print(f"   Recommendation: {overall.get('recommendation', 'N/A')}")
            print(f"   Confidence: {overall.get('confidence', 'N/A')}")

            # Competency mapping
            competencies = evaluation_report.get('competency_mapping', [])
            print(f"   Skill Areas Evaluated: {len(competencies)}")

            # Question analysis
            questions = evaluation_report.get('question_analysis', [])
            print(f"   Questions Analyzed: {len(questions)}")

            # Critical analysis
            critical = evaluation_report.get('critical_analysis', {})
            red_flags = critical.get('red_flags', [])
            exceptional = critical.get('exceptional_responses', [])
            print(f"   Red Flags: {len(red_flags)}")
            print(f"   Exceptional Responses: {len(exceptional)}")

            # Question groups from gather step
            groups = question_groups.get('groups', [])
            print(f"   Question Groups (from gather): {len(groups)}")

            return result
        else:
            print(f"❌ /generate-report endpoint failed: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            return None

    except Exception as e:
        print(f"❌ Error testing /generate-report endpoint: {e}")
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

def main():
    """Main test function"""
    print("🚀 Testing New Interview API Endpoints")
    print("=" * 60)

    # Test API health
    if not test_api_health():
        return

    # Test gather endpoint first
    gather_result = test_gather_endpoint()

    # Test generate-report endpoint
    report_result = test_generate_report_endpoint()

    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)

    gather_status = "✅ PASSED" if gather_result else "❌ FAILED"
    report_status = "✅ PASSED" if report_result else "❌ FAILED"

    print(f"/gather endpoint: {gather_status}")
    print(f"/generate-report endpoint: {report_status}")

    if gather_result and report_result:
        print("\n🎉 All tests passed! The new endpoints are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()