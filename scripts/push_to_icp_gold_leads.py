#!/usr/bin/env python3
"""
Push OEM dealer data to Supabase icp_gold_leads table

This script takes scraped OEM dealer data and pushes it to the
icp_gold_leads table in Supabase for sales-agent to process.

Philosophy: NAME IS THE ANCHOR
- ALL records with company names go to Supabase
- Sales-agent team handles deduplication on their side
- We set has_hvac=True for HVAC OEMs, etc.

Usage:
    ./venv/bin/python3 scripts/push_to_icp_gold_leads.py --oem carrier
    ./venv/bin/python3 scripts/push_to_icp_gold_leads.py --all

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
"""

import sys
import os
import json
import argparse
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import requests

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

OEM_DATA_DIR = Path("output/oem_data")

# Map OEM keys to their data directories and capability flags
OEM_CONFIG = {
    "carrier": {"name": "Carrier", "category": "HVAC", "has_hvac": True},
    "trane": {"name": "Trane", "category": "HVAC", "has_hvac": True},
    "mitsubishi": {"name": "Mitsubishi", "category": "HVAC", "has_hvac": True},
    "rheem": {"name": "Rheem", "category": "HVAC", "has_hvac": True},
    "york": {"name": "York", "category": "HVAC", "has_hvac": True},
    "generac": {"name": "Generac", "category": "Generator", "has_energy": True},
    "briggs": {"name": "Briggs & Stratton", "category": "Generator", "has_energy": True},
    "cummins": {"name": "Cummins", "category": "Generator", "has_energy": True},
    "kohler": {"name": "Kohler", "category": "Generator", "has_energy": True},
    "schneider": {"name": "Schneider Electric", "category": "Electrical", "has_electrical": True},
    "tesla": {"name": "Tesla", "category": "Solar/Battery", "has_solar": True, "has_energy": True},
    "sma": {"name": "SMA", "category": "Inverter", "has_solar": True},
    "enphase": {"name": "Enphase", "category": "Microinverter", "has_solar": True},
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

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

    # Format as (XXX) XXX-XXXX for readability
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def find_latest_data_file(oem_key: str) -> Optional[Path]:
    """Find the most recent JSON file for an OEM."""
    oem_dir = OEM_DATA_DIR / oem_key

    if not oem_dir.exists():
        return None

    # Look for national files first, then checkpoints, then any JSON
    patterns = [
        f"{oem_key}_national_*.json",
        f"{oem_key}_checkpoint_*.json",
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
        # Check for nested structure (checkpoints use 'dealers')
        if 'dealers' in data:
            return data['dealers']
        elif 'contractors' in data:
            return data['contractors']
        elif 'data' in data:
            return data['data']

    return []


def transform_dealer_to_lead(dealer: Dict, oem_key: str, oem_config: Dict) -> Dict:
    """
    Transform a dealer record to icp_gold_leads table format.

    IMPORTANT: ALL records with a company name go to Supabase.
    NAME IS THE ANCHOR.
    """

    # Extract fields with fallbacks for different schemas
    name = dealer.get('name') or dealer.get('company_name') or dealer.get('dealer_name', '')
    phone = dealer.get('phone') or dealer.get('primary_phone', '')
    email = dealer.get('email') or dealer.get('primary_email', '')
    website = dealer.get('website') or dealer.get('website_url', '')

    # Normalize phone
    normalized_phone = normalize_phone(phone)

    # Build the lead record matching icp_gold_leads schema
    # NOTE: trade_count is a GENERATED column - do not include it
    # NOTE: id must be explicitly provided (no DEFAULT in table)
    lead = {
        'id': str(uuid.uuid4()),  # Generate UUID for each record
        'company_name': name,
        'contact_phone': normalized_phone,
        'contact_email': email if email else None,
        'source': f"OEM:{oem_config['name']}",  # Track which OEM
        'status_label': 'new',
        'icp_tier': 'silver',  # Default tier (lowercase required by CHECK constraint)
        'coperniq_score': 50,  # Default score
        'qualification_score': 0,  # Sales-agent will enrich
        # trade_count is auto-computed from has_* flags

        # Capability flags based on OEM category
        'has_hvac': oem_config.get('has_hvac', False),
        'has_plumbing': False,  # OEMs don't typically have plumbing
        'has_electrical': oem_config.get('has_electrical', False),
        'has_solar': oem_config.get('has_solar', False),
        'has_energy': oem_config.get('has_energy', False),

        'is_atl': False,  # Sales-agent determines ATL status
        'created_at': datetime.now().isoformat(),
    }

    return lead


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PUSH LOGIC
# ═══════════════════════════════════════════════════════════════════════════

def push_oem_to_supabase(supabase_url: str, service_key: str, oem_key: str) -> Dict[str, int]:
    """
    Push a single OEM's data to Supabase icp_gold_leads.

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

    # Transform to leads format - ALL records with names go through
    leads = []
    skipped_no_name = 0
    for dealer in dealers:
        try:
            lead = transform_dealer_to_lead(dealer, oem_key, oem_config)
            if lead['company_name']:  # Must have a name - this is the only filter
                leads.append(lead)
            else:
                skipped_no_name += 1
        except Exception as e:
            print(f"  ⚠️  Transform error: {e}")

    print(f"  ✅ Transformed {len(leads)} valid leads")
    if skipped_no_name > 0:
        print(f"  ⚠️  Skipped {skipped_no_name} records with no company name")

    # Push to Supabase in batches
    batch_size = 100
    inserted = 0
    skipped = 0
    errors = 0

    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }

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
        'loaded': len(dealers),
        'inserted': inserted,
        'skipped': skipped,
        'errors': errors
    }


def main():
    parser = argparse.ArgumentParser(description="Push OEM data to Supabase icp_gold_leads")
    parser.add_argument('--oem', help="Specific OEM to push (e.g., 'carrier')")
    parser.add_argument('--all', action='store_true', help="Push all available OEMs")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be pushed")

    args = parser.parse_args()

    if not args.oem and not args.all:
        parser.print_help()
        print("\nExample: ./venv/bin/python3 scripts/push_to_icp_gold_leads.py --oem carrier")
        return 1

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return 1

    print("\n" + "="*60)
    print("  SUPABASE ICP_GOLD_LEADS PUSH")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Target: {supabase_url}")
    print(f"  Table: icp_gold_leads")

    if args.dry_run:
        print("  Mode: DRY RUN (no data will be pushed)")
        return 0

    # Determine which OEMs to push
    if args.all:
        oems_to_push = list(OEM_CONFIG.keys())
    else:
        oems_to_push = [args.oem.lower()]

    # Push each OEM
    total_stats = {'loaded': 0, 'inserted': 0, 'skipped': 0, 'errors': 0}

    for oem_key in oems_to_push:
        stats = push_oem_to_supabase(supabase_url, supabase_key, oem_key)
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
