#!/usr/bin/env python3

import json
import requests

def test_api_integration():
    """
    Test the /generate-report API endpoint integration
    """
    api_url = "http://localhost:8000"

    # Load sample evaluation data
    try:
        with open('sample/evaluate.json', 'r') as f:
            evaluation_data = json.load(f)
        print("✓ Loaded sample evaluation data")
    except Exception as e:
        print(f"✗ Failed to load sample data: {e}")
        return

    # Test API endpoint
    print(f"\n🚀 Testing /generate-report API at {api_url}")
    print("=" * 50)

    try:
        response = requests.post(
            f"{api_url}/generate-report",
            json=evaluation_data,
            headers={"Content-Type": "application/json"},
            timeout=300
        )

        if response.status_code == 200:
            print("✓ API call successful!")
            api_response = response.json()

            # Display key results
            print("\n📊 EVALUATION SUMMARY")
            print("-" * 30)

            if 'evaluation' in api_response:
                evaluation = api_response['evaluation']

                # Overall recommendation
                if 'overall_recommendation' in evaluation:
                    rec = evaluation['overall_recommendation']
                    print(f"Overall Score: {rec.get('overall_score', 'N/A')}/10")
                    print(f"Recommendation: {rec.get('recommendation', 'N/A')}")
                    print(f"Confidence: {rec.get('confidence_level', 'N/A')}")

                # Skill areas
                if 'skill_area_evaluations' in evaluation:
                    print(f"\n🎯 SKILL AREAS")
                    print("-" * 20)
                    for skill_eval in evaluation['skill_area_evaluations']:
                        skill_name = skill_eval.get('skill_area_name', 'Unknown')
                        score = skill_eval.get('score', 'N/A')
                        print(f"{skill_name}: {score}/10")

                # Technical assessment
                if 'technical_assessment' in evaluation:
                    tech = evaluation['technical_assessment']
                    print(f"\n💻 TECHNICAL SCORES")
                    print("-" * 20)
                    print(f"Problem Solving: {tech.get('problem_solving_score', 'N/A')}/10")
                    print(f"Technical Depth: {tech.get('technical_depth_score', 'N/A')}/10")
                    print(f"Communication: {tech.get('communication_score', 'N/A')}/10")

            # Metadata
            if 'metadata' in api_response:
                meta = api_response['metadata']
                print(f"\n⚙️ METADATA")
                print("-" * 20)
                print(f"Processing Time: {meta.get('processing_time_seconds', 'N/A')}s")
                print(f"Model Used: {meta.get('model_used', 'N/A')}")

        else:
            print(f"✗ API Error {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        print("Make sure the FastAPI server is running on http://localhost:8000")

if __name__ == "__main__":
    test_api_integration()