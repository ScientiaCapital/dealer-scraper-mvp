#!/usr/bin/env python3
"""
Push OEM contractor data from SQLite to Supabase icp_gold_leads

This script pulls from pipeline.db (the master SQLite database) and pushes
to icp_gold_leads in Supabase for sales-agent to enrich and process.

Philosophy: NAME IS THE ANCHOR
- ALL records with company names go to Supabase
- Phone is OPTIONAL (sales-agent enriches with Hunter/Apollo)
- Sales-agent team handles deduplication on their side

Usage:
    ./venv/bin/python3 scripts/push_sqlite_to_supabase.py --oem carrier
    ./venv/bin/python3 scripts/push_sqlite_to_supabase.py --all
    ./venv/bin/python3 scripts/push_sqlite_to_supabase.py --all --dry-run

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
    - output/pipeline.db with OEM data
"""

import sys
import os
import argparse
import sqlite3
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import requests

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

SQLITE_DB = Path("output/pipeline.db")

# Map OEM names to capability flags
OEM_CAPABILITIES = {
    "Carrier": {"has_hvac": True},
    "Trane": {"has_hvac": True},
    "Mitsubishi": {"has_hvac": True},
    "Rheem": {"has_hvac": True},
    "York": {"has_hvac": True},
    "Generac": {"has_energy": True},
    "Briggs & Stratton": {"has_energy": True},
    "Cummins": {"has_energy": True},
    "Kohler": {"has_energy": True},
    "Schneider Electric": {"has_electrical": True},
    "Tesla": {"has_solar": True, "has_energy": True},
    "SMA": {"has_solar": True},
    "Enphase": {"has_solar": True},
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def normalize_phone(phone: str) -> Optional[str]:
    """Normalize phone to (XXX) XXX-XXXX format, exclude toll-free."""
    if not phone:
        return None

    # Extract digits only
    digits = re.sub(r'\D', '', phone)

    # Remove country code if present
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Must be exactly 10 digits
    if len(digits) != 10:
        return None

    # Exclude toll-free numbers
    toll_free_prefixes = ['800', '888', '877', '866', '855', '844', '833']
    if digits[:3] in toll_free_prefixes:
        return None

    # Format as (XXX) XXX-XXXX for readability
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def get_oem_contractors(conn: sqlite3.Connection, oem_name: str) -> List[Dict]:
    """Get all contractors for a specific OEM from SQLite."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.company_name,
            c.primary_phone,
            c.primary_email,
            c.website_url,
            c.city,
            c.state,
            oc.certification_tier
        FROM contractors c
        JOIN oem_certifications oc ON c.id = oc.contractor_id
        WHERE oc.oem_name = ?
        AND c.is_deleted = 0
        AND c.company_name IS NOT NULL
        AND c.company_name != ''
    """, (oem_name,))

    columns = ['company_name', 'primary_phone', 'primary_email', 'website_url',
               'city', 'state', 'certification_tier']
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_all_oems(conn: sqlite3.Connection) -> List[str]:
    """Get list of all OEMs in the database."""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT oem_name FROM oem_certifications ORDER BY oem_name")
    return [row[0] for row in cur.fetchall()]


def transform_to_lead(contractor: Dict, oem_name: str) -> Dict:
    """Transform contractor record to icp_gold_leads format."""
    caps = OEM_CAPABILITIES.get(oem_name, {})

    return {
        'id': str(uuid.uuid4()),
        'company_name': contractor['company_name'],
        'contact_phone': normalize_phone(contractor['primary_phone']),
        'contact_email': contractor['primary_email'] if contractor['primary_email'] else None,
        'source': f"OEM:{oem_name}",
        'status_label': 'new',
        'icp_tier': 'silver',  # lowercase required by CHECK constraint
        'coperniq_score': 50,
        'qualification_score': 0,
        # Capability flags from OEM type
        'has_hvac': caps.get('has_hvac', False),
        'has_plumbing': False,
        'has_electrical': caps.get('has_electrical', False),
        'has_solar': caps.get('has_solar', False),
        'has_energy': caps.get('has_energy', False),
        'is_atl': False,
        'created_at': datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PUSH LOGIC
# ═══════════════════════════════════════════════════════════════════════════

def push_oem_to_supabase(supabase_url: str, service_key: str,
                         conn: sqlite3.Connection, oem_name: str,
                         dry_run: bool = False) -> Dict[str, int]:
    """Push a single OEM's contractors to Supabase."""

    print(f"\n{'='*60}")
    print(f"  PUSHING: {oem_name}")
    print(f"{'='*60}")

    # Get contractors from SQLite
    contractors = get_oem_contractors(conn, oem_name)
    if not contractors:
        print(f"  ⚠️  No contractors found for {oem_name}")
        return {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    print(f"  📊 Found {len(contractors)} contractors in SQLite")

    # Transform to leads
    leads = [transform_to_lead(c, oem_name) for c in contractors]

    # Count with/without phone
    with_phone = sum(1 for l in leads if l['contact_phone'])
    print(f"  📞 {with_phone}/{len(leads)} have phone ({with_phone/len(leads)*100:.0f}%)")

    if dry_run:
        print(f"  🏃 DRY RUN - would insert {len(leads)} records")
        return {'loaded': len(contractors), 'inserted': 0, 'skipped': 0, 'errors': 0}

    # Push to Supabase in batches
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }

    batch_size = 100
    inserted = 0
    skipped = 0
    errors = 0

    for i in range(0, len(leads), batch_size):
        batch = leads[i:i + batch_size]
        try:
            response = requests.post(
                f'{supabase_url}/rest/v1/icp_gold_leads',
                headers=headers,
                json=batch
            )

            if response.status_code in [200, 201]:
                inserted += len(batch)
            elif response.status_code == 409:  # Conflict/duplicate
                # Try inserting one by one
                for lead in batch:
                    try:
                        single_resp = requests.post(
                            f'{supabase_url}/rest/v1/icp_gold_leads',
                            headers=headers,
                            json=lead
                        )
                        if single_resp.status_code in [200, 201]:
                            inserted += 1
                        elif single_resp.status_code == 409:
                            skipped += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1
            else:
                errors += len(batch)
                print(f"  ❌ Batch error: {response.status_code} - {response.text[:100]}")

            if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(leads):
                print(f"  📤 Progress: {min(i + batch_size, len(leads))}/{len(leads)}")

        except Exception as e:
            errors += len(batch)
            print(f"  ❌ Request error: {str(e)[:100]}")

    print(f"\n  📊 Results:")
    print(f"     Inserted: {inserted}")
    print(f"     Skipped (duplicates): {skipped}")
    print(f"     Errors: {errors}")

    return {
        'loaded': len(contractors),
        'inserted': inserted,
        'skipped': skipped,
        'errors': errors
    }


def main():
    parser = argparse.ArgumentParser(description="Push SQLite OEM data to Supabase")
    parser.add_argument('--oem', help="Specific OEM to push (e.g., 'Carrier')")
    parser.add_argument('--all', action='store_true', help="Push all available OEMs")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be pushed")

    args = parser.parse_args()

    if not args.oem and not args.all:
        parser.print_help()
        print("\nExample: ./venv/bin/python3 scripts/push_sqlite_to_supabase.py --oem Carrier")
        print("         ./venv/bin/python3 scripts/push_sqlite_to_supabase.py --all")
        return 1

    # Check SQLite database exists
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found: {SQLITE_DB}")
        return 1

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return 1

    print("\n" + "="*60)
    print("  SQLITE → SUPABASE PUSH")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Source: {SQLITE_DB}")
    print(f"  Target: {supabase_url}")
    print(f"  Table: icp_gold_leads")
    if args.dry_run:
        print("  Mode: DRY RUN")

    # Connect to SQLite
    conn = sqlite3.connect(SQLITE_DB)

    # Determine which OEMs to push
    if args.all:
        oems_to_push = get_all_oems(conn)
        print(f"  OEMs to push: {len(oems_to_push)}")
    else:
        oems_to_push = [args.oem]

    # Push each OEM
    total_stats = {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    for oem_name in oems_to_push:
        stats = push_oem_to_supabase(supabase_url, supabase_key, conn, oem_name, args.dry_run)
        for key in total_stats:
            total_stats[key] += stats[key]

    conn.close()

    # Final summary
    print("\n" + "="*60)
    print("  PUSH COMPLETE")
    print("="*60)
    print(f"  Total loaded: {total_stats['loaded']}")
    print(f"  Total inserted: {total_stats['inserted']}")
    print(f"  Total skipped: {total_stats['skipped']}")
    print(f"  Total errors: {total_stats['errors']}")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
