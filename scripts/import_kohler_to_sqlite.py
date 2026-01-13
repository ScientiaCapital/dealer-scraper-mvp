#!/usr/bin/env python3
"""
Kohler Dealer Import Script

Imports Kohler dealer data from kohler_master.json into pipeline.db.
- Deduplicates by phone number
- Inserts into contractors table (source_type='oem_dealer')
- Inserts into oem_certifications table (oem_name='Kohler')

Usage:
    python scripts/import_kohler_to_sqlite.py
    python scripts/import_kohler_to_sqlite.py --dry-run  # Preview without inserting
    python scripts/import_kohler_to_sqlite.py --input path/to/master.json
"""

import argparse
import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path(__file__).parent.parent / "output" / "kohler" / "kohler_master.json"
DEFAULT_DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"

TOLL_FREE_PREFIXES = ('800', '888', '877', '866', '855', '844', '833')


def normalize_phone(phone: str | None) -> str | None:
    """Normalize phone to 10 digits, exclude toll-free."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    if digits.startswith(TOLL_FREE_PREFIXES):
        return None
    return digits


def normalize_company_name(name: str | None) -> str:
    """Normalize company name for deduplication."""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = re.sub(r'[^\w\s&]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def extract_domain(website: str | None) -> str | None:
    """Extract domain from website URL."""
    if not website:
        return None
    domain = website.lower().strip()
    domain = re.sub(r'^https?://', '', domain)
    domain = re.sub(r'^www\.', '', domain)
    domain = domain.split('/')[0]
    if not domain or domain in ('', 'localhost'):
        return None
    return domain


def load_kohler_data(input_path: Path) -> list[dict[str, Any]]:
    """Load dealers from kohler_master.json."""
    if not input_path.exists():
        raise FileNotFoundError(f"Master JSON not found: {input_path}")

    with open(input_path) as f:
        data = json.load(f)

    dealers = data.get('dealers', [])
    logger.info(f"Loaded {len(dealers)} dealers from {input_path}")
    return dealers


def deduplicate_by_phone(dealers: list[dict]) -> list[dict]:
    """Deduplicate dealers by normalized phone number."""
    seen_phones = set()
    unique = []

    for dealer in dealers:
        phone = normalize_phone(dealer.get('phone'))
        if phone and phone in seen_phones:
            continue
        if phone:
            seen_phones.add(phone)
        unique.append(dealer)

    logger.info(f"Deduplication: {len(dealers)} -> {len(unique)} unique dealers")
    return unique


def import_to_sqlite(
    dealers: list[dict],
    db_path: Path,
    dry_run: bool = False
) -> dict[str, int]:
    """Import dealers into SQLite database."""
    stats = {
        'total': len(dealers),
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'oem_certs': 0
    }

    if dry_run:
        logger.info("DRY RUN: No changes will be made")
        for d in dealers[:5]:
            logger.info(f"  Would insert: {d.get('name')} | {d.get('phone')} | {d.get('tier')}")
        return stats

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for dealer in dealers:
        name = dealer.get('name', '').strip()
        if not name:
            stats['skipped'] += 1
            continue

        phone = normalize_phone(dealer.get('phone'))
        normalized = normalize_company_name(name)
        domain = extract_domain(dealer.get('website') or dealer.get('domain'))
        tier = dealer.get('tier', 'Certified')
        scraped_zip = dealer.get('scraped_from_zip', '')

        # Check for existing contractor by phone
        existing_id = None
        if phone:
            cursor.execute(
                "SELECT id FROM contractors WHERE primary_phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            if row:
                existing_id = row[0]

        if existing_id:
            # Update existing - add OEM cert if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip)
                VALUES (?, 'Kohler', ?, ?)
            """, (existing_id, tier, scraped_zip))

            if cursor.rowcount > 0:
                stats['oem_certs'] += 1

            # Update source_type to 'both' if it was state_license
            cursor.execute("""
                UPDATE contractors SET source_type = 'both', updated_at = ?
                WHERE id = ? AND source_type = 'state_license'
            """, (datetime.now().isoformat(), existing_id))

            stats['updated'] += 1
        else:
            # Insert new contractor
            cursor.execute("""
                INSERT INTO contractors
                (company_name, normalized_name, street, city, state, zip,
                 primary_phone, primary_domain, source_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'oem_dealer', ?, ?)
            """, (
                name,
                normalized,
                dealer.get('street', ''),
                dealer.get('city', ''),
                dealer.get('state', ''),
                dealer.get('zip', ''),
                phone,
                domain,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            contractor_id = cursor.lastrowid

            # Insert OEM certification
            cursor.execute("""
                INSERT INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip)
                VALUES (?, 'Kohler', ?, ?)
            """, (contractor_id, tier, scraped_zip))

            stats['inserted'] += 1
            stats['oem_certs'] += 1

    conn.commit()
    conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Import Kohler dealers to SQLite")
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT,
                        help="Path to kohler_master.json")
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH,
                        help="Path to pipeline.db")
    parser.add_argument('--dry-run', action='store_true',
                        help="Preview changes without inserting")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("KOHLER DEALER IMPORT")
    logger.info("=" * 60)

    # Load data
    dealers = load_kohler_data(args.input)

    # Deduplicate
    unique_dealers = deduplicate_by_phone(dealers)

    # Import
    stats = import_to_sqlite(unique_dealers, args.db, args.dry_run)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("IMPORT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total dealers:     {stats['total']}")
    logger.info(f"Inserted (new):    {stats['inserted']}")
    logger.info(f"Updated (existing):{stats['updated']}")
    logger.info(f"Skipped (no name): {stats['skipped']}")
    logger.info(f"OEM certs added:   {stats['oem_certs']}")

    # Tier distribution
    if not args.dry_run and args.db.exists():
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT certification_tier, COUNT(*)
            FROM oem_certifications
            WHERE oem_name = 'Kohler'
            GROUP BY certification_tier
            ORDER BY COUNT(*) DESC
        """)
        logger.info("")
        logger.info("Tier Distribution:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]}")
        conn.close()


if __name__ == '__main__':
    main()
