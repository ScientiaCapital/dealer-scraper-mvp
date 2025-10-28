#!/usr/bin/env python3
"""
Convert Cummins checkpoint file to final deduplicated output using enhanced deduplication
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.cummins_scraper import CumminsScraper
from scrapers.base_scraper import ScraperMode, StandardizedDealer
from datetime import datetime
import json
import glob

def main():
    # Find the latest checkpoint file
    checkpoint_files = glob.glob("output/cummins_national_checkpoint_*.json")
    if not checkpoint_files:
        print("❌ No checkpoint files found!")
        return

    # Sort by checkpoint number (extract number from filename)
    def get_checkpoint_num(filename):
        # Extract number from pattern like checkpoint_130_
        import re
        match = re.search(r'checkpoint_(\d+)_', filename)
        return int(match.group(1)) if match else 0

    latest_checkpoint = max(checkpoint_files, key=get_checkpoint_num)
    print(f"📂 Loading checkpoint: {latest_checkpoint}")

    # Load dealers from checkpoint
    with open(latest_checkpoint, 'r') as f:
        dealers_data = json.load(f)

    print(f"   Loaded {len(dealers_data):,} raw dealer records")

    # Convert to StandardizedDealer objects
    dealers = []
    for d in dealers_data:
        dealer = StandardizedDealer(
            name=d.get('name', ''),
            phone=d.get('phone', ''),
            domain=d.get('domain', ''),
            website=d.get('website', ''),
            street=d.get('street', ''),
            city=d.get('city', ''),
            state=d.get('state', ''),
            zip=d.get('zip', ''),
            address_full=d.get('address_full', ''),
            rating=d.get('rating', 0.0),
            review_count=d.get('review_count', 0),
            tier=d.get('tier', 'Standard'),
            distance=d.get('distance', ''),
            distance_miles=d.get('distance_miles', 0.0),
            oem_source=d.get('oem_source', 'Cummins'),
            scraped_from_zip=d.get('scraped_from_zip', '')
        )
        dealers.append(dealer)

    # Create scraper and use ENHANCED deduplication
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.dealers = dealers

    print("\n🔬 Applying ENHANCED multi-signal deduplication...")
    before_count = len(scraper.dealers)

    # Use the NEW enhanced deduplication method
    scraper.deduplicate_by_phone()

    after_count = len(scraper.dealers)

    duplicate_count = before_count - after_count
    duplicate_pct = (duplicate_count / before_count * 100) if before_count > 0 else 0

    print(f"\n📊 Enhanced Deduplication Results:")
    print(f"   • Before: {before_count:,} raw dealer records")
    print(f"   • After: {after_count:,} unique dealers")
    print(f"   • Removed: {duplicate_count:,} duplicates ({duplicate_pct:.1f}%)")
    print(f"   • Deduplication rate: {duplicate_pct:.1f}%")

    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_file = f"output/cummins_dealers_{timestamp}_deduped.csv"
    json_file = f"output/cummins_dealers_{timestamp}_deduped.json"

    scraper.save_csv(csv_file)
    scraper.save_json(json_file)

    print(f"\n✅ Cummins national finalization complete with ENHANCED deduplication!")
    print(f"   📁 CSV: {csv_file}")
    print(f"   📁 JSON: {json_file}")
    print(f"   📊 Total unique dealers: {len(scraper.dealers):,}")

    # Also save a version with the expected name for grandmaster script
    expected_csv = f"output/cummins_dealers_{timestamp}.csv"
    scraper.save_csv(expected_csv)
    print(f"   📁 Also saved as: {expected_csv} (for grandmaster script)")

if __name__ == "__main__":
    main()