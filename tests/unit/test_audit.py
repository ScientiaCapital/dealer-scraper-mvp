"""
Unit Tests for Audit Trail Module

Tests FileFingerprint, ImportLock, and AuditTrail classes.
"""

import json
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from database.audit import FileFingerprint, ImportLock, AuditTrail


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("name,email,phone\n")
        f.write("ABC Solar,info@abc.com,5551234567\n")
        f.write("XYZ Energy,contact@xyz.com,5559876543\n")
        f.write("DEF Power,admin@def.com,5555555555\n")
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database with audit tables."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create contractor_history table (matches schema.sql)
    cursor.execute("""
        CREATE TABLE contractor_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            source TEXT,
            file_import_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create import_locks table (matches schema.sql)
    cursor.execute("""
        CREATE TABLE import_locks (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            lock_holder TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            reason TEXT
        )
    """)

    # Create file_imports table (for reference)
    cursor.execute("""
        CREATE TABLE file_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            file_size INTEGER,
            row_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    yield conn
    conn.close()


# ============================================
# FileFingerprint Tests
# ============================================

def test_calculate_hash(temp_csv):
    """Test SHA256 hash calculation."""
    hash1 = FileFingerprint.calculate_hash(temp_csv)

    # Hash should be consistent
    hash2 = FileFingerprint.calculate_hash(temp_csv)
    assert hash1 == hash2

    # Hash should be 64 hex characters (SHA256)
    assert len(hash1) == 64
    assert all(c in '0123456789abcdef' for c in hash1)


def test_count_rows(temp_csv):
    """Test CSV row counting (excludes header)."""
    count = FileFingerprint.count_rows(temp_csv)
    assert count == 3  # 3 data rows (header excluded)


def test_get_file_info(temp_csv):
    """Test comprehensive file info extraction."""
    info = FileFingerprint.get_file_info(temp_csv)

    assert 'file_name' in info
    assert 'file_size' in info
    assert 'file_hash' in info
    assert 'row_count' in info

    assert info['file_name'].endswith('.csv')
    assert info['file_size'] > 0
    assert len(info['file_hash']) == 64
    assert info['row_count'] == 3


def test_file_info_non_csv(tmp_path):
    """Test file info for non-CSV files."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello World")

    info = FileFingerprint.get_file_info(txt_file)

    assert info['file_name'] == 'test.txt'
    assert info['file_size'] == 11  # "Hello World" = 11 bytes
    assert len(info['file_hash']) == 64
    assert info['row_count'] == 0  # Non-CSV has 0 row count


# ============================================
# ImportLock Tests
# ============================================

def test_acquire_lock_success(test_db):
    """Test successful lock acquisition."""
    lock = ImportLock(test_db)
    acquired = lock.acquire(reason="Test import")

    assert acquired is True

    # Verify lock exists in database
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM import_locks WHERE id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert 'Test import' in row[4]  # reason column (index: id=0, lock_holder=1, created_at=2, expires_at=3, reason=4)


def test_acquire_lock_failure_already_held(test_db):
    """Test lock acquisition fails when already held."""
    lock1 = ImportLock(test_db)
    lock2 = ImportLock(test_db)

    # First lock succeeds
    assert lock1.acquire(reason="First import") is True

    # Second lock fails (already held)
    assert lock2.acquire(reason="Second import") is False


def test_release_lock(test_db):
    """Test lock release."""
    lock = ImportLock(test_db)

    # Acquire then release
    lock.acquire(reason="Test import")
    released = lock.release()

    assert released is True

    # Verify lock removed from database
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM import_locks WHERE id = 1")
    row = cursor.fetchone()

    assert row is None


def test_release_lock_not_held(test_db):
    """Test releasing a lock that's not held."""
    lock = ImportLock(test_db)
    released = lock.release()

    assert released is False


def test_check_lock_when_held(test_db):
    """Test checking lock status when held."""
    lock = ImportLock(test_db)
    lock.acquire(reason="Test import")

    lock_info = lock.check_lock()

    assert lock_info is not None
    assert lock_info['reason'] == "Test import"
    assert 'lock_holder' in lock_info
    assert 'created_at' in lock_info
    assert lock_info['age_minutes'] < 1  # Just created


def test_check_lock_when_available(test_db):
    """Test checking lock status when available."""
    lock = ImportLock(test_db)
    lock_info = lock.check_lock()

    assert lock_info is None


def test_lock_auto_expiry(test_db):
    """Test that expired locks are automatically cleaned up."""
    cursor = test_db.cursor()

    # Manually insert an expired lock (31 minutes old)
    expired_time = datetime.now() - timedelta(minutes=31)
    expired_expires = expired_time + timedelta(minutes=30)  # Would have expired 1 min ago
    cursor.execute("""
        INSERT INTO import_locks (id, lock_holder, reason, created_at, expires_at)
        VALUES (1, 'expired_process', 'Old import', ?, ?)
    """, (expired_time.isoformat(), expired_expires.isoformat()))
    test_db.commit()

    # Trying to acquire should clean up expired lock and succeed
    lock = ImportLock(test_db)
    acquired = lock.acquire(reason="New import")

    assert acquired is True


# ============================================
# AuditTrail Tests
# ============================================

def test_log_insert(test_db):
    """Test logging INSERT operation."""
    audit = AuditTrail(test_db, source="FL_DBPR", file_import_id=123)

    audit.log_insert(
        contractor_id=1,
        new_values={'company_name': 'ABC Solar', 'state': 'FL'}
    )
    audit.flush()

    # Verify audit record
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM contractor_history WHERE contractor_id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert row[2] == 'INSERT'  # change_type
    assert row[3] is None  # old_values
    new_vals = json.loads(row[4])
    assert new_vals['company_name'] == 'ABC Solar'
    assert row[5] == 'FL_DBPR'  # source


def test_log_update_only_changed_fields(test_db):
    """Test UPDATE only logs changed fields."""
    audit = AuditTrail(test_db, source="FL_DBPR")

    old_values = {'company_name': 'ABC Solar', 'state': 'FL', 'city': 'Miami'}
    new_values = {'company_name': 'ABC Solar', 'state': 'FL', 'city': 'Tampa'}

    audit.log_update(
        contractor_id=1,
        old_values=old_values,
        new_values=new_values
    )
    audit.flush()

    # Verify only 'city' was logged (the changed field)
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM contractor_history WHERE contractor_id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert row[2] == 'UPDATE'  # change_type

    old_vals = json.loads(row[3])
    new_vals = json.loads(row[4])

    # Only city should be logged
    assert 'city' in old_vals
    assert old_vals['city'] == 'Miami'
    assert new_vals['city'] == 'Tampa'

    # company_name and state should NOT be logged (unchanged)
    assert 'company_name' not in old_vals
    assert 'state' not in old_vals


def test_log_update_no_changes(test_db):
    """Test UPDATE with no changes logs nothing."""
    audit = AuditTrail(test_db, source="FL_DBPR")

    old_values = {'company_name': 'ABC Solar', 'state': 'FL'}
    new_values = {'company_name': 'ABC Solar', 'state': 'FL'}

    audit.log_update(
        contractor_id=1,
        old_values=old_values,
        new_values=new_values
    )
    audit.flush()

    # Should log nothing (no changes)
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM contractor_history WHERE contractor_id = 1")
    count = cursor.fetchone()[0]

    assert count == 0


def test_log_delete(test_db):
    """Test logging DELETE operation."""
    audit = AuditTrail(test_db, source="FL_DBPR")

    audit.log_delete(
        contractor_id=1,
        old_values={'company_name': 'ABC Solar', 'state': 'FL'},
        reason='Duplicate of contractor_id=2'
    )
    audit.flush()

    # Verify audit record
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM contractor_history WHERE contractor_id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert row[2] == 'DELETE'  # change_type
    assert row[4] is None  # new_values

    old_vals = json.loads(row[3])
    assert old_vals['company_name'] == 'ABC Solar'
    assert old_vals['_delete_reason'] == 'Duplicate of contractor_id=2'


def test_log_merge(test_db):
    """Test logging MERGE operation."""
    audit = AuditTrail(test_db, source="FL_DBPR")

    audit.log_merge(
        master_id=1,
        merged_id=2,
        merged_values={'company_name': 'ABC Solar', 'phone': '5551234567'}
    )
    audit.flush()

    # Verify audit record
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM contractor_history WHERE contractor_id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert row[2] == 'MERGE'  # change_type
    assert row[3] is None  # old_values

    new_vals = json.loads(row[4])
    assert new_vals['company_name'] == 'ABC Solar'
    assert new_vals['_merged_id'] == 2
    assert new_vals['_master_id'] == 1


def test_batch_auto_flush(test_db):
    """Test that batch auto-flushes at batch_size."""
    audit = AuditTrail(test_db, source="FL_DBPR")
    audit._batch_size = 5  # Set small batch size for testing

    # Add 7 records (should auto-flush at 5)
    for i in range(7):
        audit.log_insert(
            contractor_id=i,
            new_values={'company_name': f'Company {i}'}
        )

    # Should have auto-flushed 5 records
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM contractor_history")
    count = cursor.fetchone()[0]
    assert count == 5

    # Manual flush should write remaining 2
    audit.flush()
    cursor.execute("SELECT COUNT(*) FROM contractor_history")
    count = cursor.fetchone()[0]
    assert count == 7


def test_batch_flush_returns_count(test_db):
    """Test that flush() returns count of records written."""
    audit = AuditTrail(test_db, source="FL_DBPR")

    # Add 3 records
    for i in range(3):
        audit.log_insert(
            contractor_id=i,
            new_values={'company_name': f'Company {i}'}
        )

    # Flush should return 3
    count = audit.flush()
    assert count == 3

    # Second flush should return 0 (batch is empty)
    count = audit.flush()
    assert count == 0


def test_audit_with_file_import_id(test_db):
    """Test audit trail with file_import_id linking."""
    audit = AuditTrail(test_db, source="FL_DBPR", file_import_id=999)

    audit.log_insert(
        contractor_id=1,
        new_values={'company_name': 'ABC Solar'}
    )
    audit.flush()

    # Verify file_import_id was stored
    cursor = test_db.cursor()
    cursor.execute("SELECT file_import_id FROM contractor_history WHERE contractor_id = 1")
    file_import_id = cursor.fetchone()[0]

    assert file_import_id == 999


# ============================================
# Integration Tests
# ============================================

def test_import_workflow_with_lock_and_audit(test_db, temp_csv):
    """Test complete import workflow: lock + fingerprint + audit."""
    # 1. Get file fingerprint
    file_info = FileFingerprint.get_file_info(temp_csv)
    assert file_info['row_count'] == 3

    # 2. Acquire lock
    lock = ImportLock(test_db)
    acquired = lock.acquire(reason="FL import test")
    assert acquired is True

    try:
        # 3. Insert file_imports record
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO file_imports (file_name, file_hash, file_size, row_count)
            VALUES (?, ?, ?, ?)
        """, (file_info['file_name'], file_info['file_hash'],
              file_info['file_size'], file_info['row_count']))
        test_db.commit()
        file_import_id = cursor.lastrowid

        # 4. Log audit trail
        audit = AuditTrail(test_db, source="FL_DBPR", file_import_id=file_import_id)

        for i in range(3):
            audit.log_insert(
                contractor_id=i + 1,
                new_values={'company_name': f'Company {i + 1}'}
            )

        count = audit.flush()
        assert count == 3

    finally:
        # 5. Release lock
        released = lock.release()
        assert released is True

    # Verify audit records were created with correct file_import_id
    cursor.execute("SELECT COUNT(*) FROM contractor_history WHERE file_import_id = ?", (file_import_id,))
    count = cursor.fetchone()[0]
    assert count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
