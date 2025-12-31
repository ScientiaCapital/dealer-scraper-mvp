#!/usr/bin/env python3
"""
Test script for debugging Kohler scraper with ZIP 53044
"""
import sys
sys.path.insert(0, '/Users/tmk/tmp/worktrees/dealer-scraper-mvp/feature-sprint-dec27')

from scrapers.kohler_scraper import KohlerScraper
from scrapers.base_scraper import ScraperMode

def test_kohler_53044():
    """Test Kohler scraper with Wisconsin ZIP 53044"""
    print("\n" + "="*70)
    print("Testing Kohler Scraper - ZIP 53044 (Wisconsin)")
    print("Expected: ~9 dealers including JRB ELECTRIC INC")
    print("="*70 + "\n")

    # Use PATCHRIGHT mode (stealth browser)
    scraper = KohlerScraper(mode=ScraperMode.PATCHRIGHT)

    # Test with ZIP 53044
    dealers = scraper.scrape_zip_code("53044")

    print("\n" + "="*70)
    print(f"RESULTS: Found {len(dealers)} dealers")
    print("="*70)

    if dealers:
        for i, dealer in enumerate(dealers, 1):
            print(f"\n{i}. {dealer.name}")
            print(f"   Tier: {dealer.tier}")
            print(f"   Phone: {dealer.phone}")
            print(f"   Address: {dealer.address_full}")
            print(f"   Distance: {dealer.distance}")
            if dealer.website:
                print(f"   Website: {dealer.website}")
    else:
        print("\n❌ NO DEALERS FOUND - Check debug files:")
        print("   - /tmp/kohler_debug_53044.png")
        print("   - /tmp/kohler_debug_53044.html")

if __name__ == "__main__":
    test_kohler_53044()
