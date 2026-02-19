"""
test_api.py - Example script to test the AI Timetable Generator API

This script demonstrates how to interact with the backend API.
Run the backend first, then run this script.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api"

# Test user data
TEST_USER = {
    "email": "test@example.com",
    "name": "Test User",
    "is_student": True,
    "wake_up_time": "06:00",
    "sleep_time": "23:00",
    "work_start_time": "09:00",
    "work_end_time": "17:00",
    "subjects": [
        {"name": "Data Structures", "priority": 1, "daily_hours": 3},
        {"name": "Web Development", "priority": 2, "daily_hours": 2},
        {"name": "Mathematics", "priority": 3, "daily_hours": 1.5}
    ],
    "productivity_type": "morning_person",
    "goal_type": "exam_prep",
    "break_frequency": 30,
    "lunch_time_preference": "12:30",
    "tea_time_preference": "15:00",
    "exercise_time": "07:00",
    "exercise_duration": 45,
    "free_time_required": 2,
    "preferred_timetable_type": "daily"
}


def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_create_profile():
    """Test: Create user profile"""
    print_section("CREATE USER PROFILE")
    
    response = requests.post(f"{BASE_URL}/profiles", json=TEST_USER)
    
    if response.status_code == 201:
        profile = response.json()
        print("✅ Profile created successfully!")
        print(f"Profile ID: {profile.get('_id')}")
        print(f"Email: {profile.get('email')}")
        return profile.get("_id")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return None


def test_get_profile(email):
    """Test: Get user profile"""
    print_section("GET USER PROFILE")
    
    response = requests.get(f"{BASE_URL}/profiles/{email}")
    
    if response.status_code == 200:
        profile = response.json()
        print("✅ Profile retrieved successfully!")
        print(json.dumps(profile, indent=2, default=str))
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_generate_daily_timetable(user_id):
    """Test: Generate daily timetable"""
    print_section("GENERATE DAILY TIMETABLE")
    
    payload = {
        "user_id": user_id,
        "timetable_type": "daily",
        "start_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    response = requests.post(f"{BASE_URL}/timetables/generate", json=payload)
    
    if response.status_code == 201:
        timetable = response.json()
        print("✅ Daily timetable generated successfully!")
        print(f"Timetable ID: {timetable.get('_id')}")
        print(f"Type: {timetable.get('type')}")
        print(f"Date: {timetable.get('date')}")
        
        # Print blocks
        print("\nSchedule:")
        blocks = timetable.get("timetable", {}).get("blocks", [])
        for block in blocks:
            activity = block.get("type").upper()
            subject = f" ({block.get('subject')})" if block.get("subject") else ""
            print(f"  {block.get('start')} - {block.get('end')}: {activity}{subject}")
        
        return timetable.get("_id")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return None


def test_generate_weekly_timetable(user_id):
    """Test: Generate weekly timetable"""
    print_section("GENERATE WEEKLY TIMETABLE")
    
    payload = {
        "user_id": user_id,
        "timetable_type": "weekly",
        "start_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    response = requests.post(f"{BASE_URL}/timetables/generate", json=payload)
    
    if response.status_code == 201:
        timetable = response.json()
        print("✅ Weekly timetable generated successfully!")
        print(f"Timetable ID: {timetable.get('_id')}")
        print(f"Week: {timetable.get('timetable', {}).get('week_start')} to {timetable.get('timetable', {}).get('week_end')}")
        
        # Print summary
        summary = timetable.get("timetable", {}).get("summary", {})
        print(f"\nWeekly Summary:")
        print(f"  Total Study Hours: {summary.get('total_study_hours')}")
        print(f"  Total Work Hours: {summary.get('total_work_hours')}")
        print(f"  Subject Distribution:")
        for subject, hours in summary.get("subject_distribution", {}).items():
            print(f"    - {subject}: {hours} hours")
        
        return timetable.get("_id")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return None


def test_get_timetable(timetable_id):
    """Test: Get timetable by ID"""
    print_section("GET TIMETABLE")
    
    response = requests.get(f"{BASE_URL}/timetables/{timetable_id}")
    
    if response.status_code == 200:
        timetable = response.json()
        print("✅ Timetable retrieved successfully!")
        print(f"ID: {timetable.get('_id')}")
        print(f"Type: {timetable.get('type')}")
        print(f"Created: {timetable.get('created_at')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_regenerate_timetable(timetable_id, optimization):
    """Test: Regenerate timetable with optimization"""
    print_section(f"REGENERATE TIMETABLE - {optimization.upper()}")
    
    payload = {"optimization": optimization}
    response = requests.post(f"{BASE_URL}/timetables/{timetable_id}/regenerate", json=payload)
    
    if response.status_code == 200:
        timetable = response.json()
        print(f"✅ Timetable regenerated with '{optimization}' optimization!")
        modifications = timetable.get("modifications", [])
        print(f"Total modifications: {len(modifications)}")
        if modifications:
            print(f"Latest: {modifications[-1].get('type')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_export_timetable(timetable_id):
    """Test: Export timetable"""
    print_section("EXPORT TIMETABLE")
    
    # JSON export
    response = requests.get(f"{BASE_URL}/export/{timetable_id}/json")
    if response.status_code == 200:
        print("✅ JSON export available")
    
    # CSV export
    response = requests.get(f"{BASE_URL}/export/{timetable_id}/csv")
    if response.status_code == 200:
        print("✅ CSV export available")
    
    # Share link
    response = requests.get(f"{BASE_URL}/export/{timetable_id}/share")
    if response.status_code == 200:
        share_data = response.json()
        print("✅ Share link generated")
        print(f"URL: {share_data.get('shareUrl')}")


def test_get_user_timetables(user_id):
    """Test: Get all user timetables"""
    print_section("GET ALL USER TIMETABLES")
    
    response = requests.get(f"{BASE_URL}/timetables/user/{user_id}")
    
    if response.status_code == 200:
        timetables = response.json()
        print(f"✅ Found {len(timetables)} timetable(s)")
        for tt in timetables:
            print(f"  - {tt.get('type')}: {tt.get('date')} (ID: {tt.get('_id')})")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  AI TIMETABLE GENERATOR - API TEST SUITE")
    print("="*60)
    print("Ensure the backend is running before starting tests!")
    print("Run: python run.py")
    
    try:
        # Test 1: Create profile
        user_id = test_create_profile()
        if not user_id:
            print("\n❌ Failed to create profile. Exiting.")
            return
        
        # Test 2: Get profile
        test_get_profile(TEST_USER["email"])
        
        # Test 3: Generate daily timetable
        daily_id = test_generate_daily_timetable(user_id)
        
        # Test 4: Generate weekly timetable
        weekly_id = test_generate_weekly_timetable(user_id)
        
        # Test 5: Get timetable
        if daily_id:
            test_get_timetable(daily_id)
        
        # Test 6: Regenerate with optimizations
        if daily_id:
            test_regenerate_timetable(daily_id, "reduce_stress")
            test_regenerate_timetable(daily_id, "more_focus")
        
        # Test 7: Export
        if daily_id:
            test_export_timetable(daily_id)
        
        # Test 8: Get all user timetables
        test_get_user_timetables(user_id)
        
        print("\n" + "="*60)
        print("  ✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to backend at http://localhost:8000")
        print("Make sure the backend is running: python run.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
