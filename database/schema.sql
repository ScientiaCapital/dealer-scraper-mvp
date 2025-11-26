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
    source_type TEXT DEFAULT 'state_license',  -- 'state_license', 'oem_dealer', 'both'
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,                      -- 'fl_license_import', 'oem_import', 'manual', 'api'
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
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,          -- Auto-expire after 30 min
    reason TEXT
);

-- ============================================
-- OBSERVABILITY TABLES (scraper health + data inventory)
-- For GTM team, CEO/CTO visibility into pipeline health
-- ============================================

-- Scraper registry - Master list of all scrapers with status
-- Tracks which scrapers exist, work/broken status, fix difficulty
CREATE TABLE IF NOT EXISTS scraper_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_name TEXT UNIQUE NOT NULL,      -- 'generac', 'tesla', 'nyc_dob'
    scraper_type TEXT NOT NULL,              -- 'OEM', 'STATE_LICENSE', 'THIRD_PARTY'
    source_url TEXT,                         -- Dealer locator URL
    status TEXT DEFAULT 'UNKNOWN',           -- 'WORKING', 'BROKEN', 'UNTESTED', 'DEPRECATED'
    last_test_date TIMESTAMP,
    last_successful_run TIMESTAMP,
    total_records_lifetime INTEGER DEFAULT 0,
    fix_difficulty TEXT,                     -- 'EASY', 'MEDIUM', 'HARD'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraper runs - Audit trail of every scrape execution
-- Enables tracking of scraper performance over time
CREATE TABLE IF NOT EXISTS scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_name TEXT NOT NULL,
    run_started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_completed_at TIMESTAMP,
    status TEXT DEFAULT 'RUNNING',           -- 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL'
    records_found INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    run_parameters TEXT,                     -- JSON: {"zips": [...], "states": [...]}
    FOREIGN KEY (scraper_name) REFERENCES scraper_registry(scraper_name)
);

-- Data inventory - Summary of what data exists by source
-- Enables answering "what do we have?" for GTM team
CREATE TABLE IF NOT EXISTS data_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,               -- 'generac', 'fl_license', 'spw'
    source_type TEXT NOT NULL,               -- 'OEM', 'STATE_LICENSE', 'THIRD_PARTY'
    record_count INTEGER NOT NULL DEFAULT 0,
    with_email_count INTEGER DEFAULT 0,
    with_phone_count INTEGER DEFAULT 0,
    states_covered TEXT,                     -- JSON array: ["CA", "TX", "FL"]
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_freshness_days INTEGER,             -- Calculated: days since last update
    quality_score INTEGER,                   -- 0-100 based on completeness
    notes TEXT,
    UNIQUE(source_name, source_type)
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
CREATE INDEX IF NOT EXISTS idx_contractors_source_type ON contractors(source_type);

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
CREATE INDEX IF NOT EXISTS idx_contractor_history_ts ON contractor_history(created_at);
CREATE INDEX IF NOT EXISTS idx_contractor_history_type ON contractor_history(change_type);
CREATE INDEX IF NOT EXISTS idx_contractor_history_import ON contractor_history(file_import_id);

-- Observability indexes
CREATE INDEX IF NOT EXISTS idx_scraper_registry_status ON scraper_registry(status);
CREATE INDEX IF NOT EXISTS idx_scraper_registry_type ON scraper_registry(scraper_type);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_name ON scraper_runs(scraper_name);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_started ON scraper_runs(run_started_at);
CREATE INDEX IF NOT EXISTS idx_data_inventory_source ON data_inventory(source_name);
CREATE INDEX IF NOT EXISTS idx_data_inventory_type ON data_inventory(source_type);

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

-- Scraper health overview (for dashboard)
CREATE VIEW IF NOT EXISTS v_scraper_health AS
SELECT
    sr.scraper_name,
    sr.scraper_type,
    sr.status,
    sr.fix_difficulty,
    sr.total_records_lifetime,
    sr.last_successful_run,
    CAST(julianday('now') - julianday(sr.last_successful_run) AS INTEGER) as days_since_run,
    (SELECT COUNT(*) FROM scraper_runs WHERE scraper_name = sr.scraper_name AND status = 'SUCCESS') as successful_runs,
    (SELECT COUNT(*) FROM scraper_runs WHERE scraper_name = sr.scraper_name AND status = 'FAILED') as failed_runs
FROM scraper_registry sr;

-- Data freshness summary (for dashboard)
CREATE VIEW IF NOT EXISTS v_data_freshness AS
SELECT
    source_name,
    source_type,
    record_count,
    with_email_count,
    with_phone_count,
    CAST(julianday('now') - julianday(last_updated) AS INTEGER) as days_old,
    CASE
        WHEN julianday('now') - julianday(last_updated) <= 7 THEN 'FRESH'
        WHEN julianday('now') - julianday(last_updated) <= 30 THEN 'STALE'
        ELSE 'OUTDATED'
    END as freshness_status,
    quality_score
FROM data_inventory;

-- Overall pipeline health (for executive dashboard)
CREATE VIEW IF NOT EXISTS v_pipeline_health AS
SELECT
    (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0) as total_contractors,
    (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0 AND primary_email IS NOT NULL) as with_email,
    (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0 AND primary_phone IS NOT NULL) as with_phone,
    (SELECT COUNT(*) FROM v_multi_license) as multi_license_count,
    (SELECT COUNT(*) FROM v_unicorns) as unicorn_count,
    (SELECT COUNT(*) FROM v_multi_oem) as multi_oem_count,
    (SELECT COUNT(*) FROM scraper_registry WHERE status = 'WORKING') as working_scrapers,
    (SELECT COUNT(*) FROM scraper_registry WHERE status = 'BROKEN') as broken_scrapers,
    (SELECT COUNT(*) FROM scraper_registry WHERE status = 'UNTESTED') as untested_scrapers;

-- ============================================
-- COST & VALUE TRACKING (Full Funnel ROI)
-- For GTM/Founders: Show cost to build vs. value generated
-- ============================================

-- Cost tracking by category (infrastructure, scraping, enrichment, outreach)
-- Tracks investments over time for ROI calculation
CREATE TABLE IF NOT EXISTS cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cost_date DATE NOT NULL,                   -- Date of the cost
    category TEXT NOT NULL,                    -- 'infrastructure', 'scraping', 'enrichment', 'outreach', 'labor'
    subcategory TEXT,                          -- 'runpod', 'browserbase', 'apollo', 'hunter', 'sendgrid'
    amount_cents INTEGER NOT NULL,             -- Cost in cents (avoid float precision issues)
    currency TEXT DEFAULT 'USD',
    description TEXT,                          -- 'RunPod GPU hours for 329-ZIP scrape'
    billable_units INTEGER,                    -- Number of units (ZIPs scraped, emails enriched, etc.)
    cost_per_unit_cents INTEGER,               -- Calculated: amount_cents / billable_units
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Funnel events - Track each lead's progression through the sales funnel
-- Stages: RAW_LEAD → ENRICHED → CONTACTED → DEMO_SET → OPPORTUNITY → CLOSED_WON/CLOSED_LOST
CREATE TABLE IF NOT EXISTS funnel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,                  -- 'STAGE_CHANGE', 'ENRICHMENT', 'OUTREACH', 'RESPONSE', 'MEETING'
    stage_from TEXT,                           -- Previous stage (null for new leads)
    stage_to TEXT NOT NULL,                    -- New stage
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_source TEXT,                         -- 'auto_scrape', 'apollo', 'manual', 'close_crm', 'calendly'
    event_details TEXT,                        -- JSON: {"email_sent": true, "template": "cold_intro"}
    time_in_previous_stage_hours INTEGER,      -- How long in previous stage
    FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE
);

-- Funnel stages enum reference (not a real enum in SQLite)
-- RAW_LEAD: Just scraped, no enrichment
-- ENRICHED: Has email/phone from Apollo/Hunter
-- CONTACTED: Email sent or call made
-- RESPONDED: Got a reply (positive or negative)
-- DEMO_SET: Demo/meeting scheduled
-- OPPORTUNITY: In CRM as active opportunity
-- CLOSED_WON: Deal closed, revenue booked
-- CLOSED_LOST: Deal lost
-- DISQUALIFIED: Removed (bad fit, bad data, etc.)

-- Opportunities - Track deals through to close
-- Links back to contractors for full attribution
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL,
    opportunity_name TEXT NOT NULL,            -- 'ABC Solar - Platform License'
    crm_opportunity_id TEXT,                   -- Close CRM ID for sync
    stage TEXT NOT NULL DEFAULT 'NEW',         -- 'NEW', 'QUALIFYING', 'DEMO', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST'
    amount_cents INTEGER,                      -- Deal value in cents
    currency TEXT DEFAULT 'USD',
    close_date DATE,                           -- Expected or actual close date
    probability_pct INTEGER DEFAULT 10,        -- Win probability (0-100)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,                       -- When WON or LOST
    close_reason TEXT,                         -- 'pricing', 'competitor', 'timing', 'no_budget'
    deal_source TEXT,                          -- 'outbound_scraper', 'inbound', 'referral', 'event'
    assigned_to TEXT,                          -- BDR name
    notes TEXT,
    FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE
);

-- Lead attribution - Track how leads were acquired for cost allocation
-- Links contractors to their acquisition source and cost
CREATE TABLE IF NOT EXISTS lead_attribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL UNIQUE,     -- One attribution per contractor
    acquisition_source TEXT NOT NULL,          -- 'state_license_fl', 'oem_generac', 'spw', 'manual'
    acquisition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acquisition_cost_cents INTEGER DEFAULT 0,  -- Calculated: total scrape cost / leads acquired
    enrichment_cost_cents INTEGER DEFAULT 0,   -- Cost to enrich this lead
    outreach_cost_cents INTEGER DEFAULT 0,     -- Cost to contact this lead
    total_cost_cents INTEGER GENERATED ALWAYS AS (
        acquisition_cost_cents + enrichment_cost_cents + outreach_cost_cents
    ) STORED,
    first_contact_date TIMESTAMP,              -- When first outreach happened
    first_response_date TIMESTAMP,             -- When they first responded
    days_to_first_contact INTEGER,             -- Calculated: first_contact - acquisition
    days_to_first_response INTEGER,            -- Calculated: first_response - first_contact
    current_funnel_stage TEXT DEFAULT 'RAW_LEAD',
    FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE
);

-- ============================================
-- COST/VALUE INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_cost_tracking_date ON cost_tracking(cost_date);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_category ON cost_tracking(category);
CREATE INDEX IF NOT EXISTS idx_funnel_events_contractor ON funnel_events(contractor_id);
CREATE INDEX IF NOT EXISTS idx_funnel_events_stage ON funnel_events(stage_to);
CREATE INDEX IF NOT EXISTS idx_funnel_events_timestamp ON funnel_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_opportunities_contractor ON opportunities(contractor_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opportunities_close_date ON opportunities(close_date);
CREATE INDEX IF NOT EXISTS idx_lead_attribution_source ON lead_attribution(acquisition_source);
CREATE INDEX IF NOT EXISTS idx_lead_attribution_stage ON lead_attribution(current_funnel_stage);

-- ============================================
-- COST/VALUE VIEWS (ROI Calculations)
-- ============================================

-- Funnel metrics by stage (for GTM visibility)
CREATE VIEW IF NOT EXISTS v_funnel_metrics AS
SELECT
    current_funnel_stage as stage,
    COUNT(*) as lead_count,
    ROUND(AVG(total_cost_cents) / 100.0, 2) as avg_cost_per_lead,
    ROUND(SUM(total_cost_cents) / 100.0, 2) as total_cost,
    ROUND(AVG(days_to_first_contact), 1) as avg_days_to_contact,
    ROUND(AVG(days_to_first_response), 1) as avg_days_to_response
FROM lead_attribution
GROUP BY current_funnel_stage
ORDER BY
    CASE current_funnel_stage
        WHEN 'RAW_LEAD' THEN 1
        WHEN 'ENRICHED' THEN 2
        WHEN 'CONTACTED' THEN 3
        WHEN 'RESPONDED' THEN 4
        WHEN 'DEMO_SET' THEN 5
        WHEN 'OPPORTUNITY' THEN 6
        WHEN 'CLOSED_WON' THEN 7
        WHEN 'CLOSED_LOST' THEN 8
        ELSE 9
    END;

-- Monthly cost summary (for founders)
CREATE VIEW IF NOT EXISTS v_monthly_costs AS
SELECT
    strftime('%Y-%m', cost_date) as month,
    category,
    SUM(amount_cents) / 100.0 as total_cost_usd,
    SUM(billable_units) as total_units,
    ROUND(AVG(cost_per_unit_cents) / 100.0, 4) as avg_cost_per_unit
FROM cost_tracking
GROUP BY strftime('%Y-%m', cost_date), category
ORDER BY month DESC, total_cost_usd DESC;

-- Pipeline ROI summary (the money slide)
CREATE VIEW IF NOT EXISTS v_pipeline_roi AS
SELECT
    -- Investment side
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking) as total_investment_usd,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking WHERE category = 'infrastructure') as infrastructure_cost,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking WHERE category = 'enrichment') as enrichment_cost,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking WHERE category = 'outreach') as outreach_cost,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking WHERE category = 'labor') as labor_cost,

    -- Pipeline value side
    (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0) as total_leads,
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage = 'ENRICHED') as enriched_leads,
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('CONTACTED', 'RESPONDED', 'DEMO_SET')) as active_leads,
    (SELECT COUNT(*) FROM opportunities WHERE stage NOT IN ('WON', 'LOST')) as open_opportunities,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM opportunities WHERE stage NOT IN ('WON', 'LOST')) as pipeline_value_usd,

    -- Closed business
    (SELECT COUNT(*) FROM opportunities WHERE stage = 'WON') as closed_won_count,
    (SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM opportunities WHERE stage = 'WON') as closed_won_value_usd,
    (SELECT COUNT(*) FROM opportunities WHERE stage = 'LOST') as closed_lost_count,

    -- ROI calculation
    CASE
        WHEN (SELECT COALESCE(SUM(amount_cents), 0) FROM cost_tracking) > 0 THEN
            ROUND(
                ((SELECT COALESCE(SUM(amount_cents), 0) FROM opportunities WHERE stage = 'WON') -
                 (SELECT COALESCE(SUM(amount_cents), 0) FROM cost_tracking)) * 100.0 /
                (SELECT SUM(amount_cents) FROM cost_tracking), 1
            )
        ELSE NULL
    END as roi_percentage,

    -- Cost per metrics
    CASE
        WHEN (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0) > 0 THEN
            ROUND((SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking) /
                  (SELECT COUNT(*) FROM contractors WHERE is_deleted = 0), 4)
        ELSE NULL
    END as cost_per_lead_usd,

    CASE
        WHEN (SELECT COUNT(*) FROM opportunities WHERE stage = 'WON') > 0 THEN
            ROUND((SELECT COALESCE(SUM(amount_cents), 0) / 100.0 FROM cost_tracking) /
                  (SELECT COUNT(*) FROM opportunities WHERE stage = 'WON'), 2)
        ELSE NULL
    END as cost_per_closed_deal_usd;

-- Conversion rates (the funnel slide)
CREATE VIEW IF NOT EXISTS v_conversion_rates AS
SELECT
    'Raw → Enriched' as conversion,
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage != 'RAW_LEAD') as numerator,
    (SELECT COUNT(*) FROM lead_attribution) as denominator,
    ROUND(
        (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage != 'RAW_LEAD') * 100.0 /
        NULLIF((SELECT COUNT(*) FROM lead_attribution), 0), 1
    ) as conversion_rate_pct
UNION ALL
SELECT
    'Enriched → Contacted',
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('CONTACTED', 'RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')),
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage != 'RAW_LEAD'),
    ROUND(
        (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('CONTACTED', 'RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')) * 100.0 /
        NULLIF((SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage != 'RAW_LEAD'), 0), 1
    )
UNION ALL
SELECT
    'Contacted → Response',
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')),
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('CONTACTED', 'RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')),
    ROUND(
        (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')) * 100.0 /
        NULLIF((SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('CONTACTED', 'RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')), 0), 1
    )
UNION ALL
SELECT
    'Response → Demo',
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')),
    (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')),
    ROUND(
        (SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')) * 100.0 /
        NULLIF((SELECT COUNT(*) FROM lead_attribution WHERE current_funnel_stage IN ('RESPONDED', 'DEMO_SET', 'OPPORTUNITY', 'CLOSED_WON')), 0), 1
    )
UNION ALL
SELECT
    'Demo → Closed Won',
    (SELECT COUNT(*) FROM opportunities WHERE stage = 'WON'),
    (SELECT COUNT(*) FROM opportunities WHERE stage IN ('WON', 'LOST')),
    ROUND(
        (SELECT COUNT(*) FROM opportunities WHERE stage = 'WON') * 100.0 /
        NULLIF((SELECT COUNT(*) FROM opportunities WHERE stage IN ('WON', 'LOST')), 0), 1
    );
