# Dealer Scraper MVP - Current Tasks

**Last Updated**: 2025-12-25

**CRITICAL RULES:**
- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- API keys in `.env` only, never hardcoded
- ALWAYS create failsafe archive before database changes

---

## Active Tasks

### 🔥 Priority 1: Close CRM Custom Fields Implementation

**Status**: Script Complete, Testing Pending
**Effort**: 4-6 hours
**PRP**: `PRPs/2025-11-30-close-crm-oem-fields.md` (if generated)

**⚠️ PROJECT BOUNDARY NOTE**:
Close CRM sync script (`sync_to_close_crm.py`) was developed in dealer-scraper for testing,
but PRODUCTION use should be in the sales-agent repository. This script will be moved to
sales-agent after validation. dealer-scraper's job is to push to Supabase ONLY.

**Tasks**:
- [ ] Create OEM Certifications multi-value field in Close CRM
- [ ] Create State Licenses multi-value field in Close CRM
- [ ] Create OEM Count number field
- [x] Create `scripts/sync_to_close_crm.py` (COMPLETE - 29 TDD tests passing)
- [ ] Test with 5 leads (READY - script exists, needs integration test)
- [ ] Create Smart Views for OEM filtering

**Dependencies**:
- Close CRM API access
- OEM data in SQLite
- Test leads identified

**Blockers**: None

**Plan**: `~/.claude/plans/streamed-moseying-moon.md`

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

**Status**: Ready to Execute
**Effort**: 2 hours

**Tasks**:
- [ ] Review extraction script (VALIDATED Nov 28)
- [ ] Run Browserbase production scraper
- [ ] Import to SQLite
- [ ] Verify data quality (phone %, expected count)
- [ ] Push to Supabase
- [ ] Update CLAUDE.md status to COMPLETE

**Dependencies**:
- Browserbase API credits
- SQLite database ready

**Blockers**: None

**Expected**: 500+ generator dealers, 99% phone coverage

---

### Priority 4: OEM Scraper Validation Sprint

**Status**: ✅ COMPLETE (Dec 25, 2025)
**Effort**: 4-6 hours

**Final Status: 20 Active Scrapers, 8 Archived**

**Active (Working)**:
- HVAC (8): Carrier, Trane, Lennox, York, Rheem, Mitsubishi, Honeywell, Sensi
- Generators (4): Generac, Briggs & Stratton, Cummins, Kohler
- Solar/Inverter (6): Tesla, Enphase, Fronius, SMA, Sol-Ark, SolarEdge
- Battery (1): SimpliPhi
- Building Automation (1): Schneider Electric

**Archived (Not Viable for Bulk Scraping)**:
- ABB: Divested residential solar 2020
- Delta, GoodWe, Growatt, Sungrow, Tigo: No public ZIP-searchable locator
- Johnson Controls: Returns corporate offices only (not contractor ICPs)

**Completed Tasks**:
- [x] Live tested all 5 remaining scrapers (Honeywell, Sensi, Sol-Ark, SimpliPhi, Schneider)
- [x] Archived Johnson Controls (returns corporate offices, not ICPs)
- [x] Moved Schneider Electric from archived → active (EcoXpert contractors)
- [x] Added Browserbase mode to York, Kohler, Tesla (bot detection bypass)
- [x] Fixed Tesla US locale (/en_us/)
- [x] Created 5 new unit test files (212 tests)
- [x] Updated OEM_SCRAPER_STATUS.md
- [x] Structure validation: 20/20 pass
- [x] Test suite: 364 tests passing

**Dependencies**: MCP Playwright, Browserbase

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

**Last Reviewed**: 2025-11-30
**Next Review**: Daily standup
