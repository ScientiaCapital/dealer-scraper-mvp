# Complete All 18 OEM Scrapers - Execution Plan

**Date:** November 1, 2025
**Goal:** Complete extraction scripts and validation tests for remaining 12 OEMs
**Approach:** Sequential deep-dive (one OEM fully complete before next)
**Timeline:** 9.5 hours (30 min audit + 9 hours implementation)

---

## Executive Summary

We will complete the remaining 12 OEM scrapers using a sequential deep-dive approach. Each OEM receives full attention: DOM inspection → extraction script → test script → validation → commit. Quality over speed. Business value determines priority order.

**Current Status:** 6/18 complete (Tesla, Enphase, Generac, Cummins, Kohler, Fronius)
**Remaining:** 12 OEMs need scripts + validation
**Success Criteria:** 18/18 OEMs production-ready with extraction.js + test script + passing validation

---

## Phase 1: Audit Current State (30 min)

Before writing any code, audit all 12 remaining OEMs to avoid duplication.

### Audit Scope

**Check in order:**
1. Feature branch (`feature/complete-all-18-oem-scrapers`) - extraction.js + test scripts
2. Main branch - extraction.js scripts that may exist
3. Production data (`output/oem_data/*/`) - existing CSV files
4. Test scripts directory (`scripts/test_*.py`)

### Classification System

For each OEM:
- ✅ **Complete**: Has extraction.js + test script + passing validation → Skip
- 🟨 **Partial**: Has extraction.js, needs test script → Add test only
- 🟥 **Missing**: Needs full implementation → Build from scratch

### 12 OEMs to Audit (Business Value Order)

1. **SolarEdge** - Major inverter brand (likely 2,000-3,000 contractors)
2. **Lennox** - HVAC (resimercial signal, MEP+R overlap)
3. **SimpliPhi** - Battery storage (pure storage focus)
4. **Briggs & Stratton** - Generator (completes generator coverage)
5. **Carrier** - HVAC (large network)
6. **York** - HVAC (resimercial signal)
7. **Mitsubishi** - HVAC/VRF (commercial focus)
8. **Trane** - HVAC (premium brand)
9. **Rheem** - HVAC (large network)
10. **SMA** - Solar inverter (major brand)
11. **Sol-Ark** - Hybrid inverter+storage
12. **GoodWe/Growatt** - Chinese inverters (may lack viable locators)

### Audit Output

Document exact status for each OEM:
- Extraction script status (exists/missing)
- Test script status (exists/missing)
- Production data status (has CSV/missing)
- Action required (skip/test only/full build)

---

## Phase 2: Per-OEM Workflow (40-50 min each)

Execute in priority order. Complete one OEM before starting next.

### Step 1: Pre-Flight Check (2 min)

- Verify dealer locator URL exists and is accessible
- Check for cookie/GDPR acceptance requirements
- Identify search mechanism (ZIP input vs. dropdown vs. map)

### Step 2: DOM Inspection with Playwright MCP (10-15 min)

**Tools:** browser_navigate, browser_snapshot, browser_type, browser_click

**Process:**
1. Navigate to dealer locator
2. Take snapshot (see initial page structure)
3. Type ZIP code into search field
4. Click search button
5. Wait 3-5 seconds for AJAX results
6. Take snapshot (see results structure)

**Analyze:**
- Result containers (cards, list items, table rows)
- Data selectors (name, phone, address, website, rating)
- Pagination vs. infinite scroll
- AJAX delays

### Step 3: Write extraction.js (20-30 min)

**Location:** `scrapers/{oem}/extraction.js`

**Reference patterns from:**
- `scrapers/generac/extraction.js` - Table-based extraction
- `scrapers/tesla/extraction.js` - Card-based extraction
- `scrapers/enphase/extraction.js` - List-based extraction

**Requirements:**
- Extract all StandardizedDealer fields (name, phone, address, website, rating, etc.)
- Handle missing fields gracefully (don't crash on nulls)
- Deduplicate by phone within same ZIP
- Return array of dealer objects
- Include error handling for edge cases

### Step 4: Write test_{oem}.py (10 min)

**Location:** `scripts/test_{oem}.py`

**Test with 3 diverse ZIP codes:**
- 94102 (San Francisco - urban, dense market)
- 78701 (Austin - suburban, moderate market)
- 19103 (Philadelphia - mixed, testing diversity)

**Validation thresholds:**
- Dealers extracted: ≥5 per ZIP (unless sparse market)
- Missing names: 0% (critical field)
- Missing phones: <10% (acceptable, can enrich later)
- Duplicate phones: 0 within same ZIP
- Execution time: <2 minutes per ZIP

### Step 5: Run Test & Debug (10-20 min)

**Execute:** `python3 scripts/test_{oem}.py`

**If test fails:**
1. Re-inspect DOM with browser_snapshot
2. Fix selectors in extraction.js
3. Retest same 3 ZIPs
4. Continue until passing

**If bot detection:**
1. Switch to Browserbase mode immediately
2. Update scraper: `ScraperFactory.create("OEM", mode=ScraperMode.BROWSERBASE)`
3. Retry test

**Recovery rule:** Never spend >15 minutes stuck on one OEM
- First 5 min: Debug locally
- Next 5 min: Try Browserbase
- Still failing: Document issue, skip, move to next

### Step 6: Commit (2 min)

**Commit message format:**
```
feat: {OEM} scraper - PRODUCTION READY ✅
```

**Files to include:**
- `scrapers/{oem}/extraction.js`
- `scripts/test_{oem}.py`

**No unrelated changes in commit**

### Step 7: Update Progress & Move Next

- Mark OEM complete in todo list
- Note actual time vs. estimate
- Start Step 1 for next OEM in priority order

---

## Error Handling & Recovery

### Bot Detection / Captcha

**Symptom:** Access denied, captcha page, "automated traffic detected"

**Solution:**
1. Switch to Browserbase mode immediately
2. Add 3-5 second delays between actions
3. If still failing, skip and revisit later

### Empty Results (0 dealers extracted)

**Symptom:** Extraction returns empty array despite visible dealers

**Causes:**
- Wrong selector
- AJAX not complete
- JavaScript framework (React/Angular/Vue)
- Shadow DOM or iframe

**Solution:**
1. Wait longer (5-10 seconds) for AJAX
2. Re-inspect with browser_snapshot
3. Check shadow DOM or iframe
4. Try alternative selectors (CSS vs. XPath)
5. Look for dynamic class names or data-* attributes

### Malformed Data (50%+ missing critical fields)

**Symptom:** Phone numbers, names, or addresses missing on most dealers

**Causes:**
- Incorrect selector
- Data in non-standard location
- Opt-in display

**Solution:**
1. Re-inspect DOM for each problematic field
2. Check alternative locations (data attributes, hidden spans, tooltips)
3. Accept partial data if name + location present (phone can be enriched later)

### Timeout Errors

**Symptom:** Page load timeout after 30 seconds

**Solution:**
1. Increase timeout to 60 seconds
2. Switch to Browserbase (better infrastructure)
3. If persistent, skip and revisit

### No Dealer Locator Exists

**Symptom:** OEM website has no ZIP-searchable dealer finder

**Examples:** GoodWe, Growatt may have static lists or contact forms only

**Solution:**
1. Document in commit: "No ZIP-searchable locator available"
2. Unregister from ScraperFactory
3. Update CLAUDE.md to reflect unavailable status
4. **Don't block progress** - move to next OEM

---

## Quality Gates (Must Pass Before Next OEM)

### Gate 1: Extraction Script Exists
- ✅ File: `scrapers/{oem}/extraction.js` committed
- ✅ Contains: `extractDealers()` function
- ✅ Returns: StandardizedDealer array
- ✅ Handles: Missing fields gracefully (no crashes on nulls)

### Gate 2: Test Script Exists & Runs
- ✅ File: `scripts/test_{oem}.py` committed
- ✅ Tests: 3 diverse ZIP codes
- ✅ Executes: Without Python errors or exceptions

### Gate 3: Data Quality Validation
- ✅ Dealers extracted: ≥5 per ZIP (or justified if sparse)
- ✅ Missing names: 0% (critical field)
- ✅ Missing phones: <10% (acceptable)
- ✅ Duplicate phones: 0 within same ZIP
- ✅ Execution time: <2 minutes per ZIP

### Gate 4: Commit Quality
- ✅ Message: `feat: {OEM} scraper - PRODUCTION READY ✅`
- ✅ Files: extraction.js + test script
- ✅ Clean: No unrelated changes

**If any gate fails:** Debug and fix before proceeding to next OEM.

---

## Progress Tracking

### Milestones

- **25% (3/12)**: Validate momentum, adjust time estimates
- **50% (6/12)**: Mid-point check, reassess timeline
- **75% (9/12)**: Final push, defer only truly problematic OEMs
- **100% (12/12)**: Final validation, ready for merge

### Live Tracker (Updated via TodoWrite)

```
OEM Scraper Completion:
[ ] 1. SolarEdge (Major inverter) - Est: 50 min
[ ] 2. Lennox (HVAC) - Est: 45 min
[ ] 3. SimpliPhi (Battery) - Est: 45 min
[ ] 4. Briggs & Stratton (Generator) - Est: 40 min
[ ] 5. Carrier (HVAC) - Est: 40 min
[ ] 6. York (HVAC) - Est: 40 min
[ ] 7. Mitsubishi (VRF/HVAC) - Est: 45 min
[ ] 8. Trane (HVAC) - Est: 40 min
[ ] 9. Rheem (HVAC) - Est: 40 min
[ ] 10. SMA (Inverter) - Est: 40 min
[ ] 11. Sol-Ark (Hybrid) - Est: 45 min
[ ] 12. GoodWe/Growatt (Research) - Est: 30 min
```

---

## Success Criteria

### Definition of "Production Ready"

An OEM scraper is production-ready when ALL criteria met:

1. ✅ Extraction script exists: `scrapers/{oem}/extraction.js`
2. ✅ Test script exists: `scripts/test_{oem}.py`
3. ✅ Tests pass: All 3 ZIPs extract dealers with acceptable quality
4. ✅ Committed: Both files in `feature/complete-all-18-oem-scrapers`
5. ✅ Documented: If no locator, reason documented and unregistered

### End-of-Day Success Criteria

- **Primary Goal**: 18/18 OEMs production-ready
- **Acceptable**: 16-17/18 (if GoodWe/Growatt have no viable locators)
- **Minimum**: 15/18 (6 done + 9 of remaining 12)

### Branch Readiness Check

Before declaring success:
1. All 18 extraction scripts exist (or documented why not)
2. All 18 test scripts exist (or documented why not)
3. All test scripts pass when run
4. Feature branch clean (no uncommitted changes)
5. All commits have proper messages
6. Ready to merge to main

---

## Timeline Estimate

- **Phase 1 (Audit):** 30 minutes
- **Phase 2 (12 OEMs × 45 min avg):** 9 hours
- **Total:** 9.5 hours

**With breaks:** Fits in 10-hour focused day

**Optimization:** As proficiency increases, later OEMs may take 35-40 min instead of 45-50 min

---

## Post-Completion Actions (Tomorrow)

1. **Merge to main**: `git checkout main && git merge feature/complete-all-18-oem-scrapers`
2. **Run full production**: 18 OEMs × 310 ZIPs = 5,580 scrapes (~8-10 hours runtime)
3. **Aggregate data**: Create grandmaster list with phone deduplication
4. **Multi-OEM analysis**: Identify contractors in 2-3+ networks
5. **ICP scoring**: Apply Coperniq algorithm (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)
6. **Update docs**: Reflect actual completion status in CLAUDE.md

---

## Tools & Resources

**Browser Automation:**
- Primary: Playwright MCP (local browser)
- Fallback: Browserbase (cloud browser with stealth)

**Reference Scrapers:**
- Generac: Table-based extraction
- Tesla: Card-based extraction
- Enphase: List-based extraction

**Test Pattern:**
- 3 diverse ZIPs: 94102 (SF), 78701 (Austin), 19103 (Philly)
- Validates: urban, suburban, smaller market coverage

---

**Ready to execute.**
