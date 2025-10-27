#!/usr/bin/env python3
"""
Deduplicate Generac dealer CSV by phone number (primary key)
Keeps the first occurrence of each unique dealer
"""

import csv
from pathlib import Path

INPUT_CSV = "output/generac_dealers.csv"
OUTPUT_CSV = "output/generac_dealers_deduped.csv"
BACKUP_CSV = "output/generac_dealers_backup.csv"

def normalize_phone(phone):
    """Remove all non-digit characters from phone number"""
    return ''.join(c for c in str(phone) if c.isdigit())

def deduplicate_dealers():
    """Remove duplicate dealers, keeping first occurrence"""

    # Backup original file
    if not Path(INPUT_CSV).exists():
        print(f"❌ No data file found at {INPUT_CSV}")
        return [], {}
        
    Path(INPUT_CSV).rename(BACKUP_CSV)
    print(f"✅ Backed up original to {BACKUP_CSV}")

    # Read all dealers
    with open(BACKUP_CSV, 'r') as f:
        reader = csv.DictReader(f)
        dealers = list(reader)
        headers = reader.fieldnames

    print(f"📊 Total dealers before deduplication: {len(dealers)}")

    # Deduplicate by phone number
    seen_phones = set()
    seen_names = set()
    unique_dealers = []
    duplicates = []

    for dealer in dealers:
        phone = normalize_phone(dealer.get('phone', ''))
        name = dealer.get('name', '').strip().lower()

        # Use phone as primary key (most reliable)
        if phone and phone in seen_phones:
            duplicates.append(dealer)
            continue

        # Fallback to name if no phone
        if not phone and name in seen_names:
            duplicates.append(dealer)
            continue

        # Keep this dealer
        if phone:
            seen_phones.add(phone)
        if name:
            seen_names.add(name)
        unique_dealers.append(dealer)

    print(f"✅ Unique dealers: {len(unique_dealers)}")
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
        writer.writerows(unique_dealers)

    print(f"\n💾 Saved deduplicated file to {OUTPUT_CSV}")

    # Rename deduplicated file to original name
    Path(OUTPUT_CSV).rename(INPUT_CSV)
    print(f"✅ Replaced original with deduplicated version")

    # Show which ZIPs are actually in the data
    zip_counts = {}
    for dealer in unique_dealers:
        zip_code = dealer.get('scraped_from_zip', '')
        zip_counts[zip_code] = zip_counts.get(zip_code, 0) + 1

    print(f"\n📍 Dealers by ZIP code ({len(zip_counts)} unique ZIPs):")
    for zip_code in sorted(zip_counts.keys()):
        print(f"   {zip_code}: {zip_counts[zip_code]} dealers")

    return unique_dealers, zip_counts

if __name__ == "__main__":
    print("=" * 80)
    print("🧹 GENERAC DEALER DEDUPLICATION")
    print("=" * 80)

    unique, zip_counts = deduplicate_dealers()

    print("\n" + "=" * 80)
    print("✅ DEDUPLICATION COMPLETE!")
    print("=" * 80)
