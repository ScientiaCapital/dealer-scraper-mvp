#!/usr/bin/env python3
"""
Cost Tracking Utility

Track costs for the lead generation pipeline for ROI calculation.
Supports adding costs, viewing reports, and seeding initial data.

Usage:
    # Add a cost
    python3 scripts/track_costs.py add --category infrastructure --amount 50.00 --desc "RunPod GPU hours"

    # Seed initial costs (one-time setup)
    python3 scripts/track_costs.py seed

    # View monthly report
    python3 scripts/track_costs.py report

    # View ROI summary
    python3 scripts/track_costs.py roi
"""

import sqlite3
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "output" / "master" / "pipeline.db"


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_cost(
    category: str,
    amount_usd: float,
    description: str,
    subcategory: Optional[str] = None,
    billable_units: Optional[int] = None,
    cost_date: Optional[str] = None,
    notes: Optional[str] = None
):
    """Add a cost entry to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    amount_cents = int(amount_usd * 100)
    cost_date = cost_date or date.today().isoformat()
    cost_per_unit = amount_cents // billable_units if billable_units else None

    cursor.execute("""
        INSERT INTO cost_tracking
        (cost_date, category, subcategory, amount_cents, description,
         billable_units, cost_per_unit_cents, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cost_date, category, subcategory, amount_cents, description,
        billable_units, cost_per_unit, notes
    ))

    conn.commit()
    cost_id = cursor.lastrowid
    conn.close()

    print(f"✅ Added cost #{cost_id}: ${amount_usd:.2f} ({category})")
    return cost_id


def seed_initial_costs():
    """Seed initial costs from project history."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM cost_tracking")
    if cursor.fetchone()[0] > 0:
        print("⚠️  Costs already exist. Use 'add' command to add more.")
        conn.close()
        return

    # Initial costs based on project history
    initial_costs = [
        # Infrastructure costs
        ("2025-10-01", "infrastructure", "runpod", 2000, "RunPod GPU hours - October (scraper development)", 500),
        ("2025-10-15", "infrastructure", "browserbase", 500, "Browserbase credits - bot detection bypass", 200),
        ("2025-11-01", "infrastructure", "runpod", 3000, "RunPod GPU hours - November (production scraping)", 800),
        ("2025-11-15", "infrastructure", "vercel", 0, "Vercel dashboard hosting (free tier)", None),

        # Scraping costs (calculated by time invested)
        ("2025-10-01", "scraping", "oem_scrapers", 0, "18 OEM scraper development - labor value", 18),  # OEMs
        ("2025-11-01", "scraping", "state_license", 0, "State license scrapers (FL, CA, TX, NYC) - labor value", 4),  # States

        # Labor estimates (your time as BDR/dev - conservatively valued)
        ("2025-10-01", "labor", "development", 20000, "October development hours (~40 hrs @ $50/hr)", 40),
        ("2025-11-01", "labor", "development", 30000, "November development hours (~60 hrs @ $50/hr)", 60),

        # Future enrichment costs (placeholders)
        # ("2025-11-15", "enrichment", "apollo", 0, "Apollo credits - not yet purchased", None),
        # ("2025-11-15", "enrichment", "hunter", 0, "Hunter credits - not yet purchased", None),

        # Outreach costs (none yet)
        # ("2025-11-20", "outreach", "sendgrid", 0, "SendGrid - not yet set up", None),
    ]

    for cost_date, category, subcategory, amount_cents, description, units in initial_costs:
        cost_per_unit = amount_cents // units if units else None
        cursor.execute("""
            INSERT INTO cost_tracking
            (cost_date, category, subcategory, amount_cents, description,
             billable_units, cost_per_unit_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cost_date, category, subcategory, amount_cents, description, units, cost_per_unit))

    conn.commit()
    conn.close()

    print("✅ Seeded initial cost data:")
    print("   - Infrastructure: $55.00 (RunPod, Browserbase)")
    print("   - Labor: $500.00 (100 hrs @ $50/hr)")
    print("   - Total: $555.00")
    print("\nAdjust these values with 'python3 scripts/track_costs.py add' as needed.")


def show_monthly_report():
    """Show monthly cost breakdown."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM v_monthly_costs")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("📊 No costs recorded yet. Run 'seed' command first.")
        return

    print("\n" + "=" * 60)
    print("MONTHLY COST REPORT")
    print("=" * 60)

    current_month = None
    for row in rows:
        if row['month'] != current_month:
            current_month = row['month']
            print(f"\n📅 {current_month}")
            print("-" * 40)

        units_str = f"{row['total_units']:,} units" if row['total_units'] else ""
        per_unit = f"(${row['avg_cost_per_unit']:.4f}/unit)" if row['avg_cost_per_unit'] else ""

        print(f"   {row['category']:15} ${row['total_cost_usd']:>8.2f}  {units_str} {per_unit}")

    # Total
    cursor = get_db_connection().cursor()
    cursor.execute("SELECT SUM(amount_cents) / 100.0 as total FROM cost_tracking")
    total = cursor.fetchone()['total'] or 0

    print("\n" + "-" * 40)
    print(f"   {'TOTAL':15} ${total:>8.2f}")
    print("=" * 60)


def show_roi_summary():
    """Show the ROI summary (money slide)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM v_pipeline_roi")
    roi = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM v_conversion_rates")
    conversions = [dict(r) for r in cursor.fetchall()]

    conn.close()

    print("\n" + "=" * 70)
    print("💰 PIPELINE ROI SUMMARY")
    print("=" * 70)

    print("\n📈 INVESTMENT")
    print("-" * 40)
    print(f"   Total Investment:     ${roi['total_investment_usd'] or 0:>10,.2f}")
    print(f"   └─ Infrastructure:    ${roi['infrastructure_cost'] or 0:>10,.2f}")
    print(f"   └─ Enrichment:        ${roi['enrichment_cost'] or 0:>10,.2f}")
    print(f"   └─ Outreach:          ${roi['outreach_cost'] or 0:>10,.2f}")
    print(f"   └─ Labor:             ${roi['labor_cost'] or 0:>10,.2f}")

    print("\n📊 PIPELINE")
    print("-" * 40)
    print(f"   Total Leads:          {roi['total_leads'] or 0:>10,}")
    print(f"   Enriched:             {roi['enriched_leads'] or 0:>10,}")
    print(f"   Active (contacted):   {roi['active_leads'] or 0:>10,}")
    print(f"   Open Opportunities:   {roi['open_opportunities'] or 0:>10,}")
    print(f"   Pipeline Value:       ${roi['pipeline_value_usd'] or 0:>10,.2f}")

    print("\n🏆 RESULTS")
    print("-" * 40)
    print(f"   Closed Won:           {roi['closed_won_count'] or 0:>10,}")
    print(f"   Closed Won Value:     ${roi['closed_won_value_usd'] or 0:>10,.2f}")
    print(f"   Closed Lost:          {roi['closed_lost_count'] or 0:>10,}")

    print("\n📏 KEY METRICS")
    print("-" * 40)
    cost_per_lead = roi['cost_per_lead_usd']
    print(f"   Cost per Lead:        ${cost_per_lead or 0:>10,.4f}")
    if roi['closed_won_count'] and roi['closed_won_count'] > 0:
        print(f"   Cost per Closed Deal: ${roi['cost_per_closed_deal_usd'] or 0:>10,.2f}")
        print(f"   ROI:                  {roi['roi_percentage'] or 0:>10,.1f}%")
    else:
        print(f"   Cost per Closed Deal: {'N/A':>10} (no deals yet)")
        print(f"   ROI:                  {'N/A':>10} (no deals yet)")

    print("\n🔄 CONVERSION RATES")
    print("-" * 40)
    for conv in conversions:
        rate = conv['conversion_rate_pct']
        rate_str = f"{rate:.1f}%" if rate else "N/A"
        print(f"   {conv['conversion']:20} {rate_str:>8}  ({conv['numerator'] or 0}/{conv['denominator'] or 0})")

    print("=" * 70)

    # Calculate lead value
    if roi['total_leads'] and roi['total_leads'] > 0 and cost_per_lead:
        leads_per_dollar = 1 / cost_per_lead if cost_per_lead > 0 else 0
        print(f"\n💡 You're generating {leads_per_dollar:,.0f} leads per $1 invested")

        # Compare to industry benchmarks
        if cost_per_lead < 0.10:
            print("   🏆 This is EXCEPTIONAL (industry avg: $5-50/lead)")
        elif cost_per_lead < 1.00:
            print("   ✅ This is EXCELLENT (industry avg: $5-50/lead)")
        elif cost_per_lead < 5.00:
            print("   👍 This is GOOD (industry avg: $5-50/lead)")

    print()


def main():
    parser = argparse.ArgumentParser(description="Track pipeline costs for ROI calculation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a cost entry")
    add_parser.add_argument("--category", required=True,
                           choices=["infrastructure", "scraping", "enrichment", "outreach", "labor"],
                           help="Cost category")
    add_parser.add_argument("--amount", type=float, required=True, help="Amount in USD")
    add_parser.add_argument("--desc", required=True, help="Description")
    add_parser.add_argument("--subcategory", help="Subcategory (e.g., runpod, apollo)")
    add_parser.add_argument("--units", type=int, help="Number of billable units")
    add_parser.add_argument("--date", help="Cost date (YYYY-MM-DD)")
    add_parser.add_argument("--notes", help="Additional notes")

    # Seed command
    subparsers.add_parser("seed", help="Seed initial cost data")

    # Report command
    subparsers.add_parser("report", help="Show monthly cost report")

    # ROI command
    subparsers.add_parser("roi", help="Show ROI summary")

    args = parser.parse_args()

    if args.command == "add":
        add_cost(
            category=args.category,
            amount_usd=args.amount,
            description=args.desc,
            subcategory=args.subcategory,
            billable_units=args.units,
            cost_date=args.date,
            notes=args.notes
        )
    elif args.command == "seed":
        seed_initial_costs()
    elif args.command == "report":
        show_monthly_report()
    elif args.command == "roi":
        show_roi_summary()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
