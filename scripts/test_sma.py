#!/usr/bin/env python3
"""
Quick test of SMA scraper with California ZIP
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

def main():
    print("=" * 80)
    print("TESTING SMA WITH CA ZIP 94102 (San Francisco)")
    print("=" * 80)

    # Create scraper
    scraper = ScraperFactory.create("SMA", mode=ScraperMode.PLAYWRIGHT)

    # Test single ZIP
    test_zip = "94102"
    print(f"\nTesting ZIP: {test_zip}")

    dealers = scraper.scrape_zip_code(test_zip)

    print(f"\n{'=' * 80}")
    print(f"RESULTS: Found {len(dealers)} SMA POWERUP+ installers")
    print(f"{'=' * 80}\n")

    if dealers:
        print("✓ Success! First 3 installers:")
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"\n{i}. {dealer.name}")
            print(f"   Phone: {dealer.phone}")
            print(f"   City: {dealer.city}, {dealer.state}")
            if dealer.website:
                print(f"   Website: {dealer.website}")
            print(f"   Distance: {dealer.distance}")
    else:
        print("❌ No installers found - may need debugging")

if __name__ == "__main__":
    main()
