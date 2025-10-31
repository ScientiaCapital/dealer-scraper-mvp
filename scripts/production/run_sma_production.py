"""
SMA Solar Production Scraper - 140 SREC State ZIPs

Runs SMA scraper across all SREC state ZIPs with checkpoint saves.
Targets commercial solar installers for Coperniq outreach.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.sma_scraper import SMAScraper
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL
from datetime import datetime
import csv

def run_sma_production():
    """Run SMA Solar production scrape."""

    print("\n" + "="*80)
    print("SMA SOLAR PRODUCTION SCRAPER - 140 SREC STATE ZIPS")
    print("="*80 + "\n")

    scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)

    all_installers = []
    checkpoint_interval = 25

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/sma_production_{timestamp}.csv"

    print(f"📊 Configuration:")
    print(f"   Total ZIPs: {len(ZIP_CODES_SREC_ALL)} SREC states")
    print(f"   Checkpoint: Every {checkpoint_interval} ZIPs")
    print(f"   Output: {output_file}")
    print()

    for i, zip_code in enumerate(ZIP_CODES_SREC_ALL, 1):
        print(f"[{i}/{len(ZIP_CODES_SREC_ALL)}] Scraping SMA for ZIP {zip_code}...")

        try:
            installers = scraper.scrape_zip_code(zip_code)
            all_installers.extend(installers)

            print(f"  ✅ Found {len(installers)} installers (Total: {len(all_installers)})")

            # Checkpoint save
            if i % checkpoint_interval == 0:
                save_checkpoint(all_installers, output_file, i)

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Final save
    save_to_csv(all_installers, output_file)

    print(f"\n{'='*80}")
    print(f"PRODUCTION COMPLETE")
    print(f"{'='*80}\n")
    print(f"✅ Total installers extracted: {len(all_installers)}")
    print(f"💾 Saved to: {output_file}")

    # Statistics
    states = {}
    with_phone = 0
    with_website = 0

    for installer in all_installers:
        state = installer.state or 'Unknown'
        states[state] = states.get(state, 0) + 1
        if installer.phone:
            with_phone += 1
        if installer.website:
            with_website += 1

    if len(all_installers) > 0:
        print(f"\n📈 Statistics:")
        print(f"   Installers with phone: {with_phone} ({100*with_phone/len(all_installers):.1f}%)")
        print(f"   Installers with website: {with_website} ({100*with_website/len(all_installers):.1f}%)")
        print(f"\n📍 Top states:")
        for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {state:20s}: {count:4d} installers")

    print(f"\n{'='*80}\n")


def save_checkpoint(installers, filename, zip_count):
    """Save checkpoint."""
    print(f"\n💾 Checkpoint: Saving {len(installers)} installers after {zip_count} ZIPs...")
    save_to_csv(installers, filename)
    print(f"   ✅ Saved to {filename}")


def save_to_csv(installers, filename):
    """Save installers to CSV."""
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
        for installer in installers:
            writer.writerow([
                installer.name,
                installer.phone,
                installer.website,
                installer.domain,
                installer.street,
                installer.city,
                installer.state,
                installer.zip,
                installer.address_full,
                installer.distance,
                installer.distance_miles,
                installer.rating,
                installer.review_count,
                installer.tier,
                installer.oem_source,
                installer.scraped_from_zip
            ])


if __name__ == "__main__":
    run_sma_production()
