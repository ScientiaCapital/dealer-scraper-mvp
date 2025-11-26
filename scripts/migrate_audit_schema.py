#!/usr/bin/env python3
"""
Migrate existing database to add audit trail tables.

This script safely adds the new audit trail schema to an existing database:
- file_imports (import tracking and deduplication)
- contractor_history (change history with before/after snapshots)
- import_locks (concurrency control)
- Soft delete columns on contractors table

Usage:
    python migrate_audit_schema.py [--db-path PATH] [--dry-run]

Examples:
    # Dry run on default database
    python migrate_audit_schema.py --dry-run

    # Apply migration to production database
    python migrate_audit_schema.py --db-path /path/to/pipeline.db

    # Apply to default database (output/master/pipeline.db)
    python migrate_audit_schema.py
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

# Default database path (relative to project root)
DEFAULT_DB = Path(__file__).parent.parent / "output" / "master" / "pipeline.db"


def check_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table already exists in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def check_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def add_audit_tables(conn: sqlite3.Connection, dry_run: bool = False) -> Dict[str, List[str]]:
    """
    Add the three audit trail tables to the database.

    Returns:
        Dict with 'created' and 'already_exists' lists of table names.
    """
    result = {"created": [], "already_exists": []}

    tables = {
        "file_imports": """
            CREATE TABLE IF NOT EXISTS file_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size_bytes INTEGER,
                row_count INTEGER,
                source_type TEXT,
                import_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                import_completed_at TIMESTAMP,
                import_status TEXT DEFAULT 'in_progress',
                records_created INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                records_merged INTEGER DEFAULT 0,
                records_skipped INTEGER DEFAULT 0,
                error_message TEXT,
                UNIQUE(file_hash)
            )
        """,
        "contractor_history": """
            CREATE TABLE IF NOT EXISTS contractor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contractor_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                file_import_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE SET NULL,
                FOREIGN KEY (file_import_id) REFERENCES file_imports(id)
            )
        """,
        "import_locks": """
            CREATE TABLE IF NOT EXISTS import_locks (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                lock_holder TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                reason TEXT
            )
        """
    }

    for table_name, create_sql in tables.items():
        exists = check_table_exists(conn, table_name)

        if exists:
            result["already_exists"].append(table_name)
            print(f"  ✓ Table {table_name} already exists (skipping)")
        else:
            if dry_run:
                print(f"  [DRY RUN] Would create table: {table_name}")
            else:
                conn.execute(create_sql)
                result["created"].append(table_name)
                print(f"  ✓ Created table: {table_name}")

    return result


def add_soft_delete_columns(conn: sqlite3.Connection, dry_run: bool = False) -> Dict[str, List[str]]:
    """
    Add soft delete columns to the contractors table.

    Returns:
        Dict with 'added' and 'already_exists' lists of column names.
    """
    result = {"added": [], "already_exists": []}

    columns = {
        "is_deleted": "ALTER TABLE contractors ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "deleted_at": "ALTER TABLE contractors ADD COLUMN deleted_at TIMESTAMP",
        "deleted_by": "ALTER TABLE contractors ADD COLUMN deleted_by TEXT",
        "deletion_reason": "ALTER TABLE contractors ADD COLUMN deletion_reason TEXT"
    }

    # First check if contractors table exists
    if not check_table_exists(conn, "contractors"):
        print("  ⚠️  WARNING: contractors table does not exist!")
        return result

    for column_name, alter_sql in columns.items():
        exists = check_column_exists(conn, "contractors", column_name)

        if exists:
            result["already_exists"].append(column_name)
            print(f"  ✓ Column contractors.{column_name} already exists (skipping)")
        else:
            if dry_run:
                print(f"  [DRY RUN] Would add column: contractors.{column_name}")
            else:
                conn.execute(alter_sql)
                result["added"].append(column_name)
                print(f"  ✓ Added column: contractors.{column_name}")

    return result


def add_audit_indexes(conn: sqlite3.Connection, dry_run: bool = False) -> Dict[str, List[str]]:
    """
    Add indexes for audit trail tables and soft delete.

    Returns:
        Dict with 'created' and 'already_exists' lists of index names.
    """
    result = {"created": [], "already_exists": []}

    indexes = {
        "idx_contractors_deleted": "CREATE INDEX IF NOT EXISTS idx_contractors_deleted ON contractors(is_deleted)",
        "idx_file_imports_hash": "CREATE INDEX IF NOT EXISTS idx_file_imports_hash ON file_imports(file_hash)",
        "idx_file_imports_status": "CREATE INDEX IF NOT EXISTS idx_file_imports_status ON file_imports(import_status)",
        "idx_contractor_history_cid": "CREATE INDEX IF NOT EXISTS idx_contractor_history_cid ON contractor_history(contractor_id)",
        "idx_contractor_history_ts": "CREATE INDEX IF NOT EXISTS idx_contractor_history_ts ON contractor_history(created_at)",
        "idx_contractor_history_type": "CREATE INDEX IF NOT EXISTS idx_contractor_history_type ON contractor_history(change_type)",
        "idx_contractor_history_import": "CREATE INDEX IF NOT EXISTS idx_contractor_history_import ON contractor_history(file_import_id)"
    }

    for index_name, create_sql in indexes.items():
        # Check if index exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (index_name,)
        )
        exists = cursor.fetchone() is not None

        if exists:
            result["already_exists"].append(index_name)
            print(f"  ✓ Index {index_name} already exists (skipping)")
        else:
            if dry_run:
                print(f"  [DRY RUN] Would create index: {index_name}")
            else:
                conn.execute(create_sql)
                result["created"].append(index_name)
                print(f"  ✓ Created index: {index_name}")

    return result


def migrate(db_path: Path, dry_run: bool = False) -> Dict[str, any]:
    """
    Run all migrations to add audit trail to existing database.

    Args:
        db_path: Path to the SQLite database file
        dry_run: If True, show what would be done without modifying database

    Returns:
        Dict with migration summary: {
            "tables": {...},
            "columns": {...},
            "indexes": {...}
        }
    """
    # Validate database exists
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Print backup warning
    print("\n" + "="*60)
    print("⚠️  BACKUP REMINDER")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
    print("\nBefore running this migration, ensure you have a backup!")
    print("  cp output/master/pipeline.db output/master/pipeline.db.backup")
    print("="*60 + "\n")

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    else:
        response = input("Proceed with migration? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)
        print()

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        summary = {}

        # Step 1: Add audit tables
        print("Step 1: Adding audit trail tables")
        print("-" * 40)
        summary["tables"] = add_audit_tables(conn, dry_run)
        print()

        # Step 2: Add soft delete columns
        print("Step 2: Adding soft delete columns to contractors")
        print("-" * 40)
        summary["columns"] = add_soft_delete_columns(conn, dry_run)
        print()

        # Step 3: Add indexes
        print("Step 3: Adding audit trail indexes")
        print("-" * 40)
        summary["indexes"] = add_audit_indexes(conn, dry_run)
        print()

        # Commit changes
        if not dry_run:
            conn.commit()
            print("✅ Migration completed successfully!")
        else:
            print("✅ Dry run completed (no changes made)")

        # Print summary
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)

        tables_created = len(summary["tables"]["created"])
        tables_existing = len(summary["tables"]["already_exists"])
        columns_added = len(summary["columns"]["added"])
        columns_existing = len(summary["columns"]["already_exists"])
        indexes_created = len(summary["indexes"]["created"])
        indexes_existing = len(summary["indexes"]["already_exists"])

        print(f"Tables:  {tables_created} created, {tables_existing} already existed")
        print(f"Columns: {columns_added} added, {columns_existing} already existed")
        print(f"Indexes: {indexes_created} created, {indexes_existing} already existed")

        if summary["tables"]["created"]:
            print(f"\nNew tables: {', '.join(summary['tables']['created'])}")
        if summary["columns"]["added"]:
            print(f"New columns: {', '.join(summary['columns']['added'])}")
        if summary["indexes"]["created"]:
            print(f"New indexes: {', '.join(summary['indexes']['created'])}")

        print("="*60 + "\n")

        return summary

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate existing database to add audit trail schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be done
  python migrate_audit_schema.py --dry-run

  # Apply migration to production database
  python migrate_audit_schema.py

  # Apply to custom database location
  python migrate_audit_schema.py --db-path /path/to/pipeline.db
        """
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to database file (default: {DEFAULT_DB})"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    try:
        migrate(args.db_path, dry_run=args.dry_run)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
