#!/usr/bin/env python3
"""
Quick test of RunPod endpoint with correct workflow format.

Tests the endpoint with a simple workflow to verify handler is working.
"""

import os
import requests
from dotenv import load_dotenv

# Load credentials
load_dotenv()

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")

def test_endpoint():
    """Test RunPod endpoint with correct workflow format"""

    print("=" * 70)
    print("RUNPOD WORKFLOW TEST")
    print("=" * 70)
    print()

    # Check credentials
    if not RUNPOD_API_KEY:
        print("❌ RUNPOD_API_KEY not found in .env")
        return False

    if not RUNPOD_ENDPOINT_ID:
        print("❌ RUNPOD_ENDPOINT_ID not found in .env")
        return False

    print(f"✅ API Key: {RUNPOD_API_KEY[:20]}...")
    print(f"✅ Endpoint ID: {RUNPOD_ENDPOINT_ID}")
    print()

    # Build API URL
    api_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"

    print(f"📡 Testing endpoint: {api_url}")
    print()

    # Correct payload format - simple workflow
    payload = {
        "input": {
            "workflow": [
                {"action": "navigate", "url": "https://www.google.com"},
                {"action": "evaluate", "script": "() => document.title"}
            ],
            "options": {}
        }
    }

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        print("🚀 Sending workflow request (navigate to Google, get title)...")
        print()

        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=120
        )

        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            result = response.json()
            print("✅ Response received!")
            print()
            print("Full response:")
            import json
            print(json.dumps(result, indent=2))
            print()

            # Check result
            if "output" in result or "result" in result:
                print("=" * 70)
                print("✅ RUNPOD WORKFLOW TEST PASSED!")
                print("=" * 70)
                return True
            else:
                print("⚠️  Unexpected response format")
                return False

        else:
            print(f"❌ HTTP Error {response.status_code}")
            print()
            print("Response:", response.text[:500])
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timed out (endpoint may be initializing)")
        print("   Try again in 30 seconds")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_endpoint()
    exit(0 if success else 1)
