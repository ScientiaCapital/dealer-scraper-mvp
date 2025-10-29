#!/usr/bin/env python3
"""
Production scraping: Carrier + Mitsubishi across ALL 343 ZIPs
(140 SREC + 203 Major Metro areas)

Run ONE OEM at a time for stability:
1. Carrier (47 dealers/ZIP avg) = ~16,000 contractors
2. Mitsubishi Diamond Commercial (37/ZIP avg) = ~12,700 contractors
TOTAL: ~28,700 HVAC contractors

Expected runtime:
- 343 ZIPs × 5-6 sec/ZIP = ~30-35 minutes per OEM
- Total: ~60-70 minutes for both OEMs
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL, ZIP_CODES_MAJOR_METROS_ALL


def run_oem_scrape(oem_name: str, zip_codes: list):
    """
    Run scraping for a single OEM across all ZIP codes.

    Args:
        oem_name: Name of OEM to scrape (e.g., "Carrier", "Mitsubishi Electric")
        zip_codes: List of ZIP codes to scrape
    """
    print("=" * 100)
    print(f"STARTING {oem_name.upper()} PRODUCTION SCRAPE")
    print("=" * 100)
    print(f"Total ZIPs: {len(zip_codes)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Create scraper
    scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)

    # Scrape all ZIPs
    start_time = time.time()
    all_dealers = []
    failed_zips = []

    for i, zip_code in enumerate(zip_codes, 1):
        try:
            print(f"\n[{i}/{len(zip_codes)}] Scraping {oem_name} for ZIP {zip_code}...")

            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)

            print(f"  ✅ Found {len(dealers)} dealers (Total so far: {len(all_dealers)})")

            # Progress update every 25 ZIPs
            if i % 25 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining_zips = len(zip_codes) - i
                eta_minutes = (remaining_zips * avg_time) / 60

                print(f"\n{'=' * 80}")
                print(f"📊 PROGRESS UPDATE: {i}/{len(zip_codes)} ZIPs ({i/len(zip_codes)*100:.1f}%)")
                print(f"   Total dealers: {len(all_dealers)}")
                print(f"   Avg time/ZIP: {avg_time:.1f}s")
                print(f"   ETA: {eta_minutes:.1f} minutes")
                print(f"{'=' * 80}\n")

        except Exception as e:
            print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
            failed_zips.append(zip_code)
            continue

    # Deduplicate by phone
    print(f"\n{'=' * 100}")
    print(f"🔄 DEDUPLICATING BY PHONE NUMBER...")
    print(f"{'=' * 100}")

    deduped_dealers = scraper.deduplicate_by_phone(all_dealers)

    print(f"  Raw dealers: {len(all_dealers)}")
    print(f"  After dedup: {len(deduped_dealers)}")
    print(f"  Duplicates removed: {len(all_dealers) - len(deduped_dealers)}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    # Save CSV
    csv_filename = f"{oem_name.lower().replace(' ', '_')}_production_{timestamp}.csv"
    csv_path = output_dir / csv_filename
    scraper.dealers = deduped_dealers
    scraper.save_csv(csv_path)

    # Save JSON
    json_filename = f"{oem_name.lower().replace(' ', '_')}_production_{timestamp}.json"
    json_path = output_dir / json_filename
    scraper.save_json(json_path)

    # Final summary
    elapsed_total = time.time() - start_time

    print(f"\n{'=' * 100}")
    print(f"✅ {oem_name.upper()} SCRAPE COMPLETE!")
    print(f"{'=' * 100}")
    print(f"Total ZIPs scraped: {len(zip_codes)}")
    print(f"Total dealers found: {len(deduped_dealers)}")
    print(f"Failed ZIPs: {len(failed_zips)}")
    if failed_zips:
        print(f"  Failed: {', '.join(failed_zips[:10])}" + (" ..." if len(failed_zips) > 10 else ""))
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Avg time/ZIP: {elapsed_total/len(zip_codes):.1f}s")
    print(f"\n📁 Output files:")
    print(f"   CSV: {csv_path}")
    print(f"   JSON: {json_path}")
    print(f"{'=' * 100}\n")

    return deduped_dealers, failed_zips


def main():
    """Main execution: Carrier first, then Mitsubishi."""

    # Combine all ZIP codes
    all_zips = list(ZIP_CODES_SREC_ALL) + list(ZIP_CODES_MAJOR_METROS_ALL)

    print("\n" + "=" * 100)
    print("🚀 CARRIER + MITSUBISHI PRODUCTION SCRAPE")
    print("=" * 100)
    print(f"SREC State ZIPs: {len(ZIP_CODES_SREC_ALL)}")
    print(f"Major Metro ZIPs: {len(ZIP_CODES_MAJOR_METROS_ALL)}")
    print(f"TOTAL ZIPs: {len(all_zips)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Phase 1: Carrier
    print("\n\n" + "🎯" * 50)
    print("PHASE 1: CARRIER")
    print("🎯" * 50 + "\n")

    carrier_dealers, carrier_failed = run_oem_scrape("Carrier", all_zips)

    # Brief pause between OEMs
    print("\n⏸️  Pausing 30 seconds before next OEM...\n")
    time.sleep(30)

    # Phase 2: Mitsubishi
    print("\n\n" + "🎯" * 50)
    print("PHASE 2: MITSUBISHI ELECTRIC")
    print("🎯" * 50 + "\n")

    mitsubishi_dealers, mitsubishi_failed = run_oem_scrape("Mitsubishi Electric", all_zips)

    # Final summary
    print("\n\n" + "=" * 100)
    print("🎉 ALL SCRAPING COMPLETE!")
    print("=" * 100)
    print(f"\n📊 FINAL RESULTS:")
    print(f"   Carrier dealers: {len(carrier_dealers)}")
    print(f"   Mitsubishi dealers: {len(mitsubishi_dealers)}")
    print(f"   TOTAL CONTRACTORS: {len(carrier_dealers) + len(mitsubishi_dealers)}")
    print(f"\n❌ FAILED ZIPS:")
    print(f"   Carrier: {len(carrier_failed)}")
    print(f"   Mitsubishi: {len(mitsubishi_failed)}")
    print(f"\n📁 All files saved to: output/")
    print("=" * 100)


if __name__ == "__main__":
    main()
