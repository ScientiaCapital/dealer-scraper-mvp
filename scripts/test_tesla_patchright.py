"""
Test Tesla Scraper with Patchright Stealth Mode

Quick test script to verify Patchright bot detection bypass works with Tesla.
Tests on a single ZIP code first, then scales to 10 ZIPs if successful.

Usage:
    # Single ZIP test (San Francisco)
    python scripts/test_tesla_patchright.py

    # Test on 10 wealthy ZIPs
    python scripts/test_tesla_patchright.py --full
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.tesla_scraper import TeslaScraper
from scrapers.base_scraper import ScraperMode
from datetime import datetime
import argparse

def test_single_zip(zip_code: str = "94102"):
    """Test Tesla scraper on single ZIP code"""
    print("\n" + "="*60)
    print(" Tesla Patchright Stealth Test - Single ZIP")
    print("="*60 + "\n")

    scraper = TeslaScraper(mode=ScraperMode.PATCHRIGHT)

    try:
        print(f"Testing ZIP: {zip_code} (San Francisco)")
        dealers = scraper.scrape_zip_code(zip_code)

        print(f"\n✓ Success! Extracted {len(dealers)} Tesla installers")
        print("\nSample results:")
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"  {i}. {dealer.name}")
            print(f"     Phone: {dealer.phone}")
            print(f"     Tier: {dealer.tier}")
            print(f"     Website: {dealer.website}")
            print()

        return True, len(dealers)

    except Exception as e:
        print(f"\n✗ Failed: {str(e)}")
        return False, 0

def test_ten_zips():
    """Test Tesla scraper on 10 wealthy ZIPs"""
    print("\n" + "="*60)
    print(" Tesla Patchright Stealth Test - 10 ZIPs")
    print("="*60 + "\n")

    # 10 wealthy ZIPs across SREC states
    test_zips = [
        "94102",  # San Francisco, CA
        "90210",  # Beverly Hills, CA
        "94301",  # Palo Alto, CA
        "77019",  # Houston, TX
        "78746",  # Austin, TX
        "19103",  # Philadelphia, PA
        "02108",  # Boston, MA
        "07102",  # Newark, NJ
        "33139",  # Miami Beach, FL
        "33480",  # Palm Beach, FL
    ]

    scraper = TeslaScraper(mode=ScraperMode.PATCHRIGHT)

    success_count = 0
    total_dealers = 0

    for i, zip_code in enumerate(test_zips, 1):
        try:
            print(f"[{i:2d}/10] {zip_code}...", end=" ", flush=True)
            dealers = scraper.scrape_zip_code(zip_code)
            print(f"✓ {len(dealers):2d} installers")
            success_count += 1
            total_dealers += len(dealers)
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")

    # Summary
    print("\n" + "="*60)
    print(" Test Results")
    print("="*60)
    print(f"\nSuccess Rate: {success_count}/10 ZIPs ({success_count*10}%)")
    print(f"Total Installers: {total_dealers}")
    print(f"Average per ZIP: {total_dealers/success_count:.1f}" if success_count > 0 else "N/A")

    # Save results
    if scraper.dealers:
        scraper.deduplicate()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/tesla_patchright_test_{timestamp}.csv"
        scraper.save_csv(filename)
        print(f"\n✓ Results saved: {filename}")

    return success_count, total_dealers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Tesla scraper with Patchright stealth")
    parser.add_argument("--full", action="store_true", help="Run full 10-ZIP test")
    parser.add_argument("--zip", type=str, default="94102", help="Single ZIP to test (default: 94102)")
    args = parser.parse_args()

    if args.full:
        success, total = test_ten_zips()
        if success >= 8:
            print("\n✓ PATCHRIGHT STEALTH VERIFIED - Ready for production!")
        elif success >= 5:
            print("\n⚠ PARTIAL SUCCESS - May need proxy rotation")
        else:
            print("\n✗ INSUFFICIENT SUCCESS - Check bot detection")
    else:
        success, count = test_single_zip(args.zip)
        if success:
            print("✓ Single ZIP test passed! Run with --full to test 10 ZIPs")
        else:
            print("✗ Single ZIP test failed - check error above")
