#!/usr/bin/env python3
"""
Kohler Batch Scraper - 5 ZIPs at a time with full audit.
Run, audit output, refine, repeat.
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
BATCH_SIZE = 5
DELAY_BETWEEN_ZIPS = (2, 4)

def get_all_zips():
    """Flatten ZIP codes from all states."""
    zips = []
    for state, state_zips in ZIP_CODES_SREC_ALL.items():
        zips.extend(state_zips)
    return zips

def save_dealers_csv(dealers, filename):
    """Save dealers to CSV file."""
    if not dealers:
        print(f"  ⚠️ No dealers to save")
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

def audit_dealers(dealers):
    """Print audit report for scraped dealers."""
    print("\n" + "=" * 60)
    print("AUDIT REPORT")
    print("=" * 60)

    if not dealers:
        print("  No dealers collected")
        return

    # Basic counts
    total = len(dealers)
    with_phone = sum(1 for d in dealers if d.phone)
    with_address = sum(1 for d in dealers if d.address_full)
    with_website = sum(1 for d in dealers if d.website)

    print(f"  Total dealers: {total}")
    print(f"  With phone: {with_phone} ({with_phone/total*100:.0f}%)")
    print(f"  With address: {with_address} ({with_address/total*100:.0f}%)")
    print(f"  With website: {with_website} ({with_website/total*100:.0f}%)")

    # Tier distribution
    tiers = {}
    for d in dealers:
        tier = getattr(d, 'tier', 'Unknown')
        tiers[tier] = tiers.get(tier, 0) + 1

    print(f"\n  Tier distribution:")
    for tier, count in sorted(tiers.items(), key=lambda x: -x[1]):
        print(f"    {tier}: {count}")

    # State distribution
    states = {}
    for d in dealers:
        state = d.state or 'Unknown'
        states[state] = states.get(state, 0) + 1

    print(f"\n  State distribution:")
    for state, count in sorted(states.items(), key=lambda x: -x[1]):
        print(f"    {state}: {count}")

    # Sample dealers
    print(f"\n  Sample dealers:")
    for d in dealers[:3]:
        print(f"    - {d.name}")
        print(f"      Phone: {d.phone}")
        print(f"      Address: {d.address_full}")
        print(f"      Tier: {getattr(d, 'tier', 'N/A')}")

def run_batch(start_idx=0):
    """Run batch of 5 ZIPs starting from index."""
    print("=" * 60)
    print(f"KOHLER BATCH SCRAPER - 5 ZIPs (starting at index {start_idx})")
    print("=" * 60)

    all_zips = get_all_zips()
    total_zips = len(all_zips)
    print(f"Total ZIPs available: {total_zips}")

    # Select batch
    end_idx = min(start_idx + BATCH_SIZE, total_zips)
    batch_zips = all_zips[start_idx:end_idx]

    if not batch_zips:
        print(f"  ⚠️ No ZIPs in range {start_idx}-{end_idx}")
        return [], []

    print(f"Processing ZIPs {start_idx+1}-{end_idx}: {batch_zips}")
    print()

    # Initialize scraper
    scraper = KohlerScraper(mode=ScraperMode.PATCHRIGHT)

    # Track progress
    all_dealers = []
    failed_zips = []

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, zip_code in enumerate(batch_zips, 1):
        print(f"\n[{i}/{len(batch_zips)}] Processing ZIP: {zip_code}")

        try:
            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            print(f"  ✓ Found {len(dealers)} dealers (Batch total: {len(all_dealers)})")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_zips.append(zip_code)

        # Random delay between ZIPs
        if i < len(batch_zips):
            delay = random.uniform(*DELAY_BETWEEN_ZIPS)
            print(f"  ⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Deduplicate by phone
    print("\n" + "=" * 60)
    print("DEDUPLICATION")
    print("=" * 60)

    unique_phones = {}
    for d in all_dealers:
        phone = d.phone
        if phone and phone not in unique_phones:
            unique_phones[phone] = d

    unique_dealers = list(unique_phones.values())
    print(f"  Total collected: {len(all_dealers)}")
    print(f"  Unique dealers: {len(unique_dealers)}")
    print(f"  Duplicates removed: {len(all_dealers) - len(unique_dealers)}")

    # Save batch output
    batch_file = f"{OUTPUT_DIR}/kohler_batch_{start_idx:03d}_{timestamp}.csv"
    save_dealers_csv(unique_dealers, batch_file)

    # Run audit
    audit_dealers(unique_dealers)

    # Summary
    print("\n" + "=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"  ZIPs processed: {len(batch_zips)}")
    print(f"  ZIPs failed: {len(failed_zips)}")
    print(f"  Unique dealers: {len(unique_dealers)}")
    print(f"  Output file: {batch_file}")

    if failed_zips:
        print(f"\n  Failed ZIPs: {failed_zips}")

    # Next batch info
    next_start = end_idx
    if next_start < total_zips:
        print(f"\n  📍 Next batch: python3 scripts/kohler_batch_5.py {next_start}")
    else:
        print(f"\n  ✅ All ZIPs processed!")

    return unique_dealers, batch_file

if __name__ == "__main__":
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run_batch(start_idx)
