# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

**Coperniq Partner Prospecting System** - Automated contractor lead generation for Coperniq's brand-agnostic monitoring platform.

**Business Context**:
- **Who**: Sr. BDR at Coperniq.io targeting multi-brand contractors
- **Target**: "Resimercial" contractors (residential + commercial) who install generators, solar, and batteries
- **Geography**: SREC states (CA, TX, PA, MA, NJ, FL) - sustainable markets post-ITC expiration
- **Urgency**: Federal ITC deadlines (residential Dec 2025, commercial Q2 2026)
- **Unique Value**: Coperniq is the only brand-agnostic monitoring platform for microinverters + batteries + generators

**Current Status** (as of Oct 28, 2025):
- ✅ 18 OEM scrapers (all production-ready with registration + extraction scripts)
- ✅ **Enhanced deduplication system** (97.3% accuracy on 25,800 records!)
- ✅ **Grandmaster list**: 3,242 unique contractors from 5 OEMs
- ✅ Multi-OEM cross-reference detector (114 crossover contractors identified)
- ✅ SREC state filtering (15 states: CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
- ✅ Year 1 GTM-aligned ICP scoring (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)
- ✅ Generic scraper pattern for scalable OEM additions
- ✅ Multi-OEM production script (`scripts/run_multi_oem_scraping.py`)
- ✅ Playwright local automation (primary scraping mode)
- ✅ HVAC OEM expansion started (Mitsubishi Diamond Commercial VRF contractors - 90% complete)
- ⏳ RunPod cloud deployment (infrastructure ready, not primary yet)
- ⏳ Apollo enrichment integration (API key TBD)
- ⏳ Close CRM import (API key TBD)

## Architecture

### Multi-OEM Scraper Framework

**Base Classes** (`scrapers/base_scraper.py`):
- `BaseDealerScraper`: Abstract base class for all OEM scrapers
- `StandardizedDealer`: Unified data structure across OEMs (15 core fields + enrichment fields)
- `DealerCapabilities`: Tracks product/trade/business capabilities
- `ScraperMode`: PLAYWRIGHT (manual MCP) | RUNPOD (automated cloud) | BROWSERBASE (future)

**OEM-Specific Scrapers** (18 total, all registered with factory):
1. `GeneracScraper` - Backup generators (custom navigation)
2. `TeslaScraper` - Powerwall batteries (custom navigation)
3. `EnphaseScraper` - Microinverters (custom navigation)
4. `SolarEdgeScraper` - Solar inverters (custom navigation)
5. `BriggsStrattonScraper` - Backup generators (generic scraper)
6. `CumminsScraper` - Backup generators (generic scraper)
7. `KohlerScraper` - Backup generators (generic scraper)
8. `FroniusScraper` - Solar inverters (generic scraper)
9. `SMAScraper` - Solar inverters (generic scraper)
10. `SolArkScraper` - Hybrid inverters (generic scraper)
11. `GoodWeScraper` - Solar inverters (generic scraper)
12. `GrowattScraper` - Solar inverters (generic scraper)
13. `SungrowScraper` - Solar inverters (generic scraper)
14. `ABBScraper` - Solar inverters (generic scraper)
15. `DeltaScraper` - Solar inverters (generic scraper)
16. `TigoScraper` - Solar optimizers (generic scraper)
17. `SimpliPhiScraper` - Battery storage (generic scraper)
18. `MitsubishiScraper` - VRF/HVAC systems (generic scraper, HIGHEST PRIORITY)

All scrapers have registration code and extraction scripts. Custom navigation logic exists for top 4 OEMs; others use generic scraper pattern. **Mitsubishi Diamond Commercial** targets VRF contractors (resimercial signal).

**Factory Pattern** (`scrapers/scraper_factory.py`):
```python
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Create scraper by name (any of 17 registered OEMs)
generac = ScraperFactory.create("Generac", mode=ScraperMode.PLAYWRIGHT)
tesla = ScraperFactory.create("Tesla", mode=ScraperMode.PLAYWRIGHT)
briggs = ScraperFactory.create("Briggs & Stratton", mode=ScraperMode.PLAYWRIGHT)

# All scrapers auto-register on import
# See run_multi_oem_scraping.py for registration pattern
```

### Cross-Reference & Targeting

**Enhanced Deduplication System** (`scrapers/base_scraper.py`) ⭐ NEW:
- **97.3% accuracy** on 25,800 Cummins records!
- Multi-signal matching hierarchy:
  1. **Phone normalization** (96.5% of duplicates): Strip to 10 digits, remove country code
  2. **Domain matching** (0.7% additional): Extract root domain, case-insensitive
  3. **Fuzzy name matching** (0.1% additional): 85% similarity threshold + same state
- New methods:
  - `normalize_company_name()`: Standardizes business names for comparison
  - `deduplicate_by_phone()`: Enhanced multi-signal deduplication
- Test with: `python3 scripts/test_dedup_enhancement.py`

**Multi-OEM Detection** (`analysis/multi_oem_detector.py`):
- Identifies contractors certified with 2-3 OEM brands (highest value prospects)
- Primary matching: Phone number (normalized to digits only)
- Secondary matching: Domain (root domain after removing www/subdomains)
- Tertiary validation: Fuzzy company name matching (high threshold to avoid false positives)
- Confidence scoring: 100% (all signals), 90% (phone + domain OR phone + name), 80% (phone only)
- Multi-OEM score: 3+ OEMs = 100pts, 2 OEMs = 50pts, 1 OEM = 25pts
- **Current results**: 114 multi-OEM contractors (4 triple, 110 dual)

**SREC State Filter** (`targeting/srec_itc_filter.py`):
- Filters to states with Solar Renewable Energy Credit programs (sustainable post-ITC)
- HIGH priority: CA, TX, PA, MA, NJ, FL (primary focus)
- MEDIUM priority: OH, MD, DC, DE, NH, RI, CT, IL
- ITC urgency levels:
  - CRITICAL: Commercial projects (must start by June 30, 2026 for safe harbor)
  - HIGH: Residential (ITC expires December 31, 2025)
  - MEDIUM: SREC states (sustainable market post-ITC)
  - LOW: Non-SREC states

**ICP Filter** (`targeting/icp_filter.py`):
- Year 1 GTM-aligned multi-dimensional 0-100 scoring:
  1. **Resimercial (35%)**: Both residential + commercial (scaling $5-10M → $50-100M contractors)
  2. **Multi-OEM (25%)**: Managing 3-4+ platforms = core pain point
  3. **MEP+R (25%)**: Self-performing multi-trade = platform power users, blue ocean market
  4. **O&M (15%)**: Operations & maintenance (platform features maturing in Year 2)
- ICP Tiers: PLATINUM (80-100), GOLD (60-79), SILVER (40-59), BRONZE (<40)
- Ideal ICP Flag: All 4 dimensions ≥ 70% (resimercial) or ≥ 50% (multi-OEM, MEP+R)

### Execution Modes

**PLAYWRIGHT Mode** (Primary Production Mode):
- Local Playwright automation via `run_multi_oem_scraping.py`
- Supports all 17 OEMs with custom + generic scraper patterns
- Automated 6-step workflow per ZIP code:
  1. Navigate to dealer locator URL
  2. Accept cookies (if needed)
  3. Fill ZIP code into search input
  4. Click search button
  5. Wait for AJAX results (3-5 seconds)
  6. Execute JavaScript extraction script
- Performance: ~5-6 seconds per ZIP code
- Cost: Free (local compute)
- Current Usage: 140 ZIPs × 17 OEMs = 2,380 scrapes (~3.5-4 hours total)

**RUNPOD Mode** (Cloud Alternative - Infrastructure Ready):
- Serverless Playwright via HTTP API (see `runpod-playwright-api/`)
- Singleton browser pattern for 2s faster startup
- Auto-scales 0→N workers (pay-per-second, ~$0.001 per ZIP)
- Status: Deployed but not primary mode yet
- Requires: `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` in .env

**BROWSERBASE Mode** (Future):
- Alternative cloud browser option
- Placeholder exists but not implemented

## Data Schema

### StandardizedDealer (Core Fields)

```python
{
  # Core identification
  "name": str,
  "phone": str,
  "domain": str,
  "website": str,

  # Location
  "street": str,
  "city": str,
  "state": str,
  "zip": str,
  "address_full": str,

  # Quality signals
  "rating": float,           # 0-5 scale
  "review_count": int,
  "tier": str,               # OEM-specific tier (Premier, Platinum, etc.)
  "certifications": List[str],

  # Distance
  "distance": str,           # "8.3 mi"
  "distance_miles": float,   # 8.3

  # OEM source
  "oem_source": str,         # "Generac", "Tesla", "Enphase"
  "scraped_from_zip": str,

  # Enrichment (populated later)
  "apollo_enriched": bool,
  "employee_count": int,
  "estimated_revenue": str,
  "linkedin_url": str,

  # Coperniq scoring
  "coperniq_score": int,           # 0-100 total
  "multi_oem_score": int,          # 0-100 (from multi-OEM presence)
  "srec_state_priority": str,      # "HIGH", "MEDIUM", "LOW"
  "itc_urgency": str,              # "CRITICAL", "HIGH", "MEDIUM", "LOW"
}
```

### DealerCapabilities

```python
{
  # Product capabilities
  "has_generator": bool,
  "has_solar": bool,
  "has_battery": bool,
  "has_microinverters": bool,
  "has_inverters": bool,

  # Trade capabilities
  "has_electrical": bool,
  "has_hvac": bool,
  "has_roofing": bool,
  "has_plumbing": bool,

  # Business characteristics
  "is_commercial": bool,
  "is_residential": bool,
  "is_gc": bool,                    # General contractor
  "is_sub": bool,                   # Specialized sub

  # OEM certifications (populated by multi-OEM detector)
  "oem_certifications": Set[str],   # {"Generac", "Tesla", "Enphase"}
  "capability_count": int,          # Total capabilities (for scoring)
}
```

## Configuration

### SREC State ZIP Codes (config.py)

**California** (15 ZIPs):
- SF Bay Area: 94102, 94301, 94022, 94024, 94027
- Los Angeles: 90001, 90210, 90265, 91101
- San Diego: 92101, 92037, 92067
- Sacramento: 95814, 95819
- Orange County: 92660, 92625, 92657

**Texas** (15 ZIPs):
- Houston: 77002, 77019, 77024, 77005, 77056
- Dallas: 75201, 75205, 75225, 75229
- Austin: 78701, 78746, 78733, 78730
- San Antonio: 78201, 78209
- Fort Worth: 76102, 76107

**Pennsylvania**, **Massachusetts**, **New Jersey**, **Florida**, **New York**, **Ohio**, **Maryland**, **DC**, **Delaware**, **New Hampshire**, **Rhode Island**, **Connecticut**, **Illinois**: Similar coverage of major metros + wealthy suburbs

**Wealthy ZIP Targeting Strategy**:
- All 140 ZIPs selected based on 2024-2025 Census ACS data (American Community Survey)
- Criteria: $150K-$250K+ median household income, high property values
- Rationale: Solar/battery/generator buyers in $40K-$80K+ system price range
- Examples: Old Greenwich CT ($826K avg), Kenilworth IL ($460K avg), Terrace Park OH ($292K avg)

**Combined**: `ZIP_CODES_SREC_ALL` (140 ZIPs total across 15 SREC states)

### Environment Variables (.env.example)

```bash
# Scraping
RUNPOD_API_KEY=your_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_here

# Enrichment (Future)
APOLLO_API_KEY=your_key_here
CLAY_WEBHOOK_URL=your_url_here

# CRM (Future)
CLOSE_API_KEY=your_key_here

# Outreach Automation (Future)
# SENDGRID_API_KEY, TWILIO_*, etc.
```

## Production Usage

### 17-OEM Multi-Brand Scraping (Current Production)

**Run comprehensive scrape across all 17 OEMs**:
```bash
python3 -u scripts/run_multi_oem_scraping.py \
  --oems Generac "Briggs & Stratton" Cummins Kohler Enphase \
         Fronius SolarEdge SMA Sol-Ark GoodWe Growatt \
         Sungrow ABB Delta Tigo Tesla SimpliPhi \
  --states CA TX PA MA NJ FL NY OH MD DC DE NH RI CT IL \
  2>&1 | tee output/multi_oem_production.log
```

**Performance**:
- 140 ZIPs × 17 OEMs = 2,380 scrapes
- ~5-6 seconds per ZIP code
- Total time: ~3.5-4 hours
- Cost: $0 (local Playwright)

**Output Files**:
1. `output/multi_oem_deduped_YYYYMMDD.csv` ← Raw scraped data (all dealers)
2. `output/multi_oem_crossover_YYYYMMDD.csv` ← Multi-OEM matches (3-4+ brands)
3. `output/icp_analysis_YYYYMMDD.csv` ← ICP-scored contractors (PLATINUM/GOLD/SILVER/BRONZE)

### Quick Test Run (Single State, Few ZIPs)

```bash
python3 -u scripts/run_multi_oem_scraping.py \
  --oems Generac Tesla Enphase \
  --states CA --limit-zips 3
```

### Lead Generation Flow

```
1. Scrape dealers from SREC state ZIPs
   ↓
2. Deduplicate by phone number
   ↓
3. Convert to MultiOEMMatch format (single-OEM for MVP)
   ↓
4. Filter to SREC states only
   ↓
5. Tag with ITC urgency
   ↓
6. Score with Coperniq algorithm (0-100)
   ↓
7. Export CSV sorted by score (HIGH first)
```

## Testing

### Validated Results

Generac scraper tested across 3 metros:
- Milwaukee (53202): 59 dealers
- Chicago (60601): 59 dealers
- Minneapolis (55401): 28 dealers

Performance: ~5-6 seconds per ZIP code

### Known Issues

**Address Parsing** (Low Priority):
- Dealers with 0 reviews have corrupted street addresses
- Example: `"3 mi0.0(0)0.0 out of 5 stars.   7816 frontage rd"`
- Should be: `"7816 frontage rd"`
- Location: extraction.js lines 72-74
- Impact: ~60% of dealers (those with no reviews)
- Status: Data still usable, can be cleaned with regex if needed

## Future Development

### Immediate Next Steps

1. **Tesla Powerwall Scraper**:
   - URL: https://www.tesla.com/support/certified-installers-powerwall
   - Status: Structure ready, needs extraction script (manual site inspection required)
   - Use PLAYWRIGHT mode to inspect DOM and write extraction.js logic

2. **Enphase Installer Scraper**:
   - URL: https://enphase.com/installer-locator
   - Status: Structure ready, needs extraction script (manual site inspection required)
   - Same process as Tesla

3. **Multi-OEM Cross-Referencing**:
   - Once Tesla + Enphase scrapers are working, run `MultiOEMDetector`
   - Find contractors in 2-3 networks (highest value prospects)
   - Example: Contractor certified for Generac + Tesla + Enphase = score of 100/100 on multi-OEM dimension

### Medium-Term Enhancements

4. **Apollo Enrichment**:
   - Add `APOLLO_API_KEY` to .env
   - Enrich with employee count, revenue, LinkedIn
   - Improves commercial capability scoring (20 pts)

5. **Close CRM Import**:
   - Add `CLOSE_API_KEY` to .env
   - Bulk import leads
   - Auto-create Smart Views by:
     - OEM presence (3+ OEMs, 2 OEMs, 1 OEM)
     - SREC state (CA, TX, PA, MA, NJ, FL)
     - Priority tier (HIGH, MEDIUM, LOW)

6. **Clay Automation**:
   - Add `CLAY_WEBHOOK_URL` to .env
   - Advanced enrichment waterfall

### Long-Term (10x BDR Goal)

7. **Outreach Automation**:
   - Email sequences (SendGrid/Mailgun)
   - SMS campaigns (Twilio)
   - AI agent testing (future)

## Market Context

### Federal ITC Deadlines

- **Residential ITC**: Expires December 31, 2025 (30% tax credit ends)
- **Commercial Safe Harbor**: Projects must start by June 30, 2026 to claim ITC
- Creates urgency for contractors to close deals before deadlines

### SREC States (Sustainable Post-ITC)

States with Solar Renewable Energy Credit programs that continue after federal ITC expires:
- **CA**: SGIP (Self-Generation Incentive Program) + NEM 3.0
- **TX**: Deregulated market + ERCOT arbitrage opportunities
- **PA**: PA Solar Renewable Energy Credits (SRECs)
- **MA**: SREC II + SMART Program
- **NJ**: NJ Transition Renewable Energy Certificates (TRECs)
- **FL**: Net metering + property tax exemptions

### Coperniq's Unique Value

**Problem**: Contractors managing multiple brands need 3+ separate monitoring platforms:
- Enphase Enlighten (microinverters)
- Tesla app (Powerwall batteries)
- Generac Mobile Link (generators)
- Each has different UI, login, customer experience

**Solution**: Coperniq is the **only** brand-agnostic monitoring platform
- Single dashboard for microinverters + batteries + generators
- Unified customer experience
- Production + consumption monitoring

**Target**: Multi-brand contractors (2-3 OEMs) = highest value prospects
- They feel the pain most acutely (managing 3+ platforms)
- Larger customer bases (certified across multiple brands)
- More sophisticated businesses (investment in multiple certifications)

## Tips for Claude Code

1. **Multi-OEM scrapers**: Tesla + Enphase need extraction scripts filled in
   - Use PLAYWRIGHT mode with `browser_snapshot` to inspect DOM
   - Write extraction logic similar to Generac's tested script
   - Test on 1-2 ZIPs before scaling

2. **API keys**: All API keys go in `.env` (git-ignored)
   - Never hardcode in source files
   - Use `os.getenv()` to load

3. **Testing changes**: Use `--limit-zips 1` or `--limit-zips 3` for fast testing

4. **Scoring adjustments**: Coperniq scoring weights are in `targeting/coperniq_lead_scorer.py`
   - Adjust dimension weights if needed (currently 40/20/20/10/10)

5. **SREC states**: ZIP code lists in `config.py`
   - Add/remove ZIPs per state as needed
   - Focus on major metros + wealthy suburbs

6. **Commit messages**: Use detailed messages like existing commits
   - Include business context (why) not just technical changes (what)
