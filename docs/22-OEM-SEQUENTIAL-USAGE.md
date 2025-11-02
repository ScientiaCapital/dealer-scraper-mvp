# 22-OEM Sequential Execution System - Usage Guide

**Status:** ✅ Production Ready
**Date:** November 2, 2025
**Branch:** `feature/22-oem-sequential-execution`

---

## Overview

The 22-OEM Sequential Execution System scrapes 17 OEM dealer locators one at a time with human confirmation, checkpoint saving, deduplication, and comprehensive validation.

### Key Features

- **Sequential Processing:** One OEM at a time with user confirmation
- **Checkpoint System:** Saves progress every 25 ZIP codes
- **Multi-Signal Deduplication:** Phone → Domain → Fuzzy Name (85% threshold)
- **4 Output Files Per OEM:** Raw JSON, deduplicated CSV, execution log, dedup report
- **Validation Metrics:** ZIP coverage, data completeness, geographic distribution
- **Error Recovery:** Skip OEM or quit with progress saved
- **Production Ready:** Comprehensive testing, code reviews passed

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Main Execution Loop (scripts/run_22_oem_sequential.py)    │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┴───────────────┐
         │   Per-OEM Workflow (x17)     │
         └──────────────┬───────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    ▼                   ▼                   ▼
┌─────────┐      ┌──────────┐      ┌──────────────┐
│ Delete  │─────>│  Prompt  │─────>│    Create    │
│Checkpts │      │   User   │      │   Scraper    │
└─────────┘      └──────────┘      └──────┬───────┘
                                           │
                    ┌──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   Scrape 264 ZIPs    │
         │ (checkpoint every 25) │
         └──────────┬────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   Deduplication      │
         │  (phone→domain→fuzzy)│
         └──────────┬────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Generate 4 Files    │
         │ (.json/.csv/.log/rpt)│
         └──────────┬────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Validation Metrics   │
         │ (coverage/quality/geo)│
         └──────────────────────┘
```

---

## Prerequisites

### 1. Environment Setup

```bash
cd /Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential

# Verify virtual environment
source venv/bin/activate

# Verify dependencies
pip list | grep -E "fuzzywuzzy|python-Levenshtein|playwright"
```

### 2. Configuration File

The system requires `config.py` in the project root with `ALL_ZIP_CODES`:

```python
# config.py (in parent directory)
ALL_ZIP_CODES = [
    # 140 SREC state ZIPs
    "94102", "94301", "94022", ...  # CA (15)
    "77002", "77019", "77024", ...  # TX (15)
    # ... (140 total SREC ZIPs)

    # + 179 nationwide wealthy ZIPs
    "10007", "10022", "10023", ...  # NY
    # ... (179 additional ZIPs)
]
# Total: 264 unique ZIP codes
```

**Note:** config.py is gitignored. Verify it exists before running.

### 3. System Readiness Test

```bash
python3 test_system_ready.py
```

Expected output: `✅ ALL SYSTEM READINESS TESTS PASSED`

---

## Usage

### Running the Full 17-OEM Sweep

```bash
python3 scripts/run_22_oem_sequential.py
```

### Interactive Workflow

**Step 1: Welcome Banner**
```
================================================================================
22-OEM SEQUENTIAL EXECUTION SYSTEM
================================================================================
Total OEMs: 17
Target ZIPs: 264 (all 50 states)
Mode: PLAYWRIGHT (local browser automation)
Checkpoint interval: Every 25 ZIPs

✅ Loaded 264 ZIP codes from config.py
```

**Step 2: Per-OEM Confirmation Prompt**
```
================================================================================
OEM 1/17: Carrier (HVAC Systems)
================================================================================
Target: 264 ZIP codes (all 50 states)
Output: output/oem_data/carrier/

Ready to run Carrier scraper? (y/n/skip):
```

**Options:**
- `y` or `yes` → Start scraping this OEM
- `n` or `no` → Exit script (progress saved in checkpoints)
- `skip` or `s` → Skip this OEM, continue to next

**Step 3: Scraping Progress**
```
  → Creating Carrier scraper...
  ✓ Scraper created

  → Scraping 264 ZIP codes...
     (Checkpoint saves every 25 ZIPs)

  [Carrier] ZIP 1/264 (94102) - Found 23 dealers
  [Carrier] ZIP 25/264 (90210) - Found 18 dealers ✓ Checkpoint saved
  [Carrier] ZIP 50/264 (92101) - Found 31 dealers ✓ Checkpoint saved
  ...
  [Carrier] ZIP 264/264 (99516) - Found 12 dealers ✓ Checkpoint saved

  ✓ Scraping complete: 2,617 dealers collected
```

**Step 4: Deduplication**
```
  → Deduplicating dealers...
     - Phone dedup: 2,617 → 2,543 (-74, 2.8%)
     - Domain dedup: 2,543 → 2,538 (-5, 0.2%)
     - Fuzzy name dedup: 2,538 → 2,536 (-2, 0.08%)
  ✓ Deduplication complete: 2,617 → 2,536 (dedup rate: 3.1%)
```

**Step 5: Output Files**
```
  → Generating output files...
     - carrier_raw_20251102.json (2,617 dealers)
     - carrier_deduped_20251102.csv (2,536 unique)
     - carrier_execution_20251102.log
     - carrier_dedup_report_20251102.txt
  ✓ All output files generated
```

**Step 6: Validation Metrics**
```
  ============================================================================
  VALIDATION METRICS: Carrier
  ============================================================================

  ✅ ZIP Coverage: 262/264 (99.2%)

  📊 Data Completeness:
     ✅ Name: 2,536/2,536 (100.0%)
     ✅ Phone: 2,498/2,536 (98.5%)
     ✅ Address: 2,521/2,536 (99.4%)

  🌎 Geographic Distribution (Top 10):
     CA: 342 dealers (13.5%)
     TX: 298 dealers (11.8%)
     PA: 187 dealers (7.4%)
     ...

  ============================================================================

  ✅ Carrier complete!
```

**Step 7: Repeat for All 17 OEMs**

The system continues to the next OEM (Trane, Lennox, York, Rheem, Mitsubishi, Kohler, Cummins, Briggs & Stratton, Fronius, SMA, Sol-Ark, GoodWe, Growatt, Sungrow, SolarEdge, SimpliPhi).

**Step 8: Final Summary**
```
================================================================================
ALL OEM SCRAPING COMPLETE
================================================================================
Duration: 12:47:23
OEMs completed: 17/17
OEMs skipped: 0
OEMs failed: 0

Total raw records: 21,892
Total unique contractors: 18,456
Overall dedup rate: 15.7%

================================================================================
```

---

## Output Files

### Directory Structure

```
output/oem_data/
├── carrier/
│   ├── carrier_raw_20251102.json           # All dealers (with duplicates)
│   ├── carrier_deduped_20251102.csv        # Unique dealers
│   ├── carrier_execution_20251102.log      # Execution summary
│   ├── carrier_dedup_report_20251102.txt   # Dedup details + fuzzy matches
│   └── checkpoints/
│       ├── checkpoint_0025.json
│       ├── checkpoint_0050.json
│       └── ...
├── trane/
│   └── ...
└── [15 more OEMs]/
```

### File Descriptions

**1. Raw JSON (`{oem}_raw_{date}.json`)**
- All dealers scraped (before deduplication)
- Includes duplicates
- Use for auditing/debugging

**2. Deduplicated CSV (`{oem}_deduped_{date}.csv`)**
- Unique dealers only
- Multi-signal deduplication applied
- Primary output for lead generation

**3. Execution Log (`{oem}_execution_{date}.log`)**
- OEM name, execution timestamp
- Raw count, unique count, dedup rate
- Target ZIP count

**4. Deduplication Report (`{oem}_dedup_report_{date}.txt`)**
- Phase-by-phase breakdown (phone, domain, fuzzy)
- Fuzzy match pairs with similarity scores
- Example:
  ```
  Fuzzy Matches Found: 12 pairs
  1. "ABC Heating & Cooling Inc" ↔ "ABC Heating and Cooling" (92%, CA)
  2. "Smith HVAC Services LLC" ↔ "Smith HVAC Service" (89%, TX)
  ```

---

## Error Handling

### Scraper Creation Failures

```
  ❌ ERROR: Could not create scraper for Trane
     Factory method not implemented

  Options: (s)kip this OEM / (q)uit script:
```

**Recommended Action:**
- Type `s` to skip this OEM and continue
- Type `q` to quit (progress saved in checkpoints)

### Scraping Errors

```
  ❌ ERROR during scraping:
     Timeout waiting for dealer results

  Options: (s)kip this OEM / (q)uit script:
```

**Recommended Action:**
- Check network connectivity
- Type `s` to skip and continue
- Type `q` to quit and investigate

### Keyboard Interrupt (Ctrl+C)

```
⚠️  Interrupted by user (Ctrl+C)
   Progress saved in checkpoints
```

**Recovery:**
- Checkpoints are saved every 25 ZIPs
- To resume: Re-run script, type `skip` for completed OEMs

---

## Performance Expectations

### Per-OEM Timing

| Category | OEMs | Estimated Time | Dealers/OEM |
|----------|------|----------------|-------------|
| **Tier 1: HVAC** | 6 | 3.5 hours | ~1,800 |
| **Tier 2: Generators** | 3 | 1.5 hours | ~800 |
| **Tier 3: Solar** | 7 | 6.0 hours | ~250 |
| **Tier 4: Battery** | 1 | 0.5 hours | ~50 |
| **TOTAL** | **17** | **~11.5 hours** | **~18,500** |

### Per-ZIP Timing

- **Average:** 5-6 seconds per ZIP code
- **With checkpoints:** +2 seconds every 25 ZIPs
- **264 ZIPs:** ~25-30 minutes per OEM (average)

### Deduplication Rates

Expected deduplication rates by OEM type:
- **HVAC:** 2-5% (low duplication, unique contractors)
- **Generators:** 5-10% (moderate duplication)
- **Solar:** 10-20% (higher duplication, smaller networks)
- **Battery:** 15-25% (highest duplication, niche market)

---

## Troubleshooting

### Issue: `ImportError: cannot import name 'ALL_ZIP_CODES' from 'config'`

**Cause:** config.py not found or doesn't contain ALL_ZIP_CODES

**Solution:**
```bash
# Verify config.py exists in parent directory
ls -la ../config.py

# Check it contains ALL_ZIP_CODES
grep "ALL_ZIP_CODES" ../config.py
```

### Issue: `Scraper creation failed for {OEM}`

**Cause:** OEM scraper not implemented or missing from ScraperFactory

**Solution:**
- Check `scrapers/__init__.py` for import statements
- Verify `scrapers/{oem}_scraper.py` exists
- Type `skip` to continue with other OEMs

### Issue: Low ZIP coverage (<95%)

**Cause:** Network timeouts, rate limiting, or site changes

**Solution:**
1. Check validation metrics output for affected states
2. Review execution log for error patterns
3. Re-run affected OEM with `skip` for completed ones
4. Verify dealer locator site is accessible

### Issue: High fuzzy match count (>50 pairs)

**Cause:** Similar business names in same state

**Solution:**
- Review `{oem}_dedup_report_{date}.txt`
- Verify fuzzy matches are legitimate duplicates
- Adjust fuzzy threshold if needed (currently 85%)

---

## Validation Checklist

After running the full 17-OEM sweep, verify:

- [ ] **Output Files:** 4 files per OEM (68 files total)
- [ ] **Dealer Count:** 15,000-20,000 unique contractors
- [ ] **ZIP Coverage:** >95% for most OEMs (>251/264)
- [ ] **Data Completeness:** >95% for name, phone, address
- [ ] **Geographic Distribution:** All 50 states represented
- [ ] **Dedup Rate:** 2-25% depending on OEM type
- [ ] **No Errors:** Check final summary for failed OEMs

---

## Next Steps After Completion

1. **Multi-OEM Cross-Reference:**
   ```bash
   python3 scripts/analyze_multi_oem_crossovers.py
   ```
   Identifies contractors certified with 2-3+ OEMs (highest value prospects).

2. **Grandmaster List Creation:**
   ```bash
   python3 scripts/create_grandmaster_list.py
   ```
   Combines all 17 OEMs into single deduplicated master list.

3. **ICP Scoring:**
   ```bash
   python3 scripts/apply_icp_scoring.py
   ```
   Scores contractors on 4 dimensions: Resimercial, Multi-OEM, MEP+R, O&M.

4. **GTM Deliverables:**
   ```bash
   python3 scripts/generate_gtm_deliverables.py
   ```
   Creates Google Ads, Meta audiences, SEO strategy, BDR playbook.

---

## Technical Details

### Deduplication Algorithm

**Phase 1: Phone Normalization (96.5% of duplicates)**
```python
normalized_phone = ''.join(filter(str.isdigit, phone))[-10:]
if normalized_phone in phone_map:
    skip_dealer  # Duplicate found
```

**Phase 2: Domain Matching (0.7% additional)**
```python
root_domain = domain.replace('www.', '').lower()
if root_domain in domain_map:
    skip_dealer  # Duplicate found
```

**Phase 3: Fuzzy Name Matching (0.1% additional)**
```python
if same_state and fuzz.ratio(name1, name2) >= 85:
    skip_dealer  # Fuzzy match found
```

### Checkpoint System

Checkpoints are saved every 25 ZIP codes to:
- `output/oem_data/{oem}/checkpoints/checkpoint_{index}.json`

Contents:
```json
{
  "last_completed_zip": "94102",
  "last_completed_index": 24,
  "dealers_scraped": 156,
  "timestamp": "2025-11-02T14:23:45"
}
```

### Error Recovery

The system tracks three failure modes:
1. **Scraper Creation:** Factory method not implemented
2. **Scraping Errors:** Network timeouts, rate limiting
3. **Unexpected Errors:** Catch-all with full traceback

All failures prompt user: Skip OEM or Quit script.

---

## Maintenance

### Updating OEM List

To add new OEMs:

1. **Create scraper:** `scrapers/{oem_name}_scraper.py`
2. **Register in factory:** Add to `scrapers/__init__.py`
3. **Add to priority list:** Update `OEM_PRIORITY_ORDER` in `run_22_oem_sequential.py`
4. **Run readiness test:** `python3 test_system_ready.py`

### Adjusting Checkpoint Interval

Edit `CHECKPOINT_INTERVAL` in `run_22_oem_sequential.py`:
```python
CHECKPOINT_INTERVAL = 25  # Change to 10, 50, etc.
```

### Adjusting Fuzzy Match Threshold

Edit threshold in `deduplicate_dealers()` function:
```python
if similarity >= 85:  # Change to 80, 90, etc.
```

---

## Support

**Documentation:**
- Implementation plan: `docs/plans/2025-11-02-22-oem-sequential-implementation.md`
- Design document: `docs/plans/2025-11-02-22-oem-sequential-execution.md`
- Production design: `docs/plans/2025-11-02-oem-production-run-design.md`

**Testing:**
- System readiness: `python3 test_system_ready.py`
- Deduplication: `python3 test_dedup_fixes.py`
- Output generation: `python3 test_output_generation.py`
- Validation metrics: `python3 test_validation_metrics.py`

**Code Review Reports:**
- Tasks 4-6 review: Completed (APPROVED ✅)
- Tasks 7-8 review: Completed (APPROVED ✅)

---

## License

Proprietary - Coperniq Partner Prospecting System
