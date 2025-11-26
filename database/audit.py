"""
Audit Trail Module

Provides comprehensive change tracking for all database operations:
- FileFingerprint: Prevent duplicate file imports via SHA256 hashing
- ImportLock: Prevent concurrent imports with auto-expiring singleton lock
- AuditTrail: Batch-write change history with before/after values

Usage:
    from database.audit import FileFingerprint, ImportLock, AuditTrail

    # Check if file already imported
    file_info = FileFingerprint.get_file_info(Path("data.csv"))

    # Acquire import lock
    lock = ImportLock(conn)
    if lock.acquire(reason="FL license import"):
        try:
            # Import data with audit trail
            audit = AuditTrail(conn, source="FL_DBPR", file_import_id=123)
            audit.log_insert(contractor_id=1, new_values={"name": "ABC Solar"})
            audit.flush()
        finally:
            lock.release()
"""

import hashlib
import json
import os
import socket
from datetime import datetime, timedelta
from pathlib import Path
from sqlite3 import Connection
from typing import Any, Dict, List, Optional
import csv


class FileFingerprint:
    """Calculate and verify file fingerprints for duplicate import detection."""

    @staticmethod
    def calculate_hash(file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate SHA256 hash of file content.

        Reads file in chunks to handle large files efficiently.

        Args:
            file_path: Path to file
            chunk_size: Bytes to read per chunk (default 8KB)

        Returns:
            Hex string of SHA256 hash

        Example:
            >>> hash_val = FileFingerprint.calculate_hash(Path("data.csv"))
            >>> print(hash_val)
            'a3f2b1c4d5e6...'
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def count_rows(file_path: Path) -> int:
        """
        Count rows in CSV (excluding header).

        Args:
            file_path: Path to CSV file

        Returns:
            Number of data rows (excludes header)

        Example:
            >>> count = FileFingerprint.count_rows(Path("data.csv"))
            >>> print(f"Data rows: {count}")
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            # Skip header
            next(reader, None)
            # Count remaining rows
            return sum(1 for _ in reader)

    @staticmethod
    def get_file_info(file_path: Path) -> Dict[str, Any]:
        """
        Get comprehensive file information for import tracking.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with keys:
                - file_name: Name of file
                - file_size: Size in bytes
                - file_hash: SHA256 hash
                - row_count: Number of data rows (CSV only)

        Example:
            >>> info = FileFingerprint.get_file_info(Path("data.csv"))
            >>> print(f"Hash: {info['file_hash']}, Rows: {info['row_count']}")
        """
        file_path = Path(file_path)  # Ensure Path object

        info = {
            'file_name': file_path.name,
            'file_size': file_path.stat().st_size,
            'file_hash': FileFingerprint.calculate_hash(file_path),
            'row_count': 0
        }

        # Count rows if CSV
        if file_path.suffix.lower() == '.csv':
            info['row_count'] = FileFingerprint.count_rows(file_path)

        return info


class ImportLock:
    """
    Prevent concurrent imports using database lock table with auto-expiry.

    Uses a singleton pattern (id=1) to ensure only one import at a time.
    Locks automatically expire after LOCK_TIMEOUT_MINUTES to prevent
    deadlocks from crashed processes.
    """

    LOCK_TIMEOUT_MINUTES = 30

    def __init__(self, conn: Connection) -> None:
        """
        Initialize lock manager.

        Args:
            conn: SQLite database connection
        """
        self.conn = conn
        self.lock_holder = f"{socket.gethostname()}:{os.getpid()}:{datetime.now().isoformat()}"

    def acquire(self, reason: str = "") -> bool:
        """
        Attempt to acquire import lock.

        Args:
            reason: Description of import operation (for debugging)

        Returns:
            True if lock acquired, False if lock already held by another process

        Example:
            >>> lock = ImportLock(conn)
            >>> if lock.acquire(reason="FL license import"):
            >>>     try:
            >>>         # Do import
            >>>         pass
            >>>     finally:
            >>>         lock.release()
        """
        cursor = self.conn.cursor()

        # First, clean up expired locks
        expiry_time = datetime.now() - timedelta(minutes=self.LOCK_TIMEOUT_MINUTES)
        cursor.execute("""
            DELETE FROM import_locks
            WHERE created_at < ?
        """, (expiry_time.isoformat(),))

        # Try to acquire lock (singleton id=1)
        try:
            cursor.execute("""
                INSERT INTO import_locks (id, lock_holder, reason, created_at)
                VALUES (1, ?, ?, ?)
            """, (self.lock_holder, reason, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception:
            # Lock already exists
            self.conn.rollback()
            return False

    def release(self) -> bool:
        """
        Release the import lock.

        Returns:
            True if lock released, False if lock was not held

        Example:
            >>> lock.release()
            True
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            DELETE FROM import_locks
            WHERE id = 1 AND lock_holder = ?
        """, (self.lock_holder,))

        deleted = cursor.rowcount > 0
        self.conn.commit()
        return deleted

    def check_lock(self) -> Optional[Dict[str, Any]]:
        """
        Check current lock status without acquiring.

        Returns:
            Dictionary with lock info if locked, None if available:
                - lock_holder: Process identifier
                - reason: Import description
                - created_at: Lock acquisition time
                - age_minutes: How long lock has been held

        Example:
            >>> lock_info = lock.check_lock()
            >>> if lock_info:
            >>>     print(f"Locked by {lock_info['lock_holder']}")
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT lock_holder, reason, created_at
            FROM import_locks
            WHERE id = 1
        """)

        row = cursor.fetchone()
        if not row:
            return None

        created_at = datetime.fromisoformat(row[2])
        age = datetime.now() - created_at

        return {
            'lock_holder': row[0],
            'reason': row[1],
            'created_at': row[2],
            'age_minutes': age.total_seconds() / 60
        }


class AuditTrail:
    """
    Batch-write change history with before/after values.

    Efficiently logs all database changes (INSERT/UPDATE/DELETE/MERGE)
    with full before/after snapshots. Uses batching for performance.
    """

    def __init__(self, conn: Connection, source: str = "unknown", file_import_id: Optional[int] = None) -> None:
        """
        Initialize audit trail logger.

        Args:
            conn: SQLite database connection
            source: Source identifier (e.g., "FL_DBPR", "CA_CSLB", "TX_TDLR")
            file_import_id: ID from file_imports table (if applicable)

        Example:
            >>> audit = AuditTrail(conn, source="FL_DBPR", file_import_id=123)
        """
        self.conn = conn
        self.source = source
        self.file_import_id = file_import_id
        self._batch: List[Dict] = []
        self._batch_size = 1000

    def log_insert(self, contractor_id: int, new_values: Dict[str, Any]) -> None:
        """
        Log INSERT operation.

        Args:
            contractor_id: ID of newly created contractor
            new_values: Dictionary of field values inserted

        Example:
            >>> audit.log_insert(
            >>>     contractor_id=123,
            >>>     new_values={
            >>>         'company_name': 'ABC Solar LLC',
            >>>         'state': 'FL',
            >>>         'city': 'Miami'
            >>>     }
            >>> )
        """
        self._add_to_batch(
            contractor_id=contractor_id,
            change_type='INSERT',
            old_values=None,
            new_values=new_values
        )

    def log_update(self, contractor_id: int, old_values: Dict[str, Any],
                   new_values: Dict[str, Any]) -> None:
        """
        Log UPDATE operation - only stores CHANGED fields.

        Automatically detects which fields changed and only logs those
        in the before/after snapshots for efficiency.

        Args:
            contractor_id: ID of contractor being updated
            old_values: Dictionary of old field values
            new_values: Dictionary of new field values

        Example:
            >>> audit.log_update(
            >>>     contractor_id=123,
            >>>     old_values={'city': 'Miami', 'state': 'FL'},
            >>>     new_values={'city': 'Tampa', 'state': 'FL'}
            >>> )
            # Only logs: old_values={'city': 'Miami'}, new_values={'city': 'Tampa'}
        """
        # Only log changed fields
        changed_old = {}
        changed_new = {}

        for key in new_values:
            old_val = old_values.get(key)
            new_val = new_values.get(key)

            # Compare values (handle None vs empty string)
            if old_val != new_val:
                changed_old[key] = old_val
                changed_new[key] = new_val

        # Only log if there were actual changes
        if changed_old or changed_new:
            self._add_to_batch(
                contractor_id=contractor_id,
                change_type='UPDATE',
                old_values=changed_old,
                new_values=changed_new
            )

    def log_delete(self, contractor_id: int, old_values: Dict[str, Any],
                   reason: str = "") -> None:
        """
        Log DELETE operation.

        Args:
            contractor_id: ID of contractor being deleted
            old_values: Dictionary of field values before deletion
            reason: Optional reason for deletion

        Example:
            >>> audit.log_delete(
            >>>     contractor_id=123,
            >>>     old_values={'company_name': 'ABC Solar LLC'},
            >>>     reason='Duplicate of contractor_id=456'
            >>> )
        """
        # Add reason to old_values if provided
        if reason:
            old_values = {**old_values, '_delete_reason': reason}

        self._add_to_batch(
            contractor_id=contractor_id,
            change_type='DELETE',
            old_values=old_values,
            new_values=None
        )

    def log_merge(self, master_id: int, merged_id: int,
                  merged_values: Dict[str, Any]) -> None:
        """
        Log MERGE operation (deduplication).

        Records when duplicate contractors are merged together,
        tracking which record was kept (master) and which was merged.

        Args:
            master_id: ID of contractor that was kept (master record)
            merged_id: ID of contractor that was merged (duplicate)
            merged_values: Dictionary of values from merged record

        Example:
            >>> audit.log_merge(
            >>>     master_id=123,
            >>>     merged_id=456,
            >>>     merged_values={'company_name': 'ABC Solar', 'phone': '5551234567'}
            >>> )
        """
        # Add merge metadata to values
        merge_info = {
            **merged_values,
            '_merged_id': merged_id,
            '_master_id': master_id
        }

        self._add_to_batch(
            contractor_id=master_id,
            change_type='MERGE',
            old_values=None,
            new_values=merge_info
        )

    def flush(self) -> int:
        """
        Write batch to database.

        Returns:
            Number of audit records written

        Example:
            >>> count = audit.flush()
            >>> print(f"Wrote {count} audit records")
        """
        if not self._batch:
            return 0

        cursor = self.conn.cursor()

        # Prepare batch for executemany
        rows = [
            (
                record['contractor_id'],
                record['change_type'],
                record['old_values_json'],
                record['new_values_json'],
                self.source,
                self.file_import_id,
                record['created_at']
            )
            for record in self._batch
        ]

        cursor.executemany("""
            INSERT INTO audit_trail (
                contractor_id,
                change_type,
                old_values,
                new_values,
                source,
                file_import_id,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)

        self.conn.commit()

        count = len(self._batch)
        self._batch.clear()
        return count

    def _add_to_batch(self, contractor_id: int, change_type: str,
                      old_values: Optional[Dict[str, Any]],
                      new_values: Optional[Dict[str, Any]]) -> None:
        """
        Add change to batch, auto-flush if batch size reached.

        Args:
            contractor_id: ID of contractor
            change_type: 'INSERT', 'UPDATE', 'DELETE', or 'MERGE'
            old_values: Dictionary of old values (or None)
            new_values: Dictionary of new values (or None)
        """
        record = {
            'contractor_id': contractor_id,
            'change_type': change_type,
            'old_values_json': json.dumps(old_values) if old_values else None,
            'new_values_json': json.dumps(new_values) if new_values else None,
            'created_at': datetime.now().isoformat()
        }

        self._batch.append(record)

        # Auto-flush if batch size reached
        if len(self._batch) >= self._batch_size:
            self.flush()
