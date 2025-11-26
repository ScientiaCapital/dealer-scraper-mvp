#!/usr/bin/env python3
"""
Florida Multi-License Contractor Finder

Analyzes FL contractor license data to find:
- Multi-trade contractors (HVAC + Plumbing + Electrical + Roofing)
- These are SELF-PERFORMING contractors = highest ICP value for Coperniq
- Already have emails from state license database!

FL License Type Key:
- CAC: Class A Air Conditioning (HVAC)
- CMC: Certified Mechanical Contractor (HVAC)
- CPC: Certified Plumbing Contractor (PLUMBING)
- CFC: Certified Fire Contractor (FIRE)
- FRO: Florida Registered Roofing (ROOFING)
- CCC: Certified Roofing Contractor (ROOFING)
- CGC: Certified General Contractor (GENERAL)
- CBC: Certified Building Contractor (BUILDING)
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "enrichment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path.home() / "Downloads"
EVERYONE_FILE = DOWNLOADS / "Contractor List.xlsx - Everyone.csv"

# MEP+R License Types (Coperniq ICP targets)
LICENSE_CATEGORIES = {
    # HVAC
    "CAC": "HVAC",
    "CMC": "HVAC",
    # Plumbing
    "CPC": "PLUMBING",
    # Fire/Low Voltage
    "CFC": "FIRE",
    # Roofing
    "FRO": "ROOFING",
    "CCC": "ROOFING",
    # General/Building (resimercial signal)
    "CGC": "GENERAL",
    "CBC": "BUILDING",
    # Specialty
    "CUC": "UTILITY",
    "SCC": "SPECIALTY",
}


def normalize_name(name: str) -> str:
    """Normalize company/person name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" llc", " inc", " inc.", " corp", " corp.", " co", " co.",
                   " ltd", " ltd.", " company", ", llc", ", inc", ", inc."]:
        name = name.replace(suffix, "")
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def normalize_phone(phone: str) -> str:
    """Normalize phone to 10 digits."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def main():
    print("\n" + "=" * 70)
    print("FLORIDA MULTI-LICENSE CONTRACTOR FINDER")
    print("=" * 70)

    if not EVERYONE_FILE.exists():
        print(f"❌ File not found: {EVERYONE_FILE}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Index by company name and email to find multi-license holders
    company_licenses = defaultdict(lambda: {
        "licenses": set(),
        "categories": set(),
        "names": set(),
        "emails": set(),
        "addresses": [],
        "rows": []
    })

    email_licenses = defaultdict(lambda: {
        "licenses": set(),
        "categories": set(),
        "companies": set(),
        "names": set(),
        "rows": []
    })

    print(f"\n📂 Loading {EVERYONE_FILE.name}...")

    total_rows = 0
    mep_rows = 0

    with open(EVERYONE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader, None)

        for row in reader:
            total_rows += 1
            if len(row) < 10:
                continue

            license_type = row[0].strip().upper() if row[0] else ""
            name = row[1].strip() if len(row) > 1 else ""
            company = row[2].strip() if len(row) > 2 else ""
            address = row[3].strip() if len(row) > 3 else ""
            city = row[5].strip() if len(row) > 5 else ""
            state = row[6].strip() if len(row) > 6 else ""
            zipcode = row[7].strip() if len(row) > 7 else ""
            email = row[9].strip().upper() if len(row) > 9 else ""

            # Only process MEP+R license types
            category = LICENSE_CATEGORIES.get(license_type)
            if not category:
                continue

            mep_rows += 1

            # Use company name as primary key, fall back to person name
            key = normalize_name(company) if company else normalize_name(name)
            if not key:
                continue

            company_licenses[key]["licenses"].add(license_type)
            company_licenses[key]["categories"].add(category)
            company_licenses[key]["names"].add(name)
            if email:
                company_licenses[key]["emails"].add(email)
            company_licenses[key]["addresses"].append({
                "address": address,
                "city": city,
                "state": state,
                "zip": zipcode
            })
            company_licenses[key]["rows"].append(row)

            # Also index by email
            if email:
                email_licenses[email]["licenses"].add(license_type)
                email_licenses[email]["categories"].add(category)
                email_licenses[email]["companies"].add(company or name)
                email_licenses[email]["names"].add(name)
                email_licenses[email]["rows"].append(row)

    print(f"✅ Loaded {total_rows:,} total rows")
    print(f"✅ MEP+R contractors: {mep_rows:,}")
    print(f"✅ Unique companies: {len(company_licenses):,}")
    print(f"✅ Unique emails: {len(email_licenses):,}")

    # Find multi-license contractors (2+ different categories)
    print("\n🔍 Finding multi-license contractors...")

    multi_license = []
    for key, data in company_licenses.items():
        if len(data["categories"]) >= 2:
            multi_license.append({
                "key": key,
                "company_names": list(data["names"])[:3],  # First 3 names
                "emails": list(data["emails"]),
                "licenses": list(data["licenses"]),
                "categories": list(data["categories"]),
                "category_count": len(data["categories"]),
                "address": data["addresses"][0] if data["addresses"] else {}
            })

    # Sort by number of categories (more = higher value)
    multi_license.sort(key=lambda x: -x["category_count"])

    print(f"\n🎯 Found {len(multi_license):,} multi-license contractors!")

    # Category distribution
    print("\n📊 Multi-License Category Distribution:")
    cat_counts = defaultdict(int)
    for ml in multi_license:
        for cat in ml["categories"]:
            cat_counts[cat] += 1

    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count:,}")

    # Find UNICORNS: 3+ categories (HVAC + Plumbing + Roofing, etc.)
    unicorns = [ml for ml in multi_license if ml["category_count"] >= 3]
    print(f"\n🦄 UNICORNS (3+ trade categories): {len(unicorns)}")

    # Top examples
    print("\n📋 Top 10 Multi-Trade Contractors:")
    for i, ml in enumerate(multi_license[:10], 1):
        cats = ", ".join(ml["categories"])
        name = ml["company_names"][0] if ml["company_names"] else ml["key"]
        emails = ml["emails"][:2]
        print(f"   {i}. {name}")
        print(f"      Categories: {cats}")
        print(f"      Emails: {', '.join(emails) if emails else 'N/A'}")

    # Output: Multi-license contractors with emails (ready for outreach!)
    output_file = OUTPUT_DIR / f"fl_multi_license_contractors_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company_name", "contact_names", "emails", "licenses", "categories",
            "category_count", "city", "state", "zip"
        ])
        writer.writeheader()

        for ml in multi_license:
            if ml["emails"]:  # Only those with emails
                writer.writerow({
                    "company_name": ml["company_names"][0] if ml["company_names"] else ml["key"],
                    "contact_names": "|".join(ml["company_names"][:3]),
                    "emails": "|".join(ml["emails"][:5]),
                    "licenses": "|".join(ml["licenses"]),
                    "categories": "|".join(ml["categories"]),
                    "category_count": ml["category_count"],
                    "city": ml["address"].get("city", ""),
                    "state": ml["address"].get("state", ""),
                    "zip": ml["address"].get("zip", ""),
                })

    print(f"\n✅ Saved: {output_file}")

    # Output: Unicorns (3+ categories)
    if unicorns:
        unicorn_file = OUTPUT_DIR / f"fl_unicorn_contractors_{timestamp}.csv"
        with open(unicorn_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "company_name", "contact_names", "emails", "licenses", "categories",
                "category_count", "city", "state", "zip"
            ])
            writer.writeheader()

            for ml in unicorns:
                writer.writerow({
                    "company_name": ml["company_names"][0] if ml["company_names"] else ml["key"],
                    "contact_names": "|".join(ml["company_names"][:3]),
                    "emails": "|".join(ml["emails"][:5]),
                    "licenses": "|".join(ml["licenses"]),
                    "categories": "|".join(ml["categories"]),
                    "category_count": ml["category_count"],
                    "city": ml["address"].get("city", ""),
                    "state": ml["address"].get("state", ""),
                    "zip": ml["address"].get("zip", ""),
                })

        print(f"✅ Saved: {unicorn_file}")

    # Summary
    with_emails = sum(1 for ml in multi_license if ml["emails"])

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total FL MEP+R contractors: {mep_rows:,}")
    print(f"Multi-license contractors: {len(multi_license):,}")
    print(f"Multi-license with emails: {with_emails:,} (ready for outreach!)")
    print(f"UNICORNS (3+ trades): {len(unicorns)}")
    print(f"\n📁 Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
