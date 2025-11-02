#!/usr/bin/env python3
"""
Test checkpoint feature with Generac scraper
Tests: 30 ZIPs with 10-zip checkpoint interval
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL

def main():
    print("="*60)
    print("Testing Checkpoint Feature - Briggs & Stratton Scraper")
    print("="*60)

    # Use first 30 ZIPs from SREC list
    test_zips = ZIP_CODES_SREC_ALL[:30]

    print(f"\nConfiguration:")
    print(f"  OEM: Briggs & Stratton")
    print(f"  ZIPs: {len(test_zips)}")
    print(f"  Checkpoint Interval: 10 (testing)")
    print(f"  Expected Checkpoints: 3 (at 10, 20, 30)")

    # Create scraper
    scraper = ScraperFactory.create("Briggs & Stratton", mode=ScraperMode.PLAYWRIGHT)

    # Run with checkpoints
    dealers = scraper.scrape_multiple(
        zip_codes=test_zips,
        verbose=True,
        checkpoint_interval=10
    )

    print(f"\n{'='*60}")
    print(f"Test Complete!")
    print(f"  Total dealers: {len(dealers)}")
    print(f"  Check: output/oem_data/briggs_stratton/briggs_stratton_checkpoint_*.json")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
