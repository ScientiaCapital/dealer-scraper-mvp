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

**Current Status (MVP)**:
- ✅ Generac dealer scraper (tested, production-ready)
- ✅ Multi-OEM cross-reference detector
- ✅ SREC state filtering + ITC urgency tagging
- ✅ Coperniq lead scoring algorithm (0-100 multi-dimensional)
- ✅ MVP lead generation script (`scripts/generate_leads.py`)
- ⏳ Tesla Powerwall scraper (structure ready, extraction logic TBD)
- ⏳ Enphase installer scraper (structure ready, extraction logic TBD)
- ⏳ Apollo enrichment integration (API key TBD)
- ⏳ Close CRM import (API key TBD)

## Architecture

### Multi-OEM Scraper Framework

**Base Classes** (`scrapers/base_scraper.py`):
- `BaseDealerScraper`: Abstract base class for all OEM scrapers
- `StandardizedDealer`: Unified data structure across OEMs (15 core fields + enrichment fields)
- `DealerCapabilities`: Tracks product/trade/business capabilities
- `ScraperMode`: PLAYWRIGHT (manual MCP) | RUNPOD (automated cloud) | BROWSERBASE (future)

**OEM-Specific Scrapers**:
- `GeneracScraper` (`scrapers/generac_scraper.py`): ✅ Production-ready with tested extraction
- `TeslaScraper` (`scrapers/tesla_scraper.py`): Structure ready, needs extraction script
- `EnphaseScraper` (`scrapers/enphase_scraper.py`): Structure ready, needs extraction script

**Factory Pattern** (`scrapers/scraper_factory.py`):
```python
from scrapers.scraper_factory import ScraperFactory

# Create scraper by name
generac = ScraperFactory.create("Generac", mode=ScraperMode.RUNPOD)
tesla = ScraperFactory.create("Tesla", mode=ScraperMode.RUNPOD)

# Get all scrapers
all_scrapers = ScraperFactory.create_all(mode=ScraperMode.RUNPOD)
```

### Cross-Reference & Targeting

**Multi-OEM Detection** (`analysis/multi_oem_detector.py`):
- Identifies contractors certified with 2-3 OEM brands (highest value prospects)
- Primary matching: Phone number (normalized to digits only)
- Secondary matching: Domain (root domain after removing www/subdomains)
- Tertiary validation: Fuzzy company name matching (high threshold to avoid false positives)
- Confidence scoring: 100% (all signals), 90% (phone + domain OR phone + name), 80% (phone only)
- Multi-OEM score: 3+ OEMs = 100pts, 2 OEMs = 50pts, 1 OEM = 25pts

**SREC State Filter** (`targeting/srec_itc_filter.py`):
- Filters to states with Solar Renewable Energy Credit programs (sustainable post-ITC)
- HIGH priority: CA, TX, PA, MA, NJ, FL (primary focus)
- MEDIUM priority: OH, MD, DC, DE, NH, RI, CT, IL
- ITC urgency levels:
  - CRITICAL: Commercial projects (must start by June 30, 2026 for safe harbor)
  - HIGH: Residential (ITC expires December 31, 2025)
  - MEDIUM: SREC states (sustainable market post-ITC)
  - LOW: Non-SREC states

**Coperniq Lead Scorer** (`targeting/coperniq_lead_scorer.py`):
- Multi-dimensional 0-100 scoring:
  1. Multi-OEM Presence (40 pts): 3+ OEMs = 40, 2 OEMs = 25, 1 OEM = 10
  2. SREC State Priority (20 pts): HIGH = 20, MEDIUM = 10
  3. Commercial Capability (20 pts): Based on employee count (Apollo) or tier estimation
  4. Geographic Value (10 pts): Wealthy ZIP proximity (top 10 = 10pts, top 30 = 7pts)
  5. ITC Urgency (10 pts): CRITICAL = 10, HIGH = 7, MEDIUM = 5
- Priority tiers: HIGH (80-100), MEDIUM (50-79), LOW (<50)

### Execution Modes

**PLAYWRIGHT Mode** (Local MCP):
- Manual execution via MCP Playwright tools
- 6-step workflow per ZIP code:
  1. `browser_navigate` to dealer locator URL
  2. `browser_click` Accept Cookies button
  3. `browser_type` ZIP code into input field
  4. `browser_click` Search button
  5. `browser_wait_for` AJAX results (3 seconds minimum)
  6. `browser_evaluate` JavaScript extraction script
- Good for testing/development
- Element refs change per page load - always take fresh `browser_snapshot`

**RUNPOD Mode** (Production):
- Automated cloud Playwright via HTTP API
- Deployed serverless infrastructure (see `runpod-playwright-api/`)
- Singleton browser pattern (initialized once, saves ~2s per request)
- Context per request (clean state isolation)
- Auto-scales 0→N workers (pay-per-second, ~$0.001 per ZIP)
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

**Pennsylvania**, **Massachusetts**, **New Jersey**, **Florida**: Similar coverage of major metros + wealthy suburbs

**Combined**: `ZIP_CODES_SREC_ALL` (~75 ZIPs total across 6 states)

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

## MVP Usage

### Quick Start (5 minutes to get leads)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Add RunPod API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add RUNPOD_API_KEY + RUNPOD_ENDPOINT_ID
   ```

3. **Generate leads** (Generac only for MVP):
   ```bash
   python scripts/generate_leads.py --mode runpod --states CA --limit-zips 5
   ```

4. **Review output**:
   - `output/coperniq_leads_YYYYMMDD_HHMMSS.csv` ← START HERE (scored, sorted)
   - HIGH priority (80-100) = call first
   - MEDIUM priority (50-79) = call second
   - LOW priority (<50) = call last or skip

### Full Production Run

```bash
python scripts/generate_leads.py --mode runpod --states CA TX PA MA NJ FL
```

Scrapes ~75 ZIPs, generates scored CSV in ~10-15 minutes, costs ~$0.50

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
