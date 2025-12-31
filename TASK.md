# Dealer Scraper MVP - Current Tasks

**Last Updated**: 2025-12-26

**CRITICAL RULES:**
- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- API keys in `.env` only, never hardcoded
- ALWAYS create failsafe archive before database changes

---

## Active Tasks

### ✅ Priority 1: Close CRM Custom Fields Implementation

**Status**: ✅ COMPLETE (Dec 26, 2025)
**Effort**: 4-6 hours

**⚠️ PROJECT BOUNDARY NOTE**:
Close CRM sync script (`crm/`) was developed in dealer-scraper for testing,
but PRODUCTION use should be in the sales-agent repository. This script will be moved to
sales-agent after validation. dealer-scraper's job is to push to Supabase ONLY.

**Completed Tasks**:
- [x] Create 8 custom fields in Close CRM (OEM_Certifications, State_Licenses, OEM_Count, etc.)
- [x] Implement Supabase extraction from dim_companies (sales-agent shared DB)
- [x] Fix Close API contact format (phones: [{phone: "..."}])
- [x] Fix empty array handling (skip in payload)
- [x] Test with 5 leads - ALL SYNCED SUCCESSFULLY
- [ ] Create Smart Views for OEM filtering (manual in Close UI)

**Custom Fields Created**:
| Field | Type | Close ID |
|-------|------|----------|
| OEM_Certifications | list | cf_5txDBf... |
| State_Licenses | list | cf_xxxx |
| OEM_Count | number | cf_xxxx |
| License_Count | number | cf_xxxx |
| Is_Multi_OEM | boolean | cf_xxxx |
| Is_Multi_State | boolean | cf_xxxx |
| Source_Type | text | cf_xxxx |
| Coperniq_Score | number | cf_xxxx |

**CRM Module**: `crm/` (5 files, 1,177 lines)
- close_field_manager.py - Creates/fetches custom fields
- close_importer.py - Lead upsert with phone deduplication
- close_sync_service.py - Orchestrates full sync workflow
- data_extractor.py - SQLite + Supabase extraction
- models.py - CloseLeadPayload, SyncReport dataclasses

**Next Step**: Create Smart Views manually in Close CRM UI

---

### Priority 2: Trane Detail Page Enrichment

**Status**: Not Started
**Effort**: 1 day

**Problem**: 2,802 Trane records with 0% contact info (phone shows 866 call center, NOT dealer)

**Discovery**: Detail pages have valuable PRE-QUALIFICATION data:
- Google ratings (stars) - VERIFIED by Trane
- Google review count - social proof
- Certifications/tier
- Business hours

**Value**: "They do the work for us before our enrichment team verifies" - pre-qualified leads with Google ratings ready for Hunter/Apollo enrichment.

**Tasks**:
- [ ] Update Trane scraper to capture detail page data
- [ ] Extract Google ratings, review count, certs, hours
- [ ] Mark as ENRICHMENT-READY in database
- [ ] Create Hunter.io enrichment batch script
- [ ] Test with 50 sample records

**Dependencies**:
- MCP Playwright for selector testing
- Browserbase for production run
- Hunter.io API credits

**Blockers**: None

---

### Priority 3: Kohler Production Run

**Status**: 🔄 IN PROGRESS (Dec 29, 2025)
**Effort**: 4+ hours (Patchright local, no Browserbase)

**Progress (Dec 29)**:
- [x] Fixed Kohler scraper (cookie consent, React input, popup extraction)
- [x] Built master scraper v2 with card-clicking for full details
- [x] Updated config.py with 395 SREC ZIPs (30 per state × 13 states)
- [x] **307/395 ZIPs scraped (78%)**
- [x] **337 unique dealers captured**
- [x] **100% phone coverage** (0 toll-free numbers)
- [x] **~94% address coverage**
- [ ] Complete remaining 88 ZIPs
- [ ] Import to SQLite
- [ ] Push to Supabase

**Tier Distribution**:
| Tier | Count |
|------|-------|
| Titanium | 66 |
| Platinum | 56 |
| Gold | 46 |
| Silver | 61 |
| Certified | 108 |

**States Covered**: CA(21), TX(56), FL(68), PA(31), NJ(35), MA(13), OH(30), MD(13), NY(15), NH(12), RI(4), CT(3), DE(1), others

**Technical Notes**:
- Using Patchright (stealth Playwright) locally - bypasses Akamai bot detection
- Card-clicking extraction gets full dealer details from popup
- NYC ZIPs (10xxx) return 0 dealers - expected (no generators in dense urban)

**Dependencies**: None (local Patchright, no cloud API needed)

**Expected Final**: 350-400 unique dealers across 15 SREC states

---

### Priority 4: OEM Scraper Validation Sprint

**Status**: ✅ COMPLETE (Dec 26, 2025 - Sprint 3)
**Effort**: 8+ hours (3 sprints)

**Final Status: 20 Active Scrapers, 8 Archived**
**Live Validation: 15 WORKING, 5 PARTIAL (need Browserbase)**

**Working (15)**:
- HVAC: Carrier, Trane, Lennox, Rheem, Mitsubishi, Sensi
- Generators: Generac, Briggs & Stratton, Cummins
- Solar/Inverter: Enphase, SMA, Sol-Ark, SolarEdge
- Battery: SimpliPhi
- Building Automation: Schneider Electric

**Need Browserbase (5)**:
- York, Kohler (bot detection)
- Tesla, Honeywell (iframe/context issues)
- Fronius (geolocation API required)

**Archived (Not Viable for Bulk Scraping)**:
- ABB: Divested residential solar 2020
- Delta, GoodWe, Growatt, Sungrow, Tigo: No public ZIP-searchable locator
- Johnson Controls: Returns corporate offices only (not contractor ICPs)

**Sprint 3 Completed (Dec 26)**:
- [x] Converted SimpliPhi from manual → auto Playwright (10 dealers/ZIP)
- [x] Converted Sol-Ark from manual → auto Playwright (20 dealers/ZIP)
- [x] Converted SolarEdge from manual → auto Playwright (5 dealers/ZIP)
- [x] Fixed Trane ZIP selector + extraction script (6 dealers/ZIP)
- [x] Fixed Sensi DDL cards + Google Places autocomplete (500+ locations)
- [x] Documented Fronius Browserbase requirement (geolocation API)
- [x] Updated OEM_SCRAPER_STATUS.md with Sprint 3 results
- [x] Structure validation: 20/20 pass

**Sprint 1-2 Completed (Dec 25)**:
- [x] Archived Johnson Controls (returns corporate offices, not ICPs)
- [x] Moved Schneider Electric from archived → active
- [x] Added Browserbase mode to York, Kohler, Tesla
- [x] Fixed Tesla US locale (/en_us/)
- [x] Created 5 unit test files (212 tests)
- [x] Test suite: 380 tests (355 pass, 25 env issues)

**Dependencies**: Playwright, Browserbase

**Blockers**: None

---

### Priority 5: TX Data Cleanup

**Status**: Not Started
**Effort**: 2 hours

**Problem**: 72K records are INDIVIDUALS ("Last, First" format), not companies

**Solution**: Filter to BUSINESSES only for sales-agent export

**Tasks**:
- [ ] Create `scripts/filter_tx_individuals.py`
- [ ] Detect "Last, First" pattern
- [ ] Mark as `is_individual = True` in SQLite
- [ ] Exclude from sales-agent export
- [ ] Verify company records remain

**Dependencies**: None

**Blockers**: None

**Expected**: ~30K business records retained

---

## Backlog

### Medium Priority

- [ ] Hunter.io Batch 2 enrichment (leads 501-1000, ~$5)
- [ ] Re-enrich stale leads (30+ days old)
- [ ] Dashboard connection to real Supabase data
- [ ] Increase HOT leads (only 2 currently, need more direct phones)

### Low Priority

- [ ] Redis caching layer
- [ ] Queue system for scraper jobs (Celery)
- [ ] PostgreSQL migration (if SQLite exceeds 500MB)
- [ ] Distributed scraping (multiple Browserbase sessions)

---

## Completed Tasks

### 2025-12-26
- [x] **OEM Scraper Sprint 3** - 15 working, 5 need Browserbase
- [x] Converted SimpliPhi from manual → auto Playwright (10 dealers/ZIP)
- [x] Converted Sol-Ark from manual → auto Playwright (20 dealers/ZIP)
- [x] Converted SolarEdge from manual → auto Playwright (5 dealers/ZIP)
- [x] Fixed Trane ZIP input selector + extraction script
- [x] Fixed Sensi DDL cards + Google Places autocomplete
- [x] Documented Fronius Browserbase requirement (geolocation API)
- [x] Updated OEM_SCRAPER_STATUS.md with Sprint 3 results
- [x] Close CRM Custom Fields Implementation - 8 fields created, 5 leads synced
- [x] Implemented Supabase extraction from dim_companies (sales-agent shared DB)
- [x] Fixed Close API contact format and empty array handling
- [x] Created crm/ module (5 files, 1,177 lines)
- [x] Added crm/ to git tracking (removed from .gitignore)

### 2025-12-25
- [x] OEM Scraper Validation Sprint - 20 active scrapers, 8 archived
- [x] Live tested 5 scrapers: Honeywell (25 dealers), Sensi (500+), Sol-Ark (10+), SimpliPhi (5+), Schneider (2)
- [x] Archived Johnson Controls (returns corporate offices, not ICPs)
- [x] Moved Schneider Electric from archived → active (EcoXpert contractors)
- [x] Added Browserbase mode for York, Kohler, Tesla (bot detection bypass)
- [x] Fixed Tesla US locale (/en_us/)
- [x] Created 5 unit test files: honeywell, sensi, solark, simpliphi, schneider (212 tests)
- [x] Updated OEM_SCRAPER_STATUS.md with full audit
- [x] Structure validation: 20/20 pass
- [x] Full test suite: 364 tests passing

### 2025-12-24
- [x] Colorado DORA bulk migration (7,508 contractors, 114 multi-trade, 9 TDD tests)
- [x] CO multi-trade export (290 PLATINUM business entities to CSV/JSON)
- [x] Close CRM sync script (215 lines, 29 TDD tests passing)
- [x] Browserbase retry logic (3 scrapers: Cummins, Schneider, Tesla)
- [x] Doc cleanup (7 stale files archived to docs/_archive/)
- [x] Supabase push script (push_to_supabase.py - 280 lines)

### 2025-11-30
- [x] Created context engineering files (validate, generate-prp, execute-prp)
- [x] Created PRP base template
- [x] Created PLANNING.md
- [x] Created TASK.md

### 2025-11-28 (from CLAUDE.md)
- [x] Supabase push COMPLETE (14,204 leads in icp_gold_leads)
- [x] SQLite push (12,426 OEM-certified contractors)
- [x] Close CRM integration plan READY
- [x] Kohler scraper VALIDATED (extraction script ready)
- [x] Trane scraper deep dive (identified detail page enrichment opportunity)
- [x] Auto-sync script created (`sync_dashboard_data.py`)
- [x] Failsafe archive system implemented

### Earlier Milestones
- [x] OEM scraper factory pattern implemented
- [x] Multi-signal deduplication (phone, email, domain, fuzzy name)
- [x] StandardizedDealer pattern
- [x] State license migrations (FL, CA, TX, NY)
- [x] ICP scoring system
- [x] Dashboard (Vercel deployment)

---

## Notes

**Current Focus**: Close CRM custom fields for OEM tracking

**Next Milestone**: Sync 1,000+ prioritized leads to Close CRM with OEM data

**Risks**:
- Hunter.io costs (mitigation: batch processing, credit monitoring)
- Browserbase rate limits (mitigation: stagger runs, use STEALTH mode for sensitive sites)
- Trane detail page structure changes (mitigation: test with 50 samples first)

**Dependencies**:
- Close CRM API key
- Browserbase API credits
- Hunter.io API credits

---

## Task Management Workflow

1. **New Feature Requested**:
   - Run `/generate-prp` to create PRP
   - Add tasks to this file
   - Prioritize in Active Tasks section

2. **Working on Task**:
   - Move to "In Progress" status
   - Update PRP with progress
   - Run `/validate` frequently
   - Create failsafe archive if touching database

3. **Task Complete**:
   - Check off in PRP
   - Move to Completed Tasks section
   - Update CLAUDE.md if OEM status changed
   - Update dashboard (`sync_dashboard_data.py`)
   - Run `/validate` to ensure quality

4. **Task Blocked**:
   - Note blocker in Blockers section
   - Move to Backlog if long-term block

---

## Data Quality Metrics (Current)

| Metric | Value |
|--------|-------|
| Total contractors | 217,523 |
| Phone coverage | 35% |
| Email coverage | 28% |
| Duplicate rate | 1.8% |
| OEM-certified | 12,426 (5.7%) |
| Multi-trade | 4,231 (1.9%) |

**Target Metrics** (End of Month):
- Total contractors: 250,000+
- Phone coverage: 40%+
- Email coverage: 30%+
- Duplicate rate: <2%
- OEM-certified: 15,000+ (6%+)

---

**Last Reviewed**: 2025-12-26
**Next Review**: Daily standup
