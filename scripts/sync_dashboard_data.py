#!/usr/bin/env python3
"""
Auto-Sync Dashboard Data from SQLite Database
==============================================
Generates dashboard_data.json from the pipeline database.
Run this script whenever data changes to keep dashboard accurate.

USAGE:
    ./venv/bin/python3 scripts/sync_dashboard_data.py

This script:
1. Queries pipeline.db for current counts
2. Determines WORKING/BROKEN status based on record counts
3. Updates dashboard_data.json with real data
4. Optionally deploys to Vercel if --deploy flag is passed
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import argparse
import subprocess


class DashboardSync:
    """Sync dashboard data with SQLite database."""

    def __init__(self, db_path: str = "output/pipeline.db"):
        self.db_path = Path(db_path)
        self.dashboard_path = Path("dashboard/public/data/dashboard_data.json")
        self.conn = None

    def connect(self):
        """Connect to SQLite database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def get_oem_stats(self) -> list:
        """Get OEM certification stats from database."""
        query = """
        SELECT
            oem_name,
            COUNT(*) as contractor_count,
            COUNT(DISTINCT c.state) as states_covered,
            MAX(o.created_at) as last_scrape,
            SUM(CASE WHEN c.primary_phone IS NOT NULL AND c.primary_phone != '' THEN 1 ELSE 0 END) as with_phone,
            SUM(CASE WHEN c.primary_email IS NOT NULL AND c.primary_email != '' THEN 1 ELSE 0 END) as with_email
        FROM oem_certifications o
        LEFT JOIN contractors c ON o.contractor_id = c.id
        WHERE c.is_deleted = 0
        GROUP BY oem_name
        ORDER BY contractor_count DESC
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_contractor_stats(self) -> dict:
        """Get overall contractor stats."""
        stats = {}

        # Total contractors
        cursor = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM contractors WHERE is_deleted = 0"
        )
        stats['total_contractors'] = cursor.fetchone()['cnt']

        # With email
        cursor = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM contractors
            WHERE is_deleted = 0
            AND primary_email IS NOT NULL AND primary_email != ''
        """)
        stats['with_email'] = cursor.fetchone()['cnt']

        # With phone
        cursor = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM contractors
            WHERE is_deleted = 0
            AND primary_phone IS NOT NULL AND primary_phone != ''
        """)
        stats['with_phone'] = cursor.fetchone()['cnt']

        # Multi-license contractors
        cursor = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT contractor_id FROM licenses
                GROUP BY contractor_id
                HAVING COUNT(DISTINCT license_category) >= 2
            )
        """)
        stats['multi_license_count'] = cursor.fetchone()['cnt']

        # Unicorns (3+ trades)
        cursor = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT contractor_id FROM licenses
                GROUP BY contractor_id
                HAVING COUNT(DISTINCT license_category) >= 3
            )
        """)
        stats['unicorn_count'] = cursor.fetchone()['cnt']

        # Multi-OEM contractors
        cursor = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT contractor_id FROM oem_certifications
                GROUP BY contractor_id
                HAVING COUNT(DISTINCT oem_name) >= 2
            )
        """)
        stats['multi_oem_count'] = cursor.fetchone()['cnt']

        # Calculate rates
        if stats['total_contractors'] > 0:
            stats['email_rate'] = round(stats['with_email'] / stats['total_contractors'] * 100, 1)
            stats['phone_rate'] = round(stats['with_phone'] / stats['total_contractors'] * 100, 1)
        else:
            stats['email_rate'] = 0
            stats['phone_rate'] = 0

        return stats

    def get_state_coverage(self) -> list:
        """Get contractor counts by state."""
        query = """
        SELECT
            state,
            COUNT(*) as contractor_count,
            SUM(CASE WHEN primary_email IS NOT NULL AND primary_email != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN primary_phone IS NOT NULL AND primary_phone != '' THEN 1 ELSE 0 END) as with_phone
        FROM contractors
        WHERE is_deleted = 0 AND state IS NOT NULL
        GROUP BY state
        ORDER BY contractor_count DESC
        LIMIT 20
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def update_scraper_health(self, existing_health: list, oem_stats: list) -> list:
        """Update scraper health based on actual database counts."""
        # Create lookup from OEM stats
        oem_lookup = {
            s['oem_name'].lower().replace(' ', ''): s for s in oem_stats
        }

        # OEM name normalization map
        name_map = {
            'briggs & stratton': 'briggs&stratton',
            'sma solar': 'sma',
            'schneider electric': 'schneiderelectric',
        }

        updated_health = []
        for scraper in existing_health:
            name = scraper['scraper_name']
            scraper_type = scraper.get('scraper_type', 'OEM')

            # Only update OEM scrapers
            if scraper_type != 'OEM':
                updated_health.append(scraper)
                continue

            # Normalize name for lookup
            lookup_key = name.lower().replace(' ', '')
            if name.lower() in name_map:
                lookup_key = name_map[name.lower()]

            # Find matching OEM stats
            if lookup_key in oem_lookup:
                stats = oem_lookup[lookup_key]

                # Update with real data
                scraper['total_records_lifetime'] = stats['contractor_count']
                scraper['status'] = 'WORKING'
                scraper['fix_difficulty'] = None

                if stats['last_scrape']:
                    scraper['last_successful_run'] = stats['last_scrape']

                # Update notes with real stats
                phone_pct = round(stats['with_phone'] / stats['contractor_count'] * 100) if stats['contractor_count'] > 0 else 0
                email_pct = round(stats['with_email'] / stats['contractor_count'] * 100) if stats['contractor_count'] > 0 else 0
                scraper['notes'] = f"{stats['contractor_count']:,} contractors | {stats['states_covered']} states | {phone_pct}% phone | {email_pct}% email"
            else:
                # No data found - check if extraction script is validated
                notes = scraper.get('notes', '')
                is_validated = 'VALIDATED' in notes.upper()

                if scraper.get('total_records_lifetime', 0) == 0:
                    if is_validated:
                        # Extraction script works, just needs production run
                        scraper['status'] = 'WORKING'
                        scraper['fix_difficulty'] = None
                    else:
                        scraper['status'] = 'BROKEN'
                        scraper['fix_difficulty'] = 'HARD'

            updated_health.append(scraper)

        return updated_health

    def sync(self) -> dict:
        """Perform full sync and return updated dashboard data."""
        self.connect()

        try:
            # Load existing dashboard data
            if self.dashboard_path.exists():
                with open(self.dashboard_path, 'r') as f:
                    dashboard = json.load(f)
            else:
                dashboard = {}

            # Get fresh data from database
            oem_stats = self.get_oem_stats()
            contractor_stats = self.get_contractor_stats()
            state_coverage = self.get_state_coverage()

            # Update pipeline health
            dashboard['pipeline_health'] = {
                **contractor_stats,
                'generated_at': datetime.now().isoformat()
            }

            # Count scrapers by status
            if 'scraper_health' in dashboard:
                # Update scraper health with real counts
                dashboard['scraper_health'] = self.update_scraper_health(
                    dashboard['scraper_health'],
                    oem_stats
                )

                # Count working/broken
                working = sum(1 for s in dashboard['scraper_health'] if s.get('status') == 'WORKING')
                broken = sum(1 for s in dashboard['scraper_health'] if s.get('status') == 'BROKEN')
                untested = sum(1 for s in dashboard['scraper_health'] if s.get('status') == 'UNTESTED')

                dashboard['pipeline_health']['scrapers_working'] = working
                dashboard['pipeline_health']['scrapers_broken'] = broken
                dashboard['pipeline_health']['scrapers_untested'] = untested
                dashboard['pipeline_health']['scrapers_total'] = working + broken + untested

            # Update OEM coverage
            dashboard['oem_coverage'] = [
                {
                    'oem_name': s['oem_name'],
                    'contractor_count': s['contractor_count'],
                    'states_covered': s['states_covered'],
                    'with_phone': s['with_phone'],
                    'with_email': s['with_email']
                }
                for s in oem_stats
            ]

            # Update state coverage
            dashboard['state_coverage'] = state_coverage

            # Save updated dashboard
            with open(self.dashboard_path, 'w') as f:
                json.dump(dashboard, f, indent=2)

            return dashboard

        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="Sync dashboard data from SQLite database")
    parser.add_argument("--deploy", action="store_true", help="Deploy to Vercel after sync")
    parser.add_argument("--db", default="output/pipeline.db", help="Path to SQLite database")
    args = parser.parse_args()

    print("=" * 60)
    print("DASHBOARD DATA SYNC")
    print("=" * 60)

    sync = DashboardSync(args.db)

    try:
        dashboard = sync.sync()

        print(f"\n✓ Dashboard synced at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nPipeline Health:")
        print(f"  Total Contractors: {dashboard['pipeline_health']['total_contractors']:,}")
        print(f"  With Email: {dashboard['pipeline_health']['with_email']:,} ({dashboard['pipeline_health']['email_rate']}%)")
        print(f"  With Phone: {dashboard['pipeline_health']['with_phone']:,} ({dashboard['pipeline_health']['phone_rate']}%)")
        print(f"  Multi-License: {dashboard['pipeline_health']['multi_license_count']:,}")
        print(f"  Unicorns (3+ trades): {dashboard['pipeline_health']['unicorn_count']:,}")
        print(f"  Multi-OEM: {dashboard['pipeline_health']['multi_oem_count']:,}")

        print(f"\nScraper Status:")
        print(f"  WORKING: {dashboard['pipeline_health']['scrapers_working']}")
        print(f"  BROKEN: {dashboard['pipeline_health']['scrapers_broken']}")
        print(f"  UNTESTED: {dashboard['pipeline_health']['scrapers_untested']}")

        print(f"\nOEM Coverage (Top 5):")
        for oem in dashboard['oem_coverage'][:5]:
            print(f"  {oem['oem_name']}: {oem['contractor_count']:,} contractors ({oem['states_covered']} states)")

        print(f"\n✓ Saved to: {sync.dashboard_path}")

        if args.deploy:
            print("\nDeploying to Vercel...")
            subprocess.run(["vercel", "--prod"], cwd="dashboard", check=True)
            print("✓ Deployed to Vercel")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
