#!/usr/bin/env python3
"""
National scrape for Mitsubishi Diamond Commercial VRF contractors.

Runs across all 140 SREC state ZIPs to identify high-value resimercial
HVAC contractors for Coperniq's ICP targeting.

Expected output: 50-150 unique Diamond Commercial contractors.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_MAJOR_METROS_ALL
from datetime import datetime

def main():
    print("=" * 80)
    print("MITSUBISHI DIAMOND COMMERCIAL NATIONAL SCRAPE")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {len(ZIP_CODES_MAJOR_METROS_ALL)} major metro ZIPs (all 50 states)")
    print(f"Expected: 150-300 unique Diamond Commercial VRF contractors")
    print("=" * 80)

    # Create scraper
    print("\nInitializing Mitsubishi scraper...")
    scraper = ScraperFactory.create("Mitsubishi", mode=ScraperMode.PLAYWRIGHT)

    # Run scrape across all major metros
    print(f"\nScraping {len(ZIP_CODES_MAJOR_METROS_ALL)} ZIP codes across all 50 states...")
    print("This will take approximately 3-4 hours (~5-6 seconds per ZIP)")
    print("-" * 80)

    all_dealers = []

    for idx, zip_code in enumerate(ZIP_CODES_MAJOR_METROS_ALL, 1):
        print(f"\n[{idx}/{len(ZIP_CODES_MAJOR_METROS_ALL)}] Processing ZIP: {zip_code}")

        try:
            dealers = scraper.scrape([zip_code])

            if dealers:
                print(f"  ✓ Found {len(dealers)} contractors")
                all_dealers.extend(dealers)
            else:
                print(f"  - No contractors found")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    # Final statistics
    print("\n" + "=" * 80)
    print("SCRAPE COMPLETE")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total contractors collected: {len(all_dealers)}")
    print(f"ZIP codes processed: {len(ZIP_CODES_MAJOR_METROS_ALL)}")

    # Deduplicate
    unique_contractors = {}
    for dealer in all_dealers:
        key = dealer.phone  # Deduplicate by phone
        if key not in unique_contractors:
            unique_contractors[key] = dealer

    print(f"Unique contractors (after deduplication): {len(unique_contractors)}")

    # Save output
    output_file = f"output/mitsubishi_deduped_{datetime.now().strftime('%Y%m%d')}.csv"
    print(f"\nSaving to: {output_file}")

    scraper.save_to_csv(list(unique_contractors.values()), output_file)

    print(f"✅ National scrape complete! Data saved to {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
