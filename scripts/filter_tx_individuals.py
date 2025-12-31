#!/usr/bin/env python3
"""
Filter TX Individual Records

Detects individual names ("LASTNAME, FIRSTNAME" pattern) in TX license data
and marks them with is_individual=1 in the contractors table.

Business records are retained for sales-agent exports.
Individual records are kept in database but excluded from exports.

Usage:
    python scripts/filter_tx_individuals.py [--dry-run] [--verbose]
"""

import argparse
import re
import sqlite3
from pathlib import Path
from datetime import datetime


# Business entity indicators that override individual detection
BUSINESS_INDICATORS = [
    'LLC', 'INC', 'CORP', 'LTD', 'CO.', 'CO,', 'COMPANY', 'CORPORATION',
    'SERVICES', 'SERVICE', 'ELECTRIC', 'ELECTRICAL', 'HVAC', 'PLUMBING',
    'AIR', 'HEATING', 'COOLING', 'CONTRACTORS', 'CONSTRUCTION',
    'ENTERPRISES', 'SOLUTIONS', 'SYSTEMS', 'MECHANICAL', 'TECH',
    'GROUP', 'ASSOCIATES', 'PARTNERS', 'INDUSTRIES', 'PROFESSIONALS',
    'DBA', 'D/B/A', 'T/A', 'TRADING AS', '&', 'AND SONS', 'AND SON',
    'BROTHERS', 'BROS', 'FAMILY', 'RESIDENTIAL', 'COMMERCIAL'
]

# Common individual name patterns
INDIVIDUAL_PATTERNS = [
    # "LASTNAME, FIRSTNAME" - most common TX format
    r'^[A-Z][A-Za-z\'-]+,\s+[A-Z][A-Za-z\'-]+$',
    # "LASTNAME, FIRSTNAME MIDDLE"
    r'^[A-Z][A-Za-z\'-]+,\s+[A-Z][A-Za-z\'-]+\s+[A-Z][A-Za-z\'-]*$',
    # "LASTNAME, F." or "LASTNAME, F M"
    r'^[A-Z][A-Za-z\'-]+,\s+[A-Z]\.?(\s+[A-Z]\.?)?$',
]


def has_business_indicator(name: str) -> bool:
    """Check if name contains business indicators."""
    name_upper = name.upper()
    return any(ind in name_upper for ind in BUSINESS_INDICATORS)


def is_individual_name(name: str) -> bool:
    """
    Detect if a company name is actually an individual person.

    Returns True if the name matches individual patterns AND
    does not contain business indicators.
    """
    if not name or len(name) < 3:
        return False

    name = name.strip()

    # Business indicators always override
    if has_business_indicator(name):
        return False

    # Check individual patterns
    for pattern in INDIVIDUAL_PATTERNS:
        if re.match(pattern, name):
            return True

    # Additional heuristics:
    # Names with exactly one comma and no numbers are likely individuals
    if ',' in name and name.count(',') == 1:
        parts = name.split(',')
        if len(parts) == 2:
            last = parts[0].strip()
            first = parts[1].strip()
            # Both parts should be alphabetic only (with hyphens/apostrophes)
            if (re.match(r'^[A-Za-z\'-]+$', last) and
                re.match(r'^[A-Za-z\'-\s]+$', first) and
                len(last) >= 2 and len(first) >= 1):
                # Exclude if first part looks like a business abbreviation
                if last.upper() not in ['AIR', 'ACE', 'PRO', 'ALL']:
                    return True

    return False


def filter_tx_individuals(db_path: str, dry_run: bool = False, verbose: bool = False) -> dict:
    """
    Filter TX individual records in the database.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, don't modify database
        verbose: If True, print individual names being filtered

    Returns:
        dict with statistics
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get TX contractors
    cursor.execute("""
        SELECT id, company_name
        FROM contractors
        WHERE state = 'TX'
        AND is_deleted = 0
        AND (is_individual IS NULL OR is_individual = 0)
    """)

    tx_records = cursor.fetchall()

    stats = {
        'total_tx_records': len(tx_records),
        'individuals_found': 0,
        'businesses_retained': 0,
        'updated_at': datetime.now().isoformat()
    }

    individuals = []
    businesses = []

    for record_id, company_name in tx_records:
        if is_individual_name(company_name):
            individuals.append((record_id, company_name))
            stats['individuals_found'] += 1
        else:
            businesses.append((record_id, company_name))
            stats['businesses_retained'] += 1

    if verbose:
        print("\n=== SAMPLE INDIVIDUALS (first 20) ===")
        for record_id, name in individuals[:20]:
            print(f"  [{record_id}] {name}")

        print("\n=== SAMPLE BUSINESSES (first 20) ===")
        for record_id, name in businesses[:20]:
            print(f"  [{record_id}] {name}")

    if not dry_run and individuals:
        # Update individuals in batches
        batch_size = 500
        for i in range(0, len(individuals), batch_size):
            batch = individuals[i:i + batch_size]
            ids = [r[0] for r in batch]
            placeholders = ','.join('?' * len(ids))
            cursor.execute(f"""
                UPDATE contractors
                SET is_individual = 1,
                    individual_detection_method = 'name_format',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            """, ids)

        conn.commit()
        print(f"\n✅ Updated {stats['individuals_found']} records with is_individual=1")

    conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(description='Filter TX individual records')
    parser.add_argument('--dry-run', action='store_true', help='Preview without modifying database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show sample records')
    parser.add_argument('--db', default='output/pipeline.db', help='Database path')
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    print("=" * 60)
    print("TX INDIVIDUAL FILTER")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    stats = filter_tx_individuals(str(db_path), dry_run=args.dry_run, verbose=args.verbose)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total TX records scanned: {stats['total_tx_records']:,}")
    print(f"Individuals detected:     {stats['individuals_found']:,}")
    print(f"Businesses retained:      {stats['businesses_retained']:,}")
    print(f"Individual %:             {stats['individuals_found'] * 100 / max(stats['total_tx_records'], 1):.1f}%")
    print()

    if args.dry_run:
        print("⚠️  DRY RUN - no changes made. Run without --dry-run to apply.")

    return 0


if __name__ == '__main__':
    exit(main())
