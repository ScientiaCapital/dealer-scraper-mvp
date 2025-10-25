#!/usr/bin/env python3
"""
Test script for Tesla Powerwall installer scraper.

This script tests the Tesla scraper using Browserbase mode (cloud browser).
It will scrape Tesla Premier installers from a test ZIP code and display results.

Usage:
    python scripts/test_tesla.py
"""

import sys
import os
import json
from datetime import datetime
from typing import List

# Add parent directory to path so we can import scrapers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.tesla_scraper import TeslaScraper
from scrapers.base_scraper import ScraperMode, StandardizedDealer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_tesla_scraper(zip_code: str = "94102", mode: ScraperMode = ScraperMode.BROWSERBASE):
    """
    Test Tesla scraper on a single ZIP code.

    Args:
        zip_code: ZIP code to test (default: 94102 - San Francisco)
        mode: Scraper mode to use (default: BROWSERBASE for cloud browser)
    """
    print(f"\n{'='*70}")
    print(f"TESLA POWERWALL INSTALLER SCRAPER TEST")
    print(f"{'='*70}")
    print(f"Mode: {mode.value}")
    print(f"ZIP Code: {zip_code}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    try:
        # Initialize scraper
        print(f"[1/4] Initializing Tesla scraper in {mode.value} mode...")
        scraper = TeslaScraper(mode=mode)

        # Scrape ZIP code
        print(f"[2/4] Scraping installers for ZIP {zip_code}...")
        print(f"      This may take 10-20 seconds as we navigate the Tesla site...\n")

        dealers = scraper.scrape_zip_code(zip_code)

        # Display results
        print(f"\n[3/4] Results Summary:")
        print(f"      Found {len(dealers)} Tesla Premier installers")

        if dealers:
            print(f"\n{'='*70}")
            print(f"INSTALLER DETAILS")
            print(f"{'='*70}")

            for i, dealer in enumerate(dealers, 1):
                print(f"\n{i}. {dealer.name}")
                print(f"   {'─'*60}")
                print(f"   Phone: {dealer.phone}")
                print(f"   Website: {dealer.website}")
                print(f"   Domain: {dealer.domain}")
                print(f"   Tier: {dealer.tier}")
                print(f"   Certifications: {', '.join(dealer.certifications)}")

                # Display capabilities (what they can install)
                caps = dealer.capabilities
                capabilities = []
                if caps.has_battery: capabilities.append("Battery")
                if caps.has_solar: capabilities.append("Solar")
                if caps.has_electrical: capabilities.append("Electrical")
                if caps.has_roofing: capabilities.append("Roofing")

                if capabilities:
                    print(f"   Capabilities: {', '.join(capabilities)}")

                # Check for generator keywords (our target!)
                name_lower = dealer.name.lower()
                if any(kw in name_lower for kw in ["generator", "power", "backup", "electric"]):
                    print(f"   🎯 POTENTIAL GENERATOR DEALER (keyword match)")

            # Save results to JSON
            print(f"\n[4/4] Saving results...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)

            output_file = f"{output_dir}/tesla_test_{zip_code}_{timestamp}.json"

            # Convert dealers to dictionaries for JSON
            dealer_dicts = [d.to_dict() for d in dealers]

            with open(output_file, 'w') as f:
                json.dump({
                    "scraper": "Tesla",
                    "mode": mode.value,
                    "zip_code": zip_code,
                    "timestamp": timestamp,
                    "total_dealers": len(dealers),
                    "dealers": dealer_dicts
                }, f, indent=2)

            print(f"      Results saved to: {output_file}")

            # Analysis for generator overlap potential
            print(f"\n{'='*70}")
            print(f"GENERATOR OVERLAP ANALYSIS")
            print(f"{'='*70}")

            # Count dealers with generator-related keywords
            generator_keywords = ["generator", "power", "backup", "electric", "energy", "solar"]
            potential_generator_dealers = [
                d for d in dealers
                if any(kw in d.name.lower() for kw in generator_keywords)
            ]

            print(f"Total Tesla installers: {len(dealers)}")
            print(f"Potential generator overlap: {len(potential_generator_dealers)} dealers")

            if potential_generator_dealers:
                print(f"\nDealers with generator/power keywords:")
                for d in potential_generator_dealers[:5]:  # Show first 5
                    print(f"  • {d.name}")
                    if d.website:
                        print(f"    Website: {d.website}")

            print(f"\n💡 These dealers are prime targets for Coperniq!")
            print(f"   They likely manage both Tesla Powerwall AND generator installs,")
            print(f"   meaning they're juggling multiple monitoring platforms.")

        else:
            print(f"\n⚠️  No installers found for ZIP {zip_code}")
            print(f"   This might mean:")
            print(f"   1. No Premier installers in this area")
            print(f"   2. The page structure has changed")
            print(f"   3. Bot detection blocked the request")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\nTroubleshooting tips:")
        print(f"1. Check that BROWSERBASE_API_KEY is set in .env")
        print(f"2. Check that BROWSERBASE_PROJECT_ID is set in .env")
        print(f"3. Try a different ZIP code")
        print(f"4. Try PATCHRIGHT mode if Browserbase is detected as bot")

        # Try to give more specific guidance based on error
        if "BROWSERBASE_API_KEY" in str(e) or "BROWSERBASE_PROJECT_ID" in str(e):
            print(f"\n📋 To fix: Add these to your .env file:")
            print(f"   BROWSERBASE_API_KEY=your_key_here")
            print(f"   BROWSERBASE_PROJECT_ID=your_project_id_here")
        elif "playwright" in str(e).lower():
            print(f"\n📋 To fix: Install Playwright:")
            print(f"   pip install playwright")
            print(f"   playwright install chromium")

    print(f"\n{'='*70}")
    print(f"TEST COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Test with San Francisco ZIP (high Tesla penetration)
    # Using BROWSERBASE mode with corrected API URL
    test_tesla_scraper(zip_code="94102", mode=ScraperMode.BROWSERBASE)

    # Optionally test with another ZIP
    # test_tesla_scraper(zip_code="77019", mode=ScraperMode.BROWSERBASE)  # Houston