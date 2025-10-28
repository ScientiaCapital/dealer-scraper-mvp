#!/usr/bin/env python3
"""
Apply Year 1 GTM-aligned ICP scoring to grandmaster list
Scoring Dimensions:
  - Resimercial (35%): Residential + Commercial capability
  - Multi-OEM (25%): Managing multiple OEM platforms
  - MEP+R (25%): Multi-trade (Mechanical, Electrical, Plumbing + Roofing)
  - O&M (15%): Operations & Maintenance service contracts
"""
import csv
import re
from datetime import datetime
from typing import Dict, Tuple

# Keyword patterns for capability detection
RESIMERCIAL_KEYWORDS = [
    'commercial', 'residential', 'resimercial', 'home', 'business',
    'industrial', 'retail', 'office', 'apartment', 'multi-family'
]

MEP_KEYWORDS = {
    'mechanical': ['hvac', 'heating', 'cooling', 'air conditioning', 'ventilation', 'plumbing'],
    'electrical': ['electric', 'electrical', 'lighting', 'wiring'],
    'plumbing': ['plumbing', 'plumber', 'water', 'pipe', 'drain'],
    'roofing': ['roof', 'roofing', 'roofer', 'shingle', 'solar roof']
}

OM_KEYWORDS = [
    'maintenance', 'service', 'repair', 'monitoring', 'support',
    'warranty', 'inspection', 'preventive', 'scheduled', '24/7', 'emergency'
]

def normalize_text(text: str) -> str:
    """Normalize text for keyword matching"""
    if not text:
        return ""
    return text.lower().strip()

def score_resimercial(contractor: Dict) -> Tuple[int, str]:
    """
    Score residential + commercial capability (0-100)
    Returns: (score, evidence)
    """
    name = normalize_text(contractor.get('name', ''))
    tier = normalize_text(contractor.get('tier', ''))

    # Check for explicit resimercial indicators
    has_commercial = any(kw in name for kw in ['commercial', 'industrial', 'business'])
    has_residential = any(kw in name for kw in ['residential', 'home', 'house'])

    # Elite/Premier tiers often serve both markets
    is_elite = any(t in tier for t in ['elite', 'premier', 'platinum', 'certified'])

    # Generator dealers often serve both residential and commercial
    oems = normalize_text(contractor.get('OEMs_Certified', ''))
    has_generators = any(g in oems for g in ['generac', 'cummins', 'briggs', 'kohler'])

    evidence = []

    if has_commercial and has_residential:
        score = 100
        evidence.append("Explicit commercial + residential in name")
    elif has_commercial:
        score = 70
        evidence.append("Commercial indicator in name")
    elif has_residential:
        score = 60
        evidence.append("Residential indicator in name")
    elif is_elite and has_generators:
        score = 75
        evidence.append("Elite generator dealer (likely serves both markets)")
    elif has_generators:
        score = 50
        evidence.append("Generator dealer (mixed market)")
    else:
        score = 40
        evidence.append("Market scope unclear")

    return score, "; ".join(evidence)

def score_multi_oem(contractor: Dict) -> Tuple[int, str]:
    """
    Score multi-OEM platform management complexity (0-100)
    Returns: (score, evidence)
    """
    oem_count = int(contractor.get('OEM_Count', 1))
    oems = contractor.get('OEMs_Certified', '')

    # Scoring scale
    if oem_count >= 4:
        score = 100
        evidence = f"4+ OEM certifications ({oems})"
    elif oem_count == 3:
        score = 100
        evidence = f"3 OEM certifications ({oems})"
    elif oem_count == 2:
        score = 50
        evidence = f"2 OEM certifications ({oems})"
    else:
        score = 25
        evidence = f"Single OEM ({oems})"

    return score, evidence

def score_mepr(contractor: Dict) -> Tuple[int, str]:
    """
    Score multi-trade capability: MEP+R (0-100)
    Mechanical, Electrical, Plumbing + Roofing
    Returns: (score, evidence)
    """
    name = normalize_text(contractor.get('name', ''))

    trades = {
        'Mechanical': False,
        'Electrical': False,
        'Plumbing': False,
        'Roofing': False
    }

    # Detect mechanical (HVAC)
    if any(kw in name for kw in MEP_KEYWORDS['mechanical']):
        trades['Mechanical'] = True

    # Detect electrical
    if any(kw in name for kw in MEP_KEYWORDS['electrical']):
        trades['Electrical'] = True

    # Detect plumbing
    if any(kw in name for kw in MEP_KEYWORDS['plumbing']):
        trades['Plumbing'] = True

    # Detect roofing
    if any(kw in name for kw in MEP_KEYWORDS['roofing']):
        trades['Roofing'] = True

    # Multi-trade indicators
    is_multi_trade = any(phrase in name for phrase in [
        'all trades', 'full service', 'all phase', 'complete', 'total'
    ])

    active_trades = [t for t, active in trades.items() if active]
    trade_count = len(active_trades)

    # Scoring
    if trade_count >= 3 or is_multi_trade:
        score = 100
        evidence = f"Multi-trade: {', '.join(active_trades) if active_trades else 'All Trades'}"
    elif trade_count == 2:
        score = 75
        evidence = f"Dual-trade: {', '.join(active_trades)}"
    elif trade_count == 1:
        score = 50
        evidence = f"Single trade: {active_trades[0]}"
    else:
        # Generators imply electrical at minimum
        score = 50
        evidence = "Generator installation (implies electrical)"

    return score, evidence

def score_om(contractor: Dict) -> Tuple[int, str]:
    """
    Score Operations & Maintenance capability (0-100)
    Returns: (score, evidence)
    """
    name = normalize_text(contractor.get('name', ''))
    tier = normalize_text(contractor.get('tier', ''))

    # Check for O&M keywords
    om_indicators = [kw for kw in OM_KEYWORDS if kw in name]

    # Elite tiers often include maintenance contracts
    is_elite = any(t in tier for t in ['elite', 'premier', 'platinum'])

    if len(om_indicators) >= 2:
        score = 100
        evidence = f"Strong O&M indicators: {', '.join(om_indicators[:3])}"
    elif len(om_indicators) == 1:
        score = 75
        evidence = f"O&M indicator: {om_indicators[0]}"
    elif is_elite:
        score = 60
        evidence = f"Elite tier (likely offers maintenance)"
    elif 'service' in name or 'solutions' in name:
        score = 50
        evidence = "Service-oriented name"
    else:
        score = 25
        evidence = "O&M capability unclear"

    return score, evidence

def calculate_icp_score(contractor: Dict) -> Dict:
    """
    Calculate weighted ICP score and assign tier
    Returns: contractor dict with scoring fields added
    """
    # Score each dimension
    resimercial_score, resimercial_evidence = score_resimercial(contractor)
    multi_oem_score, multi_oem_evidence = score_multi_oem(contractor)
    mepr_score, mepr_evidence = score_mepr(contractor)
    om_score, om_evidence = score_om(contractor)

    # Apply Year 1 GTM weights
    weighted_score = (
        (resimercial_score * 0.35) +
        (multi_oem_score * 0.25) +
        (mepr_score * 0.25) +
        (om_score * 0.15)
    )

    # Assign ICP tier
    if weighted_score >= 80:
        icp_tier = 'PLATINUM'
    elif weighted_score >= 60:
        icp_tier = 'GOLD'
    elif weighted_score >= 40:
        icp_tier = 'SILVER'
    else:
        icp_tier = 'BRONZE'

    # Add scoring fields to contractor
    contractor['ICP_Score'] = round(weighted_score, 1)
    contractor['ICP_Tier'] = icp_tier

    contractor['Resimercial_Score'] = resimercial_score
    contractor['Resimercial_Evidence'] = resimercial_evidence

    contractor['MultiOEM_Score'] = multi_oem_score
    contractor['MultiOEM_Evidence'] = multi_oem_evidence

    contractor['MEPR_Score'] = mepr_score
    contractor['MEPR_Evidence'] = mepr_evidence

    contractor['OM_Score'] = om_score
    contractor['OM_Evidence'] = om_evidence

    return contractor

def main():
    print("=" * 70)
    print("APPLYING YEAR 1 GTM ICP SCORING")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📊 Scoring Dimensions:")
    print("   • Resimercial (35%): Residential + Commercial")
    print("   • Multi-OEM (25%): Multiple OEM platforms")
    print("   • MEP+R (25%): Multi-trade capability")
    print("   • O&M (15%): Maintenance service contracts")
    print("=" * 70)

    # Load grandmaster list
    input_file = 'output/grandmaster_list_20251028.csv'

    print(f"\n📂 Loading grandmaster list: {input_file}")

    contractors = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)

    print(f"   Loaded {len(contractors)} contractors")

    # Apply ICP scoring
    print(f"\n🎯 Calculating ICP scores...")

    scored_contractors = []
    for contractor in contractors:
        scored = calculate_icp_score(contractor)
        scored_contractors.append(scored)

    # Count by tier
    tier_counts = {'PLATINUM': 0, 'GOLD': 0, 'SILVER': 0, 'BRONZE': 0}
    for contractor in scored_contractors:
        tier = contractor['ICP_Tier']
        tier_counts[tier] += 1

    print(f"\n📊 ICP Tier Distribution:")
    for tier in ['PLATINUM', 'GOLD', 'SILVER', 'BRONZE']:
        count = tier_counts[tier]
        pct = (count / len(scored_contractors)) * 100

        if tier == 'PLATINUM':
            icon = '💎'
        elif tier == 'GOLD':
            icon = '🥇'
        elif tier == 'SILVER':
            icon = '🥈'
        else:
            icon = '🥉'

        print(f"   {icon} {tier}: {count} ({pct:.1f}%)")

    # Save scored results
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = f"output/icp_scored_contractors_{timestamp}.csv"

    # Define output field order
    priority_fields = [
        'name', 'phone', 'domain', 'website',
        'ICP_Score', 'ICP_Tier',
        'OEM_Count', 'OEMs_Certified',
        'Resimercial_Score', 'Resimercial_Evidence',
        'MultiOEM_Score', 'MultiOEM_Evidence',
        'MEPR_Score', 'MEPR_Evidence',
        'OM_Score', 'OM_Evidence',
        'street', 'city', 'state', 'zip',
        'rating', 'review_count', 'tier',
        'oem_source', 'scraped_from_zip'
    ]

    # Get all fields
    if scored_contractors:
        all_fields = set(scored_contractors[0].keys())
        remaining = [f for f in all_fields if f not in priority_fields]
        fieldnames = priority_fields + remaining
    else:
        fieldnames = priority_fields

    # Sort by ICP_Score descending
    sorted_contractors = sorted(scored_contractors, key=lambda x: -float(x['ICP_Score']))

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_contractors)

    print(f"\n💾 Saved ICP-scored contractors: {output_file}")

    # Save Top 200 ranked prospects
    top_200 = sorted_contractors[:200]
    top_200_file = f"output/top_200_prospects_{timestamp}.csv"

    with open(top_200_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(top_200)

    print(f"💾 Saved Top 200 prospects: {top_200_file}")

    # Summary statistics for Top 200
    top_200_tiers = {'PLATINUM': 0, 'GOLD': 0, 'SILVER': 0, 'BRONZE': 0}
    for contractor in top_200:
        tier = contractor['ICP_Tier']
        top_200_tiers[tier] += 1

    print(f"\n📊 Top 200 Tier Breakdown:")
    for tier in ['PLATINUM', 'GOLD', 'SILVER', 'BRONZE']:
        count = top_200_tiers[tier]
        print(f"      {tier}: {count}")

    # Geographic distribution of top prospects
    states = {}
    for contractor in top_200:
        state = contractor.get('state', 'Unknown')
        if state:
            states[state] = states.get(state, 0) + 1

    print(f"\n   Top 10 States (Top 200):")
    for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
        print(f"      {state}: {count}")

    # Multi-OEM breakdown in Top 200
    multi_oem_200 = sum(1 for c in top_200 if int(c.get('OEM_Count', 1)) >= 2)
    print(f"\n   Multi-OEM contractors in Top 200: {multi_oem_200}")

    print(f"\n✅ ICP scoring complete!")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
