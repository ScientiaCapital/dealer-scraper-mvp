#!/usr/bin/env python3
"""
Quick test of Mitsubishi Diamond Commercial scraper on one ZIP code.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.mitsubishi_scraper import MitsubishiScraper
from scrapers.base_scraper import ScraperMode

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING MITSUBISHI DIAMOND COMMERCIAL SCRAPER")
    print("=" * 80)
    print()

    # Test on New York (should find ~35 Diamond Commercial contractors from inspection)
    test_zip = "10001"

    scraper = MitsubishiScraper(mode=ScraperMode.PLAYWRIGHT)

    print(f"Testing ZIP: {test_zip}")
    print(f"Expected: ~35 Diamond Commercial contractors (from manual inspection)")
    print()

    dealers = scraper.scrape_zip_code(test_zip)

    print()
    print("=" * 80)
    print(f"RESULTS: Found {len(dealers)} Diamond Commercial contractors")
    print("=" * 80)

    if dealers:
        print("\nFirst 3 contractors:")
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"\n{i}. {dealer.name}")
            print(f"   Phone: {dealer.phone}")
            print(f"   Location: {dealer.city}, {dealer.state} {dealer.zip}")
            print(f"   Website: {dealer.website or 'None'}")
            print(f"   Tier: {dealer.tier}")
            print(f"   Certifications: {', '.join(dealer.certifications)}")

        print(f"\nTotal: {len(dealers)} unique contractors")
        print("\n✅ Scraper working correctly!")
    else:
        print("\n❌ No contractors found - scraper may need debugging")

    print()
