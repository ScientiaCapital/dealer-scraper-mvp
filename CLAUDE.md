# CLAUDE.md

## Project Overview

**Coperniq Partner Prospecting System** - Contractor lead generation feeding into sales-agent pipeline.

**Data Flow**: `dealer-scraper-mvp` → `sales-agent` (Supabase) → `Close CRM`

## Current Status (Nov 28, 2025)

### Database
- **SQLite**: `output/pipeline.db` (217,392 contractors, ~101MB)
- **Failsafe Archive**: `output/_failsafe_archive/20251128_110403/` (489 files, 2.2GB, SHA256 checksums)

### Data Quality
| State | Records | Email % | Phone % |
|-------|---------|---------|---------|
| TX | 101,085 | 0.7% | 11.2% |
| FL | 58,504 | 96.8% | 1.1% |
| CA | 36,355 | 0.7% | 99.0% |
| NY | 2,269 | 13.7% | 15.3% |

### OEMs in Database
| OEM | Count | Status |
|-----|-------|--------|
| Trane | 2,802 | ✅ WORKING |
| Carrier | 2,618 | ✅ WORKING |
| Mitsubishi | 1,799 | ✅ WORKING |
| Generac | 1,706 | ✅ WORKING |
| Rheem | 1,648 | ✅ WORKING |
| Briggs & Stratton | 782 | ✅ WORKING |
| Cummins | 702 | ✅ WORKING |
| Schneider Electric | 143 | ✅ WORKING |
| York | 90 | ✅ WORKING |

### Dashboard
- **URL**: Vercel deployment (check `vercel project ls`)
- **Data**: `dashboard/public/data/dashboard_data.json`

## SQLite Schema

```sql
-- contractors (master table - COMPANY NAME IS ANCHOR)
id, company_name, normalized_name, street, city, state, zip,
primary_phone, primary_email, primary_domain, website_url,
icp_score, icp_tier, source_type, is_deleted, created_at, updated_at

-- licenses (1:N with contractors)
id, contractor_id, license_number, license_type, license_category, state, status

-- oem_certifications (1:N with contractors)
id, contractor_id, oem_name, tier, program

-- file_imports (tracks imported files by SHA256)
id, file_hash, file_path, imported_at, record_count
```

## Key Scripts

```bash
# Failsafe archive (RUN BEFORE ANY MIGRATION)
./venv/bin/python3 scripts/failsafe_archive.py

# Export for sales-agent
./venv/bin/python3 scripts/export_for_sales_agent.py

# State license migrations
./venv/bin/python3 scripts/migrate_fl_to_sqlite.py
./venv/bin/python3 scripts/migrate_ca_to_sqlite.py
./venv/bin/python3 scripts/migrate_tx_to_sqlite.py

# Check stats
./venv/bin/python3 -c "from database import PipelineDB; print(PipelineDB().get_stats())"
```

## Sales-Agent Integration

**sales-agent Supabase**: Already set up (see `/Users/tmkipper/Desktop/tk_projects/sales-agent/.env`)

**Import script**: `sales-agent/backend/import_from_scraper.py`

**Lead model fields** (sales-agent expects):
- `company_name` (ANCHOR - required)
- `contact_phone`, `contact_email`, `company_website`
- OEM counts: `hvac_oem_count`, `solar_oem_count`, `battery_oem_count`, `generator_oem_count`
- Capability flags: `has_hvac`, `has_solar`, `has_generator`, `has_battery`
- Scores: `mep_e_score`, `qualification_score`

**CRM sync workflow**:
1. Check if company exists in Close CRM
2. If NO → Create new lead
3. If YES → Enrich with new data
4. Track ATL (Above the Line) vs BTL (Below the Line) tiers

## ICP Scoring

| Tier | Score | Action |
|------|-------|--------|
| PLATINUM | 80-100 | Priority outreach |
| GOLD | 60-79 | High value |
| SILVER | 40-59 | Nurture |
| BRONZE | <40 | Low priority |

**Scoring dimensions**:
1. Resimercial (35%) - Both residential + commercial
2. Multi-OEM (25%) - 2+ platform certifications
3. MEP+E (25%) - Self-performing trades
4. O&M (15%) - Maintenance contracts

## Deduplication

**Hierarchy**:
1. Phone (96% of matches) - Normalized to 10 digits
2. Email - Exact match
3. Domain - Excludes webmail
4. Fuzzy Name - 85% threshold + same state

## File Structure

```
output/
├── pipeline.db                    # Master SQLite database
├── _failsafe_archive/             # Versioned backups with checksums
│   └── YYYYMMDD_HHMMSS/
│       ├── MANIFEST.json
│       ├── checksums.sha256
│       ├── csv/
│       ├── json/
│       └── sqlite/
├── sales_agent_export/            # Clean exports for sales-agent
└── oem_data/                      # Raw OEM scrape data

dashboard/
├── components/Dashboard.tsx       # Main dashboard component
└── public/data/dashboard_data.json
```

## Environment Variables

```bash
# Required
BROWSERBASE_API_KEY=...
BROWSERBASE_PROJECT_ID=...

# Optional
RUNPOD_API_KEY=...
CLOSE_API_KEY=...
HUNTER_API_KEY=...
```

## Known Limitations

- TX: 72K records are individuals (not companies)
- FL: 96.8% email, <1% phone
- CA: 99% phone, <1% email
- OEMs: Phone only (no emails from dealer locators)
- NJ/NY: MEP licenses are county-level, not state

## Conductor-AI Plugin

`plugins/scraper_tools/` contains conductor-ai compatible wrappers:
- `DealerLocatorTool` - Scrape OEM dealer locators
- `ContractorEnrichTool` - Enrich with company data
- `LicenseValidateTool` - Validate state licenses

Works standalone without conductor-ai.
