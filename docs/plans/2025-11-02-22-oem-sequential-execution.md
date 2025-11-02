# 22-OEM Sequential Execution System

**Date:** November 2, 2025
**Scope:** Scrape all 22 OEM networks with checkpoint saving and full validation
**Target:** 264 unique ZIP codes (140 SREC + 179 nationwide wealthy)
**Duration:** 13 hours (conservative estimate)

---

## Executive Summary

This system scrapes 22 OEM dealer locators sequentially, one at a time, with human confirmation before each OEM. The script saves checkpoints every 25 ZIP codes, runs full deduplication with fuzzy name matching after each OEM, and stops immediately on errors for manual recovery.

**Key Features:**
- Fresh start per OEM (deletes existing checkpoints)
- Interactive confirmation: "Ready to run [OEM]? (y/n/skip)"
- Checkpoint saves every 25 ZIPs for reliability
- Full validation: deduplication + fuzzy matching + quality metrics
- Fail-fast error handling with user decision prompts

---

## Architecture

### Sequential Master Script

The system runs as a linear state machine. Each OEM follows this flow:

```
1. Delete checkpoints (fresh start)
   ↓
2. Prompt user: "Ready to run [OEM]? (y/n/skip)"
   ↓
3. Scrape 264 ZIPs (checkpoint every 25)
   ↓
4. Run deduplication pipeline (phone → domain → fuzzy name)
   ↓
5. Generate outputs (.json, .csv, .log, dedup report)
   ↓
6. Display validation results
   ↓
7. Continue to next OEM
```

**Error Handling:**
On any scraping error, the script stops immediately, displays the full traceback, and prompts:
```
Options:
1. Skip this OEM and continue
2. Retry this ZIP code once
3. Exit script (manual debugging)
Choose (1/2/3):
```

---

## OEM Priority Order

### Tier 1: HVAC Systems (6 OEMs) - 3.5 hours
1. Carrier (HVAC) - ~2,600 contractors
2. Trane (HVAC) - ~2,800 contractors
3. Lennox (HVAC) - ~2,000 contractors
4. York (HVAC) - ~1,000 contractors
5. Rheem (HVAC/Water Heating) - ~1,500 contractors
6. Mitsubishi (VRF/HVAC) - ~1,800 contractors

### Tier 2: Backup Generators (4 OEMs) - 2.5 hours
7. Generac (Generators) - ~1,600 contractors
8. Kohler (Generators) - ~800 contractors
9. Cummins (Generators) - ~600 contractors
10. Briggs & Stratton (Generators) - ~700 contractors

### Tier 3: Solar Inverters (10 OEMs) - 6 hours
11. Enphase (Microinverters) - ~100 contractors
12. Fronius (String Inverters) - ~400 contractors
13. SMA (String Inverters) - ~300 contractors
14. Sol-Ark (Hybrid Inverters) - ~200 contractors
15. GoodWe (Inverters) - ~150 contractors
16. Growatt (Inverters) - ~150 contractors
17. Sungrow (Inverters) - ~200 contractors
18. ABB (Inverters) - ~150 contractors
19. Delta (Inverters) - ~100 contractors
20. Tigo (Optimizers) - ~100 contractors

### Tier 4: Battery Storage (2 OEMs) - 1 hour
21. Tesla (Powerwall) - ~70 contractors
22. SimpliPhi (Battery Storage) - ~50 contractors

**Rationale:**
HVAC scrapers run first to front-load maximum contractor volume. Generators follow for resimercial signal detection. Solar and battery OEMs run last (smaller volumes, tolerate late-day execution).

---

## Checkpoint System

### Checkpoint Mechanism
- **Frequency:** Save every 25 ZIP codes (264 ÷ 25 = 11 checkpoints per OEM)
- **Location:** `output/oem_data/{oem_name}/checkpoints/checkpoint_zip_{index}.json`
- **Contents:**
  ```json
  {
    "last_completed_zip": "94102",
    "last_completed_index": 24,
    "dealers_scraped": 156,
    "timestamp": "2025-11-02T14:23:45"
  }
  ```
- **Cleanup:** Delete all checkpoint files before starting each OEM

### Data Flow Per OEM

```
Scrape 264 ZIPs → Save checkpoints every 25
   ↓
{oem}_raw_20251102.json (all dealers, with duplicates)
   ↓
Deduplication pipeline:
  1. Phone normalization (strips to 10 digits)
  2. Domain matching (extracts root domain)
  3. Fuzzy name matching (85% similarity, same state)
   ↓
Outputs:
  - {oem}_deduped_20251102.csv (unique dealers)
  - {oem}_execution_20251102.log (timestamps, errors)
  - {oem}_dedup_report_20251102.txt (dedup stats + fuzzy matches)
```

**File Naming:**
- Raw: `carrier_raw_20251102.json`
- Deduplicated: `carrier_deduped_20251102.csv`
- Log: `carrier_execution_20251102.log`
- Dedup report: `carrier_dedup_report_20251102.txt`

---

## Validation Pipeline

The system runs full analysis after each OEM completes:

### Step 1: Deduplication Analysis
Run multi-signal deduplication and report statistics:
```
Raw dealers scraped: 2,617
After phone dedup: 2,543 (-2.8%)
After domain dedup: 2,538 (-0.2%)
After fuzzy name dedup: 2,536 (-0.08%)
Final unique dealers: 2,536
Total deduplication rate: 3.1%
```

### Step 2: Fuzzy Match Analysis
Display high-confidence fuzzy name matches (≥85% similarity, same state):
```
Fuzzy Matches Found: 12
1. "ABC Heating & Cooling Inc" ↔ "ABC Heating and Cooling" (92%, CA)
2. "Smith HVAC Services LLC" ↔ "Smith HVAC Service" (89%, TX)
```

### Step 3: Quality Metrics
- **Coverage:** ZIPs with results / 264 total (target: >95%)
- **Data completeness:** % of dealers with phone, address, name
- **Geographic distribution:** Dealers per state (detects scraping gaps)
- **Tier distribution:** Premier/Elite vs Standard (OEM quality signal)

---

## User Interaction Flow

### Per-OEM Confirmation
```
================================================================================
OEM 1/22: Carrier (HVAC Systems)
================================================================================
Expected contractors: ~2,600+
Target: 264 ZIP codes (all 50 states)
Output: output/oem_data/carrier/

Ready to run Carrier scraper? (y/n/skip): _
```

**Input Handling:**
- `y` or `yes` → Start scraping
- `n` or `no` → Exit script: "Stopped at user request"
- `skip` or `s` → Log skip, display "⏭️ Skipped Carrier", continue to next OEM
- Invalid → Re-prompt: "Invalid input. Enter y/n/skip:"

### Progress Display
```
  [Carrier] ZIP 1/264 (94102) - 23 dealers found
  [Carrier] ZIP 25/264 (90210) - 18 dealers ✓ Checkpoint saved
  [Carrier] ZIP 50/264 (92101) - 31 dealers ✓ Checkpoint saved
  ...
  [Carrier] ZIP 264/264 (99516) - 12 dealers ✓ Complete

  ✅ Carrier scraping complete: 2,617 dealers from 264 ZIPs
```

### Validation Display
```
  → Running deduplication pipeline...
     - Phone dedup: 2,617 → 2,543 (-2.8%)
     - Domain dedup: 2,543 → 2,538 (-0.2%)
     - Fuzzy name dedup: 2,538 → 2,536 (-0.08%)

  → Fuzzy matches found: 12 pairs

  → Quality metrics:
     - ZIP coverage: 262/264 (99.2%)
     - Data completeness: 98.7% (phone), 99.1% (address), 100% (name)
     - Geographic spread: CA (342), TX (298), PA (187)...

  ✅ Validation complete

  📁 Files generated:
     - carrier_raw_20251102.json (2,617 dealers)
     - carrier_deduped_20251102.csv (2,536 unique)
     - carrier_execution_20251102.log
     - carrier_dedup_report_20251102.txt
```

### Final Summary
```
================================================================================
ALL OEM SCRAPING COMPLETE
================================================================================
Duration: 12h 47m
OEMs completed: 20/22
OEMs skipped: 2 (SMA, Tigo)
Total unique contractors: 18,456
Total raw records: 21,892 (dedup rate: 15.7%)

Next steps:
1. Run multi-OEM cross-reference: python3 scripts/analyze_multi_oem_crossovers.py
2. Generate grandmaster list: python3 scripts/create_grandmaster_list.py
3. Run ICP scoring: python3 scripts/apply_icp_scoring.py
```

---

## Error Handling

### Scraping Errors (during ZIP iteration)
The script catches exceptions, logs the full traceback, and displays:
```
❌ Error scraping ZIP 94102 for Carrier: ConnectionTimeout
```

Then prompts:
```
Options:
1. Skip this OEM and continue to next
2. Retry this ZIP code once
3. Exit script (manual debugging needed)
Choose (1/2/3):
```

### Validation Errors (during dedup/analysis)
Non-fatal warnings logged, best-effort dedup continues:
```
Warning: Fuzzy matching library unavailable, skipping fuzzy dedup
```

### File I/O Errors
Fatal errors stop the script immediately:
```
Cannot write to output/oem_data/carrier/ - check permissions
```

---

## Implementation Requirements

### Prerequisites
1. Merge `feature/oem-checkpoint-production-run` branch (checkpoint functionality)
2. Verify `ALL_ZIP_CODES` in config.py (264 unique ZIPs)
3. Ensure all 22 OEM scrapers implement `scrape_multiple()` method

### Master Script: `scripts/run_22_oem_sequential.py`

**Responsibilities:**
- Delete existing checkpoints per OEM (fresh start policy)
- Prompt user for y/n/skip confirmation
- Call `scraper.scrape_multiple(ALL_ZIP_CODES, checkpoint_interval=25)`
- Run deduplication pipeline with fuzzy matching
- Generate all output files (.json, .csv, .log, report)
- Display validation results
- Handle errors with user prompts

**Configuration:**
- OEM priority order (hardcoded list in script)
- Checkpoint interval: 25 ZIPs
- Fuzzy match threshold: 85% similarity
- Target ZIP list: `ALL_ZIP_CODES` from config.py

---

## Success Criteria

**Per-OEM:**
- ✅ 264 ZIPs scraped (100% coverage)
- ✅ Checkpoints saved every 25 ZIPs
- ✅ Deduplication rate: 2-20% (depends on OEM)
- ✅ ZIP coverage: >95% (246+ ZIPs with results)
- ✅ Data completeness: >95% for phone, address, name
- ✅ All output files generated (.json, .csv, .log, report)

**Overall:**
- ✅ All 22 OEMs scraped (or explicitly skipped by user)
- ✅ No silent failures (all errors logged and handled)
- ✅ Total unique contractors: 15,000-20,000 (estimated)
- ✅ Ready for multi-OEM cross-reference analysis

---

## Timeline

**Estimated Duration:** 13 hours (conservative)
- Tier 1 HVAC: 3.5 hours (6 OEMs)
- Tier 2 Generators: 2.5 hours (4 OEMs)
- Tier 3 Solar: 6 hours (10 OEMs)
- Tier 4 Battery: 1 hour (2 OEMs)

**Per-OEM Breakdown:**
- Scraping: 25 minutes (264 ZIPs × ~5-6 seconds)
- Validation: 3 minutes (dedup + fuzzy + stats)
- User interaction: 2 minutes (confirmation + review)
- **Total:** ~30 minutes per OEM × 22 = 11 hours + 2 hours buffer

**Start time:** Flexible (user confirms each OEM)
**End time:** Same day (full day available)
