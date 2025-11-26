#!/usr/bin/env python3
"""
Migrate TX TDLR Data to SQLite Pipeline Database

Loads the TX TDLR bulk CSV file into the SQLite database,
running cross-state deduplication against existing FL and CA data.

TX Data Structure (TDLR):
- LICENSE TYPE, LICENSE NUMBER, LICENSE EXPIRATION DATE
- NAME (individual), BUSINESS NAME
- PHONE NUMBER, BUSINESS PHONE
- BUSINESS ADDRESS-LINE1, BUSINESS ADDRESS-LINE2
- BUSINESS CITY, STATE ZIP, BUSINESS ZIP
- LICENSE SUBTYPE

ICP Framework Filtering:
- INCLUDE: A/C Contractor, A/C Technician, Electrical Contractor,
           Master Electrician, Residential Wireman, Appliance Installation Contractor
- EXCLUDE: Journeyman Electrician, Apprentice Electrician (employees, not owners)

Expected Results:
- ~113,000 TX MEP records (after excluding journeymen)
- ~40-60K unique after deduplication
- Cross-state matches with FL and CA identified

Usage:
    python3 scripts/migrate_tx_to_sqlite.py
    python3 scripts/migrate_tx_to_sqlite.py --limit 1000  # Test mode
"""

import csv
import time
import logging
import re
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PipelineDB, TX_LICENSE_CATEGORIES

# Configure logging
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"tx_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# TX Data File Location
TX_FILE = Path(__file__).parent.parent / "output" / "state_licenses" / "texas" / "tx_tdlr_all_licenses_full.csv"

# Output database (same as FL/CA - cross-state dedup)
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DB_PATH = OUTPUT_DIR / "pipeline.db"


def parse_city_state_zip(city_state_zip: str) -> tuple:
    """
    Parse TX TDLR city/state/zip format.

    Example: "HOUSTON, TX 77002" -> ("HOUSTON", "TX", "77002")
    """
    if not city_state_zip:
        return "", "", ""

    city_state_zip = city_state_zip.strip()

    # Try pattern: "CITY, ST ZIP"
    match = re.match(r'^(.+?),?\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', city_state_zip)
    if match:
        return match.group(1).strip().rstrip(','), match.group(2), match.group(3)

    # Try pattern: "CITY, ST" (no ZIP)
    match = re.match(r'^(.+?),?\s+([A-Z]{2})$', city_state_zip)
    if match:
        return match.group(1).strip().rstrip(','), match.group(2), ""

    # Fallback - return as city
    return city_state_zip, "", ""


def migrate_tx_data(limit: int = None, mep_only: bool = True):
    """
    Migrate TX contractor data to SQLite.

    Args:
        limit: Optional limit on records to process (for testing)
        mep_only: If True, only load contractors with MEP license types
    """
    print("\n" + "=" * 70)
    print("TX TDLR DATA MIGRATION TO SQLITE")
    print("=" * 70)

    # Check source file
    if not TX_FILE.exists():
        print(f"Source file not found: {TX_FILE}")
        return

    # Initialize database (DO NOT reset - we're adding to FL+CA data)
    print(f"\n Database: {DB_PATH}")
    db = PipelineDB(DB_PATH)
    db.initialize()  # Creates tables if not exist

    # Get pre-migration stats
    pre_stats = db.get_stats()
    print(f"   Pre-migration contractors: {pre_stats['total_contractors']:,}")

    # Start pipeline run
    run_id = db.start_pipeline_run('TX', str(TX_FILE))
    start_time = time.time()

    print(f"\n Loading: {TX_FILE.name}")
    print(f"   Limit: {'ALL' if not limit else f'{limit:,}'}")
    print(f"   MEP Only: {mep_only}")
    print(f"\n   ICP Filter: {', '.join(TX_LICENSE_CATEGORIES.keys())}")

    # Counters
    total_rows = 0
    mep_rows = 0
    new_count = 0
    merged_count = 0
    skipped_count = 0
    license_type_counts = {}

    # Process CSV
    with open(TX_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)

        # Progress tracking
        batch_size = 10000
        last_report = 0

        for row in reader:
            total_rows += 1

            if limit and total_rows > limit:
                break

            # Progress report
            if total_rows - last_report >= batch_size:
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"   Processed {total_rows:,} rows ({mep_rows:,} MEP) - {rate:.0f} rows/sec")
                last_report = total_rows

            # Get license type
            license_type = row.get('LICENSE TYPE', '').strip()

            # Track all license types for debugging
            license_type_counts[license_type] = license_type_counts.get(license_type, 0) + 1

            # Filter to MEP only
            if mep_only:
                if license_type not in TX_LICENSE_CATEGORIES:
                    continue

            mep_rows += 1

            # Get category from mapping
            category = TX_LICENSE_CATEGORIES.get(license_type, '')

            # Extract company name (prefer BUSINESS NAME over NAME)
            company = row.get('BUSINESS NAME', '').strip()
            if not company:
                company = row.get('NAME', '').strip()

            # Skip if no company name
            if not company:
                skipped_count += 1
                continue

            # Extract phone (prefer BUSINESS PHONE over PHONE NUMBER)
            phone = row.get('BUSINESS PHONE', '').strip()
            if not phone:
                phone = row.get('PHONE NUMBER', '').strip()

            # Extract address
            address1 = row.get('BUSINESS ADDRESS-LINE1', '').strip()
            address2 = row.get('BUSINESS ADDRESS-LINE2', '').strip()
            address = f"{address1} {address2}".strip() if address2 else address1

            # Extract city/state/zip from combined field
            city_state_zip = row.get('BUSINESS CITY, STATE ZIP', '').strip()
            city, state, zipcode = parse_city_state_zip(city_state_zip)

            # Fallback to separate ZIP field if available
            if not zipcode:
                zipcode = row.get('BUSINESS ZIP', '').strip()

            # Default state to TX
            if not state:
                state = 'TX'

            # License number
            license_no = row.get('LICENSE NUMBER', '').strip()

            # Build record
            record = {
                'company_name': company,
                'address': address,
                'city': city,
                'state': state,
                'zip': zipcode,
                'phone': phone,
                'license_type': license_type,
                'license_category': category,
                'license_number': license_no,
            }

            # Add to database with deduplication
            try:
                contractor_id, is_new = db.add_contractor(record, source='TX_TDLR')
                if is_new:
                    new_count += 1
                else:
                    merged_count += 1
            except Exception as e:
                logger.error(f"Error on row {total_rows}: {e}")
                skipped_count += 1

    # Get final stats
    duration = time.time() - start_time
    stats = db.get_stats(state='TX')
    total_stats = db.get_stats()

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
    print(f"MEP rows:              {mep_rows:,}")
    print(f"Skipped (no name):     {skipped_count:,}")
    print(f"\nNew contractors:       {new_count:,}")
    print(f"Merged (duplicates):   {merged_count:,}")

    dedup_rate = (merged_count / mep_rows * 100) if mep_rows > 0 else 0
    print(f"Deduplication rate:    {dedup_rate:.1f}%")

    print("\n" + "-" * 40)
    print("TX-SPECIFIC STATS")
    print("-" * 40)
    print(f"TX contractors:        {stats['total_contractors']:,}")
    print(f"TX with phone:         {stats['with_phone']:,}")
    print(f"TX multi-license:      {stats['multi_license']:,}")
    print(f"TX unicorns (3+):      {stats['unicorns']:,}")

    print("\n" + "-" * 40)
    print("COMBINED DATABASE STATS (FL + CA + TX)")
    print("-" * 40)
    print(f"Total contractors:     {total_stats['total_contractors']:,}")
    print(f"Total with email:      {total_stats['with_email']:,}")
    print(f"Total with phone:      {total_stats['with_phone']:,}")
    print(f"Total multi-license:   {total_stats['multi_license']:,}")
    print(f"Total unicorns:        {total_stats['unicorns']:,}")

    print("\nTX License Type Distribution:")
    for lt in sorted(TX_LICENSE_CATEGORIES.keys()):
        count = license_type_counts.get(lt, 0)
        cat = TX_LICENSE_CATEGORIES[lt]
        print(f"   {lt}: {count:,} ({cat})")

    print(f"\n Duration: {duration:.1f} seconds ({mep_rows/duration:.0f} rows/sec)")

    # Export TX results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = OUTPUT_DIR / "enrichment"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export TX multi-license
    tx_ml_file = output_dir / f"tx_multi_license_sqlite_{timestamp}.csv"
    tx_ml_count = db.export_multi_license(tx_ml_file, state='TX', min_categories=2, require_email=False)
    print(f"\n Exported TX multi-license: {tx_ml_file.name} ({tx_ml_count:,} records)")

    # Export combined multi-license (FL + CA + TX)
    combined_ml_file = output_dir / f"combined_multi_license_sqlite_{timestamp}.csv"
    combined_ml_count = db.export_multi_license(combined_ml_file, min_categories=2, require_email=False)
    print(f" Exported combined multi-license: {combined_ml_file.name} ({combined_ml_count:,} records)")

    # Export cross-state contractors (in multiple states)
    cross_state_file = output_dir / f"cross_state_fl_ca_tx_{timestamp}.csv"
    cross_count = export_cross_state(db, cross_state_file)
    print(f" Exported cross-state (FL+CA+TX): {cross_state_file.name} ({cross_count:,} records)")

    # Export stats JSON
    json_dir = OUTPUT_DIR / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    stats_json = json_dir / f"tx_pipeline_stats_{timestamp}.json"
    db.export_stats_to_json(stats_json, state='TX')
    print(f" Exported TX stats: {stats_json.name}")

    logger.info(f"Migration complete. Database: {DB_PATH}, Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"\n Database saved: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f" Log file: {LOG_FILE}")


def export_cross_state(db: PipelineDB, output_path: Path) -> int:
    """
    Export contractors that appear in multiple states (FL, CA, TX).
    These are multi-state operations = highest ICP value.
    """
    query = """
    SELECT
        c.id,
        c.company_name,
        c.city,
        c.state,
        c.zip,
        c.primary_phone,
        c.primary_email,
        GROUP_CONCAT(DISTINCT l.state) as licensed_states,
        COUNT(DISTINCT l.state) as state_count,
        GROUP_CONCAT(DISTINCT l.license_category) as categories,
        COUNT(DISTINCT l.license_category) as category_count
    FROM contractors c
    JOIN licenses l ON c.id = l.contractor_id
    GROUP BY c.id
    HAVING state_count >= 2
    ORDER BY state_count DESC, category_count DESC
    """

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

    if not rows:
        return 0

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id', 'company_name', 'city', 'state', 'zip',
            'primary_phone', 'primary_email', 'licensed_states',
            'state_count', 'categories', 'category_count'
        ])
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate TX TDLR data to SQLite")
    parser.add_argument("--limit", type=int, help="Limit records to process (for testing)")
    parser.add_argument("--all-types", action="store_true",
                       help="Load all license types, not just MEP (ICP filtered)")

    args = parser.parse_args()

    migrate_tx_data(limit=args.limit, mep_only=not args.all_types)
