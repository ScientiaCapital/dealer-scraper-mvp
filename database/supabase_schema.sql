-- ============================================================
-- COPERNIQ CONTRACTOR LEADS DATABASE SCHEMA
-- Supabase PostgreSQL with Full Audit Trail
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Companies (THE ANCHOR - deduplicated by normalized_name)
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Core identification (ANCHOR)
    company_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,  -- Lowercase, stripped for dedup matching

    -- Contact info
    phone TEXT,
    email TEXT,
    website TEXT,
    domain TEXT,

    -- Location
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,

    -- Business characteristics
    is_multi_state BOOLEAN DEFAULT FALSE,
    is_multi_site BOOLEAN DEFAULT FALSE,
    office_count INTEGER DEFAULT 1,

    -- Scoring
    icp_tier TEXT CHECK (icp_tier IN ('PLATINUM', 'GOLD', 'SILVER', 'BRONZE')),
    icp_score INTEGER CHECK (icp_score >= 0 AND icp_score <= 100),
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),

    -- Audit trail
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    updated_by TEXT DEFAULT 'system',
    source_file TEXT,  -- Original file this came from
    import_batch_id UUID,  -- Links to import_batches table

    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by TEXT,

    UNIQUE(normalized_name, state)  -- One company per state
);

-- Offices (for multi-site companies)
CREATE TABLE IF NOT EXISTS offices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Location
    street TEXT,
    city TEXT,
    state TEXT NOT NULL,
    zip TEXT,

    -- Contact
    phone TEXT,
    email TEXT,

    -- Type
    is_headquarters BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source_file TEXT,
    import_batch_id UUID
);

-- OEM Certifications (many-to-many: company can have multiple OEMs)
CREATE TABLE IF NOT EXISTS oem_certifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    oem_name TEXT NOT NULL,  -- 'Generac', 'Tesla', 'Schneider Electric', etc.
    tier TEXT,  -- 'Premier', 'Platinum', 'Gold', etc.
    program TEXT,  -- 'EcoXpert', 'Powerwall Certified', etc.

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source_file TEXT,
    scraped_at TIMESTAMPTZ,

    UNIQUE(company_id, oem_name)
);

-- State Licenses (many-to-many: company can have multiple licenses)
CREATE TABLE IF NOT EXISTS state_licenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    license_number TEXT NOT NULL,
    license_type TEXT NOT NULL,  -- 'C-10', 'CAC', 'CPC', etc.
    license_category TEXT,  -- 'ELECTRICAL', 'HVAC', 'PLUMBING', etc.
    state TEXT NOT NULL,

    -- Status
    status TEXT,  -- 'ACTIVE', 'EXPIRED', 'SUSPENDED'
    issue_date DATE,
    expiration_date DATE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source_file TEXT,
    scraped_at TIMESTAMPTZ,

    UNIQUE(license_number, state)
);

-- ============================================================
-- AUDIT TRAIL TABLES
-- ============================================================

-- Import Batches (tracks each data import)
CREATE TABLE IF NOT EXISTS import_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What was imported
    source_type TEXT NOT NULL,  -- 'oem_scrape', 'state_license', 'manual', 'enrichment'
    source_name TEXT NOT NULL,  -- 'Schneider', 'FL_DBPR', 'Hunter.io', etc.
    source_file TEXT,  -- Original filename

    -- Stats
    records_total INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_duplicate INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Who ran it
    imported_by TEXT DEFAULT 'system',

    -- Status
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed', 'rolled_back'))
);

-- Change History (CDC - Change Data Capture)
CREATE TABLE IF NOT EXISTS change_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What changed
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('INSERT', 'UPDATE', 'DELETE')),

    -- Before/After values (JSONB for flexibility)
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],  -- Array of field names that changed

    -- When & Who
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by TEXT DEFAULT 'system',
    import_batch_id UUID REFERENCES import_batches(id),

    -- Context
    change_reason TEXT  -- 'initial_import', 'dedup_merge', 'enrichment', 'manual_edit'
);

-- Deduplication Log (tracks merge decisions)
CREATE TABLE IF NOT EXISTS dedup_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- The winner (kept record)
    kept_company_id UUID NOT NULL REFERENCES companies(id),

    -- The loser (merged/deleted record) - store data before delete
    merged_company_data JSONB NOT NULL,

    -- Match details
    match_type TEXT NOT NULL,  -- 'phone', 'email', 'domain', 'fuzzy_name'
    match_confidence INTEGER CHECK (match_confidence >= 0 AND match_confidence <= 100),

    -- Audit
    merged_at TIMESTAMPTZ DEFAULT NOW(),
    merged_by TEXT DEFAULT 'system',
    import_batch_id UUID REFERENCES import_batches(id)
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON companies(normalized_name);
CREATE INDEX IF NOT EXISTS idx_companies_phone ON companies(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_companies_email ON companies(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain) WHERE domain IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state);
CREATE INDEX IF NOT EXISTS idx_companies_icp_tier ON companies(icp_tier);
CREATE INDEX IF NOT EXISTS idx_companies_import_batch ON companies(import_batch_id);

CREATE INDEX IF NOT EXISTS idx_oem_certifications_company ON oem_certifications(company_id);
CREATE INDEX IF NOT EXISTS idx_oem_certifications_oem ON oem_certifications(oem_name);

CREATE INDEX IF NOT EXISTS idx_state_licenses_company ON state_licenses(company_id);
CREATE INDEX IF NOT EXISTS idx_state_licenses_state ON state_licenses(state);
CREATE INDEX IF NOT EXISTS idx_state_licenses_category ON state_licenses(license_category);

CREATE INDEX IF NOT EXISTS idx_change_history_record ON change_history(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_change_history_time ON change_history(changed_at);

-- ============================================================
-- TRIGGERS FOR AUTOMATIC AUDIT
-- ============================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Change history trigger for companies
CREATE OR REPLACE FUNCTION log_company_changes()
RETURNS TRIGGER AS $$
DECLARE
    changed_cols TEXT[];
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO change_history (table_name, record_id, change_type, new_values, change_reason)
        VALUES ('companies', NEW.id, 'INSERT', to_jsonb(NEW), 'initial_import');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Find changed columns
        SELECT array_agg(key) INTO changed_cols
        FROM jsonb_each(to_jsonb(NEW)) n
        FULL OUTER JOIN jsonb_each(to_jsonb(OLD)) o USING (key)
        WHERE n.value IS DISTINCT FROM o.value
          AND key NOT IN ('updated_at');  -- Ignore automatic timestamp

        IF array_length(changed_cols, 1) > 0 THEN
            INSERT INTO change_history (table_name, record_id, change_type, old_values, new_values, changed_fields)
            VALUES ('companies', NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), changed_cols);
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO change_history (table_name, record_id, change_type, old_values, change_reason)
        VALUES ('companies', OLD.id, 'DELETE', to_jsonb(OLD), 'manual_delete');
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_audit
    AFTER INSERT OR UPDATE OR DELETE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION log_company_changes();

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- Clean leads view (for sales-agent handoff)
CREATE OR REPLACE VIEW clean_leads AS
SELECT
    c.id,
    c.company_name,
    c.phone,
    c.email,
    c.website,
    c.domain,
    c.city,
    c.state,
    c.zip,
    c.icp_tier,
    c.icp_score,
    c.quality_score,
    c.is_multi_state,
    c.is_multi_site,
    c.office_count,
    COALESCE(
        (SELECT array_agg(DISTINCT oem_name) FROM oem_certifications WHERE company_id = c.id),
        ARRAY[]::TEXT[]
    ) as oem_certifications,
    COALESCE(
        (SELECT array_agg(DISTINCT license_category) FROM state_licenses WHERE company_id = c.id),
        ARRAY[]::TEXT[]
    ) as license_categories,
    c.created_at,
    c.updated_at
FROM companies c
WHERE c.is_deleted = FALSE
  AND c.company_name IS NOT NULL
  AND c.company_name != '';

-- Multi-OEM contractors view
CREATE OR REPLACE VIEW multi_oem_contractors AS
SELECT
    c.*,
    oem_count,
    oem_list
FROM companies c
JOIN (
    SELECT
        company_id,
        COUNT(DISTINCT oem_name) as oem_count,
        array_agg(DISTINCT oem_name) as oem_list
    FROM oem_certifications
    GROUP BY company_id
    HAVING COUNT(DISTINCT oem_name) >= 2
) oems ON c.id = oems.company_id
WHERE c.is_deleted = FALSE;

-- Import summary view
CREATE OR REPLACE VIEW import_summary AS
SELECT
    source_type,
    source_name,
    COUNT(*) as batch_count,
    SUM(records_total) as total_records,
    SUM(records_new) as new_records,
    SUM(records_duplicate) as duplicates,
    MAX(completed_at) as last_import
FROM import_batches
WHERE status = 'completed'
GROUP BY source_type, source_name
ORDER BY last_import DESC;

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE offices ENABLE ROW LEVEL SECURITY;
ALTER TABLE oem_certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_history ENABLE ROW LEVEL SECURITY;

-- Policy: Authenticated users can read all
CREATE POLICY "Allow authenticated read" ON companies
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated read" ON offices
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated read" ON oem_certifications
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated read" ON state_licenses
    FOR SELECT USING (auth.role() = 'authenticated');

-- Policy: Service role can do everything
CREATE POLICY "Allow service full access" ON companies
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service full access" ON offices
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service full access" ON oem_certifications
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service full access" ON state_licenses
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service full access" ON import_batches
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service full access" ON change_history
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================
-- CRM SYNC TABLES (Close CRM Integration)
-- ============================================================

-- CRM Sync Status (tracks what's in Close CRM)
CREATE TABLE IF NOT EXISTS crm_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Close CRM reference
    close_lead_id TEXT,  -- Close CRM's lead_xxx ID
    close_contact_id TEXT,  -- Close CRM's cont_xxx ID

    -- Sync status
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN (
        'pending',      -- Not yet synced to Close
        'synced',       -- In Close, up to date
        'needs_update', -- In Close, but we have new data to push
        'skipped',      -- Deliberately skipped (duplicate, bad data)
        'failed'        -- Sync attempted but failed
    )),

    -- Sales tier
    sales_tier TEXT CHECK (sales_tier IN ('ATL', 'BTL')),  -- Above/Below the Line

    -- What was synced
    last_synced_at TIMESTAMPTZ,
    last_synced_data JSONB,  -- Snapshot of what we sent to Close
    sync_error TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id)
);

-- CRM Sync Log (every sync attempt)
CREATE TABLE IF NOT EXISTS crm_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id),

    -- What happened
    action TEXT NOT NULL CHECK (action IN (
        'create_lead',    -- New lead created in Close
        'update_lead',    -- Existing lead enriched
        'skip_duplicate', -- Skipped because already exists
        'skip_bad_data',  -- Skipped due to data quality
        'failed'          -- API error
    )),

    -- Details
    close_lead_id TEXT,
    request_data JSONB,   -- What we tried to send
    response_data JSONB,  -- What Close returned
    error_message TEXT,

    -- Timing
    attempted_at TIMESTAMPTZ DEFAULT NOW(),
    duration_ms INTEGER
);

-- View: Companies NOT in Close CRM yet
CREATE OR REPLACE VIEW pending_crm_sync AS
SELECT
    c.id,
    c.company_name,
    c.phone,
    c.email,
    c.website,
    c.city,
    c.state,
    c.icp_tier,
    c.icp_score,
    COALESCE(s.sync_status, 'pending') as sync_status
FROM companies c
LEFT JOIN crm_sync_status s ON c.id = s.company_id
WHERE c.is_deleted = FALSE
  AND c.company_name IS NOT NULL
  AND (s.sync_status IS NULL OR s.sync_status = 'pending')
ORDER BY c.icp_score DESC NULLS LAST;

-- View: Companies needing enrichment push to Close
CREATE OR REPLACE VIEW needs_crm_enrichment AS
SELECT
    c.*,
    s.close_lead_id,
    s.last_synced_at,
    s.last_synced_data
FROM companies c
JOIN crm_sync_status s ON c.id = s.company_id
WHERE s.sync_status = 'needs_update'
ORDER BY c.icp_score DESC NULLS LAST;

CREATE INDEX IF NOT EXISTS idx_crm_sync_status ON crm_sync_status(sync_status);
CREATE INDEX IF NOT EXISTS idx_crm_sync_close_id ON crm_sync_status(close_lead_id);
CREATE INDEX IF NOT EXISTS idx_crm_sync_tier ON crm_sync_status(sales_tier);

-- ============================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================

COMMENT ON TABLE companies IS 'Master table of contractor companies - THE ANCHOR for all lead data';
COMMENT ON COLUMN companies.normalized_name IS 'Lowercase, stripped company name for deduplication matching';
COMMENT ON COLUMN companies.import_batch_id IS 'Links to import_batches for full audit trail';

COMMENT ON TABLE change_history IS 'CDC (Change Data Capture) - tracks every change to companies table';
COMMENT ON TABLE dedup_log IS 'Tracks all deduplication merge decisions with full before/after data';

COMMENT ON VIEW clean_leads IS 'Sales-agent ready view - companies with all enrichment data denormalized';
