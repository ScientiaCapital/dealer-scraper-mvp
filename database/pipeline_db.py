"""
Pipeline Database - SQLite backend for contractor data.

Core class for the "Perfect One State, Then Scale" pipeline.
Handles:
- Contractor deduplication (phone, email, domain, fuzzy name)
- License tracking across states
- Contact management from multiple sources
- Pipeline run history
- Export to CSV for outreach

Usage:
    from database import PipelineDB

    db = PipelineDB()
    db.initialize()  # Creates tables if not exist

    # Add contractor with dedup check
    contractor_id, is_new = db.add_contractor(record)

    # Export multi-license contractors
    db.export_multi_license('FL', 'output/fl_multi_license.csv')
"""

import sqlite3
import hashlib
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pipeline_db')

from database.models import (
    Contractor, Contact, License, OEMCertification,
    PipelineRun, DedupMatch, SPWRanking,
    normalize_phone, normalize_email, extract_domain,
    normalize_company_name, fuzzy_match_ratio
)


# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent / "output" / "pipeline.db"

# Fuzzy match threshold for company name matching
FUZZY_THRESHOLD = 0.85


class PipelineDB:
    """
    SQLite database for contractor pipeline.

    Thread-safe via connection per call pattern.
    Uses WAL mode for better concurrent read performance.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to output/pipeline.db
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row  # Dict-like access
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA foreign_keys=ON")   # Enforce FK constraints
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """
        Initialize database schema.

        Creates all tables, indexes, and views if they don't exist.
        Safe to call multiple times.
        """
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        with self._get_connection() as conn:
            conn.executescript(schema_sql)

    def add_contractor(
        self,
        record: Dict[str, Any],
        source: str = "unknown"
    ) -> Tuple[int, bool]:
        """
        Add a contractor with deduplication.

        Checks for existing contractor by:
        1. Phone (normalized 10-digit)
        2. Email (exact)
        3. Domain (company email domain)
        4. Fuzzy name (85%+ similarity + same state)

        If duplicate found, merges contact/license info into existing.
        If new, creates new contractor record.

        Args:
            record: Dict with keys: company_name, contact_name, email, phone,
                   address, city, state, zip, license_type, license_number
            source: Source identifier (e.g., 'FL_License', 'SPW')

        Returns:
            (contractor_id, is_new) - ID and whether this was a new record
        """
        # Normalize input data
        company_name = record.get('company_name', '').strip()
        contact_name = record.get('contact_name', '').strip()
        email = normalize_email(record.get('email', ''))
        phone = normalize_phone(record.get('phone', ''))
        domain = extract_domain(email)
        state = record.get('state', '').upper().strip()
        city = record.get('city', '').strip()
        zip_code = record.get('zip', '').strip()
        street = record.get('address', '') or record.get('street', '')
        license_type = record.get('license_type', record.get('license_types', '')).strip().upper()
        license_number = record.get('license_number', '').strip()
        license_category = record.get('license_category', '')

        normalized_name = normalize_company_name(company_name)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check for existing contractor (dedup)
            existing_id, match_type, match_value = self._find_duplicate(
                cursor, phone, email, domain, normalized_name, state
            )

            if existing_id:
                # Merge into existing
                self._merge_into_existing(
                    cursor, existing_id, contact_name, email, phone,
                    license_type, license_category, license_number,
                    state, source
                )

                # Log dedup match
                self._log_dedup_match(
                    cursor, existing_id, record, match_type, match_value, source
                )

                return existing_id, False

            # Create new contractor
            cursor.execute("""
                INSERT INTO contractors
                (company_name, normalized_name, street, city, state, zip,
                 primary_phone, primary_email, primary_domain)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_name, normalized_name, street, city, state, zip_code,
                phone, email, domain
            ))
            contractor_id = cursor.lastrowid

            # Add contact
            if contact_name or email:
                cursor.execute("""
                    INSERT OR IGNORE INTO contacts
                    (contractor_id, name, email, phone, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (contractor_id, contact_name, email, phone, source, 80))

            # Add license
            if license_type and state:
                cursor.execute("""
                    INSERT OR IGNORE INTO licenses
                    (contractor_id, state, license_type, license_category,
                     license_number, source_file)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (contractor_id, state, license_type, license_category,
                      license_number, source))

            return contractor_id, True

    def _find_duplicate(
        self,
        cursor: sqlite3.Cursor,
        phone: str,
        email: str,
        domain: str,
        normalized_name: str,
        state: str
    ) -> Tuple[Optional[int], str, str]:
        """
        Find duplicate contractor by multiple signals.

        Priority order:
        1. Phone (highest confidence - 96%+ accuracy)
        2. Email (exact)
        3. Domain (same company email)
        4. Fuzzy name + same state (85%+ threshold, prefix-optimized)

        Returns:
            (contractor_id, match_type, match_value) or (None, '', '')
        """
        # 1. Phone match (highest confidence - 96%+ accuracy)
        if phone:
            cursor.execute(
                "SELECT id FROM contractors WHERE primary_phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            if row:
                return row['id'], 'phone', phone

            # Also check contacts table
            cursor.execute(
                "SELECT contractor_id FROM contacts WHERE phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            if row:
                return row['contractor_id'], 'phone', phone

        # 2. Email match (exact)
        if email:
            cursor.execute(
                "SELECT id FROM contractors WHERE primary_email = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return row['id'], 'email', email

            cursor.execute(
                "SELECT contractor_id FROM contacts WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return row['contractor_id'], 'email', email

        # 3. Domain match (same company email domain)
        if domain:
            cursor.execute(
                "SELECT id, company_name FROM contractors WHERE primary_domain = ?",
                (domain,)
            )
            row = cursor.fetchone()
            if row:
                # Verify name similarity (50%+ threshold for domain match)
                existing_name = row['company_name']
                ratio = fuzzy_match_ratio(normalized_name, existing_name)
                if ratio >= 0.5:
                    return row['id'], 'domain', domain

        # 4. Fuzzy name match (same state, 85%+ threshold)
        # OPTIMIZATION: Use prefix matching to reduce search space dramatically
        # Only check records that share the first 3 chars of normalized name
        if normalized_name and state and len(normalized_name) >= 3:
            prefix = normalized_name[:3]
            cursor.execute(
                """SELECT id, company_name, normalized_name FROM contractors
                   WHERE state = ? AND normalized_name LIKE ?
                   LIMIT 100""",
                (state, f"{prefix}%")
            )
            for row in cursor.fetchall():
                ratio = fuzzy_match_ratio(normalized_name, row['normalized_name'] or row['company_name'])
                if ratio >= FUZZY_THRESHOLD:
                    return row['id'], 'fuzzy_name', f"{normalized_name}:{ratio:.2f}"

        return None, '', ''

    def _merge_into_existing(
        self,
        cursor: sqlite3.Cursor,
        contractor_id: int,
        contact_name: str,
        email: str,
        phone: str,
        license_type: str,
        license_category: str,
        license_number: str,
        state: str,
        source: str
    ) -> None:
        """Merge duplicate record into existing contractor."""
        # Add contact if new
        if contact_name or email:
            cursor.execute("""
                INSERT OR IGNORE INTO contacts
                (contractor_id, name, email, phone, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (contractor_id, contact_name, email, phone, source, 70))

        # Add license if new
        if license_type and state:
            cursor.execute("""
                INSERT OR IGNORE INTO licenses
                (contractor_id, state, license_type, license_category,
                 license_number, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (contractor_id, state, license_type, license_category,
                  license_number, source))

        # Update timestamp
        cursor.execute("""
            UPDATE contractors SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contractor_id,))

    def _log_dedup_match(
        self,
        cursor: sqlite3.Cursor,
        master_id: int,
        record: Dict[str, Any],
        match_type: str,
        match_value: str,
        source: str
    ) -> None:
        """Log a deduplication match for debugging."""
        # Create hash of duplicate record
        record_str = str(sorted(record.items()))
        record_hash = hashlib.md5(record_str.encode()).hexdigest()[:16]

        cursor.execute("""
            INSERT INTO dedup_matches
            (master_contractor_id, duplicate_record_hash, match_type,
             match_value, match_confidence, source_file)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (master_id, record_hash, match_type, match_value, 1.0, source))

    def add_license(
        self,
        contractor_id: int,
        state: str,
        license_type: str,
        license_category: str = "",
        license_number: str = "",
        source_file: str = ""
    ) -> int:
        """Add a license to an existing contractor."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO licenses
                (contractor_id, state, license_type, license_category,
                 license_number, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (contractor_id, state, license_type.upper(), license_category.upper(),
                  license_number, source_file))
            return cursor.lastrowid or 0

    def add_contact(
        self,
        contractor_id: int,
        name: str = "",
        email: str = "",
        phone: str = "",
        title: str = "",
        source: str = "",
        confidence: int = 50
    ) -> int:
        """Add a contact to an existing contractor."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO contacts
                (contractor_id, name, email, phone, title, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contractor_id, name, normalize_email(email),
                  normalize_phone(phone), title, source, confidence))
            return cursor.lastrowid or 0

    def start_pipeline_run(
        self,
        state: str,
        source_file: str
    ) -> int:
        """Start a new pipeline run and return run ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pipeline_runs (state, source_file, status)
                VALUES (?, ?, 'in_progress')
            """, (state, source_file))
            return cursor.lastrowid

    def complete_pipeline_run(
        self,
        run_id: int,
        records_input: int,
        records_new: int,
        records_merged: int,
        multi_license_found: int,
        unicorns_found: int,
        duration_seconds: float,
        status: str = "completed",
        error_message: str = ""
    ) -> None:
        """Complete a pipeline run with stats."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pipeline_runs SET
                    records_input = ?,
                    records_new = ?,
                    records_merged = ?,
                    multi_license_found = ?,
                    unicorns_found = ?,
                    run_duration_seconds = ?,
                    status = ?,
                    error_message = ?
                WHERE id = ?
            """, (records_input, records_new, records_merged,
                  multi_license_found, unicorns_found, duration_seconds,
                  status, error_message, run_id))

    def get_stats(self, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Get pipeline statistics.

        Args:
            state: Optional state filter. If None, returns all states.

        Returns:
            Dict with counts for contractors, contacts, licenses, etc.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            where_clause = "WHERE state = ?" if state else ""
            params = (state,) if state else ()

            # Total contractors
            cursor.execute(f"""
                SELECT COUNT(*) FROM contractors {where_clause}
            """, params)
            total_contractors = cursor.fetchone()[0]

            # With email
            cursor.execute(f"""
                SELECT COUNT(*) FROM contractors
                {where_clause + " AND" if state else "WHERE"}
                primary_email IS NOT NULL AND primary_email != ''
            """, params)
            with_email = cursor.fetchone()[0]

            # With phone
            cursor.execute(f"""
                SELECT COUNT(*) FROM contractors
                {where_clause + " AND" if state else "WHERE"}
                primary_phone IS NOT NULL AND primary_phone != ''
            """, params)
            with_phone = cursor.fetchone()[0]

            # Multi-license (2+)
            lic_where = "WHERE l.state = ?" if state else ""
            lic_params = (state,) if state else ()
            cursor.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM contractors c
                    JOIN licenses l ON c.id = l.contractor_id
                    {lic_where}
                    GROUP BY c.id
                    HAVING COUNT(DISTINCT l.license_category) >= 2
                )
            """, lic_params)
            multi_license = cursor.fetchone()[0]

            # Unicorns (3+)
            cursor.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM contractors c
                    JOIN licenses l ON c.id = l.contractor_id
                    {lic_where}
                    GROUP BY c.id
                    HAVING COUNT(DISTINCT l.license_category) >= 3
                )
            """, lic_params)
            unicorns = cursor.fetchone()[0]

            # Multi-license with email
            cursor.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM contractors c
                    JOIN licenses l ON c.id = l.contractor_id
                    WHERE c.primary_email IS NOT NULL AND c.primary_email != ''
                    {"AND l.state = ?" if state else ""}
                    GROUP BY c.id
                    HAVING COUNT(DISTINCT l.license_category) >= 2
                )
            """, lic_params)
            multi_license_with_email = cursor.fetchone()[0]

            # Total dedup matches
            cursor.execute("SELECT COUNT(*) FROM dedup_matches")
            total_dedup_matches = cursor.fetchone()[0]

            # Category distribution
            cursor.execute(f"""
                SELECT l.license_category, COUNT(DISTINCT c.id) as count
                FROM contractors c
                JOIN licenses l ON c.id = l.contractor_id
                {lic_where}
                GROUP BY l.license_category
                ORDER BY count DESC
            """, lic_params)
            categories = {row['license_category']: row['count'] for row in cursor.fetchall()}

            return {
                'total_contractors': total_contractors,
                'with_email': with_email,
                'with_phone': with_phone,
                'multi_license': multi_license,
                'unicorns': unicorns,
                'multi_license_with_email': multi_license_with_email,
                'total_dedup_matches': total_dedup_matches,
                'categories': categories,
                'state': state or 'ALL'
            }

    def get_multi_license_contractors(
        self,
        state: Optional[str] = None,
        min_categories: int = 2,
        require_email: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get multi-license contractors with full details.

        Args:
            state: Optional state filter
            min_categories: Minimum number of license categories (default 2)
            require_email: Only return contractors with email

        Returns:
            List of contractor dicts with categories, contacts, etc.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            email_clause = "AND c.primary_email IS NOT NULL AND c.primary_email != ''" if require_email else ""
            state_clause = "AND l.state = ?" if state else ""
            params = (state,) if state else ()

            cursor.execute(f"""
                SELECT
                    c.id,
                    c.company_name,
                    c.city,
                    c.state,
                    c.zip,
                    c.primary_phone,
                    c.primary_email,
                    GROUP_CONCAT(DISTINCT l.license_type) as license_types,
                    GROUP_CONCAT(DISTINCT l.license_category) as categories,
                    COUNT(DISTINCT l.license_category) as category_count
                FROM contractors c
                JOIN licenses l ON c.id = l.contractor_id
                WHERE 1=1 {email_clause} {state_clause}
                GROUP BY c.id
                HAVING category_count >= ?
                ORDER BY category_count DESC, c.company_name
            """, params + (min_categories,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'company_name': row['company_name'],
                    'city': row['city'],
                    'state': row['state'],
                    'zip': row['zip'],
                    'phone': row['primary_phone'],
                    'email': row['primary_email'],
                    'license_types': row['license_types'],
                    'categories': row['categories'],
                    'category_count': row['category_count']
                })

            return results

    def export_multi_license(
        self,
        output_path: Path,
        state: Optional[str] = None,
        min_categories: int = 2,
        require_email: bool = True
    ) -> int:
        """
        Export multi-license contractors to CSV.

        Args:
            output_path: Path for output CSV
            state: Optional state filter
            min_categories: Minimum categories (default 2)
            require_email: Only export with email (default True)

        Returns:
            Number of records exported
        """
        contractors = self.get_multi_license_contractors(
            state=state,
            min_categories=min_categories,
            require_email=require_email
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if not contractors:
                return 0

            writer = csv.DictWriter(f, fieldnames=contractors[0].keys())
            writer.writeheader()
            writer.writerows(contractors)

        return len(contractors)

    def export_unicorns(
        self,
        output_path: Path,
        state: Optional[str] = None
    ) -> int:
        """Export unicorn contractors (3+ categories) to CSV."""
        return self.export_multi_license(
            output_path,
            state=state,
            min_categories=3,
            require_email=True
        )

    def export_to_json(
        self,
        output_path: Path,
        state: Optional[str] = None,
        min_categories: int = 2,
        require_email: bool = True
    ) -> int:
        """
        Export contractors to JSON format.

        Args:
            output_path: Path for output JSON file
            state: Optional state filter
            min_categories: Minimum categories (default 2)
            require_email: Only export with email (default True)

        Returns:
            Number of records exported
        """
        contractors = self.get_multi_license_contractors(
            state=state,
            min_categories=min_categories,
            require_email=require_email
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'state': state or 'ALL',
                'min_categories': min_categories,
                'require_email': require_email,
                'export_timestamp': datetime.now().isoformat(),
                'total_count': len(contractors),
                'contractors': contractors
            }, f, indent=2, default=str)

        logger.info(f"Exported {len(contractors)} contractors to {output_path}")
        return len(contractors)

    def export_stats_to_json(
        self,
        output_path: Path,
        state: Optional[str] = None
    ) -> None:
        """
        Export pipeline statistics to JSON format.

        Useful for tracking progress across runs.
        """
        stats = self.get_stats(state=state)
        runs = self.get_pipeline_runs(state=state, limit=50)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'export_timestamp': datetime.now().isoformat(),
                'stats': stats,
                'recent_runs': runs
            }, f, indent=2, default=str)

        logger.info(f"Exported stats to {output_path}")

    def get_contractor_by_id(self, contractor_id: int) -> Optional[Dict[str, Any]]:
        """Get a single contractor by ID with all related data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM contractors WHERE id = ?
            """, (contractor_id,))
            row = cursor.fetchone()
            if not row:
                return None

            contractor = dict(row)

            # Get contacts
            cursor.execute("""
                SELECT * FROM contacts WHERE contractor_id = ?
            """, (contractor_id,))
            contractor['contacts'] = [dict(r) for r in cursor.fetchall()]

            # Get licenses
            cursor.execute("""
                SELECT * FROM licenses WHERE contractor_id = ?
            """, (contractor_id,))
            contractor['licenses'] = [dict(r) for r in cursor.fetchall()]

            # Get OEM certifications
            cursor.execute("""
                SELECT * FROM oem_certifications WHERE contractor_id = ?
            """, (contractor_id,))
            contractor['oem_certifications'] = [dict(r) for r in cursor.fetchall()]

            return contractor

    def search_contractors(
        self,
        query: str,
        state: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search contractors by name, phone, or email."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query_lower = query.lower()
            query_phone = normalize_phone(query)
            state_clause = "AND state = ?" if state else ""
            params = [f"%{query_lower}%", f"%{query_lower}%"]
            if query_phone:
                params.append(query_phone)
            if state:
                params.append(state)

            cursor.execute(f"""
                SELECT
                    c.*,
                    GROUP_CONCAT(DISTINCT l.license_category) as categories
                FROM contractors c
                LEFT JOIN licenses l ON c.id = l.contractor_id
                WHERE (
                    LOWER(c.company_name) LIKE ?
                    OR LOWER(c.primary_email) LIKE ?
                    {f"OR c.primary_phone = ?" if query_phone else ""}
                )
                {state_clause}
                GROUP BY c.id
                LIMIT ?
            """, params + [limit])

            return [dict(row) for row in cursor.fetchall()]

    def get_pipeline_runs(
        self,
        state: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent pipeline runs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            state_clause = "WHERE state = ?" if state else ""
            params = (state,) if state else ()

            cursor.execute(f"""
                SELECT * FROM pipeline_runs
                {state_clause}
                ORDER BY run_timestamp DESC
                LIMIT ?
            """, params + (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def reset_database(self, confirm: bool = False) -> None:
        """
        Drop all tables and recreate schema.

        WARNING: This deletes all data!

        Args:
            confirm: Must be True to execute
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to reset database")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Drop all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                if not table.startswith('sqlite_'):
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")

            # Drop all views
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
            views = [row[0] for row in cursor.fetchall()]
            for view in views:
                cursor.execute(f"DROP VIEW IF EXISTS {view}")

        # Recreate schema
        self.initialize()


# Convenience function for quick access
def get_db(db_path: Optional[Path] = None) -> PipelineDB:
    """Get a PipelineDB instance."""
    return PipelineDB(db_path)
