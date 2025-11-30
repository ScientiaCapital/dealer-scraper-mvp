# Dealer Scraper MVP - Architecture & Planning

**Last Updated**: 2025-11-30

**CRITICAL RULES:**
- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- API keys in `.env` only, never hardcoded
- ALWAYS create failsafe archive before database changes
- Company name is the PRIMARY field ("NAME IS THE ANCHOR")

---

## Project Overview

**Coperniq Partner Prospecting System** - Contractor lead generation feeding into sales-agent pipeline.

**Purpose**: Scrape OEM dealer locators and state license databases to build a clean, enriched master list of MEP+E contractors.

**Data Flow**: `dealer-scraper-mvp` → `sales-agent` (Supabase) → `Close CRM`

---

## Current Status (Nov 30, 2025)

### Database Metrics

| Metric | Count |
|--------|-------|
| Total contractors | 217,523 |
| Supabase (icp_gold_leads) | 14,204 |
| Close CRM leads | 6,031 ($2.67M pipeline) |
| OEM-certified contractors | 12,426 |

### Data Quality by State

| State | Records | Email % | Phone % |
|-------|---------|---------|---------|
| TX | 101,085 | 0.7% | 11.2% |
| FL | 58,504 | 96.8% | 1.1% |
| CA | 36,355 | 0.7% | 99.0% |
| NY | 2,269 | 13.7% | 15.3% |

### OEM Scraper Status

| OEM | Expected | Phone % | Status |
|-----|----------|---------|--------|
| Carrier | ~2,618 | 99% | ✅ RUNNING |
| Mitsubishi | ~1,799 | 99% | ✅ RUNNING |
| Rheem | ~1,648 | 100% | ✅ RUNNING |
| Generac | ~1,706 | 98% | 🔧 FIXING |
| Trane | ~2,802 | 0% | ENRICHMENT-READY |
| Kohler | ~500 | 99% | ⏳ VALIDATED |

---

## Technology Stack

### Core Technologies
- **Python 3.10+** - Primary language
- **SQLite** - Master database (`output/pipeline.db`, ~101MB)
- **Playwright** - Browser automation (via MCP or Browserbase)
- **Patchright** - Stealth Playwright fork (bot detection bypass)
- **Browserbase** - Cloud browser automation (production runs)

### Data Pipeline
- **Supabase PostgreSQL** - Shared with sales-agent (star schema)
- **Close CRM** - Final destination (sales pipeline)
- **Hunter.io / Apollo** - Contact enrichment

### Testing
- **Pytest** - Unit and integration tests
- **Coverage** - 80%+ target

---

## Architecture Patterns

### 1. Philosophy: "NAME IS THE ANCHOR"

**Company name is the PRIMARY field**. sales-agent enriches contact info from there.

**Data Priority**:
1. `company_name` (required)
2. `primary_phone` (grab if visible, EXCLUDE toll-free)
3. `primary_email` (grab if visible)
4. `street`, `city`, `state`, `zip`
5. `website_url` / `primary_domain`

**Toll-Free Exclusion**: 800, 888, 877, 866, 855, 844, 833

### 2. Multi-Signal Deduplication

**Hierarchy** (priority order):
1. **Phone** (96% of matches) - Normalize to 10 digits
2. **Email** - Exact match, exclude generic
3. **Domain** - Exclude webmail (gmail, yahoo, hotmail)
4. **Fuzzy Name** - 85% threshold + same state

**Implementation**: `database/deduplication.py`

### 3. StandardizedDealer Pattern

**All scrapers output**: `StandardizedDealer` dataclass

```python
@dataclass
class StandardizedDealer:
    company_name: str
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_email: Optional[str] = None
    website_url: Optional[str] = None
    tier: Optional[str] = None  # OEM certification tier
    source_type: str = 'oem'
    oem_name: Optional[str] = None
```

**Why**: Uniform data structure → SQLite → Supabase → sales-agent → Close CRM

### 4. Scraper Factory Pattern

**File**: `scrapers/scraper_factory.py`

**Purpose**: Register all scrapers in one place, CLI access via `--oem [name]`

```python
SCRAPER_REGISTRY = {
    'carrier': CarrierScraper,
    'mitsubishi': MitsubishiScraper,
    'rheem': RheemScraper,
    # ... etc
}
```

**Usage**:
```bash
python scripts/run_oem_scraper.py --oem carrier --mode browserbase
```

### 5. Failsafe Archive System

**CRITICAL**: Run BEFORE any database changes

**Script**: `scripts/failsafe_archive.py`

**What it does**:
1. Creates timestamped backup directory: `output/_failsafe_archive/YYYYMMDD_HHMMSS/`
2. Copies ALL files: CSV, JSON, SQLite
3. Generates SHA256 checksums: `checksums.sha256`
4. Creates manifest: `MANIFEST.json`

**Rollback**:
```bash
ls -la output/_failsafe_archive/
cp output/_failsafe_archive/[timestamp]/pipeline.db output/pipeline.db
```

---

## Directory Structure

```
dealer-scraper-mvp/
├── scrapers/                     # OEM scrapers
│   ├── base_scraper.py           # BaseScraper class
│   ├── scraper_factory.py        # Factory pattern
│   ├── carrier_scraper.py        # Carrier HVAC
│   ├── mitsubishi_scraper.py     # Mitsubishi VRF/HVAC
│   ├── rheem_scraper.py          # Rheem HVAC
│   ├── generac_scraper.py        # Generac generators
│   ├── kohler_scraper.py         # Kohler generators
│   ├── trane_scraper.py          # Trane HVAC (enrichment-ready)
│   └── [15 more OEM scrapers]
│
├── database/                     # Database logic
│   ├── pipeline_db.py            # PipelineDB class
│   ├── deduplication.py          # Multi-signal deduplication
│   └── models.py                 # SQLAlchemy models
│
├── scripts/                      # Utility scripts
│   ├── run_oem_scraper.py        # Run individual scrapers
│   ├── failsafe_archive.py       # Backup system
│   ├── migrate_oem_to_sqlite.py  # Import OEM data
│   ├── migrate_fl_to_sqlite.py   # Import FL licenses
│   ├── migrate_ca_to_sqlite.py   # Import CA licenses
│   ├── migrate_tx_to_sqlite.py   # Import TX licenses
│   ├── push_to_supabase.py       # Push to Supabase (dim_companies)
│   ├── export_for_sales_agent.py # Export clean CSV
│   ├── sync_dashboard_data.py    # Auto-sync dashboard
│   └── audit_oem_data.py         # Data quality audit
│
├── output/                       # Data files
│   ├── pipeline.db               # Master SQLite database (~101MB)
│   ├── _failsafe_archive/        # Versioned backups
│   ├── sales_agent_export/       # Clean exports for sales-agent
│   └── oem_data/                 # Raw OEM scrape data
│
├── dashboard/                    # Streamlit dashboard
│   ├── components/Dashboard.tsx  # Main dashboard component
│   └── public/data/dashboard_data.json
│
├── tests/                        # Pytest tests
│   ├── test_scrapers.py          # Scraper tests
│   ├── test_database.py          # Database tests
│   └── test_deduplication.py     # Deduplication tests
│
├── PRPs/                         # Project Requirements Plans
│   ├── templates/                # PRP templates
│   │   └── prp_base.md           # Base template
│   └── [date]-[feature].md       # Feature PRPs
│
├── .claude/                      # Claude Code configuration
│   ├── commands/                 # Slash commands
│   │   ├── validate.md           # Multi-phase validation
│   │   ├── generate-prp.md       # PRP generation
│   │   └── execute-prp.md        # PRP execution
│   └── CLAUDE.md                 # Project instructions
│
├── PLANNING.md                   # This file
├── TASK.md                       # Current tasks
├── requirements.txt              # Python dependencies
└── pytest.ini                    # Pytest config
```

---

## Database Schema (SQLite)

### Core Tables

**contractors** (master table):
```sql
CREATE TABLE contractors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  normalized_name TEXT,
  street TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  primary_phone TEXT,
  primary_email TEXT,
  primary_domain TEXT,
  website_url TEXT,
  icp_score INTEGER DEFAULT 0,
  icp_tier TEXT,
  source_type TEXT,  -- 'oem', 'state_license', 'manual'
  is_deleted BOOLEAN DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contractors_normalized_name ON contractors(normalized_name);
CREATE INDEX idx_contractors_phone ON contractors(primary_phone);
CREATE INDEX idx_contractors_email ON contractors(primary_email);
CREATE INDEX idx_contractors_state ON contractors(state);
```

**licenses** (1:N with contractors):
```sql
CREATE TABLE licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contractor_id INTEGER REFERENCES contractors(id),
  license_number TEXT,
  license_type TEXT,
  license_category TEXT,
  state TEXT,
  status TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**oem_certifications** (1:N with contractors):
```sql
CREATE TABLE oem_certifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contractor_id INTEGER REFERENCES contractors(id),
  oem_name TEXT,
  tier TEXT,  -- 'Gold', 'Silver', 'Bronze', 'Certified'
  program TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**file_imports** (tracks imported files by SHA256):
```sql
CREATE TABLE file_imports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_hash TEXT UNIQUE,
  file_path TEXT,
  imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  record_count INTEGER
);
```

---

## Supabase Integration (Star Schema)

### Shared Tables with sales-agent

| Table | Purpose | dealer-scraper writes? |
|-------|---------|------------------------|
| `dim_companies` | Master lead list (SOURCE OF TRUTH) | ✅ Yes |
| `dim_contacts` | People at companies | ✅ Yes (from scraped data) |
| `dim_sources` | Data origin tracking | ❌ No (pre-populated) |
| `dim_users` | Team members | ❌ No (pre-populated) |
| `fact_enrichments` | Enrichment events | ✅ Yes (log each scrape) |
| `re_enrich_queue` | Cross-project queue | ✅ Yes (process pending) |
| `mv_icp_gold_leads` | Gold tier view | ❌ No (auto-refreshed) |
| `mv_bdr_work_queue` | BDR work queue | ❌ No (auto-refreshed) |

### Push Script: `push_to_supabase.py`

**Target**: `dim_companies` table (NOT `icp_gold_leads`)

**Flow**:
1. Query SQLite for contractors (exclude duplicates)
2. Map to `dim_companies` schema
3. Insert with `source_type = 'dealer_scraper'`
4. Log to `fact_enrichments`
5. Refresh materialized views (`mv_icp_gold_leads`, `mv_bdr_work_queue`)

**Usage**:
```bash
# Dry run (test without inserting)
python scripts/push_to_supabase.py --dry-run

# Production push
python scripts/push_to_supabase.py
```

### Re-Enrichment Queue: `process_reenrich_queue.py`

**Purpose**: Poll `re_enrich_queue` and re-scrape companies flagged by sales-agent

**Workflow**:
1. Poll `re_enrich_queue WHERE status = 'pending'`
2. For each company with domain:
   - Run Hunter.io domain search
   - Run Browserbase team page scrape (if enabled)
   - Compare with existing `dim_contacts`
   - Flag NEW contacts found
3. Update queue: `status = 'completed'`, `result_summary = {...}`
4. Push new contacts to `dim_contacts` with `source = 're_enrich'`
5. Refresh materialized views

**Usage**:
```bash
# Process pending re-enrichment requests
python scripts/process_reenrich_queue.py

# Check queue status
python scripts/process_reenrich_queue.py --status
```

---

## ICP Scoring System

**Philosophy**: Resimercial (residential + commercial) multi-OEM MEP+E contractors with O&M capabilities.

### Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Resimercial | 35% | Both residential + commercial |
| Multi-OEM | 25% | 2+ platform certifications |
| MEP+E | 25% | Self-performing trades (HVAC + Plumbing + Electrical) |
| O&M | 15% | Maintenance contracts |

### Tiers

| Tier | Score | Action |
|------|-------|--------|
| PLATINUM | 80-100 | Priority outreach |
| GOLD | 60-79 | High value |
| SILVER | 40-59 | Nurture |
| BRONZE | <40 | Low priority |

### Implementation

**Script**: `create_gold_standard_lists.py` (in sales-agent repo)

**Output**: ICP scores written to `icp_score`, `icp_tier` columns

---

## Scraper Modes

### 1. VALIDATE Mode (Local Testing)

**Purpose**: Test scraper with 5 records locally

**Requirements**: Playwright installed (`playwright install chromium`)

**Usage**:
```bash
python scripts/run_oem_scraper.py --oem carrier --mode validate --limit 5
```

**Pros**: Fast, free, local debugging
**Cons**: May fail on bot detection

### 2. BROWSERBASE Mode (Production)

**Purpose**: Production runs with cloud browser

**Requirements**: `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` in `.env`

**Usage**:
```bash
python scripts/run_oem_scraper.py --oem carrier --mode browserbase
```

**Pros**: Bypasses bot detection, scalable, no local resources
**Cons**: Costs money (~$0.02/session)

### 3. STEALTH Mode (Patchright)

**Purpose**: Bypass advanced bot detection (Tesla, Enphase)

**Requirements**: Patchright installed (`pip install patchright`)

**Usage**:
```bash
python scripts/run_oem_scraper.py --oem tesla --mode stealth
```

**Pros**: Stealth fingerprints, free
**Cons**: Slower than Browserbase

---

## Data Quality Audit

**Script**: `scripts/audit_oem_data.py`

**What it checks**:
- Phone coverage %
- Email coverage %
- Duplicate rate
- Expected vs. actual record count
- Toll-free number leakage

**Usage**:
```bash
# Audit all OEMs
python scripts/audit_oem_data.py

# Audit specific OEM
python scripts/audit_oem_data.py --oem carrier
```

**Output**:
```
OEM: Carrier
Expected: 2,618 records
Actual: 2,591 records (99% success)
Phone Coverage: 99%
Email Coverage: 0%
Duplicates: 1.2%
Toll-Free Leakage: 0%
```

---

## Testing Strategy

### Unit Tests (Pytest)

**Location**: `tests/test_scrapers.py`, `tests/test_database.py`

**Coverage Target**: 80%+

**Example**:
```python
def test_scraper_excludes_toll_free():
    scraper = CarrierScraper()
    dealers = scraper.scrape(limit=100)
    phones = [d.primary_phone for d in dealers if d.primary_phone]
    assert not any(p.startswith('800') for p in phones)
```

**Run**:
```bash
pytest tests/ -v --cov=scrapers --cov-fail-under=80
```

### Integration Tests

**End-to-End Flow**:
```bash
# 1. Run scraper
python scripts/run_oem_scraper.py --oem carrier --mode browserbase --limit 10

# 2. Import to SQLite
python scripts/migrate_oem_to_sqlite.py --oem carrier

# 3. Export for sales-agent
python scripts/export_for_sales_agent.py --limit 10

# 4. Validate export
cat output/sales_agent_export/leads_*.csv | head -20
```

---

## Known Limitations

### Data Quality by Source

**State Licenses**:
- **TX**: 72K records are individuals (not companies) - FILTER NEEDED
- **FL**: 96.8% email, <1% phone (DBPR doesn't publish phone)
- **CA**: 99% phone, <1% email (CSLB doesn't publish email)
- **NJ/NY**: MEP licenses are county-level, not state

**OEMs**:
- **Trane**: 0% contact (866 = call center) - Use as ENRICHMENT-READY leads
- **Most OEMs**: Phone only (dealer locators don't expose email)
- **Schneider Electric**: 77% email (HIGHEST of any OEM!)

### Geographic Coverage

**Strong States** (95%+ coverage):
- CA, FL, TX, NY

**Weak States** (fragmented licensing):
- NJ (county-level MEP licenses)
- States without centralized license databases

---

## Future Architecture Considerations

### Planned Features
- [ ] Close CRM custom fields (OEM Certifications, State Licenses, OEM Count)
- [ ] Smart Views in Close for campaign filtering
- [ ] Fix 15 broken OEM scrapers (URL changes, selector updates)
- [ ] Trane detail page enrichment (Google ratings, reviews, certs, hours)
- [ ] Kohler production run (extraction validated)
- [ ] TX data cleanup (filter individuals)

### Scalability
- [ ] Redis caching for scraped data
- [ ] Queue system for scraper jobs (Celery)
- [ ] Distributed scraping (multiple Browserbase sessions)
- [ ] PostgreSQL migration (if SQLite exceeds 500MB)

---

**Last Reviewed**: 2025-11-30
**Next Review**: 2025-12-31
