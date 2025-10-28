#!/usr/bin/env python3
"""
Test Mitsubishi scraper with multiple ZIPs from different states
"""

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

def main():
    print("=" * 80)
    print("TESTING MITSUBISHI WITH MULTIPLE ZIPS")
    print("=" * 80)
    
    # Test ZIPs from different states
    test_zips = [
        ("94102", "CA - San Francisco"),
        ("75201", "TX - Dallas"),
        ("33101", "FL - Miami"),
    ]
    
    # Create scraper
    scraper = ScraperFactory.create("Mitsubishi", mode=ScraperMode.PLAYWRIGHT)
    
    for zip_code, location in test_zips:
        print(f"\n{'=' * 80}")
        print(f"Testing: {zip_code} ({location})")
        print("=" * 80)
        
        try:
            dealers = scraper.scrape_zip(zip_code)
            
            print(f"\n✓ Found {len(dealers)} contractors")
            if dealers:
                print(f"\nFirst contractor:")
                d = dealers[0]
                print(f"  Name: {d.name}")
                print(f"  Phone: {d.phone}")
                print(f"  City: {d.city}, {d.state}")
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
