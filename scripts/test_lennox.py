"""
Quick test of Lennox HVAC scraper.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.lennox_scraper import LennoxScraper
from scrapers.base_scraper import ScraperMode

def test_lennox():
    """Test Lennox scraper on single ZIP."""

    print("\n" + "="*80)
    print("TESTING LENNOX HVAC SCRAPER")
    print("="*80 + "\n")

    scraper = LennoxScraper(mode=ScraperMode.PLAYWRIGHT)

    # Test ZIP (San Francisco)
    test_zip = "94102"

    print(f"Testing ZIP: {test_zip}\n")

    try:
        dealers = scraper.scrape_zip_code(test_zip)

        print(f"\n✅ Found {len(dealers)} Lennox dealers")

        if len(dealers) > 0:
            print(f"\nSample dealers (first 3):")
            for i, dealer in enumerate(dealers[:3], 1):
                print(f"   {i}. {dealer.name}")
                print(f"      Location: {dealer.city}, {dealer.state} {dealer.zip}")
                print(f"      Phone: {dealer.phone if dealer.phone else '(none)'}")
                if dealer.website:
                    print(f"      Website: {dealer.website}")
                print()
        else:
            print("\n❌ No dealers found - extraction may be broken")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("="*80 + "\n")


if __name__ == "__main__":
    test_lennox()
