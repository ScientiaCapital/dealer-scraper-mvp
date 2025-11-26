#!/usr/bin/env python3
"""
Schema Migration: Add ATL (Above The Line) and SPW Enrichment Columns

This migration adds columns to support:
1. ATL decision maker contact enrichment (contacts table)
2. Full SPW profile data (spw_rankings table)

Uses ADD COLUMN approach (non-destructive, preserves existing data).

Usage:
    python3 scripts/migrate_schema_atl_spw.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"


def get_existing_columns(cursor, table_name: str) -> set:
    """Get existing columns in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def add_column_if_missing(cursor, table: str, column: str, col_type: str, default=None):
    """Add a column if it doesn't already exist."""
    existing = get_existing_columns(cursor, table)
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        print(f"  ✅ Added {table}.{column} ({col_type})")
        return True
    else:
        print(f"  ⏭️  {table}.{column} already exists")
        return False


def migrate_contacts_schema(cursor):
    """
    Add ATL (Above The Line) columns to contacts table.

    These columns support:
    - Multi-contact per company (C-suite, VPs, Directors, Owners)
    - Phone type differentiation (main office vs direct line vs cell)
    - Email type (work vs personal)
    - Decision maker flagging for outreach prioritization
    """
    print("\n📇 CONTACTS TABLE - ATL Enrichment Columns")
    print("-" * 50)

    # Name components (for formal addressing)
    add_column_if_missing(cursor, "contacts", "first_name", "TEXT")
    add_column_if_missing(cursor, "contacts", "last_name", "TEXT")

    # Phone type classification
    # Values: 'main', 'direct', 'cell', 'fax'
    add_column_if_missing(cursor, "contacts", "phone_type", "TEXT")
    add_column_if_missing(cursor, "contacts", "phone_extension", "TEXT")

    # Email type classification
    # Values: 'work', 'personal', 'generic' (info@, sales@)
    add_column_if_missing(cursor, "contacts", "email_type", "TEXT")

    # Seniority classification for ATL targeting
    # Values: 'c_suite', 'vp', 'director', 'manager', 'owner', 'partner', 'founder'
    add_column_if_missing(cursor, "contacts", "seniority", "TEXT")

    # Decision maker flag (TRUE = prioritize for outreach)
    add_column_if_missing(cursor, "contacts", "is_decision_maker", "INTEGER", 0)

    # LinkedIn for social selling
    add_column_if_missing(cursor, "contacts", "linkedin_url", "TEXT")

    # Source URL (where we found this contact)
    add_column_if_missing(cursor, "contacts", "source_url", "TEXT")

    # Last verified date
    add_column_if_missing(cursor, "contacts", "verified_at", "TIMESTAMP")


def migrate_contractors_schema(cursor):
    """
    Add company-level enrichment columns to contractors table.

    These columns store company-wide data:
    - Company LinkedIn page (for company research)
    - Company website (if different from domain)
    """
    print("\n🏢 CONTRACTORS TABLE - Company Enrichment Columns")
    print("-" * 50)

    # Company LinkedIn page (different from individual contact LinkedIn)
    add_column_if_missing(cursor, "contractors", "company_linkedin_url", "TEXT")

    # Company website (full URL, may differ from email domain)
    add_column_if_missing(cursor, "contractors", "website_url", "TEXT")

    # Year founded (for company age scoring)
    add_column_if_missing(cursor, "contractors", "year_founded", "INTEGER")

    # Employee count estimate
    add_column_if_missing(cursor, "contractors", "employee_count", "INTEGER")

    # Revenue estimate (string like "$5M-$10M")
    add_column_if_missing(cursor, "contractors", "estimated_revenue", "TEXT")

    # Last enriched timestamp
    add_column_if_missing(cursor, "contractors", "enriched_at", "TIMESTAMP")


def migrate_spw_rankings_schema(cursor):
    """
    Add SPW profile enrichment columns.

    These columns store data from individual SPW company profile pages:
    - Full location (city, state)
    - Company metadata (website, founded, employees)
    - Performance metrics (cumulative kW)
    - Market coverage (markets served, service areas)
    """
    print("\n🏆 SPW_RANKINGS TABLE - Profile Enrichment Columns")
    print("-" * 50)

    # Full location (list pages only have state)
    add_column_if_missing(cursor, "spw_rankings", "city", "TEXT")

    # Company metadata
    add_column_if_missing(cursor, "spw_rankings", "website", "TEXT")
    add_column_if_missing(cursor, "spw_rankings", "year_founded", "INTEGER")
    add_column_if_missing(cursor, "spw_rankings", "employee_count", "INTEGER")

    # Performance metrics
    add_column_if_missing(cursor, "spw_rankings", "cumulative_kw", "INTEGER")

    # Descriptive content
    add_column_if_missing(cursor, "spw_rankings", "description", "TEXT")

    # Market coverage (stored as JSON arrays)
    # markets_served: ["Utility", "C&I", "Community", "Residential"]
    add_column_if_missing(cursor, "spw_rankings", "markets_served", "TEXT")
    # service_areas: ["CA", "TX", "AZ", ...] or ["Nationwide"]
    add_column_if_missing(cursor, "spw_rankings", "service_areas", "TEXT")

    # Profile tracking
    add_column_if_missing(cursor, "spw_rankings", "profile_url", "TEXT")
    add_column_if_missing(cursor, "spw_rankings", "scraped_at", "TIMESTAMP")


def create_new_indexes(cursor):
    """Create indexes for new columns to support efficient queries."""
    print("\n📊 CREATING INDEXES")
    print("-" * 50)

    indexes = [
        ("idx_contacts_seniority", "contacts(seniority)"),
        ("idx_contacts_decision_maker", "contacts(is_decision_maker)"),
        ("idx_contacts_source", "contacts(source)"),
        ("idx_contacts_linkedin", "contacts(linkedin_url)"),
        ("idx_contractors_linkedin", "contractors(company_linkedin_url)"),
        ("idx_contractors_website", "contractors(website_url)"),
        ("idx_spw_profile_url", "spw_rankings(profile_url)"),
        ("idx_spw_markets", "spw_rankings(markets_served)"),
    ]

    for idx_name, idx_def in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            print(f"  ✅ Created index {idx_name}")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print(f"  ⏭️  Index {idx_name} already exists")
            else:
                raise


def show_schema_summary(cursor):
    """Display current schema state after migration."""
    print("\n" + "=" * 70)
    print("SCHEMA MIGRATION COMPLETE")
    print("=" * 70)

    for table in ["contacts", "contractors", "spw_rankings"]:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"\n📋 {table.upper()} ({len(columns)} columns):")
        for col in columns:
            col_id, name, col_type, notnull, default, pk = col
            print(f"   {name:25} {col_type:10} {'NOT NULL' if notnull else ''}")


def run_migration():
    """Execute the schema migration."""
    print("=" * 70)
    print("SCHEMA MIGRATION: ATL + SPW Enrichment Columns")
    print(f"Database: {DB_PATH}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run state migration scripts first to create the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Run migrations
        migrate_contacts_schema(cursor)
        migrate_contractors_schema(cursor)
        migrate_spw_rankings_schema(cursor)
        create_new_indexes(cursor)

        # Commit changes
        conn.commit()

        # Show summary
        show_schema_summary(cursor)

        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
