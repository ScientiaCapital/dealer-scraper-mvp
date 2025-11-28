-- ============================================================
-- OEM LEADS TABLE - For Sales-Agent Integration
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/oyyakkuvvtckocncuwwf/sql
-- ============================================================

-- Enable UUID extension (usually already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing table if needed (BE CAREFUL - this deletes data!)
-- DROP TABLE IF EXISTS oem_leads;

-- Create the OEM leads table
CREATE TABLE IF NOT EXISTS oem_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core identification (ANCHOR - company name is primary key for dedup)
    company_name TEXT NOT NULL,
    normalized_name TEXT,  -- Lowercase, stripped for matching

    -- Contact info (from OEM scraper)
    phone TEXT,
    email TEXT,
    website TEXT,

    -- Location
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,

    -- OEM source tracking
    oem_name TEXT NOT NULL,  -- 'Carrier', 'Schneider Electric', etc.
    oem_tier TEXT,           -- 'Premier', 'EcoXpert', etc.
    oem_program TEXT,        -- Program name if applicable

    -- Data quality flags
    has_phone BOOLEAN DEFAULT FALSE,
    has_email BOOLEAN DEFAULT FALSE,
    has_website BOOLEAN DEFAULT FALSE,

    -- ICP scoring (set by sales-agent enrichment)
    icp_tier TEXT CHECK (icp_tier IN ('PLATINUM', 'GOLD', 'SILVER', 'BRONZE')),
    icp_score INTEGER CHECK (icp_score >= 0 AND icp_score <= 100),

    -- Pipeline status tracking
    enrichment_status TEXT DEFAULT 'pending' CHECK (enrichment_status IN (
        'pending',      -- Fresh from scraper, needs enrichment
        'enriched',     -- Hunter/Apollo enrichment complete
        'verified',     -- Phone/email verified
        'failed'        -- Enrichment failed
    )),
    crm_status TEXT DEFAULT 'not_synced' CHECK (crm_status IN (
        'not_synced',   -- Not yet pushed to Close CRM
        'synced',       -- In Close CRM
        'needs_update', -- Has new data to push
        'skipped'       -- Deliberately skipped
    )),
    close_lead_id TEXT,     -- Close CRM lead_xxx ID

    -- Timestamps
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    enriched_at TIMESTAMPTZ,
    synced_to_crm_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Source tracking for audit
    source_file TEXT,       -- Original scrape file
    import_batch TEXT       -- Batch ID for grouping imports
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_oem_leads_phone ON oem_leads(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_oem_leads_email ON oem_leads(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_oem_leads_oem ON oem_leads(oem_name);
CREATE INDEX IF NOT EXISTS idx_oem_leads_state ON oem_leads(state);
CREATE INDEX IF NOT EXISTS idx_oem_leads_normalized ON oem_leads(normalized_name);
CREATE INDEX IF NOT EXISTS idx_oem_leads_enrichment ON oem_leads(enrichment_status);
CREATE INDEX IF NOT EXISTS idx_oem_leads_crm ON oem_leads(crm_status);
CREATE INDEX IF NOT EXISTS idx_oem_leads_icp ON oem_leads(icp_tier);

-- Unique constraint: One company per OEM per state (prevents duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS idx_oem_leads_unique
ON oem_leads(normalized_name, oem_name, state)
WHERE normalized_name IS NOT NULL;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_oem_leads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS oem_leads_updated_at ON oem_leads;
CREATE TRIGGER oem_leads_updated_at
    BEFORE UPDATE ON oem_leads
    FOR EACH ROW
    EXECUTE FUNCTION update_oem_leads_updated_at();

-- View: Leads ready for enrichment (have contact info but not enriched yet)
CREATE OR REPLACE VIEW oem_leads_to_enrich AS
SELECT *
FROM oem_leads
WHERE enrichment_status = 'pending'
  AND (phone IS NOT NULL OR email IS NOT NULL)
ORDER BY scraped_at DESC;

-- View: Leads ready for CRM sync (enriched but not synced)
CREATE OR REPLACE VIEW oem_leads_to_sync AS
SELECT *
FROM oem_leads
WHERE enrichment_status IN ('enriched', 'verified')
  AND crm_status IN ('not_synced', 'needs_update')
ORDER BY icp_score DESC NULLS LAST;

-- Comments
COMMENT ON TABLE oem_leads IS 'OEM dealer/contractor leads from dealer-scraper-mvp, ready for sales-agent enrichment';
COMMENT ON COLUMN oem_leads.normalized_name IS 'Lowercase company name for deduplication matching';
COMMENT ON COLUMN oem_leads.enrichment_status IS 'Pipeline stage: pending → enriched → verified';
COMMENT ON COLUMN oem_leads.crm_status IS 'Close CRM sync status';

-- Row Level Security (optional - enable if needed)
-- ALTER TABLE oem_leads ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow service full access" ON oem_leads FOR ALL USING (true);

-- ============================================================
-- Sample query to check the table
-- ============================================================
-- SELECT oem_name, COUNT(*) as count,
--        SUM(CASE WHEN has_phone THEN 1 ELSE 0 END) as with_phone
-- FROM oem_leads
-- GROUP BY oem_name
-- ORDER BY count DESC;
