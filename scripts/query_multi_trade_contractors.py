#!/usr/bin/env python3
"""
Multi-Trade Contractor Query

Identifies contractors with 2+ license types across all states.
Multi-trade = PLATINUM ICP tier (highest value leads).

Usage:
  python scripts/query_multi_trade_contractors.py --state CO
  python scripts/query_multi_trade_contractors.py --all-states
  python scripts/query_multi_trade_contractors.py --min-trades 2
  python scripts/query_multi_trade_contractors.py --output-csv output/multi_trade.csv
"""

import argparse
import csv
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default database path (main repo, not worktree)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "Desktop/tk_projects/dealer-scraper-mvp/output/pipeline.db"


def is_business_entity(company_name: str) -> bool:
    """
    Detect if company name is a business entity (not an individual).

    Business patterns:
    - Contains LLC, INC, CORP, LTD, COMPANY, COMPANIES, CONTRACTORS
    - ALL CAPS (e.g., "TIC - THE INDUSTRIAL COMPANY")
    - Contains & (e.g., "Smith & Sons")

    Individual patterns (EXCLUDE):
    - Firstname Lastname (e.g., "John Smith")
    """
    if not company_name:
        return False

    name_upper = company_name.upper()

    # Business keywords
    business_keywords = [
        'LLC', 'INC', 'CORP', 'LTD', 'COMPANY', 'COMPANIES',
        'CONTRACTORS', 'CORPORATION', 'INCORPORATED', 'CONTRACTORS'
    ]

    if any(keyword in name_upper for keyword in business_keywords):
        return True

    # Ampersand indicates business (Smith & Sons)
    if '&' in company_name:
        return True

    # ALL CAPS is typically a business (unless it's 2 words which might be individual)
    if company_name == company_name.upper() and len(company_name.split()) > 2:
        return True

    # Check for "Firstname Lastname" pattern (individual)
    parts = company_name.split()
    if len(parts) == 2:
        # Both parts are capitalized words (likely firstname lastname)
        first_word, second_word = parts
        if (len(first_word) > 0 and len(second_word) > 0 and
            first_word[0].isupper() and first_word[1:].islower() and
            second_word[0].isupper() and second_word[1:].islower()):
            return False

    # Default to business if we're not sure
    return True


def filter_business_entities(contractors: List[Dict]) -> List[Dict]:
    """
    Filter out individual contractors (firstname/lastname pattern).

    Args:
        contractors: List of contractor dictionaries

    Returns:
        List of business entities only
    """
    return [c for c in contractors if is_business_entity(c['company_name'])]


def assign_icp_tier(contractor: Dict) -> str:
    """
    Assign ICP tier based on trade count and combination.

    Tiers:
    - 3+ trades = PLATINUM
    - 2 trades = GOLD (if EC+PC or EC+PL or PC+PL)
    - 2 trades = SILVER (other combos)
    - 1 trade = BRONZE

    Args:
        contractor: Dictionary with trade_count and license_types keys

    Returns:
        ICP tier string (PLATINUM, GOLD, SILVER, BRONZE)
    """
    trade_count = contractor.get('trade_count', 0)
    license_types = contractor.get('license_types', '')

    # 3+ trades = PLATINUM
    if trade_count >= 3:
        return "PLATINUM"

    # 2 trades
    if trade_count == 2:
        # Check for high-value combinations (EC+PC, EC+PL, PC+PL)
        high_value_combos = [
            ('Electrical Contractor', 'Plumbing Contractor'),
            ('Electrical Contractor', 'Plumbing'),
            ('Plumbing Contractor', 'Electrical'),
        ]

        for combo in high_value_combos:
            if all(license in license_types for license in combo):
                return "GOLD"

        # Other 2-trade combos = SILVER
        return "SILVER"

    # 1 trade = BRONZE
    return "BRONZE"


def query_multi_trade_contractors(
    db_path: Optional[Path] = None,
    state: Optional[str] = None,
    min_trades: int = 2,
    exclude_individuals: bool = True,
    output_csv: Optional[Path] = None
) -> List[Dict]:
    """
    Query SQLite for contractors with multiple license types.

    Args:
        db_path: Path to pipeline.db (defaults to main repo location)
        state: Filter to specific state (None = all states)
        min_trades: Minimum number of trades required (default: 2)
        exclude_individuals: Filter out individual contractors (default: True)
        output_csv: Optional path to export CSV

    Returns:
        List of dicts with keys: company_name, state, trade_count,
        license_types (comma-separated), total_licenses
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return []

    logger.info(f"Querying database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build query (selecting only columns that always exist)
    query = """
    SELECT DISTINCT
        c.id,
        c.company_name,
        c.state,
        COUNT(DISTINCT l.license_type) as trade_count,
        GROUP_CONCAT(DISTINCT l.license_type) as license_types,
        COUNT(l.id) as total_licenses
    FROM contractors c
    JOIN licenses l ON c.id = l.contractor_id
    WHERE c.source_type = 'state_license'
    """

    params = []

    # Add state filter if specified
    if state:
        query += " AND c.state = ?"
        params.append(state)

    query += " GROUP BY c.id HAVING trade_count >= ?"
    params.append(min_trades)

    query += " ORDER BY trade_count DESC, c.company_name"

    logger.info(f"Executing query with min_trades={min_trades}, state={state}")
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Convert to list of dicts
    results = [dict(row) for row in rows]

    logger.info(f"Found {len(results)} multi-trade contractors")

    # Filter to business entities if requested
    if exclude_individuals:
        before_count = len(results)
        results = filter_business_entities(results)
        after_count = len(results)
        logger.info(f"Filtered to {after_count} business entities (excluded {before_count - after_count} individuals)")

    # Export to CSV if requested
    if output_csv and results:
        logger.info(f"Exporting to CSV: {output_csv}")
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv, 'w', newline='') as csvfile:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        logger.info(f"✅ CSV export complete: {len(results)} rows")

    conn.close()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Query multi-trade contractors from pipeline.db"
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to pipeline.db (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        '--state',
        type=str,
        help="Filter to specific state (e.g., CO, TX, CA)"
    )
    parser.add_argument(
        '--all-states',
        action='store_true',
        help="Query all states (default behavior)"
    )
    parser.add_argument(
        '--min-trades',
        type=int,
        default=2,
        help="Minimum number of trades required (default: 2)"
    )
    parser.add_argument(
        '--output-csv',
        type=Path,
        help="Export results to CSV file"
    )
    parser.add_argument(
        '--include-individuals',
        action='store_true',
        help="Include individual contractors (default: businesses only)"
    )

    args = parser.parse_args()

    # Query
    results = query_multi_trade_contractors(
        db_path=args.db_path,
        state=args.state if not args.all_states else None,
        min_trades=args.min_trades,
        exclude_individuals=not args.include_individuals,
        output_csv=args.output_csv
    )

    # Display summary
    print("\n" + "=" * 60)
    print("Multi-Trade Contractor Query Results")
    print("=" * 60)
    print(f"Total contractors: {len(results)}")

    if results:
        # Count trade combinations
        from collections import Counter
        trade_combos = Counter(r['license_types'] for r in results)

        print(f"\nTop License Combinations:")
        for combo, count in trade_combos.most_common(10):
            # Assign tier for display
            sample = {'trade_count': combo.count(',') + 1, 'license_types': combo}
            tier = assign_icp_tier(sample)
            print(f"  [{tier}] {combo}: {count} contractors")

        print(f"\nSample Contractors (Top 10):")
        for i, contractor in enumerate(results[:10], 1):
            tier = assign_icp_tier(contractor)
            print(f"  {i}. [{tier}] {contractor['company_name']} ({contractor['trade_count']} trades)")
            print(f"     State: {contractor['state']} | Licenses: {contractor['license_types']}")

    if args.output_csv:
        print(f"\n✅ Exported to: {args.output_csv}")

    print("=" * 60 + "\n")

    return 0 if results else 1


if __name__ == '__main__':
    exit(main())
