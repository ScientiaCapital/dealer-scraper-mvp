#!/usr/bin/env python3
"""
Generate Complete Executive Package for CEO/CTO Meeting

Deliverables:
1. Executive Summary (markdown + metrics)
2. Tiered Contractor Lists (PLATINUM/GOLD/SILVER CSVs)
3. Keyword Strategy Document
4. Targeting Criteria Guide
5. Master Database (all contractors sorted by score)

For Monday presentation.
"""

import csv
import os
from datetime import datetime
from typing import List, Dict

# Import GTM generators
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def load_icp_data(icp_file: str) -> List[Dict]:
    """Load ICP analysis data from CSV."""
    contractors = []
    with open(icp_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)
    return contractors


def generate_executive_summary(contractors: List[Dict], output_dir: str):
    """Generate executive summary markdown for CEO/CTO."""

    # Calculate metrics
    total = len(contractors)

    tiers = {'PLATINUM': 0, 'GOLD': 0, 'SILVER': 0, 'BRONZE': 0}
    states_count = {}
    oem_distribution = {}

    for c in contractors:
        tier = c['ICP Tier']
        tiers[tier] += 1

        state = c['State']
        states_count[state] = states_count.get(state, 0) + 1

        oem_count = int(c['OEM Count'])
        oem_distribution[oem_count] = oem_distribution.get(oem_count, 0) + 1

    # Top contractors by score
    sorted_contractors = sorted(contractors, key=lambda x: int(x['ICP Fit Score']), reverse=True)
    top_50 = sorted_contractors[:50]

    # Generate markdown
    md = f"""# Coperniq Lead Generation - Executive Summary
**Prepared for CEO/CTO Meeting - {datetime.now().strftime('%B %d, %Y')}**

---

## 📊 OVERVIEW

**Total Contractor Database**: {total:,} qualified contractors across 15 SREC states

**Geographic Coverage**:
- **Primary Markets** (CA, TX, FL, PA, MA, NJ): {sum(states_count.get(s, 0) for s in ['CA', 'TX', 'FL', 'PA', 'MA', 'NJ']):,} contractors
- **Secondary Markets** (NY, OH, MD, DC, DE, NH, RI, CT, IL): {sum(states_count.get(s, 0) for s in ['NY', 'OH', 'MD', 'DC', 'DE', 'NH', 'RI', 'CT', 'IL']):,} contractors

**Targeting Strategy**:
- ✅ **140 Wealthy ZIP Codes** ($150K-$250K+ median income, 2024-2025 Census ACS)
- ✅ **SREC States Only** (sustainable solar markets post-ITC expiration)
- ✅ **Multi-OEM Focus** (contractors managing 2-3+ monitoring platforms = Coperniq's core pain point)

---

## 🎯 ICP TIER BREAKDOWN

Year 1 GTM-Aligned Scoring:
- **Resimercial** (35%): Both residential + commercial work
- **Multi-OEM** (25%): Managing 3-4+ platforms (core pain)
- **MEP+R** (25%): Self-performing multi-trade contractors
- **O&M** (15%): Ops & maintenance service contracts

**Contractor Tiers**:

| Tier | Count | Percentage | Call Priority |
|------|-------|------------|---------------|
| PLATINUM (80-100) | {tiers['PLATINUM']:,} | {tiers['PLATINUM']/total*100:.1f}% | **CALL FIRST** |
| GOLD (60-79) | {tiers['GOLD']:,} | {tiers['GOLD']/total*100:.1f}% | High Priority |
| SILVER (40-59) | {tiers['SILVER']:,} | {tiers['SILVER']/total*100:.1f}% | Medium Priority |
| BRONZE (<40) | {tiers['BRONZE']:,} | {tiers['BRONZE']/total*100:.1f}% | Low Priority |

---

## 🏆 TOP 50 CONTRACTORS (By ICP Fit Score)

**IMMEDIATE CALL LIST** - Highest scoring contractors for first outreach:

"""

    for i, c in enumerate(top_50, 1):
        md += f"""
### {i}. {c['Contractor Name']} ({c['State']})
- **ICP Score**: {c['ICP Fit Score']}/100 ({c['ICP Tier']} tier)
- **Phone**: {c['Phone']}
- **Domain**: {c['Domain']}
- **Location**: {c['City']}, {c['State']}
- **OEM Count**: {c['OEM Count']} ({c['OEM Sources']})
- **Scoring Breakdown**:
  - Resimercial: {c['Resimercial Score']}/100
  - O&M: {c['O&M Score']}/100
  - Multi-OEM: {c['Multi-OEM Score']}/100
  - MEP+R: {c['MEP+R Score']}/100
"""

    md += f"""

---

## 📈 MULTI-OEM BREAKDOWN

Contractors by OEM certification count:

"""

    for oem_count in sorted(oem_distribution.keys(), reverse=True):
        count = oem_distribution[oem_count]
        pct = count / total * 100
        md += f"- **{oem_count} OEMs**: {count:,} contractors ({pct:.1f}%)\n"

    md += f"""

**Key Insight**: Multi-OEM contractors (2-3+ certifications) feel Coperniq's pain point most acutely - managing multiple monitoring platforms (Enphase, Tesla, Generac, etc.)

---

## 🗺️ GEOGRAPHIC DISTRIBUTION

**Top 10 States by Contractor Count**:

"""

    top_states = sorted(states_count.items(), key=lambda x: x[1], reverse=True)[:10]
    for state, count in top_states:
        pct = count / total * 100
        md += f"- **{state}**: {count:,} contractors ({pct:.1f}%)\n"

    md += """

---

## 💡 GTM STRATEGY RECOMMENDATIONS

### Immediate Actions (Week 1)

1. **PLATINUM Tier Outreach**
   - Direct phone calls to top 50 contractors
   - Personalized email sequences highlighting multi-brand monitoring pain
   - LinkedIn outreach from founder/sales team

2. **Paid Ads Launch** (Pakistan GTM Team)
   - Google Search: $5K/month targeting O&M + multi-brand keywords
   - Meta/Instagram: $3K/month lookalike audiences from PLATINUM tier
   - Budget: $15K-30K/month total

3. **Content Marketing**
   - Case study: "How [PLATINUM Contractor] Unified Generac, Tesla, Enphase Monitoring"
   - Blog series: Multi-brand monitoring challenges
   - YouTube: Platform comparison videos

### Medium-Term (Months 2-3)

4. **Apollo Enrichment**
   - Add employee count, revenue, LinkedIn for commercial capability scoring
   - Improves GOLD → PLATINUM tier conversion

5. **Close CRM Integration**
   - Bulk import all 1,222 contractors
   - Smart Views by tier, state, OEM count
   - Automated sequences for each tier

6. **ITC Urgency Campaigns**
   - Commercial deadline: June 30, 2026 safe harbor
   - Residential deadline: December 31, 2025
   - Create urgency-based email/ad campaigns

### Long-Term (Months 4-6)

7. **Nationwide Expansion**
   - Expand beyond 15 SREC states to all 50 states
   - Target growth-stage MEP+R contractors ($5-10M revenue scaling to $50-100M)

8. **Outreach Automation**
   - Email sequences (SendGrid/Mailgun)
   - SMS campaigns (Twilio)
   - AI agent testing (future)

---

## 📁 DELIVERABLES FOR THIS MEETING

1. ✅ **Master Contractor Database** (all 1,222 sorted by ICP score)
2. ✅ **PLATINUM Tier List** (top-scored contractors - CALL FIRST)
3. ✅ **GOLD Tier List** (high-priority outreach)
4. ✅ **SILVER Tier List** (medium-priority nurture)
5. ✅ **Keyword Strategy** (50-100 commercial intent keywords for Google Ads)
6. ✅ **Targeting Criteria** (Meta/Instagram + Google Ads demographic/interest targeting)
7. ✅ **Executive Summary** (this document)

---

## 🚀 SUCCESS METRICS

**Campaign-Level KPIs** (Month 1):
- Outreach: 200+ phone calls to PLATINUM/GOLD tiers
- Meetings Booked: 25-50 qualified demos
- Pipeline Created: $500K-$1M in potential ARR

**Platform Benchmarks**:
- Google Search: $15-30 CPC, 3-5% CVR, <$200 CPL
- Meta/Instagram: $8-15 CPC, 1.5-3% CVR, <$200 CPL
- Expected Monthly Leads: 75-150 qualified contractor leads

**Business-Level KPIs** (Q1):
- SQL Rate: >30% (marketing qualified → sales qualified)
- Close Rate: >10% (demo → customer)
- Customer LTV: >$50K (multi-year contracts)

---

**Next Steps**: Review tiered contractor lists, approve GTM budget, assign outreach owners.

---

*Generated by Coperniq Lead Generation System*
*Data Sources: 17-OEM scraping across 140 wealthy ZIPs in 15 SREC states*
"""

    # Write summary
    summary_path = os.path.join(output_dir, 'EXECUTIVE_SUMMARY.md')
    with open(summary_path, 'w') as f:
        f.write(md)

    print(f"✅ Executive summary created: {summary_path}")
    return summary_path


def export_tiered_lists(contractors: List[Dict], output_dir: str):
    """Export separate CSVs for each ICP tier."""

    # Sort by ICP fit score (highest first)
    sorted_contractors = sorted(contractors, key=lambda x: int(x['ICP Fit Score']), reverse=True)

    tiers = {
        'PLATINUM': [c for c in sorted_contractors if c['ICP Tier'] == 'PLATINUM'],
        'GOLD': [c for c in sorted_contractors if c['ICP Tier'] == 'GOLD'],
        'SILVER': [c for c in sorted_contractors if c['ICP Tier'] == 'SILVER'],
        'BRONZE': [c for c in sorted_contractors if c['ICP Tier'] == 'BRONZE']
    }

    tier_files = {}

    for tier_name, tier_contractors in tiers.items():
        if not tier_contractors:
            continue

        filename = f"{tier_name}_tier_contractors.csv"
        filepath = os.path.join(output_dir, filename)

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=tier_contractors[0].keys())
            writer.writeheader()
            writer.writerows(tier_contractors)

        tier_files[tier_name] = filepath
        print(f"✅ {tier_name} tier exported: {len(tier_contractors)} contractors → {filepath}")

    return tier_files


def export_master_database(contractors: List[Dict], output_dir: str):
    """Export complete sorted master database."""

    # Sort by ICP fit score (highest first)
    sorted_contractors = sorted(contractors, key=lambda x: int(x['ICP Fit Score']), reverse=True)

    master_path = os.path.join(output_dir, 'MASTER_CONTRACTOR_DATABASE.csv')

    with open(master_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted_contractors[0].keys())
        writer.writeheader()
        writer.writerows(sorted_contractors)

    print(f"✅ Master database exported: {len(sorted_contractors)} contractors → {master_path}")
    return master_path


def main():
    print("\n" + "="*70)
    print("🚀 GENERATING EXECUTIVE PACKAGE FOR CEO/CTO MEETING")
    print("="*70)
    print()

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d')
    output_dir = f"output/gtm/executive_package_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Output directory: {output_dir}")
    print()

    # Load existing ICP data
    icp_file = "output/icp_analysis_20251025_172037.csv"
    print(f"Loading ICP data from: {icp_file}")
    contractors = load_icp_data(icp_file)
    print(f"✓ Loaded {len(contractors)} contractors")
    print()

    # Generate deliverables
    print("GENERATING DELIVERABLES:")
    print("-" * 70)

    # 1. Executive Summary
    summary_path = generate_executive_summary(contractors, output_dir)
    print()

    # 2. Tiered Lists
    tier_files = export_tiered_lists(contractors, output_dir)
    print()

    # 3. Master Database
    master_path = export_master_database(contractors, output_dir)
    print()

    # 4. Keyword Strategy
    print("Generating keyword strategy...")
    from scripts.gtm.generate_keyword_strategy import generate_keyword_strategy
    keyword_path = os.path.join(output_dir, "keyword_strategy.md")
    generate_keyword_strategy(keyword_path)
    print()

    # 5. Targeting Guide
    print("Generating targeting criteria...")
    from scripts.gtm.generate_targeting_guide import generate_targeting_guide
    targeting_path = os.path.join(output_dir, "targeting_criteria.md")
    generate_targeting_guide(targeting_path)
    print()

    # Final summary
    print("="*70)
    print("✅ EXECUTIVE PACKAGE COMPLETE!")
    print("="*70)
    print()
    print("DELIVERABLES:")
    print(f"  1. Executive Summary: {summary_path}")
    print(f"  2. Master Database: {master_path}")
    for tier, path in tier_files.items():
        print(f"  3. {tier} Tier List: {path}")
    print(f"  4. Keyword Strategy: {keyword_path}")
    print(f"  5. Targeting Guide: {targeting_path}")
    print()
    print(f"📁 All files in: {output_dir}")
    print()
    print("READY FOR MONDAY CEO/CTO MEETING! 🎉")
    print("="*70)


if __name__ == "__main__":
    main()
