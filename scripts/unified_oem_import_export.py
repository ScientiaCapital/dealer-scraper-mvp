#!/usr/bin/env python3
"""
unified_oem_import_export.py - Import OEM data and export in sales-agent compatible format

This script bridges the dealer-scraper-mvp and sales-agent projects by:
1. Importing OEM certification data from archived CSV files
2. Matching OEM dealers to existing contractors by phone/domain/name
3. Calculating enhanced ICP scores with multi-OEM signals
4. Exporting in the exact schema sales-agent expects

OEM Categories:
- Generators: Generac, Briggs & Stratton, Cummins
- HVAC: Carrier, Mitsubishi, Rheem, Trane, York
- Solar/Battery: Enphase, Tesla, SMA

Output Fields (40+ columns for sales-agent compatibility):
- Core: company_name, domain, phone, email, city, state, zip
- OEM: oems_certified (JSON), oem_tiers (JSON), total_oem_count
- Categories: hvac_oem_count, solar_oem_count, battery_oem_count, generator_oem_count
- Capabilities: has_hvac, has_solar, has_battery, has_generator, etc.
- ICP: icp_score, icp_tier, mep_e_score, renewable_readiness_score, asset_centric_score

Author: Claude + Tim Kipper
Date: 2025-11-26
"""

import csv
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "output" / "master" / "pipeline.db"
OEM_DATA_DIR = BASE_DIR / "output" / "_archive" / "2025-11-26_pre_cleanup" / "oem_data"
OUTPUT_DIR = BASE_DIR / "output" / "sales_agent_ready"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OEM file mapping with categories
OEM_FILES = {
    # Generators
    "Generac": {
        "file": "generac/generac_national_20251028.csv",
        "category": "generator",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Briggs & Stratton": {
        "file": "briggs/briggs_stratton_national_20251028.csv",
        "category": "generator",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Cummins": {
        "file": "cummins/cummins_national_20251028_deduped.csv",
        "category": "generator",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    # HVAC
    "Carrier": {
        "file": "carrier/carrier_production_20251028.csv",
        "category": "hvac",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Mitsubishi": {
        "file": "mitsubishi/mitsubishi_electric_production_20251028.csv",
        "category": "hvac",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Rheem": {
        "file": "rheem/rheem_production_20251028.csv",
        "category": "hvac",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Trane": {
        "file": "trane/trane_hvac_test_extraction.csv",
        "category": "hvac",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": None,  # No tier column
    },
    "York": {
        "file": "york/york_hvac_production_20251029.csv",
        "category": "hvac",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    # Solar/Battery
    "Enphase": {
        "file": "enphase/enphase_platinum_gold_20251026_deduped.csv",
        "category": "solar",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "Tesla": {
        "file": "tesla/tesla_powerwall_premier_20251026_deduped.csv",
        "category": "battery",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
    "SMA": {
        "file": "sma/sma_solar_production_20251029.csv",
        "category": "solar",
        "phone_col": "phone",
        "domain_col": "domain",
        "name_col": "name",
        "tier_col": "tier",
    },
}


def normalize_phone(phone: str) -> str:
    """Normalize phone to 10 digits"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def normalize_domain(domain: str) -> str:
    """Normalize domain for matching"""
    if not domain:
        return ""
    domain = domain.lower().strip()
    domain = re.sub(r'^(https?://)?(www\.)?', '', domain)
    domain = domain.split('/')[0]
    return domain


def normalize_name(name: str) -> str:
    """Normalize company name for fuzzy matching"""
    if not name:
        return ""
    name = name.upper().strip()
    # Remove common suffixes
    for suffix in [' LLC', ' INC', ' CORP', ' CO', ' LTD', ' LP', ' LLP', '.', ',']:
        name = name.replace(suffix, '')
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


class UnifiedOEMProcessor:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.stats = {
            "oem_records_loaded": 0,
            "matched_by_phone": 0,
            "matched_by_domain": 0,
            "matched_by_name": 0,
            "unmatched": 0,
            "new_certifications": 0,
        }

    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"📂 Connected to: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def get_contractor_count(self) -> int:
        """Get total contractor count"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM contractors")
        return cursor.fetchone()[0]

    def find_contractor_by_phone(self, phone: str) -> Optional[int]:
        """Find contractor by normalized phone"""
        if not phone:
            return None
        cursor = self.conn.execute(
            "SELECT id FROM contractors WHERE primary_phone = ?",
            (phone,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def find_contractor_by_domain(self, domain: str) -> Optional[int]:
        """Find contractor by domain"""
        if not domain:
            return None
        cursor = self.conn.execute(
            "SELECT id FROM contractors WHERE primary_domain = ?",
            (domain,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def find_contractor_by_name(self, name: str, state: str = None) -> Optional[int]:
        """Find contractor by normalized name (optionally with state)"""
        if not name:
            return None
        normalized = normalize_name(name)
        if state:
            cursor = self.conn.execute(
                "SELECT id FROM contractors WHERE normalized_name = ? AND state = ?",
                (normalized, state)
            )
        else:
            cursor = self.conn.execute(
                "SELECT id FROM contractors WHERE normalized_name = ?",
                (normalized,)
            )
        row = cursor.fetchone()
        return row[0] if row else None

    def add_oem_certification(self, contractor_id: int, oem_name: str, tier: str = None,
                             scraped_from_zip: str = None) -> bool:
        """Add OEM certification record"""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip)
                VALUES (?, ?, ?, ?)
            """, (contractor_id, oem_name, tier, scraped_from_zip))
            return True
        except Exception as e:
            print(f"   ⚠️ Error adding certification: {e}")
            return False

    def import_oem_file(self, oem_name: str, config: dict) -> dict:
        """Import a single OEM CSV file"""
        file_path = OEM_DATA_DIR / config["file"]
        if not file_path.exists():
            print(f"   ⚠️ File not found: {file_path}")
            return {"loaded": 0, "matched": 0, "unmatched": 0}

        stats = {"loaded": 0, "matched": 0, "unmatched": 0, "new_certs": 0}

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["loaded"] += 1

                # Extract fields
                phone = normalize_phone(row.get(config["phone_col"], ""))
                domain = normalize_domain(row.get(config["domain_col"], ""))
                name = row.get(config["name_col"], "")
                tier = row.get(config.get("tier_col", ""), "") if config.get("tier_col") else None
                state = row.get("state", "")
                scraped_zip = row.get("scraped_from_zip", "")

                # Find matching contractor
                contractor_id = None
                match_type = None

                # Try phone first (most reliable)
                if phone:
                    contractor_id = self.find_contractor_by_phone(phone)
                    if contractor_id:
                        match_type = "phone"
                        self.stats["matched_by_phone"] += 1

                # Try domain next
                if not contractor_id and domain:
                    contractor_id = self.find_contractor_by_domain(domain)
                    if contractor_id:
                        match_type = "domain"
                        self.stats["matched_by_domain"] += 1

                # Try name with state as fallback
                if not contractor_id and name:
                    contractor_id = self.find_contractor_by_name(name, state)
                    if contractor_id:
                        match_type = "name"
                        self.stats["matched_by_name"] += 1

                if contractor_id:
                    stats["matched"] += 1
                    if self.add_oem_certification(contractor_id, oem_name, tier, scraped_zip):
                        stats["new_certs"] += 1
                        self.stats["new_certifications"] += 1
                else:
                    stats["unmatched"] += 1
                    self.stats["unmatched"] += 1

        self.stats["oem_records_loaded"] += stats["loaded"]
        return stats

    def import_all_oems(self):
        """Import all OEM data files"""
        print("\n" + "=" * 70)
        print("PHASE 1: OEM DATA IMPORT")
        print("=" * 70)

        total_contractors = self.get_contractor_count()
        print(f"\n📊 Database: {total_contractors:,} contractors")
        print(f"📂 OEM Data: {OEM_DATA_DIR}\n")

        for oem_name, config in OEM_FILES.items():
            category = config["category"].upper()
            print(f"🔄 Importing {oem_name} ({category})...")
            stats = self.import_oem_file(oem_name, config)

            if stats["loaded"] > 0:
                match_rate = (stats["matched"] / stats["loaded"]) * 100
                print(f"   ✅ {stats['loaded']:,} records → {stats['matched']:,} matched ({match_rate:.1f}%)")
                print(f"      New certifications: {stats['new_certs']:,}")
            print()

        self.conn.commit()

        print("\n" + "-" * 70)
        print("IMPORT SUMMARY")
        print("-" * 70)
        print(f"   Total OEM records: {self.stats['oem_records_loaded']:,}")
        print(f"   Matched by phone:  {self.stats['matched_by_phone']:,}")
        print(f"   Matched by domain: {self.stats['matched_by_domain']:,}")
        print(f"   Matched by name:   {self.stats['matched_by_name']:,}")
        print(f"   Unmatched:         {self.stats['unmatched']:,}")
        print(f"   New certifications: {self.stats['new_certifications']:,}")

    def calculate_icp_scores(self) -> dict:
        """Calculate enhanced ICP scores with OEM data"""
        print("\n" + "=" * 70)
        print("PHASE 2: ICP SCORING")
        print("=" * 70)

        # Get all contractors with their data
        cursor = self.conn.execute("""
            SELECT
                c.id,
                c.company_name,
                c.primary_phone,
                c.primary_email,
                c.primary_domain,
                c.city,
                c.state,
                c.zip,
                -- License counts by category
                (SELECT COUNT(DISTINCT license_category) FROM licenses l WHERE l.contractor_id = c.id) as license_count,
                (SELECT COUNT(*) FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'HVAC') as hvac_license_count,
                (SELECT COUNT(*) FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'ELECTRICAL') as electrical_license_count,
                (SELECT COUNT(*) FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'PLUMBING') as plumbing_license_count,
                (SELECT COUNT(*) FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'ROOFING') as roofing_license_count,
                (SELECT COUNT(*) FROM licenses l WHERE l.contractor_id = c.id AND l.license_category IN ('SOLAR', 'ENERGY')) as solar_license_count,
                -- OEM counts by category
                (SELECT COUNT(*) FROM oem_certifications o WHERE o.contractor_id = c.id) as total_oem_count,
                (SELECT GROUP_CONCAT(oem_name, ', ') FROM oem_certifications o WHERE o.contractor_id = c.id) as oem_list,
                -- SPW data
                (SELECT SUM(kw_installed) FROM spw_rankings s WHERE s.contractor_id = c.id) as spw_kw_installed,
                (SELECT COUNT(*) FROM spw_rankings s WHERE s.contractor_id = c.id) as spw_list_count
            FROM contractors c
        """)

        contractors_data = []
        for row in cursor:
            contractors_data.append(dict(row))

        print(f"\n📊 Processing {len(contractors_data):,} contractors...")

        # Calculate scores
        scored = []
        for c in contractors_data:
            # Parse OEM list into categories
            oem_list = c.get("oem_list", "") or ""
            oems = [o.strip() for o in oem_list.split(",") if o.strip()]

            hvac_oems = [o for o in oems if o in ["Carrier", "Mitsubishi", "Rheem", "Trane", "York"]]
            generator_oems = [o for o in oems if o in ["Generac", "Briggs & Stratton", "Cummins"]]
            solar_oems = [o for o in oems if o in ["Enphase", "SMA"]]
            battery_oems = [o for o in oems if o in ["Tesla"]]

            # Calculate category scores (0-100)

            # 1. MEP+E Score (35%) - Multi-license + OEM
            mep_e_score = 0
            license_count = c.get("license_count", 0) or 0
            if license_count >= 4:
                mep_e_score = 100
            elif license_count >= 3:
                mep_e_score = 80
            elif license_count >= 2:
                mep_e_score = 60
            elif license_count >= 1:
                mep_e_score = 30

            # Boost for HVAC + Electrical combo
            if c.get("hvac_license_count", 0) and c.get("electrical_license_count", 0):
                mep_e_score = min(100, mep_e_score + 20)

            # 2. Multi-OEM Score (25%)
            total_oem = c.get("total_oem_count", 0) or 0
            if total_oem >= 3:
                multi_oem_score = 100
            elif total_oem >= 2:
                multi_oem_score = 70
            elif total_oem >= 1:
                multi_oem_score = 40
            else:
                multi_oem_score = 0

            # 3. Renewable Readiness Score (25%) - Solar/Battery focus
            renewable_score = 0
            if c.get("solar_license_count", 0) or solar_oems or battery_oems:
                renewable_score = 60
            if solar_oems and battery_oems:  # Both
                renewable_score = 100
            elif c.get("spw_kw_installed", 0):  # SPW presence
                renewable_score = max(renewable_score, 80)

            # 4. Asset-Centric Score (15%) - HVAC + Generator = monitoring opportunity
            asset_score = 0
            if hvac_oems:
                asset_score += 40
            if generator_oems:
                asset_score += 40
            if c.get("hvac_license_count", 0):
                asset_score += 20
            asset_score = min(100, asset_score)

            # Calculate weighted total
            icp_score = int(
                mep_e_score * 0.35 +
                multi_oem_score * 0.25 +
                renewable_score * 0.25 +
                asset_score * 0.15
            )

            # Determine tier
            if icp_score >= 80:
                icp_tier = "PLATINUM"
            elif icp_score >= 60:
                icp_tier = "GOLD"
            elif icp_score >= 40:
                icp_tier = "SILVER"
            else:
                icp_tier = "BRONZE"

            # Build OEM tiers dict
            oem_tiers = {}
            cursor2 = self.conn.execute(
                "SELECT oem_name, certification_tier FROM oem_certifications WHERE contractor_id = ?",
                (c["id"],)
            )
            for cert in cursor2:
                oem_tiers[cert[0]] = cert[1] or "Standard"

            scored.append({
                # Core fields
                "id": c["id"],
                "company_name": c["company_name"],
                "domain": c.get("primary_domain", ""),
                "phone": c.get("primary_phone", ""),
                "email": c.get("primary_email", ""),
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "zip": c.get("zip", ""),

                # License capabilities
                "license_count": license_count,
                "has_hvac": bool(c.get("hvac_license_count", 0)),
                "has_electrical": bool(c.get("electrical_license_count", 0)),
                "has_plumbing": bool(c.get("plumbing_license_count", 0)),
                "has_roofing": bool(c.get("roofing_license_count", 0)),
                "has_solar": bool(c.get("solar_license_count", 0) or solar_oems or battery_oems),
                "has_battery": bool(battery_oems),
                "has_generator": bool(generator_oems),

                # OEM data (sales-agent format)
                "oems_certified": oems,  # Will be JSON
                "oem_tiers": oem_tiers,  # Will be JSON
                "total_oem_count": total_oem,
                "hvac_oem_count": len(hvac_oems),
                "solar_oem_count": len(solar_oems),
                "battery_oem_count": len(battery_oems),
                "generator_oem_count": len(generator_oems),

                # ICP scores
                "icp_score": icp_score,
                "icp_tier": icp_tier,
                "mep_e_score": mep_e_score,
                "multi_oem_score": multi_oem_score,
                "renewable_readiness_score": renewable_score,
                "asset_centric_score": asset_score,

                # SPW data
                "spw_kw_installed": c.get("spw_kw_installed", 0) or 0,
                "spw_list_count": c.get("spw_list_count", 0) or 0,
            })

        # Sort by ICP score
        scored.sort(key=lambda x: (-x["icp_score"], -x["total_oem_count"]))

        # Print tier distribution
        tier_counts = {"PLATINUM": 0, "GOLD": 0, "SILVER": 0, "BRONZE": 0}
        for s in scored:
            tier_counts[s["icp_tier"]] += 1

        print("\n📊 ICP Tier Distribution:")
        for tier, count in tier_counts.items():
            pct = (count / len(scored)) * 100 if scored else 0
            print(f"   {tier}: {count:,} ({pct:.1f}%)")

        return scored

    def export_sales_agent_format(self, scored_data: list):
        """Export in sales-agent compatible format"""
        print("\n" + "=" * 70)
        print("PHASE 3: EXPORT FOR SALES-AGENT")
        print("=" * 70)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export full CSV
        csv_path = OUTPUT_DIR / f"sales_agent_leads_{timestamp}.csv"

        # Define sales-agent compatible columns
        columns = [
            "company_name", "domain", "phone", "email", "city", "state", "zip",
            "license_count", "has_hvac", "has_electrical", "has_plumbing",
            "has_roofing", "has_solar", "has_battery", "has_generator",
            "oems_certified", "oem_tiers", "total_oem_count",
            "hvac_oem_count", "solar_oem_count", "battery_oem_count", "generator_oem_count",
            "icp_score", "icp_tier", "mep_e_score", "multi_oem_score",
            "renewable_readiness_score", "asset_centric_score",
            "spw_kw_installed", "spw_list_count"
        ]

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for row in scored_data:
                # Convert lists/dicts to JSON strings for CSV
                row_copy = row.copy()
                row_copy["oems_certified"] = json.dumps(row["oems_certified"])
                row_copy["oem_tiers"] = json.dumps(row["oem_tiers"])
                writer.writerow({k: row_copy.get(k, "") for k in columns})

        print(f"\n✅ Full export: {csv_path}")
        print(f"   Records: {len(scored_data):,}")

        # Export top 1000 leads as JSON
        top_1000 = scored_data[:1000]
        json_path = OUTPUT_DIR / f"top_1000_leads_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(top_1000, f, indent=2)

        print(f"\n✅ Top 1000 JSON: {json_path}")

        # Export tier-specific CSVs
        for tier in ["PLATINUM", "GOLD", "SILVER"]:
            tier_data = [d for d in scored_data if d["icp_tier"] == tier]
            if tier_data:
                tier_path = OUTPUT_DIR / f"{tier.lower()}_tier_leads_{timestamp}.csv"
                with open(tier_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    for row in tier_data:
                        row_copy = row.copy()
                        row_copy["oems_certified"] = json.dumps(row["oems_certified"])
                        row_copy["oem_tiers"] = json.dumps(row["oem_tiers"])
                        writer.writerow({k: row_copy.get(k, "") for k in columns})
                print(f"✅ {tier} tier: {tier_path} ({len(tier_data):,} records)")

        # Export multi-OEM leads (2+ OEMs)
        multi_oem = [d for d in scored_data if d["total_oem_count"] >= 2]
        if multi_oem:
            multi_path = OUTPUT_DIR / f"multi_oem_leads_{timestamp}.csv"
            with open(multi_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in multi_oem:
                    row_copy = row.copy()
                    row_copy["oems_certified"] = json.dumps(row["oems_certified"])
                    row_copy["oem_tiers"] = json.dumps(row["oem_tiers"])
                    writer.writerow({k: row_copy.get(k, "") for k in columns})
            print(f"✅ Multi-OEM (2+): {multi_path} ({len(multi_oem):,} records)")

        return csv_path

    def print_top_leads(self, scored_data: list, n: int = 25):
        """Print top N leads"""
        print("\n" + "=" * 70)
        print(f"TOP {n} PRIORITY TARGETS")
        print("=" * 70)

        print(f"\n{'Rank':<5} {'Company':<35} {'ICP':<5} {'OEMs':<30} {'State':<6}")
        print("-" * 85)

        for i, lead in enumerate(scored_data[:n], 1):
            oems = ", ".join(lead["oems_certified"][:3])
            if len(lead["oems_certified"]) > 3:
                oems += f" +{len(lead['oems_certified'])-3}"

            print(f"{i:<5} {lead['company_name'][:33]:<35} {lead['icp_score']:<5} {oems[:28]:<30} {lead['state']:<6}")

    def run(self):
        """Execute full pipeline"""
        print("\n" + "=" * 70)
        print("UNIFIED OEM IMPORT & SALES-AGENT EXPORT")
        print("=" * 70)
        print(f"Started: {datetime.now().isoformat()}")

        self.connect()

        try:
            # Phase 1: Import OEM data
            self.import_all_oems()

            # Phase 2: Calculate ICP scores
            scored_data = self.calculate_icp_scores()

            # Phase 3: Export for sales-agent
            self.export_sales_agent_format(scored_data)

            # Show top leads
            self.print_top_leads(scored_data, 25)

            print("\n" + "=" * 70)
            print("✅ COMPLETE!")
            print("=" * 70)
            print(f"\n📁 Output directory: {OUTPUT_DIR}")
            print(f"⏱️  Finished: {datetime.now().isoformat()}")

        finally:
            self.close()


if __name__ == "__main__":
    processor = UnifiedOEMProcessor()
    processor.run()
