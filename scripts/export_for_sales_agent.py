#!/usr/bin/env python3
"""
Export Clean Leads for Sales-Agent
===================================
Creates a deduplicated, consolidated export file that matches
the sales-agent Lead model schema.

COMPANY NAME IS THE ANCHOR - every record MUST have a company name.

Output: output/sales_agent_export/clean_leads_YYYYMMDD.csv
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import re


class SalesAgentExporter:
    """Export contractor leads in sales-agent compatible format."""

    def __init__(self, db_path: str = "output/pipeline.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("output/sales_agent_export")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def normalize_phone(self, phone: str) -> str:
        """Normalize phone to 10 digits."""
        if not phone:
            return ""
        digits = re.sub(r'\D', '', str(phone))
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        return digits if len(digits) == 10 else ""

    def get_oem_data(self) -> pd.DataFrame:
        """Get OEM certification data with counts by category."""
        query = """
        SELECT
            c.id,
            c.company_name,
            c.normalized_name,
            c.primary_phone as phone,
            c.primary_email as email,
            c.website_url as website,
            c.primary_domain as domain,
            c.city,
            c.state,
            c.zip,
            -- License flags (from licenses table)
            EXISTS(SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'HVAC') as has_hvac,
            EXISTS(SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'ELECTRICAL') as has_electrical,
            EXISTS(SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'PLUMBING') as has_plumbing,
            EXISTS(SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'SOLAR') as has_solar,
            EXISTS(SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.license_category = 'ROOFING') as has_roofing,
            -- OEM certifications (grouped by category)
            GROUP_CONCAT(DISTINCT o.oem_name) as oems_certified
        FROM contractors c
        LEFT JOIN oem_certifications o ON c.id = o.contractor_id
        WHERE c.company_name IS NOT NULL
          AND c.company_name != ''
          AND c.is_deleted = 0
        GROUP BY c.id
        """
        df = pd.read_sql_query(query, self.conn)
        return df

    def categorize_oems(self, oems_str: str) -> dict:
        """Categorize OEMs into HVAC, Solar, Battery, Generator, Smart Panel."""
        if not oems_str:
            return {
                'hvac_oems': [],
                'solar_oems': [],
                'battery_oems': [],
                'generator_oems': [],
                'smart_panel_oems': []
            }

        oems = [o.strip() for o in oems_str.split(',')]

        # OEM category mappings
        hvac_brands = {'Carrier', 'Trane', 'York', 'Rheem', 'Mitsubishi', 'Mitsubishi Electric'}
        solar_brands = {'Enphase', 'SolarEdge', 'SMA', 'Fronius', 'GoodWe', 'Growatt', 'Sungrow', 'ABB', 'Delta', 'Tigo'}
        battery_brands = {'Tesla', 'SimpliPhi', 'Sol-Ark', 'SolArk'}
        generator_brands = {'Generac', 'Briggs & Stratton', 'Cummins', 'Kohler'}
        smart_panel_brands = {'Schneider Electric', 'Schneider'}

        categorized = {
            'hvac_oems': [o for o in oems if o in hvac_brands],
            'solar_oems': [o for o in oems if o in solar_brands],
            'battery_oems': [o for o in oems if o in battery_brands],
            'generator_oems': [o for o in oems if o in generator_brands],
            'smart_panel_oems': [o for o in oems if o in smart_panel_brands]
        }
        return categorized

    def calculate_mep_e_score(self, row: pd.Series) -> int:
        """Calculate MEP+E score (0-100) based on capabilities."""
        score = 0

        # License-based scoring (40 points max)
        if row.get('has_hvac'): score += 10
        if row.get('has_electrical'): score += 10
        if row.get('has_plumbing'): score += 10
        if row.get('has_solar'): score += 10

        # OEM diversity scoring (40 points max)
        oem_categories = row.get('oem_category_count', 0)
        score += min(oem_categories * 10, 40)

        # Contact completeness bonus (20 points max)
        if row.get('phone'): score += 10
        if row.get('email'): score += 10

        return min(score, 100)

    def export_clean_leads(self) -> Path:
        """Export all clean leads for sales-agent."""
        print("=" * 60)
        print("EXPORTING CLEAN LEADS FOR SALES-AGENT")
        print("=" * 60)

        # Get base data
        print("\n1. Fetching contractor data...")
        df = self.get_oem_data()
        print(f"   → {len(df)} contractors with company names")

        # Normalize phone numbers
        print("\n2. Normalizing phone numbers...")
        df['phone'] = df['phone'].apply(self.normalize_phone)

        # Categorize OEMs
        print("\n3. Categorizing OEM certifications...")
        oem_categories = df['oems_certified'].apply(self.categorize_oems)
        df['hvac_oem_count'] = oem_categories.apply(lambda x: len(x['hvac_oems']))
        df['solar_oem_count'] = oem_categories.apply(lambda x: len(x['solar_oems']))
        df['battery_oem_count'] = oem_categories.apply(lambda x: len(x['battery_oems']))
        df['generator_oem_count'] = oem_categories.apply(lambda x: len(x['generator_oems']))
        df['smart_panel_oem_count'] = oem_categories.apply(lambda x: len(x['smart_panel_oems']))

        # Calculate total OEM count and category count
        df['total_oem_count'] = df['hvac_oem_count'] + df['solar_oem_count'] + df['battery_oem_count'] + df['generator_oem_count'] + df['smart_panel_oem_count']
        df['oem_category_count'] = (
            (df['hvac_oem_count'] > 0).astype(int) +
            (df['solar_oem_count'] > 0).astype(int) +
            (df['battery_oem_count'] > 0).astype(int) +
            (df['generator_oem_count'] > 0).astype(int) +
            (df['smart_panel_oem_count'] > 0).astype(int)
        )

        # Calculate MEP+E score
        print("\n4. Calculating MEP+E scores...")
        df['mep_e_score'] = df.apply(self.calculate_mep_e_score, axis=1)

        # Create output dataframe with sales-agent schema
        print("\n5. Mapping to sales-agent schema...")
        output = pd.DataFrame({
            # Core identification (COMPANY NAME IS ANCHOR)
            'company_name': df['company_name'],

            # Contact info
            'contact_phone': df['phone'],
            'contact_email': df['email'],
            'company_website': df['website'],

            # Location
            'city': df['city'],
            'state': df['state'],
            'zip': df['zip'],

            # OEM counts by category
            'hvac_oem_count': df['hvac_oem_count'],
            'solar_oem_count': df['solar_oem_count'],
            'battery_oem_count': df['battery_oem_count'],
            'generator_oem_count': df['generator_oem_count'],
            'smart_panel_oem_count': df['smart_panel_oem_count'],
            'iot_oem_count': 0,  # Not tracked yet
            'total_oem_count': df['total_oem_count'],

            # OEM details (JSON)
            'oems_certified': df['oems_certified'].apply(lambda x: x.split(',') if x else []),

            # Capability flags
            'has_hvac': df['has_hvac'].astype(bool),
            'has_solar': df['has_solar'].astype(bool),
            'has_electrical': df['has_electrical'].astype(bool),
            'has_generator': df['generator_oem_count'] > 0,
            'has_battery': df['battery_oem_count'] > 0,

            # Scores
            'mep_e_score': df['mep_e_score'],
        })

        # Filter to only records with company name (THE ANCHOR)
        output = output[output['company_name'].notna() & (output['company_name'] != '')]

        # Quality tiers
        has_phone = output['contact_phone'].notna() & (output['contact_phone'] != '')
        has_email = output['contact_email'].notna() & (output['contact_email'] != '')

        gold = output[has_phone & has_email]
        silver_phone = output[has_phone & ~has_email]
        silver_email = output[~has_phone & has_email]
        bronze = output[~has_phone & ~has_email]

        print(f"\n6. Quality tier breakdown:")
        print(f"   GOLD (phone + email): {len(gold)}")
        print(f"   SILVER (phone only): {len(silver_phone)}")
        print(f"   SILVER (email only): {len(silver_email)}")
        print(f"   BRONZE (name only): {len(bronze)}")

        # Sort by quality: GOLD first, then by MEP+E score
        output['_quality_rank'] = 0
        output.loc[has_phone & has_email, '_quality_rank'] = 3
        output.loc[has_phone & ~has_email, '_quality_rank'] = 2
        output.loc[~has_phone & has_email, '_quality_rank'] = 1

        output = output.sort_values(['_quality_rank', 'mep_e_score'], ascending=[False, False])
        output = output.drop('_quality_rank', axis=1)

        # Save files
        print("\n7. Saving export files...")

        # Full export
        full_path = self.output_dir / f"clean_leads_full_{self.timestamp}.csv"
        output.to_csv(full_path, index=False)
        print(f"   ✓ Full export: {full_path.name} ({len(output)} records)")

        # Gold tier only (for immediate outreach)
        if len(gold) > 0:
            gold_path = self.output_dir / f"clean_leads_GOLD_{self.timestamp}.csv"
            gold.to_csv(gold_path, index=False)
            print(f"   ✓ GOLD tier: {gold_path.name} ({len(gold)} records)")

        # Silver tier (for enrichment)
        silver_combined = pd.concat([silver_phone, silver_email])
        if len(silver_combined) > 0:
            silver_path = self.output_dir / f"clean_leads_SILVER_{self.timestamp}.csv"
            silver_combined.to_csv(silver_path, index=False)
            print(f"   ✓ SILVER tier: {silver_path.name} ({len(silver_combined)} records)")

        # Summary stats
        print("\n" + "=" * 60)
        print("EXPORT SUMMARY")
        print("=" * 60)
        print(f"  Total companies: {len(output)}")
        print(f"  With phone: {has_phone.sum()}")
        print(f"  With email: {has_email.sum()}")
        print(f"  With both: {len(gold)}")
        print(f"  With OEM certs: {(output['total_oem_count'] > 0).sum()}")
        print(f"  Multi-OEM (2+): {(output['total_oem_count'] >= 2).sum()}")
        print(f"\n  Files saved to: {self.output_dir}")

        return full_path

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    exporter = SalesAgentExporter()
    try:
        output_path = exporter.export_clean_leads()
        print(f"\n✅ Export complete: {output_path}")
    finally:
        exporter.close()


if __name__ == "__main__":
    main()
