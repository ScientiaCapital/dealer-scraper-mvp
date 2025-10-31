#!/usr/bin/env python3
"""
Deduplicate Enphase installer CSV by phone number (primary key)
Keeps the first occurrence of each unique installer
"""

import csv
from pathlib import Path

INPUT_CSV = "output/enphase_platinum_gold_installers.csv"
OUTPUT_CSV = "output/enphase_platinum_gold_installers_deduped.csv"
BACKUP_CSV = "output/enphase_platinum_gold_installers_backup.csv"

def normalize_phone(phone):
    """Remove all non-digit characters from phone number"""
    return ''.join(c for c in str(phone) if c.isdigit())

def deduplicate_installers():
    """Remove duplicate installers, keeping first occurrence"""

    # Backup original file
    Path(INPUT_CSV).rename(BACKUP_CSV)
    print(f"✅ Backed up original to {BACKUP_CSV}")

    # Read all installers
    with open(BACKUP_CSV, 'r') as f:
        reader = csv.DictReader(f)
        installers = list(reader)
        headers = reader.fieldnames

    print(f"📊 Total installers before deduplication: {len(installers)}")

    # Deduplicate by phone number
    seen_phones = set()
    seen_names = set()
    unique_installers = []
    duplicates = []

    for inst in installers:
        phone = normalize_phone(inst.get('phone', ''))
        name = inst.get('name', '').strip().lower()

        # Use phone as primary key (most reliable)
        if phone and phone in seen_phones:
            duplicates.append(inst)
            continue

        # Fallback to name if no phone
        if not phone and name in seen_names:
            duplicates.append(inst)
            continue

        # Keep this installer
        if phone:
            seen_phones.add(phone)
        if name:
            seen_names.add(name)
        unique_installers.append(inst)

    print(f"✅ Unique installers: {len(unique_installers)}")
    print(f"🗑️  Duplicates removed: {len(duplicates)}")

    # Show some duplicate examples
    if duplicates:
        print("\n📋 Sample duplicates removed:")
        for dup in duplicates[:5]:
            print(f"   - {dup.get('name')} ({dup.get('phone')}) from ZIP {dup.get('scraped_from_zip')}")

    # Write deduplicated file
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(unique_installers)

    print(f"\n💾 Saved deduplicated file to {OUTPUT_CSV}")

    # Rename deduplicated file to original name
    Path(OUTPUT_CSV).rename(INPUT_CSV)
    print(f"✅ Replaced original with deduplicated version")

    # Show which ZIPs are actually in the data
    zip_counts = {}
    for inst in unique_installers:
        zip_code = inst.get('scraped_from_zip', '')
        zip_counts[zip_code] = zip_counts.get(zip_code, 0) + 1

    print(f"\n📍 Installers by ZIP code ({len(zip_counts)} unique ZIPs):")
    for zip_code in sorted(zip_counts.keys()):
        print(f"   {zip_code}: {zip_counts[zip_code]} installers")

    return unique_installers, zip_counts

if __name__ == "__main__":
    print("=" * 80)
    print("🧹 ENPHASE INSTALLER DEDUPLICATION")
    print("=" * 80)

    unique, zip_counts = deduplicate_installers()

    print("\n" + "=" * 80)
    print("✅ DEDUPLICATION COMPLETE!")
    print("=" * 80)
