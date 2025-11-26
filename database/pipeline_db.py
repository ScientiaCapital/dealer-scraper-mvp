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
import socket
import os
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
from database.audit import FileFingerprint, ImportLock, AuditTrail


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

    def add_oem_certification(
        self,
        contractor_id: int,
        oem_name: str,
        certification_tier: str = "",
        scraped_from_zip: str = "",
        source_url: str = ""
    ) -> int:
        """
        Add an OEM certification to an existing contractor.

        Args:
            contractor_id: ID of the contractor
            oem_name: OEM name (e.g., 'Generac', 'Tesla', 'Carrier')
            certification_tier: Tier level (e.g., 'Premier', 'Elite')
            scraped_from_zip: ZIP code from which this was scraped
            source_url: URL source of the data

        Returns:
            ID of the certification record, or 0 if already exists
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip, source_url)
                VALUES (?, ?, ?, ?, ?)
            """, (contractor_id, oem_name, certification_tier, scraped_from_zip, source_url))
            return cursor.lastrowid or 0

    def update_source_type(
        self,
        contractor_id: int,
        source_type: str
    ) -> None:
        """
        Update the source_type of a contractor.

        Use when an OEM dealer matches an existing state license contractor
        to mark them as 'both'.

        Args:
            contractor_id: ID of the contractor
            source_type: New source type ('state_license', 'oem_dealer', 'both')
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contractors SET source_type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (source_type, contractor_id))

    def create_contractor_from_oem(
        self,
        oem_record: Dict[str, Any],
        oem_name: str,
        source_type: str = "oem_dealer"
    ) -> int:
        """
        Create a new contractor from OEM dealer data.

        Used when an OEM dealer doesn't match any existing contractor.

        Args:
            oem_record: Dict with OEM dealer fields (name, phone, domain, etc.)
            oem_name: OEM source (e.g., 'Generac', 'Carrier')
            source_type: Source type to set (default 'oem_dealer')

        Returns:
            ID of the newly created contractor
        """
        # Extract and normalize fields
        company_name = oem_record.get('name', '').strip()
        phone = normalize_phone(oem_record.get('phone', ''))
        email = normalize_email(oem_record.get('email', ''))
        domain = oem_record.get('domain', '') or extract_domain(email)
        street = oem_record.get('street', '') or oem_record.get('address', '')
        city = oem_record.get('city', '').strip()
        state = oem_record.get('state', '').upper().strip()
        zip_code = oem_record.get('zip', '').strip()
        normalized_name = normalize_company_name(company_name)

        # OEM-specific fields
        tier = oem_record.get('tier', '')
        scraped_from_zip = oem_record.get('scraped_from_zip', '')
        website = oem_record.get('website', '') or oem_record.get('website_url', '')

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create contractor
            cursor.execute("""
                INSERT INTO contractors
                (company_name, normalized_name, street, city, state, zip,
                 primary_phone, primary_email, primary_domain, source_type, website_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_name, normalized_name, street, city, state, zip_code,
                phone, email, domain, source_type, website
            ))
            contractor_id = cursor.lastrowid

            # Add OEM certification
            cursor.execute("""
                INSERT OR IGNORE INTO oem_certifications
                (contractor_id, oem_name, certification_tier, scraped_from_zip)
                VALUES (?, ?, ?, ?)
            """, (contractor_id, oem_name, tier, scraped_from_zip))

            return contractor_id

    def find_matching_contractor(
        self,
        phone: str,
        domain: str,
        name: str,
        state: str
    ) -> Optional[int]:
        """
        Find a matching contractor by phone, domain, or fuzzy name.

        Public wrapper around _find_duplicate for OEM import use.

        Args:
            phone: Normalized phone number
            domain: Company domain
            name: Company name
            state: State code

        Returns:
            contractor_id if found, None otherwise
        """
        normalized_name = normalize_company_name(name)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            contractor_id, _, _ = self._find_duplicate(
                cursor,
                normalize_phone(phone),
                '',
                domain,
                normalized_name,
                state
            )
            return contractor_id

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

    # ========== AUDIT TRAIL METHODS ==========

    def check_file_imported(self, file_path: Path) -> Optional[Dict]:
        """
        Check if a file has already been imported.

        Calculates file hash and checks file_imports table for matching record.
        Prevents accidental duplicate imports of the same source file.

        Args:
            file_path: Path to file to check

        Returns:
            Dictionary with import record if file already imported, None if new file:
                - id: file_import_id
                - file_name: Original filename
                - file_hash: SHA256 hash
                - file_size: Size in bytes
                - row_count: Number of rows
                - status: 'completed', 'failed', or 'in_progress'
                - import_started_at: Timestamp
                - import_completed_at: Timestamp (if completed)

        Example:
            >>> existing = db.check_file_imported(Path("fl_licenses.csv"))
            >>> if existing:
            >>>     print(f"File already imported on {existing['import_started_at']}")
            >>> else:
            >>>     print("New file - safe to import")
        """
        file_info = FileFingerprint.get_file_info(file_path)
        file_hash = file_info['file_hash']

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, file_name, file_hash, file_size_bytes, row_count,
                       import_status, import_started_at, import_completed_at
                FROM file_imports
                WHERE file_hash = ?
            """, (file_hash,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def start_file_import(self, file_path: Path, source_type: str) -> int:
        """
        Start a new file import with audit tracking.

        Checks for duplicate file, acquires import lock, and creates
        file_imports record with 'in_progress' status.

        Args:
            file_path: Path to file being imported
            source_type: Source identifier (e.g., 'FL_DBPR', 'CA_CSLB', 'TX_TDLR')

        Returns:
            file_import_id: ID for tracking this import

        Raises:
            ValueError: If file already imported or import lock is held

        Example:
            >>> file_import_id = db.start_file_import(
            >>>     Path("fl_licenses.csv"),
            >>>     source_type="FL_DBPR"
            >>> )
            >>> try:
            >>>     # Import records with audit trail
            >>>     for record in records:
            >>>         contractor_id, is_new = db.add_contractor_with_audit(
            >>>             record, file_import_id, source="FL_DBPR"
            >>>         )
            >>>     db.complete_file_import(file_import_id, stats)
            >>> except Exception as e:
            >>>     db.fail_file_import(file_import_id, str(e))
        """
        file_path = Path(file_path)

        # Check if already imported
        existing = self.check_file_imported(file_path)
        if existing:
            raise ValueError(
                f"File already imported: {existing['file_name']} "
                f"on {existing['import_started_at']} (status: {existing['import_status']})"
            )

        # Calculate file fingerprint
        file_info = FileFingerprint.get_file_info(file_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Acquire import lock
            lock = ImportLock(conn)
            lock_acquired = lock.acquire(reason=f"{source_type}: {file_info['file_name']}")
            if not lock_acquired:
                lock_info = lock.check_lock()
                raise ValueError(
                    f"Import locked by {lock_info['lock_holder']} "
                    f"({lock_info['reason']}) for {lock_info['age_minutes']:.1f} minutes"
                )

            # Insert file_imports record
            hostname = socket.gethostname()
            username = os.getenv('USER', 'unknown')

            cursor.execute("""
                INSERT INTO file_imports (
                    file_name, file_path, file_hash, file_size_bytes, row_count,
                    source_type, import_status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'in_progress')
            """, (
                file_info['file_name'],
                str(file_path.absolute()),
                file_info['file_hash'],
                file_info['file_size'],
                file_info['row_count'],
                source_type
            ))

            file_import_id = cursor.lastrowid

            logger.info(
                f"Started import {file_import_id}: {file_info['file_name']} "
                f"({file_info['row_count']} rows, {file_info['file_size']} bytes)"
            )

            return file_import_id

    def complete_file_import(self, file_import_id: int, stats: Dict) -> None:
        """
        Mark file import as completed with statistics.

        Updates file_imports record with 'completed' status, completion timestamp,
        and import statistics. Releases import lock.

        Args:
            file_import_id: ID from start_file_import()
            stats: Dictionary with import statistics:
                - records_input: Total records in file
                - records_new: New contractors created
                - records_merged: Duplicates merged
                - multi_license_found: Multi-license contractors found
                - unicorns_found: Unicorns (3+ licenses) found
                - duration_seconds: Import duration

        Example:
            >>> stats = {
            >>>     'records_input': 50000,
            >>>     'records_new': 45000,
            >>>     'records_merged': 5000,
            >>>     'multi_license_found': 2500,
            >>>     'unicorns_found': 300,
            >>>     'duration_seconds': 120.5
            >>> }
            >>> db.complete_file_import(file_import_id, stats)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE file_imports SET
                    import_status = 'completed',
                    import_completed_at = ?,
                    records_created = ?,
                    records_updated = ?,
                    records_merged = ?,
                    records_skipped = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                stats.get('created', stats.get('records_created', 0)),
                stats.get('updated', stats.get('records_updated', 0)),
                stats.get('merged', stats.get('records_merged', 0)),
                stats.get('skipped', stats.get('records_skipped', 0)),
                file_import_id
            ))

            # Release import lock
            lock = ImportLock(conn)
            if not lock.release():
                logger.warning(
                    f"Import lock was not held during completion of import {file_import_id}. "
                    f"Lock may have expired or been manually released."
                )

            logger.info(
                f"Completed import {file_import_id}: "
                f"{stats.get('records_new', 0)} new, "
                f"{stats.get('records_merged', 0)} merged, "
                f"{stats.get('multi_license_found', 0)} multi-license"
            )

    def fail_file_import(self, file_import_id: int, error: str) -> None:
        """
        Mark file import as failed with error message.

        Updates file_imports record with 'failed' status and error message.
        Releases import lock.

        Args:
            file_import_id: ID from start_file_import()
            error: Error message describing failure

        Example:
            >>> try:
            >>>     file_import_id, audit = db.start_file_import(...)
            >>>     # Import logic
            >>> except Exception as e:
            >>>     db.fail_file_import(file_import_id, str(e))
            >>>     raise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE file_imports SET
                    import_status = 'failed',
                    error_message = ?
                WHERE id = ?
            """, (error, file_import_id))

            # Release import lock
            lock = ImportLock(conn)
            if not lock.release():
                logger.warning(
                    f"Import lock was not held during failure of import {file_import_id}. "
                    f"Lock may have expired or been manually released."
                )

            logger.error(f"Failed import {file_import_id}: {error}")

    def add_contractor_with_audit(
        self,
        record: Dict[str, Any],
        file_import_id: int,
        source: str = "unknown"
    ) -> Tuple[int, bool]:
        """
        Add contractor with audit trail logging.

        Calls existing add_contractor() logic and logs INSERT or MERGE
        to audit trail for full change tracking.

        Args:
            record: Contractor record dictionary (same as add_contractor)
            file_import_id: ID from start_file_import() for linking audit trail
            source: Source identifier (e.g., 'FL_DBPR')

        Returns:
            Tuple of (contractor_id, is_new):
                - contractor_id: ID of contractor (new or existing)
                - is_new: True if new contractor, False if merged into existing

        Example:
            >>> file_import_id = db.start_file_import(path, "FL_DBPR")
            >>> for record in csv_records:
            >>>     contractor_id, is_new = db.add_contractor_with_audit(
            >>>         record, file_import_id, source="FL_DBPR"
            >>>     )
            >>>     if is_new:
            >>>         print(f"Created contractor {contractor_id}")
            >>> db.complete_file_import(file_import_id, stats)
        """
        # Call existing add_contractor logic
        contractor_id, is_new = self.add_contractor(record, source=source)

        # Log to audit trail (create fresh connection for each entry)
        with self._get_connection() as conn:
            audit = AuditTrail(conn, source=source, file_import_id=file_import_id)

            if is_new:
                # New contractor - log INSERT
                audit.log_insert(
                    contractor_id=contractor_id,
                    new_values={
                        'company_name': record.get('company_name', ''),
                        'city': record.get('city', ''),
                        'state': record.get('state', ''),
                        'phone': record.get('phone', ''),
                        'email': record.get('email', ''),
                        'license_type': record.get('license_type', ''),
                        'license_number': record.get('license_number', '')
                    }
                )
            else:
                # Merged into existing - log MERGE
                audit.log_merge(
                    master_id=contractor_id,
                    merged_id=0,  # Don't have duplicate ID (not created)
                    merged_values={
                        'company_name': record.get('company_name', ''),
                        'phone': record.get('phone', ''),
                        'email': record.get('email', '')
                    }
                )

            # Flush audit entry immediately
            audit.flush(commit=False)  # Let context manager commit

        return contractor_id, is_new

    def soft_delete_contractor(
        self,
        contractor_id: int,
        reason: str,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Soft delete a contractor record.

        Sets is_deleted=1 flag and logs deletion reason. Does not actually
        remove record from database (preserves audit trail).

        Args:
            contractor_id: ID of contractor to delete
            reason: Reason for deletion (e.g., 'Duplicate of ID 123', 'Invalid data')
            conn: Optional connection to use (for transactional rollback scenarios)

        Returns:
            True if contractor deleted, False if not found

        Example:
            >>> deleted = db.soft_delete_contractor(
            >>>     contractor_id=123,
            >>>     reason="Duplicate of contractor_id=456"
            >>> )
            >>> if deleted:
            >>>     print("Contractor soft deleted")
        """
        # Determine if we need to manage our own connection
        manage_conn = conn is None

        if manage_conn:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")

        try:
            cursor = conn.cursor()

            # Get current contractor values for audit log
            cursor.execute("""
                SELECT company_name, city, state, primary_phone, primary_email
                FROM contractors
                WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0)
            """, (contractor_id,))

            row = cursor.fetchone()
            if not row:
                return False

            old_values = dict(row)

            # Soft delete
            hostname = socket.gethostname()
            username = os.getenv('USER', 'unknown')
            deleted_by = f"{username}@{hostname}"

            cursor.execute("""
                UPDATE contractors SET
                    is_deleted = 1,
                    deleted_at = ?,
                    deleted_by = ?,
                    deletion_reason = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                deleted_by,
                reason,
                contractor_id
            ))

            # Log DELETE to audit trail
            audit = AuditTrail(conn, source="manual_delete")
            audit.log_delete(
                contractor_id=contractor_id,
                old_values=old_values,
                reason=reason
            )
            audit.flush(commit=False)  # Don't commit yet - let caller handle transaction

            if manage_conn:
                conn.commit()

            logger.info(f"Soft deleted contractor {contractor_id}: {reason}")

            return True
        except Exception:
            if manage_conn:
                conn.rollback()
            raise
        finally:
            if manage_conn:
                conn.close()

    def get_contractor_history(self, contractor_id: int) -> List[Dict]:
        """
        Get full change history for a contractor.

        Retrieves all audit trail records showing how contractor record
        has evolved over time (inserts, updates, merges, deletes).

        Args:
            contractor_id: ID of contractor

        Returns:
            List of change records (newest first), each with:
                - id: History record ID
                - contractor_id: Contractor ID
                - change_type: 'INSERT', 'UPDATE', 'DELETE', or 'MERGE'
                - old_values: Dictionary of old values (parsed from JSON)
                - new_values: Dictionary of new values (parsed from JSON)
                - source: Source identifier
                - file_import_id: Associated import ID
                - created_at: Timestamp

        Example:
            >>> history = db.get_contractor_history(contractor_id=123)
            >>> for change in history:
            >>>     print(f"{change['created_at']}: {change['change_type']}")
            >>>     if change['new_values']:
            >>>         print(f"  New: {change['new_values']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    contractor_id,
                    change_type,
                    old_values,
                    new_values,
                    source,
                    file_import_id,
                    created_at
                FROM contractor_history
                WHERE contractor_id = ?
                ORDER BY created_at DESC
            """, (contractor_id,))

            results = []
            for row in cursor.fetchall():
                record = dict(row)

                # Parse JSON values with error handling
                try:
                    if record['old_values']:
                        record['old_values'] = json.loads(record['old_values'])
                    if record['new_values']:
                        record['new_values'] = json.loads(record['new_values'])
                except json.JSONDecodeError as e:
                    logger.warning(f"Corrupted JSON in history record {record['id']}: {e}")
                    # Keep as string if parsing fails (already in record from dict(row))

                results.append(record)

            return results

    def rollback_import(self, file_import_id: int) -> int:
        """
        Rollback a file import by soft-deleting all created contractors.

        Finds all contractors created in this import and soft-deletes them.
        Updates file_imports status to 'rolled_back'.

        Args:
            file_import_id: ID of import to rollback

        Returns:
            Number of contractors rolled back (soft-deleted)

        Example:
            >>> # Oops, imported wrong file!
            >>> rolled_back = db.rollback_import(file_import_id=123)
            >>> print(f"Rolled back {rolled_back} contractors")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Find all contractors created in this import
            # (Look for INSERT records in contractor_history)
            cursor.execute("""
                SELECT DISTINCT contractor_id
                FROM contractor_history
                WHERE file_import_id = ? AND change_type = 'INSERT'
            """, (file_import_id,))

            contractor_ids = [row[0] for row in cursor.fetchall()]

            if not contractor_ids:
                logger.warning(f"No contractors found for import {file_import_id}")
                return 0

            # Soft delete each contractor atomically using the shared connection
            rollback_count = 0
            for contractor_id in contractor_ids:
                deleted = self.soft_delete_contractor(
                    contractor_id,
                    reason=f"Rollback of import {file_import_id}",
                    conn=conn  # Pass connection for atomicity
                )
                if deleted:
                    rollback_count += 1

            # Update file_imports status
            cursor.execute("""
                UPDATE file_imports SET
                    import_status = 'rolled_back'
                WHERE id = ?
            """, (file_import_id,))

            logger.info(
                f"Rolled back import {file_import_id}: "
                f"{rollback_count} contractors soft-deleted"
            )

            return rollback_count

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
