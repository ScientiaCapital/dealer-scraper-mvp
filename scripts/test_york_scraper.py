"""
Test script for York HVAC scraper.

Tests York scraper on a few diverse ZIPs to verify it's working.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.york_scraper import YorkScraper
from scrapers.base_scraper import ScraperMode

def test_york_scraper():
    """Test York scraper on diverse ZIPs."""
    
    print("\n" + "="*80)
    print("TESTING YORK HVAC SCRAPER")
    print("="*80 + "\n")
    
    # Test ZIPs (diverse geographic coverage)
    test_zips = [
        "94102",  # San Francisco, CA
        "75201",  # Dallas, TX
        "10001",  # New York, NY
    ]
    
    # Create scraper
    scraper = YorkScraper(mode=ScraperMode.PLAYWRIGHT)
    
    total_dealers = 0
    
    for zip_code in test_zips:
        print(f"\n{'─'*80}")
        print(f"Testing ZIP: {zip_code}")
        print(f"{'─'*80}")
        
        dealers = scraper.scrape_zip_code(zip_code)
        
        print(f"\n✅ Found {len(dealers)} York dealers for ZIP {zip_code}")
        
        if len(dealers) > 0:
            print(f"\nSample dealers (first 3):")
            for i, dealer in enumerate(dealers[:3], 1):
                print(f"   {i}. {dealer.name}")
                print(f"      Location: {dealer.city}, {dealer.state} {dealer.zip}")
                print(f"      Phone: {dealer.phone if dealer.phone else '(none)'}")
                if dealer.website:
                    print(f"      Website: {dealer.website}")
                print()
        
        total_dealers += len(dealers)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total dealers found across {len(test_zips)} ZIPs: {total_dealers}")
    print(f"Average dealers per ZIP: {total_dealers / len(test_zips):.1f}")
    
    if total_dealers > 0:
        print(f"\n✅ York scraper is WORKING!")
        print(f"   Ready for production run (343 ZIPs)")
    else:
        print(f"\n❌ York scraper needs debugging")
        print(f"   No dealers extracted from any test ZIP")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    test_york_scraper()
