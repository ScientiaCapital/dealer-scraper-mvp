#!/usr/bin/env python3
"""
Production run: Cummins RS Dealer Locator - ALL 50 STATES
Target: 137 major metro ZIPs (2-5 cities per state)
Timeline: ~15-20 minutes
"""
from scrapers.cummins_scraper import CumminsScraper
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_MAJOR_METROS_ALL
from datetime import datetime
import json
import csv

def save_checkpoint(dealers, checkpoint_num, timestamp):
    """Save progress checkpoint (both JSON and CSV)"""
    # Save JSON checkpoint
    json_file = f"output/cummins_national_checkpoint_{checkpoint_num}_{timestamp}.json"
    dealers_dict = [d.to_dict() for d in dealers]
    with open(json_file, 'w') as f:
        json.dump(dealers_dict, f, indent=2)

    # Save CSV checkpoint
    csv_file = f"output/cummins_national_checkpoint_{checkpoint_num}_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if dealers:
            fieldnames = [
                'name', 'phone', 'domain', 'website',
                'street', 'city', 'state', 'zip', 'address_full',
                'rating', 'review_count', 'tier',
                'distance', 'distance_miles',
                'oem_source', 'scraped_from_zip'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for dealer in dealers:
                d = dealer.to_dict()
                writer.writerow({k: d.get(k, '') for k in fieldnames})

    print(f"      💾 Saved checkpoint: {len(dealers)} dealers")

def main():
    print("=" * 70)
    print("CUMMINS RESIDENTIAL STANDBY - NATIONAL RUN (ALL 50 STATES)")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ZIP Codes: {len(ZIP_CODES_MAJOR_METROS_ALL)} (137 major metro ZIPs across 50 states)")
    print(f"Strategy: Save checkpoint every 10 ZIPs")
    print("=" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create scraper
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)

    all_dealers = []

    # Run scraping (loop through ZIPs)
    print(f"\n📍 Scraping {len(ZIP_CODES_MAJOR_METROS_ALL)} ZIP codes...")

    for i, zip_code in enumerate(ZIP_CODES_MAJOR_METROS_ALL, 1):
        print(f"\n[{i}/{len(ZIP_CODES_MAJOR_METROS_ALL)}] Scraping ZIP {zip_code}...")

        try:
            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            print(f"   ✓ Found {len(dealers)} dealers (Total: {len(all_dealers)})")

            # Save checkpoint every 10 ZIPs
            if i % 10 == 0:
                save_checkpoint(all_dealers, i, timestamp)

        except Exception as e:
            print(f"   ✗ Error scraping ZIP {zip_code}: {e}")
            # Save checkpoint on error too
            save_checkpoint(all_dealers, f"{i}_error", timestamp)
            continue

    print(f"\n✅ Scraping complete!")
    print(f"   Total dealers found: {len(all_dealers)}")

    # Deduplicate by phone
    print(f"\n{'='*70}")
    print("DEDUPLICATING DEALERS BY PHONE NUMBER")
    print(f"{'='*70}")

    scraper.dealers = all_dealers
    before_count = len(scraper.dealers)
    scraper.deduplicate(key="phone")
    after_count = len(scraper.dealers)

    duplicate_count = before_count - after_count
    duplicate_pct = (duplicate_count / before_count * 100) if before_count > 0 else 0

    print(f"\n📊 Deduplication Results:")
    print(f"   • Before: {before_count:,} dealers")
    print(f"   • After: {after_count:,} unique dealers")
    print(f"   • Removed: {duplicate_count:,} duplicates ({duplicate_pct:.1f}%)")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_file = f"output/cummins_national_{timestamp}.csv"
    json_file = f"output/cummins_national_{timestamp}.json"

    scraper.save_csv(csv_file)
    scraper.save_json(json_file)

    print(f"\n✅ Cummins national run complete!")
    print(f"   📁 CSV: {csv_file}")
    print(f"   📁 JSON: {json_file}")
    print(f"   📊 Total unique dealers: {len(scraper.dealers):,}")
    print(f"\n   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
