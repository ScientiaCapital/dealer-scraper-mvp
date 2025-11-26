#!/usr/bin/env python3
"""
Migrate FL License Data to SQLite Pipeline Database

Loads the FL "Everyone" CSV file into the SQLite database,
validates deduplication, and compares results to expected metrics.

Expected Results (from CSV deduplication):
- 232,280 total FL contractors loaded
- 102,651 MEP+R contractors
- 69,795 unique after deduplication (32% dedup rate)
- 11,401 multi-license with emails
- 1,799 unicorns (3+ categories)

Usage:
    python3 scripts/migrate_fl_to_sqlite.py
"""

import csv
import time
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PipelineDB, FL_LICENSE_CATEGORIES

# Configure logging
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"fl_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# FL Data File Location
DOWNLOADS = Path.home() / "Downloads"
FL_EVERYONE_FILE = DOWNLOADS / "Contractor List.xlsx - Everyone.csv"

# Output database
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DB_PATH = OUTPUT_DIR / "pipeline.db"


def migrate_fl_data(limit: int = None, reset: bool = False):
    """
    Migrate FL contractor data to SQLite.

    Args:
        limit: Optional limit on records to process (for testing)
        reset: If True, reset database before migration
    """
    print("\n" + "=" * 70)
    print("FL LICENSE DATA MIGRATION TO SQLITE")
    print("=" * 70)

    # Check source file
    if not FL_EVERYONE_FILE.exists():
        print(f"❌ Source file not found: {FL_EVERYONE_FILE}")
        print("   Download from FL DBPR: https://www.myfloridalicense.com/")
        return

    # Initialize database
    print(f"\n📂 Database: {DB_PATH}")
    db = PipelineDB(DB_PATH)

    if reset:
        print("⚠️  Resetting database...")
        db.reset_database(confirm=True)
    else:
        db.initialize()

    # Start pipeline run
    run_id = db.start_pipeline_run('FL', str(FL_EVERYONE_FILE))
    start_time = time.time()

    print(f"\n📖 Loading: {FL_EVERYONE_FILE.name}")
    print(f"   Limit: {'ALL' if not limit else f'{limit:,}'}")

    # Counters
    total_rows = 0
    mep_rows = 0
    new_count = 0
    merged_count = 0
    skipped_count = 0

    # Process CSV
    with open(FL_EVERYONE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader, None)

        # Progress tracking
        batch_size = 10000
        last_report = 0

        for row in reader:
            total_rows += 1

            if limit and total_rows > limit:
                break

            # Progress report every batch_size rows
            if total_rows - last_report >= batch_size:
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"   Processed {total_rows:,} rows ({mep_rows:,} MEP+R) - {rate:.0f} rows/sec")
                last_report = total_rows

            # Skip malformed rows
            if len(row) < 10:
                skipped_count += 1
                continue

            # Extract fields
            license_type = row[0].strip().upper() if row[0] else ""
            name = row[1].strip() if len(row) > 1 else ""
            company = row[2].strip() if len(row) > 2 else ""
            address = row[3].strip() if len(row) > 3 else ""
            city = row[5].strip() if len(row) > 5 else ""
            state = row[6].strip().upper() if len(row) > 6 else "FL"
            zipcode = row[7].strip() if len(row) > 7 else ""
            email = row[9].strip() if len(row) > 9 else ""

            # Only process MEP+R license types
            category = FL_LICENSE_CATEGORIES.get(license_type)
            if not category:
                continue

            mep_rows += 1

            # Build record
            record = {
                'company_name': company if company else name,
                'contact_name': name,
                'address': address,
                'city': city,
                'state': state if state else 'FL',
                'zip': zipcode,
                'email': email,
                'license_type': license_type,
                'license_category': category,
            }

            # Add to database with deduplication
            try:
                _, is_new = db.add_contractor(record, source='FL_License')
                if is_new:
                    new_count += 1
                else:
                    merged_count += 1
            except Exception as e:
                print(f"   ⚠️ Error on row {total_rows}: {e}")
                skipped_count += 1

    # Get final stats
    duration = time.time() - start_time
    stats = db.get_stats(state='FL')

    # Complete pipeline run
    db.complete_pipeline_run(
        run_id,
        records_input=mep_rows,
        records_new=new_count,
        records_merged=merged_count,
        multi_license_found=stats['multi_license'],
        unicorns_found=stats['unicorns'],
        duration_seconds=duration
    )

    # Print results
    print("\n" + "=" * 70)
    print("MIGRATION RESULTS")
    print("=" * 70)
    print(f"Total CSV rows:        {total_rows:,}")
    print(f"MEP+R rows:            {mep_rows:,}")
    print(f"Skipped:               {skipped_count:,}")
    print(f"\nNew contractors:       {new_count:,}")
    print(f"Merged (duplicates):   {merged_count:,}")

    dedup_rate = (merged_count / mep_rows * 100) if mep_rows > 0 else 0
    print(f"Deduplication rate:    {dedup_rate:.1f}%")

    print("\n" + "-" * 40)
    print("DATABASE STATS")
    print("-" * 40)
    print(f"Total contractors:     {stats['total_contractors']:,}")
    print(f"With email:            {stats['with_email']:,}")
    print(f"With phone:            {stats['with_phone']:,}")
    print(f"Multi-license (2+):    {stats['multi_license']:,}")
    print(f"Multi-license + email: {stats['multi_license_with_email']:,}")
    print(f"Unicorns (3+):         {stats['unicorns']:,}")

    print("\nCategory Distribution:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count:,}")

    print(f"\n⏱️  Duration: {duration:.1f} seconds ({mep_rows/duration:.0f} rows/sec)")

    # Validation against expected metrics
    print("\n" + "=" * 70)
    print("VALIDATION VS EXPECTED")
    print("=" * 70)

    expected = {
        'total_contractors': 69795,  # From CSV dedup
        'multi_license_with_email': 11401,
        'unicorns': 1799,
        'dedup_rate': 32.0,
    }

    # Allow some variance since exact match depends on name normalization
    tolerance = 0.05  # 5% tolerance

    for metric, expected_val in expected.items():
        if metric == 'dedup_rate':
            actual = dedup_rate
        elif metric == 'total_contractors':
            actual = stats['total_contractors']
        elif metric == 'multi_license_with_email':
            actual = stats['multi_license_with_email']
        elif metric == 'unicorns':
            actual = stats['unicorns']
        else:
            continue

        variance = abs(actual - expected_val) / expected_val if expected_val > 0 else 0
        status = "✅" if variance <= tolerance else "⚠️"
        diff = actual - expected_val
        diff_pct = variance * 100

        print(f"{status} {metric}: {actual:,} (expected {expected_val:,}, diff: {diff:+,} / {diff_pct:.1f}%)")

    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = OUTPUT_DIR / "enrichment"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export multi-license with email (CSV)
    ml_file = output_dir / f"fl_multi_license_sqlite_{timestamp}.csv"
    ml_count = db.export_multi_license(ml_file, state='FL', min_categories=2, require_email=True)
    logger.info(f"Exported multi-license CSV: {ml_file.name} ({ml_count:,} records)")
    print(f"\n✅ Exported multi-license: {ml_file.name} ({ml_count:,} records)")

    # Export unicorns (CSV)
    unicorn_file = output_dir / f"fl_unicorns_sqlite_{timestamp}.csv"
    uni_count = db.export_unicorns(unicorn_file, state='FL')
    logger.info(f"Exported unicorns CSV: {unicorn_file.name} ({uni_count:,} records)")
    print(f"✅ Exported unicorns: {unicorn_file.name} ({uni_count:,} records)")

    # Export JSON files for API/tracking
    json_dir = OUTPUT_DIR / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    # Multi-license JSON
    ml_json = json_dir / f"fl_multi_license_{timestamp}.json"
    db.export_to_json(ml_json, state='FL', min_categories=2, require_email=True)
    logger.info(f"Exported multi-license JSON: {ml_json.name}")
    print(f"✅ Exported JSON: {ml_json.name}")

    # Stats JSON
    stats_json = json_dir / f"fl_pipeline_stats_{timestamp}.json"
    db.export_stats_to_json(stats_json, state='FL')
    logger.info(f"Exported stats JSON: {stats_json.name}")
    print(f"✅ Exported stats: {stats_json.name}")

    logger.info(f"Migration complete. Database: {DB_PATH}, Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"Log file: {LOG_FILE}")
    print(f"\n📁 Database saved: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"📄 Log file: {LOG_FILE}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate FL license data to SQLite")
    parser.add_argument("--limit", type=int, help="Limit records to process (for testing)")
    parser.add_argument("--reset", action="store_true", help="Reset database before migration")

    args = parser.parse_args()

    migrate_fl_data(limit=args.limit, reset=args.reset)
