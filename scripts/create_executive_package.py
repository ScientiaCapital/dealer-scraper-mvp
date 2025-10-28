#!/usr/bin/env python3
"""
Create comprehensive Executive Package for leadership team
Based on grandmaster list with ICP scoring
"""
import csv
import os
from datetime import datetime
from collections import defaultdict

def load_icp_data():
    """Load ICP-scored contractors"""
    contractors = []
    with open('output/icp_scored_contractors_20251028.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)
    return contractors

def create_tier_csvs(contractors, output_dir):
    """Create separate CSVs for each ICP tier"""

    tiers = {'PLATINUM': [], 'GOLD': [], 'SILVER': [], 'BRONZE': []}

    for contractor in contractors:
        tier = contractor.get('ICP_Tier', 'BRONZE')
        tiers[tier].append(contractor)

    # Get fieldnames
    if contractors:
        fieldnames = list(contractors[0].keys())
    else:
        return

    # Save each tier
    for tier, tier_contractors in tiers.items():
        if tier_contractors:
            filename = f"{output_dir}/{tier}_tier_contractors.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tier_contractors)

            print(f"   💾 {tier}: {len(tier_contractors)} contractors → {filename}")

def create_multi_oem_report(output_dir):
    """Create multi-OEM analysis report"""

    # Load multi-OEM crossovers
    contractors = []
    with open('output/multi_oem_crossovers_20251028.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)

    # Count by OEM count
    by_oem_count = defaultdict(list)
    for c in contractors:
        count = int(c.get('OEM_Count', 1))
        by_oem_count[count].append(c)

    md = f"""# Multi-OEM Contractor Analysis
**Date:** {datetime.now().strftime('%B %d, %Y')}

---

## 📊 Multi-OEM Distribution

**Total Multi-OEM Contractors:** {len(contractors)}

| OEM Certifications | Count | % of Multi-OEM |
|-------------------|-------|----------------|
"""

    for count in sorted(by_oem_count.keys(), reverse=True):
        contractors_list = by_oem_count[count]
        pct = (len(contractors_list) / len(contractors)) * 100

        if count >= 3:
            emoji = '💎'
            label = f'{count} OEM Networks (UNICORNS)'
        elif count == 2:
            emoji = '🥇'
            label = f'{count} OEM Networks'
        else:
            emoji = '🥈'
            label = f'{count} OEM Network'

        md += f"| {emoji} **{label}** | {len(contractors_list)} | {pct:.1f}% |\n"

    md += "\n---\n\n## 💎 Triple-OEM Contractors\n\n"

    if 3 in by_oem_count:
        triple_oem = sorted(by_oem_count[3], key=lambda x: x.get('name', ''))

        md += "| Company | OEMs | State | Phone | ICP Score |\n"
        md += "|---------|------|-------|-------|----------|\n"

        for c in triple_oem:
            name = c.get('name', 'Unknown')[:40]
            oems = c.get('OEMs_Certified', 'Unknown')[:30]
            state = c.get('state', 'N/A')
            phone = c.get('phone', 'N/A')
            score = c.get('ICP_Score', 'N/A')

            md += f"| {name} | {oems} | {state} | {phone} | {score} |\n"
    else:
        md += "*No triple-OEM contractors found in current dataset.*\n"

    md += "\n---\n\n## 🥇 Dual-OEM Contractors (Top 20)\n\n"

    if 2 in by_oem_count:
        dual_oem = sorted(by_oem_count[2], key=lambda x: -float(x.get('ICP_Score', 0)))[:20]

        md += "| Rank | Company | OEMs | State | ICP Score |\n"
        md += "|------|---------|------|-------|----------|\n"

        for i, c in enumerate(dual_oem, 1):
            name = c.get('name', 'Unknown')[:35]
            oems = c.get('OEMs_Certified', 'Unknown')[:25]
            state = c.get('state', 'N/A')
            score = c.get('ICP_Score', 'N/A')

            md += f"| {i} | {name} | {oems} | {state} | {score} |\n"

    md += "\n---\n\n## 🔍 Key Insights\n\n"
    md += "### Current Multi-OEM Pattern\n\n"
    md += "All multi-OEM contractors are currently **generator-focused**:\n"
    md += "- Generac + Cummins\n"
    md += "- Generac + Briggs & Stratton\n"
    md += "- Cummins + Briggs & Stratton\n\n"
    md += "**Strategic Implication:** Contractors managing both generators AND solar/battery (Tesla + Enphase + Generac) represent a **blue ocean opportunity**. Current dataset doesn't include enough solar/battery OEMs to find these cross-category multi-platform contractors.\n\n"
    md += "### Recommended Next Steps\n\n"
    md += "1. **Expand Solar/Battery Coverage:**\n"
    md += "   - Add SolarEdge, Fronius, SMA (solar inverters)\n"
    md += "   - Add SimpliPhi, LG, Panasonic (battery storage)\n\n"
    md += "2. **Target Current Multi-OEM Contractors:**\n"
    md += "   - 105 contractors managing multiple generator brands\n"
    md += "   - Already experiencing platform management pain\n"
    md += "   - Strong candidates for Coperniq's value proposition\n\n"

    filename = f"{output_dir}/MULTI_OEM_ANALYSIS.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"   📄 Multi-OEM Analysis → {filename}")

def create_readme(output_dir, stats):
    """Create README for executive package"""

    md = f"""# Executive Package - Coperniq Contractor Database
**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## 📦 Package Contents

### 1. ICP Tier Files

| File | Contractors | Description |
|------|-------------|-------------|
| **PLATINUM_tier_contractors.csv** | {stats['PLATINUM']} | Dream clients (ICP score 80-100) |
| **GOLD_tier_contractors.csv** | {stats['GOLD']} | High priority (ICP score 60-79) |
| **SILVER_tier_contractors.csv** | {stats['SILVER']:,} | Qualified (ICP score 40-59) |
| **BRONZE_tier_contractors.csv** | {stats['BRONZE']} | Lower priority (ICP score <40) |

### 2. Analysis Reports

- **MULTI_OEM_ANALYSIS.md** - Detailed analysis of multi-OEM contractors (105 total)
- **README.md** - This file

---

## 🎯 Quick Stats

**Total Database:**
- **Unique Contractors:** {stats['total']:,}
- **OEM Networks:** 5 (Tesla, Enphase, Generac, Cummins, Briggs & Stratton)
- **Geographic Coverage:** 15 SREC states, 140 wealthy ZIP codes
- **Multi-OEM Contractors:** 105 (3.5% of database)
  - Triple-OEM (3+ brands): 5 contractors (0.2%)
  - Dual-OEM (2 brands): 100 contractors (3.4%)

**ICP Tier Breakdown:**
- 💎 PLATINUM: {stats['PLATINUM']} ({stats['PLATINUM']/stats['total']*100:.1f}%)
- 🥇 GOLD: {stats['GOLD']} ({stats['GOLD']/stats['total']*100:.1f}%)
- 🥈 SILVER: {stats['SILVER']:,} ({stats['SILVER']/stats['total']*100:.1f}%)
- 🥉 BRONZE: {stats['BRONZE']} ({stats['BRONZE']/stats['total']*100:.1f}%)

---

## 🔍 How to Use This Data

### For BDR/Sales Team

1. **Start with GOLD tier** (`GOLD_tier_contractors.csv`)
   - 35 highest-value prospects
   - Focus on multi-OEM contractors first (check `OEM_Count` column)
   - Review `Resimercial_Evidence`, `MEPR_Evidence`, `OM_Evidence` for talking points

2. **Review Multi-OEM Analysis** (`MULTI_OEM_ANALYSIS.md`)
   - Identifies contractors managing 2-3+ OEM platforms
   - These feel the pain point most acutely (managing multiple dashboards)

3. **Use ICP Evidence Fields for Outreach:**
   - `Resimercial_Evidence`: Talk about serving both home + business customers
   - `MEPR_Evidence`: Highlight multi-trade capabilities (HVAC + Electrical + Plumbing + Roofing)
   - `OM_Evidence`: Discuss ongoing maintenance contract opportunities

### For Marketing Team

1. **Upload Audiences:**
   - GOLD tier contractors → Google Ads Customer Match
   - Multi-OEM contractors → Meta Custom Audience (for lookalikes)

2. **Messaging Angles:**
   - Multi-OEM contractors: *"Managing Generac, Cummins, AND Briggs dashboards? There's a better way."*
   - Resimercial contractors: *"One platform for residential AND commercial monitoring"*
   - Multi-trade contractors: *"Built for contractors who do it all"*

### For Executive Team

- **Market Size:** 2,959 qualified contractors across SREC states
- **High-Value Segment:** 35 GOLD + 5 PLATINUM-potential (multi-OEM contractors)
- **Blue Ocean Opportunity:** True multi-platform contractors (solar + battery + generator) remain rare
- **Recommended Expansion:** Add solar inverter brands (SolarEdge, Fronius, SMA) to find cross-category multi-OEM contractors

---

## 📊 ICP Scoring Methodology

**Year 1 GTM-Aligned Dimensions:**

1. **Resimercial (35% weight):** Residential + Commercial capability
   - Contractors serving both markets = scaling businesses ($5-10M → $50-100M revenue)
   - Most sustainable business model

2. **Multi-OEM (25% weight):** Managing multiple OEM platforms
   - 3+ OEMs = 100 points (Coperniq solves their exact pain point)
   - 2 OEMs = 50 points (feeling the pain)
   - 1 OEM = 25 points (baseline)

3. **MEP+R (25% weight):** Multi-trade capability
   - Mechanical + Electrical + Plumbing + Roofing
   - Self-performing contractors = platform power users
   - Blue ocean market (less saturated than pure solar installers)

4. **O&M (15% weight):** Operations & Maintenance
   - Ongoing service contracts = recurring revenue
   - Platform features maturing in Year 2

**Final ICP Score:** Weighted average (0-100)

**Tier Assignment:**
- PLATINUM: 80-100 (dream clients)
- GOLD: 60-79 (high priority)
- SILVER: 40-59 (qualified)
- BRONZE: <40 (lower priority)

---

## 🌍 Data Sources

**OEM Dealer Locators:**
1. Tesla Powerwall Premier Installers
2. Enphase Platinum/Gold Certified Installers
3. Generac Authorized Dealers (Elite tier prioritized)
4. Cummins Authorized Dealers
5. Briggs & Stratton Dealers (Elite IQ tier prioritized)

**Scraping Period:** October 25-28, 2025
**Geographic Targeting:** 140 wealthy ZIP codes ($150K-$250K+ median household income) across 15 SREC states
**Quality Control:** Phone number deduplication across all OEMs (3.6% duplicate rate)

---

## 📧 Questions?

Contact: BDR Team
**Package Location:** `output/gtm/executive_package_20251028/`
"""

    filename = f"{output_dir}/README.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"   📄 README → {filename}")

def main():
    print("=" * 70)
    print("CREATING EXECUTIVE PACKAGE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d")
    output_dir = f"output/gtm/executive_package_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📂 Creating package: {output_dir}")

    # Load data
    print(f"\n📊 Loading ICP-scored contractors...")
    contractors = load_icp_data()
    print(f"   Loaded {len(contractors):,} contractors")

    # Calculate stats
    stats = {
        'total': len(contractors),
        'PLATINUM': sum(1 for c in contractors if c.get('ICP_Tier') == 'PLATINUM'),
        'GOLD': sum(1 for c in contractors if c.get('ICP_Tier') == 'GOLD'),
        'SILVER': sum(1 for c in contractors if c.get('ICP_Tier') == 'SILVER'),
        'BRONZE': sum(1 for c in contractors if c.get('ICP_Tier') == 'BRONZE'),
    }

    # Create tier CSVs
    print(f"\n📊 Creating tier-specific CSV files...")
    create_tier_csvs(contractors, output_dir)

    # Create multi-OEM analysis
    print(f"\n📄 Creating multi-OEM analysis...")
    create_multi_oem_report(output_dir)

    # Create README
    print(f"\n📄 Creating README...")
    create_readme(output_dir, stats)

    print(f"\n✅ Executive package complete!")
    print(f"\n📦 Package location: {output_dir}/")
    print(f"   Files created:")
    print(f"      • PLATINUM_tier_contractors.csv ({stats['PLATINUM']} contractors)")
    print(f"      • GOLD_tier_contractors.csv ({stats['GOLD']} contractors)")
    print(f"      • SILVER_tier_contractors.csv ({stats['SILVER']:,} contractors)")
    print(f"      • BRONZE_tier_contractors.csv ({stats['BRONZE']} contractors)")
    print(f"      • MULTI_OEM_ANALYSIS.md")
    print(f"      • README.md")

    print(f"\n   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
