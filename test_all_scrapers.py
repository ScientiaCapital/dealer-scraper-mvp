#!/usr/bin/env python3
"""
Test all 4 OEM scrapers (Generac, Tesla, Enphase, SolarEdge)

Tests can run in different modes:
- BROWSERBASE: Automated cloud browser (requires BROWSERBASE_API_KEY)
- RUNPOD: Automated RunPod serverless (requires RUNPOD_API_KEY)
- PLAYWRIGHT: Manual MCP workflow (requires user to execute browser commands)

Usage:
    python test_all_scrapers.py --mode browserbase --oem tesla
    python test_all_scrapers.py --mode runpod --oem all
"""

import argparse
import json
import os

# Load environment variables BEFORE importing scrapers
from dotenv import load_dotenv
load_dotenv()

# Now import scrapers (they will have access to env vars)
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Import all scrapers to trigger self-registration
import scrapers.generac_scraper
import scrapers.tesla_scraper
import scrapers.enphase_scraper
import scrapers.solaredge_scraper

# Test ZIPs for each OEM
TEST_ZIPS = {
    "generac": "53202",   # Milwaukee (validated: 59 dealers)
    "tesla": "94102",     # San Francisco (validated: 18 Premier installers)
    "enphase": "94102",   # San Francisco
    "solaredge": "94102"  # San Francisco
}

def test_scraper(oem_name: str, mode: ScraperMode, zip_code: str = None):
    """Test a single OEM scraper"""

    print(f"\n{'='*70}")
    print(f"Testing {oem_name.upper()} Scraper - {mode.name} Mode")
    print(f"{'='*70}\n")

    # Get test ZIP
    if not zip_code:
        zip_code = TEST_ZIPS.get(oem_name.lower(), "94102")

    print(f"ZIP Code: {zip_code}")

    try:
        # Create scraper
        scraper = ScraperFactory.create(oem_name, mode=mode)

        # Scrape
        print(f"\n[Test] Scraping {oem_name} dealers in ZIP {zip_code}...")
        dealers = scraper.scrape_zip_code(zip_code)

        # Display results
        print(f"\n{'='*70}")
        print(f"✅ SUCCESS: {len(dealers)} dealers found")
        print(f"{'='*70}\n")

        if dealers:
            # Show first 3 dealers
            for i, dealer in enumerate(dealers[:3], 1):
                print(f"{i}. {dealer.name}")
                print(f"   Phone: {dealer.phone}")
                print(f"   Domain: {dealer.domain}")
                print(f"   Tier: {dealer.tier}")
                print(f"   Certifications: {', '.join(dealer.certifications)}")
                if dealer.has_om_capability:
                    print(f"   🎯 O&M Capability: YES")
                if dealer.is_mep_r_contractor:
                    print(f"   🎯 MEP+R Self-Performer: YES")
                print()

            if len(dealers) > 3:
                print(f"   ... and {len(dealers) - 3} more dealers\n")

            # Save results
            output_file = f"output/test_{oem_name.lower()}_{mode.name.lower()}.json"
            scraper.save_json(output_file)
            print(f"💾 Saved results to {output_file}")
        else:
            print("⚠️  No dealers found - check extraction script or DOM selectors")

        return dealers

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description='Test OEM scrapers')
    parser.add_argument('--mode',
                       choices=['browserbase', 'runpod', 'playwright'],
                       default='browserbase',
                       help='Scraping mode (default: browserbase)')
    parser.add_argument('--oem',
                       choices=['all', 'generac', 'tesla', 'enphase', 'solaredge'],
                       default='all',
                       help='Which OEM to test (default: all)')
    parser.add_argument('--zip',
                       help='Override default test ZIP code')

    args = parser.parse_args()

    # Convert mode string to enum
    mode_map = {
        'browserbase': ScraperMode.BROWSERBASE,
        'runpod': ScraperMode.RUNPOD,
        'playwright': ScraperMode.PLAYWRIGHT
    }
    mode = mode_map[args.mode]

    # Determine which OEMs to test
    if args.oem == 'all':
        oems = ['generac', 'tesla', 'enphase', 'solaredge']
    else:
        oems = [args.oem]

    # Test each OEM
    results = {}
    for oem in oems:
        dealers = test_scraper(oem, mode, args.zip)
        results[oem] = len(dealers) if dealers else 0

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    total = 0
    for oem, count in results.items():
        status = "✅" if count > 0 else "❌"
        print(f"{status} {oem.upper()}: {count} dealers")
        total += count

    print(f"\n📊 Total: {total} dealers across {len(results)} OEMs")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
