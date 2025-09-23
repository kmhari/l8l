#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
import psycopg2.extras
import argparse
import json
from urllib.parse import urlparse, parse_qs

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

def main():
    parser = argparse.ArgumentParser(description='Fetch call_logs data and create evaluation JSON')
    parser.add_argument('room_name', help='Room name/call_id to search for')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')

    args = parser.parse_args()

    print(f"Fetching data for room_name/call_id: {args.room_name}")

    # Fetch from Supabase
    print("Fetching from Supabase...")
    supabase_data = {}
    try:
        supabase_data = fetch_call_log_variables_supabase(args.room_name)
        if supabase_data:
            print("✓ Found data in Supabase")
        else:
            print("✗ No data found in Supabase")
    except Exception as e:
        print(f"✗ Supabase query failed: {e}")

    # Fetch from PostgreSQL
    print("Fetching from PostgreSQL...")
    postgres_data = {}
    try:
        postgres_data = fetch_call_log_variables_postgres(args.room_name)
        if postgres_data:
            print("✓ Found data in PostgreSQL")
        else:
            print("✗ No data found in PostgreSQL")
    except Exception as e:
        print(f"✗ PostgreSQL query failed: {e}")

    # Fetch job details if we have job_id
    job_details = {}
    if postgres_data and 'job_id' in postgres_data:
        job_id = postgres_data['job_id']
        print(f"Fetching job details for job_id: {job_id}")
        try:
            job_details = fetch_job_details_postgres(job_id)
            if job_details:
                print("✓ Found job details")
            else:
                print("✗ No job details found")
        except Exception as e:
            print(f"✗ Job details query failed: {e}")

    # Create evaluation JSON
    if supabase_data or postgres_data:
        evaluation_json = create_evaluation_json(supabase_data, postgres_data, job_details)

        print("\n" + "="*50)
        print("EVALUATION JSON")
        print("="*50)

        if args.pretty:
            print(json.dumps(evaluation_json, indent=2, default=str))
        else:
            print(json.dumps(evaluation_json, default=str))
    else:
        print("No data found from any source")

if __name__ == "__main__":
    main()