"""
York Production Scraper - All 343 ZIPs

Runs York scraper across all SREC state ZIPs with checkpoint saves.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.york_scraper import YorkScraper
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL, ZIP_CODES_MAJOR_METROS_ALL

# Combine all ZIPs (343 total: 140 SREC + 203 major metros)
ALL_ZIPS = list(set(list(ZIP_CODES_SREC_ALL) + list(ZIP_CODES_MAJOR_METROS_ALL)))
from datetime import datetime
import csv

def run_york_production():
    """Run York production scrape."""
    
    print("\n" + "="*80)
    print("YORK PRODUCTION SCRAPER - 343 SREC STATE ZIPS")
    print("="*80 + "\n")
    
    scraper = YorkScraper(mode=ScraperMode.PLAYWRIGHT)
    
    all_dealers = []
    checkpoint_interval = 25
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/york_production_{timestamp}.csv"
    
    print(f"📊 Configuration:")
    print(f"   Total ZIPs: {len(ALL_ZIPS)} (140 SREC + 203 major metros)")
    print(f"   Checkpoint: Every {checkpoint_interval} ZIPs")
    print(f"   Output: {output_file}")
    print()
    
    for i, zip_code in enumerate(ALL_ZIPS, 1):
        print(f"[{i}/{len(ALL_ZIPS)}] Scraping York for ZIP {zip_code}...")
        
        try:
            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            
            print(f"  ✅ Found {len(dealers)} dealers (Total: {len(all_dealers)})")
            
            # Checkpoint save
            if i % checkpoint_interval == 0:
                save_checkpoint(all_dealers, output_file, i)
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    # Final save
    save_to_csv(all_dealers, output_file)
    
    print(f"\n{'='*80}")
    print(f"PRODUCTION COMPLETE")
    print(f"{'='*80}\n")
    print(f"✅ Total dealers extracted: {len(all_dealers)}")
    print(f"💾 Saved to: {output_file}")
    
    # Statistics
    states = {}
    with_phone = 0
    with_website = 0
    
    for dealer in all_dealers:
        state = dealer.state or 'Unknown'
        states[state] = states.get(state, 0) + 1
        if dealer.phone:
            with_phone += 1
        if dealer.website:
            with_website += 1
    
    print(f"\n📈 Statistics:")
    print(f"   Dealers with phone: {with_phone} ({100*with_phone/len(all_dealers):.1f}%)")
    print(f"   Dealers with website: {with_website} ({100*with_website/len(all_dealers):.1f}%)")
    print(f"\n📍 Top states:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {state:20s}: {count:4d} dealers")
    
    print(f"\n{'='*80}\n")


def save_checkpoint(dealers, filename, zip_count):
    """Save checkpoint."""
    print(f"\n💾 Checkpoint: Saving {len(dealers)} dealers after {zip_count} ZIPs...")
    save_to_csv(dealers, filename)
    print(f"   ✅ Saved to {filename}")


def save_to_csv(dealers, filename):
    """Save dealers to CSV."""
    os.makedirs("output", exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'name', 'phone', 'website', 'domain',
            'street', 'city', 'state', 'zip',
            'address_full', 'distance', 'distance_miles',
            'rating', 'review_count', 'tier',
            'oem_source', 'scraped_from_zip'
        ])
        
        # Data
        for dealer in dealers:
            writer.writerow([
                dealer.name,
                dealer.phone,
                dealer.website,
                dealer.domain,
                dealer.street,
                dealer.city,
                dealer.state,
                dealer.zip,
                dealer.address_full,
                dealer.distance,
                dealer.distance_miles,
                dealer.rating,
                dealer.review_count,
                dealer.tier,
                dealer.oem_source,
                dealer.scraped_from_zip
            ])


if __name__ == "__main__":
    run_york_production()
