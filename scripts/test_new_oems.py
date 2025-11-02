#!/usr/bin/env python3
"""
Quick test of 4 new OEM scrapers.
Tests Schneider Electric, Honeywell Home, Sensi, and Johnson Controls.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

def test_new_oems():
    """Test all 4 new OEM scrapers with San Francisco ZIP."""

    print("\n" + "="*80)
    print("TESTING 4 NEW OEM SCRAPERS")
    print("="*80 + "\n")

    # Test ZIP: San Francisco
    test_zip = "94102"

    # New OEMs to test
    new_oems = [
        "Schneider Electric",
        "Honeywell Home",
        "Sensi",
        "Johnson Controls"
    ]

    results = {}

    for oem in new_oems:
        print(f"\n{'='*80}")
        print(f"Testing {oem}")
        print('='*80)

        try:
            scraper = ScraperFactory.create(oem, mode=ScraperMode.PLAYWRIGHT)
            dealers = scraper.scrape_zip_code(test_zip)

            results[oem] = {
                'success': True,
                'count': len(dealers),
                'dealers': dealers
            }

            print(f"\n✅ {oem}: {len(dealers)} dealers extracted")

            if len(dealers) > 0:
                # Show first dealer
                d = dealers[0]
                print(f"\nSample dealer:")
                print(f"  Name: {d.name}")
                print(f"  Phone: {d.phone if d.phone else '(none)'}")
                print(f"  Location: {d.city}, {d.state} {d.zip}")
                if d.website:
                    print(f"  Website: {d.website}")
                if d.certifications:
                    print(f"  Certifications: {', '.join(d.certifications[:3])}")

                # Show capability flags
                print(f"\nCapabilities:")
                print(f"  HVAC: {d.capabilities.has_hvac}")
                print(f"  Electrical: {d.capabilities.has_electrical}")
                print(f"  Commercial: {d.capabilities.is_commercial}")
                print(f"  Residential: {d.capabilities.is_residential}")
            else:
                print(f"\n⚠️  No dealers found - check if extraction is working")

        except Exception as e:
            results[oem] = {
                'success': False,
                'error': str(e)
            }
            print(f"\n❌ {oem} FAILED: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = [oem for oem, res in results.items() if res['success']]
    failed = [oem for oem, res in results.items() if not res['success']]

    print(f"\nSuccessful: {len(successful)}/4 OEMs")
    for oem in successful:
        count = results[oem]['count']
        print(f"  ✅ {oem}: {count} dealers")

    if failed:
        print(f"\nFailed: {len(failed)}/4 OEMs")
        for oem in failed:
            print(f"  ❌ {oem}: {results[oem]['error']}")

    # Total dealers extracted
    total_dealers = sum(res['count'] for res in results.values() if res['success'])
    print(f"\nTotal dealers extracted: {total_dealers}")

    if len(successful) == 4:
        print("\n✅ ALL 4 NEW OEM SCRAPERS WORKING!")
    else:
        print(f"\n⚠️  {len(failed)} scraper(s) need attention")

    print("="*80 + "\n")


if __name__ == "__main__":
    test_new_oems()
