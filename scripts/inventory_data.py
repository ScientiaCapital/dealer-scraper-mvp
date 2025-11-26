#!/usr/bin/env python3
"""
Data Inventory Script

Scans all data sources (SQLite, CSV files) and populates the data_inventory
table for observability tracking.

Usage:
    python scripts/inventory_data.py
    python scripts/inventory_data.py --db-path output/master/pipeline.db
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def inventory_contractors_table(conn: sqlite3.Connection) -> list:
    """
    Inventory contractors table by source_type.

    Returns list of dicts with inventory data.
    """
    cursor = conn.cursor()
    results = []

    # Get stats by source_type
    cursor.execute("""
        SELECT
            source_type,
            COUNT(*) as total,
            SUM(CASE WHEN primary_email IS NOT NULL AND primary_email != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN primary_phone IS NOT NULL AND primary_phone != '' THEN 1 ELSE 0 END) as with_phone,
            MAX(updated_at) as last_updated
        FROM contractors
        WHERE is_deleted = 0 OR is_deleted IS NULL
        GROUP BY source_type
    """)

    for row in cursor.fetchall():
        source_type = row['source_type'] or 'unknown'
        total = row['total']
        with_email = row['with_email']
        with_phone = row['with_phone']

        # Calculate quality score (0-100)
        email_pct = (with_email / total * 100) if total > 0 else 0
        phone_pct = (with_phone / total * 100) if total > 0 else 0
        quality_score = int((email_pct * 0.5) + (phone_pct * 0.5))

        results.append({
            "source_name": source_type,
            "source_type": "CONTRACTOR_DB",
            "record_count": total,
            "with_email_count": with_email,
            "with_phone_count": with_phone,
            "states_covered": None,  # Will be populated separately
            "quality_score": quality_score,
            "notes": f"From contractors table (source_type={source_type})"
        })

    return results


def inventory_state_licenses(conn: sqlite3.Connection) -> list:
    """
    Inventory licenses table by state.

    Returns list of dicts with inventory data.
    """
    cursor = conn.cursor()
    results = []

    # Get license counts by state
    cursor.execute("""
        SELECT
            l.state,
            COUNT(DISTINCT l.contractor_id) as contractor_count,
            COUNT(*) as license_count,
            GROUP_CONCAT(DISTINCT l.license_category) as categories
        FROM licenses l
        JOIN contractors c ON l.contractor_id = c.id
        WHERE c.is_deleted = 0 OR c.is_deleted IS NULL
        GROUP BY l.state
        ORDER BY contractor_count DESC
    """)

    for row in cursor.fetchall():
        state = row['state']
        if not state:
            continue

        results.append({
            "source_name": f"{state.lower()}_license",
            "source_type": "STATE_LICENSE",
            "record_count": row['contractor_count'],
            "with_email_count": 0,  # Would need JOIN to get this
            "with_phone_count": 0,  # Would need JOIN to get this
            "states_covered": json.dumps([state]),
            "quality_score": 50,  # Default for state licenses
            "notes": f"{row['license_count']} licenses, categories: {row['categories']}"
        })

    return results


def inventory_oem_certifications(conn: sqlite3.Connection) -> list:
    """
    Inventory OEM certifications by OEM name.

    Returns list of dicts with inventory data.
    """
    cursor = conn.cursor()
    results = []

    # Get OEM certification counts
    cursor.execute("""
        SELECT
            o.oem_name,
            COUNT(DISTINCT o.contractor_id) as contractor_count,
            COUNT(*) as certification_count
        FROM oem_certifications o
        JOIN contractors c ON o.contractor_id = c.id
        WHERE c.is_deleted = 0 OR c.is_deleted IS NULL
        GROUP BY o.oem_name
        ORDER BY contractor_count DESC
    """)

    for row in cursor.fetchall():
        oem_name = row['oem_name']
        if not oem_name:
            continue

        results.append({
            "source_name": oem_name.lower().replace(" ", "_"),
            "source_type": "OEM",
            "record_count": row['contractor_count'],
            "with_email_count": 0,
            "with_phone_count": 0,
            "states_covered": None,
            "quality_score": 70,  # OEM dealers typically have good data
            "notes": f"{row['certification_count']} certifications from {oem_name}"
        })

    return results


def inventory_csv_files(output_dir: Path) -> list:
    """
    Inventory CSV files in output/oem_data/ directory.

    Returns list of dicts with inventory data.
    """
    results = []
    oem_data_dir = output_dir / "oem_data"

    if not oem_data_dir.exists():
        print(f"  ⚠️  OEM data directory not found: {oem_data_dir}")
        return results

    import csv

    for oem_dir in oem_data_dir.iterdir():
        if not oem_dir.is_dir():
            continue

        oem_name = oem_dir.name
        total_records = 0
        with_email = 0
        with_phone = 0
        states = set()

        # Count records in all CSV files for this OEM
        for csv_file in oem_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total_records += 1

                        # Check for email
                        email = row.get('email') or row.get('Email') or row.get('primary_email')
                        if email and email.strip() and '@' in email:
                            with_email += 1

                        # Check for phone
                        phone = row.get('phone') or row.get('Phone') or row.get('primary_phone')
                        if phone and phone.strip():
                            with_phone += 1

                        # Track states
                        state = row.get('state') or row.get('State')
                        if state:
                            states.add(state.upper()[:2])

            except Exception as e:
                print(f"  ⚠️  Error reading {csv_file}: {e}")

        if total_records > 0:
            # Calculate quality score
            email_pct = (with_email / total_records * 100)
            phone_pct = (with_phone / total_records * 100)
            quality_score = int((email_pct * 0.5) + (phone_pct * 0.5))

            results.append({
                "source_name": oem_name,
                "source_type": "OEM_CSV",
                "record_count": total_records,
                "with_email_count": with_email,
                "with_phone_count": with_phone,
                "states_covered": json.dumps(sorted(states)) if states else None,
                "quality_score": quality_score,
                "notes": f"From CSV files in output/oem_data/{oem_name}/"
            })

    return results


def inventory_spw_rankings(conn: sqlite3.Connection) -> list:
    """
    Inventory SPW rankings table.

    Returns list of dicts with inventory data.
    """
    cursor = conn.cursor()
    results = []

    # Check if spw_rankings table has data
    cursor.execute("SELECT COUNT(*) as count FROM spw_rankings")
    count = cursor.fetchone()['count']

    if count > 0:
        cursor.execute("""
            SELECT
                list_name,
                COUNT(*) as count,
                SUM(CASE WHEN contractor_id IS NOT NULL THEN 1 ELSE 0 END) as matched
            FROM spw_rankings
            GROUP BY list_name
        """)

        for row in cursor.fetchall():
            results.append({
                "source_name": f"spw_{row['list_name'].lower().replace(' ', '_')}",
                "source_type": "THIRD_PARTY",
                "record_count": row['count'],
                "with_email_count": 0,
                "with_phone_count": 0,
                "states_covered": None,
                "quality_score": 90,  # SPW is high quality curated data
                "notes": f"{row['matched']} matched to contractors"
            })

    return results


def populate_data_inventory(conn: sqlite3.Connection, inventory_items: list, dry_run: bool = False):
    """Populate data_inventory table with inventory items."""
    cursor = conn.cursor()

    print(f"\n📊 Populating data_inventory with {len(inventory_items)} sources...")

    inserted = 0
    updated = 0

    for item in inventory_items:
        try:
            if dry_run:
                print(f"  [DRY RUN] Would upsert: {item['source_name']} ({item['source_type']})")
                inserted += 1
            else:
                # Try to update existing record first
                cursor.execute("""
                    UPDATE data_inventory SET
                        record_count = ?,
                        with_email_count = ?,
                        with_phone_count = ?,
                        states_covered = ?,
                        last_updated = ?,
                        quality_score = ?,
                        notes = ?
                    WHERE source_name = ? AND source_type = ?
                """, (
                    item["record_count"],
                    item["with_email_count"],
                    item["with_phone_count"],
                    item["states_covered"],
                    datetime.now().isoformat(),
                    item["quality_score"],
                    item["notes"],
                    item["source_name"],
                    item["source_type"],
                ))

                if cursor.rowcount > 0:
                    print(f"  ↻ Updated: {item['source_name']} ({item['source_type']}) - {item['record_count']:,} records")
                    updated += 1
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO data_inventory
                        (source_name, source_type, record_count, with_email_count,
                         with_phone_count, states_covered, last_updated, quality_score, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item["source_name"],
                        item["source_type"],
                        item["record_count"],
                        item["with_email_count"],
                        item["with_phone_count"],
                        item["states_covered"],
                        datetime.now().isoformat(),
                        item["quality_score"],
                        item["notes"],
                    ))
                    print(f"  ✓ Inserted: {item['source_name']} ({item['source_type']}) - {item['record_count']:,} records")
                    inserted += 1

        except Exception as e:
            print(f"  ✗ Error with {item['source_name']}: {e}")

    if not dry_run:
        conn.commit()

    return inserted, updated


def print_summary(conn: sqlite3.Connection):
    """Print summary of data inventory."""
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("DATA INVENTORY SUMMARY")
    print("=" * 60)

    # Count by type
    cursor.execute("""
        SELECT
            source_type,
            COUNT(*) as sources,
            SUM(record_count) as total_records,
            SUM(with_email_count) as with_email,
            SUM(with_phone_count) as with_phone,
            ROUND(AVG(quality_score), 1) as avg_quality
        FROM data_inventory
        GROUP BY source_type
        ORDER BY total_records DESC
    """)

    print("\nBy Source Type:")
    grand_total = 0
    for row in cursor.fetchall():
        total = row['total_records'] or 0
        grand_total += total
        print(f"  {row['source_type']}: {row['sources']} sources, {total:,} records "
              f"(📧 {row['with_email'] or 0:,} | 📞 {row['with_phone'] or 0:,} | ⭐ {row['avg_quality']}%)")

    print(f"\nGrand Total: {grand_total:,} records across all sources")

    # Freshness report
    cursor.execute("""
        SELECT
            source_name,
            source_type,
            record_count,
            quality_score,
            CAST(julianday('now') - julianday(last_updated) AS INTEGER) as days_old
        FROM data_inventory
        ORDER BY days_old DESC
        LIMIT 10
    """)

    print("\nData Freshness (oldest first):")
    for row in cursor.fetchall():
        days = row['days_old'] or 0
        status = "🟢 FRESH" if days <= 7 else "🟡 STALE" if days <= 30 else "🔴 OUTDATED"
        print(f"  {status} {row['source_name']}: {days} days old ({row['record_count']:,} records)")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Inventory all data sources")
    parser.add_argument("--db-path", default="output/master/pipeline.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    args = parser.parse_args()

    print("📊 Data Inventory Tool")
    print("=" * 60)

    # Check database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found: {args.db_path}")
        sys.exit(1)

    print(f"Database: {args.db_path}")

    # Connect
    conn = get_db_connection(args.db_path)

    try:
        all_inventory = []

        # 1. Inventory contractors table
        print("\n1️⃣ Inventorying contractors table...")
        contractor_items = inventory_contractors_table(conn)
        print(f"   Found {len(contractor_items)} source types")
        all_inventory.extend(contractor_items)

        # 2. Inventory state licenses
        print("\n2️⃣ Inventorying state licenses...")
        license_items = inventory_state_licenses(conn)
        print(f"   Found {len(license_items)} states with licenses")
        all_inventory.extend(license_items)

        # 3. Inventory OEM certifications
        print("\n3️⃣ Inventorying OEM certifications...")
        oem_items = inventory_oem_certifications(conn)
        print(f"   Found {len(oem_items)} OEMs with certifications")
        all_inventory.extend(oem_items)

        # 4. Inventory CSV files
        print("\n4️⃣ Inventorying OEM CSV files...")
        output_dir = Path(args.db_path).parent.parent
        csv_items = inventory_csv_files(output_dir)
        print(f"   Found {len(csv_items)} OEM CSV directories")
        all_inventory.extend(csv_items)

        # 5. Inventory SPW rankings
        print("\n5️⃣ Inventorying SPW rankings...")
        spw_items = inventory_spw_rankings(conn)
        print(f"   Found {len(spw_items)} SPW lists")
        all_inventory.extend(spw_items)

        # Populate inventory table
        inserted, updated = populate_data_inventory(conn, all_inventory, dry_run=args.dry_run)

        print(f"\n✅ Inventory complete: {inserted} inserted, {updated} updated")

        # Print summary
        if not args.dry_run:
            print_summary(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
