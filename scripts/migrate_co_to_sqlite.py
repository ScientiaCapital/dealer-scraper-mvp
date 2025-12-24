#!/usr/bin/env python3
"""
Colorado DORA License Migration Script

Fetches Electrical and Plumbing Contractor licenses from Colorado DORA
via the SODA API and migrates them to pipeline.db.

Data Source: https://data.colorado.gov/resource/7s5z-vewr.json
License Types:
  - EC: Electrical Contractor
  - PC: Plumbing Contractor

Usage:
    python scripts/migrate_co_to_sqlite.py
    python scripts/migrate_co_to_sqlite.py --limit 100  # Test mode
    python scripts/migrate_co_to_sqlite.py --include-expired  # Include expired
"""

import argparse
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Colorado DORA SODA API endpoint
SODA_API_URL = "https://data.colorado.gov/resource/7s5z-vewr.json"

# License type code to human-readable name mapping
LICENSE_TYPE_MAP = {
    # Electrical
    "EC": "Electrical Contractor",
    "ME": "Master Electrician",
    "JW": "Journeyman Electrician",
    "RW": "Residential Wireman",
    "APE": "Electrical Apprentice",
    "JEWP": "Journeyman Electrician Work Permit",
    "MEWP": "Master Electrician Work Permit",
    "RWWP": "Residential Wireman Work Permit",
    "METPE": "Master Electrician Temp Permit Emergency",
    # Plumbing
    "PC": "Plumbing Contractor",
    "MP": "Master Plumber",
    "JP": "Journeyman Plumber",
    "RP": "Residential Plumber",
    "JPWP": "Journeyman Plumber Work Permit",
    "MPWP": "Master Plumber Work Permit",
    "RPWP": "Residential Plumber Work Permit",
    "MPTPE": "Master Plumber Temp Permit Emergency",
    # Water Conditioning (Blue Ocean!)
    "WC": "Water Conditioning Contractor",
    "WI": "Water Conditioning Installer",
    "WP": "Water Conditioning Principal",
}

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"


def normalize_company_name(name: str | None) -> str:
    """
    Normalize company name for deduplication.

    - Lowercase
    - Strip whitespace
    - Remove punctuation (except &)
    """
    if not name:
        return ""

    # Lowercase and strip
    normalized = name.lower().strip()

    # Remove punctuation except & (common in company names like "Smith & Sons")
    normalized = re.sub(r'[^\w\s&]', '', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized


def transform_dora_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Transform a DORA SODA API record to pipeline.db format.

    Handles both business licenses (entityname) and individual licenses (firstname/lastname).

    Args:
        record: Raw record from SODA API

    Returns:
        Transformed record ready for pipeline.db insertion
    """
    license_type_code = record.get("licensetype", "")
    license_type_name = LICENSE_TYPE_MAP.get(license_type_code, license_type_code)

    # Extract verification URL if present
    verify_link = record.get("linktoverifylicense", {})
    verify_url = verify_link.get("url") if isinstance(verify_link, dict) else None

    # Get company name - prefer entityname (business), fallback to firstname/lastname (individual)
    company_name = record.get("entityname")
    if not company_name:
        # Individual license - construct name from first/last
        first = record.get("firstname", "").strip()
        last = record.get("lastname", "").strip()
        if first and last:
            company_name = f"{first} {last}"
        elif last:
            company_name = last

    return {
        "company_name": company_name,
        "city": record.get("city"),
        "state": record.get("state") or "CO",  # Default to CO
        "zip": record.get("mailzipcode"),
        "license_type": license_type_name,
        "license_type_code": license_type_code,
        "license_number": record.get("licensenumber"),
        "license_status": record.get("licensestatusdescription"),
        "license_first_issued": record.get("licensefirstissuedate"),
        "license_last_renewed": record.get("licenselastreneweddate"),
        "license_expiration": record.get("licenseexpirationdate"),
        "verify_url": verify_url,
        "source": "CO_DORA",
        "is_individual": record.get("entityname") is None,  # Flag individual vs business
    }


def should_include_record(record: dict[str, Any], include_expired: bool = False) -> bool:
    """
    Determine if a record should be included in the migration.

    Args:
        record: Raw SODA API record
        include_expired: Whether to include expired licenses

    Returns:
        True if record should be included
    """
    status = record.get("licensestatusdescription", "").lower()

    if include_expired:
        return True

    # Only include active licenses by default
    return status == "active"


def fetch_records(
    license_type: str,
    limit: int | None = None,
    offset: int = 0,
    active_only: bool = True
) -> list[dict[str, Any]]:
    """
    Fetch records from SODA API for a specific license type.

    Args:
        license_type: License type code (EC, PC, etc.)
        limit: Maximum records to fetch (None for SODA default of 1000)
        offset: Number of records to skip
        active_only: Only fetch active licenses

    Returns:
        List of records from SODA API
    """
    params = {
        "$where": f"licensetype='{license_type}'" + (
            " AND licensestatusdescription='Active'" if active_only else ""
        ),
        "$order": "licensenumber",
        "$offset": offset,
    }

    if limit:
        params["$limit"] = limit
    else:
        params["$limit"] = 10000  # Max per request

    response = requests.get(SODA_API_URL, params=params, timeout=60)
    response.raise_for_status()

    return response.json()


def fetch_all_records(
    license_types: list[str],
    include_expired: bool = False,
    limit: int | None = None
) -> Generator[dict[str, Any], None, None]:
    """
    Fetch all records for specified license types with pagination.

    Args:
        license_types: List of license type codes to fetch
        include_expired: Whether to include expired licenses
        limit: Maximum total records to fetch (None for all)

    Yields:
        Individual records from SODA API
    """
    total_fetched = 0

    for lt in license_types:
        offset = 0
        page_size = 10000

        while True:
            if limit and total_fetched >= limit:
                return

            # Adjust page size if limit would be exceeded
            current_limit = page_size
            if limit:
                current_limit = min(page_size, limit - total_fetched)

            logger.info(f"Fetching {lt} records (offset={offset}, limit={current_limit})")

            records = fetch_records(
                license_type=lt,
                limit=current_limit,
                offset=offset,
                active_only=not include_expired
            )

            if not records:
                break

            for record in records:
                if limit and total_fetched >= limit:
                    return
                yield record
                total_fetched += 1

            # Check if we got a full page (more records may exist)
            if len(records) < current_limit:
                break

            offset += len(records)

    logger.info(f"Total records fetched: {total_fetched}")


def migrate_to_sqlite(
    db_path: Path = DEFAULT_DB_PATH,
    include_expired: bool = False,
    limit: int | None = None,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Migrate Colorado DORA contractor licenses to pipeline.db.

    Args:
        db_path: Path to SQLite database
        include_expired: Whether to include expired licenses
        limit: Maximum records to migrate (None for all)
        dry_run: If True, don't actually write to database

    Returns:
        Statistics dict with counts
    """
    stats = {
        "total_fetched": 0,
        "inserted": 0,
        "skipped_duplicate": 0,
        "skipped_no_name": 0,
        "licenses_added": 0,
    }

    # License types we care about for ICP
    # ONLY business licenses (entityname) - these are $5M-$50M companies
    # Skip individual licenses (firstname/lastname) - those are Jobber/Housecall Pro users
    license_types = [
        # Contractors (BUSINESS licenses only)
        "EC",  # Electrical Contractor
        "PC",  # Plumbing Contractor
        "WC",  # Water Conditioning Contractor
        # Skip ME, MP, JW, JP, RW, RP, WI, WP - these are individual licenses
    ]

    if not dry_run:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Check existing contractors by normalized name + state
        cur.execute("""
            SELECT normalized_name, id FROM contractors
            WHERE state = 'CO'
        """)
        existing = {row[0]: row[1] for row in cur.fetchall()}
    else:
        existing = {}
        conn = None
        cur = None

    try:
        for record in fetch_all_records(license_types, include_expired, limit):
            stats["total_fetched"] += 1

            transformed = transform_dora_record(record)

            # Skip records without company name
            if not transformed["company_name"]:
                stats["skipped_no_name"] += 1
                continue

            normalized_name = normalize_company_name(transformed["company_name"])

            if dry_run:
                logger.info(f"[DRY RUN] Would insert: {transformed['company_name']}")
                stats["inserted"] += 1
                continue

            # Check for existing contractor
            if normalized_name in existing:
                contractor_id = existing[normalized_name]
                stats["skipped_duplicate"] += 1

                # Still add license if not exists
                cur.execute("""
                    INSERT OR IGNORE INTO licenses (
                        contractor_id, license_number, license_type,
                        license_category, state, license_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    contractor_id,
                    transformed["license_number"],
                    transformed["license_type"],
                    transformed["license_type_code"],
                    "CO",
                    transformed["license_status"]
                ))
                if cur.rowcount > 0:
                    stats["licenses_added"] += 1
            else:
                # Insert new contractor
                cur.execute("""
                    INSERT INTO contractors (
                        company_name, normalized_name, city, state, zip,
                        source_type, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transformed["company_name"],
                    normalized_name,
                    transformed["city"],
                    "CO",
                    transformed["zip"],
                    "state_license",
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                contractor_id = cur.lastrowid
                existing[normalized_name] = contractor_id
                stats["inserted"] += 1

                # Add license record
                cur.execute("""
                    INSERT INTO licenses (
                        contractor_id, license_number, license_type,
                        license_category, state, license_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    contractor_id,
                    transformed["license_number"],
                    transformed["license_type"],
                    transformed["license_type_code"],
                    "CO",
                    transformed["license_status"]
                ))
                stats["licenses_added"] += 1

            # Periodic commit and progress
            if stats["total_fetched"] % 500 == 0:
                conn.commit()
                logger.info(
                    f"Progress: {stats['total_fetched']} fetched, "
                    f"{stats['inserted']} inserted, "
                    f"{stats['skipped_duplicate']} duplicates"
                )

        if conn:
            conn.commit()

    finally:
        if conn:
            conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Colorado DORA contractor licenses to pipeline.db"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--include-expired",
        action="store_true",
        help="Include expired licenses (default: active only)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum records to migrate (for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to database, just log what would happen"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("COLORADO DORA LICENSE MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Include expired: {args.include_expired}")
    logger.info(f"Limit: {args.limit or 'None (fetch all)'}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    stats = migrate_to_sqlite(
        db_path=args.db_path,
        include_expired=args.include_expired,
        limit=args.limit,
        dry_run=args.dry_run
    )

    logger.info("=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total fetched: {stats['total_fetched']}")
    logger.info(f"Inserted: {stats['inserted']}")
    logger.info(f"Skipped (duplicate): {stats['skipped_duplicate']}")
    logger.info(f"Skipped (no name): {stats['skipped_no_name']}")
    logger.info(f"Licenses added: {stats['licenses_added']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
