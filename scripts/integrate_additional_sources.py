#!/usr/bin/env python3
"""
Integrate Additional Data Sources into Pipeline Database

Integrates:
1. FL Roofers with emails (enrich existing FL contractors)
2. SPW Commercial top solar installers (tag high-value contractors)

These are ENRICHMENT sources - they add data to existing contractors,
not create new ones.

Usage:
    python3 scripts/integrate_additional_sources.py
    python3 scripts/integrate_additional_sources.py --source fl_roofers
    python3 scripts/integrate_additional_sources.py --source spw
"""

import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import PipelineDB, normalize_company_name, normalize_email

# Data source files
FL_ROOFERS_FILE = Path(__file__).parent.parent / "output" / "enrichment" / "fl_roofers_with_emails_20251125_2232.csv"
SPW_COMMERCIAL_FILE = Path(__file__).parent.parent / "output" / "enrichment" / "spw_commercial_master_20251125_2232.csv"
DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"


def fuzzy_match(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Check if two company names are similar enough to be a match."""
    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)
    if not n1 or not n2:
        return False
    return SequenceMatcher(None, n1, n2).ratio() >= threshold


def integrate_fl_roofers():
    """
    Integrate FL Roofers data to enrich existing FL contractors.

    Strategy: Match by normalized company name, add email/contact if missing.
    """
    print("\n" + "=" * 70)
    print("INTEGRATING FL ROOFERS DATA")
    print("=" * 70)

    if not FL_ROOFERS_FILE.exists():
        print(f"❌ File not found: {FL_ROOFERS_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load all FL contractors
    cursor.execute("""
        SELECT c.id, c.company_name, c.normalized_name, c.primary_email
        FROM contractors c
        JOIN licenses l ON c.id = l.contractor_id
        WHERE l.state = 'FL'
        GROUP BY c.id
    """)
    fl_contractors = {row[2]: {'id': row[0], 'name': row[1], 'email': row[3]}
                      for row in cursor.fetchall() if row[2]}

    print(f"📋 FL contractors in database: {len(fl_contractors):,}")

    # Process FL roofers
    matched = 0
    emails_added = 0
    contacts_added = 0

    with open(FL_ROOFERS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        roofers = list(reader)

    print(f"📋 FL roofers to integrate: {len(roofers):,}")

    for roofer in roofers:
        company = roofer.get('company_name', '')
        email = normalize_email(roofer.get('email', ''))
        contact_name = roofer.get('contact_name', '')
        city = roofer.get('city', '')

        if not company:
            continue

        norm_name = normalize_company_name(company)

        # Try exact normalized match first
        if norm_name in fl_contractors:
            contractor = fl_contractors[norm_name]
            matched += 1

            # Add email if contractor doesn't have one
            if email and not contractor['email']:
                cursor.execute("""
                    UPDATE contractors SET primary_email = ? WHERE id = ?
                """, (email, contractor['id']))
                emails_added += 1

            # Add contact if we have name
            if contact_name:
                cursor.execute("""
                    INSERT OR IGNORE INTO contacts
                    (contractor_id, name, email, source, confidence)
                    VALUES (?, ?, ?, 'FL_Roofers', 80)
                """, (contractor['id'], contact_name, email))
                contacts_added += 1

            continue

        # Try fuzzy matching (slower)
        for norm, contractor in fl_contractors.items():
            if fuzzy_match(norm_name, norm, 0.90):  # High threshold
                matched += 1

                if email and not contractor['email']:
                    cursor.execute("""
                        UPDATE contractors SET primary_email = ? WHERE id = ?
                    """, (email, contractor['id']))
                    emails_added += 1

                if contact_name:
                    cursor.execute("""
                        INSERT OR IGNORE INTO contacts
                        (contractor_id, name, email, source, confidence)
                        VALUES (?, ?, ?, 'FL_Roofers', 75)
                    """, (contractor['id'], contact_name, email))
                    contacts_added += 1

                break

    conn.commit()
    conn.close()

    print(f"\n✅ Results:")
    print(f"   Matched to existing: {matched:,}")
    print(f"   Emails added:        {emails_added:,}")
    print(f"   Contacts added:      {contacts_added:,}")


def integrate_spw_commercial():
    """
    Integrate SPW Commercial data to tag high-value solar contractors.

    Strategy: Match by company name + state, add SPW ranking to database.
    """
    print("\n" + "=" * 70)
    print("INTEGRATING SPW COMMERCIAL DATA")
    print("=" * 70)

    if not SPW_COMMERCIAL_FILE.exists():
        print(f"❌ File not found: {SPW_COMMERCIAL_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure spw_rankings table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spw_rankings (
            id INTEGER PRIMARY KEY,
            contractor_id INTEGER REFERENCES contractors(id),
            company_name TEXT,
            list_name TEXT,
            rank_position INTEGER,
            kw_installed REAL,
            headquarters_state TEXT,
            year INTEGER DEFAULT 2024,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(contractor_id, list_name)
        )
    """)

    # Load all contractors (for matching)
    cursor.execute("""
        SELECT c.id, c.company_name, c.normalized_name, c.state
        FROM contractors c
    """)
    all_contractors = {}
    for row in cursor.fetchall():
        key = (normalize_company_name(row[1]), row[3])  # (normalized_name, state)
        all_contractors[key] = {'id': row[0], 'name': row[1]}

    print(f"📋 Total contractors in database: {len(all_contractors):,}")

    # Process SPW data
    with open(SPW_COMMERCIAL_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        spw_companies = list(reader)

    print(f"📋 SPW Commercial companies: {len(spw_companies):,}")

    matched = 0
    added = 0

    for company in spw_companies:
        name = company.get('company_name', '')
        state = company.get('state', '')
        rank = int(company.get('rank', 0)) if company.get('rank') else 0
        kw = float(company.get('kw_installed', 0)) if company.get('kw_installed') else 0

        if not name:
            continue

        norm_name = normalize_company_name(name)
        key = (norm_name, state)

        # Try exact match first
        contractor = all_contractors.get(key)

        # If no exact match, try fuzzy
        if not contractor:
            for (n, s), c in all_contractors.items():
                if s == state and fuzzy_match(norm_name, n, 0.85):
                    contractor = c
                    break

        if contractor:
            matched += 1
            cursor.execute("""
                INSERT OR REPLACE INTO spw_rankings
                (contractor_id, company_name, list_name, rank_position, kw_installed, headquarters_state)
                VALUES (?, ?, 'SPW_Commercial', ?, ?, ?)
            """, (contractor['id'], name, rank, kw, state))
            added += 1
        else:
            # SPW company not in our database - create new record
            cursor.execute("""
                INSERT INTO contractors (company_name, normalized_name, state)
                VALUES (?, ?, ?)
            """, (name, norm_name, state))
            new_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO spw_rankings
                (contractor_id, company_name, list_name, rank_position, kw_installed, headquarters_state)
                VALUES (?, ?, 'SPW_Commercial', ?, ?, ?)
            """, (new_id, name, rank, kw, state))
            added += 1

    conn.commit()

    # Show SPW contractors that are also in our state license data
    cursor.execute("""
        SELECT s.company_name, s.rank_position, s.kw_installed, s.headquarters_state,
               GROUP_CONCAT(DISTINCT l.license_category) as categories
        FROM spw_rankings s
        JOIN contractors c ON s.contractor_id = c.id
        LEFT JOIN licenses l ON c.id = l.contractor_id
        GROUP BY s.id
        HAVING categories IS NOT NULL
        ORDER BY s.rank_position
        LIMIT 10
    """)
    cross_matches = cursor.fetchall()

    conn.close()

    print(f"\n✅ Results:")
    print(f"   Matched to existing: {matched:,}")
    print(f"   SPW rankings added:  {added:,}")

    if cross_matches:
        print(f"\n🏆 TOP SPW COMPANIES WITH STATE LICENSES:")
        for name, rank, kw, state, cats in cross_matches:
            print(f"   #{rank:>3} {name[:35]:35} ({state}) - {cats}")


def cross_enrich_contacts():
    """
    Cross-enrich contact data between states.

    CA has 99% phone, FL has 98% email - try to match contractors
    and fill in missing contact info.
    """
    print("\n" + "=" * 70)
    print("CROSS-ENRICHING CONTACT DATA")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find contractors with both FL and CA licenses (cross-state)
    cursor.execute("""
        SELECT c.id, c.company_name, c.primary_phone, c.primary_email
        FROM contractors c
        JOIN licenses l ON c.id = l.contractor_id
        GROUP BY c.id
        HAVING COUNT(DISTINCT l.state) >= 2
    """)
    cross_state = cursor.fetchall()
    print(f"📋 Cross-state contractors: {len(cross_state):,}")

    # For each cross-state contractor, check if we can fill phone/email
    phone_filled = 0
    email_filled = 0

    for c_id, name, phone, email in cross_state:
        if not phone or not email:
            # Check contacts table for additional info
            cursor.execute("""
                SELECT phone, email FROM contacts
                WHERE contractor_id = ? AND (phone != '' OR email != '')
            """, (c_id,))
            contacts = cursor.fetchall()

            for c_phone, c_email in contacts:
                if not phone and c_phone:
                    cursor.execute("UPDATE contractors SET primary_phone = ? WHERE id = ?",
                                   (c_phone, c_id))
                    phone_filled += 1
                    phone = c_phone

                if not email and c_email:
                    cursor.execute("UPDATE contractors SET primary_email = ? WHERE id = ?",
                                   (c_email, c_id))
                    email_filled += 1
                    email = c_email

    conn.commit()
    conn.close()

    print(f"\n✅ Cross-enrichment results:")
    print(f"   Phones filled:  {phone_filled:,}")
    print(f"   Emails filled:  {email_filled:,}")


def show_enrichment_summary():
    """Show summary of enrichment status."""
    print("\n" + "=" * 70)
    print("ENRICHMENT SUMMARY")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Overall stats
    cursor.execute("SELECT COUNT(*) FROM contractors")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_email != ''")
    with_email = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_phone != ''")
    with_phone = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_email != '' AND primary_phone != ''")
    with_both = cursor.fetchone()[0]

    # SPW tagged
    cursor.execute("SELECT COUNT(DISTINCT contractor_id) FROM spw_rankings")
    spw_tagged = cursor.fetchone()[0]

    # Contacts count
    cursor.execute("SELECT COUNT(*) FROM contacts")
    contacts = cursor.fetchone()[0]

    conn.close()

    print(f"Total contractors:     {total:,}")
    print(f"With email:            {with_email:,} ({with_email/total*100:.1f}%)")
    print(f"With phone:            {with_phone:,} ({with_phone/total*100:.1f}%)")
    print(f"With BOTH:             {with_both:,} ({with_both/total*100:.1f}%)")
    print(f"SPW ranked:            {spw_tagged:,}")
    print(f"Total contacts:        {contacts:,}")

    # What's still needed
    no_contact = total - with_email - with_phone + with_both
    print(f"\n⚠️ Still missing contact info: {no_contact:,} ({no_contact/total*100:.1f}%)")
    print(f"   → Need Hunter.io or website scraping for these")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Integrate additional data sources")
    parser.add_argument("--source", choices=['fl_roofers', 'spw', 'cross', 'all'],
                       default='all', help="Which source to integrate")

    args = parser.parse_args()

    if args.source in ['fl_roofers', 'all']:
        integrate_fl_roofers()

    if args.source in ['spw', 'all']:
        integrate_spw_commercial()

    if args.source in ['cross', 'all']:
        cross_enrich_contacts()

    show_enrichment_summary()
