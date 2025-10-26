# Technical Debt Cleanup - One OEM Per File Strategy

**Date**: 2025-10-26
**Status**: Approved
**Author**: Claude Code

## Context

The codebase had multiple scraper implementations and orchestration scripts that were causing issues:
- Multi-OEM script triggering bot detection with rapid-fire requests
- Duplicate Tesla scraper files (standalone vs. browserbase)
- Generic runner scripts that added complexity without value

## Problem Statement

We need a clean, maintainable scraper architecture where:
1. Each OEM has ONE working `.py` file
2. Each scraper can run independently with custom anti-bot timing
3. No orchestration layer triggering detection patterns
4. Clear separation between production (Browserbase) and manual fallback (local Playwright)

## Design Decision

### One Scraper Per OEM Strategy

Each OEM website has unique bot detection patterns, so each needs its own standalone scraper file:
- `scrape_tesla_browserbase.py` - Tesla Powerwall installer scraper
- `scrape_enphase_browserbase.py` - (Future) Enphase microinverter installer scraper
- `scrape_solaredge_browserbase.py` - (Future) SolarEdge inverter installer scraper
- `scrape_generac_browserbase.py` - (Future) Generac generator installer scraper

### Final File Structure

**KEEP** (3 files):
```
scripts/
├── scrape_tesla_browserbase.py      # Production Tesla scraper (Browserbase cloud)
├── run_post_scrape_pipeline.py      # Post-processing pipeline (dedup, ICP scoring)
└── run_local_playwright.py          # Manual fallback for debugging
```

**REMOVE** (3 files):
```
scripts/
├── scrape_tesla_standalone.py       # DELETE - Duplicate, not working
├── run_multi_oem_scraping.py        # DELETE - Orchestration triggers bot detection
└── run_scraper.py                   # DELETE - Redundant generic runner
```

## Rationale

### Why Keep run_local_playwright.py?
- **Manual fallback**: If Browserbase has downtime or API issues, local Playwright provides quick debugging
- **Inspection tool**: Useful for manually inspecting new OEM websites before writing extraction scripts
- **No automation risk**: Manual usage doesn't trigger bot detection patterns

### Why Delete Multi-OEM Script?
- **Bot detection**: Looping through multiple OEMs in rapid succession triggers JavaScript fingerprinting
- **Complexity**: Orchestration layer adds unnecessary abstraction
- **One-at-a-time approach**: User confirmed we should run each OEM to completion before moving to next

### Why Delete Standalone Tesla Scraper?
- **Redundant**: Browserbase version is the working solution
- **Not functional**: Local browser consistently blocked by Tesla's bot detection
- **Confusion**: Having two Tesla scrapers creates ambiguity

## Implementation Steps

1. **Delete redundant files**:
   ```bash
   git rm scripts/scrape_tesla_standalone.py
   git rm scripts/run_multi_oem_scraping.py
   git rm scripts/run_scraper.py
   ```

2. **Verify dependencies**: Ensure `scrape_tesla_browserbase.py` has all required imports

3. **Test Tesla scraper**: Run test mode to confirm functionality

4. **Commit cleanup**:
   ```
   git commit -m "Cleanup: Remove technical debt, establish one-scraper-per-OEM pattern

   Removed:
   - scrape_tesla_standalone.py (redundant, not working)
   - run_multi_oem_scraping.py (orchestration triggers bot detection)
   - run_scraper.py (redundant generic runner)

   Kept:
   - scrape_tesla_browserbase.py (working Tesla scraper)
   - run_post_scrape_pipeline.py (post-processing pipeline)
   - run_local_playwright.py (manual fallback for debugging)

   Establishes pattern: Each OEM gets dedicated scraper file to handle
   unique bot detection patterns independently."
   ```

## Future OEM Additions

When adding Enphase, SolarEdge, or Generac:
1. Create new `scrape_{oem}_browserbase.py` file
2. Inspect OEM website manually using `run_local_playwright.py`
3. Write custom extraction script for that OEM's DOM structure
4. Test with 3 ZIPs before full production run
5. Run to completion (179 ZIPs) before moving to next OEM

## Success Criteria

- ✅ Only 3 files remain in `scripts/` (Tesla scraper + pipeline + fallback)
- ✅ Tesla scraper runs without errors
- ✅ Clear path for adding future OEM scrapers
- ✅ No multi-OEM orchestration complexity
- ✅ Manual debugging fallback available
