#!/usr/bin/env python3
"""
Data Quality Analysis for the Pipeline Database

Comprehensive review of FL + CA + TX contractor data.
"""

import sqlite3
from pathlib import Path

def analyze_data_quality():
    db_path = Path(__file__).parent.parent / 'output' / 'pipeline.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print('=' * 70)
    print('DATA QUALITY REVIEW - THE BIG 3 STATES (FL + CA + TX)')
    print('=' * 70)

    # 1. License Type Distribution
    print('\nLICENSE CATEGORY DISTRIBUTION')
    print('-' * 50)
    cursor.execute("""
        SELECT l.license_category, l.state, COUNT(DISTINCT l.contractor_id) as contractors
        FROM licenses l
        WHERE l.license_category != ''
        GROUP BY l.license_category, l.state
        ORDER BY contractors DESC
    """)
    results = cursor.fetchall()

    # Group by category
    categories = {}
    for cat, state, count in results:
        if cat not in categories:
            categories[cat] = {'FL': 0, 'CA': 0, 'TX': 0, 'total': 0}
        categories[cat][state] = count
        categories[cat]['total'] += count

    for cat in sorted(categories.keys(), key=lambda x: categories[x]['total'], reverse=True):
        data = categories[cat]
        print(f'{cat:15} FL:{data["FL"]:>7,}  CA:{data["CA"]:>7,}  TX:{data["TX"]:>7,}  Total:{data["total"]:>8,}')

    # 2. Cross-state contractors (operate in multiple states)
    print('\nCROSS-STATE CONTRACTORS (Licensed in 2+ States)')
    print('-' * 50)
    cursor.execute("""
        SELECT c.id, GROUP_CONCAT(DISTINCT l.state) as states
        FROM contractors c
        JOIN licenses l ON c.id = l.contractor_id
        GROUP BY c.id
        HAVING COUNT(DISTINCT l.state) >= 2
    """)
    cross_state = cursor.fetchall()
    print(f'Contractors in 2+ states: {len(cross_state):,}')

    if cross_state:
        cursor.execute("""
            SELECT c.company_name, c.city, c.state, GROUP_CONCAT(DISTINCT l.state) as licensed_states,
                   GROUP_CONCAT(DISTINCT l.license_category) as categories
            FROM contractors c
            JOIN licenses l ON c.id = l.contractor_id
            GROUP BY c.id
            HAVING COUNT(DISTINCT l.state) >= 2
            LIMIT 5
        """)
        examples = cursor.fetchall()
        print('\nTop cross-state examples:')
        for name, city, state, lic_states, cats in examples:
            print(f'  - {name[:40]:40} | States: {lic_states:10} | {cats}')

    # 3. Multi-license breakdown
    print('\nMULTI-LICENSE BREAKDOWN')
    print('-' * 50)
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            CASE
                WHEN cnt >= 4 THEN '4+ categories (SUPER UNICORN)'
                WHEN cnt = 3 THEN '3 categories (UNICORN)'
                WHEN cnt = 2 THEN '2 categories (Multi-License)'
                ELSE '1 category'
            END as tier
        FROM (
            SELECT c.id, COUNT(DISTINCT l.license_category) as cnt
            FROM contractors c
            JOIN licenses l ON c.id = l.contractor_id
            WHERE l.license_category != ''
            GROUP BY c.id
        )
        GROUP BY tier
        ORDER BY count DESC
    """)
    for count, tier in cursor.fetchall():
        print(f'{tier:35} {count:>10,}')

    # 4. Contact info coverage
    print('\nCONTACT INFO COVERAGE')
    print('-' * 50)
    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_phone != ''")
    with_phone = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_email != ''")
    with_email = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contractors WHERE primary_phone != '' AND primary_email != ''")
    with_both = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM contractors')
    total = cursor.fetchone()[0]

    print(f'Total contractors:      {total:>10,}')
    print(f'With phone:             {with_phone:>10,} ({with_phone/total*100:.1f}%)')
    print(f'With email:             {with_email:>10,} ({with_email/total*100:.1f}%)')
    print(f'With BOTH:              {with_both:>10,} ({with_both/total*100:.1f}%)')
    no_contact = total - with_phone - with_email + with_both
    print(f'Missing contact info:   {no_contact:>10,} ({no_contact/total*100:.1f}%)')

    # 5. Sample UNICORN records check
    print('\nSAMPLE UNICORN RECORDS (3+ Categories)')
    print('-' * 50)
    cursor.execute("""
        SELECT c.company_name, c.city, c.state, c.primary_phone, c.primary_email,
               GROUP_CONCAT(DISTINCT l.license_category) as categories,
               COUNT(DISTINCT l.license_category) as cat_count
        FROM contractors c
        JOIN licenses l ON c.id = l.contractor_id
        WHERE l.license_category != ''
        GROUP BY c.id
        HAVING cat_count >= 3
        ORDER BY cat_count DESC, c.company_name
        LIMIT 10
    """)
    for name, city, state, phone, email, cats, cat_count in cursor.fetchall():
        print(f'{cat_count} cats | {name[:35]:35} | {state} | {cats}')

    # 6. State breakdown with email coverage
    print('\nSTATE-BY-STATE CONTACT COVERAGE')
    print('-' * 50)
    for state in ['FL', 'CA', 'TX']:
        cursor.execute(f"""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN primary_email != '' THEN 1 ELSE 0 END) as with_email,
                   SUM(CASE WHEN primary_phone != '' THEN 1 ELSE 0 END) as with_phone
            FROM contractors c
            WHERE EXISTS (SELECT 1 FROM licenses l WHERE l.contractor_id = c.id AND l.state = '{state}')
        """)
        total, with_email, with_phone = cursor.fetchone()
        email_pct = with_email / total * 100 if total > 0 else 0
        phone_pct = with_phone / total * 100 if total > 0 else 0
        print(f'{state}: {total:>7,} contractors | Email: {with_email:>6,} ({email_pct:>5.1f}%) | Phone: {with_phone:>6,} ({phone_pct:>5.1f}%)')

    # 7. Database file info
    print('\nDATABASE INFO')
    print('-' * 50)
    db_size = db_path.stat().st_size / 1024 / 1024
    print(f'Database file: {db_path}')
    print(f'Size: {db_size:.1f} MB')

    conn.close()

if __name__ == '__main__':
    analyze_data_quality()
