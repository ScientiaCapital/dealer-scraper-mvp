#!/usr/bin/env python3
"""
integrate_oem_data.py - Integrate OEM dealer data into master database

This script:
1. Loads all OEM CSV files from archive
2. Matches contractors to existing database records (by phone/domain/name)
3. Creates OEM certification records
4. Cross-references with state licenses, SPW, Amicus
5. Calculates enhanced ICP scores
6. Outputs top 500-1000 leads sorted by score

ICP Scoring (from CLAUDE.md):
- Resimercial (35%): Both residential + commercial
- Multi-OEM (25%): Managing 3-4+ monitoring platforms
- MEP+E (25%): Electrical + HVAC + Plumbing trades
- O&M (15%): Install AND maintain

PLATINUM TARGET: Multi-License + Multi-OEM + SPW/Amicus

Author: Claude + Tim Kipper
Date: 2025-11-26
"""

import csv
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "output" / "master" / "pipeline.db"
OEM_DATA_DIR = PROJECT_ROOT / "output" / "_archive" / "2025-11-26_pre_cleanup" / "oem_data"
SPW_DIR = PROJECT_ROOT / "output" / "sources" / "spw_2025"
AMICUS_DIR = PROJECT_ROOT / "output" / "sources" / "amicus"
OUTPUT_DIR = PROJECT_ROOT / "output" / "master"

# OEM files to import
OEM_FILES = {
    "Generac": "generac/generac_national_20251028.csv",
    "Briggs & Stratton": "briggs/briggs_stratton_national_20251028.csv",
    "Cummins": "cummins/cummins_national_20251028_deduped.csv",
    "Tesla": "tesla/tesla_powerwall_premier_20251026_deduped.csv",
    "Enphase": "enphase/enphase_platinum_gold_20251026_deduped.csv",
    "Carrier": "carrier/carrier_production_20251028.csv",
    "Mitsubishi": "mitsubishi/mitsubishi_electric_production_20251028.csv",
    "York": "york/york_hvac_production_20251029.csv",
    "SMA": "sma/sma_solar_production_20251029.csv",
}

# OEM categories for capability inference
OEM_CATEGORIES = {
    "Generac": {"type": "generator", "has_generator": True},
    "Briggs & Stratton": {"type": "generator", "has_generator": True},
    "Cummins": {"type": "generator", "has_generator": True},
    "Kohler": {"type": "generator", "has_generator": True},
    "Tesla": {"type": "battery", "has_battery": True, "has_solar": True},
    "Enphase": {"type": "solar", "has_solar": True, "has_microinverters": True},
    "SolarEdge": {"type": "solar", "has_solar": True, "has_inverters": True},
    "SMA": {"type": "solar", "has_solar": True, "has_inverters": True},
    "Carrier": {"type": "hvac", "has_hvac": True},
    "Mitsubishi": {"type": "hvac", "has_hvac": True},
    "York": {"type": "hvac", "has_hvac": True},
    "Trane": {"type": "hvac", "has_hvac": True},
    "Rheem": {"type": "hvac", "has_hvac": True},
}

# SREC states
SREC_STATES = {"CA", "TX", "PA", "MA", "NJ", "FL", "NY", "OH", "MD", "DC", "DE", "NH", "RI", "CT", "IL"}


def normalize_phone(phone: str) -> str:
    """Normalize phone to 10 digits"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def normalize_domain(url_or_domain: str) -> str:
    """Extract clean domain from URL"""
    if not url_or_domain:
        return ""
    if not url_or_domain.startswith("http"):
        url_or_domain = "http://" + url_or_domain
    try:
        parsed = urlparse(url_or_domain)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching"""
    if not name:
        return ""
    name = name.lower().strip()
    suffixes = [" llc", " inc", " corp", " co", " company", " ltd", " llp"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def load_spw_data() -> dict:
    """Load SPW data indexed by normalized name"""
    spw_files = list(SPW_DIR.glob("spw_lists_*.json"))
    if not spw_files:
        return {}
    latest = max(spw_files, key=lambda f: f.stat().st_mtime)
    data = json.loads(latest.read_text())
    companies = data if isinstance(data, list) else data.get("companies", [])
    return {normalize_company_name(c.get("company_name", "")): c for c in companies if c.get("company_name")}


def load_amicus_data() -> dict:
    """Load Amicus data indexed by domain"""
    amicus_files = list(AMICUS_DIR.glob("amicus_members_*.json"))
    if not amicus_files:
        return {}
    latest = max(amicus_files, key=lambda f: f.stat().st_mtime)
    data = json.loads(latest.read_text())
    return {m.get("domain"): m for m in data.get("members", []) if m.get("domain")}


def load_oem_file(oem_name: str, file_path: Path) -> list[dict]:
    """Load a single OEM CSV file"""
    if not file_path.exists():
        print(f"   ⚠️ File not found: {file_path}")
        return []

    contractors = []
    with open(file_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize fields
            contractor = {
                "name": row.get("name", "").strip(),
                "phone": normalize_phone(row.get("phone", "")),
                "domain": normalize_domain(row.get("domain") or row.get("website", "")),
                "website": row.get("website", ""),
                "email": row.get("email", ""),
                "street": row.get("street", ""),
                "city": row.get("city", ""),
                "state": row.get("state", "").upper()[:2] if row.get("state") else "",
                "zip": row.get("zip", "")[:5] if row.get("zip") else "",
                "tier": row.get("tier", ""),
                "certifications": row.get("certifications", ""),
                "oem_source": oem_name,
                "scraped_from_zip": row.get("scraped_from_zip", ""),
            }
            if contractor["name"]:
                contractors.append(contractor)

    return contractors


def match_to_existing_contractor(cursor, contractor: dict) -> int | None:
    """Try to match contractor to existing database record"""
    # Match by phone
    if contractor["phone"]:
        cursor.execute("""
            SELECT id FROM contractors
            WHERE primary_phone = ? OR primary_phone LIKE ?
        """, (contractor["phone"], f"%{contractor['phone']}%"))
        result = cursor.fetchone()
        if result:
            return result[0]

    # Match by domain
    if contractor["domain"]:
        cursor.execute("""
            SELECT id FROM contractors
            WHERE primary_domain = ?
        """, (contractor["domain"],))
        result = cursor.fetchone()
        if result:
            return result[0]

    # Match by normalized name + state
    norm_name = normalize_company_name(contractor["name"])
    if norm_name and contractor["state"]:
        cursor.execute("""
            SELECT id FROM contractors
            WHERE normalized_name = ? AND state = ?
        """, (norm_name, contractor["state"]))
        result = cursor.fetchone()
        if result:
            return result[0]

    return None


def create_contractor(cursor, contractor: dict) -> int:
    """Create new contractor record"""
    cursor.execute("""
        INSERT INTO contractors (
            company_name, normalized_name, street, city, state, zip,
            primary_phone, primary_email, primary_domain, website_url,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contractor["name"],
        normalize_company_name(contractor["name"]),
        contractor["street"],
        contractor["city"],
        contractor["state"],
        contractor["zip"],
        contractor["phone"],
        contractor["email"],
        contractor["domain"],
        contractor["website"],
        datetime.now(),
        datetime.now()
    ))
    return cursor.lastrowid


def add_oem_certification(cursor, contractor_id: int, oem_name: str, tier: str, scraped_zip: str):
    """Add OEM certification record"""
    # Check if already exists
    cursor.execute("""
        SELECT id FROM oem_certifications
        WHERE contractor_id = ? AND oem_name = ?
    """, (contractor_id, oem_name))

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO oem_certifications (
                contractor_id, oem_name, certification_tier,
                scraped_from_zip, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (contractor_id, oem_name, tier, scraped_zip, datetime.now()))


def get_contractor_data(cursor, contractor_id: int) -> dict:
    """Get full contractor data including licenses and OEM certs"""
    # Get contractor base info
    cursor.execute("""
        SELECT * FROM contractors WHERE id = ?
    """, (contractor_id,))
    row = cursor.fetchone()
    if not row:
        return None

    columns = [desc[0] for desc in cursor.description]
    contractor = dict(zip(columns, row))

    # Get licenses
    cursor.execute("""
        SELECT license_category, state FROM licenses
        WHERE contractor_id = ?
    """, (contractor_id,))
    licenses = cursor.fetchall()
    contractor["license_categories"] = list(set(l[0] for l in licenses if l[0]))
    contractor["licensed_states"] = list(set(l[1] for l in licenses if l[1] and len(l[1]) == 2))

    # Get OEM certifications
    cursor.execute("""
        SELECT oem_name, certification_tier FROM oem_certifications
        WHERE contractor_id = ?
    """, (contractor_id,))
    oems = cursor.fetchall()
    contractor["oem_certifications"] = [o[0] for o in oems]
    contractor["oem_tiers"] = {o[0]: o[1] for o in oems}

    return contractor


def calculate_enhanced_icp_score(contractor: dict, spw_data: dict, amicus_data: dict) -> dict:
    """Calculate enhanced ICP score using all signals"""

    # Initialize scores
    resimercial_score = 0
    multi_oem_score = 0
    mepr_score = 0
    om_score = 0

    # Evidence tracking
    evidence = {
        "resimercial": [],
        "multi_oem": [],
        "mepr": [],
        "om": []
    }

    # === RESIMERCIAL (35%) ===
    # Check if serves both residential and commercial
    oems = contractor.get("oem_certifications", [])
    has_hvac_oem = any(o in ["Carrier", "Mitsubishi", "York", "Trane"] for o in oems)
    has_generator_oem = any(o in ["Generac", "Briggs & Stratton", "Cummins", "Kohler"] for o in oems)
    has_solar_oem = any(o in ["Tesla", "Enphase", "SMA", "SolarEdge"] for o in oems)

    # HVAC contractors typically serve both residential and commercial
    if has_hvac_oem:
        resimercial_score += 25
        evidence["resimercial"].append("HVAC OEM (typically resimercial)")

    # Multiple product types = likely resimercial
    product_types = sum([has_hvac_oem, has_generator_oem, has_solar_oem])
    if product_types >= 2:
        resimercial_score += 10
        evidence["resimercial"].append(f"Multi-product ({product_types} types)")

    # === MULTI-OEM (25%) ===
    oem_count = len(oems)
    if oem_count >= 3:
        multi_oem_score = 25
        evidence["multi_oem"].append(f"Triple+ OEM ({oem_count} brands) - UNICORN!")
    elif oem_count == 2:
        multi_oem_score = 15
        evidence["multi_oem"].append(f"Dual OEM ({oems[0]}, {oems[1]})")
    elif oem_count == 1:
        multi_oem_score = 5
        evidence["multi_oem"].append(f"Single OEM ({oems[0]})")

    # === MEP+E (25%) - Self-performing multi-trade ===
    license_cats = contractor.get("license_categories", [])

    # Check for MEP trades
    has_electrical = "ELECTRICAL" in license_cats or any(o in ["Enphase", "Tesla", "SMA"] for o in oems)
    has_hvac = "HVAC" in license_cats or has_hvac_oem
    has_plumbing = "PLUMBING" in license_cats
    has_roofing = "ROOFING" in license_cats
    has_solar = "SOLAR" in license_cats or has_solar_oem

    mep_count = sum([has_electrical, has_hvac, has_plumbing])
    mepr_count = mep_count + (1 if has_roofing or has_solar else 0)

    if mepr_count >= 3:
        mepr_score = 25
        evidence["mepr"].append(f"Multi-MEP+R ({mepr_count} trades) - Self-performing!")
    elif mepr_count == 2:
        mepr_score = 15
        evidence["mepr"].append(f"Dual-trade ({mepr_count} trades)")
    elif mepr_count == 1:
        mepr_score = 5
        trades = []
        if has_electrical: trades.append("Electrical")
        if has_hvac: trades.append("HVAC")
        if has_plumbing: trades.append("Plumbing")
        evidence["mepr"].append(f"Single trade: {', '.join(trades)}")

    # === O&M (15%) - Install AND maintain ===
    # Amicus O&M membership is strong signal
    domain = contractor.get("primary_domain") or contractor.get("domain", "")
    amicus_match = amicus_data.get(domain) if domain else None

    if amicus_match and amicus_match.get("in_amicus_om"):
        om_score += 15
        evidence["om"].append("Amicus O&M member (proven O&M capability)")
    elif has_hvac_oem:
        om_score += 10
        evidence["om"].append("HVAC OEM (service contracts typical)")
    elif has_generator_oem:
        om_score += 5
        evidence["om"].append("Generator OEM (maintenance required)")

    # === BONUS SIGNALS ===
    bonus = 0

    # SPW presence
    norm_name = normalize_company_name(contractor.get("company_name", ""))
    spw_match = spw_data.get(norm_name)
    if spw_match:
        kw = spw_match.get("kw_installed", 0)
        lists = len(spw_match.get("source_lists", []))
        bonus += 10
        evidence["multi_oem"].append(f"SPW ranked ({kw:,} kW, {lists} lists)")

    # Amicus Solar presence
    if amicus_match and amicus_match.get("in_amicus_solar"):
        bonus += 5
        evidence["resimercial"].append("Amicus Solar member (values-driven)")

    # SREC state
    states = contractor.get("licensed_states", [])
    if any(s in SREC_STATES for s in states):
        bonus += 5
        evidence["resimercial"].append(f"SREC state ({', '.join([s for s in states if s in SREC_STATES])})")

    # Calculate total
    total_score = resimercial_score + multi_oem_score + mepr_score + om_score + bonus
    total_score = min(total_score, 100)  # Cap at 100

    # Determine tier
    if total_score >= 80:
        tier = "PLATINUM"
    elif total_score >= 60:
        tier = "GOLD"
    elif total_score >= 40:
        tier = "SILVER"
    else:
        tier = "BRONZE"

    return {
        "icp_score": total_score,
        "icp_tier": tier,
        "resimercial_score": resimercial_score,
        "multi_oem_score": multi_oem_score,
        "mepr_score": mepr_score,
        "om_score": om_score,
        "bonus_score": bonus,
        "evidence": evidence,
        "oem_count": oem_count,
        "oems_certified": oems,
        "mepr_count": mepr_count,
        "in_spw": spw_match is not None,
        "in_amicus_solar": amicus_match.get("in_amicus_solar", False) if amicus_match else False,
        "in_amicus_om": amicus_match.get("in_amicus_om", False) if amicus_match else False,
    }


def main():
    print("=" * 70)
    print("🔄 OEM DATA INTEGRATION")
    print("=" * 70)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load external data
    print("\n📖 Loading external data sources...")
    spw_data = load_spw_data()
    print(f"   SPW: {len(spw_data)} companies")
    amicus_data = load_amicus_data()
    print(f"   Amicus: {len(amicus_data)} members")

    # Track stats
    stats = {
        "total_oem_records": 0,
        "matched_existing": 0,
        "created_new": 0,
        "certifications_added": 0,
    }

    # Process each OEM file
    print("\n📥 Importing OEM dealer data...")
    for oem_name, file_path in OEM_FILES.items():
        full_path = OEM_DATA_DIR / file_path
        contractors = load_oem_file(oem_name, full_path)

        if not contractors:
            continue

        print(f"\n   {oem_name}: {len(contractors)} dealers")

        for contractor in contractors:
            stats["total_oem_records"] += 1

            # Try to match existing
            contractor_id = match_to_existing_contractor(cursor, contractor)

            if contractor_id:
                stats["matched_existing"] += 1
            else:
                # Create new contractor
                contractor_id = create_contractor(cursor, contractor)
                stats["created_new"] += 1

            # Add OEM certification
            add_oem_certification(
                cursor, contractor_id, oem_name,
                contractor.get("tier", ""),
                contractor.get("scraped_from_zip", "")
            )
            stats["certifications_added"] += 1

    # Commit changes
    conn.commit()

    # Print import stats
    print("\n" + "=" * 70)
    print("📊 IMPORT STATISTICS")
    print("=" * 70)
    print(f"   Total OEM records processed: {stats['total_oem_records']:,}")
    print(f"   Matched to existing contractors: {stats['matched_existing']:,}")
    print(f"   New contractors created: {stats['created_new']:,}")
    print(f"   OEM certifications added: {stats['certifications_added']:,}")

    # Get contractors with OEM certifications
    print("\n📊 Scoring contractors with OEM certifications...")
    cursor.execute("""
        SELECT DISTINCT contractor_id FROM oem_certifications
    """)
    oem_contractor_ids = [row[0] for row in cursor.fetchall()]
    print(f"   Found {len(oem_contractor_ids)} contractors with OEM certifications")

    # Score all OEM contractors
    scored_contractors = []
    for contractor_id in oem_contractor_ids:
        contractor = get_contractor_data(cursor, contractor_id)
        if contractor:
            score_data = calculate_enhanced_icp_score(contractor, spw_data, amicus_data)
            contractor.update(score_data)
            scored_contractors.append(contractor)

    # Sort by ICP score
    scored_contractors.sort(key=lambda c: (-c["icp_score"], c["company_name"] or ""))

    # Get tier distribution
    tiers = defaultdict(int)
    for c in scored_contractors:
        tiers[c["icp_tier"]] += 1

    print("\n🏆 ICP TIER DISTRIBUTION (OEM Contractors):")
    print(f"   PLATINUM (80-100): {tiers['PLATINUM']:,}")
    print(f"   GOLD (60-79): {tiers['GOLD']:,}")
    print(f"   SILVER (40-59): {tiers['SILVER']:,}")
    print(f"   BRONZE (<40): {tiers['BRONZE']:,}")

    # Get multi-OEM contractors
    multi_oem = [c for c in scored_contractors if c["oem_count"] >= 2]
    triple_oem = [c for c in scored_contractors if c["oem_count"] >= 3]
    print(f"\n🌟 MULTI-OEM CONTRACTORS:")
    print(f"   Triple+ OEM (3+ brands): {len(triple_oem)} 🏆 UNICORNS")
    print(f"   Dual OEM (2 brands): {len(multi_oem) - len(triple_oem)}")

    # Save top 1000 leads
    top_leads = scored_contractors[:1000]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON
    json_path = OUTPUT_DIR / f"top_1000_leads_{timestamp}.json"
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scored": len(scored_contractors),
            "top_leads": len(top_leads),
            "tiers": dict(tiers),
            "multi_oem_count": len(multi_oem),
            "triple_oem_count": len(triple_oem),
        },
        "leads": top_leads
    }
    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    # Save CSV
    csv_path = OUTPUT_DIR / f"top_1000_leads_{timestamp}.csv"
    csv_fields = [
        "company_name", "primary_phone", "primary_domain", "primary_email",
        "city", "state", "zip",
        "icp_score", "icp_tier",
        "oem_count", "oems_certified",
        "mepr_count", "license_categories",
        "in_spw", "in_amicus_solar", "in_amicus_om",
        "resimercial_score", "multi_oem_score", "mepr_score", "om_score"
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for lead in top_leads:
            lead["oems_certified"] = ", ".join(lead.get("oems_certified", []))
            lead["license_categories"] = ", ".join(lead.get("license_categories", []))
            writer.writerow(lead)

    print(f"\n💾 SAVED TOP 1000 LEADS:")
    print(f"   JSON: {json_path}")
    print(f"   CSV: {csv_path}")

    # Show top 20
    print("\n" + "=" * 70)
    print("⭐ TOP 20 LEADS")
    print("=" * 70)
    for i, lead in enumerate(top_leads[:20], 1):
        oems = ", ".join(lead.get("oems_certified", []))
        print(f"\n{i}. [{lead['icp_tier']}] {lead['company_name']} (Score: {lead['icp_score']})")
        print(f"   📍 {lead.get('city', '')}, {lead.get('state', '')}")
        print(f"   🏭 OEMs: {oems}")
        if lead.get("license_categories"):
            print(f"   📜 Licenses: {', '.join(lead['license_categories'])}")
        if lead.get("in_spw"):
            print(f"   📈 In SPW Rankings")
        if lead.get("in_amicus_solar") or lead.get("in_amicus_om"):
            amicus = []
            if lead.get("in_amicus_solar"): amicus.append("Solar")
            if lead.get("in_amicus_om"): amicus.append("O&M")
            print(f"   🤝 Amicus: {', '.join(amicus)}")

    conn.close()
    print("\n" + "=" * 70)
    print("✅ OEM INTEGRATION COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
