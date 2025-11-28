# CLAUDE.md

## Project Overview

**Coperniq Partner Prospecting System** - Contractor lead generation feeding into sales-agent pipeline.

**Data Flow**: `dealer-scraper-mvp` → `sales-agent` (Supabase) → `Close CRM`

## Current Status (Nov 28, 2025 - End of Day)

### Database
- **SQLite**: `output/pipeline.db` (217,523 contractors, ~101MB)
- **Failsafe Archive**: `output/_failsafe_archive/20251128_110403/` (489 files, 2.2GB, SHA256 checksums)

### Data Quality
| State | Records | Email % | Phone % |
|-------|---------|---------|---------|
| TX | 101,085 | 0.7% | 11.2% |
| FL | 58,504 | 96.8% | 1.1% |
| CA | 36,355 | 0.7% | 99.0% |
| NY | 2,269 | 13.7% | 15.3% |

### OEMs in Database (12 total, 12,426 records)
| OEM | Count | Phone % | Status | Notes |
|-----|-------|---------|--------|-------|
| Trane | 2,802 | 0% | ENRICHMENT-READY | Has Google ratings/reviews on detail pages |
| Carrier | 2,618 | 99% | WORKING | |
| Mitsubishi | 1,799 | 99% | WORKING | VRF/HVAC - high commercial value |
| Generac | 1,706 | 98% | WORKING | |
| Rheem | 1,648 | 100% | WORKING | |
| Briggs & Stratton | 782 | 99% | WORKING | |
| Cummins | 702 | 99% | WORKING | Browserbase validated |
| Schneider Electric | 143 | 66% | WORKING | 77% email! EcoXpert partners |
| York | 90 | 100% | WORKING | |
| Tesla | 67 | 96% | WORKING | |
| SMA | 43 | 100% | WORKING | |
| Enphase | 26 | 96% | WORKING | |

### Dashboard
- **URL**: Vercel deployment (check `vercel project ls`)
- **Data**: `dashboard/public/data/dashboard_data.json`
- **Auto-sync**: `./venv/bin/python3 scripts/sync_dashboard_data.py`

---

## WEEKEND PRIORITIES (Nov 29 - Dec 1, 2025)

### Priority 1: Trane Enrichment Strategy
**Problem**: 2,802 records with 0% contact info (phone shows 1-866-953-1673 = Trane call center, NOT dealer)

**Discovery**: Detail pages have valuable PRE-QUALIFICATION data:
- Company name + location
- Google ratings (stars) - VERIFIED by Trane
- Google review count - social proof
- Certifications/tier
- Business hours

**Value**: "They do the work for us before our enrichment team verifies" - pre-qualified leads with Google ratings ready for Hunter/Apollo enrichment.

**Action**: Update Trane scraper to capture detail page data (ratings, reviews, certs, hours) even without direct phone.

### Priority 2: Fix 15 BROKEN OEM Scrapers
Most are URL changes (404s) or selector updates needed:
- Delta, Fronius, ABB, GoodWe, Growatt (Solar inverters)
- Honeywell, Sensi, Lennox (HVAC/Smart home)
- SimpliPhi, Sol-Ark, SolarEdge, Sungrow, Tigo (Solar/Battery)
- Johnson Controls (Building automation)

**Approach**: Use MCP Playwright to inspect each site, update URLs/selectors

### Priority 3: Kohler Production Run
- Extraction script VALIDATED (Nov 28)
- Needs Browserbase production run
- Expected: 500+ generator dealers

### Priority 4: TX Data Cleanup
- 72K records are INDIVIDUALS ("Last, First" format)
- Filter to BUSINESSES only for sales-agent export

---

## KEY INSIGHTS (Captured Nov 28)

### OEM Data Quality Audit Results
**EXCELLENT (95%+ phone - outreach-ready)**:
- Carrier, Mitsubishi, Generac, Rheem, Briggs & Stratton, Cummins, York, Tesla, SMA, Enphase

**GOOD (66%+ - partial outreach)**:
- Schneider Electric (66% phone, 77% email - highest email of any OEM!)

**ENRICHMENT-READY (0% contact but valuable pre-qual data)**:
- Trane (2,802 records) - Has Google ratings/reviews, needs Hunter/Apollo for contact

### Trane Deep Dive Findings
1. "Call Now" button shows 1-866-953-1673 = Trane corporate call center (USELESS)
2. Detail pages have rich data: company name, city, state, Google stars, review count, certs, hours
3. Strategy: Treat as ENRICHMENT-READY leads, not direct-contact leads
4. Google reviews on Trane = pre-verification before sales-agent enrichment

### Kohler Scraper Fix (Nov 28)
- Site: kohlerhomeenergy.rehlko.com/find-a-dealer (Rehlko rebrand 2024)
- Uses Tailwind CSS - selector: `li.list-none`
- Extracts: name, phone, tier (Gold/Silver/Bronze), address, website
- Dedupes by phone, skips 844 main line
- Status: VALIDATED, needs Browserbase run

### Auto-Sync Script Created
`scripts/sync_dashboard_data.py`:
- Queries pipeline.db for real counts
- Updates dashboard_data.json automatically
- Preserves VALIDATED scrapers even with 0 records
- Optional `--deploy` flag for Vercel

---

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
# Auto-sync dashboard with database
./venv/bin/python3 scripts/sync_dashboard_data.py
./venv/bin/python3 scripts/sync_dashboard_data.py --deploy  # Deploy to Vercel

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

# Check OEM counts
./venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('output/pipeline.db')
cur = conn.cursor()
cur.execute('SELECT oem_name, COUNT(*) as cnt FROM oem_certifications GROUP BY oem_name ORDER BY cnt DESC')
for r in cur.fetchall(): print(f'{r[0]}: {r[1]}')"
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

scripts/
├── sync_dashboard_data.py         # Auto-sync dashboard with DB
├── export_for_sales_agent.py      # Export leads for sales-agent
├── failsafe_archive.py            # Create versioned backup
└── run_oem_scraper.py             # Run individual OEM scrapers

scrapers/
├── base_scraper.py                # Base class with StandardizedDealer
├── scraper_factory.py             # Factory pattern for OEM scrapers
├── kohler_scraper.py              # VALIDATED Nov 28 - needs production run
├── trane_scraper.py               # ENRICHMENT-READY - needs detail page update
└── [17 more OEM scrapers]
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

- TX: 72K records are individuals (not companies) - FILTER NEEDED
- FL: 96.8% email, <1% phone (DBPR doesn't publish phone)
- CA: 99% phone, <1% email (CSLB doesn't publish email)
- OEMs: Phone only (dealer locators don't expose email) - EXCEPT Schneider (77% email)
- NJ/NY: MEP licenses are county-level, not state
- Trane: 0% contact (866 = call center) - Use as ENRICHMENT-READY leads

## Conductor-AI Plugin

`plugins/scraper_tools/` contains conductor-ai compatible wrappers:
- `DealerLocatorTool` - Scrape OEM dealer locators
- `ContractorEnrichTool` - Enrich with company data
- `LicenseValidateTool` - Validate state licenses

Works standalone without conductor-ai.
