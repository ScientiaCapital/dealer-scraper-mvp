#!/usr/bin/env python3
"""
Multi-State License Cross-Reference with Overlap Tracking

Matches contractors across:
- ALL state licenses (CA, TX, FL, NYC)
- ALL OEM dealer networks (Generac, Tesla, Enphase, etc.)

Identifies:
1. Contractors with licenses in multiple states
2. Contractors in multiple OEM networks
3. Contractors in BOTH license databases AND OEM networks (HIGHEST VALUE)

Adds overlap tracking columns:
- num_overlaps: Total count of sources (OEMs + state licenses)
- overlap_sources: List of all sources (e.g., "Generac, Tesla, CA-CSLB, TX-TDLR")

Usage:
    python3 scripts/crossref_multi_state_licenses.py

Inputs:
    - output/california_icp_master_20251101.csv
    - output/state_licenses/texas/tx_tdlr_processed_20251031.csv
    - output/state_licenses/florida/fl_dbpr_all_licenses_20251031.csv
    - output/state_licenses/new_york/nyc_dob_licenses_20251031.csv
    - output/grandmaster_list_expanded_20251029.csv

Outputs:
    - output/grandmaster_multi_state_enriched_20251101.csv (master with overlaps)
    - output/high_overlap_contractors_20251101.csv (4+ overlaps - HOTTEST)
    - output/multi_state_licensed_20251101.csv (licensed in 2+ states)
    - output/multi_oem_multi_state_20251101.csv (2+ OEMs + 2+ states - UNICORNS)
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# Input files
CA_LICENSE_FILE = OUTPUT_DIR / "california_icp_master_20251101.csv"
TX_LICENSE_FILE = OUTPUT_DIR / "state_licenses/texas/tx_tdlr_processed_20251031.csv"
FL_LICENSE_FILE = OUTPUT_DIR / "state_licenses/florida/fl_dbpr_all_licenses_20251031.csv"
NYC_LICENSE_FILE = OUTPUT_DIR / "state_licenses/new_york/nyc_dob_licenses_20251031.csv"
OEM_DEALER_FILE = OUTPUT_DIR / "grandmaster_list_expanded_20251029.csv"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_phone(phone_str):
    """Normalize phone number to 10 digits."""
    if pd.isna(phone_str):
        return None

    digits = re.sub(r'\D', '', str(phone_str))

    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]

    if len(digits) == 10:
        return digits

    return None


def load_all_licenses():
    """
    Load and normalize all state license data.

    Returns DataFrame with columns:
        - phone_normalized
        - business_name
        - city
        - state
        - license_source (CA-CSLB, TX-TDLR, FL-DBPR, NYC-DOB)
        - license_number
        - license_status
        - license_classifications
    """
    all_licenses = []

    # California (CSLB)
    if CA_LICENSE_FILE.exists():
        print(f"Loading California licenses: {CA_LICENSE_FILE.name}")
        ca_df = pd.read_csv(CA_LICENSE_FILE)
        ca_df = ca_df[~ca_df['is_duplicate']].copy()  # Exclude duplicates

        ca_licenses = pd.DataFrame({
            'phone_normalized': ca_df['phone_normalized'],
            'business_name': ca_df['BusinessName'],
            'city': ca_df['City'],
            'state': 'CA',
            'license_source': 'CA-CSLB',
            'license_number': ca_df['LicenseNo'],
            'license_status': ca_df['PrimaryStatus'],
            'license_classifications': ca_df['Classifications(s)']
        })
        all_licenses.append(ca_licenses)
        print(f"  Loaded {len(ca_licenses):,} CA licenses")

    # Texas (TDLR)
    if TX_LICENSE_FILE.exists():
        print(f"Loading Texas licenses: {TX_LICENSE_FILE.name}")
        tx_df = pd.read_csv(TX_LICENSE_FILE)
        tx_df['phone_normalized'] = tx_df['phone'].apply(normalize_phone)

        tx_licenses = pd.DataFrame({
            'phone_normalized': tx_df['phone_normalized'],
            'business_name': tx_df['business_name'],
            'city': tx_df['city'],
            'state': 'TX',
            'license_source': 'TX-TDLR',
            'license_number': tx_df['license_number'],
            'license_status': tx_df['license_status'],
            'license_classifications': tx_df['license_type']
        })
        all_licenses.append(tx_licenses)
        print(f"  Loaded {len(tx_licenses):,} TX licenses")

    # Florida (DBPR)
    if FL_LICENSE_FILE.exists():
        print(f"Loading Florida licenses: {FL_LICENSE_FILE.name}")
        fl_df = pd.read_csv(FL_LICENSE_FILE, low_memory=False)
        fl_df['phone_normalized'] = fl_df['phone'].apply(normalize_phone)

        fl_licenses = pd.DataFrame({
            'phone_normalized': fl_df['phone_normalized'],
            'business_name': fl_df['business_name'],
            'city': fl_df['city'],
            'state': 'FL',
            'license_source': 'FL-DBPR',
            'license_number': fl_df['license_number'],
            'license_status': fl_df['license_status'],
            'license_classifications': fl_df['license_type']
        })
        all_licenses.append(fl_licenses)
        print(f"  Loaded {len(fl_licenses):,} FL licenses")

    # NYC (DOB)
    if NYC_LICENSE_FILE.exists():
        print(f"Loading NYC licenses: {NYC_LICENSE_FILE.name}")
        nyc_df = pd.read_csv(NYC_LICENSE_FILE)
        nyc_df['phone_normalized'] = nyc_df['phone'].apply(normalize_phone)

        nyc_licenses = pd.DataFrame({
            'phone_normalized': nyc_df['phone_normalized'],
            'business_name': nyc_df['business_name'],
            'city': nyc_df['city'],
            'state': 'NY',
            'license_source': 'NYC-DOB',
            'license_number': nyc_df['license_number'],
            'license_status': nyc_df['license_status'],
            'license_classifications': nyc_df['license_type']
        })
        all_licenses.append(nyc_licenses)
        print(f"  Loaded {len(nyc_licenses):,} NYC licenses")

    # Combine all licenses
    if not all_licenses:
        print("⚠️  No license files found")
        return pd.DataFrame()

    combined_df = pd.concat(all_licenses, ignore_index=True)
    print(f"\nTotal licenses loaded: {len(combined_df):,}")
    print(f"  Valid phones: {combined_df['phone_normalized'].notna().sum():,}")

    return combined_df


def match_contractors_across_all_sources(licenses_df, dealers_df):
    """
    Match contractors across all sources (licenses + OEM dealers).

    Returns DataFrame with overlap tracking:
        - num_overlaps: Count of sources
        - overlap_sources: List of all sources
    """
    print("\nMatching contractors across all sources...")

    # Normalize dealer phone numbers
    dealers_df['phone_normalized'] = dealers_df['phone'].apply(normalize_phone)

    # Build contractor registry by phone
    contractor_registry = {}

    # Add all dealers to registry
    print("  Processing OEM dealers...")
    for idx, dealer in dealers_df.iterrows():
        phone = dealer['phone_normalized']
        if not phone:
            continue

        if phone not in contractor_registry:
            contractor_registry[phone] = {
                'name': dealer['name'],
                'city': dealer.get('city', ''),
                'state': dealer.get('state', ''),
                'phone': dealer.get('phone', ''),
                'website': dealer.get('website', ''),
                'oem_sources': set(),
                'license_sources': set(),
                'all_sources': []
            }

        # Add OEM source
        oem_source = dealer.get('oem_source', '')
        if oem_source:
            contractor_registry[phone]['oem_sources'].add(oem_source)
            contractor_registry[phone]['all_sources'].append(oem_source)

    print(f"    {len(contractor_registry):,} unique phone numbers from OEM data")

    # Add all licenses to registry
    print("  Processing state licenses...")
    license_matches = 0

    for idx, lic in licenses_df.iterrows():
        phone = lic['phone_normalized']
        if not phone:
            continue

        if phone not in contractor_registry:
            contractor_registry[phone] = {
                'name': lic['business_name'],
                'city': lic['city'],
                'state': lic['state'],
                'phone': phone,
                'website': '',
                'oem_sources': set(),
                'license_sources': set(),
                'all_sources': []
            }

        # Add license source
        license_source = lic['license_source']
        if license_source not in contractor_registry[phone]['license_sources']:
            contractor_registry[phone]['license_sources'].add(license_source)
            contractor_registry[phone]['all_sources'].append(license_source)
            license_matches += 1

    print(f"    {license_matches:,} license records matched to contractors")
    print(f"    {len(contractor_registry):,} total unique contractors")

    # Convert to DataFrame
    print("\n  Calculating overlap statistics...")
    contractors_list = []

    for phone, data in contractor_registry.items():
        num_oems = len(data['oem_sources'])
        num_licenses = len(data['license_sources'])
        num_overlaps = num_oems + num_licenses

        # Format overlap sources
        overlap_sources = ', '.join(sorted(data['all_sources']))

        contractors_list.append({
            'phone': phone,
            'name': data['name'],
            'city': data['city'],
            'state': data['state'],
            'website': data['website'],
            'num_oems': num_oems,
            'num_licenses': num_licenses,
            'num_overlaps': num_overlaps,
            'oem_sources': ', '.join(sorted(data['oem_sources'])),
            'license_sources': ', '.join(sorted(data['license_sources'])),
            'overlap_sources': overlap_sources
        })

    contractors_df = pd.DataFrame(contractors_list)

    # Statistics
    print(f"\n  Overlap distribution:")
    print(f"    1 source: {(contractors_df['num_overlaps'] == 1).sum():,}")
    print(f"    2 sources: {(contractors_df['num_overlaps'] == 2).sum():,}")
    print(f"    3 sources: {(contractors_df['num_overlaps'] == 3).sum():,}")
    print(f"    4 sources: {(contractors_df['num_overlaps'] == 4).sum():,}")
    print(f"    5+ sources: {(contractors_df['num_overlaps'] >= 5).sum():,}")

    print(f"\n  High-value segments:")
    print(f"    Multi-OEM (2+): {(contractors_df['num_oems'] >= 2).sum():,}")
    print(f"    Multi-state licensed (2+): {(contractors_df['num_licenses'] >= 2).sum():,}")
    print(f"    Multi-OEM + Multi-state (UNICORNS): {((contractors_df['num_oems'] >= 2) & (contractors_df['num_licenses'] >= 2)).sum():,}")

    return contractors_df


def main():
    """Main cross-reference pipeline."""

    print("="*80)
    print("Multi-State License + OEM Cross-Reference with Overlap Tracking")
    print("="*80)
    print()

    # Load all license data
    licenses_df = load_all_licenses()

    if licenses_df.empty:
        print("❌ No license data found. Exiting.")
        return

    # Load OEM dealer data
    print(f"\nLoading OEM dealer data: {OEM_DEALER_FILE.name}")

    if not OEM_DEALER_FILE.exists():
        print(f"❌ OEM dealer file not found: {OEM_DEALER_FILE}")
        return

    dealers_df = pd.read_csv(OEM_DEALER_FILE)
    print(f"  Loaded {len(dealers_df):,} OEM dealers")

    # Match contractors across all sources
    contractors_df = match_contractors_across_all_sources(licenses_df, dealers_df)

    # Export results
    print("\n" + "="*80)
    print("Exporting results...")
    print("="*80)
    print()

    # Master list (all contractors with overlap data)
    master_output = OUTPUT_DIR / "grandmaster_multi_state_enriched_20251101.csv"
    contractors_df.to_csv(master_output, index=False)
    print(f"✅ Master list: {master_output.name} ({len(contractors_df):,} contractors)")

    # High-overlap contractors (4+ sources)
    high_overlap = contractors_df[contractors_df['num_overlaps'] >= 4].copy()
    high_overlap = high_overlap.sort_values('num_overlaps', ascending=False)
    high_overlap_output = OUTPUT_DIR / "high_overlap_contractors_20251101.csv"
    high_overlap.to_csv(high_overlap_output, index=False)
    print(f"✅ High-overlap (4+): {high_overlap_output.name} ({len(high_overlap):,} contractors)")

    # Multi-state licensed (2+ states)
    multi_state = contractors_df[contractors_df['num_licenses'] >= 2].copy()
    multi_state = multi_state.sort_values('num_licenses', ascending=False)
    multi_state_output = OUTPUT_DIR / "multi_state_licensed_20251101.csv"
    multi_state.to_csv(multi_state_output, index=False)
    print(f"✅ Multi-state licensed (2+): {multi_state_output.name} ({len(multi_state):,} contractors)")

    # Multi-OEM + Multi-state (UNICORNS)
    unicorns = contractors_df[
        (contractors_df['num_oems'] >= 2) &
        (contractors_df['num_licenses'] >= 2)
    ].copy()
    unicorns = unicorns.sort_values(['num_oems', 'num_licenses'], ascending=False)
    unicorns_output = OUTPUT_DIR / "multi_oem_multi_state_20251101.csv"
    unicorns.to_csv(unicorns_output, index=False)
    print(f"✅ UNICORNS (2+ OEMs + 2+ states): {unicorns_output.name} ({len(unicorns):,} contractors)")

    print()
    print("="*80)
    print("✅ Cross-reference complete!")
    print("="*80)
    print()
    print("Summary:")
    print(f"  Total unique contractors: {len(contractors_df):,}")
    print(f"  High-overlap (4+ sources): {len(high_overlap):,}")
    print(f"  Multi-state licensed: {len(multi_state):,}")
    print(f"  UNICORNS (Multi-OEM + Multi-state): {len(unicorns):,}")
    print()
    print("Top 10 highest overlap contractors:")
    print(contractors_df.nlargest(10, 'num_overlaps')[['name', 'city', 'state', 'num_overlaps', 'overlap_sources']])
    print()
    print("Next steps:")
    print("  1. Review UNICORNS list (multi_oem_multi_state_20251101.csv)")
    print("  2. Prioritize high-overlap contractors (4+ sources)")
    print("  3. Use overlap_sources to validate contractor sophistication")
    print()


if __name__ == "__main__":
    main()
