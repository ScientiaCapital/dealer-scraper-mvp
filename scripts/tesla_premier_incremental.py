#!/usr/bin/env python3
"""
Tesla Premier Installer - Incremental CSV Collection
Saves results immediately after each ZIP to avoid memory buildup
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path

# Priority state ZIPs (40 total across CA, TX, MA, PA, NJ, FL, NY, IL)
PRIORITY_ZIPS = {
    "CA": ["94027", "94022", "94024", "94301", "90210"],
    "TX": ["76092", "77010", "77401", "77005", "78733"],
    "MA": ["02030", "02482", "01776", "02420", "02052"],
    "PA": ["19035", "19087", "19085", "19003", "19010"],
    "NJ": ["07078", "07021", "07620", "07458", "07042"],
    "FL": ["33109", "33480", "33156", "33496", "34102"],
    "NY": ["10007", "10024", "10065", "10583", "11962"],
    "IL": ["60043", "60022", "60093", "60521", "60045"]
}

OUTPUT_DIR = "output"
CSV_FILE = f"{OUTPUT_DIR}/tesla_premier_installers.csv"
PROGRESS_FILE = f"{OUTPUT_DIR}/tesla_premier_progress.json"

# CSV headers
HEADERS = [
    "name", "phone", "website", "domain", "email",
    "tier", "certifications", "oem_source",
    "scraped_from_zip", "state", "collection_date"
]


def load_progress():
    """Load which ZIPs have been completed"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_zips": [], "total_collected": 0}


def save_progress(progress):
    """Save progress JSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def append_installers_to_csv(installers):
    """Append installers to master CSV (create file if doesn't exist)"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)

        # Write header only if file is new
        if not file_exists:
            writer.writeheader()

        writer.writerows(installers)

    print(f"  ✓ Appended {len(installers)} Premier installers to {CSV_FILE}")


def get_remaining_zips():
    """Get list of ZIPs still to be scraped"""
    progress = load_progress()
    completed = set(progress["completed_zips"])

    all_zips = []
    for state, zips in PRIORITY_ZIPS.items():
        for zip_code in zips:
            if zip_code not in completed:
                all_zips.append((state, zip_code))

    return all_zips


def mark_zip_complete(zip_code, installer_count):
    """Mark ZIP as completed and update progress"""
    progress = load_progress()
    progress["completed_zips"].append(zip_code)
    progress["total_collected"] += installer_count
    save_progress(progress)
    print(f"  ✓ Progress saved: {len(progress['completed_zips'])}/40 ZIPs completed")


def print_status():
    """Print current collection status"""
    progress = load_progress()
    remaining = get_remaining_zips()

    print("=" * 70)
    print("TESLA PREMIER INSTALLER COLLECTION - INCREMENTAL MODE")
    print("=" * 70)
    print(f"Total Target: 40 ZIPs (8 priority states)")
    print(f"Completed: {len(progress['completed_zips'])} ZIPs")
    print(f"Remaining: {len(remaining)} ZIPs")
    print(f"Total Installers Collected: {progress['total_collected']}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    print_status()

    remaining = get_remaining_zips()
    if remaining:
        print(f"Next ZIP to scrape: {remaining[0][1]} ({remaining[0][0]})")
        print()
        print("WORKFLOW:")
        print("1. Use MCP Playwright browser to navigate and extract")
        print("2. Pass extracted installers to append_installers_to_csv()")
        print("3. Call mark_zip_complete(zip_code, count)")
        print("4. Repeat for next ZIP")
    else:
        print("✅ All 40 ZIPs completed!")
        print(f"Final output: {CSV_FILE}")
