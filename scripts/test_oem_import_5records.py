#!/usr/bin/env python3
"""
Test OEM import with 5 Generac records.
Verifies that:
1. New contractors are created with source_type='oem_dealer'
2. OEM certifications are added
3. Matching works (if any match existing contractors)
"""

import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "output" / "master" / "pipeline.db"
TEST_FILE = Path("/tmp/generac_test_5.csv")

def normalize_phone(phone: str) -> str:
    """Normalize phone to 10 digits"""
    import re
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""

def normalize_domain(domain: str) -> str:
    """Normalize domain"""
    import re
    if not domain:
        return ""
    domain = domain.lower().strip()
    domain = re.sub(r'^(https?://)?(www\.)?', '', domain)
    domain = domain.split('/')[0]
    return domain

def normalize_name(name: str) -> str:
    """Normalize company name"""
    import re
    if not name:
        return ""
    name = name.upper().strip()
    for suffix in [' LLC', ' INC', ' CORP', ' CO', ' LTD', ' LP', ' LLP', '.', ',']:
        name = name.replace(suffix, '')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def main():
    print("=" * 60)
    print("TEST: OEM Import with 5 Generac Records")
    print("=" * 60)

    # Get initial counts
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("SELECT COUNT(*) FROM contractors")
    initial_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'oem_dealer'")
    initial_oem_only = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'both'")
    initial_both = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM oem_certifications")
    initial_certs = cursor.fetchone()[0]

    print(f"\n📊 BEFORE Import:")
    print(f"   Total contractors:       {initial_count:,}")
    print(f"   source_type='oem_dealer': {initial_oem_only:,}")
    print(f"   source_type='both':       {initial_both:,}")
    print(f"   OEM certifications:       {initial_certs:,}")

    # Read test file
    print(f"\n📂 Reading test file: {TEST_FILE}")

    stats = {"matched": 0, "created": 0, "failed": 0}

    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            name = row.get("name", "")
            phone = normalize_phone(row.get("phone", ""))
            domain = normalize_domain(row.get("domain", ""))
            tier = row.get("tier", "")
            state = row.get("state", "").upper()
            city = row.get("city", "")
            zip_code = row.get("zip", "")
            street = row.get("street", "")
            website = row.get("website", "")
            scraped_zip = row.get("scraped_from_zip", "")

            print(f"\n{i}. {name} ({phone})")

            # Try to find matching contractor
            contractor_id = None
            match_type = None

            # Try phone
            if phone:
                cursor = conn.execute(
                    "SELECT id FROM contractors WHERE primary_phone = ?",
                    (phone,)
                )
                row_result = cursor.fetchone()
                if row_result:
                    contractor_id = row_result[0]
                    match_type = "phone"

            # Try domain
            if not contractor_id and domain:
                cursor = conn.execute(
                    "SELECT id FROM contractors WHERE primary_domain = ?",
                    (domain,)
                )
                row_result = cursor.fetchone()
                if row_result:
                    contractor_id = row_result[0]
                    match_type = "domain"

            # Try name
            if not contractor_id and name:
                normalized = normalize_name(name)
                cursor = conn.execute(
                    "SELECT id FROM contractors WHERE normalized_name = ? AND state = ?",
                    (normalized, state)
                )
                row_result = cursor.fetchone()
                if row_result:
                    contractor_id = row_result[0]
                    match_type = "name"

            if contractor_id:
                # Matched! Update source_type to 'both'
                print(f"   ✅ MATCHED (by {match_type}) → contractor_id={contractor_id}")
                conn.execute("""
                    UPDATE contractors SET source_type = 'both', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND source_type = 'state_license'
                """, (contractor_id,))
                stats["matched"] += 1
            else:
                # Create new contractor
                normalized = normalize_name(name)
                cursor = conn.execute("""
                    INSERT INTO contractors
                    (company_name, normalized_name, street, city, state, zip,
                     primary_phone, primary_domain, source_type, website_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'oem_dealer', ?)
                """, (name, normalized, street, city, state, zip_code, phone, domain, website))
                contractor_id = cursor.lastrowid
                print(f"   🆕 CREATED → contractor_id={contractor_id} (source_type='oem_dealer')")
                stats["created"] += 1

            # Add OEM certification
            conn.execute("""
                INSERT OR IGNORE INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip)
                VALUES (?, ?, ?, ?)
            """, (contractor_id, "Generac", tier, scraped_zip))

    conn.commit()

    # Get final counts
    cursor = conn.execute("SELECT COUNT(*) FROM contractors")
    final_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'oem_dealer'")
    final_oem_only = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'both'")
    final_both = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM oem_certifications")
    final_certs = cursor.fetchone()[0]

    print(f"\n📊 AFTER Import:")
    print(f"   Total contractors:       {final_count:,} (+{final_count - initial_count})")
    print(f"   source_type='oem_dealer': {final_oem_only:,} (+{final_oem_only - initial_oem_only})")
    print(f"   source_type='both':       {final_both:,} (+{final_both - initial_both})")
    print(f"   OEM certifications:       {final_certs:,} (+{final_certs - initial_certs})")

    print(f"\n📈 Import Stats:")
    print(f"   Matched existing:  {stats['matched']}")
    print(f"   Created new:       {stats['created']}")

    # Verify the new contractors
    print(f"\n🔍 Verifying new OEM contractors:")
    cursor = conn.execute("""
        SELECT c.id, c.company_name, c.primary_phone, c.source_type, c.state,
               o.oem_name, o.certification_tier
        FROM contractors c
        JOIN oem_certifications o ON c.id = o.contractor_id
        WHERE o.oem_name = 'Generac'
        ORDER BY c.id DESC
        LIMIT 5
    """)

    for row in cursor:
        print(f"   ID={row[0]}: {row[1]} ({row[3]}) - {row[5]} {row[6]}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
