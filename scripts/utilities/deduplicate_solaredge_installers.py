#!/usr/bin/env python3
import csv
from pathlib import Path

INPUT_CSV = "output/solaredge_installers.csv"

def normalize_phone(phone):
    return ''.join(c for c in str(phone) if c.isdigit())

def deduplicate():
    if not Path(INPUT_CSV).exists():
        print(f"❌ No data at {INPUT_CSV}")
        return
        
    Path(INPUT_CSV).rename("output/solaredge_installers_backup.csv")
    
    with open("output/solaredge_installers_backup.csv", 'r') as f:
        reader = csv.DictReader(f)
        installers = list(reader)
        headers = reader.fieldnames

    print(f"📊 Total: {len(installers)}")

    seen_phones = set()
    seen_names = set()
    unique = []

    for inst in installers:
        phone = normalize_phone(inst.get('phone', ''))
        name = inst.get('name', '').strip().lower()

        if (phone and phone in seen_phones) or (not phone and name in seen_names):
            continue

        if phone:
            seen_phones.add(phone)
        if name:
            seen_names.add(name)
        unique.append(inst)

    print(f"✅ Unique: {len(unique)}")
    print(f"🗑️  Duplicates: {len(installers) - len(unique)}")

    with open(INPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(unique)

    print(f"✅ Saved to {INPUT_CSV}")

if __name__ == "__main__":
    print("=" * 80)
    print("🧹 SOLAREDGE DEDUPLICATION")
    print("=" * 80)
    deduplicate()
