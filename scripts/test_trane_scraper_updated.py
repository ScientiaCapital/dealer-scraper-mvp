"""
Test the updated Trane scraper with table-based extraction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.trane_scraper import TraneScraper
from scrapers.base_scraper import ScraperMode
import json

def test_trane_scraper():
    """Test the updated Trane scraper."""
    
    print("\n" + "="*80)
    print("TESTING UPDATED TRANE SCRAPER (Table-Based Extraction)")
    print("="*80 + "\n")
    
    # Create scraper
    scraper = TraneScraper(mode=ScraperMode.PLAYWRIGHT)
    
    # Scrape dealers (ZIP code is ignored - extracts full table)
    print("📋 NOTE: ZIP code is ignored - extracting FULL dealer list from table")
    print("   Expected: ~1,138 dealers\n")
    
    dealers = scraper.scrape_zip_code("00000")  # Dummy ZIP (ignored)
    
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}\n")
    
    print(f"✅ Total dealers extracted: {len(dealers)}")
    
    if len(dealers) > 0:
        print(f"\n📊 Sample dealers (first 10):\n")
        for i, dealer in enumerate(dealers[:10], 1):
            print(f"   {i:2d}. {dealer.name}")
            print(f"       Location: {dealer.city}, {dealer.state} {dealer.zip}")
            print(f"       Phone: {dealer.phone if dealer.phone else '(enrichment needed)'}")
            print()
        
        # Statistics
        states = {}
        for dealer in dealers:
            state = dealer.state or 'Unknown'
            states[state] = states.get(state, 0) + 1
        
        print(f"📍 Dealers by state (top 15):")
        for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"   {state:20s}: {count:4d} dealers")
        
        # Save to CSV
        os.makedirs("output", exist_ok=True)
        output_file = "output/trane_test_extraction.csv"
        
        with open(output_file, 'w') as f:
            # Header
            f.write("name,city,state,zip,country,phone,website,domain\n")
            
            # Data
            for dealer in dealers:
                name = dealer.name.replace('"', '""')  # Escape quotes
                city = dealer.city.replace('"', '""')
                state = dealer.state
                zip_code = dealer.zip
                country = getattr(dealer, 'country', 'US')
                phone = dealer.phone
                website = dealer.website
                domain = dealer.domain
                
                f.write(f'"{name}","{city}","{state}","{zip_code}","{country}","{phone}","{website}","{domain}"\n')
        
        print(f"\n💾 Results saved to: {output_file}")
        print(f"   {len(dealers)} dealers ready for enrichment (Apollo/Clay)")
    else:
        print("❌ No dealers extracted - something went wrong")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    test_trane_scraper()
