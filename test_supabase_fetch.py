#!/usr/bin/env python3

import os
from fetch_call_logs import fetch_call_log_variables, fetch_call_log_variables_supabase, fetch_call_log_variables_postgres

def test_fetch():
    """
    Test the fetch_call_logs function with a sample room_name
    """
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Please create a .env file with required database credentials")
        print("Required variables:")
        print("- SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (for Supabase)")
        print("- HIREVOX_DATABASE_URL (for PostgreSQL)")
        return

    # Test with a sample room name
    test_room_name = "test_room"

    print(f"Testing fetch for room_name/call_id: {test_room_name}")
    print("=" * 50)

    # Test both sources
    print("1. Testing both sources (default):")
    try:
        variables = fetch_call_log_variables(test_room_name)
        print(f"Result: {variables}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Testing Supabase only:")
    try:
        variables = fetch_call_log_variables_supabase(test_room_name)
        print(f"Result: {variables}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n3. Testing PostgreSQL only:")
    try:
        variables = fetch_call_log_variables_postgres(test_room_name)
        print(f"Result: {variables}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fetch()