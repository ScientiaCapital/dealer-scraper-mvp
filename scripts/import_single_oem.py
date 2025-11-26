#!/usr/bin/env python3
"""
Import a single OEM's data to test before full import.
Usage: python import_single_oem.py Generac
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.unified_oem_import_export import UnifiedOEMProcessor, OEM_FILES

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_single_oem.py <OEM_NAME>")
        print(f"Available OEMs: {', '.join(OEM_FILES.keys())}")
        sys.exit(1)

    oem_name = sys.argv[1]

    if oem_name not in OEM_FILES:
        print(f"❌ Unknown OEM: {oem_name}")
        print(f"Available OEMs: {', '.join(OEM_FILES.keys())}")
        sys.exit(1)

    print(f"\n🎯 Importing single OEM: {oem_name}")
    print("=" * 60)

    processor = UnifiedOEMProcessor()
    processor.connect()

    try:
        # Get initial counts
        initial_count = processor.get_contractor_count()
        cursor = processor.conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'oem_dealer'")
        initial_oem_only = cursor.fetchone()[0]
        cursor = processor.conn.execute("SELECT COUNT(*) FROM oem_certifications")
        initial_certs = cursor.fetchone()[0]

        print(f"\n📊 BEFORE Import:")
        print(f"   Total contractors:       {initial_count:,}")
        print(f"   source_type='oem_dealer': {initial_oem_only:,}")
        print(f"   OEM certifications:       {initial_certs:,}")

        # Import single OEM
        config = OEM_FILES[oem_name]
        print(f"\n🔄 Importing {oem_name} ({config['category'].upper()})...")
        stats = processor.import_oem_file(oem_name, config)

        processor.conn.commit()

        # Get final counts
        final_count = processor.get_contractor_count()
        cursor = processor.conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'oem_dealer'")
        final_oem_only = cursor.fetchone()[0]
        cursor = processor.conn.execute("SELECT COUNT(*) FROM contractors WHERE source_type = 'both'")
        final_both = cursor.fetchone()[0]
        cursor = processor.conn.execute("SELECT COUNT(*) FROM oem_certifications")
        final_certs = cursor.fetchone()[0]

        print(f"\n📊 AFTER Import:")
        print(f"   Total contractors:       {final_count:,} (+{final_count - initial_count})")
        print(f"   source_type='oem_dealer': {final_oem_only:,} (+{final_oem_only - initial_oem_only})")
        print(f"   source_type='both':       {final_both:,}")
        print(f"   OEM certifications:       {final_certs:,} (+{final_certs - initial_certs})")

        print(f"\n📈 Import Stats:")
        print(f"   Loaded:   {stats['loaded']:,}")
        print(f"   Matched:  {stats['matched']:,}")
        print(f"   Created:  {stats.get('created', 0):,}")
        print(f"   New certs: {stats['new_certs']:,}")

        # Sample new contractors
        print(f"\n🔍 Sample new {oem_name} contractors (last 5):")
        cursor = processor.conn.execute(f"""
            SELECT c.id, c.company_name, c.state, c.source_type, o.certification_tier
            FROM contractors c
            JOIN oem_certifications o ON c.id = o.contractor_id
            WHERE o.oem_name = ?
            ORDER BY c.id DESC
            LIMIT 5
        """, (oem_name,))
        for row in cursor:
            print(f"   ID={row[0]}: {row[1]} ({row[3]}) - {row[2]} - {row[4]}")

    finally:
        processor.close()

    print("\n" + "=" * 60)
    print("✅ SINGLE OEM IMPORT COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
