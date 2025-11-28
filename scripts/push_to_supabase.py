#!/usr/bin/env python3
"""
Push OEM dealer data to Supabase (sales-agent project)

This script takes scraped OEM dealer data and pushes it to the
oem_leads table in Supabase for sales-agent to process.

Usage:
    ./venv/bin/python3 scripts/push_to_supabase.py --oem carrier
    ./venv/bin/python3 scripts/push_to_supabase.py --oem schneider
    ./venv/bin/python3 scripts/push_to_supabase.py --all  # Push all available OEMs

Requirements:
    - oem_leads table must exist in Supabase (run database/create_oem_leads_table.sql)
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
"""

import sys
import os
import json
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase package not installed. Run: ./venv/bin/pip install supabase")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

OEM_DATA_DIR = Path("output/oem_data")

# Map OEM keys to their data directories and names
OEM_CONFIG = {
    "carrier": {"name": "Carrier", "category": "HVAC"},
    "trane": {"name": "Trane", "category": "HVAC"},
    "mitsubishi": {"name": "Mitsubishi", "category": "HVAC"},
    "generac": {"name": "Generac", "category": "Generator"},
    "rheem": {"name": "Rheem", "category": "HVAC"},
    "briggs": {"name": "Briggs & Stratton", "category": "Generator"},
    "cummins": {"name": "Cummins", "category": "Generator"},
    "schneider": {"name": "Schneider Electric", "category": "Electrical"},
    "york": {"name": "York", "category": "HVAC"},
    "tesla": {"name": "Tesla", "category": "Solar/Battery"},
    "sma": {"name": "SMA", "category": "Inverter"},
    "enphase": {"name": "Enphase", "category": "Microinverter"},
    "kohler": {"name": "Kohler", "category": "Generator"},
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def normalize_name(name: str) -> str:
    """Normalize company name for deduplication matching."""
    if not name:
        return ""
    # Lowercase, remove punctuation, collapse spaces
    normalized = name.lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def normalize_phone(phone: str) -> Optional[str]:
    """Normalize phone to 10 digits, exclude toll-free."""
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

    return digits


def find_latest_data_file(oem_key: str) -> Optional[Path]:
    """Find the most recent JSON file for an OEM."""
    oem_dir = OEM_DATA_DIR / oem_key

    if not oem_dir.exists():
        return None

    # Look for national files first, then any JSON
    patterns = [
        f"{oem_key}_national_*.json",
        f"{oem_key}_*.json",
        "*.json"
    ]

    for pattern in patterns:
        files = list(oem_dir.glob(pattern))
        if files:
            # Return most recently modified
            return max(files, key=lambda f: f.stat().st_mtime)

    return None


def load_oem_data(oem_key: str) -> List[Dict]:
    """Load dealer data from JSON file."""
    data_file = find_latest_data_file(oem_key)

    if not data_file:
        print(f"  ⚠️  No data file found for {oem_key}")
        return []

    print(f"  📁 Loading: {data_file.name}")

    with open(data_file) as f:
        data = json.load(f)

    # Handle different JSON structures
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Check for nested structure (Schneider uses 'contractors')
        if 'contractors' in data:
            return data['contractors']
        elif 'dealers' in data:
            return data['dealers']
        elif 'data' in data:
            return data['data']

    return []


def transform_dealer_to_lead(dealer: Dict, oem_key: str, oem_config: Dict, import_batch: str) -> Dict:
    """
    Transform a dealer record to oem_leads table format.

    IMPORTANT: ALL records with a company name go to Supabase.
    No aggressive deduplication here - sales-agent team handles that.
    NAME IS THE ANCHOR.
    """

    # Extract fields with fallbacks for different schemas
    name = dealer.get('name') or dealer.get('company_name') or dealer.get('dealer_name', '')
    phone = dealer.get('phone') or dealer.get('primary_phone', '')
    email = dealer.get('email') or dealer.get('primary_email', '')
    website = dealer.get('website') or dealer.get('website_url', '')

    # Address fields
    street = dealer.get('street') or dealer.get('address', '')
    city = dealer.get('city', '')
    state = dealer.get('state', '')
    zip_code = dealer.get('zip') or dealer.get('zip_code', '')

    # Tier/program info
    tier = dealer.get('tier') or dealer.get('dealer_tier') or dealer.get('certification_level', '')
    program = dealer.get('program') or dealer.get('dealer_program', '')

    # Normalize phone (but keep original if present)
    normalized_phone = normalize_phone(phone)
    raw_phone = phone if phone else None

    return {
        'company_name': name,
        'normalized_name': normalize_name(name),
        'phone': normalized_phone if normalized_phone else raw_phone,  # Keep raw if normalization fails
        'email': email if email else None,
        'website': website if website else None,
        'street': street if street else None,
        'city': city if city else None,
        'state': state if state else None,
        'zip': str(zip_code) if zip_code else None,
        'oem_name': oem_config['name'],
        'oem_tier': tier if tier else None,
        'oem_program': program if program else None,
        'has_phone': bool(phone),  # True if ANY phone was provided
        'has_email': bool(email),
        'has_website': bool(website),
        'enrichment_status': 'pending',
        'crm_status': 'not_synced',
        'scraped_at': datetime.now().isoformat(),
        'source_file': str(find_latest_data_file(oem_key)),
        'import_batch': import_batch,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PUSH LOGIC
# ═══════════════════════════════════════════════════════════════════════════

def push_oem_to_supabase(supabase: Client, oem_key: str) -> Dict[str, int]:
    """
    Push a single OEM's data to Supabase.

    Philosophy: ALL records with company names go to Supabase.
    Sales-agent team handles deduplication with their own logic.
    NAME IS THE ANCHOR.
    """

    if oem_key not in OEM_CONFIG:
        print(f"  ❌ Unknown OEM: {oem_key}")
        return {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    oem_config = OEM_CONFIG[oem_key]
    print(f"\n{'='*60}")
    print(f"  PUSHING: {oem_config['name']} ({oem_config['category']})")
    print(f"{'='*60}")

    # Load data
    dealers = load_oem_data(oem_key)
    if not dealers:
        return {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    print(f"  📊 Loaded {len(dealers)} records")

    # Create import batch ID for this push
    import_batch = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Transform to leads format - ALL records with names go through
    leads = []
    skipped_no_name = 0
    for dealer in dealers:
        try:
            lead = transform_dealer_to_lead(dealer, oem_key, oem_config, import_batch)
            if lead['company_name']:  # Must have a name - this is the only filter
                leads.append(lead)
            else:
                skipped_no_name += 1
        except Exception as e:
            print(f"  ⚠️  Transform error: {e}")

    print(f"  ✅ Transformed {len(leads)} valid leads")
    if skipped_no_name > 0:
        print(f"  ⚠️  Skipped {skipped_no_name} records with no company name")

    # Push to Supabase in batches - use insert (not upsert)
    # Let the unique constraint handle any exact duplicates
    batch_size = 100
    inserted = 0
    skipped = 0
    errors = 0

    for i in range(0, len(leads), batch_size):
        batch = leads[i:i + batch_size]
        try:
            # Use insert - sales-agent handles dedup
            result = supabase.table('oem_leads').insert(batch).execute()
            inserted += len(batch)

            if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(leads):
                print(f"  📤 Progress: {min(i + batch_size, len(leads))}/{len(leads)}")

        except Exception as e:
            error_msg = str(e)
            if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
                # If batch has duplicates, try inserting one by one
                for lead in batch:
                    try:
                        supabase.table('oem_leads').insert(lead).execute()
                        inserted += 1
                    except Exception as inner_e:
                        if 'duplicate' in str(inner_e).lower() or 'unique' in str(inner_e).lower():
                            skipped += 1
                        else:
                            errors += 1
            else:
                errors += len(batch)
                print(f"  ❌ Batch error: {error_msg[:100]}")

    print(f"\n  📊 Results:")
    print(f"     Inserted: {inserted}")
    print(f"     Skipped (exact dups): {skipped}")
    print(f"     Errors: {errors}")

    return {
        'loaded': len(dealers),
        'inserted': inserted,
        'skipped': skipped,
        'errors': errors
    }


def main():
    parser = argparse.ArgumentParser(description="Push OEM data to Supabase")
    parser.add_argument('--oem', help="Specific OEM to push (e.g., 'carrier')")
    parser.add_argument('--all', action='store_true', help="Push all available OEMs")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be pushed without pushing")

    args = parser.parse_args()

    if not args.oem and not args.all:
        parser.print_help()
        print("\nExample: ./venv/bin/python3 scripts/push_to_supabase.py --oem carrier")
        return 1

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return 1

    print("\n" + "="*60)
    print("  SUPABASE OEM LEADS PUSH")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Target: {supabase_url}")

    if args.dry_run:
        print("  Mode: DRY RUN (no data will be pushed)")
        return 0

    # Connect to Supabase
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("  ✅ Connected to Supabase")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return 1

    # Determine which OEMs to push
    if args.all:
        oems_to_push = list(OEM_CONFIG.keys())
    else:
        oems_to_push = [args.oem.lower()]

    # Push each OEM
    total_stats = {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    for oem_key in oems_to_push:
        stats = push_oem_to_supabase(supabase, oem_key)
        for key in total_stats:
            total_stats[key] += stats[key]

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
