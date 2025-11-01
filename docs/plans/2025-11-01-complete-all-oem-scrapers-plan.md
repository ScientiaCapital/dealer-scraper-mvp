# Complete All 18 OEM Scrapers - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete extraction scripts and production runs for all 18 OEM dealer locators with full 310-ZIP coverage.

**Architecture:** Manual Playwright MCP inspection to understand each site's DOM structure, write custom extraction.js scripts, validate with 3-ZIP tests, then execute full 310-ZIP production runs. Sequential execution with Browserbase fallback for bot detection.

**Tech Stack:** Playwright MCP (DOM inspection), Python 3.11+, Pandas (deduplication), ScraperFactory pattern (PLAYWRIGHT/BROWSERBASE modes)

---

## Task 1: Consolidate ZIP Codes

**Files:**
- Modify: `config.py` (add ZIP_CODES_ALL array)

**Step 1: Add metro ZIP codes list**

Add after existing ZIP_CODES_SREC_ALL definition:

```python
# Additional metro area ZIPs (170 ZIPs from non-SREC states)
ZIP_CODES_METRO_NON_SREC = [
    # Georgia - Atlanta metro
    "30301", "30305", "30309", "30318", "30324", "30327", "30342", "30350",

    # Washington - Seattle metro
    "98101", "98102", "98103", "98109", "98112", "98115", "98119", "98122",

    # Colorado - Denver metro
    "80202", "80203", "80206", "80209", "80210", "80218", "80220", "80230",

    # Arizona - Phoenix metro
    "85001", "85004", "85012", "85014", "85016", "85018", "85020", "85028",

    # North Carolina - Charlotte metro
    "28202", "28203", "28204", "28205", "28207", "28209", "28211", "28226",

    # Tennessee - Nashville metro
    "37201", "37203", "37204", "37205", "37206", "37212", "37215", "37220",

    # Oregon - Portland metro
    "97201", "97202", "97205", "97209", "97210", "97211", "97214", "97221",

    # Nevada - Las Vegas metro
    "89101", "89102", "89103", "89104", "89109", "89117", "89118", "89144",

    # Michigan - Detroit metro
    "48201", "48202", "48207", "48214", "48226", "48235", "48301", "48304",

    # Minnesota - Minneapolis metro (additional)
    "55401", "55402", "55403", "55404", "55405", "55406", "55407", "55408",

    # Wisconsin - Milwaukee metro (additional)
    "53201", "53202", "53203", "53204", "53205", "53206", "53207", "53208",

    # Missouri - St. Louis metro
    "63101", "63102", "63103", "63104", "63108", "63109", "63110", "63118",

    # Indiana - Indianapolis metro
    "46201", "46202", "46203", "46204", "46205", "46208", "46220", "46240",

    # Virginia - Richmond metro
    "23219", "23220", "23221", "23222", "23223", "23224", "23225", "23226",

    # South Carolina - Charleston metro
    "29401", "29403", "29407", "29412", "29414", "29455", "29464", "29466",

    # Louisiana - New Orleans metro
    "70112", "70113", "70114", "70115", "70116", "70117", "70118", "70119",

    # Alabama - Birmingham metro
    "35203", "35205", "35206", "35209", "35213", "35216", "35222", "35226",

    # Kentucky - Louisville metro
    "40202", "40203", "40204", "40205", "40206", "40207", "40208", "40209",

    # Oklahoma - Oklahoma City metro
    "73102", "73103", "73104", "73105", "73106", "73107", "73108", "73109",

    # Utah - Salt Lake City metro
    "84101", "84102", "84103", "84104", "84105", "84106", "84107", "84108",

    # New Mexico - Albuquerque metro
    "87101", "87102", "87104", "87105", "87106", "87107", "87108", "87109",
]

# Consolidated list - ALL 310 ZIPs
ZIP_CODES_ALL = ZIP_CODES_SREC_ALL + ZIP_CODES_METRO_NON_SREC
```

**Step 2: Verify ZIP count**

Run in Python REPL:
```bash
python3 -c "from config import ZIP_CODES_ALL; print(f'Total ZIPs: {len(ZIP_CODES_ALL)}')"
```

Expected output: `Total ZIPs: 310`

**Step 3: Commit**

```bash
git add config.py
git commit -m "feat: consolidate ZIP codes into ZIP_CODES_ALL (310 total)"
```

---

## Task 2: Tesla Powerwall - DOM Inspection

**Files:**
- Inspect: https://www.tesla.com/support/certified-installers-powerwall
- Notes: Keep notes in terminal/text editor for next step

**Step 1: Navigate to Tesla site**

```bash
# Use Playwright MCP browser_navigate tool
```

Navigate to: `https://www.tesla.com/support/certified-installers-powerwall`

**Step 2: Take initial snapshot**

```bash
# Use Playwright MCP browser_snapshot tool
```

Examine accessibility tree for:
- Search input field (name, role, placeholder)
- Search button (text, role)
- Result containers after search

**Step 3: Fill test ZIP and search**

```bash
# Use Playwright MCP browser_type tool
```

Type `94102` into search input
Click search button
Wait 3 seconds

**Step 4: Take results snapshot**

```bash
# Use Playwright MCP browser_snapshot tool
```

Note in text editor:
- Result container selector (class/id)
- Dealer name selector
- Phone selector
- Address selectors
- Website selector
- Any pagination elements

---

## Task 3: Tesla Powerwall - Write Extraction Script

**Files:**
- Create: `scrapers/tesla/extraction.js`

**Step 1: Create extraction script from DOM inspection**

Use notes from Task 2 to fill in selectors:

```javascript
/**
 * Tesla Powerwall Certified Installer Extraction Script
 *
 * This script is injected into the page AFTER search results load.
 * It extracts dealer information from the DOM.
 */

function extractDealers() {
  const dealers = [];

  // TODO: Update selector based on DOM inspection
  const resultContainers = document.querySelectorAll('.installer-result-card');

  if (resultContainers.length === 0) {
    console.log('No dealer results found. Possible selectors issue.');
    return dealers;
  }

  resultContainers.forEach((card, index) => {
    try {
      // Extract dealer data
      const nameEl = card.querySelector('.installer-name');
      const phoneEl = card.querySelector('.installer-phone');
      const addressEl = card.querySelector('.installer-address');
      const websiteEl = card.querySelector('.installer-website a');

      const dealer = {
        name: nameEl?.textContent.trim() || '',
        phone: phoneEl?.textContent.trim() || '',
        address_full: addressEl?.textContent.trim() || '',
        website: websiteEl?.href || '',

        // Extract from address if available
        city: '',
        state: '',
        zip: '',

        // Optional fields
        rating: 0,
        review_count: 0,
        distance: '',
        tier: '',
        certifications: [],
      };

      // Parse address into components
      if (dealer.address_full) {
        const addressParts = dealer.address_full.split(',').map(p => p.trim());
        if (addressParts.length >= 2) {
          dealer.city = addressParts[addressParts.length - 2];

          const stateZip = addressParts[addressParts.length - 1];
          const stateZipMatch = stateZip.match(/([A-Z]{2})\s+(\d{5})/);
          if (stateZipMatch) {
            dealer.state = stateZipMatch[1];
            dealer.zip = stateZipMatch[2];
          }
        }
      }

      // Only add if has minimum required fields
      if (dealer.name && (dealer.phone || dealer.website)) {
        dealers.push(dealer);
      }

    } catch (err) {
      console.log(`Error extracting dealer ${index}:`, err.message);
    }
  });

  console.log(`Extracted ${dealers.length} Tesla Powerwall dealers`);
  return dealers;
}

// Execute extraction
extractDealers();
```

**Step 2: Save file**

File already saved by Write tool.

**Step 3: Commit**

```bash
git add scrapers/tesla/extraction.js
git commit -m "feat: add Tesla Powerwall extraction script (initial)"
```

---

## Task 4: Tesla Powerwall - Test Extraction

**Files:**
- Test: `scrapers/tesla/extraction.js`
- Run: Manual Playwright MCP test

**Step 1: Navigate and search**

Using Playwright MCP:
1. Navigate to Tesla installer locator
2. Fill ZIP: `94102`
3. Click search
4. Wait 3 seconds

**Step 2: Execute extraction script**

```bash
# Use Playwright MCP browser_evaluate tool
```

Execute the extraction.js content
Check console output for: `Extracted N Tesla Powerwall dealers`

**Step 3: Verify data quality**

Expected results:
- At least 5 dealers extracted
- All have names
- 90%+ have phone numbers
- No duplicate phone numbers
- Address parsing works (city, state, zip populated)

**Step 4: Adjust selectors if needed**

If extraction fails or data is incomplete:
- Re-inspect DOM with browser_snapshot
- Update selectors in extraction.js
- Repeat Steps 1-3
- Commit when passing: `git commit -am "fix: adjust Tesla extraction selectors"`

---

## Task 5: Tesla Powerwall - Create Test Script

**Files:**
- Create: `scripts/test_tesla_scraper.py`

**Step 1: Write test script**

```python
#!/usr/bin/env python3
"""
Quick test script for Tesla Powerwall scraper.
Tests 3 ZIPs to validate extraction before full production run.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

TEST_ZIPS = ["94102", "78701", "19103"]  # SF, Austin, Philly

def main():
    print("=" * 80)
    print("Tesla Powerwall Scraper - Quick Test")
    print("=" * 80)
    print()

    scraper = ScraperFactory.create("Tesla", mode=ScraperMode.PLAYWRIGHT)

    all_dealers = []
    for zip_code in TEST_ZIPS:
        print(f"\nTesting ZIP: {zip_code}")
        print("-" * 40)

        dealers = scraper.scrape_dealers(zip_code)

        print(f"  Found: {len(dealers)} dealers")
        if dealers:
            print(f"  First dealer: {dealers[0].name}")
            print(f"  Phone: {dealers[0].phone}")
            print(f"  Website: {dealers[0].website}")

        all_dealers.extend(dealers)

    print()
    print("=" * 80)
    print(f"Total dealers: {len(all_dealers)}")
    print("=" * 80)

    # Quality checks
    missing_names = sum(1 for d in all_dealers if not d.name)
    missing_phones = sum(1 for d in all_dealers if not d.phone)

    print(f"\nQuality checks:")
    print(f"  Missing names: {missing_names} ({missing_names/len(all_dealers)*100:.1f}%)")
    print(f"  Missing phones: {missing_phones} ({missing_phones/len(all_dealers)*100:.1f}%)")

    if len(all_dealers) >= 15 and missing_names == 0 and missing_phones < len(all_dealers) * 0.1:
        print("\n✅ Test PASSED - Ready for production")
        return 0
    else:
        print("\n❌ Test FAILED - Review extraction script")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make executable**

```bash
chmod +x scripts/test_tesla_scraper.py
```

**Step 3: Run test**

```bash
python3 scripts/test_tesla_scraper.py
```

Expected: `✅ Test PASSED - Ready for production`

**Step 4: Commit**

```bash
git add scripts/test_tesla_scraper.py
git commit -m "test: add Tesla Powerwall 3-ZIP validation script"
```

---

## Task 6: Tesla Powerwall - Production Run

**Files:**
- Run: Production scraper with 310 ZIPs
- Output: `output/oem_data/tesla/tesla_all_zips_20251101.csv`

**Step 1: Create production script**

Create: `scripts/run_tesla_production.py`

```python
#!/usr/bin/env python3
"""
Tesla Powerwall - Full Production Run (310 ZIPs)
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode
from config import ZIP_CODES_ALL
import pandas as pd

OUTPUT_DIR = PROJECT_ROOT / "output" / "oem_data" / "tesla"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 80)
    print(f"Tesla Powerwall - Production Run ({len(ZIP_CODES_ALL)} ZIPs)")
    print("=" * 80)
    print()

    scraper = ScraperFactory.create("Tesla", mode=ScraperMode.PLAYWRIGHT)

    all_dealers = []
    checkpoint_interval = 25

    for i, zip_code in enumerate(ZIP_CODES_ALL, 1):
        print(f"\n[{i}/{len(ZIP_CODES_ALL)}] Scraping ZIP: {zip_code}")

        try:
            dealers = scraper.scrape_dealers(zip_code)
            print(f"  ✓ Found {len(dealers)} dealers")
            all_dealers.extend(dealers)

            # Checkpoint save
            if i % checkpoint_interval == 0:
                checkpoint_file = OUTPUT_DIR / f"tesla_checkpoint_{i}zips.csv"
                df = pd.DataFrame([d.__dict__ for d in all_dealers])
                df.to_csv(checkpoint_file, index=False)
                print(f"  💾 Checkpoint saved: {len(all_dealers)} total dealers")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            continue

    # Final save
    print()
    print("=" * 80)
    print("Saving final results...")
    print("=" * 80)

    df = pd.DataFrame([d.__dict__ for d in all_dealers])

    # Raw output
    date_str = datetime.now().strftime("%Y%m%d")
    raw_file = OUTPUT_DIR / f"tesla_all_zips_{date_str}.csv"
    df.to_csv(raw_file, index=False)
    print(f"✅ Raw: {raw_file.name} ({len(df)} dealers)")

    # Deduplicated
    df_deduped = df.drop_duplicates(subset=['phone'], keep='first')
    dedup_file = OUTPUT_DIR / f"tesla_deduped_{date_str}.csv"
    df_deduped.to_csv(dedup_file, index=False)
    print(f"✅ Deduplicated: {dedup_file.name} ({len(df_deduped)} unique dealers)")

    print()
    print(f"Deduplication: {len(df) - len(df_deduped)} duplicates removed")
    print()

if __name__ == "__main__":
    main()
```

**Step 2: Make executable**

```bash
chmod +x scripts/run_tesla_production.py
```

**Step 3: Run production (monitor first 10 ZIPs)**

```bash
python3 -u scripts/run_tesla_production.py 2>&1 | tee output/logs/tesla_production_20251101.log
```

Watch first 10 ZIPs for errors. If stable, proceed to next task. If errors:
- Check logs
- Debug extraction script
- Consider Browserbase fallback
- Restart production run

**Step 4: Commit production script**

```bash
git add scripts/run_tesla_production.py
git commit -m "feat: add Tesla Powerwall production script (310 ZIPs)"
```

---

## Task 7: Enphase - Repeat Tesla Pattern

**Files:**
- Inspect: https://enphase.com/installer-locator
- Create: `scrapers/enphase/extraction.js`
- Create: `scripts/test_enphase_scraper.py`
- Create: `scripts/run_enphase_production.py`

**Repeat Tasks 2-6 for Enphase:**
1. DOM inspection with Playwright MCP
2. Write extraction.js (update selectors)
3. Test with 3 ZIPs
4. Create test script
5. Run test script (must pass)
6. Create production script
7. Run production (310 ZIPs)

**Expected timeline:** 76 minutes (inspect 30 min + write 20 min + test 10 min + run 26 min, but run happens in background)

---

## Task 8-23: Remaining 16 OEMs

**Priority order:**
3. Generac (re-validate)
4. SolarEdge
5. Cummins (re-validate)
6. Briggs & Stratton (re-validate)
7. Mitsubishi
8. Carrier (re-validate)
9. Trane
10. York (re-validate)
11. Lennox
12. Rheem
13. Fronius
14. SMA (re-validate)
15. GoodWe
16. Growatt
17. Kohler
18. SimpliPhi

**For each OEM, repeat the pattern:**
1. DOM inspection (20 min)
2. Write extraction.js (20 min)
3. Test 3 ZIPs (10 min)
4. Run production 310 ZIPs (26 min in background)
5. While scraper N runs, start scraper N+1 inspection

**Optimization:** Overlap inspection/writing (40 min) with previous scraper's production run (26 min). Net time: 50 min first scraper + 26 min per remaining = 7.8 hours for 16 scrapers.

**Template for each scraper:**

### Task N: [OEM Name] - Complete Scraper

**Step 1: DOM Inspection**
- Navigate to [dealer locator URL]
- Take snapshots
- Note selectors

**Step 2: Write extraction.js**
- Create `scrapers/[oem_name]/extraction.js`
- Based on DOM structure
- Commit: `git add scrapers/[oem_name]/extraction.js && git commit -m "feat: add [OEM] extraction script"`

**Step 3: Test 3 ZIPs**
- Create `scripts/test_[oem]_scraper.py`
- Run test: `python3 scripts/test_[oem]_scraper.py`
- Must pass before production

**Step 4: Run Production**
- Create `scripts/run_[oem]_production.py`
- Execute: `python3 -u scripts/run_[oem]_production.py 2>&1 | tee output/logs/[oem]_production_20251101.log`
- Monitor first 10 ZIPs, then move to next OEM

**Step 5: Verify Output**
- Check: `output/oem_data/[oem]/[oem]_deduped_20251101.csv` exists
- Count: 500-3000 unique dealers expected

---

## Task 24: Aggregate All OEM Data

**Files:**
- Create: `scripts/aggregate_all_oems_20251101.py`
- Output: `output/grandmaster_list_full_20251101.csv`

**Step 1: Write aggregation script**

```python
#!/usr/bin/env python3
"""
Aggregate All OEM Data - November 1, 2025
Combines all 18 OEM scrapers into unified grandmaster list.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OEM_DATA_DIR = OUTPUT_DIR / "oem_data"

OEMS = [
    "tesla", "enphase", "generac", "solaredge", "cummins",
    "briggs_stratton", "mitsubishi", "carrier", "trane", "york",
    "lennox", "rheem", "fronius", "sma", "goodwe",
    "growatt", "kohler", "simpliphi"
]

def main():
    print("=" * 80)
    print("Aggregating All OEM Data (18 Scrapers)")
    print("=" * 80)
    print()

    all_dealers = []

    for oem in OEMS:
        oem_dir = OEM_DATA_DIR / oem
        dedup_file = list(oem_dir.glob(f"{oem}_deduped_*.csv"))

        if not dedup_file:
            print(f"⚠️  {oem}: No deduplicated file found, skipping")
            continue

        df = pd.read_csv(dedup_file[0])
        print(f"✓ {oem}: {len(df)} unique dealers")
        all_dealers.append(df)

    # Combine
    print()
    print("Combining all OEM data...")
    combined_df = pd.concat(all_dealers, ignore_index=True)
    print(f"  Total records: {len(combined_df):,}")

    # Global deduplication by phone
    print("Deduplicating by phone...")
    combined_df['phone_normalized'] = combined_df['phone'].str.replace(r'\D', '', regex=True)
    deduped_df = combined_df.drop_duplicates(subset=['phone_normalized'], keep='first')
    print(f"  Unique contractors: {len(deduped_df):,}")
    print(f"  Duplicates removed: {len(combined_df) - len(deduped_df):,}")

    # Save
    date_str = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"grandmaster_list_full_{date_str}.csv"
    deduped_df.to_csv(output_file, index=False)

    print()
    print("=" * 80)
    print(f"✅ Grandmaster list saved: {output_file.name}")
    print(f"   Total unique contractors: {len(deduped_df):,}")
    print("=" * 80)

if __name__ == "__main__":
    main()
```

**Step 2: Run aggregation**

```bash
python3 scripts/aggregate_all_oems_20251101.py
```

Expected: 20,000-30,000 unique contractors

**Step 3: Commit**

```bash
git add scripts/aggregate_all_oems_20251101.py
git commit -m "feat: aggregate all 18 OEM scrapers into grandmaster list"
```

---

## Task 25: Multi-OEM Cross-Reference

**Files:**
- Run existing: `analysis/multi_oem_detector.py`
- Output: `output/multi_oem_crossover_20251101.csv`

**Step 1: Run multi-OEM detector**

```bash
python3 analysis/multi_oem_detector.py \
  --input output/grandmaster_list_full_20251101.csv \
  --output output/multi_oem_crossover_20251101.csv
```

Expected: Identify contractors in 2-3+ OEM networks

**Step 2: Review top crossovers**

```bash
head -20 output/multi_oem_crossover_20251101.csv
```

Look for contractors with 3+ OEM certifications (unicorns)

---

## Task 26: Apply ICP Scoring

**Files:**
- Run existing: `targeting/coperniq_lead_scorer.py`
- Output: `output/icp_scored_contractors_20251101.csv`

**Step 1: Run ICP scorer**

```bash
python3 targeting/coperniq_lead_scorer.py \
  --input output/grandmaster_list_full_20251101.csv \
  --multi-oem output/multi_oem_crossover_20251101.csv \
  --output output/icp_scored_contractors_20251101.csv
```

**Step 2: Generate tier CSVs**

```bash
python3 targeting/generate_tier_csvs.py \
  --input output/icp_scored_contractors_20251101.csv \
  --output-dir output/tiers_20251101/
```

Expected outputs:
- `gold_tier_20251101.csv` (60-79 score)
- `silver_tier_20251101.csv` (40-59 score)
- `bronze_tier_20251101.csv` (<40 score)

---

## Task 27: Final Commit & Documentation

**Files:**
- Update: `CLAUDE.md` (current status)
- Commit all changes

**Step 1: Update CLAUDE.md status**

Update "Current Status" section:
```markdown
**Current Status** (as of Nov 1, 2025):
- ✅ **18 OEM scrapers - ALL COMPLETE** with 310-ZIP production runs
- ✅ **Grandmaster list: 20K-30K unique contractors** (deduplicated)
- ✅ Multi-OEM cross-reference (200+ contractors in 2-3+ networks)
- ✅ ICP scoring applied (GOLD/SILVER/BRONZE tiers)
- ✅ ZIP code consolidation (310 ZIPs: 140 SREC + 170 metro)
```

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete all 18 OEM scrapers with 310-ZIP coverage

MAJOR MILESTONE: All 18 OEM dealer locators scraped and production-ready

OEMs completed:
- Tesla Powerwall (batteries)
- Enphase (microinverters)
- Generac (generators)
- SolarEdge, Fronius, SMA, GoodWe, Growatt (inverters)
- Cummins, Briggs & Stratton, Kohler (generators)
- Mitsubishi, Carrier, Trane, York, Lennox, Rheem (HVAC)
- SimpliPhi (battery storage)

Results:
- 20K-30K unique contractors in grandmaster list
- 310-ZIP coverage (140 SREC + 170 metro areas)
- Multi-OEM cross-reference identifies high-value prospects
- ICP scoring ready for BDR outreach

Next: Apollo enrichment + Close CRM import"
```

**Step 3: Push to GitHub**

```bash
git push origin main
```

---

## Error Handling & Recovery

### If Playwright Fails (Bot Detection, Timeout, etc.)

**Switch to Browserbase mode:**

1. Ensure `.env` has Browserbase credentials:
```bash
BROWSERBASE_API_KEY=your_key_here
BROWSERBASE_PROJECT_ID=your_project_here
```

2. Update scraper creation in production script:
```python
scraper = ScraperFactory.create("Tesla", mode=ScraperMode.BROWSERBASE)
```

3. Re-run production script
4. If Browserbase also fails: Skip OEM, continue to next, revisit later

### If Extraction Returns 0 Dealers

1. Re-inspect DOM with Playwright MCP browser_snapshot
2. Verify search executed (check for "No results" message vs. wrong selectors)
3. Increase wait time (3s → 5s)
4. Update extraction.js selectors
5. Re-test with 3 ZIPs before production

### If Production Script Crashes Mid-Run

1. Check checkpoint file: `output/oem_data/[oem]/[oem]_checkpoint_*.csv`
2. Resume from last checkpoint ZIP
3. Modify production script to skip already-scraped ZIPs
4. Continue production run

---

## Success Criteria

✅ All 18 OEM extraction scripts written and committed
✅ All 18 OEM test scripts pass 3-ZIP validation
✅ All 18 OEM production runs complete (310 ZIPs each)
✅ Grandmaster list aggregated: 20K-30K unique contractors
✅ Multi-OEM cross-reference identifies 200+ high-value prospects
✅ ICP scoring applied to all contractors
✅ Output CSVs exist for all tiers (GOLD, SILVER, BRONZE)
✅ No showstopper errors blocking completion
✅ All code committed and pushed to GitHub

---

**Estimated Total Time:** 10.3 hours
- Task 1: 10 min (ZIP consolidation)
- Tasks 2-6: 90 min (Tesla, including first production run)
- Task 7: 76 min (Enphase)
- Tasks 8-23: 416 min = 6.9 hours (16 OEMs × 26 min each, overlapping development)
- Tasks 24-27: 30 min (aggregation, analysis, final commit)

**Total: 618 minutes = 10.3 hours**
