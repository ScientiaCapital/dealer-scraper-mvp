#!/usr/bin/env python3
"""
Convert Cummins checkpoint file to final deduplicated output
"""
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

    latest_checkpoint = max(checkpoint_files)
    print(f"📂 Loading checkpoint: {latest_checkpoint}")

    # Load dealers from checkpoint
    with open(latest_checkpoint, 'r') as f:
        dealers_data = json.load(f)

    print(f"   Loaded {len(dealers_data):,} dealers")

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

    # Create scraper and deduplicate
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.dealers = dealers

    before_count = len(scraper.dealers)
    scraper.deduplicate(key="phone")
    after_count = len(scraper.dealers)

    duplicate_count = before_count - after_count
    duplicate_pct = (duplicate_count / before_count * 100) if before_count > 0 else 0

    print(f"\n📊 Deduplication Results:")
    print(f"   • Before: {before_count:,} dealers")
    print(f"   • After: {after_count:,} unique dealers")
    print(f"   • Removed: {duplicate_count:,} duplicates ({duplicate_pct:.1f}%)")

    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_file = f"output/cummins_national_{timestamp}.csv"
    json_file = f"output/cummins_national_{timestamp}.json"

    scraper.save_csv(csv_file)
    scraper.save_json(json_file)

    print(f"\n✅ Cummins national finalization complete!")
    print(f"   📁 CSV: {csv_file}")
    print(f"   📁 JSON: {json_file}")
    print(f"   📊 Total unique dealers: {len(scraper.dealers):,}")

if __name__ == "__main__":
    main()
