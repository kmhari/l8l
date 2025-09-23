#!/usr/bin/env python3

import json
import requests

def test_dynamic_sample_generation():
    """
    Test that the evaluation uses the correct skill areas from the input
    """
    api_url = "http://localhost:8000"

    # Create test data with Data Warehousing skills
    test_data = {
        "resume": {
            "resume": "Test candidate with data warehousing experience",
            "job_title": "Data Engineer",
            "company_name": "Test Company",
            "candidate_name": "Test Candidate"
        },
        "transcript": {
            "messages": [
                {
                    "role": "agent",
                    "time": 1000,
                    "endTime": 2000,
                    "message": "Can you explain your experience with Snowflake?",
                    "duration": 1000,
                    "secondsFromStart": 0.0
                },
                {
                    "role": "user",
                    "time": 2000,
                    "endTime": 4000,
                    "message": "I have 3 years of experience with Snowflake data warehousing, including SQL optimization and DBT transformations.",
                    "duration": 2000,
                    "secondsFromStart": 1.0
                }
            ]
        },
        "technical_questions": "Q1: Explain your experience with Snowflake data warehousing",
        "key_skill_areas": [
            {
                "name": "Data Warehousing",
                "subSkillAreas": [
                    "Snowflake",
                    "SQL"
                ],
                "difficultyLevel": "medium"
            },
            {
                "name": "ETL/ELT Development",
                "subSkillAreas": [
                    "DBT Transformations"
                ],
                "difficultyLevel": "medium"
            },
            {
                "name": "Data Modeling",
                "subSkillAreas": [
                    "Star Schema"
                ],
                "difficultyLevel": "medium"
            }
        ]
    }

    print("🚀 Testing Dynamic Sample Response Generation")
    print("=" * 60)
    print(f"Input skill areas:")
    for skill in test_data["key_skill_areas"]:
        print(f"  - {skill['name']}: {skill['subSkillAreas']}")

    print(f"\n📡 Calling /generate-report API...")

    try:
        response = requests.post(
            f"{api_url}/generate-report",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=300
        )

        if response.status_code == 200:
            api_response = response.json()
            print("✅ API call successful!")

            # Debug: Show what we actually got
            print(f"\n🔍 RESPONSE STRUCTURE DEBUG")
            print("-" * 40)
            print(f"Response keys: {list(api_response.keys())}")
            if api_response:
                print(f"Response preview: {str(api_response)[:500]}...")

            # Check if evaluation contains the correct skill areas
            if 'evaluation_report' in api_response:
                evaluation = api_response['evaluation_report']

                if 'competency_mapping' in evaluation:
                    print(f"\n🔍 COMPETENCY MAPPING CHECK")
                    print("-" * 40)

                    competency_mapping = evaluation['competency_mapping']
                    actual_skill_areas = [comp['skill_area'] for comp in competency_mapping]
                    expected_skill_areas = [skill['name'] for skill in test_data['key_skill_areas']]

                    print(f"Expected skill areas: {expected_skill_areas}")
                    print(f"Actual skill areas:   {actual_skill_areas}")

                    # Check if they match
                    if set(actual_skill_areas) == set(expected_skill_areas):
                        print("✅ SUCCESS: Skill areas match!")

                        # Check subskills
                        print(f"\n🔍 SUBSKILL CHECK")
                        print("-" * 40)
                        for comp in competency_mapping:
                            skill_name = comp['skill_area']
                            actual_subskills = [sub['name'] for sub in comp.get('sub_skills', [])]

                            # Find expected subskills
                            expected_subskills = []
                            for skill in test_data['key_skill_areas']:
                                if skill['name'] == skill_name:
                                    expected_subskills = skill['subSkillAreas']
                                    break

                            print(f"{skill_name}:")
                            print(f"  Expected: {expected_subskills}")
                            print(f"  Actual:   {actual_subskills}")

                            if set(actual_subskills) == set(expected_subskills):
                                print(f"  ✅ Match!")
                            else:
                                print(f"  ❌ Mismatch!")
                    else:
                        print("❌ FAILURE: Skill areas don't match!")
                        print("This indicates the dynamic sample generation is not working correctly.")

                        # Show what we got instead
                        print(f"\nActual response structure:")
                        for comp in competency_mapping:
                            skill_name = comp['skill_area']
                            subskills = [sub['name'] for sub in comp.get('sub_skills', [])]
                            print(f"  {skill_name}: {subskills}")
                else:
                    print("❌ No competency_mapping found in response")
            else:
                print("❌ No evaluation found in response")
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        print("Make sure the FastAPI server is running on http://localhost:8000")

if __name__ == "__main__":
    test_dynamic_sample_generation()