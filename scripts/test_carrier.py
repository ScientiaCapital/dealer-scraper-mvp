#!/usr/bin/env python3
"""
Quick test of Carrier scraper with California ZIP

Expected: ~47 dealers for ZIP 94102 (San Francisco) with "All Dealers" filter
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
    print("TESTING CARRIER WITH CA ZIP 94102 (San Francisco)")
    print("=" * 80)

    # Create scraper
    scraper = ScraperFactory.create("Carrier", mode=ScraperMode.PLAYWRIGHT)

    # Test single ZIP
    test_zip = "94102"
    print(f"\nTesting ZIP: {test_zip}")

    dealers = scraper.scrape_zip_code(test_zip)

    print(f"\n{'=' * 80}")
    print(f"RESULTS: Found {len(dealers)} Carrier dealers")
    print(f"{'=' * 80}\n")

    if dealers:
        print("✓ Success! First 5 dealers:")
        for i, dealer in enumerate(dealers[:5], 1):
            print(f"\n{i}. {dealer.name}")
            print(f"   Phone: {dealer.phone}")
            print(f"   Location: {dealer.city}, {dealer.state}")
            if dealer.website:
                print(f"   Website: {dealer.website}")
            if dealer.tier:
                print(f"   Tier/Certs: {dealer.tier}")
            if dealer.rating > 0:
                print(f"   Rating: {dealer.rating}★ ({dealer.review_count} reviews)")

        print(f"\n📊 Summary:")
        print(f"   Total dealers: {len(dealers)}")
        dealers_with_websites = sum(1 for d in dealers if d.website)
        print(f"   With websites: {dealers_with_websites}")
        dealers_with_ratings = sum(1 for d in dealers if d.rating > 0)
        print(f"   With ratings: {dealers_with_ratings}")
        dealers_with_certs = sum(1 for d in dealers if d.certifications)
        print(f"   With certifications: {dealers_with_certs}")
    else:
        print("❌ No dealers found - may need debugging")


if __name__ == "__main__":
    main()
