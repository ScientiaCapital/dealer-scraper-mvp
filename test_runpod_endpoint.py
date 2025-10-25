#!/usr/bin/env python3
"""
Quick test of RunPod endpoint connectivity.

Tests the endpoint with a simple Generac scrape to verify it's working.
"""

import os
import requests
from dotenv import load_dotenv

# Load credentials
load_dotenv()

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")

def test_endpoint():
    """Test RunPod endpoint with a simple request"""

    print("=" * 70)
    print("RUNPOD ENDPOINT TEST")
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

    # Simple test payload (Generac scraper for Milwaukee)
    payload = {
        "input": {
            "oem": "generac",
            "zip_code": "53202",
            "mode": "runpod"
        }
    }

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        print("🚀 Sending test request (Generac scraper, ZIP 53202)...")
        print()

        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=120  # 2 minute timeout
        )

        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            result = response.json()

            # Check for RunPod's response structure
            if "status" in result:
                print(f"✅ Endpoint Status: {result['status']}")

                if result["status"] == "COMPLETED":
                    output = result.get("output", {})
                    dealers = output.get("dealers", [])

                    print(f"✅ Found {len(dealers)} dealers!")
                    print()

                    if dealers:
                        print("Sample dealer:")
                        print(f"  Name: {dealers[0].get('name', 'N/A')}")
                        print(f"  Phone: {dealers[0].get('phone', 'N/A')}")
                        print(f"  Tier: {dealers[0].get('tier', 'N/A')}")

                    print()
                    print("=" * 70)
                    print("✅ RUNPOD ENDPOINT TEST PASSED!")
                    print("=" * 70)
                    return True

                elif result["status"] == "IN_PROGRESS":
                    print("⏳ Job still in progress (this shouldn't happen with /runsync)")

                elif result["status"] == "FAILED":
                    error = result.get("error", "Unknown error")
                    print(f"❌ Job failed: {error}")

            else:
                # Might be direct handler output
                print("Response:", result)
                print()
                print("⚠️  Unexpected response format")

        else:
            print(f"❌ HTTP Error {response.status_code}")
            print()
            print("Response:", response.text[:500])

    except requests.exceptions.Timeout:
        print("❌ Request timed out (endpoint may be cold-starting)")
        print("   Try again in 30 seconds")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print()
    print("=" * 70)
    print("❌ RUNPOD ENDPOINT TEST FAILED")
    print("=" * 70)
    return False

if __name__ == "__main__":
    test_endpoint()
