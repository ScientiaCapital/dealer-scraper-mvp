# PRP: [Feature Name]

**Date Created**: YYYY-MM-DD
**Type**: [OEM Scraper / Data Pipeline / Integration / Fix]
**Priority**: [High/Medium/Low]
**Effort Estimate**: [Hours/Days]
**Risk Level**: [High/Medium/Low]

**CRITICAL RULES:**
- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot via OpenRouter
- API keys in `.env` only, never hardcoded
- ALWAYS create failsafe archive before database changes
- 80%+ pytest coverage required

---

## Overview

**Problem Statement:**
[What data quality issue, scraper, or integration does this solve?]

**Business Value:**
[Why is this important? How many leads? What quality improvement?]

**Expected Outcome:**
- [X] new contractors added to pipeline
- [Y%] phone coverage expected
- [Z%] email coverage expected (if available)

---

## Technical Design

### Architecture Overview

**Scraper Type**: [New OEM Scraper / Pipeline Improvement / Integration]
**Scraper Mode**: [BROWSERBASE / PLAYWRIGHT / STEALTH]
**Database Changes**: Yes/No
**Supabase Integration**: Yes/No

**Affected Systems:**
- [ ] SQLite (`output/pipeline.db`)
- [ ] Supabase (`dim_companies`, `dim_contacts`)
- [ ] sales-agent integration
- [ ] Close CRM sync
- [ ] Dashboard

### Data Flow

```
OEM Website → Scraper → StandardizedDealer → SQLite → Deduplication → Supabase → sales-agent → Close CRM
```

### Database Schema

**New Tables** (if applicable):
```sql
-- Example: New table for feature
CREATE TABLE IF NOT EXISTS new_feature (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contractor_id INTEGER REFERENCES contractors(id),
  field_name TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Modified Tables**:
- [Table name] - [What changes]

### Deduplication Strategy

**Signals** (in priority order):
1. **Phone** (96% of matches) - Normalize to 10 digits, exclude toll-free
2. **Email** - Exact match, exclude generic (info@, contact@)
3. **Domain** - Exclude webmail (gmail, yahoo, hotmail)
4. **Fuzzy Name** - 85% threshold + same state

**Toll-Free Exclusion**: 800, 888, 877, 866, 855, 844, 833

### Scraper Design

**OEM Name**: [Full name]
**Expected Records**: [X] contractors
**Data Quality Expectation**: [Y%] phone, [Z%] email

**Key Fields**:
- `company_name` (required)
- `primary_phone` (if available)
- `primary_email` (if available)
- `street`, `city`, `state`, `zip`
- `website_url` (if available)
- `tier` (if OEM has certification tiers)

**Selectors** (if web scraping):
- Main container: `[CSS selector]`
- Company name: `[CSS selector]`
- Phone: `[CSS selector]`
- Address: `[CSS selector]`

---

## Implementation Plan

### Phase 1: Research & Design (Estimated: X hours)

**Objective**: Inspect OEM website, plan scraper architecture

- [ ] Inspect OEM dealer locator manually
- [ ] Use MCP Playwright to test selectors
- [ ] Identify required fields vs. available fields
- [ ] Document data quality expectations (phone %, email %)
- [ ] Plan deduplication strategy
- [ ] Check if scraper needs STEALTH mode (bot detection)
- [ ] Document expected record count

**Deliverables**:
- Architecture decision documented
- Scraper mode selected (BROWSERBASE/PLAYWRIGHT/STEALTH)
- Expected record count documented

**Validation**:
- No code changes (research only)
- Update this PRP with findings

---

### Phase 2: Scraper Implementation (Estimated: X hours)

**Objective**: Build scraper, test with sample data

- [ ] Create `scrapers/[oem]_scraper.py`
- [ ] Extend `BaseScraper` class
- [ ] Implement `StandardizedDealer` mapping
- [ ] Add toll-free exclusion logic (800/888/877/866/855/844/833)
- [ ] Add multi-trade detection (if applicable)
- [ ] Register scraper in `scraper_factory.py`
- [ ] Test with `--mode validate --limit 5`

**Files to Create**:
- `scrapers/[oem]_scraper.py`
- `tests/test_[oem]_scraper.py`

**Files to Modify**:
- `scrapers/scraper_factory.py` - Register scraper
- `scripts/run_oem_scraper.py` - Add CLI option

**Deliverables**:
- Scraper file created
- Sample output JSON validated
- No duplicate phone numbers in sample

**Validation**:
```bash
python scripts/run_oem_scraper.py --oem [name] --mode validate --limit 5
cat output/oem_data/[oem]_dealers.json | jq '.[:5]'
```

---

### Phase 3: Database Integration (Estimated: X hours)

**Objective**: Import scraped data to SQLite, apply deduplication

- [ ] Create failsafe archive: `python scripts/failsafe_archive.py`
- [ ] Update SQLite schema (if needed)
- [ ] Implement deduplication logic
- [ ] Add OEM to `oem_certifications` table
- [ ] Calculate ICP scores
- [ ] Test with sample data (10-20 records)
- [ ] Verify duplicates marked correctly

**Files to Create**:
- `scripts/migrate_[oem]_to_sqlite.py` (if custom logic needed)

**Files to Modify**:
- `database/pipeline_db.py` - Add deduplication logic (if needed)

**Deliverables**:
- SQLite database updated
- Duplicates marked
- ICP scores calculated

**Validation**:
```bash
python scripts/migrate_oem_to_sqlite.py --oem [name] --limit 20
python -c "from database import PipelineDB; print(PipelineDB().get_stats())"
python -c "from database import PipelineDB; print(PipelineDB().get_duplicate_stats())"
```

---

### Phase 4: Data Quality Validation (Estimated: X hours)

**Objective**: Run scraper in production, audit data quality

- [ ] Run scraper in production mode (full dataset)
- [ ] Audit data quality (phone %, email %)
- [ ] Verify deduplication working (<2% duplicates)
- [ ] Check for duplicates manually (sample 50 records)
- [ ] Compare expected vs. actual record count
- [ ] Update CLAUDE.md with OEM status

**Files to Modify**:
- `CLAUDE.md` - Update OEM status table

**Deliverables**:
- Full dataset scraped
- Data quality report generated
- CLAUDE.md updated

**Validation**:
```bash
python scripts/run_oem_scraper.py --oem [name] --mode browserbase
python scripts/audit_oem_data.py --oem [name]
python -c "from database import PipelineDB; db = PipelineDB(); print(db.get_duplicate_stats())"
```

---

### Phase 5: Supabase Integration (Estimated: X hours)

**Objective**: Push data to Supabase, verify sales-agent integration

- [ ] Create failsafe archive: `python scripts/failsafe_archive.py`
- [ ] Test Supabase connection: `python scripts/test_supabase_connection.py`
- [ ] Run `push_to_supabase.py` with `--dry-run` flag
- [ ] Verify RLS policies apply correctly
- [ ] Push to Supabase production
- [ ] Refresh materialized views (`mv_icp_gold_leads`, `mv_bdr_work_queue`)
- [ ] Validate in sales-agent dashboard

**Deliverables**:
- Data pushed to Supabase `dim_companies` table
- Materialized views refreshed
- sales-agent dashboard showing new leads

**Validation**:
```bash
python scripts/test_supabase_connection.py
python scripts/push_to_supabase.py --dry-run
python scripts/push_to_supabase.py
# Check Supabase dashboard: dim_companies, mv_icp_gold_leads
```

---

### Phase 6: Documentation & Monitoring (Estimated: X hours)

**Objective**: Update docs, sync dashboard, monitor for errors

- [ ] Update CLAUDE.md with OEM status (VALIDATED/RUNNING/COMPLETE)
- [ ] Sync dashboard: `python scripts/sync_dashboard_data.py`
- [ ] Document known limitations in CLAUDE.md
- [ ] Update TASK.md (mark complete)
- [ ] Deploy dashboard to Vercel (if applicable)
- [ ] Monitor for data quality issues (30 days)

**Files to Modify**:
- `CLAUDE.md` - OEM status, known limitations
- `TASK.md` - Mark complete
- `dashboard/public/data/dashboard_data.json` - Auto-synced

**Deliverables**:
- All docs updated
- Dashboard synced
- Monitoring configured

**Validation**:
```bash
python scripts/sync_dashboard_data.py
python scripts/sync_dashboard_data.py --deploy  # Optional
```

---

## Validation Criteria

**All must pass before marking PRP complete:**

- [ ] Pytest coverage: 80%+
- [ ] Data quality: 90%+ phone or email
- [ ] Deduplication: <2% duplicates
- [ ] Expected record count: 90%+ achieved
- [ ] SQLite database: Integrity check passes
- [ ] Supabase push: Successful
- [ ] sales-agent integration: Verified
- [ ] Dashboard: Synced
- [ ] CLAUDE.md: Updated
- [ ] TASK.md: Cleared of completed tasks

---

## Data Quality Targets

**Phone Coverage**: [X%] (e.g., 95%+ for Carrier, 0% for Trane)
**Email Coverage**: [Y%] (e.g., 77% for Schneider Electric, <1% for most OEMs)
**Expected Records**: [Z] contractors
**Duplicate Rate**: <2%

**Known Limitations**:
- [Document any known issues, e.g., "Trane phone is 866 call center, not dealer"]

---

## Rollback Plan

**If issues occur post-deployment:**

1. **SQLite Rollback:**
   ```bash
   ls -la output/_failsafe_archive/
   cp output/_failsafe_archive/[timestamp]/pipeline.db output/pipeline.db
   ```

2. **Supabase Rollback:**
   - Use Supabase dashboard to delete records:
   - `DELETE FROM dim_companies WHERE source_type = 'dealer_scraper' AND created_at > '[timestamp]'`

3. **Code Rollback:**
   ```bash
   git revert [commit-hash]
   git push origin main
   ```

4. **Dashboard Rollback:**
   ```bash
   python scripts/sync_dashboard_data.py --force
   ```

---

## Files Changed

**Created:**
- `scrapers/[oem]_scraper.py` - New scraper
- `tests/test_[oem]_scraper.py` - Tests
- `output/oem_data/[oem]_dealers.json` - Scraped data

**Modified:**
- `scrapers/scraper_factory.py` - Register scraper
- `scripts/run_oem_scraper.py` - Add CLI option
- `CLAUDE.md` - Update OEM status table
- `dashboard/public/data/dashboard_data.json` - Auto-synced
- `TASK.md` - Task completion tracking

---

## Testing Plan

**Unit Tests** (`tests/test_[oem]_scraper.py`):
```python
def test_scraper_returns_standardized_dealers():
    scraper = OEMScraper()
    dealers = scraper.scrape(limit=5)
    assert len(dealers) > 0
    assert all(d.company_name for d in dealers)
    assert all(d.state for d in dealers)

def test_scraper_excludes_toll_free_numbers():
    scraper = OEMScraper()
    dealers = scraper.scrape(limit=100)
    phones = [d.primary_phone for d in dealers if d.primary_phone]
    assert not any(p.startswith('800') for p in phones)
    assert not any(p.startswith('888') for p in phones)
```

**Integration Tests**:
```bash
# End-to-end flow
python scripts/run_oem_scraper.py --oem [name] --mode browserbase --limit 10
python scripts/migrate_oem_to_sqlite.py --oem [name]
python scripts/export_for_sales_agent.py --limit 10
```

---

## Notes

[Any additional context, decisions made, or future considerations]

**Example**:
- Trane scraper needs detail page enrichment (Phase 2)
- Kohler extraction validated, needs production run
- Generac PLAYWRIGHT mode fixed (was printing manual instructions)

---

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Last Updated**: YYYY-MM-DD
