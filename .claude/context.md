# Project: Dealer Scraper MVP - State License Acquisition
Last Updated: 2025-11-19

## Current Sprint/Focus - New Jersey State License Scraper
- [x] Research NJ MyLicense portal structure (ASP.NET WebForms)
- [x] Build production scraper with proper pagination support
- [x] Add all 4 MEP+Energy professions
- [x] Run full production scrape
- [x] Verify data quality (821 active Electrical Contractors extracted!)
- [ ] Re-run Home Improvement with full pagination
- [ ] Investigate Master Plumbers and HVACR (0 results issue)
- [ ] Implement multi-license detection (self-performing contractors)
- [ ] Replicate pattern to Maryland

## Architecture Overview

### NJ Scraper Breakthrough
- **Framework**: Python + Playwright (local automation)
- **Portal**: https://newjersey.mylicense.com/verification/Search.aspx?facility=Y
- **Key Challenge**: ASP.NET WebForms pagination with __doPostBack
- **Solution**: Direct JavaScript execution + raw HTML regex parsing

### Technical Pattern (Reusable for Other States)
1. **HTML Extraction**: Use `page.content()` to get raw HTML (JavaScript DOM queries fail on NJ's non-standard tables)
2. **Regex Parsing**: Python regex on raw HTML finds contractor records
3. **ASP.NET Pagination**: Execute `__doPostBack('datagrid_results$_ctl44$_ctl{N}','')` where N = page_num - 2
4. **Fresh Sessions**: New browser per profession to avoid rate limiting
5. **Error Handling**: Continue on timing errors (page.content() during navigation)

## Recent Changes (2025-11-19)

### Major Breakthrough: NJ Pagination Working! 🎉
- **Results**:
  - ✅ **821 active Electrical Contractors** across 42 pages (COMPLETE)
  - ✅ **14 Home Improvement Contractors** (partial - page 1 only, needs re-run)
  - ❌ **0 Master Plumbers** (needs investigation)
  - ❌ **0 HVACR** (needs investigation)

### Key Insights Gained
1. **Self-Performing Contractors = Highest Value**: Contractors with multiple trade licenses (appearing in 2+ profession lists) are the most valuable targets
2. **Quality Over Speed**: "there is 'Gold in them Hills of NJ' claude" - get it right
3. **Project Focus**: This project handles data acquisition ONLY - enrichment happens in separate `sales-agent` project

## Next Steps

### Immediate
1. Re-run Home Improvement Contractors with full pagination
2. Investigate Master Plumbers and HVACR (0 results issue)
3. Implement multi-license detection script

### Short-Term
4. Document NJ scraper pattern in reusable template
5. Replicate pattern to Maryland

## File Locations
- Production: `scripts/scrape_new_jersey.py`
- Output: `output/state_licenses/new_jersey/nj_electrical_contractors_20251119.csv` (821 contractors)
- Logs: `output/nj_proper_pagination_test.log`
