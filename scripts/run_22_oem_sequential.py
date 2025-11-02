#!/usr/bin/env python3
"""
22-OEM Sequential Execution System
Scrapes all 22 OEM networks with checkpoints and full validation.

NOTE: Currently 17 OEMs are production-ready. Missing:
- Generac (needs conversion to unified framework)
- Tesla (needs conversion to unified framework)
- Enphase (needs conversion to unified framework)
- Tigo (placeholder, needs implementation)
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from fuzzywuzzy import fuzz
import pandas as pd
from typing import List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# OEM Priority Order (HVAC → Generators → Solar → Battery)
# Updated to reflect 18 production-ready OEMs (22 planned, 4 not yet implemented)
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC Systems (6 OEMs)
    "Carrier",
    "Trane",
    "Lennox",
    "York",
    "Rheem",
    "Mitsubishi",

    # Tier 2: Backup Generators (3 OEMs - Generac needs conversion)
    "Kohler",
    "Cummins",
    "Briggs & Stratton",

    # Tier 3: Solar Inverters (8 OEMs - Enphase/Tigo not ready, ABB/Delta commented out)
    "Fronius",
    "SMA",
    "Sol-Ark",
    "GoodWe",
    "Growatt",
    "Sungrow",
    "SolarEdge",
    # "ABB",      # Commented out in scraper (FIMER acquisition)
    # "Delta",    # Commented out in scraper (no public locator)
    # "Tigo",     # Commented out in scraper (needs implementation)

    # Tier 4: Battery Storage (1 OEM - Tesla needs conversion)
    "SimpliPhi"
    # "Tesla",    # Needs conversion to unified framework
]

# Configuration
CHECKPOINT_INTERVAL = 25
TODAY = datetime.now().strftime("%Y%m%d")


def delete_checkpoints(oem_name: str) -> None:
    """
    Delete all checkpoint files for an OEM (fresh start policy).

    Args:
        oem_name: Name of OEM (e.g., "Carrier", "Briggs & Stratton")
    """
    # Normalize OEM name: lowercase, replace spaces with _, replace & with "and"
    oem_dir_name = oem_name.lower().replace(" ", "_").replace("&", "and")
    checkpoint_dir = PROJECT_ROOT / "output" / "oem_data" / oem_dir_name / "checkpoints"

    if checkpoint_dir.exists():
        checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoint_files:
            print(f"  → Deleting {len(checkpoint_files)} old checkpoints...")
            for checkpoint_file in checkpoint_files:
                checkpoint_file.unlink()
            print(f"  ✓ Checkpoints deleted")
    else:
        print(f"  → No existing checkpoints")


def prompt_user_confirmation(oem_name: str, oem_index: int, total_oems: int) -> str:
    """
    Prompt user for confirmation before running OEM scraper.

    Args:
        oem_name: Name of OEM (e.g., "Carrier")
        oem_index: Index in priority list (0-based)
        total_oems: Total number of OEMs

    Returns:
        'y' = proceed, 'n' = exit script, 'skip' = skip this OEM
    """
    print(f"\n{'='*80}")
    print(f"OEM {oem_index + 1}/{total_oems}: {oem_name}")
    print(f"{'='*80}")
    print(f"Target: 264 ZIP codes (all 50 states)")
    print(f"Output: output/oem_data/{oem_name.lower().replace(' ', '_').replace('&', 'and')}/")
    print()

    while True:
        response = input(f"Ready to run {oem_name} scraper? (y/n/skip): ").strip().lower()

        if response in ['y', 'yes']:
            return 'y'
        elif response in ['n', 'no']:
            return 'n'
        elif response in ['skip', 's']:
            return 'skip'
        else:
            print("Invalid input. Enter y/n/skip:")


def deduplicate_dealers(dealers: List[Dict], oem_name: str) -> Tuple[List[Dict], Dict]:
    """
    Deduplicate dealers using multi-signal matching (phone → domain → fuzzy name).

    Args:
        dealers: List of dealer dictionaries
        oem_name: Name of OEM for logging

    Returns:
        (deduplicated_dealers, stats_dict)
    """
    print(f"  → Running deduplication pipeline...")

    initial_count = len(dealers)
    stats = {
        'initial': initial_count,
        'phone_dupes': 0,
        'domain_dupes': 0,
        'fuzzy_dupes': 0,
        'fuzzy_matches': []
    }

    # Phase 1: Phone normalization deduplication
    phone_map = {}
    dealers_after_phone = []

    for dealer in dealers:
        phone = dealer.get('phone', '')
        # Normalize: strip to 10 digits
        normalized_phone = ''.join(filter(str.isdigit, phone))[-10:] if phone else ''

        if normalized_phone and normalized_phone in phone_map:
            stats['phone_dupes'] += 1
        else:
            if normalized_phone:
                phone_map[normalized_phone] = dealer
            dealers_after_phone.append(dealer)

    print(f"     - Phone dedup: {initial_count} → {len(dealers_after_phone)} (-{stats['phone_dupes']}, {stats['phone_dupes']/initial_count*100:.1f}%)")

    # Phase 2: Domain deduplication
    domain_map = {}
    dealers_after_domain = []

    for dealer in dealers_after_phone:
        domain = dealer.get('domain', '')
        # Extract root domain
        root_domain = domain.replace('www.', '').lower() if domain else ''

        if root_domain and root_domain in domain_map:
            stats['domain_dupes'] += 1
        else:
            if root_domain:
                domain_map[root_domain] = dealer
            dealers_after_domain.append(dealer)

    print(f"     - Domain dedup: {len(dealers_after_phone)} → {len(dealers_after_domain)} (-{stats['domain_dupes']}, {stats['domain_dupes']/len(dealers_after_phone)*100:.1f}%)")

    # Phase 3: Fuzzy name matching (85% threshold, same state)
    dealers_final = []
    name_state_map = {}

    for dealer in dealers_after_domain:
        name = dealer.get('name', '').strip().lower()
        state = dealer.get('state', '').strip().upper()

        if not name:
            dealers_final.append(dealer)
            continue

        # Check for fuzzy matches in same state
        found_match = False
        for existing_name, existing_dealer in name_state_map.items():
            if existing_dealer.get('state', '').strip().upper() == state:
                similarity = fuzz.ratio(name, existing_name)
                if similarity >= 85:
                    stats['fuzzy_dupes'] += 1
                    stats['fuzzy_matches'].append({
                        'name1': existing_dealer.get('name'),
                        'name2': dealer.get('name'),
                        'similarity': similarity,
                        'state': state
                    })
                    found_match = True
                    break

        if not found_match:
            name_state_map[name] = dealer
            dealers_final.append(dealer)

    print(f"     - Fuzzy name dedup: {len(dealers_after_domain)} → {len(dealers_final)} (-{stats['fuzzy_dupes']}, {stats['fuzzy_dupes']/len(dealers_after_domain)*100:.1f}%)")

    stats['final'] = len(dealers_final)
    total_dedup_rate = (initial_count - len(dealers_final)) / initial_count * 100
    print(f"  ✓ Deduplication complete: {initial_count} → {len(dealers_final)} (dedup rate: {total_dedup_rate:.1f}%)")

    return dealers_final, stats
