#!/usr/bin/env python3
"""
CHECKPOINT-SAFE HVAC Production Scraping

Runs ONE OEM at a time across ALL 343 ZIPs with checkpoint saving:
- Saves progress every 25 ZIPs to avoid data loss
- Can resume from checkpoint if interrupted
- Final deduplication at the end

Usage:
    # Start fresh scrape
    python3 scripts/run_hvac_production_safe.py --oem "Rheem"

    # Resume from checkpoint
    python3 scripts/run_hvac_production_safe.py --oem "Rheem" --resume
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_SREC_ALL, ZIP_CODES_MAJOR_METROS_ALL


def save_checkpoint(oem_name: str, all_dealers: list, completed_zips: list, output_dir: Path):
    """Save checkpoint to avoid data loss."""
    checkpoint_path = output_dir / f"{oem_name.lower().replace(' ', '_')}_checkpoint.json"

    checkpoint_data = {
        "oem_name": oem_name,
        "timestamp": datetime.now().isoformat(),
        "completed_zips": completed_zips,
        "total_dealers": len(all_dealers),
        "dealers": [d.to_dict() for d in all_dealers]
    }

    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    print(f"  💾 Checkpoint saved: {len(all_dealers)} dealers, {len(completed_zips)} ZIPs")


def load_checkpoint(oem_name: str, output_dir: Path):
    """Load checkpoint if exists."""
    checkpoint_path = output_dir / f"{oem_name.lower().replace(' ', '_')}_checkpoint.json"

    if not checkpoint_path.exists():
        return None, []

    print(f"\n📂 Loading checkpoint from: {checkpoint_path}")
    with open(checkpoint_path, 'r') as f:
        checkpoint_data = json.load(f)

    print(f"  Checkpoint from: {checkpoint_data['timestamp']}")
    print(f"  Completed ZIPs: {len(checkpoint_data['completed_zips'])}")
    print(f"  Dealers loaded: {checkpoint_data['total_dealers']}")

    return checkpoint_data['dealers'], checkpoint_data['completed_zips']


def run_oem_scrape(oem_name: str, zip_codes: list, resume: bool = False):
    """
    Run scraping for a single OEM across all ZIP codes with checkpoint saving.

    Args:
        oem_name: Name of OEM to scrape (e.g., "Rheem", "York", "Trane")
        zip_codes: List of ZIP codes to scrape
        resume: If True, resume from checkpoint
    """
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    print("=" * 100)
    print(f"STARTING {oem_name.upper()} PRODUCTION SCRAPE (CHECKPOINT-SAFE)")
    print("=" * 100)
    print(f"Total ZIPs: {len(zip_codes)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Checkpoint frequency: Every 25 ZIPs")
    print("=" * 100)

    # Load checkpoint if resuming
    all_dealers = []
    completed_zips = []

    if resume:
        checkpoint_dealers, completed_zips = load_checkpoint(oem_name, output_dir)
        if checkpoint_dealers:
            # Reconstruct StandardizedDealer objects
            from scrapers.base_scraper import StandardizedDealer
            scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)
            all_dealers = [StandardizedDealer(**d) for d in checkpoint_dealers]

            # Remove completed ZIPs from todo list
            zip_codes = [z for z in zip_codes if z not in completed_zips]
            print(f"\n✅ Resuming with {len(all_dealers)} dealers")
            print(f"   Remaining ZIPs: {len(zip_codes)}")
        else:
            print(f"\n⚠️  No checkpoint found, starting fresh")

    # Create scraper
    scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)

    # Scrape remaining ZIPs
    start_time = time.time()
    failed_zips = []
    checkpoint_counter = 0

    for i, zip_code in enumerate(zip_codes, 1):
        try:
            total_progress = len(completed_zips) + i
            print(f"\n[{total_progress}/{len(completed_zips) + len(zip_codes)}] Scraping {oem_name} for ZIP {zip_code}...")

            dealers = scraper.scrape_zip_code(zip_code)
            all_dealers.extend(dealers)
            completed_zips.append(zip_code)

            print(f"  ✅ Found {len(dealers)} dealers (Total so far: {len(all_dealers)})")

            checkpoint_counter += 1

            # Save checkpoint every 25 ZIPs
            if checkpoint_counter % 25 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / checkpoint_counter
                remaining_zips = len(zip_codes) - i
                eta_minutes = (remaining_zips * avg_time) / 60

                print(f"\n{'=' * 80}")
                print(f"📊 PROGRESS UPDATE: {total_progress}/{len(completed_zips) + len(zip_codes)} ZIPs ({total_progress/(len(completed_zips) + len(zip_codes))*100:.1f}%)")
                print(f"   Total dealers: {len(all_dealers)}")
                print(f"   Avg time/ZIP: {avg_time:.1f}s")
                print(f"   ETA: {eta_minutes:.1f} minutes")

                # SAVE CHECKPOINT
                save_checkpoint(oem_name, all_dealers, completed_zips, output_dir)

                print(f"{'=' * 80}\n")

        except Exception as e:
            print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
            failed_zips.append(zip_code)

            # Save checkpoint on error to preserve progress
            save_checkpoint(oem_name, all_dealers, completed_zips, output_dir)
            continue

    # Final checkpoint save
    save_checkpoint(oem_name, all_dealers, completed_zips, output_dir)

    # Deduplicate by phone
    print(f"\n{'=' * 100}")
    print(f"🔄 DEDUPLICATING BY PHONE NUMBER...")
    print(f"{'=' * 100}")

    # Set dealers before deduplication
    scraper.dealers = all_dealers
    scraper.deduplicate_by_phone()
    deduped_dealers = scraper.dealers

    print(f"  Raw dealers: {len(all_dealers)}")
    print(f"  After dedup: {len(deduped_dealers)}")
    print(f"  Duplicates removed: {len(all_dealers) - len(deduped_dealers)}")

    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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
    print(f"Total ZIPs scraped: {len(completed_zips)}")
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

    # Clean up checkpoint file
    checkpoint_path = output_dir / f"{oem_name.lower().replace(' ', '_')}_checkpoint.json"
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"🧹 Checkpoint file removed (scrape completed successfully)")

    return deduped_dealers, failed_zips


def main():
    """Main execution with checkpoint support."""
    parser = argparse.ArgumentParser(description='HVAC OEM Production Scraping (Checkpoint-Safe)')
    parser.add_argument('--oem', required=True, help='OEM name (e.g., "Rheem", "York", "Trane")')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()

    # Combine all ZIP codes
    all_zips = list(ZIP_CODES_SREC_ALL) + list(ZIP_CODES_MAJOR_METROS_ALL)

    print("\n" + "=" * 100)
    print(f"🚀 {args.oem.upper()} PRODUCTION SCRAPE (CHECKPOINT-SAFE)")
    print("=" * 100)
    print(f"SREC State ZIPs: {len(ZIP_CODES_SREC_ALL)}")
    print(f"Major Metro ZIPs: {len(ZIP_CODES_MAJOR_METROS_ALL)}")
    print(f"TOTAL ZIPs: {len(all_zips)}")
    print(f"Mode: {'RESUME' if args.resume else 'FRESH START'}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Run scrape
    dealers, failed = run_oem_scrape(args.oem, all_zips, resume=args.resume)

    print("\n" + "=" * 100)
    print("🎉 SCRAPING COMPLETE!")
    print("=" * 100)
    print(f"\n📊 FINAL RESULTS:")
    print(f"   {args.oem} dealers: {len(dealers)}")
    print(f"   Failed ZIPs: {len(failed)}")
    print(f"\n📁 All files saved to: output/")
    print("=" * 100)


if __name__ == "__main__":
    main()
