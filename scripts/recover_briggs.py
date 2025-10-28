#!/usr/bin/env python3
"""Recover Briggs national data from checkpoint and re-save with fixed CSV fields"""

import sys
import json
from pathlib import Path
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode, StandardizedDealer, DealerCapabilities

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    print("🔧 BRIGGS RECOVERY - Loading checkpoint and re-saving with fixed fields")
    print("=" * 70)
    
    # Load latest checkpoint (ZIP 130)
    checkpoint_file = "output/briggs_national_checkpoint_130_20251028_083051.json"
    
    print(f"Loading checkpoint: {checkpoint_file}")
    with open(checkpoint_file, 'r') as f:
        checkpoint_data = json.load(f)
    
    print(f"Loaded {len(checkpoint_data)} dealers from checkpoint")
    
    # Create scraper instance
    scraper = ScraperFactory.create("Briggs & Stratton", mode=ScraperMode.PLAYWRIGHT)
    
    # Reconstruct StandardizedDealer objects
    for dealer_dict in checkpoint_data:
        # Separate capabilities from dealer data
        caps_data = dealer_dict.pop("capabilities", {})
        caps = DealerCapabilities(**caps_data)
        
        dealer = StandardizedDealer(**dealer_dict, capabilities=caps)
        scraper.dealers.append(dealer)
    
    print(f"Reconstructed {len(scraper.dealers)} dealers")
    print()
    
    # Now scrape the final 7 ZIPs (131-137)
    final_zips = ["99301", "99501", "99701", "96801", "96720", "97301", "98101"]  # WA, AK, HI, OR
    
    print(f"Scraping final {len(final_zips)} ZIPs...")
    for i, zip_code in enumerate(final_zips, start=131):
        print(f"[{i}/137] Scraping ZIP {zip_code}...")
        try:
            dealers = scraper.scrape_zip(zip_code)
            print(f"   ✓ Found {len(dealers)} dealers (Total: {len(scraper.dealers)})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print()
    print("=" * 70)
    print("DEDUPLICATING DEALERS BY PHONE NUMBER")
    print("=" * 70)
    
    before_count = len(scraper.dealers)
    scraper.deduplicate_by_phone()
    after_count = len(scraper.dealers)
    removed = before_count - after_count
    
    print(f"Removed {removed} duplicate dealers (by phone)")
    print()
    print(f"📊 Deduplication Results:")
    print(f"   • Before: {before_count:,} dealers")
    print(f"   • After: {after_count:,} unique dealers")
    print(f"   • Removed: {removed:,} duplicates ({removed/before_count*100:.1f}%)")
    print()
    
    # Save with fixed CSV fields
    timestamp = "20251028"
    csv_file = f"output/briggs_national_{timestamp}.csv"
    json_file = f"output/briggs_national_{timestamp}.json"
    
    print(f"💾 Saving results...")
    scraper.save_csv(csv_file)
    scraper.save_json(json_file)
    
    print()
    print("✅ RECOVERY COMPLETE!")
    print(f"   • Unique dealers: {len(scraper.dealers)}")
    print(f"   • CSV: {csv_file}")
    print(f"   • JSON: {json_file}")

if __name__ == "__main__":
    main()
