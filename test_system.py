"""
Quick system test script
Tests if all components are working
"""
import requests
import time

print("=" * 60)
print("Testing Pizza Violation Detection System")
print("=" * 60)

# Test 1: Streaming Service
print("\n1. Testing Streaming Service...")
try:
    response = requests.get("http://localhost:8000/api/status", timeout=5)
    if response.status_code == 200:
        print("   OK - Streaming Service is running")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Violations: {data.get('total_violations', 0)}")
    else:
        print(f"   ERROR - Status code: {response.status_code}")
except Exception as e:
    print(f"   ERROR - Cannot connect: {e}")
    print("   Make sure Streaming Service is running!")

# Test 2: Frontend
print("\n2. Testing Frontend...")
try:
    response = requests.get("http://localhost:3000", timeout=5)
    if response.status_code == 200:
        print("   OK - Frontend is accessible")
    else:
        print(f"   ERROR - Status code: {response.status_code}")
except Exception as e:
    print(f"   ERROR - Cannot connect: {e}")
    print("   Make sure Frontend server is running!")

# Test 3: Latest frame
print("\n3. Testing for latest frame...")
try:
    response = requests.get("http://localhost:8000/api/latest-frame", timeout=5)
    if response.status_code == 200:
        print("   OK - Frames are being processed!")
        data = response.json()
        print(f"   Frame number: {data.get('frame_number')}")
    elif response.status_code == 404:
        print("   WAITING - No frame available yet")
        print("   This is normal if the system just started")
        print("   Wait 30-60 seconds and try again")
    else:
        print(f"   ERROR - Status code: {response.status_code}")
except Exception as e:
    print(f"   ERROR - Cannot connect: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
print("\nIf all tests passed, open: http://localhost:3000")
print("Wait 30-60 seconds for the video to appear")
print("\nPress Ctrl+C to exit")




