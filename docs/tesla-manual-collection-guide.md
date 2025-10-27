# Tesla Manual Collection Guide

**Created**: 2025-10-26
**Status**: Active workflow for collecting 179 wealthy ZIP codes

## Quick Start

```bash
cd /Users/tmkipper/Desktop/dealer-scraper-mvp
python3 scripts/tesla_manual_collection.py
```

## The Workflow

### What the Script Does
1. Opens Tesla page in Chrome (visible browser)
2. Shows you the next ZIP code to collect
3. Waits for you to press Enter when results are loaded
4. Automatically extracts all installer data with JavaScript
5. Saves progress after each ZIP
6. Creates batch CSV files every 20 ZIPs
7. Merges everything at the end

### What You Do
1. **Enter the ZIP code** shown by the script into the Tesla search box
2. **Select United States** if the region selector appears
3. **Wait for results to load** completely (scroll down to see all cards)
4. **Press Enter** to trigger extraction
5. Repeat for next ZIP

## Features

### ✅ Resume Support
- Progress saved after each ZIP in `output/tesla_manual_progress.json`
- Can stop anytime (Ctrl+C) and resume later
- Skips already-collected ZIPs automatically

### ✅ Batch Saving
- Saves CSV every 20 ZIPs (`tesla_manual_batch_001.csv`, etc.)
- If script crashes, you only lose current batch (max 20 ZIPs)

### ✅ Auto-Deduplication
- Final merge removes duplicates by phone number
- Keeps first occurrence of each unique installer

### ✅ Same Extraction Logic
- Uses identical JavaScript extraction as automated scraper
- Extracts: name, phone, website, domain, email, tier, certifications

## Output Files

**During Collection**:
- `output/tesla_manual_batch_001.csv` - First 20 ZIPs
- `output/tesla_manual_batch_002.csv` - Next 20 ZIPs
- ... (9 total batch files for 179 ZIPs)
- `output/tesla_manual_progress.json` - Resume state

**After Completion**:
- `output/tesla_manual_YYYYMMDD_HHMMSS.csv` - Final merged & deduplicated results

## Expected Timeline

- **179 ZIPs total**
- **~2-3 minutes per ZIP** (manual entry + wait + extract)
- **Total time: 6-9 hours** (can split across multiple sessions)

## Tips for Efficiency

1. **Keep rhythm**: Enter ZIP → wait for load → press Enter → repeat
2. **Watch for region selector**: Only appears first time or after page refresh
3. **Don't rush**: Better to wait 5 extra seconds than miss results
4. **Take breaks**: Script remembers your progress, resume anytime
5. **Scroll down**: Make sure all installer cards are visible before pressing Enter

## Troubleshooting

### "Extracted 0 installers"
- **Cause**: Results didn't finish loading
- **Fix**: Reload page, enter ZIP again, wait longer

### Script crashes
- **Fix**: Just run it again - it will resume from last completed ZIP
- **Check**: `output/tesla_manual_progress.json` shows completed ZIPs

### Missing installers for a ZIP
- **Fix**: Delete that ZIP from `completed_zips` in progress.json, run script again

## Post-Collection

Once you have `tesla_manual_YYYYMMDD_HHMMSS.csv`:

```bash
# Run ICP scoring and multi-OEM detection
python3 scripts/run_post_scrape_pipeline.py \
  --input output/tesla_manual_YYYYMMDD_HHMMSS.csv \
  --output output/tesla_scored_YYYYMMDD.csv
```

This will:
- Score installers with Coperniq ICP algorithm (0-100)
- Tag SREC state priority (HIGH/MEDIUM/LOW)
- Mark ITC urgency (CRITICAL/HIGH/MEDIUM/LOW)
- Sort by score (highest quality leads first)

## Why Manual Collection?

**Short-term**: Gets you Tesla data TODAY while automation is being debugged
**Long-term**: Automation will be fixed for future updates, but manual collection proves the extraction logic works

---

**Need help?** The script shows clear prompts for each step. Just follow along!
