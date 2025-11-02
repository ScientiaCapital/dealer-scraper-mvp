#!/usr/bin/env python3
"""
Master OEM Production Runner
Runs all 20 OEM scrapers ONE AT A TIME with checkpoint saving (every 25 ZIPs)

Usage:
    python3 scripts/run_all_oems_production.py

Features:
- Runs ONE OEM scraper to completion before starting the next
- Semi-automated: Prompts before each OEM
- Pause-and-alert error handling
- Priority ordering: HVAC → Generators → Solar → Battery
- Checkpoint saving every 25 ZIPs per OEM
- Progress tracking and statistics
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode, StandardizedDealer
from config import ALL_ZIP_CODES

# OEM Priority Order (High-value first)
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC (Highest contractor counts)
    "Carrier", "Lennox", "Trane", "Mitsubishi", "York", "Rheem",

    # Tier 2: Generators (Large networks)
    "Generac", "Kohler", "Cummins", "Briggs & Stratton",

    # Tier 3: Solar Inverters (Medium networks)
    "SolarEdge", "Enphase", "SMA", "Fronius", "Sungrow",
    "GoodWe", "Growatt", "Sol-Ark",

    # Tier 4: Battery Storage (Smaller networks)
    "Tesla", "SimpliPhi"
]

def print_banner():
    """Print startup banner with configuration"""
    print("=" * 70)
    print("OEM CHECKPOINT PRODUCTION RUN")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Total OEMs: {len(OEM_PRIORITY_ORDER)}")
    print(f"  Total ZIP codes: {len(ALL_ZIP_CODES)}")
    print(f"  Checkpoint interval: 25 ZIPs")
    print(f"  Total operations: {len(OEM_PRIORITY_ORDER) * len(ALL_ZIP_CODES):,}")
    print(f"  Estimated time: 7-9 hours")
    print(f"  Mode: PLAYWRIGHT (local automation)")
    print(f"\n  ⚠️  RUNS ONE OEM TO COMPLETION BEFORE STARTING NEXT")
    print("\n" + "=" * 70)


def run_oem_scraper(oem_name: str) -> Dict:
    """
    Run scraper for single OEM to completion with checkpoint saving

    Args:
        oem_name: Name of OEM to scrape

    Returns:
        Dict with results (dealers_raw, dealers_deduped, duration, status)
    """
    start_time = datetime.now()

    try:
        # Create scraper
        scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)

        # Run with checkpoints (every 25 ZIPs) - COMPLETES ALL ZIPS BEFORE RETURNING
        dealers = scraper.scrape_multiple(
            zip_codes=ALL_ZIP_CODES,
            verbose=True,
            checkpoint_interval=25
        )

        # Deduplicate
        scraper.deduplicate_by_phone()

        # Save final CSV/JSON
        date_str = datetime.now().strftime("%Y%m%d")
        oem_name_lower = oem_name.lower().replace(" ", "_")
        output_dir = f"output/oem_data/{oem_name_lower}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        scraper.save_csv(f"{output_dir}/{oem_name_lower}_national_{date_str}.csv")
        scraper.save_json(f"{output_dir}/{oem_name_lower}_national_{date_str}.json")

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success",
            "dealers_raw": len(dealers),
            "dealers_deduped": len(scraper.dealers),
            "duration": duration,
            "output_dir": output_dir
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        return {
            "status": "error",
            "error": str(e),
            "duration": duration
        }


def main():
    """Main execution loop - runs ONE OEM at a time to completion"""

    print_banner()

    # Results tracking
    results = {}
    completed = []
    skipped = []
    failed = []

    for i, oem_name in enumerate(OEM_PRIORITY_ORDER, 1):
        print(f"\n{'=' * 70}")
        print(f"[{i}/{len(OEM_PRIORITY_ORDER)}] Next OEM: {oem_name}")
        print(f"{'=' * 70}")

        # Semi-automated prompt
        user_input = input("\nReady to run? (yes/no/skip): ").strip().lower()

        if user_input == 'yes':
            print(f"\n🚀 Starting {oem_name} scraper...")
            print(f"   ZIPs: {len(ALL_ZIP_CODES)}")
            print(f"   Checkpoints will save every 25 ZIPs")
            print(f"   ⚠️  Will run to completion before moving to next OEM\n")

            # Run scraper TO COMPLETION
            result = run_oem_scraper(oem_name)
            results[oem_name] = result

            if result["status"] == "success":
                completed.append(oem_name)
                print(f"\n✅ {oem_name} COMPLETE!")
                print(f"   Dealers collected: {result['dealers_raw']}")
                print(f"   After deduplication: {result['dealers_deduped']}")
                print(f"   Duration: {result['duration']/60:.1f} minutes")
                print(f"   Saved to: {result['output_dir']}")

            else:
                failed.append(oem_name)
                print(f"\n❌ {oem_name} FAILED")
                print(f"   Error: {result['error']}")
                print(f"   Last checkpoint preserved")

                # Pause and alert
                choice = input("\nOptions: (r)etry / (s)kip / (q)uit: ").strip().lower()

                if choice == 'r':
                    # Retry same OEM
                    print(f"\n🔄 Retrying {oem_name}...")
                    result = run_oem_scraper(oem_name)
                    results[oem_name] = result

                    if result["status"] == "success":
                        completed.append(oem_name)
                        failed.remove(oem_name)

                elif choice == 's':
                    # Skip to next
                    continue

                else:
                    # Quit entire run
                    print("\n🛑 Production run stopped by user")
                    break

        elif user_input == 'skip':
            skipped.append(oem_name)
            print(f"⏭️  Skipping {oem_name}")
            continue

        else:
            # Exit completely
            print("\n🛑 Production run stopped by user")
            break

    # Final summary
    print("\n" + "=" * 70)
    print("PRODUCTION RUN COMPLETE")
    print("=" * 70)
    print(f"\n✅ Completed: {len(completed)} OEMs")
    if completed:
        for oem in completed:
            print(f"   - {oem}")

    print(f"\n⏭️  Skipped: {len(skipped)} OEMs")
    if skipped:
        for oem in skipped:
            print(f"   - {oem}")

    print(f"\n❌ Failed: {len(failed)} OEMs")
    if failed:
        for oem in failed:
            print(f"   - {oem}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
