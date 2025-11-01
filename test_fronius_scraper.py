"""
Test script for Fronius scraper
Tests end-to-end extraction for Fronius certified installers
"""

import sys
from scrapers.fronius_scraper import FroniusScraper
from scrapers.base_scraper import ScraperMode

def test_fronius_scraper():
    print("="*60)
    print("Testing Fronius Scraper")
    print("="*60)
    print()

    # Create scraper in PLAYWRIGHT mode
    scraper = FroniusScraper(mode=ScraperMode.PLAYWRIGHT)

    # Test with San Francisco ZIP code
    test_zip = "94102"
    print(f"Testing with ZIP code: {test_zip}")
    print()

    try:
        # Scrape dealers
        dealers = scraper.scrape_zip_code(test_zip)

        print()
        print("="*60)
        print(f"✅ SUCCESS: Extracted {len(dealers)} dealers from ZIP {test_zip}")
        print("="*60)
        print()

        # Show first 3 dealers
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"Dealer {i}:")
            print(f"  Name: {dealer.name}")
            print(f"  Phone: {dealer.phone}")
            print(f"  Address: {dealer.address_full}")
            print(f"  Tier: {dealer.tier}")
            print(f"  Distance: {dealer.distance}")
            print()

        if len(dealers) > 3:
            print(f"... and {len(dealers) - 3} more dealers")
            print()

        return True

    except Exception as e:
        print()
        print("="*60)
        print(f"❌ ERROR: {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fronius_scraper()
    sys.exit(0 if success else 1)
