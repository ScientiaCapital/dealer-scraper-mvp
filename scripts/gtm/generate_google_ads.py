#!/usr/bin/env python3
"""
Generate Google Ads Customer Match CSV
Extracts PLATINUM + GOLD tier contractors for Similar Audiences
"""
import csv
import sys
from pathlib import Path

def generate_google_ads_csv(icp_analysis_path: str, output_path: str):
    """
    Generate Google Ads Customer Match CSV from ICP analysis.

    Format optimized for Google Ads upload:
    - Email (domain-based business emails)
    - Phone (cleaned, digits only)
    - Company Name
    - ZIP Code
    - Country (US)

    Args:
        icp_analysis_path: Path to ICP analysis CSV
        output_path: Path to save Google Ads CSV
    """
    print("\n" + "="*70)
    print("🎯 GENERATING GOOGLE ADS CUSTOMER MATCH LIST")
    print("="*70)
    print(f"Source: {icp_analysis_path}")
    print(f"Output: {output_path}")
    print()

    high_value_contractors = []

    # Read ICP analysis and filter to PLATINUM + GOLD tiers
    with open(icp_analysis_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['ICP Tier'] in ['PLATINUM', 'GOLD']:
                high_value_contractors.append(row)

    platinum_count = len([c for c in high_value_contractors if c['ICP Tier'] == 'PLATINUM'])
    gold_count = len([c for c in high_value_contractors if c['ICP Tier'] == 'GOLD'])

    print(f"Found {len(high_value_contractors)} high-value contractors:")
    print(f"  PLATINUM (80-100): {platinum_count}")
    print(f"  GOLD (60-79): {gold_count}")

    if len(high_value_contractors) == 0:
        print("\n⚠️  No PLATINUM/GOLD tier contractors found!")
        print("Tip: Check ICP scoring thresholds")
        return

    # Write Google Ads-optimized CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header (Google Ads Customer Match format)
        writer.writerow([
            'Email',
            'Phone',
            'First Name',
            'Last Name',
            'Country',
            'Zip',
            'Company',
            'ICP_Tier',
            'ICP_Score',
            'OEM_Count',
            'OEM_Brands'
        ])

        # Data rows
        for contractor in high_value_contractors:
            # Format phone: remove all non-digits
            phone_raw = contractor['Phone']
            phone_clean = ''.join(filter(str.isdigit, phone_raw))

            # Generate business email from domain
            domain = contractor['Domain']
            if domain:
                # Common business email patterns
                email = f"info@{domain}"  # Most common
            else:
                email = ""

            # Parse company name for first/last (Google Ads likes this)
            company_name = contractor['Contractor Name']
            # For company names, use empty first/last (Google matches on company)
            first_name = ""
            last_name = ""

            writer.writerow([
                email,
                phone_clean,
                first_name,
                last_name,
                'US',
                contractor.get('ZIP', ''),
                company_name,
                contractor['ICP Tier'],
                contractor['ICP Fit Score'],
                contractor['OEM Count'],
                contractor['OEM Sources']
            ])

    print(f"\n✅ Google Ads Customer Match CSV saved: {output_path}")
    print()
    print("HIGH-VALUE TIER BREAKDOWN:")
    print(f"  PLATINUM (call first): {platinum_count} contractors")
    print(f"  GOLD (high priority): {gold_count} contractors")

    # Show multi-OEM distribution
    multi_oem = len([c for c in high_value_contractors if int(c['OEM Count']) >= 2])
    single_oem = len([c for c in high_value_contractors if int(c['OEM Count']) == 1])
    print()
    print(f"  Multi-OEM (2+ brands): {multi_oem} ← Managing multiple platforms!")
    print(f"  Single OEM: {single_oem}")

    # Show state distribution
    states = {}
    for c in high_value_contractors:
        state = c['State']
        states[state] = states.get(state, 0) + 1

    print("\n  Top 5 states:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {state}: {count} contractors")

    print()
    print("NEXT STEPS FOR PAKISTAN TEAM:")
    print("1. Upload CSV to Google Ads")
    print("2. Tools & Settings → Audience Manager → Customer Match")
    print("3. Upload customer list (match on email + phone)")
    print("4. Create Similar Audiences for expansion")
    print("5. Target: Commercial solar, backup power, facility management")
    print("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Google Ads Customer Match CSV")
    parser.add_argument("--input", required=True, help="Path to ICP analysis CSV")
    parser.add_argument("--output", default="output/gtm/google_ads_leads.csv", help="Output path")

    args = parser.parse_args()

    generate_google_ads_csv(args.input, args.output)
