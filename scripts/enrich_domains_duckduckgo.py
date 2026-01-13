#!/usr/bin/env python3
"""
DuckDuckGo Domain Enrichment for Dealer-Scraper
================================================
Searches DuckDuckGo to find company domains for contractors without websites.

Usage:
    python scripts/enrich_domains_duckduckgo.py --batch 10 --dry-run
    python scripts/enrich_domains_duckduckgo.py --batch 100
    python scripts/enrich_domains_duckduckgo.py --all

Requirements:
    pip install duckduckgo-search

Author: Claude
Date: 2026-01-12
"""

import argparse
import sqlite3
import time
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    from duckduckgo_search import DDGS
except ImportError:
    print("ERROR: duckduckgo-search not installed")
    print("Run: pip install duckduckgo-search")
    exit(1)

# Config
DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"
DELAY_BETWEEN_SEARCHES = 2  # seconds (rate limit)


def normalize_domain(url: str) -> str:
    """Extract clean domain from URL."""
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def is_valid_company_domain(domain: str, company_name: str) -> bool:
    """Check if domain looks like a company website (not social media, etc.)."""
    if not domain:
        return False

    # Exclude common non-company domains
    excluded = [
        "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "youtube.com", "yelp.com", "bbb.org", "yellowpages.com",
        "mapquest.com", "google.com", "apple.com", "amazon.com",
        "angi.com", "angieslist.com", "homeadvisor.com", "thumbtack.com",
        "houzz.com", "nextdoor.com", "manta.com", "chamberofcommerce.com",
        "wikipedia.org", "indeed.com", "glassdoor.com"
    ]

    for exc in excluded:
        if exc in domain:
            return False

    return True


def search_company_domain(company_name: str, city: str, state: str) -> dict:
    """Search DuckDuckGo for company domain."""
    query = f'"{company_name}" {city} {state} HVAC'

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return {"found": False, "query": query}

        # Find first valid company domain
        for r in results:
            url = r.get("href", "")
            domain = normalize_domain(url)

            if is_valid_company_domain(domain, company_name):
                return {
                    "found": True,
                    "domain": domain,
                    "url": url,
                    "title": r.get("title", ""),
                    "query": query
                }

        return {"found": False, "query": query, "results_count": len(results)}

    except Exception as e:
        return {"found": False, "error": str(e), "query": query}


def get_contractors_without_domains(db_path: str, limit: int = None) -> list:
    """Get contractors that need domain enrichment."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT id, company_name, city, state
        FROM contractors
        WHERE is_deleted = 0
            AND (primary_domain IS NULL OR primary_domain = '')
            AND company_name IS NOT NULL
            AND city IS NOT NULL
            AND state IS NOT NULL
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return rows


def update_contractor_domain(db_path: str, contractor_id: int, domain: str, url: str):
    """Update contractor with found domain."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE contractors
        SET primary_domain = ?,
            domain_verified_at = ?,
            domain_is_valid = 1,
            domain_check_status = 'duckduckgo_search'
        WHERE id = ?
    """, (domain, datetime.utcnow().isoformat(), contractor_id))

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Enrich contractor domains via DuckDuckGo')
    parser.add_argument('--db-path', default=str(DB_PATH), help='Path to database')
    parser.add_argument('--batch', type=int, default=10, help='Batch size')
    parser.add_argument('--all', action='store_true', help='Process all')
    parser.add_argument('--dry-run', action='store_true', help='Dry run only')

    args = parser.parse_args()

    print("\n" + "="*70)
    print(" DUCKDUCKGO DOMAIN ENRICHMENT")
    print("="*70)

    # Get contractors
    limit = None if args.all else args.batch
    contractors = get_contractors_without_domains(args.db_path, limit)

    print(f"\nContractors to enrich: {len(contractors)}")

    if args.dry_run:
        print("\n[DRY RUN] First 5 contractors:")
        for c in contractors[:5]:
            print(f"  {c['company_name'][:40]:40s} | {c['city']}, {c['state']}")
        return

    # Process
    found_count = 0
    not_found_count = 0
    error_count = 0

    for i, c in enumerate(contractors, 1):
        print(f"\n[{i}/{len(contractors)}] {c['company_name'][:50]}")
        print(f"  Location: {c['city']}, {c['state']}")

        result = search_company_domain(c['company_name'], c['city'], c['state'])

        if result.get("found"):
            domain = result["domain"]
            print(f"  ✅ Found: {domain}")

            update_contractor_domain(args.db_path, c['id'], domain, result.get("url", ""))
            found_count += 1
        elif result.get("error"):
            print(f"  ❌ Error: {result['error']}")
            error_count += 1
        else:
            print(f"  ⚠️  Not found")
            not_found_count += 1

        # Rate limit
        time.sleep(DELAY_BETWEEN_SEARCHES)

    # Summary
    print("\n" + "="*70)
    print(" ENRICHMENT SUMMARY")
    print("="*70)
    print(f"  Total processed: {len(contractors)}")
    print(f"  ✅ Found: {found_count} ({found_count/len(contractors)*100:.1f}%)")
    print(f"  ⚠️  Not found: {not_found_count}")
    print(f"  ❌ Errors: {error_count}")


if __name__ == "__main__":
    main()
