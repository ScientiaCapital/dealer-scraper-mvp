#!/usr/bin/env python3
"""
Kohler Production Run - Using Fixed KohlerScraper with Patchright
Scrapes all SREC state ZIPs with proper cookie consent handling and React input.
"""

import sys
import os
import csv
import time
import random
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.kohler_scraper import KohlerScraper
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL

# Configuration
OUTPUT_DIR = "output"
BATCH_SIZE = 25  # Save after every N ZIPs
DELAY_BETWEEN_ZIPS = (3, 6)  # Random delay range in seconds

def get_all_zips():
    """Flatten ZIP codes from all states."""
    zips = []
    for state, state_zips in ZIP_CODES_SREC_ALL.items():
        zips.extend(state_zips)
    return zips

def save_dealers_csv(dealers, filename):
    """Save dealers to CSV file."""
    if not dealers:
        return

    fieldnames = [
        'name', 'phone', 'website', 'domain', 'street', 'city',
        'state', 'zip', 'address_full', 'rating', 'review_count',
        'tier', 'certifications', 'distance', 'distance_miles',
        'scraped_from_zip', 'oem_source'
    ]

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in dealers:
            row = {
                'name': d.name,
                'phone': d.phone,
                'website': d.website,
                'domain': getattr(d, 'domain', ''),
                'street': d.street,
                'city': d.city,
                'state': d.state,
                'zip': d.zip_code,
                'address_full': d.address_full,
                'rating': d.rating,
                'review_count': d.review_count,
                'tier': getattr(d, 'tier', 'Certified'),
                'certifications': ','.join(d.certifications) if d.certifications else '',
                'distance': getattr(d, 'distance', ''),
                'distance_miles': getattr(d, 'distance_miles', 0),
                'scraped_from_zip': d.search_zip,
                'oem_source': 'Kohler'
            }
            writer.writerow(row)

    print(f"  ✓ Saved {len(dealers)} dealers to {filename}")

def run_production():
    """Run full production scrape."""
    print("=" * 70)
    print("KOHLER PRODUCTION RUN - PATCHRIGHT MODE")
    print("=" * 70)

    all_zips = get_all_zips()
    print(f"Total ZIPs: {len(all_zips)} (15 SREC states)")
    print()

    # Initialize scraper
    scraper = KohlerScraper(mode=ScraperMode.PATCHRIGHT)

    # Track progress
    all_dealers = []
    failed_zips = []
    batch_num = 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, zip_code in enumerate(all_zips, 1):
        print(f"\n[{i}/{len(all_zips)}] Processing ZIP: {zip_code}")

        try:
            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            print(f"  ✓ Found {len(dealers)} dealers (Total: {len(all_dealers)})")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_zips.append(zip_code)

        # Save batch checkpoint
        if i % BATCH_SIZE == 0:
            batch_file = f"{OUTPUT_DIR}/kohler_batch_{batch_num:03d}_{timestamp}.csv"
            save_dealers_csv(all_dealers, batch_file)
            batch_num += 1

        # Random delay between ZIPs
        if i < len(all_zips):
            delay = random.uniform(*DELAY_BETWEEN_ZIPS)
            print(f"  ⏳ Waiting {delay:.1f}s before next ZIP...")
            time.sleep(delay)

    # Deduplicate by phone
    print("\n" + "=" * 70)
    print("DEDUPLICATION")
    print("=" * 70)

    unique_phones = {}
    for d in all_dealers:
        phone = d.phone
        if phone and phone not in unique_phones:
            unique_phones[phone] = d

    unique_dealers = list(unique_phones.values())
    print(f"Total collected: {len(all_dealers)}")
    print(f"Unique dealers: {len(unique_dealers)}")
    print(f"Duplicates removed: {len(all_dealers) - len(unique_dealers)}")

    # Save final output
    final_file = f"{OUTPUT_DIR}/kohler_dealers_{timestamp}.csv"
    save_dealers_csv(unique_dealers, final_file)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"ZIPs processed: {len(all_zips)}")
    print(f"ZIPs failed: {len(failed_zips)}")
    print(f"Unique dealers: {len(unique_dealers)}")
    print(f"Output file: {final_file}")

    if failed_zips:
        print(f"\nFailed ZIPs: {failed_zips}")

    # Calculate phone coverage
    with_phone = sum(1 for d in unique_dealers if d.phone)
    phone_pct = (with_phone / len(unique_dealers) * 100) if unique_dealers else 0
    print(f"\nPhone coverage: {with_phone}/{len(unique_dealers)} ({phone_pct:.1f}%)")

    return unique_dealers, final_file

if __name__ == "__main__":
    run_production()
