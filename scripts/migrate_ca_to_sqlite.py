#!/usr/bin/env python3
"""
Migrate CA CSLB Data to SQLite Pipeline Database

Loads the CA CSLB bulk CSV file into the SQLite database,
running cross-state deduplication against existing FL data.

CA Data Structure:
- LicenseNo, BusinessName, BusinessPhone
- MailingAddress, City, State, County, ZIPCode
- Classifications(s) - pipe-separated (e.g., "A| B| C10| C20")
- PrimaryStatus, IssueDate, ExpirationDate

Expected Results:
- ~67,000 CA contractors loaded
- Cross-state matches with FL identified
- Multi-license CA contractors tagged

Usage:
    python3 scripts/migrate_ca_to_sqlite.py
    python3 scripts/migrate_ca_to_sqlite.py --limit 1000  # Test mode
"""

import csv
import time
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PipelineDB, CA_LICENSE_CATEGORIES

# Configure logging
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"ca_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# CA Data File Location
CA_FILE = Path(__file__).parent.parent / "output" / "state_licenses" / "california" / "ca_cslb_all_20251101.csv"

# Output database (same as FL - cross-state dedup)
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DB_PATH = OUTPUT_DIR / "pipeline.db"


def parse_classifications(cls_string: str) -> list:
    """
    Parse CA classifications string into list.

    Example: "A| B| C10| C20" -> ["A", "B", "C10", "C20"]
    """
    if not cls_string:
        return []
    return [c.strip() for c in cls_string.split('|') if c.strip()]


def migrate_ca_data(limit: int = None, mep_only: bool = True):
    """
    Migrate CA contractor data to SQLite.

    Args:
        limit: Optional limit on records to process (for testing)
        mep_only: If True, only load contractors with MEP+Energy classifications
    """
    print("\n" + "=" * 70)
    print("CA CSLB DATA MIGRATION TO SQLITE")
    print("=" * 70)

    # Check source file
    if not CA_FILE.exists():
        print(f"❌ Source file not found: {CA_FILE}")
        return

    # Initialize database (DO NOT reset - we're adding to FL data)
    print(f"\n📂 Database: {DB_PATH}")
    db = PipelineDB(DB_PATH)
    db.initialize()  # Creates tables if not exist

    # Get pre-migration stats
    pre_stats = db.get_stats()
    print(f"   Pre-migration contractors: {pre_stats['total_contractors']:,}")

    # Start pipeline run
    run_id = db.start_pipeline_run('CA', str(CA_FILE))
    start_time = time.time()

    print(f"\n📖 Loading: {CA_FILE.name}")
    print(f"   Limit: {'ALL' if not limit else f'{limit:,}'}")
    print(f"   MEP Only: {mep_only}")

    # Counters
    total_rows = 0
    mep_rows = 0
    new_count = 0
    merged_count = 0
    skipped_count = 0

    # Process CSV
    with open(CA_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)

        # Progress tracking
        batch_size = 5000
        last_report = 0

        for row in reader:
            total_rows += 1

            if limit and total_rows > limit:
                break

            # Progress report
            if total_rows - last_report >= batch_size:
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"   Processed {total_rows:,} rows ({mep_rows:,} MEP+E) - {rate:.0f} rows/sec")
                last_report = total_rows

            # Skip if not active
            status = row.get('PrimaryStatus', '').strip().upper()
            if status != 'CLEAR':
                skipped_count += 1
                continue

            # Parse classifications
            classifications = parse_classifications(row.get('Classifications(s)', ''))

            # Filter to MEP+Energy if requested
            if mep_only:
                has_mep = any(c in CA_LICENSE_CATEGORIES for c in classifications)
                if not has_mep:
                    continue

            mep_rows += 1

            # Extract fields
            company = row.get('BusinessName', '').strip()
            if not company:
                company = row.get('FullBusinessName', '').strip()

            phone = row.get('BusinessPhone', '').strip()
            address = row.get('MailingAddress', '').strip()
            city = row.get('City', '').strip()
            state = row.get('State', 'CA').strip().upper()
            zipcode = row.get('ZIPCode', '').strip()
            license_no = row.get('LicenseNo', '').strip()

            # Process each classification as a separate license
            for cls in classifications:
                category = CA_LICENSE_CATEGORIES.get(cls, '')
                if not category and mep_only:
                    continue  # Skip non-MEP classifications

                # Build record
                record = {
                    'company_name': company,
                    'address': address,
                    'city': city,
                    'state': state if state else 'CA',
                    'zip': zipcode,
                    'phone': phone,
                    'license_type': cls,
                    'license_category': category if category else cls,
                    'license_number': license_no,
                }

                # Add to database with deduplication
                try:
                    contractor_id, is_new = db.add_contractor(record, source='CA_CSLB')
                    if is_new:
                        new_count += 1
                    else:
                        merged_count += 1
                except Exception as e:
                    logger.error(f"Error on row {total_rows}: {e}")
                    skipped_count += 1

    # Get final stats
    duration = time.time() - start_time
    stats = db.get_stats(state='CA')
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
    print(f"MEP+Energy rows:       {mep_rows:,}")
    print(f"Skipped (inactive):    {skipped_count:,}")
    print(f"\nNew contractors:       {new_count:,}")
    print(f"Merged (duplicates):   {merged_count:,}")

    dedup_rate = (merged_count / mep_rows * 100) if mep_rows > 0 else 0
    print(f"Deduplication rate:    {dedup_rate:.1f}%")

    print("\n" + "-" * 40)
    print("CA-SPECIFIC STATS")
    print("-" * 40)
    print(f"CA contractors:        {stats['total_contractors']:,}")
    print(f"CA with phone:         {stats['with_phone']:,}")
    print(f"CA multi-license:      {stats['multi_license']:,}")
    print(f"CA unicorns (3+):      {stats['unicorns']:,}")

    print("\n" + "-" * 40)
    print("CROSS-STATE ANALYSIS")
    print("-" * 40)
    print(f"(Cross-state contractors will be exported to CSV)")

    print("\n" + "-" * 40)
    print("COMBINED DATABASE STATS")
    print("-" * 40)
    print(f"Total contractors:     {total_stats['total_contractors']:,}")
    print(f"Total with email:      {total_stats['with_email']:,}")
    print(f"Total with phone:      {total_stats['with_phone']:,}")
    print(f"Total multi-license:   {total_stats['multi_license']:,}")
    print(f"Total unicorns:        {total_stats['unicorns']:,}")

    print("\nCA Category Distribution:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count:,}")

    print(f"\n⏱️  Duration: {duration:.1f} seconds ({mep_rows/duration:.0f} rows/sec)")

    # Export CA results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = OUTPUT_DIR / "enrichment"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export CA multi-license
    ca_ml_file = output_dir / f"ca_multi_license_sqlite_{timestamp}.csv"
    ca_ml_count = db.export_multi_license(ca_ml_file, state='CA', min_categories=2, require_email=False)
    print(f"\n✅ Exported CA multi-license: {ca_ml_file.name} ({ca_ml_count:,} records)")

    # Export combined multi-license (FL + CA)
    combined_ml_file = output_dir / f"combined_multi_license_sqlite_{timestamp}.csv"
    combined_ml_count = db.export_multi_license(combined_ml_file, min_categories=2, require_email=False)
    print(f"✅ Exported combined multi-license: {combined_ml_file.name} ({combined_ml_count:,} records)")

    # Export cross-state contractors (in both FL and CA)
    cross_state_file = output_dir / f"cross_state_fl_ca_{timestamp}.csv"
    cross_count = export_cross_state(db, cross_state_file)
    print(f"✅ Exported cross-state (FL+CA): {cross_state_file.name} ({cross_count:,} records)")

    # Export stats JSON
    json_dir = OUTPUT_DIR / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    stats_json = json_dir / f"ca_pipeline_stats_{timestamp}.json"
    db.export_stats_to_json(stats_json, state='CA')
    print(f"✅ Exported CA stats: {stats_json.name}")

    logger.info(f"Migration complete. Database: {DB_PATH}, Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"\n📁 Database saved: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"📄 Log file: {LOG_FILE}")


def export_cross_state(db: PipelineDB, output_path: Path) -> int:
    """
    Export contractors that appear in both FL and CA.
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

    parser = argparse.ArgumentParser(description="Migrate CA CSLB data to SQLite")
    parser.add_argument("--limit", type=int, help="Limit records to process (for testing)")
    parser.add_argument("--all-classifications", action="store_true",
                       help="Load all contractors, not just MEP+Energy")

    args = parser.parse_args()

    migrate_ca_data(limit=args.limit, mep_only=not args.all_classifications)
