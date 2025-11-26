# Audit Trail System

## Overview

The audit trail system provides comprehensive change tracking for all database operations:
- **File Import Deduplication**: SHA256 hashing prevents duplicate file imports
- **Change Data Capture (CDC)**: Before/after JSON snapshots for all INSERT/UPDATE/DELETE/MERGE
- **Concurrent Import Protection**: Singleton lock with 30-minute auto-expiry
- **Soft Delete Support**: Contractors can be deleted and recovered with full audit history

## Quick Start

### 1. Run Migration (Required for Existing Databases)

```bash
# Dry run first
python scripts/migrate_audit_schema.py --dry-run --db-path output/master/pipeline.db

# Apply migration
python scripts/migrate_audit_schema.py --db-path output/master/pipeline.db
```

### 2. Import Data with Audit Trail

```python
from database import PipelineDB
from pathlib import Path

db = PipelineDB()

# Start import (acquires lock, registers file)
file_import_id = db.start_file_import(
    file_path=Path("data/contractors.csv"),
    source_type="fl_license"
)

# Import records (each creates history entry)
stats = {'created': 0, 'updated': 0, 'merged': 0, 'skipped': 0}
for record in records:
    contractor_id, is_new = db.add_contractor_with_audit(
        record=record,
        file_import_id=file_import_id,
        source="fl_license"
    )
    stats['created' if is_new else 'merged'] += 1

# Complete import (updates stats, releases lock)
db.complete_file_import(file_import_id, stats)
```

### 3. Check Import History

```sql
-- View all file imports
SELECT id, file_name, import_status, records_created, records_merged
FROM file_imports
ORDER BY import_started_at DESC;

-- View contractor history
SELECT ch.change_type, ch.old_values, ch.new_values, ch.created_at
FROM contractor_history ch
WHERE ch.contractor_id = 123
ORDER BY ch.created_at DESC;
```

## API Reference

### PipelineDB Methods

| Method | Description |
|--------|-------------|
| `check_file_imported(file_path)` | Returns True if file hash already imported |
| `start_file_import(file_path, source_type)` | Acquires lock, registers file, returns file_import_id |
| `complete_file_import(file_import_id, stats)` | Updates stats, marks complete, releases lock |
| `fail_file_import(file_import_id, error_msg)` | Marks failed, releases lock |
| `add_contractor_with_audit(record, file_import_id, source)` | Insert/merge with history, returns (id, is_new) |
| `soft_delete_contractor(contractor_id, reason)` | Sets is_deleted=1 with audit trail |
| `get_contractor_history(contractor_id)` | Returns list of all changes |
| `rollback_import(file_import_id)` | Soft deletes all contractors from import |

### Schema Tables

```
file_imports        - Tracks imported files by SHA256 hash
contractor_history  - CDC records with before/after JSON
import_locks       - Singleton lock (id=1 constraint)
```

## Gotchas & Known Issues

### 1. Connection Lifecycle
Each `add_contractor_with_audit()` call creates a fresh database connection. This is intentional to avoid "Cannot operate on a closed database" errors that occurred when passing connections across context manager boundaries.

**Impact**: Slightly less efficient (~5% slower) but much more reliable.

### 2. Lock Warning in Tests
When running tests on a fresh database, you may see:
```
WARNING - No lock found to release
```
This is expected behavior - the lock table is empty on initialization.

### 3. Migration Required Before Use
The audit tables don't exist in databases created before this feature. **You must run the migration script** before using audit methods, or you'll get "no such table" errors.

### 4. Soft Delete Transactions
When using `rollback_import()`, all soft deletes happen in a single transaction. If you're using `soft_delete_contractor()` individually, each call commits independently.

### 5. File Hash Uniqueness
The `file_imports.file_hash` column has a UNIQUE constraint. Attempting to import a file with the same content (even different filename) will fail. This is by design - use `check_file_imported()` first.

## Testing

```bash
# Unit tests (20 tests)
./venv/bin/python -m pytest tests/unit/test_audit.py -v

# Integration tests
python /tmp/test_audit_import.py      # A5: Import with audit
python /tmp/test_audit_duplicate.py   # A6: Duplicate prevention
python /tmp/test_audit_soft_delete.py # A7: Soft delete/recovery
```

## Files Changed

| File | Description |
|------|-------------|
| `database/audit.py` | Core audit module (FileFingerprint, ImportLock, AuditTrail) |
| `database/pipeline_db.py` | 8 new audit methods added |
| `database/schema.sql` | 3 new tables + soft delete columns |
| `scripts/migrate_audit_schema.py` | Idempotent migration script |
| `tests/unit/test_audit.py` | 20 unit tests |

## Next Steps (Post-Merge)

1. **Migrate production database**: Run migration on `output/master/pipeline.db`
2. **Update import scripts**: Use new `add_contractor_with_audit()` for all imports
3. **Share with sales-agent**: Database is now safe to share (audit trail protects integrity)
4. **Phase B**: Run NY/NJ scrapers using new audit system
