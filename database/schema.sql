-- Pipeline Database Schema
-- Version: 1.0
-- Purpose: Track contractors, licenses, contacts across all states
--
-- Design Philosophy:
-- - Contractors are the master entity (deduplicated by phone/email/domain/name)
-- - Contacts and Licenses are child records (many per contractor)
-- - Pipeline runs track ingestion history for auditability
-- - Dedup matches track WHY records were merged (debugging/validation)

-- Master contractor table (deduplicated)
CREATE TABLE IF NOT EXISTS contractors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    normalized_name TEXT,  -- Lowercase, no suffixes, for fuzzy matching
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    primary_phone TEXT,    -- Normalized 10-digit
    primary_email TEXT,    -- Lowercase
    primary_domain TEXT,   -- Extracted from email, excludes webmail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Soft delete support (for audit trail)
    is_deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    deleted_by TEXT,
    deletion_reason TEXT
);

-- Contact information (multiple per contractor)
-- Supports multiple contacts per company (owners, managers, etc.)
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT,
    phone TEXT,            -- Normalized 10-digit
    title TEXT,            -- 'Owner', 'President', 'Manager'
    source TEXT,           -- 'FL_License', 'SPW', 'Hunter', 'Apollo'
    confidence INTEGER DEFAULT 50,  -- 0-100 confidence score
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contractor_id, email)  -- Prevent duplicate emails per contractor
);

-- License records (multiple per contractor)
-- A contractor can hold multiple licenses in multiple states
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE CASCADE,
    state TEXT NOT NULL,
    license_type TEXT,     -- 'CAC', 'CPC', 'FRO', 'C-10', etc.
    license_category TEXT, -- 'HVAC', 'PLUMBING', 'ROOFING', 'ELECTRICAL'
    license_number TEXT,
    license_status TEXT DEFAULT 'active',  -- 'active', 'expired', 'suspended'
    source_file TEXT,      -- Which file this came from
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contractor_id, state, license_type, license_number)
);

-- Pipeline run history for auditing
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    source_file TEXT,
    records_input INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_merged INTEGER DEFAULT 0,  -- Duplicates merged into existing
    multi_license_found INTEGER DEFAULT 0,
    unicorns_found INTEGER DEFAULT 0,  -- 3+ categories
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_duration_seconds REAL,
    status TEXT DEFAULT 'in_progress',  -- 'in_progress', 'completed', 'failed'
    error_message TEXT
);

-- Deduplication tracking (for debugging and validation)
-- Tracks WHY two records were considered duplicates
CREATE TABLE IF NOT EXISTS dedup_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE CASCADE,
    duplicate_record_hash TEXT,  -- Hash of the duplicate record data
    match_type TEXT NOT NULL,    -- 'phone', 'email', 'domain', 'fuzzy_name'
    match_value TEXT,            -- The actual value that matched
    match_confidence REAL,       -- 0.0-1.0 confidence
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- OEM certifications (from dealer scrapers)
-- Links contractors to their OEM certifications
CREATE TABLE IF NOT EXISTS oem_certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE CASCADE,
    oem_name TEXT NOT NULL,      -- 'Generac', 'Tesla', 'Enphase', etc.
    certification_tier TEXT,     -- 'Premier', 'Elite', 'Authorized'
    scraped_from_zip TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contractor_id, oem_name)
);

-- SPW rankings (from Solar Power World lists)
CREATE TABLE IF NOT EXISTS spw_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER REFERENCES contractors(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,  -- Original name from SPW
    list_name TEXT NOT NULL,     -- 'Top Commercial', 'Top Residential', 'Top EPCs'
    rank_position INTEGER,
    kw_installed INTEGER,
    year INTEGER DEFAULT 2024,
    headquarters_state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AUDIT TRAIL TABLES (for import tracking and change history)
-- ============================================

-- File imports tracking (which files were imported, when, and outcome)
-- Prevents duplicate imports and enables rollback by file
CREATE TABLE IF NOT EXISTS file_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,          -- SHA256 of file content
    file_size_bytes INTEGER,
    row_count INTEGER,
    source_type TEXT,                 -- 'fl_license', 'ca_license', 'tx_license', 'oem_generac', etc.
    import_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    import_completed_at TIMESTAMP,
    import_status TEXT DEFAULT 'in_progress',  -- 'completed', 'failed', 'rolled_back'
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_merged INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    UNIQUE(file_hash)
);

-- Contractor change history (before/after snapshots for all changes)
-- Enables point-in-time recovery and debugging of data quality issues
CREATE TABLE IF NOT EXISTS contractor_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL,
    change_type TEXT NOT NULL,        -- 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'RESTORE'
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_source TEXT,               -- 'fl_license_import', 'oem_import', 'manual', 'api'
    file_import_id INTEGER,
    old_values TEXT,                  -- JSON of fields before change
    new_values TEXT,                  -- JSON of fields after change
    FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE SET NULL,
    FOREIGN KEY (file_import_id) REFERENCES file_imports(id)
);

-- Import locks (prevent concurrent imports from corrupting data)
-- Singleton table with max 1 row - acts as distributed lock
CREATE TABLE IF NOT EXISTS import_locks (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton row
    lock_holder TEXT NOT NULL,              -- 'hostname:pid'
    lock_acquired_at TIMESTAMP NOT NULL,
    lock_expires_at TIMESTAMP NOT NULL,     -- Auto-expire after 30 min
    lock_reason TEXT
);

-- ============================================
-- INDEXES for fast lookups
-- ============================================

-- Primary dedup indexes (most frequently queried)
CREATE INDEX IF NOT EXISTS idx_contractors_phone ON contractors(primary_phone);
CREATE INDEX IF NOT EXISTS idx_contractors_email ON contractors(primary_email);
CREATE INDEX IF NOT EXISTS idx_contractors_domain ON contractors(primary_domain);
CREATE INDEX IF NOT EXISTS idx_contractors_normalized ON contractors(normalized_name);
CREATE INDEX IF NOT EXISTS idx_contractors_state ON contractors(state);
CREATE INDEX IF NOT EXISTS idx_contractors_deleted ON contractors(is_deleted);

-- Contact indexes
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
CREATE INDEX IF NOT EXISTS idx_contacts_contractor ON contacts(contractor_id);

-- License indexes (for multi-license queries)
CREATE INDEX IF NOT EXISTS idx_licenses_state ON licenses(state);
CREATE INDEX IF NOT EXISTS idx_licenses_category ON licenses(license_category);
CREATE INDEX IF NOT EXISTS idx_licenses_contractor ON licenses(contractor_id);
CREATE INDEX IF NOT EXISTS idx_licenses_type ON licenses(license_type);

-- OEM indexes
CREATE INDEX IF NOT EXISTS idx_oem_contractor ON oem_certifications(contractor_id);
CREATE INDEX IF NOT EXISTS idx_oem_name ON oem_certifications(oem_name);

-- Pipeline run indexes
CREATE INDEX IF NOT EXISTS idx_runs_state ON pipeline_runs(state);
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON pipeline_runs(run_timestamp);

-- Audit trail indexes
CREATE INDEX IF NOT EXISTS idx_file_imports_hash ON file_imports(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_imports_status ON file_imports(import_status);
CREATE INDEX IF NOT EXISTS idx_contractor_history_cid ON contractor_history(contractor_id);
CREATE INDEX IF NOT EXISTS idx_contractor_history_ts ON contractor_history(change_timestamp);
CREATE INDEX IF NOT EXISTS idx_contractor_history_type ON contractor_history(change_type);
CREATE INDEX IF NOT EXISTS idx_contractor_history_import ON contractor_history(file_import_id);

-- ============================================
-- VIEWS for common queries
-- ============================================

-- Multi-license contractors (2+ categories)
CREATE VIEW IF NOT EXISTS v_multi_license AS
SELECT
    c.id,
    c.company_name,
    c.city,
    c.state,
    c.primary_phone,
    c.primary_email,
    GROUP_CONCAT(DISTINCT l.license_category) as categories,
    COUNT(DISTINCT l.license_category) as category_count
FROM contractors c
JOIN licenses l ON c.id = l.contractor_id
GROUP BY c.id
HAVING category_count >= 2;

-- Unicorns (3+ categories)
CREATE VIEW IF NOT EXISTS v_unicorns AS
SELECT * FROM v_multi_license
WHERE category_count >= 3;

-- Multi-OEM contractors
CREATE VIEW IF NOT EXISTS v_multi_oem AS
SELECT
    c.id,
    c.company_name,
    c.city,
    c.state,
    c.primary_phone,
    c.primary_email,
    GROUP_CONCAT(DISTINCT o.oem_name) as oems,
    COUNT(DISTINCT o.oem_name) as oem_count
FROM contractors c
JOIN oem_certifications o ON c.id = o.contractor_id
GROUP BY c.id
HAVING oem_count >= 2;

-- Cross-state contractors
CREATE VIEW IF NOT EXISTS v_cross_state AS
SELECT
    c.id,
    c.company_name,
    c.primary_phone,
    c.primary_email,
    GROUP_CONCAT(DISTINCT l.state) as states,
    COUNT(DISTINCT l.state) as state_count,
    GROUP_CONCAT(DISTINCT l.license_category) as categories
FROM contractors c
JOIN licenses l ON c.id = l.contractor_id
GROUP BY c.id
HAVING state_count > 1;

-- Pipeline stats by state
CREATE VIEW IF NOT EXISTS v_state_stats AS
SELECT
    state,
    COUNT(*) as total_contractors,
    SUM(CASE WHEN primary_email IS NOT NULL AND primary_email != '' THEN 1 ELSE 0 END) as with_email,
    SUM(CASE WHEN primary_phone IS NOT NULL AND primary_phone != '' THEN 1 ELSE 0 END) as with_phone
FROM contractors
GROUP BY state;
