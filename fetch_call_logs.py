#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
import psycopg2.extras
import argparse
import json
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

def save_response_to_json(data: dict, source: str, call_id: str, data_type: str = "call_logs", output_dir: str = "database_responses") -> str:
    """
    Save database response to JSON file

    Args:
        data: The response data to save
        source: The data source ('supabase' or 'postgres')
        call_id: The call ID for naming the file
        data_type: Type of data ('call_logs', 'job_details')

    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create filename
    filename = f"{source}_{data_type}_{call_id}_{timestamp}.json"
    file_path = output_path / filename

    # Prepare data with metadata
    output_data = {
        "metadata": {
            "source": source,
            "data_type": data_type,
            "call_id": call_id,
            "timestamp": timestamp,
            "generated_at": datetime.now().isoformat()
        },
        "data": data
    }

    # Save to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Saved {source} {data_type} response to: {file_path}")
        return str(file_path)
    except Exception as e:
        print(f"❌ Failed to save {source} response: {e}")
        return ""

def fetch_call_log_variables_supabase(room_name: str) -> dict:
    """
    Fetch entire call_logs row from table for a given room_name using Supabase

    Args:
        room_name: The room name to search for

    Returns:
        Dictionary containing the entire row data
    """
    # Load environment variables
    load_dotenv()

    # Get Supabase credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env file")

    # Create Supabase client
    supabase: Client = create_client(url, key)

    try:
        # Query call_logs table for the room_name - fetch all columns
        response = supabase.table('call_logs').select('*').eq('room_name', room_name).execute()

        if not response.data:
            print(f"No records found for room_name: {room_name}")
            return {}

        # Return the entire row from the first match
        return response.data[0]

    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        return {}

def fetch_call_log_variables_postgres(room_name: str) -> dict:
    """
    Fetch entire call_logs row from table for a given call_id (room_name) using direct PostgreSQL

    Args:
        room_name: The call_id to search for

    Returns:
        Dictionary containing the entire row data
    """
    # Load environment variables
    load_dotenv()

    # Get PostgreSQL connection URL
    database_url = os.getenv('HIREVOX_DATABASE_URL')

    if not database_url:
        raise ValueError("Missing HIREVOX_DATABASE_URL in .env file")

    try:
        # Parse the URL to clean it up and remove unsupported parameters
        parsed = urlparse(database_url)

        # Create a clean connection string with only standard PostgreSQL parameters
        clean_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}{parsed.path}"

        # Connect to PostgreSQL with the cleaned URL
        conn = psycopg2.connect(clean_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query call_logs table for the call_id - fetch all columns
        cursor.execute("SELECT job_id FROM call_logs WHERE call_id = %s", (room_name,))

        result = cursor.fetchone()

        if not result:
            print(f"No records found for call_id: {room_name}")
            return {}

        # Close connections
        cursor.close()
        conn.close()

        # Convert result to dict and return
        return dict(result)

    except Exception as e:
        print(f"Error fetching data from PostgreSQL: {e}")
        return {}

def fetch_job_details_postgres(job_id: int) -> dict:
    """
    Fetch job details from jobs table for a given job_id using direct PostgreSQL

    Args:
        job_id: The job_id to search for

    Returns:
        Dictionary containing the job data
    """
    # Load environment variables
    load_dotenv()

    # Get PostgreSQL connection URL
    database_url = os.getenv('HIREVOX_DATABASE_URL')

    if not database_url:
        raise ValueError("Missing HIREVOX_DATABASE_URL in .env file")

    try:
        # Parse the URL to clean it up and remove unsupported parameters
        parsed = urlparse(database_url)

        # Create a clean connection string with only standard PostgreSQL parameters
        clean_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}{parsed.path}"

        # Connect to PostgreSQL with the cleaned URL
        conn = psycopg2.connect(clean_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query jobs table for the job_id
        cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))

        result = cursor.fetchone()

        if not result:
            print(f"No job found for job_id: {job_id}")
            return {}

        # Close connections
        cursor.close()
        conn.close()

        # Convert result to dict and return
        return dict(result)

    except Exception as e:
        print(f"Error fetching job data from PostgreSQL: {e}")
        return {}

def fetch_call_log_variables(room_name: str, source: str = 'both') -> dict:
    """
    Fetch entire call_logs row from table for a given room_name/call_id

    Args:
        room_name: The room name/call_id to search for
        source: 'supabase', 'postgres', or 'both' (default)

    Returns:
        Dictionary containing the entire row data
    """
    if source in ['supabase', 'both']:
        try:
            result = fetch_call_log_variables_supabase(room_name)
            if result:
                print(f"Found data in Supabase for room_name: {room_name}")
                return result
        except Exception as e:
            print(f"Supabase query failed: {e}")

    if source in ['postgres', 'both']:
        try:
            result = fetch_call_log_variables_postgres(room_name)
            if result:
                print(f"Found data in PostgreSQL for call_id: {room_name}")
                return result
        except Exception as e:
            print(f"PostgreSQL query failed: {e}")

    return {}

def create_evaluation_json(supabase_data: dict, postgres_data: dict, job_details: dict) -> dict:
    """
    Create JSON structure matching sample/evaluate2.json format

    Args:
        supabase_data: Data from Supabase call_logs
        postgres_data: Data from PostgreSQL call_logs
        job_details: Job details from PostgreSQL jobs table

    Returns:
        Dictionary in the required format
    """
    # Use postgres_data as primary source since it has more complete data
    call_data = postgres_data if postgres_data else supabase_data

    # Extract transcript from the data
    transcript_data = {}
    if 'transcript' in supabase_data:
        if isinstance(supabase_data['transcript'], str):
            try:
                transcript_data = json.loads(supabase_data['transcript'])
            except:
                transcript_data = {"messages": []}
        else:
            transcript_data = supabase_data['transcript']
    elif 'artifact' in call_data and 'messages' in call_data['artifact']:
        transcript_data = {"messages": call_data['artifact']['messages']}

    # Extract resume details from Supabase variables field
    resume_data = {
        "resume": "Resume content not available",
        "job_title": "Job title not available",
        "company_name": "Company name not available",
        "salary_range": "Not specified",
        "candidate_name": "Candidate name not available",
        "company_profile": "Company profile not available",
        "job_requirements": "Job requirements not available",
        "candidate_contact": "Contact not available",
        "lead_contact_name": "Lead contact not available",
        "additional_questions": "Additional questions not available",
        "recruitment_firm_name": "HireVox",
        "non_technical_questions": ""
    }

    # Try to extract resume details from Supabase variables
    if supabase_data and 'variables' in supabase_data:
        variables = supabase_data['variables']
        if isinstance(variables, dict):
            # Extract all available fields from variables
            resume_data.update({
                "resume": variables.get("resume", resume_data["resume"]),
                "job_title": variables.get("job_title", resume_data["job_title"]),
                "company_name": variables.get("company_name", resume_data["company_name"]),
                "salary_range": variables.get("salary_range", resume_data["salary_range"]),
                "candidate_name": variables.get("candidate_name", resume_data["candidate_name"]),
                "company_profile": variables.get("company_profile", resume_data["company_profile"]),
                "job_requirements": variables.get("job_requirements", resume_data["job_requirements"]),
                "candidate_contact": variables.get("candidate_contact", resume_data["candidate_contact"]),
                "lead_contact_name": variables.get("lead_contact_name", resume_data["lead_contact_name"]),
                "additional_questions": variables.get("additional_questions", resume_data["additional_questions"]),
                "recruitment_firm_name": variables.get("recruitment_firm_name", resume_data["recruitment_firm_name"]),
                "non_technical_questions": variables.get("non_technical_questions", resume_data["non_technical_questions"])
            })

    # Build the evaluation JSON structure
    evaluation_json = {
        "resume": resume_data,
        "transcript": transcript_data,
        "technical_questions": "Technical questions not available",
        "key_skill_areas": job_details.get('key_skill_areas', []) if job_details else []
    }

    return evaluation_json

def generate_call_report(supabase_data: dict, postgres_data: dict, job_details: dict) -> dict:
    """
    Generate a comprehensive report for the call

    Args:
        supabase_data: Data from Supabase call_logs
        postgres_data: Data from PostgreSQL call_logs
        job_details: Job details from PostgreSQL jobs table

    Returns:
        Dictionary containing the report
    """
    call_data = postgres_data if postgres_data else supabase_data

    # Extract basic call information - prioritize PostgreSQL data
    call_id = 'N/A'
    status = 'N/A'

    if postgres_data:
        call_id = postgres_data.get('call_id', 'N/A')
        status = postgres_data.get('status', 'N/A')
    elif supabase_data:
        call_id = supabase_data.get('room_name', 'N/A')
        status = supabase_data.get('status', 'N/A')

    call_info = {
        "call_id": call_id,
        "status": status,
        "duration": "N/A",
        "candidate_name": "N/A",
        "job_title": "N/A",
        "company_name": "N/A"
    }

    # Extract duration from different sources
    if 'call_duration' in call_data:
        duration_seconds = call_data['call_duration']
        call_info["duration"] = f"{duration_seconds // 60}m {duration_seconds % 60}s"
    elif supabase_data and 'transcript' in supabase_data:
        # Handle string transcript
        transcript_data = supabase_data['transcript']
        if isinstance(transcript_data, str):
            try:
                transcript = json.loads(transcript_data)
            except:
                transcript = {}
        else:
            transcript = transcript_data

        if isinstance(transcript, dict) and 'stats' in transcript:
            duration_ms = transcript['stats'].get('duration', 0)
            duration_seconds = duration_ms // 1000
            call_info["duration"] = f"{duration_seconds // 60}m {duration_seconds % 60}s"

    # Extract candidate info from variables
    if supabase_data and 'variables' in supabase_data:
        variables = supabase_data['variables']
        if isinstance(variables, dict):
            call_info["candidate_name"] = variables.get('candidate_name', 'N/A')
            call_info["job_title"] = variables.get('job_title', 'N/A')
            call_info["company_name"] = variables.get('company_name', 'N/A')

    # Extract key skill areas
    skill_areas = []
    if job_details and 'key_skill_areas' in job_details:
        skill_areas = job_details['key_skill_areas']

    # Count transcript messages
    message_stats = {"total_messages": 0, "user_messages": 0, "agent_messages": 0}
    if supabase_data and 'transcript' in supabase_data:
        # Handle string transcript
        transcript_data = supabase_data['transcript']
        if isinstance(transcript_data, str):
            try:
                transcript = json.loads(transcript_data)
            except:
                transcript = {}
        else:
            transcript = transcript_data

        if isinstance(transcript, dict) and 'messages' in transcript:
            messages = transcript['messages']
            message_stats["total_messages"] = len(messages)
            message_stats["user_messages"] = len([m for m in messages if m.get('role') == 'user'])
            message_stats["agent_messages"] = len([m for m in messages if m.get('role') == 'agent'])

    return {
        "call_information": call_info,
        "skill_areas": skill_areas,
        "conversation_stats": message_stats,
        "data_sources": {
            "supabase_available": bool(supabase_data),
            "postgres_available": bool(postgres_data),
            "job_details_available": bool(job_details)
        }
    }

def print_report(report: dict):
    """Print a formatted report"""
    print("\n" + "="*60)
    print("CALL INTERVIEW REPORT")
    print("="*60)

    # Call Information
    print("\n📞 CALL INFORMATION")
    print("-" * 30)
    call_info = report["call_information"]
    print(f"Call ID: {call_info['call_id']}")
    print(f"Status: {call_info['status']}")
    print(f"Duration: {call_info['duration']}")
    print(f"Candidate: {call_info['candidate_name']}")
    print(f"Position: {call_info['job_title']}")
    print(f"Company: {call_info['company_name']}")

    # Conversation Statistics
    print("\n💬 CONVERSATION STATISTICS")
    print("-" * 30)
    stats = report["conversation_stats"]
    print(f"Total Messages: {stats['total_messages']}")
    print(f"Candidate Messages: {stats['user_messages']}")
    print(f"Interviewer Messages: {stats['agent_messages']}")

    # Skill Areas
    print("\n🎯 KEY SKILL AREAS")
    print("-" * 30)
    skill_areas = report["skill_areas"]
    if skill_areas:
        for i, skill in enumerate(skill_areas, 1):
            print(f"{i}. {skill['name']} ({skill['difficultyLevel']})")
            for sub_skill in skill.get('subSkillAreas', []):
                print(f"   • {sub_skill}")
    else:
        print("No skill areas found")

    # Data Sources
    print("\n📊 DATA SOURCES")
    print("-" * 30)
    sources = report["data_sources"]
    print(f"Supabase: {'✓ Available' if sources['supabase_available'] else '✗ Not found'}")
    print(f"PostgreSQL: {'✓ Available' if sources['postgres_available'] else '✗ Not found'}")
    print(f"Job Details: {'✓ Available' if sources['job_details_available'] else '✗ Not found'}")

def call_generate_report_api(evaluation_json: dict, api_url: str = "http://localhost:8000") -> dict:
    """
    Call the /generate-report API endpoint with evaluation data

    Args:
        evaluation_json: The evaluation data in the required format
        api_url: Base URL for the API (default: localhost:8000)

    Returns:
        Dictionary containing the API response
    """
    # Transform evaluation_json to match API request structure
    api_request = {
        "transcript": evaluation_json.get("transcript", {}),
        "resume": evaluation_json.get("resume", {}),
        "key_skill_areas": evaluation_json.get("key_skill_areas", [])
    }

    #store api_request to a file for debugging
    with open("api_request_debug.json", "w") as f:
        json.dump(api_request, f, indent=2, ensure_ascii=False, default=str)

    try:
        response = requests.post(
            f"{api_url}/generate-report",
            json=api_request,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minute timeout for LLM processing
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error {response.status_code}: {response.text}")
            return {}

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Generate interview report using /generate-report API')
    parser.add_argument('call_id', help='Call ID to search for')
    parser.add_argument('--json', action='store_true', help='Output full API response JSON')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--local-only', action='store_true', help='Skip API call, show only local data')
    parser.add_argument('--no-save', action='store_true', help='Skip saving database responses to JSON files')
    parser.add_argument('--save-dir', default='database_responses', help='Directory to save JSON files (default: database_responses)')

    args = parser.parse_args()

    print(f"Generating report for call_id: {args.call_id}")

    # Fetch from Supabase
    print("Fetching from Supabase...")
    supabase_data = {}
    supabase_file_path = ""
    try:
        supabase_data = fetch_call_log_variables_supabase(args.call_id)
        if supabase_data:
            print("✓ Found data in Supabase")
            # Save Supabase response to JSON file
            if not args.no_save:
                supabase_file_path = save_response_to_json(supabase_data, "supabase", args.call_id, "call_logs", args.save_dir)
        else:
            print("✗ No data found in Supabase")
    except Exception as e:
        print(f"✗ Supabase query failed: {e}")

    # Fetch from PostgreSQL
    print("Fetching from PostgreSQL...")
    postgres_data = {}
    postgres_file_path = ""
    try:
        postgres_data = fetch_call_log_variables_postgres(args.call_id)
        if postgres_data:
            print("✓ Found data in PostgreSQL")
            # Save PostgreSQL response to JSON file
            if not args.no_save:
                postgres_file_path = save_response_to_json(postgres_data, "postgres", args.call_id, "call_logs", args.save_dir)
        else:
            print("✗ No data found in PostgreSQL")
    except Exception as e:
        print(f"✗ PostgreSQL query failed: {e}")

    # Fetch job details if we have job_id
    job_details = {}
    job_details_file_path = ""
    if postgres_data and 'job_id' in postgres_data:
        job_id = postgres_data['job_id']
        print(f"Fetching job details for job_id: {job_id}")
        try:
            job_details = fetch_job_details_postgres(job_id)
            if job_details:
                print("✓ Found job details")
                # Save job details response to JSON file
                if not args.no_save:
                    job_details_file_path = save_response_to_json(job_details, "postgres", args.call_id, "job_details", args.save_dir)
            else:
                print("✗ No job details found")
        except Exception as e:
            print(f"✗ Job details query failed: {e}")

    # Generate evaluation JSON for API
    if supabase_data or postgres_data:
        evaluation_json = create_evaluation_json(supabase_data, postgres_data, job_details)

        if args.local_only:
            # Output local data only
            print("\n" + "="*50)
            print("LOCAL EVALUATION DATA")
            print("="*50)
            if args.pretty:
                print(json.dumps(evaluation_json, indent=2, default=str))
            else:
                print(json.dumps(evaluation_json, default=str))
        else:
            # Call the API for report generation
            print(f"\nCalling /generate-report API at {args.api_url}...")
            api_response = call_generate_report_api(evaluation_json, args.api_url)

            if api_response:
                print("✓ Report generated successfully")
                print("\n" + "="*60)
                print("INTERVIEW EVALUATION REPORT")
                print("="*60)

                if args.json:
                    # Output full API response
                    if args.pretty:
                        print(json.dumps(api_response, indent=2, default=str))
                    else:
                        print(json.dumps(api_response, default=str))
                else:
                    # Extract and display key information from API response
                    if 'evaluation' in api_response:
                        evaluation = api_response['evaluation']

                        # Display overall score and recommendation
                        if 'overall_recommendation' in evaluation:
                            rec = evaluation['overall_recommendation']
                            print(f"Overall Score: {rec.get('overall_score', 'N/A')}/10")
                            print(f"Recommendation: {rec.get('recommendation', 'N/A')}")
                            print(f"Confidence: {rec.get('confidence_level', 'N/A')}")

                        # Display skill area evaluations
                        if 'skill_area_evaluations' in evaluation:
                            print(f"\n🎯 SKILL AREA EVALUATIONS")
                            print("-" * 30)
                            for skill_eval in evaluation['skill_area_evaluations']:
                                skill_name = skill_eval.get('skill_area_name', 'Unknown')
                                score = skill_eval.get('score', 'N/A')
                                print(f"{skill_name}: {score}/10")

                        # Display technical assessment
                        if 'technical_assessment' in evaluation:
                            tech = evaluation['technical_assessment']
                            print(f"\n💻 TECHNICAL ASSESSMENT")
                            print("-" * 30)
                            print(f"Problem Solving: {tech.get('problem_solving_score', 'N/A')}/10")
                            print(f"Technical Depth: {tech.get('technical_depth_score', 'N/A')}/10")
                            print(f"Communication: {tech.get('communication_score', 'N/A')}/10")

                        # Display key insights
                        if 'key_insights' in evaluation:
                            insights = evaluation['key_insights']
                            if insights.get('strengths'):
                                print(f"\n✅ STRENGTHS")
                                print("-" * 30)
                                for strength in insights['strengths']:
                                    print(f"• {strength}")

                            if insights.get('areas_for_improvement'):
                                print(f"\n⚠️ AREAS FOR IMPROVEMENT")
                                print("-" * 30)
                                for area in insights['areas_for_improvement']:
                                    print(f"• {area}")

                    # Display metadata
                    if 'metadata' in api_response:
                        meta = api_response['metadata']
                        print(f"\n📊 METADATA")
                        print("-" * 30)
                        print(f"Processing Time: {meta.get('processing_time_seconds', 'N/A')}s")
                        print(f"Model Used: {meta.get('model_used', 'N/A')}")
                        print(f"Generated At: {meta.get('generated_at', 'N/A')}")
            else:
                print("✗ Failed to generate report via API")
                print("Falling back to local analysis...")
                # Fallback to local report generation
                report = generate_call_report(supabase_data, postgres_data, job_details)
                print_report(report)

        # Show summary of saved files
        if not args.no_save:
            print(f"\n📁 SAVED FILES SUMMARY")
            print("-" * 30)
            if supabase_file_path:
                print(f"Supabase call_logs: {supabase_file_path}")
            if postgres_file_path:
                print(f"PostgreSQL call_logs: {postgres_file_path}")
            if job_details_file_path:
                print(f"Job details: {job_details_file_path}")
            if not any([supabase_file_path, postgres_file_path, job_details_file_path]):
                print("No files were saved (no data found)")
        else:
            print(f"\n📁 File saving was disabled (--no-save flag used)")
    else:
        print("No data found from any source")

if __name__ == "__main__":
    main()