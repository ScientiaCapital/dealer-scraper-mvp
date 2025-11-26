#!/usr/bin/env python3
"""
merge_to_master.py - Unify all data sources into one master list

Data Sources:
1. State Licenses (SQLite) - 204K contractors with license types
2. SPW Rankings (JSON) - 401 solar companies with kW installed
3. Amicus Cooperative (JSON) - 104 quality solar companies

Unified Schema includes:
- Core identification: name, domain, phone, email
- Location: state, city, address
- Capabilities: has_solar, has_electrical, has_hvac, has_plumbing, has_roofing
- Source signals: in_spw, in_amicus_solar, in_amicus_om, has_state_license
- Quality metrics: spw_kw_installed, spw_list_count, license_count
- ICP Score: multi_source_score, capability_score, total_icp_score

Author: Claude + Tim Kipper
Date: 2025-11-26
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "output" / "master" / "pipeline.db"
SPW_DIR = PROJECT_ROOT / "output" / "sources" / "spw_2025"
AMICUS_DIR = PROJECT_ROOT / "output" / "sources" / "amicus"
OUTPUT_DIR = PROJECT_ROOT / "output" / "master"

# License category to capability mapping
CAPABILITY_MAP = {
    "SOLAR": "has_solar",
    "ELECTRICAL": "has_electrical",
    "HVAC": "has_hvac",
    "PLUMBING": "has_plumbing",
    "ROOFING": "has_roofing",
    "REFRIGERATION": "has_hvac",  # HVAC-adjacent
    "LOW_VOLTAGE": "has_electrical",  # Electrical-adjacent
    "FIRE": "has_fire_protection",
    "GENERAL": "has_general_contractor",
    "BUILDING": "has_general_contractor",
}

# SREC states (high value for solar)
SREC_STATES = {"CA", "TX", "PA", "MA", "NJ", "FL", "NY", "OH", "MD", "DC", "DE", "NH", "RI", "CT", "IL"}


def normalize_domain(url_or_domain: str) -> str:
    """Extract clean domain from URL or domain string"""
    if not url_or_domain:
        return ""

    # Add http if missing
    if not url_or_domain.startswith("http"):
        url_or_domain = "http://" + url_or_domain

    try:
        parsed = urlparse(url_or_domain)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url_or_domain.lower().replace("www.", "")


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching"""
    if not name:
        return ""

    # Lowercase and strip
    name = name.lower().strip()

    # Remove common suffixes
    suffixes = [
        " llc", " inc", " corp", " co", " company", " ltd", " llp",
        " solar", " energy", " electric", " electrical", " hvac",
        " plumbing", " roofing", " services", " service", " solutions"
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)

    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def load_spw_data() -> dict:
    """Load SPW rankings from JSON file"""
    spw_files = list(SPW_DIR.glob("spw_lists_*.json"))
    if not spw_files:
        print("⚠️ No SPW data found")
        return {}

    # Get most recent file
    latest_file = max(spw_files, key=lambda f: f.stat().st_mtime)
    print(f"📖 Loading SPW data from: {latest_file.name}")

    with open(latest_file) as f:
        data = json.load(f)

    # SPW data is a flat list of companies
    companies = data if isinstance(data, list) else data.get("companies", [])

    # Index by normalized company name
    spw_by_name = {}
    for company in companies:
        norm_name = normalize_company_name(company.get("company_name", ""))
        if norm_name:
            spw_by_name[norm_name] = company

    print(f"   Loaded {len(spw_by_name)} SPW companies")
    return spw_by_name


def load_amicus_data() -> dict:
    """Load Amicus cooperative data from JSON file"""
    amicus_files = list(AMICUS_DIR.glob("amicus_members_*.json"))
    if not amicus_files:
        print("⚠️ No Amicus data found")
        return {}

    # Get most recent file
    latest_file = max(amicus_files, key=lambda f: f.stat().st_mtime)
    print(f"📖 Loading Amicus data from: {latest_file.name}")

    with open(latest_file) as f:
        data = json.load(f)

    # Index by domain
    amicus_by_domain = {}
    for member in data.get("members", []):
        domain = member.get("domain", "")
        if domain:
            amicus_by_domain[domain] = member

    print(f"   Loaded {len(amicus_by_domain)} Amicus members")
    return amicus_by_domain


def get_contractor_capabilities(cursor, contractor_id: int) -> dict:
    """Get capability flags from license types"""
    cursor.execute("""
        SELECT DISTINCT license_category
        FROM licenses
        WHERE contractor_id = ?
    """, (contractor_id,))

    categories = [row[0] for row in cursor.fetchall()]

    capabilities = {
        "has_solar": False,
        "has_electrical": False,
        "has_hvac": False,
        "has_plumbing": False,
        "has_roofing": False,
        "has_fire_protection": False,
        "has_general_contractor": False,
        "license_categories": categories,
        "license_count": len(categories),
    }

    for cat in categories:
        if cat in CAPABILITY_MAP:
            capabilities[CAPABILITY_MAP[cat]] = True

    return capabilities


def get_contractor_states(cursor, contractor_id: int) -> list:
    """Get all states where contractor is licensed"""
    cursor.execute("""
        SELECT DISTINCT state
        FROM licenses
        WHERE contractor_id = ? AND state IS NOT NULL AND LENGTH(state) = 2
    """, (contractor_id,))

    return [row[0] for row in cursor.fetchall()]


def calculate_icp_score(record: dict) -> int:
    """Calculate ICP score (0-100) based on multiple signals"""
    score = 0

    # Source signals (max 40 points)
    if record.get("in_spw"):
        score += 15  # SPW = established solar company
    if record.get("in_amicus_solar"):
        score += 10  # Amicus = values-driven company
    if record.get("in_amicus_om"):
        score += 10  # O&M = monitoring need
    if record.get("has_state_license"):
        score += 5   # Licensed = legitimate

    # Capability signals (max 30 points)
    if record.get("has_solar"):
        score += 10
    if record.get("has_electrical"):
        score += 5
    if record.get("has_hvac"):
        score += 5
    if record.get("has_general_contractor"):
        score += 5
    if record.get("license_count", 0) >= 3:
        score += 5   # Multi-licensed = resimercial

    # Volume signals (max 20 points)
    kw = record.get("spw_kw_installed", 0)
    if kw > 1_000_000:
        score += 10
    elif kw > 100_000:
        score += 5

    list_count = record.get("spw_list_count", 0)
    if list_count >= 5:
        score += 10
    elif list_count >= 3:
        score += 5

    # Location signals (max 10 points)
    states = record.get("licensed_states", [])
    if any(s in SREC_STATES for s in states):
        score += 5
    if len(states) >= 3:
        score += 5   # Multi-state = larger operation

    return min(score, 100)


def build_master_list():
    """Build unified master list from all sources"""
    print("=" * 60)
    print("🔄 BUILDING UNIFIED MASTER LIST")
    print("=" * 60)

    # Load external data
    spw_data = load_spw_data()
    amicus_data = load_amicus_data()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all contractors with their data
    print("\n📊 Processing contractors from database...")
    cursor.execute("""
        SELECT
            c.id, c.company_name, c.normalized_name,
            c.street, c.city, c.state, c.zip,
            c.primary_phone, c.primary_email, c.primary_domain,
            c.website_url
        FROM contractors c
        ORDER BY c.company_name
    """)

    master_records = []
    stats = defaultdict(int)

    for row in cursor.fetchall():
        contractor_id = row["id"]

        # Get capabilities from licenses
        capabilities = get_contractor_capabilities(cursor, contractor_id)

        # Get licensed states
        licensed_states = get_contractor_states(cursor, contractor_id)

        # Normalize for matching
        norm_name = normalize_company_name(row["company_name"] or "")
        domain = normalize_domain(row["primary_domain"] or row["website_url"] or "")

        # Check SPW match
        spw_match = spw_data.get(norm_name)
        in_spw = spw_match is not None

        # Check Amicus match
        amicus_match = amicus_data.get(domain) if domain else None
        in_amicus_solar = amicus_match.get("in_amicus_solar", False) if amicus_match else False
        in_amicus_om = amicus_match.get("in_amicus_om", False) if amicus_match else False

        # Build unified record
        record = {
            # Core identification
            "id": contractor_id,
            "company_name": row["company_name"],
            "normalized_name": row["normalized_name"],
            "domain": domain,
            "website": row["website_url"],
            "phone": row["primary_phone"],
            "email": row["primary_email"],

            # Location
            "street": row["street"],
            "city": row["city"],
            "state": row["state"],
            "zip": row["zip"],
            "licensed_states": licensed_states,
            "state_count": len(licensed_states),

            # Capabilities
            **capabilities,

            # Source signals
            "has_state_license": True,
            "in_spw": in_spw,
            "in_amicus_solar": in_amicus_solar,
            "in_amicus_om": in_amicus_om,
            "source_count": 1 + (1 if in_spw else 0) + (1 if in_amicus_solar or in_amicus_om else 0),

            # SPW metrics (use kw_installed which has the correct value)
            "spw_kw_installed": spw_match.get("kw_installed", 0) if spw_match else 0,
            "spw_list_count": len(spw_match.get("source_lists", [])) if spw_match else 0,
            "spw_lists": spw_match.get("source_lists", []) if spw_match else [],

            # Amicus metrics
            "amicus_cooperative_count": (1 if in_amicus_solar else 0) + (1 if in_amicus_om else 0),
        }

        # Calculate ICP score
        record["icp_score"] = calculate_icp_score(record)

        # Determine tier
        if record["icp_score"] >= 80:
            record["icp_tier"] = "PLATINUM"
        elif record["icp_score"] >= 60:
            record["icp_tier"] = "GOLD"
        elif record["icp_score"] >= 40:
            record["icp_tier"] = "SILVER"
        else:
            record["icp_tier"] = "BRONZE"

        master_records.append(record)

        # Track stats
        stats["total"] += 1
        if in_spw:
            stats["in_spw"] += 1
        if in_amicus_solar or in_amicus_om:
            stats["in_amicus"] += 1
        if record["source_count"] >= 2:
            stats["multi_source"] += 1
        stats[record["icp_tier"]] += 1

    # Add Amicus-only companies (not in state license DB)
    print("\n📊 Adding Amicus-only companies...")
    existing_domains = {r["domain"] for r in master_records if r["domain"]}

    for domain, amicus_member in amicus_data.items():
        if domain not in existing_domains:
            # Check SPW match by name
            norm_name = normalize_company_name(amicus_member.get("company_name", ""))
            spw_match = spw_data.get(norm_name)

            record = {
                "id": None,
                "company_name": amicus_member.get("company_name"),
                "normalized_name": norm_name,
                "domain": domain,
                "website": amicus_member.get("website"),
                "phone": None,
                "email": None,
                "street": None,
                "city": None,
                "state": None,
                "zip": None,
                "licensed_states": [],
                "state_count": 0,

                # Capabilities (unknown from Amicus)
                "has_solar": True,  # Amicus = solar companies
                "has_electrical": False,
                "has_hvac": False,
                "has_plumbing": False,
                "has_roofing": False,
                "has_fire_protection": False,
                "has_general_contractor": False,
                "license_categories": [],
                "license_count": 0,

                # Source signals
                "has_state_license": False,
                "in_spw": spw_match is not None,
                "in_amicus_solar": amicus_member.get("in_amicus_solar", False),
                "in_amicus_om": amicus_member.get("in_amicus_om", False),
                "source_count": (1 if spw_match else 0) + 1,  # At least Amicus

                # SPW metrics (use kw_installed which has the correct value)
                "spw_kw_installed": spw_match.get("kw_installed", 0) if spw_match else 0,
                "spw_list_count": len(spw_match.get("source_lists", [])) if spw_match else 0,
                "spw_lists": spw_match.get("source_lists", []) if spw_match else [],
                "spw_hq_state": spw_match.get("headquarters_state") if spw_match else None,

                # Amicus metrics
                "amicus_cooperative_count": amicus_member.get("cooperative_count", 1),
            }

            record["icp_score"] = calculate_icp_score(record)

            if record["icp_score"] >= 80:
                record["icp_tier"] = "PLATINUM"
            elif record["icp_score"] >= 60:
                record["icp_tier"] = "GOLD"
            elif record["icp_score"] >= 40:
                record["icp_tier"] = "SILVER"
            else:
                record["icp_tier"] = "BRONZE"

            master_records.append(record)
            stats["amicus_only"] += 1
            stats["total"] += 1
            stats["in_amicus"] += 1
            stats[record["icp_tier"]] += 1

    # Add SPW-only companies
    print("\n📊 Adding SPW-only companies...")
    existing_names = {r["normalized_name"] for r in master_records if r["normalized_name"]}

    for norm_name, spw_company in spw_data.items():
        if norm_name not in existing_names:
            record = {
                "id": None,
                "company_name": spw_company.get("company_name"),
                "normalized_name": norm_name,
                "domain": normalize_domain(spw_company.get("website", "")),
                "website": spw_company.get("website"),
                "phone": None,
                "email": None,
                "street": None,
                "city": spw_company.get("city"),
                "state": spw_company.get("hq_state"),
                "zip": None,
                "licensed_states": [spw_company.get("hq_state")] if spw_company.get("hq_state") else [],
                "state_count": 1 if spw_company.get("hq_state") else 0,

                # Capabilities (SPW = solar)
                "has_solar": True,
                "has_electrical": False,
                "has_hvac": False,
                "has_plumbing": False,
                "has_roofing": False,
                "has_fire_protection": False,
                "has_general_contractor": False,
                "license_categories": [],
                "license_count": 0,

                # Source signals
                "has_state_license": False,
                "in_spw": True,
                "in_amicus_solar": False,
                "in_amicus_om": False,
                "source_count": 1,

                # SPW metrics
                "spw_kw_installed": spw_company.get("kw_installed", 0),
                "spw_list_count": len(spw_company.get("source_lists", [])),
                "spw_lists": spw_company.get("source_lists", []),

                # Amicus metrics
                "amicus_cooperative_count": 0,
            }

            record["icp_score"] = calculate_icp_score(record)

            if record["icp_score"] >= 80:
                record["icp_tier"] = "PLATINUM"
            elif record["icp_score"] >= 60:
                record["icp_tier"] = "GOLD"
            elif record["icp_score"] >= 40:
                record["icp_tier"] = "SILVER"
            else:
                record["icp_tier"] = "BRONZE"

            master_records.append(record)
            stats["spw_only"] += 1
            stats["total"] += 1
            stats["in_spw"] += 1
            stats[record["icp_tier"]] += 1

    conn.close()

    # Sort by ICP score descending
    master_records.sort(key=lambda r: (-r["icp_score"], r["company_name"] or ""))

    return master_records, stats


def save_master_list(records: list, stats: dict):
    """Save master list to JSON and CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON (full data)
    json_path = OUTPUT_DIR / f"master_list_{timestamp}.json"
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(records),
            "stats": dict(stats),
        },
        "records": records
    }

    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"\n💾 Saved JSON: {json_path}")

    # Save CSV (flat for spreadsheet)
    import csv
    csv_path = OUTPUT_DIR / f"master_list_{timestamp}.csv"

    # Flatten for CSV
    csv_fields = [
        "company_name", "domain", "phone", "email",
        "city", "state", "zip", "state_count",
        "has_solar", "has_electrical", "has_hvac", "has_plumbing", "has_roofing",
        "license_count",
        "in_spw", "in_amicus_solar", "in_amicus_om", "has_state_license",
        "source_count", "spw_kw_installed", "spw_list_count",
        "icp_score", "icp_tier"
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    print(f"💾 Saved CSV: {csv_path}")

    return json_path, csv_path


def print_summary(records: list, stats: dict):
    """Print summary of master list"""
    print("\n" + "=" * 60)
    print("📊 MASTER LIST SUMMARY")
    print("=" * 60)

    print(f"\n📈 Total Records: {stats['total']:,}")
    print(f"   └─ From State Licenses: {stats['total'] - stats.get('amicus_only', 0) - stats.get('spw_only', 0):,}")
    print(f"   └─ Amicus-only: {stats.get('amicus_only', 0):,}")
    print(f"   └─ SPW-only: {stats.get('spw_only', 0):,}")

    print(f"\n🔗 Source Coverage:")
    print(f"   └─ In SPW Rankings: {stats.get('in_spw', 0):,}")
    print(f"   └─ In Amicus: {stats.get('in_amicus', 0):,}")
    print(f"   └─ Multi-Source (2+): {stats.get('multi_source', 0):,}")

    print(f"\n🏆 ICP Tier Distribution:")
    print(f"   └─ PLATINUM (80-100): {stats.get('PLATINUM', 0):,}")
    print(f"   └─ GOLD (60-79): {stats.get('GOLD', 0):,}")
    print(f"   └─ SILVER (40-59): {stats.get('SILVER', 0):,}")
    print(f"   └─ BRONZE (<40): {stats.get('BRONZE', 0):,}")

    # Show top 10 by ICP score
    print("\n⭐ TOP 10 BY ICP SCORE:")
    for i, r in enumerate(records[:10], 1):
        sources = []
        if r["in_spw"]:
            sources.append("SPW")
        if r["in_amicus_solar"]:
            sources.append("Amicus-S")
        if r["in_amicus_om"]:
            sources.append("Amicus-OM")
        if r["has_state_license"]:
            sources.append("License")

        print(f"   {i}. [{r['icp_tier']}] {r['company_name']} (Score: {r['icp_score']})")
        print(f"      Sources: {', '.join(sources)}")
        if r["spw_kw_installed"]:
            print(f"      SPW: {r['spw_kw_installed']:,} kW across {r['spw_list_count']} lists")

    print("=" * 60)


def main():
    print("🚀 Starting Master List Merge...")
    print(f"   Database: {DB_PATH}")
    print(f"   SPW Source: {SPW_DIR}")
    print(f"   Amicus Source: {AMICUS_DIR}")

    records, stats = build_master_list()
    json_path, csv_path = save_master_list(records, stats)
    print_summary(records, stats)

    print(f"\n✅ Master list complete!")
    print(f"   JSON: {json_path}")
    print(f"   CSV: {csv_path}")


if __name__ == "__main__":
    main()
