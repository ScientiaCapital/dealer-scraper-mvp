#!/usr/bin/env python3
"""
Quick test of Mitsubishi scraper with California ZIP
"""

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

def main():
    print("=" * 80)
    print("TESTING MITSUBISHI WITH CA ZIP 94102 (San Francisco)")
    print("=" * 80)
    
    # Create scraper
    scraper = ScraperFactory.create("Mitsubishi", mode=ScraperMode.PLAYWRIGHT)
    
    # Test single ZIP
    test_zip = "94102"
    print(f"\nTesting ZIP: {test_zip}")
    
    dealers = scraper.scrape_zip(test_zip)
    
    print(f"\n{'=' * 80}")
    print(f"RESULTS: Found {len(dealers)} Diamond Commercial contractors")
    print(f"{'=' * 80}\n")
    
    if dealers:
        print("✓ Success! First 3 contractors:")
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"\n{i}. {dealer.name}")
            print(f"   Phone: {dealer.phone}")
            print(f"   City: {dealer.city}, {dealer.state}")
            print(f"   Tier: {dealer.tier}")
    else:
        print("❌ No contractors found - may need debugging")

if __name__ == "__main__":
    main()
