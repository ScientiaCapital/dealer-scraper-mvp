# Commercial Inverter OEM Scraper Research
**Date**: 2025-10-25
**Researcher**: Claude Code
**Task**: Research Delta Electronics, Tigo Energy, and ABB for installer/dealer locator tools

## Executive Summary

**Status**: None of the three OEMs have ZIP code-based dealer locators like Generac's interactive search tool.

**Findings**:
1. **Delta Electronics**: No public installer locator found
2. **Tigo Energy**: Static installer list (not ZIP-searchable)
3. **ABB**: Sold solar inverter business to FIMER in 2020, no locator tool

**Recommendation**: These OEMs are NOT suitable for automated scraping using the current Generac-style workflow (navigate → search ZIP → extract results). Alternative approach needed.

---

## 1. Delta Electronics

### URLs Investigated
- https://www.deltaww.com (redirects/blocked)
- https://www.delta-americas.com (redirected to SPAN.io - unrelated smart panel company)
- https://www.deltaww.com/en-US/Solutions/pv-solutions/ALL/
- https://www.deltaww.com/en-us/products/Photovoltaic-Inverter/ALL/

### Findings
- **No installer locator tool found**
- Delta sells solar inverters (3kW - 80kW range, up to 98.8% efficiency)
- Products available through:
  - Delta Americas direct contact
  - Third-party distributors (Solaris-Shop.com, etc.)
  - EnergySage platform (indirect)
- Monitoring platform: My Delta Solar Cloud (https://mydeltasolar.deltaww.com/contact)

### Why No Scraper Possible
Delta does not provide a public-facing installer locator database. Users must:
1. Contact Delta Americas directly
2. Work with solar equipment distributors
3. Search on third-party platforms (EnergySage)

### Recommendation
**Cannot build scraper** - no dealer locator exists.

**Alternative**: Could potentially scrape EnergySage or other third-party platforms that list Delta-certified installers, but this would require different scraping infrastructure (not OEM-specific).

---

## 2. Tigo Energy

### URLs Investigated
- https://www.tigoenergy.com
- https://www.tigoenergy.com/installers/list ← **INSTALLER LIST FOUND**

### Findings
- **Static installer list exists** (not ZIP-searchable)
- URL: https://www.tigoenergy.com/installers/list
- Page structure: Massive static list of all Tigo-certified installers globally
- Page size: 40,000+ tokens (too large to process in single MCP call)

### Why Current Scraping Approach Doesn't Work
1. **Not ZIP code-based**: Unlike Generac's dealer locator which accepts ZIP input and returns nearby dealers, Tigo displays ALL installers in one giant list
2. **No AJAX workflow**: No search → wait → extract pattern. All data loaded at once.
3. **Global list**: Contains installers from all countries, not filterable by location via web UI
4. **Massive payload**: 40K+ tokens suggests hundreds or thousands of installers in DOM

### Alternative Scraping Approaches

**Option A: Full page scrape (not recommended)**
- Extract entire installer list in one call
- Filter to US-based installers post-scrape
- Problem: Massive data transfer, no ZIP code granularity

**Option B: Inspect for pagination or filtering**
- May have hidden filters/pagination in DOM
- Would require deeper investigation of page structure
- May use JavaScript-based filtering (not server-side)

**Option C: Skip Tigo for MVP**
- Focus on OEMs with ZIP-searchable locators
- Revisit Tigo if demand exists

### Recommendation
**Cannot build Generac-style scraper** - architecture mismatch.

**If Tigo is critical**: Would need custom scraper that:
1. Loads full installer list once
2. Extracts all installers
3. Geocodes addresses to match ZIP codes
4. Creates own geographic indexing

This is 5-10x more complex than Generac's approach.

---

## 3. ABB

### URLs Investigated
- https://www.abb.com
- https://new.abb.com/solar
- https://new.abb.com/power-converters-inverters/solar (blocked/aborted)

### Findings
- **ABB sold solar inverter business to FIMER in 2020**
- Quote from ABB website: "Please note ABB has signed an agreement with Fimer to acquire the solar inverter business."
- Press release: https://new.abb.com/news/detail/57766/abb-completes-divestment-of-solar-inverter-business-to-fimer-spa
- **No installer locator tool found** on ABB website
- ABB still sells other solar products (surge protection, electrical components) but NOT inverters

### Why No Scraper Possible
1. ABB exited the solar inverter business entirely
2. No installer network to scrape (transferred to FIMER)
3. Remaining ABB solar products (electrical components) are sold through general electrical distributors

### FIMER Investigation Needed
Since ABB sold to FIMER, should investigate:
- https://www.fimer.com (if exists)
- FIMER installer locator (if exists)
- FIMER may maintain ABB's former installer network

### Recommendation
**Cannot build ABB scraper** - ABB no longer in inverter business.

**Next step**: Research FIMER separately if ABB/FIMER inverters are priority target.

---

## Alternative OEM Recommendations

If the goal is to build commercial inverter OEM scrapers similar to Generac, consider these alternatives:

### Strong Candidates (likely have ZIP-searchable locators)
1. **SolarEdge** - Major commercial inverter manufacturer, has "Find an Installer" tool
2. **SMA** - Large commercial/industrial inverter player, German company with US presence
3. **Fronius** - Commercial inverter manufacturer with US dealer network
4. **Schneider Electric** (Conext series) - Commercial inverters, large installer network

### Why These Are Better
- Established US dealer networks
- Consumer-facing websites (not just B2B)
- Likely have ZIP code-based locator tools like Generac
- High market share in commercial solar segment

---

## Technical Notes for Future OEM Scraper Development

### Requirements for Generac-Style Scraper
To use the existing `BaseDealerScraper` framework, an OEM must have:

1. **ZIP code input field** - Interactive search by location
2. **AJAX-based results** - Dealers load dynamically after search
3. **Consistent DOM structure** - Dealer cards with extractable fields
4. **Client-side rendering** - Data accessible via `browser_evaluate` JavaScript

### Red Flags Indicating Incompatible Architecture
- Static lists without search functionality (Tigo)
- "Contact us for installers" approach (Delta)
- Business divestiture / no longer in market (ABB → FIMER)
- Behind login/authentication walls
- API-only access (no web UI)

### Alternative Scraping Methods
For OEMs without ZIP locators, would need:

**Method 1: Full List Scrape + Geocoding**
- Scrape entire installer list
- Geocode addresses → lat/long
- Create own ZIP code index
- Example: Tigo

**Method 2: Distributor Scraping**
- Scrape distributor databases (e.g., EnergySage, Solaris-Shop)
- Cross-reference to specific OEM products
- Example: Delta

**Method 3: LinkedIn Sales Navigator**
- Search for "[OEM] certified installer" on LinkedIn
- Export company lists
- Enrich with contact data
- Manual/semi-automated approach

---

## Conclusion

**None of the three requested OEMs (Delta, Tigo, ABB) have ZIP code-based dealer locators suitable for automated scraping using the current Generac-style framework.**

**Recommendations**:
1. Do NOT build scrapers for Delta, Tigo, or ABB
2. Pivot to OEMs with ZIP-searchable locators (SolarEdge, SMA, Fronius, Schneider)
3. If Tigo is critical, budget 5-10x development time for custom architecture
4. If ABB/FIMER is critical, investigate FIMER separately

**Next Steps**:
- Get stakeholder approval to pivot to different OEMs
- OR proceed with placeholder scrapers that document "no locator available"
- OR invest in custom Tigo scraper architecture (high complexity)
