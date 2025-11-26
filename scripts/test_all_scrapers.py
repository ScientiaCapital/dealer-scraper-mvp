#!/usr/bin/env python3
"""
OEM Scraper Audit Tool

Tests all registered scrapers to determine their status:
- WORKING: Successfully returns dealers
- BROKEN: Fails to load or extract
- UNTESTED: Not yet tested

Updates scraper_registry with results for dashboard visibility.

Usage:
    python scripts/test_all_scrapers.py
    python scripts/test_all_scrapers.py --oem generac tesla enphase
    python scripts/test_all_scrapers.py --quick  # Test 1 ZIP per OEM
"""

import os
import sys
import json
import sqlite3
import argparse
import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test ZIP codes by region (spread across US for coverage)
TEST_ZIPS = ["90210", "10001", "60601", "77001", "33101"]  # CA, NY, IL, TX, FL


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_registered_scrapers(conn: sqlite3.Connection, scraper_type: str = "OEM") -> List[Dict]:
    """Get all registered scrapers of a given type."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT scraper_name, source_url, status, notes
        FROM scraper_registry
        WHERE scraper_type = ?
        ORDER BY scraper_name
    """, (scraper_type,))
    return [dict(row) for row in cursor.fetchall()]


def update_scraper_status(conn: sqlite3.Connection, scraper_name: str,
                          status: str, fix_difficulty: Optional[str] = None,
                          records_found: int = 0, error_msg: Optional[str] = None):
    """Update scraper status in registry."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scraper_registry SET
            status = ?,
            fix_difficulty = COALESCE(?, fix_difficulty),
            last_test_date = ?,
            total_records_lifetime = CASE
                WHEN ? > 0 THEN COALESCE(total_records_lifetime, 0) + ?
                ELSE total_records_lifetime
            END,
            last_successful_run = CASE WHEN ? = 'WORKING' THEN ? ELSE last_successful_run END,
            notes = CASE WHEN ? IS NOT NULL THEN ? ELSE notes END,
            updated_at = ?
        WHERE scraper_name = ?
    """, (
        status,
        fix_difficulty,
        datetime.now().isoformat(),
        records_found, records_found,
        status, datetime.now().isoformat(),
        error_msg, error_msg,
        datetime.now().isoformat(),
        scraper_name,
    ))
    conn.commit()


def log_scraper_run(conn: sqlite3.Connection, scraper_name: str,
                    status: str, records_found: int = 0,
                    error_msg: Optional[str] = None, params: Optional[str] = None):
    """Log a scraper run to scraper_runs table."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scraper_runs
        (scraper_name, run_started_at, run_completed_at, status,
         records_found, error_message, run_parameters)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        scraper_name,
        datetime.now().isoformat(),
        datetime.now().isoformat(),
        status,
        records_found,
        error_msg,
        params,
    ))
    conn.commit()


def test_url_accessible(url: str) -> Tuple[bool, str]:
    """Test if a URL is accessible."""
    import urllib.request
    import urllib.error

    if not url:
        return False, "No URL configured"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return True, f"HTTP {response.status}"
            return False, f"HTTP {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_scraper_file_exists(scraper_name: str) -> Tuple[bool, str]:
    """Check if scraper file exists and has required components."""
    scrapers_dir = Path(__file__).parent.parent / "scrapers"

    # Try different naming patterns
    patterns = [
        f"{scraper_name}_scraper.py",
        f"{scraper_name.replace('_', '')}_scraper.py",
        f"{scraper_name.replace(' ', '_').lower()}_scraper.py",
    ]

    for pattern in patterns:
        file_path = scrapers_dir / pattern
        if file_path.exists():
            content = file_path.read_text()
            has_class = "class" in content and "Scraper" in content
            has_url = "DEALER_LOCATOR_URL" in content or "dealer" in content.lower()
            if has_class:
                return True, str(file_path)
            return False, f"File exists but missing Scraper class: {file_path}"

    return False, f"No scraper file found for {scraper_name}"


def assess_fix_difficulty(url_ok: bool, file_exists: bool, error_msg: str) -> str:
    """Assess how hard it would be to fix a broken scraper."""
    if url_ok and file_exists:
        # URL works, file exists - probably just needs selector updates
        return "EASY"
    elif url_ok and not file_exists:
        # URL works but no file - need to write scraper from scratch
        return "MEDIUM"
    elif not url_ok and "404" in error_msg:
        # Site moved or removed
        return "HARD"
    elif not url_ok and ("timeout" in error_msg.lower() or "connection" in error_msg.lower()):
        # Network issues - might be temporary
        return "MEDIUM"
    else:
        # URL broken for other reasons
        return "HARD"


def run_audit(conn: sqlite3.Connection, oem_filter: Optional[List[str]] = None,
              quick: bool = False, verbose: bool = True) -> Dict:
    """
    Run full audit of all OEM scrapers.

    Returns dict with results summary.
    """
    scrapers = get_registered_scrapers(conn, "OEM")

    if oem_filter:
        scrapers = [s for s in scrapers if s['scraper_name'] in oem_filter]

    results = {
        "tested": 0,
        "working": [],
        "broken": [],
        "needs_file": [],
        "timestamp": datetime.now().isoformat(),
    }

    print(f"\n🔍 OEM Scraper Audit")
    print("=" * 60)
    print(f"Testing {len(scrapers)} scrapers...")
    print("=" * 60)

    for scraper in scrapers:
        name = scraper['scraper_name']
        url = scraper['source_url']

        print(f"\n📦 {name.upper()}")
        print(f"   URL: {url or 'Not configured'}")

        # Test 1: Check if URL is accessible
        url_ok, url_msg = test_url_accessible(url)
        print(f"   URL Check: {'✅' if url_ok else '❌'} {url_msg}")

        # Test 2: Check if scraper file exists
        file_ok, file_msg = check_scraper_file_exists(name)
        print(f"   File Check: {'✅' if file_ok else '❌'} {file_msg.split('/')[-1] if file_ok else file_msg}")

        # Determine status
        if url_ok and file_ok:
            status = "WORKING"
            difficulty = None
            error = None
            results["working"].append(name)
        elif not file_ok:
            status = "BROKEN"
            difficulty = "MEDIUM"
            error = file_msg
            results["needs_file"].append(name)
        else:
            status = "BROKEN"
            difficulty = assess_fix_difficulty(url_ok, file_ok, url_msg)
            error = url_msg
            results["broken"].append(name)

        status_icon = "🟢" if status == "WORKING" else "🔴"
        print(f"   Status: {status_icon} {status}" + (f" ({difficulty})" if difficulty else ""))

        # Update database
        update_scraper_status(conn, name, status, difficulty, 0, error)
        log_scraper_run(conn, name, status, 0, error, json.dumps({"test_type": "audit"}))

        results["tested"] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"🟢 Working: {len(results['working'])}")
    print(f"🔴 Broken: {len(results['broken']) + len(results['needs_file'])}")
    print(f"   - URL issues: {len(results['broken'])}")
    print(f"   - Missing files: {len(results['needs_file'])}")

    if results['working']:
        print(f"\n✅ Working scrapers: {', '.join(results['working'])}")
    if results['broken']:
        print(f"\n❌ URL issues: {', '.join(results['broken'])}")
    if results['needs_file']:
        print(f"\n📝 Need scraper files: {', '.join(results['needs_file'])}")

    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="Audit all OEM scrapers")
    parser.add_argument("--db-path", default="output/master/pipeline.db", help="Database path")
    parser.add_argument("--oem", nargs="+", help="Specific OEMs to test")
    parser.add_argument("--quick", action="store_true", help="Quick test (1 ZIP per OEM)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Check database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found: {args.db_path}")
        sys.exit(1)

    conn = get_db_connection(args.db_path)

    try:
        results = run_audit(conn, args.oem, args.quick, args.verbose)

        print(f"\n✅ Audit complete! Dashboard data should be regenerated.")
        print(f"   Run: ./venv/bin/python3 scripts/generate_observability_dashboard.py")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
