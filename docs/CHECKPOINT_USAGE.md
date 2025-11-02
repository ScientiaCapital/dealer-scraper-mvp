# Checkpoint Feature Usage Guide

## Overview

The enhanced OEM scraper system automatically saves progress every 25 ZIP codes, creating checkpoint files for recovery and monitoring.

## Automatic Checkpoint Saving

All OEM scrapers now support checkpoint saving:

```python
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ALL_ZIP_CODES

scraper = ScraperFactory.create("Generac", mode=ScraperMode.PLAYWRIGHT)
dealers = scraper.scrape_multiple(
    zip_codes=ALL_ZIP_CODES,
    checkpoint_interval=25  # Save every 25 ZIPs (default)
)
```

## Checkpoint Files

**Location:** `output/oem_data/{oem_name}/`

**Files created:**
- `{oem}_checkpoint_0025.json` - Dealer data + metadata after 25 ZIPs
- `{oem}_checkpoint_0025.log` - Human-readable progress log
- `{oem}_checkpoint_0050.json` - After 50 ZIPs
- `{oem}_checkpoint_0050.log`
- ... continues every 25 ZIPs ...
- `{oem}_checkpoint_0264.json` - Final complete dataset (status: "completed")
- `{oem}_checkpoint_0264.log`
- `{oem}_national_YYYYMMDD.csv` - Final deduplicated CSV
- `{oem}_national_YYYYMMDD.json` - Final deduplicated JSON
- `{oem}_run_YYYYMMDD_HHMMSS.log` - Complete run log

## Checkpoint JSON Schema

```json
{
  "oem_name": "Generac",
  "started_at": "2025-11-02T08:15:23.123456",
  "last_updated": "2025-11-02T08:45:12.654321",
  "total_zips": 264,
  "completed_zips": 50,
  "failed_zips": [],
  "total_dealers": 587,
  "dealers_after_dedup": 521,
  "checkpoint_number": 50,
  "status": "in_progress",
  "dealers": [
    {
      "name": "ABC Solar & Electric",
      "phone": "5551234567",
      "domain": "abcsolar.com",
      ...
    }
  ]
}
```

**Enhanced fields:**
- `started_at`: Run start timestamp (persists across checkpoints)
- `dealers_after_dedup`: Unique dealers after multi-signal deduplication
- `status`: "in_progress" or "completed"

## Master Production Runner

Run all 20 OEMs with semi-automated execution:

```bash
python3 scripts/run_all_oems_production.py
```

**Features:**
- Prompts before each OEM starts (yes/no/skip)
- Saves checkpoints every 25 ZIPs automatically
- Pause-and-alert error handling
- Priority ordering: HVAC → Generators → Solar → Battery
- Statistics and progress tracking after each OEM
- Final summary with completed/skipped/failed lists

**OEM Priority Order (20 total):**
1. **Tier 1 HVAC**: Carrier, Lennox, Trane, Mitsubishi, York, Rheem
2. **Tier 2 Generators**: Generac, Kohler, Cummins, Briggs & Stratton
3. **Tier 3 Solar**: SolarEdge, Enphase, SMA, Fronius, Sungrow, GoodWe, Growatt, Sol-Ark
4. **Tier 4 Battery**: Tesla, SimpliPhi

## Error Recovery

If a scraper fails during execution:

1. **Last checkpoint is automatically saved** (no data loss)
2. **User prompted with options:**
   - `(r)etry` - Retry the same OEM from beginning
   - `(s)kip` - Skip to next OEM in priority list
   - `(q)uit` - Stop entire production run

3. **Manual resume (if needed):**

```python
import json
from config import ALL_ZIP_CODES

# Load checkpoint
with open('output/oem_data/generac/generac_checkpoint_0150.json') as f:
    checkpoint = json.load(f)

# Get remaining ZIPs
completed_zips = checkpoint['completed_zips']
remaining_zips = ALL_ZIP_CODES[completed_zips:]

# Resume scraping from where it left off
scraper = ScraperFactory.create("Generac", mode=ScraperMode.PLAYWRIGHT)
scraper.scrape_multiple(remaining_zips, checkpoint_interval=25)
```

## Configuration Options

### Custom Checkpoint Interval

```python
# Save every 50 ZIPs instead of 25
dealers = scraper.scrape_multiple(
    zip_codes=ALL_ZIP_CODES,
    checkpoint_interval=50
)
```

### Custom Checkpoint Directory

```python
# Override default output directory
dealers = scraper.scrape_multiple(
    zip_codes=ALL_ZIP_CODES,
    checkpoint_interval=25,
    checkpoint_dir="custom/checkpoint/path"
)
```

## Production Run Workflow

**Full production run (7-9 hours for 20 OEMs × 264 ZIPs):**

1. **Start master runner:**
   ```bash
   python3 scripts/run_all_oems_production.py
   ```

2. **Review configuration:**
   - 20 OEMs in priority order
   - 264 ZIP codes (deduplicated SREC + nationwide wealthy)
   - 5,280 total operations
   - Checkpoint interval: 25 ZIPs

3. **For each OEM:**
   - Prompted: "Ready to run? (yes/no/skip)"
   - Enter `yes` to start scraping
   - Monitor progress: `[X/264] Scraping {OEM} dealers for ZIP {zipcode}...`
   - Checkpoint saves: `📦 Checkpoint saved: X zips, Y dealers`
   - On error: Choose (r)etry/(s)kip/(q)uit

4. **After each OEM completes:**
   - Statistics displayed (raw dealers, deduplicated, duration)
   - Final CSV/JSON saved to `output/oem_data/{oem}/`

5. **Final summary:**
   - ✅ Completed OEMs
   - ⏭️ Skipped OEMs
   - ❌ Failed OEMs

## Performance Metrics

**From test run (Briggs & Stratton, 30 ZIPs):**
- Average: ~11 seconds per ZIP code
- Checkpoints: 3 files created (at 10, 20, 30 ZIPs)
- Raw dealers: 299
- After deduplication: 77 unique (74% dedup rate)
- Total runtime: 5 minutes 33 seconds

**Expected production performance:**
- 264 ZIPs × 20 OEMs = 5,280 operations
- ~5-6 seconds per ZIP (Playwright automation)
- Total runtime: 7-9 hours
- Checkpoints: ~11 per OEM (every 25 ZIPs)

## Deduplication Algorithm

Checkpoints use enhanced multi-signal deduplication (97.3% accuracy):

1. **Phone normalization** (96.5% of duplicates): Strip to 10 digits, remove country code
2. **Domain matching** (0.7% additional): Extract root domain, case-insensitive
3. **Fuzzy name matching** (0.1% additional): 85% similarity threshold + same state

This prevents data bloat in checkpoint files and ensures accurate dealer counts.

## Monitoring Progress

**During execution:**
- Console output shows real-time progress
- Log files updated continuously
- Checkpoint files saved every 25 ZIPs

**Check progress programmatically:**
```python
import json

# Read latest checkpoint
with open('output/oem_data/generac/generac_checkpoint_0150.json') as f:
    checkpoint = json.load(f)

print(f"Progress: {checkpoint['completed_zips']}/{checkpoint['total_zips']} ZIPs")
print(f"Dealers: {checkpoint['dealers_after_dedup']} unique")
print(f"Status: {checkpoint['status']}")
```

## Troubleshooting

**Issue: Checkpoint save failed**
- Error logged: `CHECKPOINT FAILED: Unable to save...`
- Scraping continues (no crash)
- Check disk space: `df -h`
- Verify directory permissions: `ls -la output/oem_data/`

**Issue: Need to resume after crash**
- Find last successful checkpoint: `ls -lt output/oem_data/{oem}/`
- Load checkpoint and extract `completed_zips`
- Calculate remaining ZIPs: `ALL_ZIP_CODES[completed_zips:]`
- Resume scraping from remaining ZIPs

**Issue: Duplicate dealers in final output**
- Deduplication runs automatically in `scrape_multiple()`
- Check `dealers_after_dedup` in checkpoint metadata
- If duplicates persist, verify phone numbers are normalized
- Re-run `scraper.deduplicate_by_phone()` on final dataset

## Testing

**Test checkpoint feature (quick validation):**
```bash
python3 scripts/test_checkpoint_feature.py
```

This runs Briggs & Stratton on 30 ZIPs with 10-ZIP checkpoints (~5 minutes).

**Verify checkpoint files:**
```bash
ls -lh output/oem_data/briggs_*_stratton/*checkpoint*.json
ls -lh output/oem_data/briggs_*_stratton/*checkpoint*.log
```

**Validate JSON structure:**
```bash
python3 -m json.tool output/oem_data/briggs_*_stratton/*checkpoint_0010.json | head -30
```
