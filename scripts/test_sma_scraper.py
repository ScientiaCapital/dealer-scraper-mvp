"""
Quick test of SMA Solar scraper to diagnose the issue.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.sma_scraper import SMAScraper
from scrapers.base_scraper import ScraperMode

def test_sma():
    """Test SMA scraper on single ZIP."""
    
    print("\n" + "="*80)
    print("TESTING SMA SOLAR SCRAPER")
    print("="*80 + "\n")
    
    scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)
    
    # Test ZIP (San Francisco)
    test_zip = "94102"
    
    print(f"Testing ZIP: {test_zip}\n")
    
    try:
        dealers = scraper.scrape_zip_code(test_zip)
        
        print(f"\n✅ Found {len(dealers)} SMA installers")
        
        if len(dealers) > 0:
            print(f"\nSample installers (first 3):")
            for i, dealer in enumerate(dealers[:3], 1):
                print(f"   {i}. {dealer.name}")
                print(f"      Location: {dealer.city}, {dealer.state} {dealer.zip}")
                print(f"      Phone: {dealer.phone if dealer.phone else '(none)'}")
                if dealer.website:
                    print(f"      Website: {dealer.website}")
                print()
        else:
            print("\n❌ No installers found - extraction may be broken")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*80 + "\n")


if __name__ == "__main__":
    test_sma()
