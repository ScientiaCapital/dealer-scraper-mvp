#!/usr/bin/env python3
"""
Combine NJ Scraper Results

Combines all successful NJ scrapes into a single master file.
"""

import csv
import pandas as pd
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
DATE_SUFFIX = datetime.now().strftime("%Y%m%d")

# Input files
ELECTRICAL_FILE = OUTPUT_DIR / "nj_electrical_contractors_20251119.csv"
HOME_IMPROVEMENT_FILE = OUTPUT_DIR / "nj_home_improvement_contractors_final_20251119.csv"

# Output file
COMBINED_FILE = OUTPUT_DIR / f"nj_mep_contractors_master_{DATE_SUFFIX}.csv"

print("="*80)
print("NJ CONTRACTOR DATA - COMBINING RESULTS")
print("="*80)

# Load files
contractors = []

# Electrical Contractors (full pagination - 821 active)
if ELECTRICAL_FILE.exists():
    with open(ELECTRICAL_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictWriter(f, fieldnames=None)
        electrical = list(csv.DictReader(f))
        contractors.extend(electrical)
        print(f"\n✅ Loaded {len(electrical)} Electrical Contractors")
else:
    print(f"\n⚠️  {ELECTRICAL_FILE.name} not found")

# Home Improvement Contractors (partial - 14 active)
if HOME_IMPROVEMENT_FILE.exists():
    with open(HOME_IMPROVEMENT_FILE, 'r', encoding='utf-8') as f:
        home_improvement = list(csv.DictReader(f))
        contractors.extend(home_improvement)
        print(f"✅ Loaded {len(home_improvement)} Home Improvement Contractors")
else:
    print(f"⚠️  {HOME_IMPROVEMENT_FILE.name} not found")

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"\n📊 Total contractors: {len(contractors)}")

# Breakdown by profession
profession_counts = {}
for c in contractors:
    prof = c['profession']
    profession_counts[prof] = profession_counts.get(prof, 0) + 1

print(f"\n📋 By Profession:")
for prof, count in sorted(profession_counts.items()):
    print(f"   - {prof}: {count:,}")

# Breakdown by status
status_counts = {}
for c in contractors:
    status = c['license_status']
    status_counts[status] = status_counts.get(status, 0) + 1

print(f"\n📋 By Status:")
for status, count in sorted(status_counts.items()):
    print(f"   - {status}: {count:,}")

# Save combined file
if contractors:
    with open(COMBINED_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=contractors[0].keys())
        writer.writeheader()
        writer.writerows(contractors)

    print(f"\n✅ Master file saved: {COMBINED_FILE.name}")
    print(f"📁 Location: {COMBINED_FILE}")
else:
    print(f"\n❌ No contractors to save")

# Notes
print(f"\n{'='*80}")
print("NOTES")
print(f"{'='*80}")
print("""
✅ COMPLETE:
   - Electrical Contractors: 821 active (42 pages, full pagination)
   - Home Improvement Contractors: 14 active (page 1 only, partial data)

⚠️  INCOMPLETE:
   - Master Plumbers: 0 results (profession exists but portal returns no data)
   - HVACR: 0 results (profession exists but portal returns no data)

💡 INSIGHTS:
   - NJ portal has timing issues with some professions (page navigation errors)
   - Master Plumbers/HVACR may require additional search criteria (county, name, etc.)
   - OR they may genuinely have 0 state-licensed contractors (possible)
   - Home Improvement has data but needs special timing handling

🎯 NEXT STEPS:
   1. Manual portal inspection to understand Master Plumbers/HVACR requirements
   2. Alternative data sources (county-level licensing, trade associations)
   3. Maryland scraper replication (simpler portal, different structure)
""")

print(f"{'='*80}\n")
