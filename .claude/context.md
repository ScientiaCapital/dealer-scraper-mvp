# Project: Dealer Scraper MVP - State License Expansion
Last Updated: 2025-11-19 (Evening Session)

## Current Sprint/Focus: STRATEGIC PIVOT - County-Level AHJ Licensing

### CRITICAL FINDING - Nov 19, 2025

**STATE-LEVEL LICENSING IS INCOMPLETE FOR MEP CONTRACTORS!**

Both NJ and NY license MEP contractors (HVAC, Plumbing, Electrical) at the **COUNTY/MUNICIPAL level**, not state level. This fundamentally changes our approach.

## What Was Completed Today

### New Jersey Research
- ✅ Scraped NJ MyLicense portal (newjersey.mylicense.com)
- ✅ Found 25 Electrical Contractors (BUSINESS portal)
- ✅ Discovered PERSON vs BUSINESS portal distinction
- ❌ **HVACR returns ONLY CE Sponsors** (Continuing Education providers), NOT actual contractors
- ❌ **Master Plumbers database is EMPTY** (42 pages, all empty)
- ✅ Dumped all 53 profession options (both portals identical)
- ✅ Explored RGB portal (rgbportal.dca.njoag.gov) - wrong data (business registrations, not contractor licenses)

### New York Research
- ✅ Confirmed NY has NO unified statewide contractor licensing
- ✅ **NYC DOB portal is JACKPOT!** (a810-bisweb.nyc.gov)
- ✅ Found comprehensive license types:
  - A) ELECTRICAL CONTRACTOR
  - P) MASTER PLUMBER
  - O) OIL BURNER INSTALLER (HVAC heating)
  - F) FIRE SUPPRESSION CONTRACTOR
  - G) GENERAL CONTRACTOR
  - K) ENERGY AUDITOR / RETRO-COMMISSION AGENT

### Scripts Created
- `scripts/scrape_new_jersey.py` - NJ BUSINESS portal scraper with pagination
- `scripts/scrape_nj_persons.py` - NJ PERSON portal scraper
- `scripts/dump_all_nj_professions.py` - Dumps all profession options
- `scripts/explore_rgb_portal.py` - RGB portal explorer
- `scripts/explore_nyc_dob.py` - NYC DOB portal explorer
- `scripts/explore_county_ahjs.py` - County-level AHJ research script (READY TO RUN)
- `scripts/convert_portal_excel.py` - Excel to CSV converter

### Output Files Created
- `output/state_licenses/new_jersey/professions_person.json`
- `output/state_licenses/new_jersey/professions_business.json`
- `output/state_licenses/new_york/nyc_dob/page_content.html`
- `output/state_licenses/new_jersey/nj_electrical_contractors_20251119.csv` (25 contractors)

## Key Insights

### State Licensing Structure (CRITICAL!)
1. **MEP contractors are licensed at COUNTY/MUNICIPAL level in NJ and NY**
2. State portals only have:
   - Continuing Education sponsors
   - Business registrations
   - Some specific professions (nursing, pharmacy, etc.)
3. **Strategy must pivot to AHJ (Authority Having Jurisdiction) portals**

### Wealthy County Targets Identified (Top 10)
**New York:**
- Nassau County ($130K median income)
- Westchester County ($110K) - has known trade license search
- Putnam County ($100K)
- Suffolk County ($95K)

**New Jersey:**
- Hunterdon County ($126K)
- Somerset County ($123K)
- Morris County ($120K)
- Bergen County ($110K)
- Monmouth County ($106K)

## Next Steps for Tomorrow

### IMMEDIATE PRIORITY (Do First!)
1. **Run `scripts/explore_county_ahjs.py`** - Systematically research all 10 wealthy county portals
2. **Identify which AHJs have online searchable contractor databases**
3. **Focus on Westchester County first** (known trade license search at consumer.westchestergov.com)

### NYC DOB Scraper (High Value)
1. Build scraper for NYC DOB portal (a810-bisweb.nyc.gov)
2. Target license types: ELECTRICAL CONTRACTOR, MASTER PLUMBER, OIL BURNER INSTALLER, FIRE SUPPRESSION, GENERAL CONTRACTOR, ENERGY AUDITOR
3. Search by business name (iterate through alphabet)

### County-Level Strategy
1. For each wealthy county with searchable database:
   - Explore portal structure
   - Identify license types available
   - Build scraper
2. Combine county data into unified dataset
3. Deduplicate across counties (contractors may be licensed in multiple)

## Architecture Notes

### ASP.NET Pagination Pattern (NJ)
```python
postback_target = f"datagrid_results$_ctl44$_ctl{page_num - 2}"
await page.evaluate(f"__doPostBack('{postback_target}', '')")
```

### License Number Patterns
- NJ Electrical: `34XX########`
- NJ Home Improvement: `13VH########`
- NYC varies by license type

### Portal Types
- **PERSON portal**: Individual licenses (Master Plumber, HVACR person)
- **BUSINESS portal**: Business/firm licenses (Electrical Contractor firm)

## Files to Review Tomorrow
- `output/state_licenses/new_york/nyc_dob/page_content.html` - NYC DOB structure
- `output/state_licenses/new_jersey/professions_*.json` - Available professions
- `scripts/explore_county_ahjs.py` - Ready to run for county research
