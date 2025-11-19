#!/usr/bin/env python3
"""
MEP+Energy Contractor Analysis Script

Analyzes existing license data (CA/TX/FL/NYC) to identify high-value contractors matching 4 profiles:
1. Multi-trade (Electrical + HVAC + Solar)
2. Multi-state licensed (2+ states)
3. License + OEM overlap (contractors in BOTH license databases AND OEM networks)
4. High-tenure contractors (10+ years licensed)

Usage:
    python3 scripts/analyze_mep_energy_contractors.py

Outputs:
    - output/mep_energy_contractors_YYYYMMDD.csv
    - output/multi_state_mep_YYYYMMDD.csv
    - output/license_oem_overlap_mep_YYYYMMDD.csv
    - output/established_mep_contractors_YYYYMMDD.csv
    - output/top_100_mep_energy_prospects_YYYYMMDD.csv
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
STATE_LICENSES_DIR = OUTPUT_DIR / "state_licenses"

# Input files
CA_LICENSE_FILE = STATE_LICENSES_DIR / "california" / "california_icp_master_20251101.csv"
TX_LICENSE_FILE = STATE_LICENSES_DIR / "texas" / "tx_tdlr_processed_20251031.csv"
FL_CONSTRUCTION_FILE = STATE_LICENSES_DIR / "florida" / "fl_dbpr_fresh_download_20251119.csv"
FL_ELECTRICAL_FILE = STATE_LICENSES_DIR / "florida" / "fl_electrical_contractors_20251119.csv"
NYC_LICENSE_FILE = STATE_LICENSES_DIR / "new_york" / "nyc_dob_licenses_20251031.csv"
OEM_DEALER_FILE = OUTPUT_DIR / "grandmaster_list_expanded_20251029.csv"

# Date suffix for outputs
DATE_SUFFIX = datetime.now().strftime("%Y%m%d")


def normalize_phone(phone_str):
    """Normalize phone number to 10 digits."""
    if pd.isna(phone_str):
        return None

    digits = re.sub(r'\D', '', str(phone_str))

    # Remove leading 1 for US country code
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]

    if len(digits) == 10:
        return digits

    return None


def load_california_licenses():
    """
    Load and analyze California licenses.

    Returns:
        DataFrame with normalized data + trade flags
    """
    print(f"\n📊 Loading California licenses from {CA_LICENSE_FILE.name}...")

    if not CA_LICENSE_FILE.exists():
        print(f"⚠️  File not found: {CA_LICENSE_FILE}")
        return pd.DataFrame()

    ca_df = pd.read_csv(CA_LICENSE_FILE)

    # Filter out duplicates
    ca_df = ca_df[~ca_df['is_duplicate']].copy()

    print(f"   ✅ Loaded {len(ca_df):,} unique CA contractors")
    print(f"   - Electrical (C-10): {ca_df['has_electrical'].sum():,}")
    print(f"   - HVAC (C-20): {ca_df['has_hvac'].sum():,}")
    print(f"   - Solar (C-46): {ca_df['has_solar'].sum():,}")

    # Check multi-trade by parsing Classifications column for multiple MEP trade codes
    ca_df['classifications_str'] = ca_df['Classifications(s)'].astype(str)

    # Detect MEP+Energy multi-trade combinations
    ca_df['has_c10_c20'] = (ca_df['classifications_str'].str.contains('C-10|C10', case=False, na=False) &
                            ca_df['classifications_str'].str.contains('C-20|C20', case=False, na=False))

    ca_df['has_c10_c46'] = (ca_df['classifications_str'].str.contains('C-10|C10', case=False, na=False) &
                            ca_df['classifications_str'].str.contains('C-46|C46', case=False, na=False))

    ca_df['has_c20_c46'] = (ca_df['classifications_str'].str.contains('C-20|C20', case=False, na=False) &
                            ca_df['classifications_str'].str.contains('C-46|C46', case=False, na=False))

    ca_df['has_all_three'] = (ca_df['classifications_str'].str.contains('C-10|C10', case=False, na=False) &
                              ca_df['classifications_str'].str.contains('C-20|C20', case=False, na=False) &
                              ca_df['classifications_str'].str.contains('C-46|C46', case=False, na=False))

    # Overall multi-trade flag
    ca_df['is_multi_trade'] = ca_df['has_c10_c20'] | ca_df['has_c10_c46'] | ca_df['has_c20_c46']

    # Calculate tenure (years since first licensed)
    ca_df['issue_date_parsed'] = pd.to_datetime(ca_df['IssueDate'], errors='coerce')
    today = datetime.now()
    ca_df['tenure_years'] = (today - ca_df['issue_date_parsed']).dt.days / 365.25
    ca_df['is_high_tenure'] = ca_df['tenure_years'] >= 10

    print(f"   - Multi-trade (2+ capabilities): {ca_df['is_multi_trade'].sum():,}")
    print(f"     • C-10 + C-20 (Elec + HVAC): {ca_df['has_c10_c20'].sum():,}")
    print(f"     • C-10 + C-46 (Elec + Solar): {ca_df['has_c10_c46'].sum():,}")
    print(f"     • C-20 + C-46 (HVAC + Solar): {ca_df['has_c20_c46'].sum():,}")
    print(f"     • All 3 (UNICORNS): {ca_df['has_all_three'].sum():,}")
    print(f"   - High-tenure (10+ years): {ca_df['is_high_tenure'].sum():,}")

    # Normalize columns
    ca_normalized = pd.DataFrame({
        'contractor_id': 'CA-' + ca_df['LicenseNo'].astype(str),
        'business_name': ca_df['BusinessName'],
        'phone_normalized': ca_df['phone_normalized'],
        'city': ca_df['City'],
        'state': 'CA',
        'zip': ca_df['ZIPCode'],
        'license_classifications': ca_df['Classifications(s)'],
        'license_count': ca_df['license_count'],
        'license_status': ca_df['PrimaryStatus'],
        'issue_date': ca_df['IssueDate'],
        'tenure_years': ca_df['tenure_years'],
        'has_electrical': ca_df['has_electrical'],
        'has_hvac': ca_df['has_hvac'],
        'has_solar': ca_df['has_solar'],
        'has_plumbing': ca_df['has_plumbing'],
        'is_multi_trade': ca_df['is_multi_trade'],
        'has_c10_c20': ca_df['has_c10_c20'],
        'has_c10_c46': ca_df['has_c10_c46'],
        'has_c20_c46': ca_df['has_c20_c46'],
        'has_all_three': ca_df['has_all_three'],
        'is_high_tenure': ca_df['is_high_tenure'],
        'coperniq_score': ca_df['coperniq_total_score'],
        'icp_tier': ca_df['icp_tier'],
        'source_file': 'CA-CSLB'
    })

    return ca_normalized


def load_florida_licenses():
    """
    Load and analyze Florida licenses (Construction + Electrical).

    FL has two separate files:
    - Construction file: HVAC (AC, Mechanical) + Solar + other construction trades (WITH phone)
    - Electrical file: EC (Electrical Contractor) licenses (NO phone numbers)

    Returns:
        DataFrame with normalized data + trade flags
    """
    print(f"\n📊 Loading Florida licenses from {FL_CONSTRUCTION_FILE.name} + {FL_ELECTRICAL_FILE.name}...")

    fl_records = []

    # Load construction file (HVAC + Solar + other trades)
    if FL_CONSTRUCTION_FILE.exists():
        constr_df = pd.read_csv(FL_CONSTRUCTION_FILE, header=None, low_memory=False)

        # Column mapping (15 columns):
        # 0: License code, 1: License type, 2-4: Name fields, 5: Business name
        # 6-8: Address, 9-11: City/State/ZIP, 12: Unknown, 13: Phone, 14: Unknown

        # Filter to MEP+Energy license types
        mep_mask = constr_df[1].str.contains(
            'AC Contractor|Mechanical Contractor|Solar Contractor',
            case=False,
            na=False
        )
        constr_mep = constr_df[mep_mask].copy()

        # Parse trade capabilities
        constr_mep['has_electrical'] = False  # Construction file doesn't have electrical
        constr_mep['has_hvac'] = constr_mep[1].str.contains('AC|Mechanical', case=False, na=False)
        constr_mep['has_solar'] = constr_mep[1].str.contains('Solar', case=False, na=False)
        constr_mep['has_plumbing'] = constr_mep[1].str.contains('Plumbing', case=False, na=False)

        # Normalize phone
        constr_mep['phone_normalized'] = constr_mep[13].apply(normalize_phone)

        # Create business name (use column 5 if present, else concat name fields)
        constr_mep['business_name_parsed'] = constr_mep.apply(
            lambda row: row[5] if pd.notna(row[5]) and row[5].strip() else f"{row[2]} {row[3] or ''} {row[4]}".strip(),
            axis=1
        )

        # Calculate tenure (no issue date in this file, so we can't calculate it)
        constr_mep['tenure_years'] = None
        constr_mep['is_high_tenure'] = False

        # Multi-trade detection
        trade_count = (constr_mep['has_electrical'].astype(int) + constr_mep['has_hvac'].astype(int) +
                      constr_mep['has_solar'].astype(int))
        constr_mep['is_multi_trade'] = trade_count >= 2

        # Add to records list
        for _, row in constr_mep.iterrows():
            fl_records.append({
                'contractor_id': f"FL-CONSTR-{row[0]}",
                'business_name': row['business_name_parsed'],
                'phone_normalized': row['phone_normalized'],
                'city': row[9],
                'state': 'FL',
                'zip': str(row[10]) if pd.notna(row[10]) else '',
                'license_classifications': row[1],
                'license_count': 1,
                'license_status': 'Active',  # Assume active (file only has active)
                'issue_date': None,
                'tenure_years': None,
                'has_electrical': False,
                'has_hvac': row['has_hvac'],
                'has_solar': row['has_solar'],
                'has_plumbing': row['has_plumbing'],
                'is_multi_trade': row['is_multi_trade'],
                'has_c10_c20': False,  # FL doesn't use CA classifications
                'has_c10_c46': False,
                'has_c20_c46': row['has_hvac'] and row['has_solar'],  # HVAC + Solar combo
                'has_all_three': False,
                'is_high_tenure': False,
                'coperniq_score': 0,
                'icp_tier': '',
                'source_file': 'FL-DBPR-Construction'
            })

        print(f"   ✅ Loaded {len(constr_mep):,} FL construction contractors (HVAC + Solar)")
        print(f"   - HVAC (AC/Mechanical): {constr_mep['has_hvac'].sum():,}")
        print(f"   - Solar: {constr_mep['has_solar'].sum():,}")
        print(f"   - Multi-trade (HVAC+Solar): {constr_mep['is_multi_trade'].sum():,}")
        print(f"   - Phone numbers available: {constr_mep['phone_normalized'].notna().sum():,} ({constr_mep['phone_normalized'].notna().sum() / len(constr_mep) * 100:.1f}%)")

    # Load electrical file (EC licenses - NO phone numbers)
    if FL_ELECTRICAL_FILE.exists():
        elec_df = pd.read_csv(FL_ELECTRICAL_FILE, header=None, low_memory=False)

        # Column mapping (22 columns):
        # 0: Category, 1: License type (EC), 2: Name, 3: Business name
        # 5-7: Address, 8-10: City/State/ZIP, 11: County code, 12: License number
        # 13-14: Status codes, 15: Original issue, 16: Effective date, 17: Expiration

        # Parse issue date for tenure calculation
        elec_df['issue_date_parsed'] = pd.to_datetime(elec_df[15], errors='coerce')
        today = datetime.now()
        elec_df['tenure_years'] = (today - elec_df['issue_date_parsed']).dt.days / 365.25
        elec_df['is_high_tenure'] = elec_df['tenure_years'] >= 10

        # Create business name (use column 3 if present, else column 2)
        elec_df['business_name_parsed'] = elec_df.apply(
            lambda row: row[3] if pd.notna(row[3]) and row[3].strip() else row[2],
            axis=1
        )

        for _, row in elec_df.iterrows():
            fl_records.append({
                'contractor_id': f"FL-EC-{row[12]}",
                'business_name': row['business_name_parsed'],
                'phone_normalized': None,  # Electrical file has NO phone numbers
                'city': row[8],
                'state': 'FL',
                'zip': str(row[10]) if pd.notna(row[10]) else '',
                'license_classifications': 'EC (Electrical Contractor)',
                'license_count': 1,
                'license_status': 'Active',
                'issue_date': row[15],
                'tenure_years': row['tenure_years'],
                'has_electrical': True,
                'has_hvac': False,
                'has_solar': False,
                'has_plumbing': False,
                'is_multi_trade': False,  # Single license record
                'has_c10_c20': False,
                'has_c10_c46': False,
                'has_c20_c46': False,
                'has_all_three': False,
                'is_high_tenure': row['is_high_tenure'],
                'coperniq_score': 0,
                'icp_tier': '',
                'source_file': 'FL-DBPR-Electrical'
            })

        print(f"   ✅ Loaded {len(elec_df):,} FL electrical contractors (EC)")
        print(f"   - ⚠️  NO phone numbers in electrical file (can't match cross-state)")
        print(f"   - High-tenure (10+ years): {elec_df['is_high_tenure'].sum():,}")

    fl_normalized = pd.DataFrame(fl_records)

    if len(fl_normalized) > 0:
        print(f"\n   📊 TOTAL FL MEP+Energy contractors: {len(fl_normalized):,}")
        print(f"   - With phone numbers: {fl_normalized['phone_normalized'].notna().sum():,}")
        print(f"   - Without phone numbers: {fl_normalized['phone_normalized'].isna().sum():,}")

    return fl_normalized


def load_nyc_licenses():
    """
    Load and analyze NYC licenses.

    Returns:
        DataFrame with normalized data + trade flags
    """
    print(f"\n📊 Loading NYC licenses from {NYC_LICENSE_FILE.name}...")

    if not NYC_LICENSE_FILE.exists():
        print(f"⚠️  File not found: {NYC_LICENSE_FILE}")
        return pd.DataFrame()

    nyc_df = pd.read_csv(NYC_LICENSE_FILE)

    # NYC data is mostly "Home Improvement Contractor" - general, not MEP-specific
    # We'll infer capabilities from business names if possible
    nyc_df['business_name_lower'] = nyc_df['business_name'].fillna('').str.lower()

    nyc_df['has_electrical'] = nyc_df['business_name_lower'].str.contains('electric|electrical', case=False, na=False)
    nyc_df['has_hvac'] = nyc_df['business_name_lower'].str.contains('hvac|heating|cooling|air cond', case=False, na=False)
    nyc_df['has_solar'] = nyc_df['business_name_lower'].str.contains('solar|photovoltaic', case=False, na=False)
    nyc_df['has_plumbing'] = nyc_df['business_name_lower'].str.contains('plumb', case=False, na=False)

    print(f"   ✅ Loaded {len(nyc_df):,} NYC contractors")
    print(f"   - Electrical (inferred from name): {nyc_df['has_electrical'].sum():,}")
    print(f"   - HVAC (inferred from name): {nyc_df['has_hvac'].sum():,}")
    print(f"   - Solar (inferred from name): {nyc_df['has_solar'].sum():,}")

    # Check multi-trade (rare - based on business name inference)
    trade_count = (nyc_df['has_electrical'].astype(int) + nyc_df['has_hvac'].astype(int) +
                   nyc_df['has_solar'].astype(int))
    nyc_df['is_multi_trade'] = trade_count >= 2

    # Calculate tenure
    nyc_df['license_creation_parsed'] = pd.to_datetime(nyc_df['license_creation'], errors='coerce')
    today = datetime.now()
    nyc_df['tenure_years'] = (today - nyc_df['license_creation_parsed']).dt.days / 365.25
    nyc_df['is_high_tenure'] = nyc_df['tenure_years'] >= 10

    print(f"   - Multi-trade (inferred, 2+ capabilities): {nyc_df['is_multi_trade'].sum():,}")
    print(f"   - High-tenure (10+ years): {nyc_df['is_high_tenure'].sum():,}")

    # Normalize phone
    nyc_df['phone_normalized'] = nyc_df['phone'].apply(normalize_phone)

    # Normalize columns
    nyc_normalized = pd.DataFrame({
        'contractor_id': 'NYC-' + nyc_df['license_number'].astype(str),
        'business_name': nyc_df['business_name'].fillna(nyc_df['licensee_name']),
        'phone_normalized': nyc_df['phone_normalized'],
        'city': nyc_df['city'],
        'state': 'NY',
        'zip': nyc_df['zip'],
        'license_classifications': nyc_df['license_type'],
        'license_count': 1,  # NYC data has one license per record
        'license_status': nyc_df['license_status'],
        'issue_date': nyc_df['license_creation'],
        'tenure_years': nyc_df['tenure_years'],
        'has_electrical': nyc_df['has_electrical'],
        'has_hvac': nyc_df['has_hvac'],
        'has_solar': nyc_df['has_solar'],
        'has_plumbing': nyc_df['has_plumbing'],
        'is_multi_trade': nyc_df['is_multi_trade'],
        'has_c10_c20': False,  # NYC doesn't use CA classifications
        'has_c10_c46': False,
        'has_c20_c46': False,
        'has_all_three': False,
        'is_high_tenure': nyc_df['is_high_tenure'],
        'coperniq_score': 0,  # Not calculated yet for NYC
        'icp_tier': '',
        'source_file': 'NYC-DCA/DOB'
    })

    return nyc_normalized


def load_texas_licenses():
    """
    Load and analyze Texas licenses.

    Returns:
        DataFrame with normalized data + trade flags
    """
    print(f"\n📊 Loading Texas licenses from {TX_LICENSE_FILE.name}...")

    if not TX_LICENSE_FILE.exists():
        print(f"⚠️  File not found: {TX_LICENSE_FILE}")
        return pd.DataFrame()

    tx_df = pd.read_csv(TX_LICENSE_FILE)

    # Map license types to trade capabilities
    tx_df['has_electrical'] = tx_df['license_type'].str.contains('Electrical', case=False, na=False)
    tx_df['has_hvac'] = tx_df['license_type'].str.contains('Air Conditioning|HVAC|Refrigeration', case=False, na=False)
    tx_df['has_solar'] = tx_df['license_type'].str.contains('Solar', case=False, na=False)
    tx_df['has_plumbing'] = tx_df['license_type'].str.contains('Plumbing', case=False, na=False)

    print(f"   ✅ Loaded {len(tx_df):,} TX contractors")
    print(f"   - Electrical: {tx_df['has_electrical'].sum():,}")
    print(f"   - HVAC: {tx_df['has_hvac'].sum():,}")
    print(f"   - Solar: {tx_df['has_solar'].sum():,}")

    # Check multi-trade (rare in TX - single license per record usually)
    trade_count = (tx_df['has_electrical'].astype(int) + tx_df['has_hvac'].astype(int) +
                   tx_df['has_solar'].astype(int))
    tx_df['is_multi_trade'] = trade_count >= 2

    # Calculate tenure
    tx_df['issue_date_parsed'] = pd.to_datetime(tx_df['original_issue_date'], errors='coerce')
    today = datetime.now()
    tx_df['tenure_years'] = (today - tx_df['issue_date_parsed']).dt.days / 365.25
    tx_df['is_high_tenure'] = tx_df['tenure_years'] >= 10

    print(f"   - Multi-trade (2+ capabilities): {tx_df['is_multi_trade'].sum():,}")
    print(f"   - High-tenure (10+ years): {tx_df['is_high_tenure'].sum():,}")

    # Normalize phone
    tx_df['phone_normalized'] = tx_df['phone'].apply(normalize_phone)

    # Normalize columns
    tx_normalized = pd.DataFrame({
        'contractor_id': 'TX-' + tx_df['license_number'].astype(str),
        'business_name': tx_df['business_name'].fillna(tx_df['licensee_name']),
        'phone_normalized': tx_df['phone_normalized'],
        'city': tx_df['city'],
        'state': 'TX',
        'zip': tx_df['zip'],
        'license_classifications': tx_df['license_type'],
        'license_count': 1,  # TX data has one license per record
        'license_status': tx_df['license_status'],
        'issue_date': tx_df['original_issue_date'],
        'tenure_years': tx_df['tenure_years'],
        'has_electrical': tx_df['has_electrical'],
        'has_hvac': tx_df['has_hvac'],
        'has_solar': tx_df['has_solar'],
        'has_plumbing': tx_df['has_plumbing'],
        'is_multi_trade': tx_df['is_multi_trade'],
        'is_high_tenure': tx_df['is_high_tenure'],
        'coperniq_score': 0,  # Not calculated yet for TX
        'icp_tier': '',
        'source_file': 'TX-TDLR'
    })

    return tx_normalized


def identify_multi_state_contractors(all_licenses_df):
    """
    Identify contractors licensed in 2+ states.

    Uses phone number as primary matching signal.

    Returns:
        DataFrame of contractors with state_count, states_licensed
    """
    print("\n🗺️  Identifying multi-state licensed contractors...")

    # Group by phone number
    phone_groups = all_licenses_df[all_licenses_df['phone_normalized'].notna()].groupby('phone_normalized')

    multi_state_contractors = []

    for phone, group in phone_groups:
        states = group['state'].unique()

        if len(states) >= 2:
            # This contractor is licensed in 2+ states!
            # Take the record with highest ICP score as primary
            primary_record = group.sort_values('coperniq_score', ascending=False).iloc[0]

            multi_state_contractors.append({
                'phone_normalized': phone,
                'business_name': primary_record['business_name'],
                'primary_state': primary_record['state'],
                'state_count': len(states),
                'states_licensed': ', '.join(sorted(states)),
                'total_licenses': group['license_count'].sum(),
                'has_electrical': group['has_electrical'].any(),
                'has_hvac': group['has_hvac'].any(),
                'has_solar': group['has_solar'].any(),
                'is_multi_trade': group['is_multi_trade'].any(),
                'max_tenure_years': group['tenure_years'].max(),
                'is_high_tenure': group['is_high_tenure'].any(),
                'max_coperniq_score': group['coperniq_score'].max(),
                'best_icp_tier': primary_record['icp_tier']
            })

    multi_state_df = pd.DataFrame(multi_state_contractors)

    if len(multi_state_df) > 0:
        print(f"   ✅ Found {len(multi_state_df):,} multi-state contractors")
        print(f"   - 2 states: {(multi_state_df['state_count'] == 2).sum():,}")
        print(f"   - 3+ states: {(multi_state_df['state_count'] >= 3).sum():,}")

        # Show top state combinations
        print("\n   Top State Combinations:")
        top_combos = multi_state_df['states_licensed'].value_counts().head(5)
        for combo, count in top_combos.items():
            print(f"      {combo}: {count:,} contractors")
    else:
        print("   ⚠️  No multi-state contractors found")

    return multi_state_df


def identify_license_oem_overlap(all_licenses_df, oem_dealers_df):
    """
    Identify contractors in BOTH license databases AND OEM networks.

    These are the highest-value prospects - verified by both state license and OEM certification.

    Returns:
        DataFrame of overlapping contractors with source details
    """
    print("\n🎯 Identifying License + OEM overlap contractors...")

    if oem_dealers_df is None or len(oem_dealers_df) == 0:
        print("   ⚠️  OEM dealer file not loaded, skipping overlap analysis")
        return pd.DataFrame()

    # Normalize OEM phone numbers
    oem_dealers_df['phone_normalized'] = oem_dealers_df['phone'].apply(normalize_phone)

    # Find overlaps by phone number
    license_phones = set(all_licenses_df[all_licenses_df['phone_normalized'].notna()]['phone_normalized'])
    oem_phones = set(oem_dealers_df[oem_dealers_df['phone_normalized'].notna()]['phone_normalized'])

    overlap_phones = license_phones & oem_phones

    print(f"   ✅ Found {len(overlap_phones):,} contractors in BOTH license DBs AND OEM networks")

    if len(overlap_phones) == 0:
        return pd.DataFrame()

    # Get license records for overlapping contractors
    license_overlaps = all_licenses_df[all_licenses_df['phone_normalized'].isin(overlap_phones)].copy()

    # Get OEM records for overlapping contractors
    oem_overlaps = oem_dealers_df[oem_dealers_df['phone_normalized'].isin(overlap_phones)].copy()

    # Merge to create enriched overlap records
    overlap_df = license_overlaps.merge(
        oem_overlaps[['phone_normalized', 'oem_source', 'tier', 'rating', 'review_count']],
        on='phone_normalized',
        how='left'
    )

    # Count OEM sources per contractor
    oem_source_counts = oem_overlaps.groupby('phone_normalized')['oem_source'].apply(lambda x: ', '.join(x.unique())).to_dict()
    oem_count = oem_overlaps.groupby('phone_normalized')['oem_source'].nunique().to_dict()

    overlap_df['oem_sources'] = overlap_df['phone_normalized'].map(oem_source_counts)
    overlap_df['oem_source_count'] = overlap_df['phone_normalized'].map(oem_count)

    print(f"   - Multi-OEM overlaps (2+ OEMs + licensed): {(overlap_df['oem_source_count'] >= 2).sum():,}")
    print(f"   - Multi-trade overlaps (licensed + OEM): {overlap_df['is_multi_trade'].sum():,}")

    return overlap_df


def generate_top_500_prospects(all_licenses, multi_state_df, overlap_df):
    """
    Generate Top 500 MEP+Energy prospects list based on composite scoring.

    Scoring criteria:
    - Multi-state: +25 pts
    - Multi-trade: +30 pts
    - UNICORN (all 3 trades): +20 pts bonus
    - License + OEM overlap: +20 pts
    - High tenure: +15 pts
    - Existing Coperniq ICP score: up to +100 pts

    Returns:
        DataFrame of top 500 prospects sorted by composite score
    """
    print("\n🏆 Generating Top 500 MEP+Energy Prospects...")

    # Start with all licenses
    prospects = all_licenses.copy()

    # Fill NaN values in boolean columns to avoid masking errors
    prospects['has_all_three'] = prospects['has_all_three'].fillna(False)
    prospects['is_multi_trade'] = prospects['is_multi_trade'].fillna(False)
    prospects['is_high_tenure'] = prospects['is_high_tenure'].fillna(False)

    # Initialize composite score with existing Coperniq score
    prospects['composite_score'] = prospects['coperniq_score'].fillna(0)

    # Add multi-trade bonus
    prospects.loc[prospects['is_multi_trade'] == True, 'composite_score'] += 30
    prospects.loc[prospects['has_all_three'] == True, 'composite_score'] += 20  # UNICORN bonus

    # Add high tenure bonus
    prospects.loc[prospects['is_high_tenure'] == True, 'composite_score'] += 15

    # Add multi-state bonus
    if len(multi_state_df) > 0:
        multi_state_phones = set(multi_state_df['phone_normalized'])
        prospects.loc[prospects['phone_normalized'].isin(multi_state_phones), 'composite_score'] += 25

    # Add OEM overlap bonus
    if len(overlap_df) > 0:
        oem_overlap_phones = set(overlap_df['phone_normalized'])
        prospects.loc[prospects['phone_normalized'].isin(oem_overlap_phones), 'composite_score'] += 20

    # Sort by composite score
    prospects = prospects.sort_values('composite_score', ascending=False)

    # Take top 500
    top_500 = prospects.head(500).copy()

    # Add scoring breakdown
    top_500['score_breakdown'] = top_500.apply(
        lambda row: f"Base: {row['coperniq_score']:.0f} | Multi-trade: {30 if row['is_multi_trade'] else 0} | "
                   f"UNICORN: {20 if row['has_all_three'] else 0} | Tenure: {15 if row['is_high_tenure'] else 0} | "
                   f"Multi-state: {25 if row['phone_normalized'] in multi_state_df['phone_normalized'].values else 0} | "
                   f"OEM: {20 if row['phone_normalized'] in overlap_df['phone_normalized'].values else 0}",
        axis=1
    )

    print(f"   ✅ Generated Top 500 prospects")
    print(f"   - Score range: {top_500['composite_score'].min():.0f} - {top_500['composite_score'].max():.0f}")
    print(f"   - Average score: {top_500['composite_score'].mean():.1f}")
    print(f"   - Multi-trade: {top_500['is_multi_trade'].sum()} ({top_500['is_multi_trade'].sum() / len(top_500) * 100:.0f}%)")
    print(f"   - UNICORNS: {top_500['has_all_three'].sum()}")
    print(f"   - High-tenure (10+): {top_500['is_high_tenure'].sum()}")
    print(f"   - Multi-state: {top_500['phone_normalized'].isin(multi_state_df['phone_normalized']).sum()}")
    print(f"   - OEM-certified: {top_500['phone_normalized'].isin(overlap_df['phone_normalized']).sum()}")

    # State breakdown
    print(f"\n   State distribution:")
    for state, count in top_500['state'].value_counts().items():
        print(f"      {state}: {count}")

    return top_500


def main():
    print("=" * 80)
    print("MEP+ENERGY CONTRACTOR ANALYSIS")
    print("=" * 80)

    # Load all license data
    ca_licenses = load_california_licenses()
    tx_licenses = load_texas_licenses()
    fl_licenses = load_florida_licenses()
    nyc_licenses = load_nyc_licenses()

    # Combine all licenses
    all_licenses = pd.concat([ca_licenses, tx_licenses, fl_licenses, nyc_licenses], ignore_index=True)

    print(f"\n📊 TOTAL LICENSE RECORDS: {len(all_licenses):,}")
    print(f"   - California: {len(ca_licenses):,}")
    print(f"   - Texas: {len(tx_licenses):,}")
    print(f"   - Florida: {len(fl_licenses):,}")
    print(f"   - New York City: {len(nyc_licenses):,}")

    print(f"\n⚠️  NOTE: Florida electrical contractors (EC) have NO phone numbers")
    print(f"   - FL HVAC/Solar contractors: {(fl_licenses['phone_normalized'].notna()).sum():,} with phones")
    print(f"   - FL Electrical contractors: {(fl_licenses['has_electrical']).sum():,} WITHOUT phones (can't match cross-state)")

    # Analysis 1: Multi-trade contractors
    print("\n" + "=" * 80)
    print("ANALYSIS 1: MULTI-TRADE CONTRACTORS (Electrical + HVAC + Solar)")
    print("=" * 80)

    multi_trade = all_licenses[all_licenses['is_multi_trade']].copy()
    print(f"\n✅ Found {len(multi_trade):,} multi-trade contractors")

    if len(multi_trade) > 0:
        output_file = OUTPUT_DIR / f"mep_energy_contractors_{DATE_SUFFIX}.csv"
        multi_trade.to_csv(output_file, index=False)
        print(f"   📄 Saved to: {output_file.name}")

    # Analysis 2: Multi-state contractors
    print("\n" + "=" * 80)
    print("ANALYSIS 2: MULTI-STATE LICENSED CONTRACTORS")
    print("=" * 80)

    multi_state = identify_multi_state_contractors(all_licenses)

    if len(multi_state) > 0:
        output_file = OUTPUT_DIR / f"multi_state_mep_{DATE_SUFFIX}.csv"
        multi_state.to_csv(output_file, index=False)
        print(f"   📄 Saved to: {output_file.name}")

    # Analysis 3: License + OEM overlap
    print("\n" + "=" * 80)
    print("ANALYSIS 3: LICENSE + OEM OVERLAP (Highest Value)")
    print("=" * 80)

    # Load OEM dealer data
    oem_dealers = None
    if OEM_DEALER_FILE.exists():
        print(f"   Loading OEM dealers from {OEM_DEALER_FILE.name}...")
        oem_dealers = pd.read_csv(OEM_DEALER_FILE)
        print(f"   ✅ Loaded {len(oem_dealers):,} OEM contractors")

    overlap = identify_license_oem_overlap(all_licenses, oem_dealers)

    if len(overlap) > 0:
        output_file = OUTPUT_DIR / f"license_oem_overlap_mep_{DATE_SUFFIX}.csv"
        overlap.to_csv(output_file, index=False)
        print(f"   📄 Saved to: {output_file.name}")

    # Analysis 4: High-tenure contractors
    print("\n" + "=" * 80)
    print("ANALYSIS 4: ESTABLISHED CONTRACTORS (10+ Years Tenure)")
    print("=" * 80)

    high_tenure = all_licenses[all_licenses['is_high_tenure']].copy()
    print(f"\n✅ Found {len(high_tenure):,} established contractors (10+ years)")

    # Filter to MEP trades only
    high_tenure_mep = high_tenure[
        high_tenure['has_electrical'] | high_tenure['has_hvac'] | high_tenure['has_solar']
    ]
    print(f"   - With MEP+Energy capabilities: {len(high_tenure_mep):,}")

    if len(high_tenure_mep) > 0:
        output_file = OUTPUT_DIR / f"established_mep_contractors_{DATE_SUFFIX}.csv"
        high_tenure_mep.to_csv(output_file, index=False)
        print(f"   📄 Saved to: {output_file.name}")

    # Analysis 5: Top 500 Prospects
    print("\n" + "=" * 80)
    print("ANALYSIS 5: TOP 500 MEP+ENERGY PROSPECTS")
    print("=" * 80)

    top_500 = generate_top_500_prospects(all_licenses, multi_state, overlap)

    if len(top_500) > 0:
        output_file = OUTPUT_DIR / f"top_500_mep_energy_prospects_{DATE_SUFFIX}.csv"
        top_500.to_csv(output_file, index=False)
        print(f"   📄 Saved to: {output_file.name}")

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   - Multi-trade contractors: {len(multi_trade):,}")
    print(f"   - Multi-state licensed: {len(multi_state):,}")
    print(f"   - License + OEM overlap: {len(overlap):,}")
    print(f"   - Established MEP contractors: {len(high_tenure_mep):,}")
    print(f"   - Top 500 prospects: {len(top_500):,}")
    print(f"\n✅ All outputs saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
