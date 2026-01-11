# Project Context - Dealer Scraper MVP

**Last Updated**: 2025-12-31
**Branch**: main (merged from feature/sprint-dec27)

## Done (This Session - Dec 31)

### Kohler Scraper Production Run
- ✅ Fixed infinite retry loop for empty ZIPs
- ✅ Scraped 410 dealers from 374 ZIPs
- ✅ Imported to SQLite (377 new contractors)
- ✅ Pushed to Supabase scraper_imports

### Trane Scraper
- ✅ Built Browserbase extraction script
- ✅ Extracted 2,826 dealers from directory
- ✅ Imported to SQLite (2,800 new contractors)
- ✅ Pushed to Supabase scraper_imports

### TX License Data
- ✅ Downloaded 943K TDLR records from Texas Open Data Portal
- ✅ Filtered to 55K ICP-relevant licenses (A/C, Electrical contractors)
- ✅ Validated 32,645 real businesses (excluded individuals)
- ✅ Pushed to Supabase with HVAC/Electrical tags

### Supabase Integration
- ✅ Total records in scraper_imports: 35,881
  - TX License: 32,645
  - Trane OEM: 2,826
  - Kohler OEM: 410

## Blockers Encountered
- TX TDLR data has no email field - sales-agent needs Hunter/Apollo enrichment
- Some Browserbase WebSocket 500 errors (transient, retry works)

## Decisions Made
1. **TX Individual Filtering**: Used name pattern detection to filter out "LASTNAME, FIRSTNAME" records
2. **OEM Tagging**: Tagged TX records with HVAC/Electrical based on license type
3. **Batch Size**: 100 records per Supabase push to avoid timeouts

## Tomorrow's Priorities
1. [ ] Enrich TX contractors with Hunter/Apollo for emails/domains
2. [ ] Run more OEM scrapers (York, Carrier, Lennox)
3. [ ] Cross-reference TX licenses with OEM dealer data
4. [ ] Test sales-agent CRM pipeline with new data

## Architecture Notes
- SQLite: `output/pipeline.db` for local processing
- Supabase: `scraper_imports` table for CRM pipeline
- Browserbase: Cloud browser for JS-heavy sites (Trane, etc.)
- Patchright: Stealth browser for bot-detection sites (Kohler)

## Key Files Modified
- `database/schema.sql` - Added dealer_enrichments table, is_individual column
- `scripts/kohler_master_scraper.py` - Fixed retry loop bug
- `scripts/trane_extract_browserbase.py` - New Browserbase extractor
- `scripts/filter_tx_individuals.py` - TX individual detection

## Data Files (not in git)
- `data/raw/tx_tdlr_all_licenses.csv` (943K records, 110MB)
- `data/raw/tx_icp_contractors.csv` (56K filtered)
- `output/kohler/kohler_dealers_export.csv` (410 records)
- `output/trane/trane_dealers.json` (2,826 records)
