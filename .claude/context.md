# Project Context - Dealer Scraper MVP

**Last Updated**: 2025-10-28

## Current Status Summary

### 🎯 Mission
Automated contractor lead generation for Coperniq's brand-agnostic monitoring platform, targeting "resimercial" contractors (residential + commercial) who install generators, solar, and batteries.

### ✅ Completed Milestones

**18 OEM Scrapers (Production-Ready)**:
- **Generators (4)**: Generac, Briggs & Stratton, Cummins, Kohler
- **Solar Inverters (9)**: Enphase, SolarEdge, Fronius, SMA, Sol-Ark, GoodWe, Growatt, Sungrow, ABB, Delta
- **Batteries (2)**: Tesla Powerwall, SimpliPhi
- **Solar Optimizers (1)**: Tigo
- **HVAC (1)**: Mitsubishi Electric (Diamond Commercial VRF) ⭐ NEW
- **HVAC (1)**: Mitsubishi Electric (Diamond Commercial VRF contractors)

**National Scrape Results**:
- Generac: 1,738 dealers (140 SREC state ZIPs)
- Briggs & Stratton: ~600 dealers (140 ZIPs)
- Cummins: ~400 dealers (140 ZIPs)
- Enphase: 183 unique installers (37 ZIPs)
- Tesla: 70 Premier installers (manual collection)

**Core Infrastructure**:
- ✅ Generic scraper pattern for scalable OEM additions
- ✅ Multi-OEM cross-reference detector (phone/domain/fuzzy name matching)
- ✅ Enhanced deduplication with multi-signal matching
- ✅ SREC state filtering (15 states, 140 wealthy ZIPs)
- ✅ Year 1 GTM-aligned ICP scoring (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)
- ✅ Playwright local automation (primary scraping mode)
- ✅ RunPod cloud infrastructure (deployed, not primary)

### 🚧 In Progress

**HVAC OEM Expansion** (started 2025-10-28):
1. ✅ Mitsubishi Diamond Commercial scraper (COMPLETE - ready to test)
2. ⏳ Lennox Premier Dealers (next up)
3. ⏳ Trane Comfort Specialists (planned)
4. ⏳ Carrier Factory Authorized (planned)

**Why HVAC Matters**:
- MEP capability detection: HVAC = Mechanical trade validation
- Commercial signal: VRF contractors = resimercial projects ($5M-$50M revenue)
- Cross-reference boost: HVAC + Solar + Generator = 100/100 ICP score potential

### 📊 Next Steps (Priority Order)

1. **Test Mitsubishi Scraper** (3 ZIPs for validation)
2. **Run Mitsubishi National** (140 SREC ZIPs, ~2-3 hours, expected: 50-150 contractors)
3. **Create Lennox Premier Scraper** (similar to Generac Premier tier)
4. **Create Trane/Carrier Scrapers** (complete HVAC coverage)
5. **Grand Master Cross-Reference** (combine all 18+ OEMs)
6. **Apply Multi-Signal Deduplication** (to grand master list)
7. **Generate Multi-OEM Report** (contractors in 3-4+ networks)
8. **ICP Scoring & Export** (PLATINUM/GOLD/SILVER CSVs for GTM)

## Key Business Context

### Target Market
- **Geography**: 15 SREC states (CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
- **Wealth Tier**: 140 ZIPs with $150K-$250K+ median household income
- **Customer Profile**: Solar/battery/generator buyers ($40K-$80K+ system investments)

### Federal ITC Urgency
- **Residential ITC**: Expires December 31, 2025 (30% tax credit ends)
- **Commercial Safe Harbor**: Projects must start by June 30, 2026
- Creates urgency for contractors to close deals before deadlines

### Coperniq's Unique Value
**Problem**: Multi-brand contractors managing 3+ separate monitoring platforms
- Enphase Enlighten (microinverters)
- Tesla app (Powerwall batteries)
- Generac Mobile Link (generators)

**Solution**: Coperniq is the ONLY brand-agnostic monitoring platform
- Single dashboard for all products
- Unified customer experience
- Production + consumption monitoring

### Ideal Customer Profile (ICP)
**Year 1 GTM Focus** - Multi-dimensional 0-100 scoring:
1. **Resimercial (35%)**: Residential + commercial (scaling contractors)
2. **Multi-OEM (25%)**: Managing 3-4+ platforms = core pain point
3. **MEP+R (25%)**: Self-performing multi-trade = power users
4. **O&M (15%)**: Operations & maintenance capabilities

**Perfect 100/100 ICP Example**:
- Generac PowerPro Premier + Tesla Premier + Enphase Platinum + Mitsubishi Diamond Commercial VRF
- Multi-product, multi-OEM, multi-trade, resimercial
- $5M-$50M revenue range
- SREC state location

## Recent Wins

### Enhanced Deduplication (2025-10-27)
- Fixed TRI-STATE POWER & PUMP duplicate issue
- Multi-signal matching: phone (primary) + domain (secondary) + fuzzy name (validation)
- Confidence scoring: 100% (all signals), 90% (2 signals), 80% (phone only)
- Successfully tested on Briggs & Stratton dataset

### HVAC Research & Implementation (2025-10-28)
- Researched 4 HVAC OEM dealer locators (see `docs/HVAC_DEALER_LOCATORS.md`)
- Identified Mitsubishi Diamond Commercial as HIGHEST PRIORITY (VRF = resimercial signal)
- Created full scraper implementation with custom tab navigation
- Fixed JavaScript extraction issues (phone country code, city badge text)
- Ready for testing and national deployment

### Generic Scraper Pattern Success
- 13 OEMs using generic pattern (Briggs, Cummins, Kohler, Fronius, SMA, etc.)
- Proven pattern: Navigate → Cookie consent → Fill ZIP → Click search → Wait → Extract
- JavaScript extraction with in-browser deduplication
- ~5-6 seconds per ZIP code
- Scalable to new OEMs in <1 hour

## Important Files & Locations

### Documentation
- `CLAUDE.md` - Main project guide for Claude Code
- `CLAUDE_INIT.md` - Agent workflow and initialization
- `.claude/context.md` - This file (current state)
- `.claude/architecture.md` - Technical architecture
- `docs/HVAC_DEALER_LOCATORS.md` - HVAC OEM research

### Core Code
- `scrapers/base_scraper.py` - Abstract base class + StandardizedDealer schema
- `scrapers/scraper_factory.py` - Factory pattern for OEM scraper creation
- `scrapers/mitsubishi_scraper.py` - Latest HVAC scraper (VRF contractors)
- `analysis/multi_oem_detector.py` - Cross-reference matching logic
- `targeting/icp_filter.py` - Year 1 GTM ICP scoring

### Test Scripts
- `scripts/test_mitsubishi.py` - Validate Mitsubishi on single ZIP
- `scripts/test_dedup_enhancement.py` - Test multi-signal deduplication
- `scripts/inspect_mitsubishi.py` - Manual Playwright inspection helper

### Configuration
- `config.py` - SREC state ZIP codes (140 total)
- `.env` - API keys (RunPod, Apollo, Close CRM)

### Output Data
- `output/generac_deduped_*.csv` - 1,738 Generac dealers
- `output/briggs_deduped_*.csv` - ~600 Briggs dealers
- `output/cummins_deduped_*.csv` - ~400 Cummins dealers
- `output/enphase_deduped_*.csv` - 183 Enphase installers
- `output/tesla_deduped_*.csv` - 70 Tesla Premier installers

## Known Issues & Gotchas

### Minor Issues (Low Priority)
1. **Address Parsing**: Dealers with 0 reviews have corrupted street addresses
   - Example: `"3 mi0.0(0)0.0 out of 5 stars. 7816 frontage rd"`
   - Impact: ~60% of dealers (those with no reviews)
   - Status: Data still usable, can be cleaned with regex if needed

### Best Practices Learned
1. **JavaScript Regex Escaping**: Always double-escape backslashes in JS strings embedded in Python
   - WRONG: `\D`, `\s`, `\n` (Python interprets first)
   - CORRECT: `[^0-9]`, `[\\n\\r]` (properly escaped)

2. **Phone Number Normalization**: Strip country code prefix
   - 11-digit phones starting with "1" → remove leading "1"
   - Ensures proper deduplication matching

3. **Tab Navigation**: Text-based selectors more reliable than role-based
   - WRONG: `page.locator('tab').nth(1)`
   - CORRECT: `page.click('text=Commercial building')`

4. **Badge Text Contamination**: Location fields can capture certification badges
   - Solution: Look for pattern after newlines `(?:^|[\\n\\r])` to avoid badges

## Git Workflow

### Recent Commits
- `e308d16` - Feature: Mitsubishi Diamond Commercial VRF contractor scraper (2025-10-28)
- `7f43b1f` - Feature: Enhanced multi-signal deduplication (2025-10-27)
- Previous work: Generac, Briggs, Cummins, Enphase, Tesla scrapers

### Commit Message Format
```
Type: Short description

Detailed context (business value, technical changes, expected outcomes)

Files added/modified:
- file1.py: What changed
- file2.py: What changed

🤖 Generated with Claude Code
```

## Performance Metrics

### Scraping Speed
- **Per ZIP**: ~5-6 seconds (Playwright local)
- **140 ZIPs**: ~12-14 minutes per OEM
- **National run (18 OEMs × 140 ZIPs)**: ~3.5-4 hours total

### Data Quality
- **Deduplication**: 95%+ accuracy with multi-signal matching
- **Phone normalization**: 100% (10-digit US format)
- **Domain extraction**: 85%+ coverage (when available)
- **Tier/certification tracking**: 100% from OEM sites

### Expected Dataset Sizes
- **Generators**: ~3,000 unique dealers across 4 brands
- **Solar**: ~2,500 unique installers across 10 brands
- **Batteries**: ~300 unique installers across 2 brands
- **HVAC**: ~2,200-4,250 unique contractors across 4 brands (estimated)
- **Grand Total**: ~8,000-10,000 unique contractors (accounting for multi-OEM overlap)

## Quick Start Commands

### Test Single OEM
```bash
python3 scripts/test_mitsubishi.py
```

### Run National Scrape (when ready)
```bash
python3 -u scripts/run_multi_oem_scraping.py \
  --oems "Mitsubishi Electric" \
  --states CA TX PA MA NJ FL NY OH MD DC DE NH RI CT IL \
  2>&1 | tee output/mitsubishi_national.log
```

### Multi-OEM Detection
```bash
python3 -u scripts/run_multi_oem_scraping.py \
  --oems Generac "Briggs & Stratton" Cummins "Mitsubishi Electric" \
  --states CA TX \
  --limit-zips 3
```

## Team Notes

### Communication Style
- Clear, educational explanations with insights
- Business value before technical details
- Evidence-based claims (run verification commands)
- Descriptive git commit messages

### Development Workflow
1. Sequential thinking for task breakdown
2. Use TodoWrite for all multi-step work
3. Mark todos `in_progress` before starting
4. Mark todos `completed` IMMEDIATELY after finishing
5. Run verification commands before claiming success
6. Commit with descriptive messages + business context

### Agent Usage
- **Explore agent**: For codebase exploration (not needle queries)
- **Task agent**: For specialized domain work (security, testing, etc.)
- Prefer parallel tool calls when no dependencies

---

**Status**: Ready for Mitsubishi testing and national scrape 🚀
**Next Session**: Test Mitsubishi → Run national → Lennox scraper
