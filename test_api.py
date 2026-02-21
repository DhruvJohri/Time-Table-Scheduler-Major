"""
test_api.py - Test script for AI Timetable Generator API

This script demonstrates how to interact with the college timetable generation API.
Run the backend first with: python -m uvicorn app.main:app --reload --port 8000
Then run this script: python test_api.py
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/timetable"


def print_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_health():
    """Test: Health check"""
    print_section("HEALTH CHECK")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://localhost:8000")
        return False


def test_generate_schedule():
    """Test: Generate timetable"""
    print_section("GENERATE TIMETABLE")
    
    payload = {
        "seed": 42,  # Deterministic generation
        "force_regenerate": True,
        "include_clubs": True
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    print("\nGenerating schedule (this may take a moment)...\n")
    
    try:
        response = requests.post(f"{BASE_URL}/generate", json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Schedule generated successfully!")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return False
    except requests.Timeout:
        print("❌ Request timed out. Generation may be taking long.")
        return False
    except ConnectionError:
        print("❌ Could not connect to server.")
        return False


def test_get_full_timetable():
    """Test: Get full timetable"""
    print_section("GET FULL TIMETABLE")
    
    try:
        response = requests.get(BASE_URL, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Timetable retrieved successfully!")
            print(f"Total entries: {result.get('total_entries', 0)}")
            print(f"Generated at: {result.get('generated_at', 'N/A')}")
            
            days = result.get('days', {})
            print(f"\nDays with entries: {', '.join(days.keys())}")
            
            # Show sample from first day
            first_day = next(iter(days.values())) if days else []
            if first_day:
                print(f"\nSample entries from first day ({len(first_day)} total):")
                for i, entry in enumerate(first_day[:3]):
                    print(f"  {i+1}. P{entry['period']} - {entry['subject']} ({entry['type']})")
                if len(first_day) > 3:
                    print(f"  ... and {len(first_day) - 3} more")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_get_branch_timetable():
    """Test: Get branch-specific timetable"""
    print_section("GET BRANCH TIMETABLE (CSE Year 3 Section A)")
    
    branch = "CSE"
    year = 3
    section = "A"
    
    try:
        response = requests.get(f"{BASE_URL}/{branch}/{year}/{section}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Branch timetable retrieved successfully!")
            print(f"Branch: {result['branch']}")
            print(f"Year: {result['year']}")
            print(f"Section: {result['section']}")
            print(f"Total entries: {result['total']}")
            
            entries = result.get('entries', [])
            if entries:
                # Group by day
                by_day = {}
                for entry in entries:
                    day = entry['day']
                    if day not in by_day:
                        by_day[day] = []
                    by_day[day].append(entry)
                
                print(f"\nSchedule:")
                for day in sorted(by_day.keys()):
                    print(f"\n  {day}:")
                    for entry in sorted(by_day[day], key=lambda x: x['period']):
                        print(f"    P{entry['period']}: {entry['subject']} - {entry['faculty']} ({entry['type']})")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            if response.status_code == 404:
                print("   Timetable not found. Generate one first.")
            else:
                print(response.json())
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_validate_schedule():
    """Test: Validate schedule"""
    print_section("VALIDATE SCHEDULE")
    
    try:
        response = requests.post(f"{BASE_URL}/validate", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Schedule validation completed!")
            print(f"Is valid: {result['is_valid']}")
            print(f"Total conflicts: {result['total_conflicts']}")
            print(f"Allocation percentage: {result['allocation_percentage']:.1f}%")
            
            if result['unallocated_subjects']:
                print(f"\nUnallocated subjects ({len(result['unallocated_subjects'])}):")
                for subject in result['unallocated_subjects'][:5]:
                    print(f"  - {subject}")
                if len(result['unallocated_subjects']) > 5:
                    print(f"  ... and {len(result['unallocated_subjects']) - 5} more")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_get_statistics():
    """Test: Get schedule statistics"""
    print_section("GET SCHEDULE STATISTICS")
    
    try:
        response = requests.get(f"{BASE_URL}/statistics", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Statistics retrieved!")
            
            print(f"\nResources:")
            print(f"  Total subjects: {stats['total_subjects']}")
            print(f"  Total branches: {stats['total_branches']}")
            print(f"  Total faculty: {stats['total_faculty']}")
            print(f"  Total classrooms: {stats['total_classrooms']}")
            print(f"  Total lab rooms: {stats['total_labrooms']}")
            
            print(f"\nScheduled entries:")
            print(f"  Lectures: {stats['lectures_scheduled']}")
            print(f"  Tutorials: {stats['tutorials_scheduled']}")
            print(f"  Labs: {stats['labs_scheduled']}")
            print(f"  Seminars: {stats['seminars_scheduled']}")
            print(f"  Club activities: {stats['clubs_scheduled']}")
            
            print(f"\nUtilization:")
            print(f"  Faculty: {stats['faculty_utilization']:.1f}%")
            print(f"  Classrooms: {stats['classroom_utilization']:.1f}%")
            print(f"  Lab rooms: {stats['labroom_utilization']:.1f}%")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  AI TIMETABLE GENERATOR - API TEST SUITE")
    print("="*70)
    print(f"\nTest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend URL: {BASE_URL}")
    
    # Check if server is running
    if not test_health():
        print("\n" + "!"*70)
        print("  Cannot proceed without server. Please start the backend:")
        print("  python -m uvicorn app.main:app --reload --port 8000")
        print("!"*70)
        return
    
    tests = [
        ("Generate Schedule", test_generate_schedule),
        ("Get Full Timetable", test_get_full_timetable),
        ("Get Branch Timetable", test_get_branch_timetable),
        ("Validate Schedule", test_validate_schedule),
        ("Get Statistics", test_get_statistics),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"❌ Error running test: {str(e)}")
            results[name] = False
        time.sleep(0.5)
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
