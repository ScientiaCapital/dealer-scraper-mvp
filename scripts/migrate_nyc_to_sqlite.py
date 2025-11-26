#!/usr/bin/env python3
"""
Migrate NYC DOB License Data to SQLite Pipeline Database

Loads NYC Department of Buildings license data, excluding General Contractors (G)
per ICP framework (GCs sub out work, don't self-perform).

License Type Mapping (ICP-aligned):
- A = ELECTRICAL (Electrical Contractor)
- P = PLUMBING (Master Plumber)
- O = HVAC (Oil Burner Installer - heating)
- F = FIRE (Fire Suppression Contractor)
- G = EXCLUDED (General Contractor - not self-performing)

Expected Results:
- ~2,440 total licenses
- ~537 excluded (General Contractors)
- ~1,669 ICP-aligned contractors (A + P + O + F)

Usage:
    python3 scripts/migrate_nyc_to_sqlite.py
    python3 scripts/migrate_nyc_to_sqlite.py --dry-run  # Preview without importing
"""

import csv
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PipelineDB

# Configure logging
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"nyc_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# NYC DOB Data File Location
OUTPUT_DIR = Path(__file__).parent.parent / "output"
NYC_DOB_FILE = OUTPUT_DIR / "_archive" / "2025-11-26_pre_cleanup" / "state_licenses" / "new_york" / "nyc_dob" / "nyc_active_licenses_20251125_220711.csv"
DB_PATH = OUTPUT_DIR / "master" / "pipeline.db"


# NYC DOB License Type Mapping (ICP-aligned trades only)
# Per ICP Framework: INCLUDE self-performing MEP+E trades, EXCLUDE General Contractors
NYC_LICENSE_CATEGORIES = {
    'A': 'ELECTRICAL',   # Electrical Contractor
    'P': 'PLUMBING',     # Master Plumber
    'O': 'HVAC',         # Oil Burner Installer (heating)
    'F': 'FIRE',         # Fire Suppression Contractor
    # 'G' intentionally excluded - General Contractors sub out work
    # 'K' excluded - Energy Auditor (not installer)
}

# License types to EXCLUDE (per ICP framework)
EXCLUDED_LICENSE_TYPES = {
    'G': 'GENERAL',      # General Contractor - subs out MEP work
    'K': 'AUDITOR',      # Energy Auditor - not installer
}


def migrate_nyc_data(dry_run: bool = False, limit: int = None):
    """
    Migrate NYC DOB contractor data to SQLite.

    Args:
        dry_run: If True, show what would be imported without writing
        limit: Optional limit on records to process (for testing)
    """
    print("\n" + "=" * 70)
    print("NYC DOB LICENSE DATA MIGRATION TO SQLITE")
    print("=" * 70)

    # Check source file - try multiple locations
    source_file = NYC_DOB_FILE
    if not source_file.exists():
        alt_file = OUTPUT_DIR / "state_licenses" / "new_york" / "nyc_dob" / "nyc_active_licenses_20251125_220711.csv"
        if alt_file.exists():
            source_file = alt_file
        else:
            print(f"❌ Source file not found: {NYC_DOB_FILE}")
            print(f"   Or alternate: {alt_file}")
            return

    print(f"📂 Source: {source_file.name}")
    print(f"📂 Database: {DB_PATH}")
    print(f"🔍 Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE IMPORT'}")

    # Initialize database
    if not dry_run:
        db = PipelineDB(DB_PATH)
        db.initialize()
        run_id = db.start_pipeline_run('NYC_DOB', str(source_file))

    start_time = time.time()

    # Counters
    total_rows = 0
    included_rows = 0
    excluded_gc = 0
    excluded_other = 0
    new_count = 0
    merged_count = 0
    skipped_count = 0

    # Category tracking
    category_counts = {}

    print(f"\n📖 Processing: {source_file.name}")
    print(f"   Limit: {'ALL' if not limit else f'{limit:,}'}")
    print()

    # ICP filtering summary
    print("🎯 ICP FILTERING:")
    print("   ✅ INCLUDE: A (Electrical), P (Plumbing), O (HVAC), F (Fire)")
    print("   ❌ EXCLUDE: G (General Contractors - sub out work)")
    print()

    # Process CSV
    with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_rows += 1

            if limit and total_rows > limit:
                break

            # Get license type code
            license_type_code = row.get('license_type_code', '').strip().upper()
            license_type = row.get('license_type', '').strip()

            # ICP FILTER: Exclude General Contractors
            if license_type_code == 'G':
                excluded_gc += 1
                continue

            # Skip unknown license types
            if license_type_code not in NYC_LICENSE_CATEGORIES:
                excluded_other += 1
                continue

            included_rows += 1

            # Get category
            category = NYC_LICENSE_CATEGORIES[license_type_code]
            category_counts[category] = category_counts.get(category, 0) + 1

            # Extract fields
            licensee_name = row.get('licensee_name', '').strip()
            license_number = row.get('license_number', '').strip()
            business_1 = row.get('business_1', '').strip()
            business_2 = row.get('business_2', '').strip()
            status = row.get('status', '').strip()
            expiration = row.get('expiration_date', '').strip()

            # Use business name as company, fall back to licensee name
            company_name = business_1 if business_1 else business_2 if business_2 else licensee_name

            # Skip if no company name
            if not company_name:
                skipped_count += 1
                continue

            # Build record
            record = {
                'company_name': company_name,
                'contact_name': licensee_name,
                'city': 'New York',
                'state': 'NY',
                'license_type': f"NYC_{license_type_code}",  # e.g. NYC_A, NYC_P
                'license_category': category,
                'license_number': license_number,
            }

            if dry_run:
                if total_rows <= 10:
                    print(f"   [{license_type_code}→{category}] {company_name[:50]}")
                new_count += 1
            else:
                # Add to database with deduplication
                try:
                    _, is_new = db.add_contractor(record, source='NYC_DOB')
                    if is_new:
                        new_count += 1
                    else:
                        merged_count += 1
                except Exception as e:
                    logger.warning(f"Error on row {total_rows}: {e}")
                    skipped_count += 1

    # Get final stats
    duration = time.time() - start_time

    # Complete pipeline run
    if not dry_run:
        stats = db.get_stats(state='NY')
        db.complete_pipeline_run(
            run_id,
            records_input=included_rows,
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
    print(f"\n🎯 ICP FILTERING:")
    print(f"   ❌ Excluded (GC):   {excluded_gc:,} (sub out work)")
    print(f"   ❌ Excluded (other):{excluded_other:,}")
    print(f"   ✅ ICP-aligned:     {included_rows:,}")

    icp_rate = (included_rows / total_rows * 100) if total_rows > 0 else 0
    gc_rate = (excluded_gc / total_rows * 100) if total_rows > 0 else 0
    print(f"\n   ICP alignment:      {icp_rate:.1f}%")
    print(f"   GC exclusion:       {gc_rate:.1f}%")

    print(f"\n📊 IMPORT RESULTS:")
    print(f"   New contractors:    {new_count:,}")
    print(f"   Merged (duplicates):{merged_count:,}")
    print(f"   Skipped:            {skipped_count:,}")

    dedup_rate = (merged_count / included_rows * 100) if included_rows > 0 else 0
    print(f"   Deduplication rate: {dedup_rate:.1f}%")

    print("\n📋 CATEGORY BREAKDOWN:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count:,}")

    if not dry_run:
        print("\n" + "-" * 40)
        print("DATABASE STATS (NY)")
        print("-" * 40)
        print(f"Total contractors:     {stats['total_contractors']:,}")
        print(f"With email:            {stats['with_email']:,}")
        print(f"With phone:            {stats['with_phone']:,}")
        print(f"Multi-license (2+):    {stats['multi_license']:,}")
        print(f"Unicorns (3+):         {stats['unicorns']:,}")

    print(f"\n⏱️  Duration: {duration:.1f} seconds")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  DRY RUN - No data written. Run without --dry-run to import.")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate NYC DOB license data to SQLite (excludes General Contractors per ICP)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview import without writing to database")
    parser.add_argument("--limit", type=int,
                        help="Limit records to process (for testing)")
    args = parser.parse_args()

    migrate_nyc_data(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
