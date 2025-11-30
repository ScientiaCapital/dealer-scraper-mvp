# Dealer Scraper MVP - Current Tasks

**Last Updated**: 2025-11-30

**CRITICAL RULES:**
- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- API keys in `.env` only, never hardcoded
- ALWAYS create failsafe archive before database changes

---

## Active Tasks

### 🔥 Priority 1: Close CRM Custom Fields Implementation

**Status**: Not Started
**Effort**: 4-6 hours
**PRP**: `PRPs/2025-11-30-close-crm-oem-fields.md` (if generated)

**Tasks**:
- [ ] Create OEM Certifications multi-value field in Close CRM
- [ ] Create State Licenses multi-value field in Close CRM
- [ ] Create OEM Count number field
- [ ] Create `scripts/sync_to_close_crm.py`
- [ ] Test with 5 leads (Tim Kipper as owner)
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

### Priority 4: Fix 15 Broken OEM Scrapers

**Status**: In Progress
**Effort**: 1 week (15 scrapers × 30min each)

**Broken Scrapers**:
- Delta, Fronius, ABB, GoodWe, Growatt (Solar inverters)
- Honeywell, Sensi, Lennox (HVAC/Smart home)
- SimpliPhi, Sol-Ark, SolarEdge, Sungrow, Tigo (Solar/Battery)
- Johnson Controls (Building automation)

**Common Issues**:
- URL changes (404s)
- Selector updates needed
- API endpoint changes

**Approach**:
1. Use MCP Playwright to inspect each site
2. Update URLs/selectors in scraper files
3. Test with `--mode validate --limit 5`
4. Run production with `--mode browserbase`

**Tasks**:
- [ ] Delta scraper
- [ ] Fronius scraper
- [ ] ABB scraper
- [ ] GoodWe scraper
- [ ] Growatt scraper
- [ ] Honeywell scraper
- [ ] Sensi scraper
- [ ] Lennox scraper
- [ ] SimpliPhi scraper
- [ ] Sol-Ark scraper
- [ ] SolarEdge scraper
- [ ] Sungrow scraper
- [ ] Tigo scraper
- [ ] Johnson Controls scraper
- [ ] Generac scraper (FIXING - extraction script needs update)

**Dependencies**: MCP Playwright

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
