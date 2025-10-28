#!/usr/bin/env python3
"""
Production Cummins dealer scraping for all 140 SREC state ZIP codes
SAVES PROGRESSIVELY - won't lose data if it crashes
"""
import json
import csv
from datetime import datetime
from scrapers.cummins_scraper import CumminsScraper
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL

def save_progress(all_dealers, checkpoint_num, timestamp):
    """Save current progress to disk"""

    # Save JSON checkpoint
    json_file = f"output/cummins_checkpoint_{checkpoint_num}_{timestamp}.json"
    dealers_dict = [d.to_dict() for d in all_dealers]
    with open(json_file, 'w') as f:
        json.dump(dealers_dict, f, indent=2)

    # Save CSV checkpoint
    csv_file = f"output/cummins_checkpoint_{checkpoint_num}_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_dealers:
            fieldnames = [
                'name', 'phone', 'domain', 'website',
                'street', 'city', 'state', 'zip', 'address_full',
                'rating', 'review_count', 'tier',
                'distance', 'distance_miles',
                'oem_source', 'scraped_from_zip'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for dealer in all_dealers:
                d = dealer.to_dict()
                writer.writerow({k: d.get(k, '') for k in fieldnames})

    print(f"      💾 Saved checkpoint: {len(all_dealers)} dealers to {json_file}")

def main():
    print("="*70)
    print("CUMMINS PRODUCTION SCRAPING")
    print("="*70)
    print(f"Target: {len(ZIP_CODES_SREC_ALL)} SREC state ZIP codes")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Strategy: Save checkpoint every 10 ZIPs")
    print("="*70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create scraper
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)

    all_dealers = []

    # Scrape in batches, saving after each batch
    print(f"\n📍 Scraping {len(ZIP_CODES_SREC_ALL)} ZIP codes...")

    for i, zip_code in enumerate(ZIP_CODES_SREC_ALL, 1):
        print(f"\n[{i}/{len(ZIP_CODES_SREC_ALL)}] Scraping Cummins dealers for ZIP {zip_code}...")

        try:
            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            print(f"   ✓ Found {len(dealers)} dealers (Total so far: {len(all_dealers)})")

            # Save checkpoint every 10 ZIPs
            if i % 10 == 0:
                save_progress(all_dealers, i, timestamp)

        except Exception as e:
            print(f"   ✗ Error scraping ZIP {zip_code}: {e}")
            # Save checkpoint on error too
            save_progress(all_dealers, f"{i}_error", timestamp)
            continue

    print(f"\n✅ Scraping complete!")
    print(f"   Total dealers found: {len(all_dealers)}")

    # Deduplicate by phone
    print(f"\n🔄 Deduplicating by phone number...")
    scraper.dealers = all_dealers
    scraper.deduplicate(key="phone")
    deduped_dealers = scraper.dealers
    print(f"   Unique dealers: {len(deduped_dealers)}")
    print(f"   Duplicates removed: {len(all_dealers) - len(deduped_dealers)}")

    # Save FINAL results
    final_timestamp = datetime.now().strftime("%Y%m%d")

    # Save JSON
    json_file = f"output/cummins_dealers_{final_timestamp}.json"
    dealers_dict = [d.to_dict() for d in deduped_dealers]
    with open(json_file, 'w') as f:
        json.dump(dealers_dict, f, indent=2)
    print(f"\n💾 Saved FINAL JSON: {json_file}")

    # Save CSV
    csv_file = f"output/cummins_dealers_{final_timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if deduped_dealers:
            fieldnames = [
                'name', 'phone', 'domain', 'website',
                'street', 'city', 'state', 'zip', 'address_full',
                'rating', 'review_count', 'tier',
                'distance', 'distance_miles',
                'oem_source', 'scraped_from_zip'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for dealer in deduped_dealers:
                d = dealer.to_dict()
                writer.writerow({k: d.get(k, '') for k in fieldnames})

    print(f"💾 Saved FINAL CSV: {csv_file}")

    # Summary stats
    print(f"\n📊 Summary Statistics:")
    print(f"   Total dealers scraped: {len(all_dealers)}")
    print(f"   Unique dealers: {len(deduped_dealers)}")
    print(f"   ZIP codes processed: {len(ZIP_CODES_SREC_ALL)}")
    print(f"   Avg dealers per ZIP: {len(all_dealers) / len(ZIP_CODES_SREC_ALL):.1f}")

    # Count by state
    states = {}
    for dealer in deduped_dealers:
        state = dealer.state or 'Unknown'
        states[state] = states.get(state, 0) + 1

    print(f"\n   Dealers by state:")
    for state in sorted(states.keys(), key=lambda s: states[s], reverse=True):
        print(f"      {state}: {states[state]}")

    print(f"\n✅ Cummins production scraping complete!")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

if __name__ == "__main__":
    main()
