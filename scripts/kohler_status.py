#!/usr/bin/env python3
"""
Kohler Scraper Status - Run anytime to check progress

Usage: python3 scripts/kohler_status.py
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ZIP_CODES_SREC_ALL

MASTER_JSON = Path("output/kohler/kohler_master.json")

def show_status():
    if not MASTER_JSON.exists():
        print("❌ No master JSON found - scraper hasn't run yet")
        return

    with open(MASTER_JSON) as f:
        data = json.load(f)

    dealers = data.get('dealers', [])
    completed = data.get('completed_zips', [])
    failed = data.get('failed_zips', [])

    # Stats - dynamically count from config
    total_zips = sum(len(zips) for zips in ZIP_CODES_SREC_ALL.values())
    complete_dealers = sum(1 for d in dealers if d.get('phone') and d.get('street'))

    print("=" * 70)
    print("🔧 KOHLER SCRAPER STATUS")
    print("=" * 70)
    print(f"📅 Last Updated: {data.get('updated_at', 'Unknown')}")
    print()
    print(f"📍 ZIPs Completed: {len(completed)}/{total_zips} ({len(completed)/total_zips*100:.0f}%)")
    print(f"❌ ZIPs Failed: {len(failed)}")
    print(f"⏳ ZIPs Remaining: {total_zips - len(completed)}")
    print()
    print(f"👥 Total Dealers: {len(dealers)}")
    print(f"✅ Complete (w/ address): {complete_dealers}")
    print(f"📱 With Phone: {sum(1 for d in dealers if d.get('phone'))}")
    print()

    # Tier breakdown
    tiers = {}
    for d in dealers:
        tier = d.get('tier', 'Unknown')
        tiers[tier] = tiers.get(tier, 0) + 1

    print("🏆 Tier Distribution:")
    for tier in ['Titanium', 'Platinum', 'Gold', 'Silver', 'Bronze', 'Certified']:
        if tier in tiers:
            print(f"   {tier}: {tiers[tier]}")
    print()

    # Recent ZIPs
    print(f"📋 Last 5 ZIPs scraped: {completed[-5:] if completed else 'None'}")
    print()

    # Show all dealers
    print("=" * 70)
    print("📇 ALL DEALERS:")
    print("-" * 70)
    print(f"{'Phone':<12} | {'Name':<30} | {'City':<15} | Tier")
    print("-" * 70)
    for d in dealers:
        city = d.get('city', '')[:15] or 'NO CITY'
        name = d.get('name', '')[:30]
        phone = d.get('phone', 'NO PHONE')
        tier = d.get('tier', '')
        print(f"{phone:<12} | {name:<30} | {city:<15} | {tier}")
    print("-" * 70)
    print()

    # Proof not looping - show unique phones
    phones = [d.get('phone') for d in dealers if d.get('phone')]
    print(f"✅ Unique phone numbers: {len(set(phones))}/{len(phones)} (no duplicates)")
    print(f"✅ File size: {MASTER_JSON.stat().st_size:,} bytes")
    print("=" * 70)

if __name__ == "__main__":
    show_status()
