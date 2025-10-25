# Dealer Scraper Status Report

**Last Updated**: 2025-10-25

## Working Scrapers (Production Ready)

### 1. Generac ✅
- **File**: `/scrapers/generac_scraper.py`
- **Status**: Production-ready, tested
- **Locator**: https://www.generac.com/dealer-locator/
- **Type**: ZIP code-based AJAX search
- **Capabilities**: Generator + Electrical
- **Modes**: PLAYWRIGHT, RUNPOD, BROWSERBASE, PATCHRIGHT
- **Testing**: Validated across 3 metros (Milwaukee, Chicago, Minneapolis)
- **Known Issues**: Address parsing for 0-review dealers (low priority)

---

## Scrapers With Structure (Need Extraction Scripts)

### 2. Tesla Powerwall ⏳
- **File**: `/scrapers/tesla_scraper.py`
- **Status**: Structure ready, needs extraction.js
- **Locator**: https://www.tesla.com/support/certified-installers-powerwall
- **Type**: ZIP code-based search (assumed)
- **Capabilities**: Battery + Electrical
- **Next Step**: Use PLAYWRIGHT mode to inspect DOM and write extraction script
- **Priority**: HIGH (major battery OEM)

### 3. Enphase ⏳
- **File**: `/scrapers/enphase_scraper.py`
- **Status**: Structure ready, needs extraction.js
- **Locator**: https://enphase.com/installer-locator
- **Type**: ZIP code-based search (assumed)
- **Capabilities**: Microinverters + Solar + Electrical
- **Next Step**: Use PLAYWRIGHT mode to inspect DOM and write extraction script
- **Priority**: HIGH (major microinverter OEM)

---

## Commercial Inverter OEMs (Not Scrapable)

### 4. Delta Electronics ❌
- **File**: `/scrapers/delta_scraper.py`
- **Status**: NO DEALER LOCATOR EXISTS
- **Reason**: Delta does not provide public installer locator
- **Alternatives**:
  - Contact Delta Americas directly
  - Search EnergySage for Delta-certified installers
  - Work with solar equipment distributors
- **Capabilities**: Solar + Inverters + Commercial
- **Priority**: LOW (no scraping path)

### 5. Tigo Energy ❌
- **File**: `/scrapers/tigo_scraper.py`
- **Status**: STATIC LIST (NOT ZIP-SEARCHABLE)
- **Locator**: https://www.tigoenergy.com/installers/list
- **Type**: Static global list (40K+ tokens, all countries)
- **Why Not Scrapable**: No ZIP search, must scrape entire list + geocode
- **Capabilities**: Solar + Optimizers + Electrical
- **Complexity**: 5-10x more complex than Generac approach
- **Priority**: MEDIUM (possible but requires custom architecture)

### 6. ABB ❌
- **File**: `/scrapers/abb_scraper.py`
- **Status**: BUSINESS DIVESTED (2020)
- **Reason**: ABB sold solar inverter business to FIMER
- **Alternative**: Research FIMER dealer locator separately
- **Capabilities**: N/A (no longer in solar inverter market)
- **Priority**: NONE (unless pivoting to FIMER)

---

## Alternative OEM Recommendations

If the goal is to build commercial inverter scrapers similar to Generac:

### Strong Candidates (Likely ZIP-Searchable)
1. **SolarEdge** - Major commercial inverter, has "Find an Installer" tool
2. **SMA** - Large commercial/industrial inverter player
3. **Fronius** - Commercial inverter with US dealer network
4. **Schneider Electric** - Conext series, large installer network

### Why These Are Better
- Established US dealer networks
- Consumer-facing websites (not just B2B)
- Likely have ZIP code-based locator tools
- High market share in commercial solar

---

## Scraper Factory Registration

**Currently Registered**:
```python
ScraperFactory.register("Generac", GeneracScraper)
ScraperFactory.register("generac", GeneracScraper)
```

**Not Registered (Pending)**:
- Tesla (needs extraction script)
- Enphase (needs extraction script)

**Not Registered (Non-Functional)**:
- Delta (no locator)
- Tigo (architecture mismatch)
- ABB (business divested)

---

## MVP Lead Generation Flow

**Current Flow** (Generac only):
1. Scrape dealers from SREC state ZIPs
2. Deduplicate by phone number
3. Convert to MultiOEMMatch format
4. Filter to SREC states
5. Tag with ITC urgency
6. Score with Coperniq algorithm (0-100)
7. Export CSV sorted by score

**Future Flow** (Multi-OEM):
1. Scrape dealers from Generac + Tesla + Enphase
2. Deduplicate by phone number (within each OEM)
3. Cross-reference by phone + domain (multi-OEM detector)
4. Prioritize 2-3 OEM contractors
5. Filter to SREC states
6. Tag with ITC urgency
7. Score with Coperniq algorithm (multi-OEM = 40 pts)
8. Export CSV sorted by score

---

## Research Documentation

**Detailed Research**: `/docs/commercial_inverter_oems_research.md`

**Key Findings**:
- None of the requested commercial OEMs (Delta, Tigo, ABB) have ZIP-searchable locators
- Only Generac-style ZIP search is compatible with current scraping framework
- Tesla + Enphase are next logical targets (similar architecture expected)
- Pivot to SolarEdge, SMA, Fronius if commercial inverters are priority

---

## Next Steps

### Immediate
1. Get stakeholder approval: Continue with Tesla + Enphase OR pivot to SolarEdge, SMA, Fronius
2. If Tesla + Enphase: Write extraction scripts (use PLAYWRIGHT mode to inspect DOM)
3. Test with ZIP 94102 (San Francisco)

### Short-Term
4. Complete Tesla + Enphase scrapers
5. Test multi-OEM cross-referencing
6. Run full SREC state scrape (Generac + Tesla + Enphase)
7. Validate multi-OEM scoring algorithm

### Medium-Term
8. Add Apollo enrichment (employee count, revenue)
9. Add Close CRM import
10. Consider SolarEdge, SMA, Fronius for broader coverage

### Long-Term
11. Custom Tigo scraper (if critical) - requires geocoding infrastructure
12. FIMER research (if ABB/FIMER is priority)
13. Outreach automation (email, SMS, AI agents)

---

## File Locations

**Scrapers**:
- `/scrapers/base_scraper.py` - Abstract base class
- `/scrapers/generac_scraper.py` - Production ready ✅
- `/scrapers/tesla_scraper.py` - Needs extraction script ⏳
- `/scrapers/enphase_scraper.py` - Needs extraction script ⏳
- `/scrapers/delta_scraper.py` - Placeholder (no locator) ❌
- `/scrapers/tigo_scraper.py` - Placeholder (static list) ❌
- `/scrapers/abb_scraper.py` - Placeholder (divested) ❌
- `/scrapers/scraper_factory.py` - Factory pattern

**Documentation**:
- `/docs/commercial_inverter_oems_research.md` - Delta, Tigo, ABB research
- `/docs/SCRAPER_STATUS.md` - This file

**Config**:
- `/config.py` - ZIP codes, extraction scripts
- `/.env` - API keys (RUNPOD, Apollo, Close)

**Scripts**:
- `/scripts/generate_leads.py` - MVP lead generation
