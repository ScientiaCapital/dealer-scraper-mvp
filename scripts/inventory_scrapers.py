#!/usr/bin/env python3
"""
Scraper Inventory Script

Scans the codebase for all scrapers (OEM + State License) and populates
the scraper_registry table for observability tracking.

Usage:
    python scripts/inventory_scrapers.py
    python scripts/inventory_scrapers.py --db-path output/master/pipeline.db
"""

import os
import sys
import re
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# OEM Scrapers - manually defined with known URLs
OEM_SCRAPERS = {
    "generac": {
        "source_url": "https://www.generac.com/service-support/dealer-locator",
        "notes": "Backup generators - custom navigation scraper"
    },
    "tesla": {
        "source_url": "https://www.tesla.com/support/certified-installers-powerwall",
        "notes": "Powerwall batteries - custom navigation"
    },
    "enphase": {
        "source_url": "https://enphase.com/installer-locator",
        "notes": "Microinverters - custom navigation"
    },
    "solaredge": {
        "source_url": "https://www.solaredge.com/us/installers-locator",
        "notes": "Solar inverters - custom navigation"
    },
    "briggs": {
        "source_url": "https://www.briggsandstratton.com/na/en_us/dealer-locator.html",
        "notes": "Backup generators - generic scraper"
    },
    "cummins": {
        "source_url": "https://www.cummins.com/parts-and-service/dealer-locator",
        "notes": "Backup generators - generic scraper"
    },
    "kohler": {
        "source_url": "https://www.kohlergenerators.com/find-a-dealer",
        "notes": "Backup generators - generic scraper"
    },
    "fronius": {
        "source_url": "https://www.fronius.com/en-us/usa/solar-energy/home-owners/contact/find-installers",
        "notes": "Solar inverters - needs verification"
    },
    "sma": {
        "source_url": "https://www.sma-america.com/service-support/installer-search.html",
        "notes": "Solar inverters - generic scraper"
    },
    "solark": {
        "source_url": "https://www.sol-ark.com/installers/",
        "notes": "Hybrid inverters - generic scraper"
    },
    "goodwe": {
        "source_url": "https://en.goodwe.com/Partners",
        "notes": "Solar inverters - generic scraper"
    },
    "growatt": {
        "source_url": "https://www.growatt-us.com/installers/",
        "notes": "Solar inverters - generic scraper"
    },
    "sungrow": {
        "source_url": "https://en.sungrowpower.com/partnerSearch",
        "notes": "Solar inverters - generic scraper"
    },
    "abb": {
        "source_url": "https://new.abb.com/ev-charging/installers",
        "notes": "Solar inverters - generic scraper"
    },
    "delta": {
        "source_url": "https://www.delta-americas.com/en-US/products/solar-inverters",
        "notes": "Solar inverters - generic scraper"
    },
    "tigo": {
        "source_url": "https://www.tigoenergy.com/find-installer",
        "notes": "Solar optimizers - generic scraper"
    },
    "simpliphi": {
        "source_url": "https://simpliphipower.com/find-an-installer/",
        "notes": "Battery storage - needs verification"
    },
    "mitsubishi": {
        "source_url": "https://www.mitsubishicomfort.com/find-a-contractor",
        "notes": "VRF/HVAC systems - HIGH PRIORITY resimercial signal"
    },
    "carrier": {
        "source_url": "https://www.carrier.com/residential/en/us/find-a-dealer/",
        "notes": "HVAC systems"
    },
    "lennox": {
        "source_url": "https://www.lennox.com/find-a-dealer",
        "notes": "HVAC systems"
    },
    "rheem": {
        "source_url": "https://www.rheem.com/find-a-contractor/",
        "notes": "HVAC systems"
    },
    "honeywell": {
        "source_url": "https://www.honeywellhome.com/en/professional-locator",
        "notes": "Smart home / HVAC controls"
    },
    "johnson_controls": {
        "source_url": "https://www.johnsoncontrols.com/",
        "notes": "Building automation"
    },
    "schneider": {
        "source_url": "https://www.se.com/us/en/partners/partner-locator/",
        "notes": "Electrical equipment"
    },
    "sensi": {
        "source_url": "https://sensi.emerson.com/en-us/contractors",
        "notes": "Smart thermostats"
    },
}

# State License Scrapers
STATE_LICENSE_SCRAPERS = {
    "fl_license": {
        "source_url": "https://www.myfloridalicense.com/",
        "notes": "Florida DBPR - CAC/CPC/CFC/FRO licenses"
    },
    "ca_license": {
        "source_url": "https://www.cslb.ca.gov/",
        "notes": "California CSLB - C-10/C-20/C-36/C-46 licenses"
    },
    "tx_license": {
        "source_url": "https://www.tdlr.texas.gov/",
        "notes": "Texas TDLR - Electrical/HVAC/Plumbing"
    },
    "nyc_dob": {
        "source_url": "https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet",
        "notes": "NYC DOB - Electrical/Plumber/Oil Burner/Fire"
    },
    "nj_license": {
        "source_url": "https://newjersey.mylicense.com/",
        "notes": "New Jersey - MEP trades (county-level)"
    },
}

# Third-party data sources
THIRD_PARTY_SOURCES = {
    "spw": {
        "source_url": "https://www.solarpowerworldonline.com/",
        "notes": "Solar Power World Top Contractors lists"
    },
    "amicus": {
        "source_url": None,
        "notes": "Amicus Solar integration"
    },
}


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def scan_scraper_files(scrapers_dir: Path) -> dict:
    """Scan scrapers directory for scraper classes."""
    found_scrapers = {}

    if not scrapers_dir.exists():
        print(f"  ⚠️  Scrapers directory not found: {scrapers_dir}")
        return found_scrapers

    for file_path in scrapers_dir.glob("*_scraper.py"):
        scraper_name = file_path.stem.replace("_scraper", "")

        # Skip base/factory files
        if scraper_name in ["base", "scraper_factory"]:
            continue

        # Read file to extract DEALER_LOCATOR_URL
        try:
            content = file_path.read_text()
            url_match = re.search(r'DEALER_LOCATOR_URL\s*=\s*["\']([^"\']+)["\']', content)
            url = url_match.group(1) if url_match else None

            found_scrapers[scraper_name] = {
                "file_path": str(file_path),
                "source_url": url,
            }
        except Exception as e:
            print(f"  ⚠️  Error reading {file_path}: {e}")

    return found_scrapers


def populate_scraper_registry(conn: sqlite3.Connection, dry_run: bool = False):
    """Populate scraper_registry table with all known scrapers."""
    cursor = conn.cursor()

    all_scrapers = []

    # Add OEM scrapers
    for name, info in OEM_SCRAPERS.items():
        all_scrapers.append({
            "scraper_name": name,
            "scraper_type": "OEM",
            "source_url": info["source_url"],
            "notes": info["notes"],
            "status": "UNTESTED",
        })

    # Add state license scrapers
    for name, info in STATE_LICENSE_SCRAPERS.items():
        all_scrapers.append({
            "scraper_name": name,
            "scraper_type": "STATE_LICENSE",
            "source_url": info["source_url"],
            "notes": info["notes"],
            "status": "UNTESTED",
        })

    # Add third-party sources
    for name, info in THIRD_PARTY_SOURCES.items():
        all_scrapers.append({
            "scraper_name": name,
            "scraper_type": "THIRD_PARTY",
            "source_url": info["source_url"],
            "notes": info["notes"],
            "status": "UNTESTED",
        })

    print(f"\n📋 Registering {len(all_scrapers)} scrapers...")

    inserted = 0
    skipped = 0

    for scraper in all_scrapers:
        try:
            if dry_run:
                print(f"  [DRY RUN] Would insert: {scraper['scraper_name']} ({scraper['scraper_type']})")
                inserted += 1
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO scraper_registry
                    (scraper_name, scraper_type, source_url, notes, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    scraper["scraper_name"],
                    scraper["scraper_type"],
                    scraper["source_url"],
                    scraper["notes"],
                    scraper["status"],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ))

                if cursor.rowcount > 0:
                    print(f"  ✓ Registered: {scraper['scraper_name']} ({scraper['scraper_type']})")
                    inserted += 1
                else:
                    print(f"  → Exists: {scraper['scraper_name']}")
                    skipped += 1

        except Exception as e:
            print(f"  ✗ Error registering {scraper['scraper_name']}: {e}")

    if not dry_run:
        conn.commit()

    return inserted, skipped


def print_summary(conn: sqlite3.Connection):
    """Print summary of scraper registry."""
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("SCRAPER REGISTRY SUMMARY")
    print("=" * 60)

    # Count by type
    cursor.execute("""
        SELECT scraper_type, COUNT(*) as count,
               SUM(CASE WHEN status = 'WORKING' THEN 1 ELSE 0 END) as working,
               SUM(CASE WHEN status = 'BROKEN' THEN 1 ELSE 0 END) as broken,
               SUM(CASE WHEN status = 'UNTESTED' THEN 1 ELSE 0 END) as untested
        FROM scraper_registry
        GROUP BY scraper_type
    """)

    print("\nBy Type:")
    for row in cursor.fetchall():
        print(f"  {row['scraper_type']}: {row['count']} total "
              f"(🟢 {row['working']} working, 🔴 {row['broken']} broken, ⚪ {row['untested']} untested)")

    # Total
    cursor.execute("SELECT COUNT(*) as total FROM scraper_registry")
    total = cursor.fetchone()['total']
    print(f"\nTotal scrapers registered: {total}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Inventory all scrapers and populate registry")
    parser.add_argument("--db-path", default="output/master/pipeline.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    args = parser.parse_args()

    print("🔍 Scraper Inventory Tool")
    print("=" * 60)

    # Check database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found: {args.db_path}")
        sys.exit(1)

    print(f"Database: {args.db_path}")

    # Connect and populate
    conn = get_db_connection(args.db_path)

    try:
        # Scan scraper files for any we missed
        scrapers_dir = Path(__file__).parent.parent / "scrapers"
        found_files = scan_scraper_files(scrapers_dir)
        print(f"\n📁 Found {len(found_files)} scraper files in {scrapers_dir}")

        # Populate registry
        inserted, skipped = populate_scraper_registry(conn, dry_run=args.dry_run)

        print(f"\n✅ Inventory complete: {inserted} inserted, {skipped} already existed")

        # Print summary
        if not args.dry_run:
            print_summary(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
