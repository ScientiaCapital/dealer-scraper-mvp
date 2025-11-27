#!/usr/bin/env python3
"""
Observability Dashboard Generator

Generates a markdown dashboard and JSON export from pipeline database
for local viewing and Vercel deployment.

Usage:
    python scripts/generate_observability_dashboard.py
    python scripts/generate_observability_dashboard.py --db-path output/master/pipeline.db

Outputs:
    - output/observability_dashboard_YYYYMMDD.md (local markdown)
    - output/dashboard_data.json (for Vercel app)
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_roi_metrics(conn: sqlite3.Connection) -> dict:
    """Get ROI and funnel metrics."""
    cursor = conn.cursor()

    # Get ROI summary
    try:
        cursor.execute("SELECT * FROM v_pipeline_roi")
        roi_row = cursor.fetchone()
        roi = dict(roi_row) if roi_row else {}
    except Exception:
        roi = {}

    # Get conversion rates
    try:
        cursor.execute("SELECT * FROM v_conversion_rates")
        conversions = [dict(r) for r in cursor.fetchall()]
    except Exception:
        conversions = []

    # Get monthly costs
    try:
        cursor.execute("SELECT * FROM v_monthly_costs")
        monthly_costs = [dict(r) for r in cursor.fetchall()]
    except Exception:
        monthly_costs = []

    # Get funnel metrics
    try:
        cursor.execute("SELECT * FROM v_funnel_metrics")
        funnel = [dict(r) for r in cursor.fetchall()]
    except Exception:
        funnel = []

    return {
        "total_investment_usd": roi.get('total_investment_usd', 0) or 0,
        "infrastructure_cost": roi.get('infrastructure_cost', 0) or 0,
        "enrichment_cost": roi.get('enrichment_cost', 0) or 0,
        "outreach_cost": roi.get('outreach_cost', 0) or 0,
        "labor_cost": roi.get('labor_cost', 0) or 0,
        "cost_per_lead_usd": roi.get('cost_per_lead_usd', 0) or 0,
        "pipeline_value_usd": roi.get('pipeline_value_usd', 0) or 0,
        "closed_won_count": roi.get('closed_won_count', 0) or 0,
        "closed_won_value_usd": roi.get('closed_won_value_usd', 0) or 0,
        "roi_percentage": roi.get('roi_percentage'),
        "conversion_rates": conversions,
        "monthly_costs": monthly_costs,
        "funnel_stages": funnel,
    }


def get_pipeline_health(conn: sqlite3.Connection) -> dict:
    """Get overall pipeline health metrics."""
    cursor = conn.cursor()

    # Get contractor counts
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN primary_email IS NOT NULL AND primary_email != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN primary_phone IS NOT NULL AND primary_phone != '' THEN 1 ELSE 0 END) as with_phone
        FROM contractors
        WHERE is_deleted = 0 OR is_deleted IS NULL
    """)
    row = cursor.fetchone()

    # Get multi-license counts
    cursor.execute("""
        SELECT COUNT(*) FROM v_multi_license
    """)
    multi_license = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM v_unicorns
    """)
    unicorns = cursor.fetchone()[0]

    # Get multi-OEM counts
    cursor.execute("""
        SELECT COUNT(*) FROM v_multi_oem
    """)
    multi_oem = cursor.fetchone()[0]

    # Get scraper health
    cursor.execute("""
        SELECT
            SUM(CASE WHEN status = 'WORKING' THEN 1 ELSE 0 END) as working,
            SUM(CASE WHEN status = 'BROKEN' THEN 1 ELSE 0 END) as broken,
            SUM(CASE WHEN status = 'UNTESTED' THEN 1 ELSE 0 END) as untested,
            COUNT(*) as total
        FROM scraper_registry
    """)
    scrapers = cursor.fetchone()

    return {
        "total_contractors": row['total'],
        "with_email": row['with_email'],
        "with_phone": row['with_phone'],
        "email_rate": round(row['with_email'] / row['total'] * 100, 1) if row['total'] else 0,
        "phone_rate": round(row['with_phone'] / row['total'] * 100, 1) if row['total'] else 0,
        "multi_license_count": multi_license,
        "unicorn_count": unicorns,
        "multi_oem_count": multi_oem,
        "scrapers_working": scrapers['working'] or 0,
        "scrapers_broken": scrapers['broken'] or 0,
        "scrapers_untested": scrapers['untested'] or 0,
        "scrapers_total": scrapers['total'] or 0,
        "generated_at": datetime.now().isoformat()
    }


def get_scraper_health(conn: sqlite3.Connection) -> list:
    """Get scraper health details."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(display_name, scraper_name) as scraper_name,
            scraper_type,
            status,
            fix_difficulty,
            total_records_lifetime,
            last_successful_run,
            source_url,
            notes
        FROM scraper_registry
        ORDER BY scraper_type, status DESC, scraper_name
    """)

    return [dict(row) for row in cursor.fetchall()]


def get_data_inventory(conn: sqlite3.Connection) -> list:
    """Get data inventory by source."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            source_name,
            source_type,
            record_count,
            with_email_count,
            with_phone_count,
            quality_score,
            last_updated,
            notes
        FROM data_inventory
        ORDER BY record_count DESC
    """)

    return [dict(row) for row in cursor.fetchall()]


def get_state_coverage(conn: sqlite3.Connection) -> list:
    """Get coverage by state."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            state,
            COUNT(*) as contractor_count,
            SUM(CASE WHEN primary_email IS NOT NULL AND primary_email != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN primary_phone IS NOT NULL AND primary_phone != '' THEN 1 ELSE 0 END) as with_phone
        FROM contractors
        WHERE (is_deleted = 0 OR is_deleted IS NULL) AND state IS NOT NULL
        GROUP BY state
        ORDER BY contractor_count DESC
        LIMIT 20
    """)

    return [dict(row) for row in cursor.fetchall()]


def get_oem_coverage(conn: sqlite3.Connection) -> list:
    """Get OEM certification counts."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            oem_name,
            COUNT(DISTINCT contractor_id) as contractor_count
        FROM oem_certifications
        GROUP BY oem_name
        ORDER BY contractor_count DESC
    """)

    return [dict(row) for row in cursor.fetchall()]


def get_recent_imports(conn: sqlite3.Connection) -> list:
    """Get recent file imports."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            file_name,
            source_type,
            import_status,
            records_created,
            records_merged,
            import_completed_at
        FROM file_imports
        ORDER BY import_started_at DESC
        LIMIT 10
    """)

    return [dict(row) for row in cursor.fetchall()]


def generate_markdown_dashboard(data: dict, output_path: Path):
    """Generate markdown dashboard file."""
    health = data['pipeline_health']
    scrapers = data['scraper_health']
    inventory = data['data_inventory']
    states = data['state_coverage']
    oems = data['oem_coverage']

    md = []
    md.append(f"# Coperniq Pipeline Dashboard")
    md.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"\n**Database**: pipeline.db")
    md.append("\n---\n")

    # Executive Summary
    md.append("## 📊 Executive Summary\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| **Total Contractors** | {health['total_contractors']:,} |")
    md.append(f"| With Email | {health['with_email']:,} ({health['email_rate']}%) |")
    md.append(f"| With Phone | {health['with_phone']:,} ({health['phone_rate']}%) |")
    md.append(f"| Multi-License (2+ trades) | {health['multi_license_count']:,} |")
    md.append(f"| Unicorns (3+ trades) | {health['unicorn_count']:,} |")
    md.append(f"| Multi-OEM (2+ brands) | {health['multi_oem_count']:,} |")
    md.append("")

    # Scraper Health
    md.append("\n## 🔧 Scraper Health\n")

    working = health['scrapers_working']
    broken = health['scrapers_broken']
    untested = health['scrapers_untested']
    total = health['scrapers_total']

    md.append(f"**Status**: 🟢 {working} working | 🔴 {broken} broken | ⚪ {untested} untested | Total: {total}\n")

    # Group by type
    by_type = {}
    for s in scrapers:
        t = s['scraper_type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(s)

    for scraper_type, items in by_type.items():
        md.append(f"\n### {scraper_type} Scrapers ({len(items)})\n")
        md.append("| Name | Status | Records | Last Run | Notes |")
        md.append("|------|--------|---------|----------|-------|")

        for s in items:
            status_icon = "🟢" if s['status'] == 'WORKING' else "🔴" if s['status'] == 'BROKEN' else "⚪"
            records = f"{s['total_records_lifetime']:,}" if s['total_records_lifetime'] else "-"
            last_run = s['last_successful_run'][:10] if s['last_successful_run'] else "Never"
            notes = (s['notes'] or "")[:40]
            md.append(f"| {s['scraper_name']} | {status_icon} {s['status']} | {records} | {last_run} | {notes} |")

    # Data Inventory
    md.append("\n## 📦 Data Inventory\n")
    md.append("| Source | Type | Records | Email | Phone | Quality |")
    md.append("|--------|------|---------|-------|-------|---------|")

    for item in inventory[:20]:  # Top 20
        email = f"{item['with_email_count']:,}" if item['with_email_count'] else "-"
        phone = f"{item['with_phone_count']:,}" if item['with_phone_count'] else "-"
        quality = f"{item['quality_score']}%" if item['quality_score'] else "-"
        md.append(f"| {item['source_name']} | {item['source_type']} | {item['record_count']:,} | {email} | {phone} | {quality} |")

    # State Coverage
    md.append("\n## 🗺️ State Coverage (Top 20)\n")
    md.append("| State | Contractors | With Email | With Phone |")
    md.append("|-------|-------------|------------|------------|")

    for state in states:
        md.append(f"| {state['state']} | {state['contractor_count']:,} | {state['with_email']:,} | {state['with_phone']:,} |")

    # OEM Coverage
    md.append("\n## 🏭 OEM Certifications\n")
    md.append("| OEM | Contractors |")
    md.append("|-----|-------------|")

    for oem in oems:
        md.append(f"| {oem['oem_name']} | {oem['contractor_count']:,} |")

    # Footer
    md.append("\n---")
    md.append(f"\n*Dashboard generated by `scripts/generate_observability_dashboard.py`*")

    # Write file
    with open(output_path, 'w') as f:
        f.write('\n'.join(md))

    return output_path


def generate_json_export(data: dict, output_path: Path):
    """Generate JSON export for Vercel dashboard."""
    # Serialize datetime objects
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=serialize)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate observability dashboard")
    parser.add_argument("--db-path", default="output/master/pipeline.db", help="Database path")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    print("📊 Generating Observability Dashboard")
    print("=" * 60)

    # Check database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found: {args.db_path}")
        sys.exit(1)

    print(f"Database: {args.db_path}")

    # Connect
    conn = get_db_connection(args.db_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Gather all data
        print("\n📥 Gathering data...")

        data = {
            "pipeline_health": get_pipeline_health(conn),
            "scraper_health": get_scraper_health(conn),
            "data_inventory": get_data_inventory(conn),
            "state_coverage": get_state_coverage(conn),
            "oem_coverage": get_oem_coverage(conn),
            "recent_imports": get_recent_imports(conn),
            "roi_metrics": get_roi_metrics(conn),
        }

        print(f"  ✓ Pipeline health: {data['pipeline_health']['total_contractors']:,} contractors")
        print(f"  ✓ Scraper health: {len(data['scraper_health'])} scrapers")
        print(f"  ✓ Data inventory: {len(data['data_inventory'])} sources")
        print(f"  ✓ State coverage: {len(data['state_coverage'])} states")
        print(f"  ✓ OEM coverage: {len(data['oem_coverage'])} OEMs")
        print(f"  ✓ ROI metrics: ${data['roi_metrics']['total_investment_usd']:.2f} invested, ${data['roi_metrics']['cost_per_lead_usd']:.4f}/lead")

        # Generate outputs
        print("\n📝 Generating outputs...")

        # Markdown dashboard
        today = datetime.now().strftime('%Y%m%d')
        md_path = output_dir / f"observability_dashboard_{today}.md"
        generate_markdown_dashboard(data, md_path)
        print(f"  ✓ Markdown: {md_path}")

        # JSON export for Vercel
        json_path = output_dir / "dashboard_data.json"
        generate_json_export(data, json_path)
        print(f"  ✓ JSON: {json_path}")

        # Print summary
        health = data['pipeline_health']
        print("\n" + "=" * 60)
        print("DASHBOARD SUMMARY")
        print("=" * 60)
        print(f"📊 Contractors: {health['total_contractors']:,}")
        print(f"📧 With Email: {health['with_email']:,} ({health['email_rate']}%)")
        print(f"📞 With Phone: {health['with_phone']:,} ({health['phone_rate']}%)")
        print(f"🏆 Multi-License: {health['multi_license_count']:,}")
        print(f"🦄 Unicorns: {health['unicorn_count']:,}")
        print(f"🤝 Multi-OEM: {health['multi_oem_count']:,}")
        print(f"\n🔧 Scrapers: 🟢 {health['scrapers_working']} | 🔴 {health['scrapers_broken']} | ⚪ {health['scrapers_untested']}")
        print("=" * 60)

        print(f"\n✅ Dashboard generated successfully!")
        print(f"\nNext steps:")
        print(f"  1. View markdown: cat {md_path}")
        print(f"  2. Deploy JSON to Vercel: copy {json_path} to dashboard/public/data/")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
