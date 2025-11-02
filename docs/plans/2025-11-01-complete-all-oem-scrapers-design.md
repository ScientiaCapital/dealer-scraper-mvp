# Complete All 18 OEM Scrapers - Design Document

**Date:** November 1, 2025
**Goal:** Complete extraction scripts and production runs for all 18 OEM scrapers today
**Scope:** Tesla, Enphase, and 16 remaining OEMs with full 310-ZIP coverage

---

## Executive Summary

We will complete 18 OEM scrapers today using manual Playwright MCP inspection to write extraction scripts, then execute sequential production runs across 310 ZIP codes (140 SREC + 170 metro). Tesla and Enphase get priority. Each scraper takes 76 minutes (50 min development + 26 min execution). Total time: 10.3 hours.

---

## Timeline

### Phase 1: Tesla + Enphase (2.5 hours)
- **Tesla Powerwall**: Inspect DOM (30 min) → Write extraction.js (30 min) → Test 3 ZIPs (15 min) → Run 310 ZIPs (26 min)
- **Enphase**: Same pattern (76 min)

### Phase 2: Remaining 16 OEMs (7.8 hours)
- **Per scraper**: Inspect (20 min) + Write (20 min) + Test (10 min) + Run 310 ZIPs (26 min) = 76 min
- **Optimization**: While scraper N runs (26 min), develop scraper N+1 (40 min)
- **Net time**: 50 min first + (26 min × 17 remaining) = 7.8 hours

### Total: 10.3 hours

---

## Configuration Changes

### Consolidate ZIP Codes

Merge SREC and metro lists into single array:

```python
# config.py
ZIP_CODES_ALL = ZIP_CODES_SREC_ALL + [
    # Metro ZIPs from non-SREC states
    ...
]  # Total: 310 ZIPs
```

Every scraper uses `ZIP_CODES_ALL` after passing tests.

---

## Playwright MCP Workflow

### For Each Scraper:

**1. Navigate & Inspect (5-10 min)**
```
Navigate to [OEM dealer locator]
Take snapshot → Returns accessibility tree
```

**2. Fill & Search (5 min)**
```
Type [test ZIP] into search input
Click search button
Wait 3 seconds
Take snapshot → Returns results structure
```

**3. Analyze DOM (10-15 min)**
- Identify result containers (cards, list items, table rows)
- Find data selectors (name, address, phone, website)
- Check pagination vs. infinite scroll
- Note AJAX delays

**4. Write extraction.js (20-30 min)**
```javascript
function extractDealers() {
  const dealers = [];
  document.querySelectorAll('.dealer-card').forEach(card => {
    dealers.push({
      name: card.querySelector('.name')?.textContent.trim(),
      phone: card.querySelector('.phone')?.textContent.trim(),
      // ...
    });
  });
  return dealers;
}
```

### DOM Patterns

- **Table-based**: Generac, Trane (structured rows/columns)
- **Card-based**: Tesla, Enphase (grid layout)
- **List-based**: SolarEdge, SMA (vertical lists)
- **Map markers**: Some OEMs (require marker clicks)

---

## Testing Strategy

### Quick Validation (10 min)

```bash
python3 scripts/test_oem_scraper.py \
  --oem "Tesla" \
  --test-zips "94102,78701,19103" \
  --mode PLAYWRIGHT
```

### Pass Criteria

✅ Extracts 5+ dealers per ZIP (unless sparse market)
✅ 0 missing names, <10% missing phones
✅ No duplicate phone numbers
✅ Completes in <2 min per ZIP

### If Test Fails

- Re-inspect DOM with Playwright MCP
- Fix selector in extraction.js
- Retest same 3 ZIPs
- Move forward only when passing

---

## Production Execution

### Command

```bash
python3 scripts/run_multi_oem_scraping.py \
  --oems "Tesla" \
  --states ALL \
  --mode PLAYWRIGHT \
  2>&1 | tee output/logs/tesla_production_20251101.log
```

### Monitoring

- Watch first 10 ZIPs for errors
- If stable → work on next scraper
- If errors → kill, debug, restart

---

## Error Handling

### Browser Mode Hierarchy

1. **Primary**: Playwright MCP (local, manual inspection)
2. **Fallback**: Browserbase (cloud, better stealth)
3. **Last Resort**: Manual script writing (no live inspection)

### Common Failures

**Playwright Connection Issues**
```
Error: "Playwright server not responding"
Solution: Switch to Browserbase immediately
```

**Bot Detection / Captcha**
```
Error: Access denied or captcha
Solution: Browserbase with stealth mode + 2-3s delays
```

**Empty Results**
```
Error: 0 dealers extracted
Solution: Re-inspect DOM, verify search executed, adjust waits
```

**Timeout Errors**
```
Error: Page load timeout (30s)
Solution: Increase to 60s or use Browserbase
```

**Malformed Data**
```
Error: 50%+ missing phones
Solution: Re-inspect DOM, update selectors
```

### Recovery Protocol

- First error → Debug 5 min max
- Still failing → Switch to Browserbase
- Browserbase fails → Skip, continue, revisit later

### Browserbase Setup

```bash
# .env
BROWSERBASE_API_KEY=your_key_here
BROWSERBASE_PROJECT_ID=your_project_here

# Update scraper mode
scraper = ScraperFactory.create("Tesla", mode=ScraperMode.BROWSERBASE)
```

---

## OEM Priority Order

### Phase 1: High-Value (2 hours)
1. Tesla Powerwall (premium battery)
2. Enphase (microinverter specialists)

### Phase 2: Core Revenue (4 hours)
3. Generac (re-validate 310 ZIPs)
4. SolarEdge (major inverter brand)
5. Cummins (re-validate 310 ZIPs)
6. Briggs & Stratton (re-validate 310 ZIPs)

### Phase 3: HVAC Expansion (3 hours)
7. Mitsubishi (VRF/commercial)
8. Carrier (re-validate 310 ZIPs)
9. Trane (full production run)
10. York (re-validate 310 ZIPs)
11. Lennox (first production run)
12. Rheem (needs integration)

### Phase 4: Solar/Inverter (2-3 hours)
13. Fronius (Austrian inverters)
14. SMA Solar (re-validate 310 ZIPs)
15. GoodWe (Chinese inverters)
16. Growatt (storage + inverters)

### Phase 5: Final Brands (2 hours)
17. Kohler (premium generators)
18. SimpliPhi (battery storage)

---

## Output Management

### Per-Scraper Format

```
output/oem_data/{oem_name}/
├── {oem_name}_all_zips_20251101.csv      # Raw 310 ZIPs
├── {oem_name}_deduped_20251101.csv       # Phone-deduplicated
├── {oem_name}_checkpoint_20251101.json   # Resume data
└── logs/{oem_name}_production_20251101.log
```

### Naming Convention

```
{oem_name}_all_zips_{YYYYMMDD}.csv

Examples:
- tesla_all_zips_20251101.csv
- enphase_all_zips_20251101.csv
- generac_all_zips_20251101.csv
```

### Monitoring

```bash
tail -f output/logs/tesla_production_20251101.log
```

Watch for: "Completed 45/310 ZIPs (14.5%)"

### End-of-Day Aggregation

```bash
python3 scripts/aggregate_all_oems.py \
  --date 20251101 \
  --output grandmaster_list_full_20251101.csv
```

### Expected Output

1. **Per-OEM CSVs**: 18 files, 500-3,000 contractors each
2. **Grandmaster**: 20,000-30,000 unique contractors (deduplicated)
3. **Multi-OEM Analysis**: Contractors in 2-3+ networks
4. **ICP Scoring**: Coperniq algorithm applied to all

### Disk Space

- Estimated: 500 MB CSVs + 100 MB logs
- Check free space before starting

### Backup

- Git commit extraction scripts only
- Output CSVs stay local (gitignored)
- Consider external backup after completion

---

## Success Criteria

✅ All 18 scrapers complete extraction scripts
✅ All 18 scrapers pass 3-ZIP tests
✅ All 18 scrapers execute full 310-ZIP production runs
✅ Grandmaster list aggregated with 20K-30K contractors
✅ No showstopper errors blocking completion

---

## Next Steps After Completion

1. Multi-OEM cross-reference (identify 2-3+ brand contractors)
2. ICP scoring with Coperniq algorithm
3. Multi-state license cross-reference
4. Apollo enrichment (employee count, revenue)
5. Close CRM import

---

**Ready to execute.**
