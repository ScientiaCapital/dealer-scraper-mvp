#!/usr/bin/env python3
"""
Export Colorado Multi-Trade PLATINUM Leads

Exports the 105 CO multi-trade BUSINESS entities (excluding individuals)
discovered on Dec 24, 2025. These are PLATINUM ICP tier contractors with
2+ license types (EC+PC combos).

Outputs:
  - output/co_multi_trade_platinum.csv (for sales review)
  - output/co_multi_trade_platinum.json (for Supabase push)
  - output/co_multi_trade_summary.txt (summary stats)

Usage:
    python scripts/export_co_multi_trade.py
    python scripts/export_co_multi_trade.py --db-path /custom/path/pipeline.db
"""

import argparse
import csv
import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths (main repo, not worktree)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "Desktop/tk_projects/dealer-scraper-mvp/output/pipeline.db"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "Desktop/tk_projects/dealer-scraper-mvp/output"


def is_business_entity(company_name: str) -> bool:
    """
    Detect if company name is a business entity (not an individual).

    Business patterns:
    - Contains LLC, INC, CORP, LTD
    - ALL CAPS (e.g., "TIC - THE INDUSTRIAL COMPANY")
    - Contains & (e.g., "Smith & Sons")

    Individual patterns (EXCLUDE):
    - Firstname Lastname (e.g., "John Smith")
    """
    if not company_name:
        return False

    name_upper = company_name.upper()

    # Business indicators
    business_keywords = ['LLC', 'INC', 'CORP', 'LTD', 'COMPANY', 'COMPANIES',
                         'CONTRACTORS', 'CORPORATION', 'INCORPORATED']

    if any(keyword in name_upper for keyword in business_keywords):
        return True

    if '&' in company_name:
        return True

    # ALL CAPS is typically a business (unless it's 2 words)
    if company_name == company_name.upper() and len(company_name.split()) > 2:
        return True

    # Exclude "Firstname Lastname" pattern (individual contractors)
    # Example: "John Smith", "Mary Johnson"
    parts = company_name.split()
    if len(parts) == 2:
        # Check if both parts are capitalized words (likely firstname lastname)
        if parts[0][0].isupper() and parts[0][1:].islower() and \
           parts[1][0].isupper() and parts[1][1:].islower():
            return False

    return True


def export_co_multi_trade(db_path: Path, output_dir: Path) -> Dict:
    """
    Export Colorado multi-trade business entities.

    Args:
        db_path: Path to pipeline.db
        output_dir: Directory to save exports

    Returns:
        Dict with export stats
    """
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # SQL query for multi-trade contractors in Colorado
    query = """
    SELECT DISTINCT
        c.company_name,
        c.street,
        c.city,
        c.state,
        c.zip,
        c.primary_phone,
        c.primary_email,
        c.website_url,
        COUNT(DISTINCT l.license_type) as trade_count,
        GROUP_CONCAT(DISTINCT l.license_type) as license_types
    FROM contractors c
    JOIN licenses l ON c.id = l.contractor_id
    WHERE c.state = 'CO'
      AND c.source_type = 'state_license'
    GROUP BY c.id
    HAVING trade_count >= 2
    ORDER BY trade_count DESC, c.company_name
    """

    logger.info("Querying multi-trade contractors...")
    cursor.execute(query)
    rows = cursor.fetchall()

    logger.info(f"Found {len(rows)} total multi-trade contractors (businesses + individuals)")

    # Filter to business entities only
    businesses = []
    individuals = []

    for row in rows:
        company_name = row['company_name']

        if is_business_entity(company_name):
            businesses.append(dict(row))
        else:
            individuals.append(company_name)

    logger.info(f"Filtered to {len(businesses)} business entities")
    logger.info(f"Excluded {len(individuals)} individuals")

    if len(individuals) > 0:
        logger.info(f"Sample individuals excluded: {individuals[:5]}")

    # Prepare output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export to CSV
    csv_path = output_dir / "co_multi_trade_platinum.csv"
    logger.info(f"Exporting to CSV: {csv_path}")

    with open(csv_path, 'w', newline='') as csvfile:
        if businesses:
            fieldnames = businesses[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(businesses)

    logger.info(f"✅ CSV export complete: {len(businesses)} rows")

    # Export to JSON
    json_path = output_dir / "co_multi_trade_platinum.json"
    logger.info(f"Exporting to JSON: {json_path}")

    with open(json_path, 'w') as jsonfile:
        json.dump(businesses, jsonfile, indent=2, default=str)

    logger.info(f"✅ JSON export complete")

    # Generate summary stats
    license_combos = Counter()
    for biz in businesses:
        licenses = biz['license_types']
        license_combos[licenses] += 1

    summary_path = output_dir / "co_multi_trade_summary.txt"
    logger.info(f"Generating summary: {summary_path}")

    with open(summary_path, 'w') as f:
        f.write(f"Colorado Multi-Trade PLATINUM Leads Export\n")
        f.write(f"=" * 60 + "\n")
        f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"Total multi-trade contractors: {len(rows)}\n")
        f.write(f"Business entities: {len(businesses)}\n")
        f.write(f"Individuals (excluded): {len(individuals)}\n\n")

        f.write(f"License Combinations (Top 10):\n")
        f.write(f"-" * 60 + "\n")
        for combo, count in license_combos.most_common(10):
            f.write(f"  {combo}: {count} contractors\n")

        f.write(f"\n")
        f.write(f"Output Files:\n")
        f.write(f"-" * 60 + "\n")
        f.write(f"  CSV:  {csv_path}\n")
        f.write(f"  JSON: {json_path}\n")
        f.write(f"\n")
        f.write(f"Sample Businesses (Top 10):\n")
        f.write(f"-" * 60 + "\n")
        for biz in businesses[:10]:
            f.write(f"  {biz['company_name']} ({biz['trade_count']} trades)\n")
            f.write(f"    Licenses: {biz['license_types']}\n")

    logger.info(f"✅ Summary complete")

    # Print summary to console
    print("\n" + "=" * 60)
    print("Colorado Multi-Trade PLATINUM Leads Export")
    print("=" * 60)
    print(f"Total multi-trade contractors: {len(rows)}")
    print(f"Business entities: {len(businesses)}")
    print(f"Individuals (excluded): {len(individuals)}")
    print()
    print("Top License Combinations:")
    for combo, count in license_combos.most_common(5):
        print(f"  {combo}: {count} contractors")
    print()
    print("Output Files:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  Summary: {summary_path}")
    print("=" * 60 + "\n")

    conn.close()

    return {
        'total_multi_trade': len(rows),
        'businesses': len(businesses),
        'individuals_excluded': len(individuals),
        'csv_path': str(csv_path),
        'json_path': str(json_path),
        'summary_path': str(summary_path)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Export Colorado multi-trade PLATINUM leads"
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to pipeline.db (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )

    args = parser.parse_args()

    # Validate database exists
    if not args.db_path.exists():
        logger.error(f"Database not found: {args.db_path}")
        logger.info("Tip: Make sure you're pointing to the main repo, not the worktree")
        return 1

    # Run export
    try:
        stats = export_co_multi_trade(args.db_path, args.output_dir)

        logger.info("=" * 60)
        logger.info("✅ Export complete!")
        logger.info(f"✅ {stats['businesses']} PLATINUM business leads exported")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
