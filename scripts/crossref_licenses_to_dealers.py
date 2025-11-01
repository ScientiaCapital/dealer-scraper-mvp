#!/usr/bin/env python3
"""
Cross-Reference California Licenses with OEM Dealer Data

Matches California CSLB license data with existing OEM scraper data to:
1. Enrich dealer records with license information (classifications, status, expiration)
2. Update Multi-OEM scores for licensed contractors
3. Identify contractors in BOTH license database AND 2+ OEM networks (HIGHEST VALUE)
4. Export enriched grandmaster list

Usage:
    python3 scripts/crossref_licenses_to_dealers.py

Inputs:
    - output/california_icp_master_20251101.csv (processed license data)
    - output/grandmaster_list_expanded_20251029.csv (existing OEM dealer data)

Outputs:
    - output/grandmaster_ca_enriched_20251101.csv (enriched grandmaster with licenses)
    - output/california_matched_dealers_20251101.csv (licenses matched to dealers)
    - output/california_unmatched_licenses_20251101.csv (licenses NOT in dealer networks)
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from rapidfuzz import fuzz

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
LICENSE_FILE = PROJECT_ROOT / "output/california_icp_master_20251101.csv"
DEALER_FILE = PROJECT_ROOT / "output/grandmaster_list_expanded_20251029.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_phone(phone_str):
    """Normalize phone number to 10 digits (same as processing script)."""
    if pd.isna(phone_str):
        return None

    digits = re.sub(r'\D', '', str(phone_str))

    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]

    if len(digits) == 10:
        return digits

    return None


def normalize_company_name(name):
    """Normalize company name for fuzzy matching (same as processing script)."""
    if pd.isna(name):
        return ""

    name = str(name).strip().upper()

    suffixes = [
        r'\bINC\.?$', r'\bINCORPORATED$', r'\bLLC\.?$', r'\bL\.L\.C\.?$',
        r'\bCORP\.?$', r'\bCORPORATION$', r'\bLTD\.?$', r'\bLIMITED$',
        r'\bCO\.?$', r'\bCOMPANY$', r'\bDBA\b', r'\bD/B/A\b'
    ]

    for suffix in suffixes:
        name = re.sub(suffix, '', name)

    name = ' '.join(name.split())

    return name


def extract_domain(website_str):
    """
    Extract root domain from website URL.

    Examples:
        "https://www.example.com" -> "example.com"
        "http://subdomain.example.com" -> "example.com"
        "example.com/path" -> "example.com"
    """
    if pd.isna(website_str):
        return None

    website = str(website_str).strip().lower()

    # Remove protocol
    website = re.sub(r'^https?://', '', website)

    # Remove www.
    website = re.sub(r'^www\.', '', website)

    # Extract domain (before first /)
    domain = website.split('/')[0]

    # Remove port if present
    domain = domain.split(':')[0]

    # Extract root domain (last 2 parts)
    parts = domain.split('.')
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"

    return domain if domain else None


def match_dealers_to_licenses(dealers_df, licenses_df):
    """
    Match dealers to license records using multi-signal approach.

    Matching hierarchy:
    1. Phone number (normalized to 10 digits)
    2. Domain (extracted from website)
    3. Fuzzy name matching (85% threshold + same city/ZIP)

    Returns DataFrame with matched dealers and their license info.
    """
    print("Starting cross-reference matching...")
    print(f"  Dealers (OEM data): {len(dealers_df):,}")
    print(f"  Licenses (CSLB): {len(licenses_df):,}")
    print()

    # Normalize dealer data
    dealers_df['phone_normalized'] = dealers_df['phone'].apply(normalize_phone)
    dealers_df['domain_normalized'] = dealers_df['website'].apply(extract_domain)
    dealers_df['name_normalized'] = dealers_df['name'].apply(normalize_company_name)

    # Index licenses by phone and domain for fast lookup
    licenses_by_phone = licenses_df[licenses_df['phone_normalized'].notna()].set_index('phone_normalized')
    licenses_by_domain = licenses_df[licenses_df.get('domain_normalized', pd.Series()).notna()].set_index('domain_normalized') if 'domain_normalized' in licenses_df.columns else pd.DataFrame()

    # Track matches
    matches = []
    match_methods = []

    # Phase 1: Phone matching
    print("Phase 1: Phone number matching...")
    phone_matches = 0

    for idx, dealer in dealers_df.iterrows():
        phone = dealer['phone_normalized']

        if pd.notna(phone) and phone in licenses_by_phone.index:
            license_row = licenses_by_phone.loc[phone]

            # Handle multiple matches (take first)
            if isinstance(license_row, pd.DataFrame):
                license_row = license_row.iloc[0]

            matches.append({
                'dealer_idx': idx,
                'license_idx': license_row.name,
                'match_method': 'phone',
                'match_confidence': 100
            })
            phone_matches += 1

    print(f"  Phone matches: {phone_matches:,}")

    # Phase 2: Domain matching (for dealers not matched by phone)
    print("Phase 2: Domain matching...")
    domain_matches = 0

    matched_dealer_idx = {m['dealer_idx'] for m in matches}

    for idx, dealer in dealers_df.iterrows():
        if idx in matched_dealer_idx:
            continue  # Already matched by phone

        domain = dealer['domain_normalized']

        if pd.notna(domain) and not licenses_by_domain.empty and domain in licenses_by_domain.index:
            license_row = licenses_by_domain.loc[domain]

            # Handle multiple matches (take first)
            if isinstance(license_row, pd.DataFrame):
                license_row = license_row.iloc[0]

            matches.append({
                'dealer_idx': idx,
                'license_idx': license_row.name,
                'match_method': 'domain',
                'match_confidence': 90
            })
            domain_matches += 1
            matched_dealer_idx.add(idx)

    print(f"  Domain matches: {domain_matches:,}")

    # Phase 3: Fuzzy name matching (for dealers not matched yet, same city/ZIP)
    print("Phase 3: Fuzzy name matching...")
    fuzzy_matches = 0

    for idx, dealer in dealers_df.iterrows():
        if idx in matched_dealer_idx:
            continue  # Already matched

        dealer_name = dealer['name_normalized']
        dealer_city = str(dealer.get('city', '')).upper()
        dealer_zip = str(dealer.get('zip', '')).strip()

        if not dealer_name:
            continue

        # Filter licenses to same city or ZIP
        city_licenses = licenses_df[
            (licenses_df['City'].str.upper() == dealer_city) |
            (licenses_df['ZIPCode'].astype(str).str.strip() == dealer_zip)
        ]

        if city_licenses.empty:
            continue

        # Find best fuzzy match
        best_match = None
        best_score = 0

        for lic_idx, lic_row in city_licenses.iterrows():
            lic_name = normalize_company_name(lic_row['BusinessName'])

            if not lic_name:
                continue

            score = fuzz.ratio(dealer_name, lic_name)

            if score > best_score:
                best_score = score
                best_match = lic_idx

        # Threshold: 85% similarity
        if best_match and best_score >= 85:
            matches.append({
                'dealer_idx': idx,
                'license_idx': best_match,
                'match_method': 'fuzzy_name',
                'match_confidence': best_score
            })
            fuzzy_matches += 1
            matched_dealer_idx.add(idx)

    print(f"  Fuzzy name matches: {fuzzy_matches:,}")
    print()

    # Build matched DataFrame
    total_matches = len(matches)
    print(f"Total matches: {total_matches:,} ({(total_matches/len(dealers_df))*100:.1f}% of dealers)")
    print()

    if not matches:
        print("⚠️  No matches found")
        return pd.DataFrame()

    # Create matched dataset
    matched_data = []

    for match in matches:
        dealer = dealers_df.loc[match['dealer_idx']]
        license_row = licenses_df.loc[match['license_idx']]

        matched_data.append({
            # Dealer info (from OEM data)
            'name': dealer['name'],
            'phone': dealer['phone'],
            'website': dealer.get('website', ''),
            'street': dealer.get('street', ''),
            'city': dealer.get('city', ''),
            'state': dealer.get('state', ''),
            'zip': dealer.get('zip', ''),
            'oem_source': dealer.get('oem_source', ''),

            # License info (from CSLB)
            'license_number': license_row['LicenseNo'],
            'license_classifications': license_row['Classifications'],
            'license_status': license_row['PrimaryStatus'],
            'license_issue_date': license_row['IssueDate'],
            'license_expiration_date': license_row['ExpirationDate'],
            'license_count': license_row['license_count'],

            # Capability flags
            'has_electrical': license_row['has_electrical'],
            'has_hvac': license_row['has_hvac'],
            'has_solar': license_row['has_solar'],
            'has_plumbing': license_row['has_plumbing'],
            'is_gc': license_row['is_gc'],
            'is_engineering_gc': license_row['is_engineering_gc'],

            # ICP scores
            'resimercial_score': license_row['resimercial_score'],
            'multi_oem_score': license_row['multi_oem_score'],
            'mep_score': license_row['mep_score'],
            'om_score': license_row['om_score'],
            'coperniq_total_score': license_row['coperniq_total_score'],
            'icp_tier': license_row['icp_tier'],

            # Match metadata
            'match_method': match['match_method'],
            'match_confidence': match['match_confidence']
        })

    matched_df = pd.DataFrame(matched_data)

    return matched_df


def update_multi_oem_scores(matched_df):
    """
    Update Multi-OEM scores for matched dealers based on OEM certifications.

    Multi-OEM Score (25%):
        - 1 OEM: 6 pts
        - 2 OEMs: 12 pts
        - 3 OEMs: 19 pts
        - 4+ OEMs: 25 pts (MAXIMUM)

    Recalculates total Coperniq score and updates ICP tier.
    """
    print("Updating Multi-OEM scores...")

    # Count OEMs per contractor (by phone)
    oem_counts = matched_df.groupby('phone')['oem_source'].nunique().to_dict()

    def calculate_multi_oem_score(oem_count):
        if oem_count >= 4:
            return 25
        elif oem_count == 3:
            return 19
        elif oem_count == 2:
            return 12
        else:
            return 6

    # Update scores
    for idx, row in matched_df.iterrows():
        phone = row['phone']
        oem_count = oem_counts.get(phone, 1)

        new_multi_oem_score = calculate_multi_oem_score(oem_count)

        # Recalculate total score
        new_total = (
            row['resimercial_score'] +
            new_multi_oem_score +
            row['mep_score'] +
            row['om_score']
        )

        # Update ICP tier
        if new_total >= 80:
            new_tier = 'PLATINUM'
        elif new_total >= 60:
            new_tier = 'GOLD'
        elif new_total >= 40:
            new_tier = 'SILVER'
        else:
            new_tier = 'BRONZE'

        # Update row
        matched_df.at[idx, 'multi_oem_score'] = new_multi_oem_score
        matched_df.at[idx, 'coperniq_total_score'] = new_total
        matched_df.at[idx, 'icp_tier'] = new_tier

    # Tier distribution after update
    print(f"  PLATINUM (80-100): {(matched_df['icp_tier'] == 'PLATINUM').sum():,}")
    print(f"  GOLD (60-79): {(matched_df['icp_tier'] == 'GOLD').sum():,}")
    print(f"  SILVER (40-59): {(matched_df['icp_tier'] == 'SILVER').sum():,}")
    print(f"  BRONZE (<40): {(matched_df['icp_tier'] == 'BRONZE').sum():,}")
    print()

    return matched_df


def main():
    """Main cross-reference pipeline."""

    print("="*80)
    print("California License → OEM Dealer Cross-Reference")
    print("="*80)
    print()

    # Load data
    print("Loading data...")

    # Check if license file exists
    if not LICENSE_FILE.exists():
        print(f"❌ License file not found: {LICENSE_FILE}")
        print("   Please run process_california_licenses.py first.")
        return

    licenses_df = pd.read_csv(LICENSE_FILE)
    print(f"  ✅ Licenses: {len(licenses_df):,} records")

    # Check if dealer file exists
    if not DEALER_FILE.exists():
        print(f"❌ Dealer file not found: {DEALER_FILE}")
        print("   Please ensure grandmaster list exists.")
        return

    dealers_df = pd.read_csv(DEALER_FILE)
    print(f"  ✅ Dealers: {len(dealers_df):,} records")

    # Filter dealers to California only
    dealers_df = dealers_df[dealers_df['state'] == 'CA'].copy()
    print(f"  ✅ California dealers: {len(dealers_df):,} records")
    print()

    # Filter licenses to non-duplicates only
    licenses_df = licenses_df[~licenses_df['is_duplicate']].copy()
    print(f"  Unique licenses (excluding duplicates): {len(licenses_df):,}")
    print()

    # Match dealers to licenses
    matched_df = match_dealers_to_licenses(dealers_df, licenses_df)

    if matched_df.empty:
        print("No matches found. Exiting.")
        return

    # Update Multi-OEM scores
    matched_df = update_multi_oem_scores(matched_df)

    # Export matched dealers
    matched_output = OUTPUT_DIR / "california_matched_dealers_20251101.csv"
    matched_df.to_csv(matched_output, index=False)
    print(f"✅ Matched dealers: {matched_output.name} ({len(matched_df):,} records)")

    # Identify unmatched licenses (licenses NOT in dealer networks)
    matched_license_nums = set(matched_df['license_number'])
    unmatched_licenses = licenses_df[~licenses_df['LicenseNo'].isin(matched_license_nums)].copy()

    unmatched_output = OUTPUT_DIR / "california_unmatched_licenses_20251101.csv"
    unmatched_licenses.to_csv(unmatched_output, index=False)
    print(f"✅ Unmatched licenses: {unmatched_output.name} ({len(unmatched_licenses):,} records)")

    # Create enriched grandmaster (merge all OEM data with license enrichment)
    print()
    print("Creating enriched grandmaster list...")

    # Load full grandmaster (all states)
    full_grandmaster = pd.read_csv(DEALER_FILE)

    # Merge license data for California contractors
    ca_enriched = full_grandmaster.merge(
        matched_df[[
            'phone', 'license_number', 'license_classifications',
            'license_status', 'license_expiration_date', 'license_count',
            'has_electrical', 'has_hvac', 'has_solar', 'has_plumbing',
            'is_gc', 'is_engineering_gc', 'coperniq_total_score', 'icp_tier'
        ]],
        on='phone',
        how='left'
    )

    grandmaster_output = OUTPUT_DIR / "grandmaster_ca_enriched_20251101.csv"
    ca_enriched.to_csv(grandmaster_output, index=False)
    print(f"✅ Enriched grandmaster: {grandmaster_output.name} ({len(ca_enriched):,} records)")

    print()
    print("="*80)
    print("✅ Cross-reference complete!")
    print("="*80)
    print()
    print("Summary:")
    print(f"  California dealers (OEM): {len(dealers_df):,}")
    print(f"  Licenses processed: {len(licenses_df):,}")
    print(f"  Matched contractors: {len(matched_df):,}")
    print(f"  Match rate: {(len(matched_df)/len(dealers_df))*100:.1f}%")
    print(f"  Unmatched licenses (blue ocean): {len(unmatched_licenses):,}")
    print()
    print("Key insights:")
    print(f"  - {(matched_df['has_solar']).sum():,} matched dealers have C-46 solar licenses")
    print(f"  - {(matched_df['license_count'] >= 2).sum():,} matched dealers are multi-trade")
    print(f"  - {(matched_df['icp_tier'] == 'PLATINUM').sum():,} PLATINUM prospects")
    print(f"  - {(matched_df['icp_tier'] == 'GOLD').sum():,} GOLD prospects")
    print()
    print("Next steps:")
    print("  1. Review PLATINUM/GOLD prospects in california_matched_dealers_20251101.csv")
    print("  2. Target unmatched C-46 solar licenses (blue ocean opportunity)")
    print("  3. Use license expiration dates for outreach timing")
    print()


if __name__ == "__main__":
    main()
