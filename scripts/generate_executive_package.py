#!/usr/bin/env python3
"""
Generate Executive Package - 10-OEM Expansion Results

Creates comprehensive executive materials:
1. Executive Summary (Markdown)
2. Tier-specific CSVs (GOLD, SILVER, BRONZE)
3. Multi-OEM Deep Dive Analysis
4. Statistical Dashboard
"""
import csv
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

def load_scored_contractors(filepath: str) -> List[Dict]:
    """Load ICP-scored contractors"""
    contractors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)
    return contractors

def generate_executive_summary(contractors: List[Dict], timestamp: str):
    """Generate executive summary in Markdown"""

    total_contractors = len(contractors)

    # Tier distribution
    tiers = defaultdict(int)
    for c in contractors:
        tiers[c['ICP_Tier']] += 1

    # Multi-OEM breakdown
    multi_oem = [c for c in contractors if int(c.get('OEM_Count', 1)) >= 2]
    triple_oem = [c for c in contractors if int(c.get('OEM_Count', 1)) >= 3]

    # Capability distribution
    hvac_contractors = [c for c in contractors if c.get('has_hvac') == 'True']
    solar_contractors = [c for c in contractors if c.get('has_solar') == 'True']
    hvac_solar = [c for c in contractors if c.get('has_hvac') == 'True' and c.get('has_solar') == 'True']

    # Geographic distribution
    states = defaultdict(int)
    for c in contractors:
        state = c.get('state', 'Unknown')
        if state:
            states[state] += 1

    # Top GOLD prospects
    gold_prospects = [c for c in contractors if c['ICP_Tier'] == 'GOLD']
    gold_prospects_sorted = sorted(gold_prospects, key=lambda x: -float(x['ICP_Score']))[:20]

    # Generate markdown report
    md = f"""# 10-OEM HVAC + Solar Expansion Executive Summary

**Generated**: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## 🎯 Key Results

### Dataset Growth
- **Total Unique Contractors**: {total_contractors:,}
- **Previous Dataset (5 OEMs)**: 3,242 contractors
- **Growth**: {total_contractors - 3242:,} contractors (+{((total_contractors - 3242) / 3242 * 100):.1f}%)

### OEM Network Coverage
- **Total OEM Networks**: 10 (Generac, Tesla, Enphase, SolarEdge, Briggs & Stratton, Carrier, Mitsubishi, Trane, York, SMA Solar)
- **HVAC Contractors**: {len(hvac_contractors):,} ({len(hvac_contractors)/total_contractors*100:.1f}%)
- **Solar Contractors**: {len(solar_contractors):,} ({len(solar_contractors)/total_contractors*100:.1f}%)
- **HVAC + Solar (Resimercial Signal)**: {len(hvac_solar)} contractors

---

## 💎 ICP Tier Distribution

Year 1 GTM-aligned scoring (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)

| Tier | Count | Percentage | Description |
|------|-------|------------|-------------|
| 💎 **PLATINUM** (≥80) | {tiers['PLATINUM']} | {tiers['PLATINUM']/total_contractors*100:.1f}% | Triple-threat: Multi-OEM + Resimercial + Multi-trade |
| 🥇 **GOLD** (60-79) | {tiers['GOLD']} | {tiers['GOLD']/total_contractors*100:.1f}% | **Priority outreach** - Strong 2-3 dimensions |
| 🥈 **SILVER** (40-59) | {tiers['SILVER']:,} | {tiers['SILVER']/total_contractors*100:.1f}% | Qualified prospects - Nurture campaign |
| 🥉 **BRONZE** (<40) | {tiers['BRONZE']} | {tiers['BRONZE']/total_contractors*100:.1f}% | Low priority - Limited fit |

**Action Items**:
- ✅ GOLD tier ({tiers['GOLD']} contractors) ready for immediate outreach
- ✅ Top 200 prospects exported for BDR workflow
- ✅ Multi-OEM contractors flagged for platform pain point messaging

---

## 🏆 Multi-OEM Contractor Analysis

**Key Insight**: Contractors certified with 2-3 OEM brands are highest-value prospects (platform consolidation pain)

| OEM Count | Contractors | Percentage | Value Tier |
|-----------|-------------|------------|------------|
| **3+ OEMs** (UNICORNS) | {len(triple_oem)} | {len(triple_oem)/total_contractors*100:.2f}% | 💎 Highest priority - Managing 3+ platforms |
| **2 OEMs** (HIGH VALUE) | {len(multi_oem) - len(triple_oem)} | {(len(multi_oem) - len(triple_oem))/total_contractors*100:.1f}% | 🥇 Strong prospects - Juggling 2 platforms |
| **1 OEM** (STANDARD) | {total_contractors - len(multi_oem):,} | {(total_contractors - len(multi_oem))/total_contractors*100:.1f}% | Standard prospects |

**Multi-OEM Messaging**:
> "Managing Generac, Tesla, and Enphase platforms separately? Coperniq consolidates all monitoring into one dashboard."

---

## 📊 Capability Distribution

### Product Capabilities
- **HVAC Systems**: {len(hvac_contractors):,} contractors ({len(hvac_contractors)/total_contractors*100:.1f}%)
- **Solar/Inverters**: {len(solar_contractors)} contractors ({len(solar_contractors)/total_contractors*100:.1f}%)
- **HVAC + Solar**: {len(hvac_solar)} contractors (resimercial + multi-trade signal)

### Business Signals
**HVAC Contractors** ({len(hvac_contractors):,} total):
- Likely serve both residential AND commercial markets
- Self-perform mechanical trade (MEP+R capability)
- Often have O&M service contracts (recurring revenue model)

**Coperniq Value Prop for HVAC**:
- Unified monitoring for HVAC + generators + solar + batteries
- Single customer experience across product lines
- Maintenance contract support (alerts, diagnostics)

---

## 🗺️ Geographic Distribution

**Top 10 States** (SREC-focused targeting)

| State | Contractors | % of Total |
|-------|-------------|------------|
"""

    # Add top 10 states
    for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
        pct = count / total_contractors * 100
        md += f"| {state} | {count:,} | {pct:.1f}% |\n"

    md += f"""
**SREC State Coverage**: 15 states (CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
**ITC Deadline Urgency**: Residential Dec 2025, Commercial Q2 2026

---

## 🎯 Top 20 GOLD Prospects (Immediate Outreach)

**Characteristics of GOLD tier** ({tiers['GOLD']} total):
- Multi-OEM certifications (2-3 brands) AND/OR
- Strong resimercial signals (serve both markets) AND/OR
- Multi-trade capabilities (HVAC + Plumbing + Electrical)

**Top 20 by ICP Score**:

| Rank | Contractor | Score | OEMs | State | Key Signals |
|------|-----------|-------|------|-------|-------------|
"""

    # Add top 20 GOLD prospects
    for i, contractor in enumerate(gold_prospects_sorted[:20], 1):
        name = contractor['name'][:40]
        score = contractor['ICP_Score']
        oem_count = contractor['OEM_Count']
        oems = contractor.get('OEMs_Certified', '')[:30]
        state = contractor.get('state', 'N/A')

        # Identify key signals
        signals = []
        if int(oem_count) >= 3:
            signals.append("Triple-OEM")
        elif int(oem_count) == 2:
            signals.append("Dual-OEM")

        if contractor.get('has_hvac') == 'True':
            signals.append("HVAC")

        if 'commercial' in name.lower():
            signals.append("Commercial")

        if 'plumbing' in name.lower():
            signals.append("Plumbing")

        if 'electric' in name.lower():
            signals.append("Electrical")

        signal_str = ", ".join(signals) if signals else "Generator dealer"

        md += f"| {i} | {name} | {score} | {oem_count} | {state} | {signal_str} |\n"

    md += f"""

---

## 📈 Scoring Insights

### Top Performers
**Highest Score**: {gold_prospects_sorted[0]['ICP_Score']} ({gold_prospects_sorted[0]['name']})
**Average GOLD Score**: {sum(float(c['ICP_Score']) for c in gold_prospects) / len(gold_prospects):.1f}

### Scoring Dimensions (Year 1 GTM Alignment)
1. **Resimercial (35%)**: Residential + Commercial capability (scaling contractors $5-10M → $50-100M)
2. **Multi-OEM (25%)**: Managing 2-3+ platforms (core Coperniq pain point)
3. **MEP+R (25%)**: Multi-trade self-performance (platform power users, blue ocean market)
4. **O&M (15%)**: Operations & Maintenance contracts (Year 2 platform features maturing)

### Why No PLATINUM Tier?
OEM dealer networks don't explicitly showcase full service capabilities. Our data captures:
- ✅ Multi-OEM certifications (direct from dealer networks)
- ✅ HVAC capabilities (tagged from HVAC OEM sources)
- ⚠️ Partial multi-trade signals (names like "ABC Plumbing & Electric")
- ❌ Complete service portfolio (requires Apollo enrichment or manual research)

**GOLD tier (60-79) contractors are still premium prospects** with strong signals across 2-3 dimensions.

---

## 🚀 Next Steps

### Immediate (This Week)
1. ✅ **BDR Outreach**: Start with Top 50 GOLD prospects
   - Multi-OEM messaging for dual/triple-OEM contractors
   - HVAC resimercial messaging for HVAC contractors
2. ✅ **Google Ads**: Upload Top 200 for Customer Match campaigns
3. ✅ **Meta/Instagram**: Upload multi-OEM contractors for lookalike audiences

### Short-Term (Next 2 Weeks)
4. **Apollo Enrichment**: Enrich GOLD tier with employee count, revenue, LinkedIn
5. **Close CRM Import**: Bulk import with Smart Views by tier + OEM presence
6. **Email Sequences**: Build nurture campaigns for SILVER tier

### Medium-Term (This Quarter)
7. **Expand to 7 More OEMs**: Lennox, Rheem, Goodman (HVAC), Panasonic, LG, Daikin, Senville
8. **SREC State Expansion**: Add remaining SREC metros (CT, IL metros)
9. **Apollo/Clay Waterfall**: Advanced enrichment for commercial capability detection

---

## 📁 Deliverables

**Production Files** (in `output/`):
1. ✅ `icp_scored_contractors_final_{timestamp}.csv` - All {total_contractors:,} scored contractors
2. ✅ `top_200_prospects_final_{timestamp}.csv` - Top 200 by ICP score
3. ✅ `gold_tier_prospects_{timestamp}.csv` - {tiers['GOLD']} GOLD tier contractors (this file)
4. ✅ `silver_tier_prospects_{timestamp}.csv` - {tiers['SILVER']:,} SILVER tier contractors
5. ✅ `multi_oem_crossovers_expanded_{timestamp}.csv` - {len(multi_oem)} multi-OEM contractors
6. ✅ `grandmaster_list_expanded_{timestamp}.csv` - Raw deduplicated data

**GTM Materials** (Phase 7):
- Google Ads Customer Match list (GOLD + top SILVER)
- Meta/Instagram Custom Audience (multi-OEM focus)
- SEO strategy document (Coperniq website optimization)
- Personal BDR playbook (outreach sequences, objection handling)

---

## 🎓 Strategic Insights

### Why HVAC Expansion Matters
1. **Market Size**: HVAC contractors vastly outnumber pure generator/solar dealers
2. **Resimercial Signal**: HVAC contractors serve both residential AND commercial (ideal Coperniq profile)
3. **Multi-Trade**: HVAC companies often self-perform electrical, plumbing (platform power users)
4. **Integration Trend**: HVAC + Solar + Battery integration accelerating (energy efficiency + resilience)

### Coperniq's Unique Position
- **Only brand-agnostic monitoring platform** for microinverters + batteries + generators + HVAC
- **ITC Deadline Urgency**: Contractors need to close deals before Dec 2025 (residential) / Q2 2026 (commercial)
- **SREC State Focus**: Sustainable markets post-ITC (state incentives continue)

---

**Report End** | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Save markdown report
    report_file = f"output/executive_summary_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"✅ Saved executive summary: {report_file}")
    return report_file

def export_tier_csvs(contractors: List[Dict], timestamp: str):
    """Export tier-specific CSV files"""

    # Get fieldnames from first contractor
    if contractors:
        fieldnames = list(contractors[0].keys())
    else:
        return

    # Export GOLD tier
    gold = [c for c in contractors if c['ICP_Tier'] == 'GOLD']
    if gold:
        gold_file = f"output/gold_tier_prospects_{timestamp}.csv"
        with open(gold_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(gold)
        print(f"✅ Saved GOLD tier: {gold_file} ({len(gold)} contractors)")

    # Export SILVER tier
    silver = [c for c in contractors if c['ICP_Tier'] == 'SILVER']
    if silver:
        silver_file = f"output/silver_tier_prospects_{timestamp}.csv"
        with open(silver_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(silver)
        print(f"✅ Saved SILVER tier: {silver_file} ({len(silver)} contractors)")

    # Export BRONZE tier
    bronze = [c for c in contractors if c['ICP_Tier'] == 'BRONZE']
    if bronze:
        bronze_file = f"output/bronze_tier_prospects_{timestamp}.csv"
        with open(bronze_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bronze)
        print(f"✅ Saved BRONZE tier: {bronze_file} ({len(bronze)} contractors)")

def generate_multi_oem_analysis(contractors: List[Dict], timestamp: str):
    """Generate deep dive analysis on multi-OEM contractors"""

    multi_oem = [c for c in contractors if int(c.get('OEM_Count', 1)) >= 2]

    if not multi_oem:
        print("⚠️  No multi-OEM contractors found")
        return

    # Analyze OEM combinations
    oem_combos = defaultdict(int)
    for c in multi_oem:
        oems = c.get('OEMs_Certified', '')
        oem_combos[oems] += 1

    # Analyze by OEM count
    oem_count_dist = defaultdict(list)
    for c in multi_oem:
        count = int(c.get('OEM_Count', 1))
        oem_count_dist[count].append(c)

    md = f"""# Multi-OEM Contractor Deep Dive

**Generated**: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## 📊 Overview

**Total Multi-OEM Contractors**: {len(multi_oem)} ({len(multi_oem)/len(contractors)*100:.1f}% of database)

### Distribution by OEM Count

| OEM Count | Contractors | Avg ICP Score | Top Tier |
|-----------|-------------|---------------|----------|
"""

    for count in sorted(oem_count_dist.keys(), reverse=True):
        contractors_list = oem_count_dist[count]
        avg_score = sum(float(c['ICP_Score']) for c in contractors_list) / len(contractors_list)

        # Count tiers
        tier_counts = defaultdict(int)
        for c in contractors_list:
            tier_counts[c['ICP_Tier']] += 1
        top_tier = max(tier_counts, key=tier_counts.get)

        md += f"| {count} OEMs | {len(contractors_list)} | {avg_score:.1f} | {top_tier} ({tier_counts[top_tier]}) |\n"

    md += f"""

---

## 🎯 Most Common OEM Combinations

**Top 10 OEM Pairings**:

| Rank | OEM Combination | Count |
|------|-----------------|-------|
"""

    # Add top 10 combos
    for i, (oems, count) in enumerate(sorted(oem_combos.items(), key=lambda x: -x[1])[:10], 1):
        md += f"| {i} | {oems} | {count} |\n"

    md += f"""

---

## 💎 Triple-OEM Contractors (UNICORNS)

**Highest Value**: Managing 3+ separate monitoring platforms

"""

    # List all triple-OEM contractors
    triple = [c for c in multi_oem if int(c.get('OEM_Count', 1)) >= 3]

    if triple:
        md += f"**Total**: {len(triple)} contractors\n\n"
        md += "| Contractor | OEMs | Score | State | Tier |\n"
        md += "|------------|------|-------|-------|------|\n"

        for c in sorted(triple, key=lambda x: -float(x['ICP_Score'])):
            name = c['name'][:40]
            oems = c['OEMs_Certified']
            score = c['ICP_Score']
            state = c.get('state', 'N/A')
            tier = c['ICP_Tier']

            md += f"| {name} | {oems} | {score} | {state} | {tier} |\n"
    else:
        md += "*No triple-OEM contractors found*\n"

    md += f"""

---

## 🥇 Dual-OEM Contractors

**High Value**: Juggling 2 monitoring platforms (prime consolidation candidates)

**Total**: {len([c for c in multi_oem if int(c.get('OEM_Count', 1)) == 2])} contractors

**Top 20 by ICP Score**:

| Rank | Contractor | OEMs | Score | State | Tier |
|------|-----------|------|-------|-------|------|
"""

    # List top 20 dual-OEM
    dual = [c for c in multi_oem if int(c.get('OEM_Count', 1)) == 2]
    dual_sorted = sorted(dual, key=lambda x: -float(x['ICP_Score']))[:20]

    for i, c in enumerate(dual_sorted, 1):
        name = c['name'][:40]
        oems = c['OEMs_Certified']
        score = c['ICP_Score']
        state = c.get('state', 'N/A')
        tier = c['ICP_Tier']

        md += f"| {i} | {name} | {oems} | {score} | {state} | {tier} |\n"

    md += """

---

## 🎯 Outreach Messaging

### For Triple-OEM Contractors
> "You're managing Generac, Tesla, AND Enphase platforms separately? That's 3 different logins, 3 UIs, 3 customer experiences. Coperniq consolidates all monitoring into one unified dashboard - one login, one customer app, one support team."

**Pain Points to Emphasize**:
- Platform switching fatigue (3+ logins daily)
- Inconsistent customer experience across brands
- Training overhead (staff learning 3 different systems)
- Support complexity (which platform for which issue?)

### For Dual-OEM Contractors
> "Managing Generac and Enphase separately? Coperniq gives your customers one app for both systems - batteries, generators, solar, all in one place."

**Pain Points to Emphasize**:
- Customer confusion ("Which app do I use?")
- Duplicate support calls (platform-specific issues)
- Missed cross-sell opportunities (battery + generator bundling)

---

**Report End** | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Save report
    report_file = f"output/multi_oem_analysis_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"✅ Saved multi-OEM analysis: {report_file}")

def main():
    print("=" * 80)
    print("GENERATING EXECUTIVE PACKAGE - 10-OEM EXPANSION")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y%m%d")

    # Load ICP-scored contractors
    input_file = f"output/icp_scored_contractors_final_{timestamp}.csv"

    print(f"\n📂 Loading ICP-scored contractors: {input_file}")
    contractors = load_scored_contractors(input_file)
    print(f"   Loaded {len(contractors)} contractors")

    # Generate executive summary
    print(f"\n📊 Generating executive summary...")
    generate_executive_summary(contractors, timestamp)

    # Export tier-specific CSVs
    print(f"\n📁 Exporting tier-specific CSVs...")
    export_tier_csvs(contractors, timestamp)

    # Generate multi-OEM deep dive
    print(f"\n🎯 Generating multi-OEM analysis...")
    generate_multi_oem_analysis(contractors, timestamp)

    print(f"\n{'=' * 80}")
    print(f"EXECUTIVE PACKAGE COMPLETE")
    print(f"{'=' * 80}")
    print(f"\n✅ Deliverables created:")
    print(f"   • Executive Summary: output/executive_summary_{timestamp}.md")
    print(f"   • GOLD Tier CSV: output/gold_tier_prospects_{timestamp}.csv")
    print(f"   • SILVER Tier CSV: output/silver_tier_prospects_{timestamp}.csv")
    print(f"   • BRONZE Tier CSV: output/bronze_tier_prospects_{timestamp}.csv")
    print(f"   • Multi-OEM Analysis: output/multi_oem_analysis_{timestamp}.md")

    print(f"\n   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
