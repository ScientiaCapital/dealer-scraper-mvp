#!/usr/bin/env python3
"""
Rebuild progress tracker from actual CSV data
Single source of truth: what's in the CSV
"""
import csv
import json
from pathlib import Path

# All 40 target ZIPs
ALL_ZIPS = [
    # California
    "94102", "94301", "94022", "94024", "94027",
    # Texas
    "77002", "76092", "77010", "77401", "77005", "78733",
    # Massachusetts
    "02481", "02030", "02482", "01776", "02420", "02052",
    # Pennsylvania
    "19035", "19087", "19085", "19003", "19010",
    # New Jersey
    "07078", "07021", "07620", "07458", "07042",
    # Florida
    "33109", "33480", "33156", "33496", "34102",
    # New York
    "10007", "10024", "10065", "10583",
    # Illinois
    "60043", "60022", "60093", "60521", "60045"
]

CSV_FILE = "output/enphase_platinum_gold_installers.csv"
PROGRESS_FILE = "output/enphase_platinum_gold_progress.json"

# Read CSV and find which ZIPs we actually collected from
completed_zips = set()
total_installers = 0

with open(CSV_FILE, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        zip_code = row.get('scraped_from_zip', '').strip()
        if zip_code and zip_code.isdigit() and len(zip_code) == 5:
            completed_zips.add(zip_code)
            total_installers += 1

# Sort completed and remaining
completed_sorted = sorted(completed_zips)
remaining_sorted = sorted([z for z in ALL_ZIPS if z not in completed_zips])

# Build accurate progress
progress = {
    "completed_zips": completed_sorted,
    "remaining_zips": remaining_sorted,
    "total_collected": total_installers,
    "notes": f"REBUILT FROM CSV: {len(completed_sorted)} ZIPs completed, {len(remaining_sorted)} remaining"
}

# Save
with open(PROGRESS_FILE, 'w') as f:
    json.dump(progress, f, indent=2)

print(f"✅ Progress rebuilt from CSV")
print(f"   Completed: {len(completed_sorted)} ZIPs")
print(f"   Remaining: {len(remaining_sorted)} ZIPs")
print(f"   Total installers: {total_installers}")
print(f"\nCompleted ZIPs: {', '.join(completed_sorted)}")
