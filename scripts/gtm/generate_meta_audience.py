#!/usr/bin/env python3
"""
Generate Meta/Instagram Custom Audience CSV
Extracts PLATINUM tier contractors for lookalike targeting
"""
import csv
import sys
from pathlib import Path

def generate_meta_audience_csv(icp_analysis_path: str, output_path: str):
    """
    Generate Meta/Instagram Custom Audience CSV from ICP analysis.

    Format optimized for Meta Business Manager upload:
    - Company Name (for business matching)
    - Phone (primary match key)
    - Domain (secondary match key)
    - City, State, ZIP (geographic matching)

    Args:
        icp_analysis_path: Path to ICP analysis CSV
        output_path: Path to save Meta audience CSV
    """
    print("\n" + "="*70)
    print("📱 GENERATING META/INSTAGRAM CUSTOM AUDIENCE")
    print("="*70)
    print(f"Source: {icp_analysis_path}")
    print(f"Output: {output_path}")
    print()

    platinum_contractors = []

    # Read ICP analysis and filter to PLATINUM tier
    with open(icp_analysis_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['ICP Tier'] == 'PLATINUM':
                platinum_contractors.append(row)

    print(f"Found {len(platinum_contractors)} PLATINUM tier contractors")

    if len(platinum_contractors) == 0:
        print("\n⚠️  No PLATINUM tier contractors found!")
        print("Tip: Try lowering threshold or check ICP scoring logic")
        return

    # Write Meta-optimized CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header (Meta Custom Audience format)
        writer.writerow([
            'company_name',
            'phone',
            'email_domain',
            'city',
            'state',
            'zip',
            'icp_score',
            'oem_count',
            'oem_brands'
        ])

        # Data rows
        for contractor in platinum_contractors:
            # Format phone: remove all non-digits for Meta matching
            phone_raw = contractor['Phone']
            phone_clean = ''.join(filter(str.isdigit, phone_raw))

            # Extract email domain from website domain
            domain = contractor['Domain']
            email_domain = f"@{domain}" if domain else ""

            writer.writerow([
                contractor['Contractor Name'],
                phone_clean,
                email_domain,
                contractor['City'],
                contractor['State'],
                contractor.get('ZIP', ''),  # May not exist in all versions
                contractor['ICP Fit Score'],
                contractor['OEM Count'],
                contractor['OEM Sources']
            ])

    print(f"\n✅ Meta Custom Audience CSV saved: {output_path}")
    print()
    print("PLATINUM TIER BREAKDOWN:")
    print(f"  Total contractors: {len(platinum_contractors)}")

    # Show OEM distribution
    multi_oem = len([c for c in platinum_contractors if int(c['OEM Count']) >= 2])
    print(f"  Multi-OEM (2+ brands): {multi_oem} ← Highest value!")

    # Show state distribution
    states = {}
    for c in platinum_contractors:
        state = c['State']
        states[state] = states.get(state, 0) + 1

    print("\n  Top 5 states:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {state}: {count} contractors")

    print()
    print("NEXT STEPS FOR PAKISTAN TEAM:")
    print("1. Upload CSV to Meta Business Manager")
    print("2. Create Custom Audience → Upload Customer List")
    print("3. Use for Lookalike Audiences (1-3% similarity)")
    print("4. Target: Commercial contractors, facility managers, energy systems")
    print("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Meta/Instagram Custom Audience CSV")
    parser.add_argument("--input", required=True, help="Path to ICP analysis CSV")
    parser.add_argument("--output", default="output/gtm/meta_platinum_leads.csv", help="Output path")

    args = parser.parse_args()

    generate_meta_audience_csv(args.input, args.output)
