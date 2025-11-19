#!/usr/bin/env python3
"""
KPI Dashboard Generator

Generates comprehensive KPI tracking dashboard for dealer scraper project:
- Data acquisition costs (time, API calls, $ spent)
- Database growth metrics
- Lead quality metrics
- State coverage
- Cost per lead calculations

Usage:
    python3 scripts/generate_kpi_dashboard.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
STATE_LICENSES_DIR = OUTPUT_DIR / "state_licenses"

# Date suffix for outputs
DATE_SUFFIX = datetime.now().strftime("%Y%m%d")


def calculate_database_metrics():
    """Calculate total database size and growth metrics."""

    metrics = {
        'state': [],
        'total_records': [],
        'mep_energy_records': [],
        'source': [],
        'date_acquired': [],
        'data_quality': []
    }

    # California
    ca_file = STATE_LICENSES_DIR / "california" / "california_icp_master_20251101.csv"
    if ca_file.exists():
        ca_df = pd.read_csv(ca_file, low_memory=False)
        ca_df = ca_df[~ca_df['is_duplicate']]
        mep_count = ca_df[ca_df['has_electrical'] | ca_df['has_hvac'] | ca_df['has_solar']].shape[0]

        metrics['state'].append('California')
        metrics['total_records'].append(len(ca_df))
        metrics['mep_energy_records'].append(mep_count)
        metrics['source'].append('CSLB Bulk Download')
        metrics['date_acquired'].append('2025-11-01')
        metrics['data_quality'].append('Excellent (phone, tenure, multi-license)')

    # Texas
    tx_file = STATE_LICENSES_DIR / "texas" / "tx_tdlr_processed_20251031.csv"
    if tx_file.exists():
        tx_df = pd.read_csv(tx_file)
        mep_count = tx_df[
            tx_df['license_type'].str.contains('Electrical|Air Conditioning|HVAC|Solar', case=False, na=False)
        ].shape[0]

        metrics['state'].append('Texas')
        metrics['total_records'].append(len(tx_df))
        metrics['mep_energy_records'].append(mep_count)
        metrics['source'].append('TDLR Bulk Download')
        metrics['date_acquired'].append('2025-10-31')
        metrics['data_quality'].append('Good (phone, no tenure data)')

    # Florida
    fl_constr = STATE_LICENSES_DIR / "florida" / "fl_dbpr_fresh_download_20251119.csv"
    fl_elec = STATE_LICENSES_DIR / "florida" / "fl_electrical_contractors_20251119.csv"

    if fl_constr.exists() and fl_elec.exists():
        constr_df = pd.read_csv(fl_constr, header=None, low_memory=False)
        elec_df = pd.read_csv(fl_elec, header=None, low_memory=False)

        # MEP+Energy from construction file
        mep_constr = constr_df[constr_df[1].str.contains('AC|Mechanical|Solar', case=False, na=False)]

        total_fl = len(constr_df) + len(elec_df)
        mep_fl = len(mep_constr) + len(elec_df)

        metrics['state'].append('Florida')
        metrics['total_records'].append(total_fl)
        metrics['mep_energy_records'].append(mep_fl)
        metrics['source'].append('DBPR Bulk Download')
        metrics['date_acquired'].append('2025-11-19')
        metrics['data_quality'].append('Mixed (HVAC/Solar has phone, Electrical NO phone)')

    # NYC
    nyc_file = STATE_LICENSES_DIR / "new_york" / "nyc_dob_licenses_20251031.csv"
    if nyc_file.exists():
        nyc_df = pd.read_csv(nyc_file)
        # NYC is mostly general contractors, limited MEP signal

        metrics['state'].append('New York City')
        metrics['total_records'].append(len(nyc_df))
        metrics['mep_energy_records'].append(33)  # Inferred from names only
        metrics['source'].append('NYC DCA/DOB')
        metrics['date_acquired'].append('2025-10-31')
        metrics['data_quality'].append('Poor (no trade-specific licenses, name inference only)')

    return pd.DataFrame(metrics)


def calculate_lead_quality_metrics():
    """Calculate lead quality metrics from analysis outputs."""

    metrics = {}

    # Multi-trade contractors
    multi_trade_file = OUTPUT_DIR / f"mep_energy_contractors_{DATE_SUFFIX}.csv"
    if multi_trade_file.exists():
        mt_df = pd.read_csv(multi_trade_file)
        metrics['total_multi_trade'] = len(mt_df)
        metrics['unicorns'] = mt_df['has_all_three'].sum() if 'has_all_three' in mt_df.columns else 0
        metrics['elec_hvac_combo'] = mt_df['has_c10_c20'].sum() if 'has_c10_c20' in mt_df.columns else 0

    # Multi-state contractors
    multi_state_file = OUTPUT_DIR / f"multi_state_mep_{DATE_SUFFIX}.csv"
    if multi_state_file.exists():
        ms_df = pd.read_csv(multi_state_file)
        metrics['total_multi_state'] = len(ms_df)
        metrics['fl_tx_bicoastal'] = len(ms_df[ms_df['states_licensed'] == 'FL, TX'])

    # License + OEM overlap
    overlap_file = OUTPUT_DIR / f"license_oem_overlap_mep_{DATE_SUFFIX}.csv"
    if overlap_file.exists():
        overlap_df = pd.read_csv(overlap_file)
        metrics['total_license_oem_overlap'] = len(overlap_df)
        metrics['multi_trade_oem_overlap'] = overlap_df['is_multi_trade'].sum()

    # Established contractors
    established_file = OUTPUT_DIR / f"established_mep_contractors_{DATE_SUFFIX}.csv"
    if established_file.exists():
        est_df = pd.read_csv(established_file)
        metrics['total_established_10plus'] = len(est_df)

    # Top 500 prospects
    top_500_file = OUTPUT_DIR / f"top_500_mep_energy_prospects_{DATE_SUFFIX}.csv"
    if top_500_file.exists():
        top_df = pd.read_csv(top_500_file)
        metrics['top_500_avg_score'] = top_df['composite_score'].mean()
        metrics['top_500_min_score'] = top_df['composite_score'].min()
        metrics['top_500_max_score'] = top_df['composite_score'].max()
        metrics['top_500_multi_trade_pct'] = (top_df['is_multi_trade'].sum() / len(top_df) * 100)

    return metrics


def calculate_cost_metrics():
    """Calculate cost metrics for data acquisition."""

    costs = []

    # State license scraping costs
    costs.append({
        'activity': 'CA License Download',
        'method': 'Bulk CSV (direct link)',
        'time_hours': 0.0,  # Instant download
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 66_173,
        'date': '2025-11-01'
    })

    costs.append({
        'activity': 'TX License Download',
        'method': 'Bulk CSV (direct link)',
        'time_hours': 0.0,
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 35_440,
        'date': '2025-10-31'
    })

    costs.append({
        'activity': 'FL License Download',
        'method': 'Bulk CSV (direct link)',
        'time_hours': 0.0,
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 32_001,
        'date': '2025-11-19'
    })

    costs.append({
        'activity': 'NYC License Download',
        'method': 'Bulk CSV (direct link)',
        'time_hours': 0.0,
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 11_791,
        'date': '2025-10-31'
    })

    # OEM scraping costs (from previous work)
    costs.append({
        'activity': '18 OEM Dealer Scraping',
        'method': 'Playwright (local) - 140 ZIPs × 18 OEMs',
        'time_hours': 4.0,
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 8_277,
        'date': '2025-10-29'
    })

    # Analysis costs
    costs.append({
        'activity': '4-State MEP Analysis',
        'method': 'Python/pandas (local)',
        'time_hours': 0.5,
        'api_calls': 0,
        'cost_usd': 0.0,
        'records_acquired': 145_405,
        'date': '2025-11-19'
    })

    cost_df = pd.DataFrame(costs)

    # Calculate totals
    totals = {
        'total_time_hours': cost_df['time_hours'].sum(),
        'total_api_calls': cost_df['api_calls'].sum(),
        'total_cost_usd': cost_df['cost_usd'].sum(),
        'total_records': cost_df['records_acquired'].sum(),
        'cost_per_lead': cost_df['cost_usd'].sum() / cost_df['records_acquired'].sum() if cost_df['records_acquired'].sum() > 0 else 0,
        'records_per_hour': cost_df['records_acquired'].sum() / cost_df['time_hours'].sum() if cost_df['time_hours'].sum() > 0 else 0
    }

    return cost_df, totals


def generate_markdown_dashboard(db_metrics, lead_metrics, cost_df, cost_totals):
    """Generate markdown-formatted KPI dashboard."""

    md = f"""# Coperniq Dealer Scraper - KPI Dashboard

**Generated**: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

---

## 📊 Database Metrics

### Total Database Size

| State | Total Records | MEP+Energy | Source | Date Acquired | Data Quality |
|-------|--------------|------------|--------|---------------|--------------|
"""

    for _, row in db_metrics.iterrows():
        md += f"| {row['state']} | {row['total_records']:,} | {row['mep_energy_records']:,} | {row['source']} | {row['date_acquired']} | {row['data_quality']} |\n"

    total_records = db_metrics['total_records'].sum()
    total_mep = db_metrics['mep_energy_records'].sum()

    md += f"| **TOTAL** | **{total_records:,}** | **{total_mep:,}** | 4 states | - | - |\n\n"

    md += f"""
### Database Growth

- **Total license records**: {total_records:,}
- **MEP+Energy contractors**: {total_mep:,} ({total_mep / total_records * 100:.1f}%)
- **OEM dealer records**: 8,277
- **Combined unique contractors**: {total_records:,} (assuming minimal license-OEM overlap)

---

## 🎯 Lead Quality Metrics

### High-Value Contractor Profiles

| Profile | Count | Business Value |
|---------|-------|----------------|
| **Multi-trade** (Elec + HVAC + Solar) | {lead_metrics.get('total_multi_trade', 0):,} | ⭐⭐⭐ Integrated energy systems capability |
| **UNICORNS** (all 3 trades) | {lead_metrics.get('unicorns', 0):,} | 🦄 Highest ICP scores |
| **Multi-state licensed** | {lead_metrics.get('total_multi_state', 0):,} | ⭐⭐ Geographic expansion capability |
| **License + OEM overlap** | {lead_metrics.get('total_license_oem_overlap', 0):,} | ⭐⭐⭐ Dual verification |
| **Established (10+ years)** | {lead_metrics.get('total_established_10plus', 0):,} | ⭐⭐ Business stability + O&M |

### Top 500 Prospects

- **Average composite score**: {lead_metrics.get('top_500_avg_score', 0):.1f} / 200
- **Score range**: {lead_metrics.get('top_500_min_score', 0):.0f} - {lead_metrics.get('top_500_max_score', 0):.0f}
- **Multi-trade concentration**: {lead_metrics.get('top_500_multi_trade_pct', 0):.0f}%

---

## 💰 Cost Metrics

### Data Acquisition Costs

| Activity | Method | Time (hrs) | API Calls | Cost ($) | Records | Date |
|----------|--------|-----------|-----------|----------|---------|------|
"""

    for _, row in cost_df.iterrows():
        md += f"| {row['activity']} | {row['method']} | {row['time_hours']:.1f} | {row['api_calls']:,} | ${row['cost_usd']:.2f} | {row['records_acquired']:,} | {row['date']} |\n"

    md += f"""| **TOTAL** | - | **{cost_totals['total_time_hours']:.1f}** | **{cost_totals['total_api_calls']:,}** | **${cost_totals['total_cost_usd']:.2f}** | **{cost_totals['total_records']:,}** | - |

### Cost Efficiency

- **Cost per lead**: ${cost_totals['cost_per_lead']:.4f}
- **Records per hour**: {cost_totals['records_per_hour']:,.0f}
- **Total time invested**: {cost_totals['total_time_hours']:.1f} hours

### Key Insight

✅ **All 4 states have FREE bulk downloads** (no API costs, no scraping needed)
- Zero acquisition cost per lead
- Instant download (no rate limiting)
- High data quality (phone numbers, tenure, multi-license tracking)

---

## 🗺️ State Coverage

### Current Coverage (4 states)

- ✅ **California**: 66,173 contractors (multi-license tracking, 10+ year tenure)
- ✅ **Texas**: 35,440 contractors (phone numbers, no tenure)
- ✅ **Florida**: 32,001 contractors (HVAC/Solar with phone, Electrical without phone)
- ✅ **New York City**: 11,791 contractors (limited MEP signal)

### Expansion Opportunities

**Tier 1 - Bulk Download (FREE)**:
- No additional states identified (only CA, TX, FL have bulk CSV)

**Tier 2 - API Access**:
- Massachusetts (8K contractors, requires API key)
- Cost: FREE (public records)

**Tier 3 - Scraping Required**:
- Pennsylvania (15K contractors, municipal-level only)
- New Jersey (unknown volume)
- Maryland (unknown volume)
- Cost: Playwright scraping (~1-2 days per state)

---

## 📈 Next Steps

### Immediate Actions (This Week)

1. **Launch outreach to Top 500**
   - 490 CA multi-trade contractors (greenfield adoption)
   - 10 FL HVAC+Solar contractors

2. **Apollo/Clay enrichment**
   - Enrich Top 500 with employee count, revenue, LinkedIn
   - Cost estimate: $100-$200 for 500 contacts

3. **Generate GTM deliverables**
   - Google Ads Customer Match (Top 500)
   - Meta Custom Audience (1,612 multi-trade)
   - BDR playbook with objection handling

### Short-Term Expansion (Next 2 Weeks)

4. **NJ/MD scrapers** (Playwright)
   - New Jersey: ~unknown volume
   - Maryland: ~unknown volume
   - Time estimate: 2-3 days

5. **Massachusetts API integration**
   - Request API key from state board
   - Build REST API integration
   - Time estimate: 4-8 hours

---

**Dashboard Updated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    return md


def main():
    print("=" * 80)
    print("GENERATING KPI DASHBOARD")
    print("=" * 80)

    # Calculate metrics
    print("\n📊 Calculating database metrics...")
    db_metrics = calculate_database_metrics()

    print("🎯 Calculating lead quality metrics...")
    lead_metrics = calculate_lead_quality_metrics()

    print("💰 Calculating cost metrics...")
    cost_df, cost_totals = calculate_cost_metrics()

    # Generate outputs
    print("\n📄 Generating dashboard outputs...")

    # CSV outputs
    db_metrics.to_csv(OUTPUT_DIR / f"kpi_database_metrics_{DATE_SUFFIX}.csv", index=False)
    cost_df.to_csv(OUTPUT_DIR / f"kpi_cost_breakdown_{DATE_SUFFIX}.csv", index=False)

    # Markdown dashboard
    markdown = generate_markdown_dashboard(db_metrics, lead_metrics, cost_df, cost_totals)
    dashboard_file = OUTPUT_DIR / f"KPI_DASHBOARD_{DATE_SUFFIX}.md"
    with open(dashboard_file, 'w') as f:
        f.write(markdown)

    print(f"   ✅ Database metrics: kpi_database_metrics_{DATE_SUFFIX}.csv")
    print(f"   ✅ Cost breakdown: kpi_cost_breakdown_{DATE_SUFFIX}.csv")
    print(f"   ✅ KPI Dashboard: KPI_DASHBOARD_{DATE_SUFFIX}.md")

    # Print summary
    print("\n" + "=" * 80)
    print("KPI DASHBOARD SUMMARY")
    print("=" * 80)

    print(f"\n📊 Database:")
    print(f"   - Total records: {db_metrics['total_records'].sum():,}")
    print(f"   - MEP+Energy: {db_metrics['mep_energy_records'].sum():,}")

    print(f"\n🎯 Lead Quality:")
    print(f"   - Multi-trade: {lead_metrics.get('total_multi_trade', 0):,}")
    print(f"   - Multi-state: {lead_metrics.get('total_multi_state', 0):,}")
    print(f"   - License + OEM: {lead_metrics.get('total_license_oem_overlap', 0):,}")

    print(f"\n💰 Costs:")
    print(f"   - Total time: {cost_totals['total_time_hours']:.1f} hours")
    print(f"   - Total cost: ${cost_totals['total_cost_usd']:.2f}")
    print(f"   - Cost per lead: ${cost_totals['cost_per_lead']:.4f}")

    print(f"\n✅ All outputs saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
