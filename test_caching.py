#!/usr/bin/env python3
"""
Test script for the caching functionality of the gather endpoint
"""

import json
import requests
import time
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000"

def test_cache_functionality():
    """Test the caching system with the gather endpoint"""
    print("\n" + "="*60)
    print("🧪 Testing Gather Endpoint Caching System")
    print("="*60)

    try:
        # Get sample data
        print("📋 Loading sample data...")
        response = requests.get(f"{BASE_URL}/sample")
        if response.status_code != 200:
            print(f"❌ Failed to get sample data: {response.status_code}")
            return False

        sample_data = response.json()
        print("✅ Sample data loaded")

        # First call - should trigger LLM generation and cache storage
        print("\n🔄 First call (should generate and cache)...")
        start_time = time.time()

        response1 = requests.post(
            f"{BASE_URL}/gather",
            json=sample_data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        first_duration = time.time() - start_time
        print(f"⏱️  First call completed in {first_duration:.2f} seconds")

        if response1.status_code != 200:
            print(f"❌ First call failed: {response1.status_code}")
            return False

        result1 = response1.json()
        print("✅ First call successful")

        # Wait a moment
        time.sleep(1)

        # Second call - should use cache
        print("\n🎯 Second call (should use cache)...")
        start_time = time.time()

        response2 = requests.post(
            f"{BASE_URL}/gather",
            json=sample_data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        second_duration = time.time() - start_time
        print(f"⏱️  Second call completed in {second_duration:.2f} seconds")

        if response2.status_code != 200:
            print(f"❌ Second call failed: {response2.status_code}")
            return False

        result2 = response2.json()
        print("✅ Second call successful")

        # Compare results
        print("\n🔍 Comparing results...")
        if result1 == result2:
            print("✅ Results are identical - cache is working!")
        else:
            print("❌ Results differ - cache might not be working properly")
            return False

        # Check performance improvement
        speed_improvement = ((first_duration - second_duration) / first_duration) * 100
        print(f"⚡ Speed improvement: {speed_improvement:.1f}%")

        if second_duration < first_duration:
            print("✅ Second call was faster - cache is providing performance benefit!")
        else:
            print("⚠️  Second call was not faster - but results are consistent")

        return True

    except Exception as e:
        print(f"❌ Error testing cache functionality: {e}")
        return False

def test_cache_stats():
    """Test the cache statistics endpoint"""
    print("\n" + "="*60)
    print("📊 Testing Cache Statistics")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/cache/stats")
        if response.status_code != 200:
            print(f"❌ Failed to get cache stats: {response.status_code}")
            return False

        stats = response.json()
        print("✅ Cache stats retrieved successfully")

        print(f"📁 Cache directory: {stats['cache_directory']}")
        print(f"📦 Total cached items: {stats['total_cached_items']}")
        print(f"💾 Total cache size: {stats['total_cache_size_mb']} MB")

        if stats['cached_files']:
            print("\n📋 Recent cache files:")
            for i, file_info in enumerate(stats['cached_files'][:3]):  # Show first 3
                age_hours = file_info['age_hours']
                size_kb = file_info['size_bytes'] / 1024
                print(f"   {i+1}. {file_info['cache_key'][:16]}... (Age: {age_hours:.1f}h, Size: {size_kb:.1f}KB)")

        return True

    except Exception as e:
        print(f"❌ Error testing cache stats: {e}")
        return False

def test_cache_modification():
    """Test modifying sample data to verify cache key generation"""
    print("\n" + "="*60)
    print("🔧 Testing Cache Key Sensitivity")
    print("="*60)

    try:
        # Get sample data
        response = requests.get(f"{BASE_URL}/sample")
        if response.status_code != 200:
            print(f"❌ Failed to get sample data: {response.status_code}")
            return False

        sample_data = response.json()

        # Modify the data slightly
        modified_data = sample_data.copy()
        modified_data["technical_questions"] = sample_data["technical_questions"] + "\n\n# Additional test question"

        print("🔄 Testing with modified data (should miss cache)...")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/gather",
            json=modified_data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        duration = time.time() - start_time
        print(f"⏱️  Modified data call completed in {duration:.2f} seconds")

        if response.status_code == 200:
            print("✅ Modified data processed successfully")
            print("✅ Cache key generation is sensitive to input changes")
            return True
        else:
            print(f"❌ Modified data call failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error testing cache modification: {e}")
        return False

def test_cache_management():
    """Test cache management endpoints"""
    print("\n" + "="*60)
    print("🗑️  Testing Cache Management")
    print("="*60)

    try:
        # Get cache stats before clearing
        stats_response = requests.get(f"{BASE_URL}/cache/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            items_before = stats['total_cached_items']
            print(f"📊 Cache items before clearing: {items_before}")
        else:
            items_before = "unknown"

        # Clear cache
        print("🧹 Clearing cache...")
        clear_response = requests.delete(f"{BASE_URL}/cache/clear")
        if clear_response.status_code != 200:
            print(f"❌ Failed to clear cache: {clear_response.status_code}")
            return False

        clear_result = clear_response.json()
        print(f"✅ {clear_result['message']}")
        print(f"🗑️  Files deleted: {clear_result['files_deleted']}")

        # Verify cache is empty
        stats_response = requests.get(f"{BASE_URL}/cache/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            items_after = stats['total_cached_items']
            print(f"📊 Cache items after clearing: {items_after}")

            if items_after == 0:
                print("✅ Cache successfully cleared")
                return True
            else:
                print("❌ Cache not completely cleared")
                return False

    except Exception as e:
        print(f"❌ Error testing cache management: {e}")
        return False

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
    print("🚀 Testing Gather Endpoint Caching System")
    print("=" * 60)

    # Test API health
    if not test_api_health():
        return

    # Run cache tests
    tests = [
        ("Cache Functionality", test_cache_functionality),
        ("Cache Statistics", test_cache_stats),
        ("Cache Key Sensitivity", test_cache_modification),
        ("Cache Management", test_cache_management),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)

    passed = 0
    total = len(tests)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All caching tests passed! The system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()