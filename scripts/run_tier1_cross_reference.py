#!/usr/bin/env python3
"""
Tier 1 Cross-Reference Script

Matches CA/FL/TX license data with existing OEM contractor database.
Outputs enriched contractor list with license metadata.

Usage:
    python3 scripts/run_tier1_cross_reference.py \
        --license-files ca_licenses.csv fl_licenses.csv tx_licenses.csv \
        --oem-contractors output/grandmaster_list_expanded_20251029.csv \
        --output output/cross_referenced_contractors.csv
"""
import argparse
import pandas as pd
from typing import List
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.license.scraper_factory import LicenseScraperFactory
from scrapers.license.models import ScraperMode, StandardizedLicensee
from scrapers.base_scraper import StandardizedDealer
from analysis.license_oem_matcher import LicenseOEMMatcher


def load_licensees(file_paths: List[str]) -> List[StandardizedLicensee]:
    """
    Load and parse license files.

    Args:
        file_paths: List of CSV file paths

    Returns:
        List of StandardizedLicensee objects
    """
    all_licensees = []

    for file_path in file_paths:
        print(f"Loading {file_path}...")

        # Determine state from filename
        file_name = Path(file_path).stem.upper()
        state = None
        if 'CA' in file_name or 'CALIF' in file_name:
            state = "CA"
        elif 'FL' in file_name or 'FLOR' in file_name:
            state = "FL"
        elif 'TX' in file_name or 'TEXAS' in file_name:
            state = "TX"

        if not state:
            print(f"  ⚠️  Could not determine state from filename: {file_name}")
            continue

        # Create scraper and parse
        scraper = LicenseScraperFactory.create(state, mode=ScraperMode.PLAYWRIGHT)
        licensees = scraper.parse_file(file_path)

        print(f"  ✅ Loaded {len(licensees)} {state} licenses")
        all_licensees.extend(licensees)

    return all_licensees


def load_oem_contractors(file_path: str) -> List[StandardizedDealer]:
    """
    Load OEM contractor CSV.

    Args:
        file_path: Path to OEM contractor CSV

    Returns:
        List of StandardizedDealer objects
    """
    print(f"Loading OEM contractors from {file_path}...")

    df = pd.read_csv(file_path)

    dealers = []
    for _, row in df.iterrows():
        # Handle optional fields with defaults
        phone = row.get('phone', '')
        if pd.isna(phone):
            phone = ''

        domain = row.get('domain', '')
        if pd.isna(domain):
            domain = ''

        website = row.get('website', '')
        if pd.isna(website):
            website = ''

        street = row.get('street', '')
        if pd.isna(street):
            street = ''

        city = row.get('city', '')
        state = row.get('state', '')
        zip_code = str(row.get('zip', ''))

        # Construct address_full from components
        address_parts = [street, city, state, zip_code]
        address_full = ', '.join([str(p) for p in address_parts if p])

        dealer = StandardizedDealer(
            name=row.get('name', ''),
            phone=phone,
            domain=domain,
            website=website,
            street=street,
            city=city,
            state=state,
            zip=zip_code,
            address_full=address_full,
            oem_source=row.get('oem_source', ''),
            scraped_from_zip=row.get('scraped_from_zip', '')
        )
        dealers.append(dealer)

    print(f"  ✅ Loaded {len(dealers)} OEM contractors")
    return dealers


def main():
    parser = argparse.ArgumentParser(description='Cross-reference Tier 1 licenses with OEM contractors')
    parser.add_argument('--license-files', nargs='+', required=True,
                       help='License CSV files (CA, FL, TX)')
    parser.add_argument('--oem-contractors', required=True,
                       help='OEM contractor CSV file')
    parser.add_argument('--output', required=True,
                       help='Output CSV path for enriched contractors')

    args = parser.parse_args()

    print("=" * 60)
    print("TIER 1 CROSS-REFERENCE SCRIPT")
    print("=" * 60)
    print()

    # Load data
    licensees = load_licensees(args.license_files)
    dealers = load_oem_contractors(args.oem_contractors)

    print()
    print(f"Total licensees loaded: {len(licensees)}")
    print(f"Total OEM contractors loaded: {len(dealers)}")
    print()

    # Match
    print("Running cross-reference matcher...")
    matcher = LicenseOEMMatcher()
    matches = matcher.match(licensees, dealers)

    print(f"  ✅ Found {len(matches)} matches")
    print()

    # Analyze matches
    by_type = {}
    for match in matches:
        match_type = match['match_type']
        by_type[match_type] = by_type.get(match_type, 0) + 1

    print("Match breakdown:")
    for match_type, count in by_type.items():
        pct = (count / len(matches) * 100) if matches else 0
        print(f"  - {match_type}: {count} ({pct:.1f}%)")
    print()

    # Export enriched contractors
    print(f"Exporting to {args.output}...")

    enriched_records = [match['enriched_dealer'] for match in matches]
    df_output = pd.DataFrame(enriched_records)

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    df_output.to_csv(args.output, index=False)

    print(f"  ✅ Exported {len(enriched_records)} enriched contractors")
    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
