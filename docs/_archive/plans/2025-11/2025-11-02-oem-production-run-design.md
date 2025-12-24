# OEM Production Run Design

**Date:** 2025-11-02
**Scope:** Run all 20 OEM scrapers with checkpoint saving
**Target:** 264 unique ZIP codes across all 50 US states

## Overview

This design implements checkpoint-based scraping for 20 OEM dealer locators. The system saves progress every 25 ZIP codes, generates .json and .log files per OEM, and enables semi-automated execution with pause-on-error handling.

## Requirements

**Functional:**
- Run 20 OEMs (9 with existing data + 11 new)
- Use ALL_ZIP_CODES (264 deduplicated ZIPs: 140 SREC + 179 nationwide wealthy)
- Save checkpoints every 25 ZIP codes
- Generate .json and .log files for each OEM
- Pause and alert user on any error
- Semi-automated: confirm before each OEM starts
- Prioritize high-value OEMs first (HVAC → Generators → Solar → Battery)

**Non-Functional:**
- Total runtime: 7-9 hours (264 zips × 20 OEMs = 5,280 operations at ~5-6 sec/zip)
- Checkpoint interval: 25 ZIPs
- Error recovery: Resume from last checkpoint

## Architecture

### Two-Layer Design

**Layer 1: Enhanced Base Scraper** (`scrapers/base_scraper.py`)
- Modify `scrape_multiple()` method to save checkpoints
- Add `checkpoint_interval` parameter (default: 25)
- Create .json (dealer data) and .log (progress) files automatically
- Store checkpoints in `output/oem_data/{oem_name}/`

**Layer 2: Master OEM Runner** (`scripts/run_all_oems_production.py`)
- Load ALL_ZIP_CODES (264 unique ZIPs)
- Run OEMs in priority order
- Prompt user before each OEM: "Ready to run {OEM}? (yes/no/skip)"
- Catch errors and pause for user decision
- Display statistics after each OEM completes

### OEM Priority Order

```python
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC (Highest contractor counts)
    "Carrier", "Lennox", "Trane", "Mitsubishi", "York", "Rheem",

    # Tier 2: Generators (Large networks)
    "Generac", "Kohler", "Cummins", "Briggs & Stratton",

    # Tier 3: Solar Inverters (Medium networks)
    "SolarEdge", "Enphase", "SMA", "Fronius", "Sungrow",
    "GoodWe", "Growatt", "Sol-Ark",

    # Tier 4: Battery Storage (Smaller networks)
    "Tesla", "SimpliPhi"
]
```

## Data Management

### Checkpoint File Structure

```
output/oem_data/{oem_name}/
├── {oem_name}_checkpoint_0025.json     # Dealers collected after 25 zips
├── {oem_name}_checkpoint_0025.log      # Progress log
├── {oem_name}_checkpoint_0050.json     # After 50 zips
├── {oem_name}_checkpoint_0050.log
├── ...
├── {oem_name}_checkpoint_0250.json
├── {oem_name}_checkpoint_0250.log
├── {oem_name}_checkpoint_0264.json     # Final checkpoint
├── {oem_name}_checkpoint_0264.log
├── {oem_name}_national_20251102.csv    # Final deduplicated CSV
├── {oem_name}_national_20251102.json   # Final deduplicated JSON
└── {oem_name}_run_20251102.log         # Complete run log
```

### Checkpoint JSON Schema

```json
{
  "oem_name": "Generac",
  "started_at": "2025-11-02T08:15:23",
  "last_updated": "2025-11-02T08:45:12",
  "total_zips": 264,
  "completed_zips": 50,
  "failed_zips": ["90210", "10007"],
  "total_dealers": 587,
  "dealers_after_dedup": 521,
  "checkpoint_number": 50,
  "status": "in_progress"
}
```

### Log File Format

```
[2025-11-02 08:15:23] Starting Generac scraper with 264 ZIP codes
[2025-11-02 08:15:28] [1/264] ZIP 94102: Found 12 dealers
[2025-11-02 08:15:34] [2/264] ZIP 90210: Found 8 dealers
...
[2025-11-02 08:20:15] CHECKPOINT: Saved 25 zips, 287 dealers total
[2025-11-02 08:20:15] Checkpoint saved to: generac_checkpoint_0025.json
```

## Implementation Details

### Enhanced Base Scraper

**File:** `scrapers/base_scraper.py`
**Method:** `scrape_multiple()` (lines 400-424)

**Current signature:**
```python
def scrape_multiple(self, zip_codes: List[str], verbose: bool = True) -> List[StandardizedDealer]:
```

**Enhanced signature:**
```python
def scrape_multiple(
    self,
    zip_codes: List[str],
    verbose: bool = True,
    checkpoint_interval: int = 25,
    checkpoint_dir: Optional[str] = None
) -> List[StandardizedDealer]:
```

**Checkpoint logic:**
```python
for i, zip_code in enumerate(zip_codes, 1):
    # Scrape single ZIP
    dealers = self.scrape_zip_code(zip_code)
    all_dealers.extend(dealers)

    # Save checkpoint every N zips
    if (i % checkpoint_interval == 0) or (i == len(zip_codes)):
        checkpoint_file = f"output/oem_data/{self.OEM_NAME.lower()}/{self.OEM_NAME.lower()}_checkpoint_{i:04d}"
        self.save_json(f"{checkpoint_file}.json")
        self._save_log(f"{checkpoint_file}.log", progress_data)
```

### Master OEM Runner

**File:** `scripts/run_all_oems_production.py`

**Execution flow:**

1. **Pre-run validation:**
   ```python
   from config import ALL_ZIP_CODES
   print(f"Ready to scrape 20 OEMs × {len(ALL_ZIP_CODES)} zips = {20 * len(ALL_ZIP_CODES)} operations")
   ```

2. **Semi-automated loop:**
   ```python
   for oem_name in OEM_PRIORITY_ORDER:
       print(f"\n{'='*60}")
       print(f"Next OEM: {oem_name}")
       print(f"{'='*60}")

       user_input = input("Ready to run? (yes/no/skip): ")

       if user_input.lower() == 'yes':
           run_oem_scraper(oem_name)
       elif user_input.lower() == 'skip':
           continue
       else:
           break  # Exit completely
   ```

3. **Error handling (Pause and Alert):**
   ```python
   try:
       scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)
       scraper.scrape_multiple(ALL_ZIP_CODES, checkpoint_interval=25)
       scraper.deduplicate_by_phone()
       scraper.save_csv(f"output/oem_data/{oem_name.lower()}/{oem_name.lower()}_national_{date}.csv")

   except Exception as e:
       print(f"\n⚠️  ERROR in {oem_name} scraper:")
       print(f"   {str(e)}")
       print(f"\nLast checkpoint saved. Progress preserved.")

       choice = input("\nOptions: (r)etry / (s)kip / (q)uit: ")

       if choice == 'r':
           # Retry same OEM
       elif choice == 's':
           # Skip to next OEM
       else:
           # Quit entire run
   ```

4. **Post-OEM completion:**
   ```python
   print(f"\n✓ {oem_name} complete:")
   print(f"  - {len(dealers)} dealers collected")
   print(f"  - {len(dealers_deduped)} dealers after deduplication")
   print(f"  - Saved to: output/oem_data/{oem_name.lower()}/{oem_name.lower()}_national_{date}.csv")
   ```

## Implementation Timeline

**Step 1: Enhance Base Scraper** (15-20 minutes)
- Modify `scrapers/base_scraper.py`
- Add checkpoint saving to `scrape_multiple()`
- Add logging configuration
- Test with Generac on 30 ZIPs

**Step 2: Create Master Runner** (10-15 minutes)
- Create `scripts/run_all_oems_production.py`
- Implement OEM priority ordering
- Add semi-automated prompts
- Add pause-and-alert error handling

**Step 3: Test Run** (5 minutes)
- Run one complete OEM (SMA or Enphase - smallest)
- Verify checkpoints created every 25 ZIPs
- Verify .json and .log files generated
- Confirm deduplication works

**Step 4: Production Execution** (7-9 hours)
- Run all 20 OEMs sequentially
- User confirms each OEM before starting
- Monitor for errors (pause-and-alert active)
- Review results after each OEM completes

**Total Time:** ~8-9 hours (setup + production run)

## Success Criteria

**Functional:**
- ✓ ALL_ZIP_CODES contains 264 unique ZIPs (deduplicated)
- ✓ Checkpoints saved every 25 ZIPs for all OEMs
- ✓ .json and .log files created for each checkpoint
- ✓ Final CSV generated per OEM with deduplicated data
- ✓ User prompted before each OEM starts
- ✓ Errors pause execution and await user decision

**Quality:**
- ✓ Resume capability: Load last checkpoint and continue
- ✓ Data integrity: Deduplication accuracy maintains 97.3%
- ✓ No data loss: All checkpoints preserved on error
- ✓ Clear logging: Timestamp, ZIP count, dealer count per entry

## Risk Mitigation

**Risk: Scraper timeout/crash**
**Mitigation:** Checkpoints every 25 ZIPs preserve progress. Resume from last checkpoint.

**Risk: Rate limiting/captcha**
**Mitigation:** Pause-and-alert stops execution. User investigates and decides next action.

**Risk: Incorrect data saved**
**Mitigation:** Checkpoints preserve incremental data. User can inspect at any interval.

**Risk: Disk space exhaustion**
**Mitigation:** 20 OEMs × 11 checkpoints × 2 files = ~440 checkpoint files (~200MB total).

## Future Enhancements

1. **Automatic resume:** Detect incomplete runs and prompt user to resume
2. **Parallel execution:** Run multiple OEMs simultaneously (requires resource management)
3. **Cloud deployment:** RunPod mode for faster execution (currently infrastructure ready)
4. **Real-time dashboard:** Web UI showing progress across all OEMs
