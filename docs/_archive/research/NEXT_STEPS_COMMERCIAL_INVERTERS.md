# Next Steps: Commercial Inverter Scrapers

**Context**: Delta, Tigo, and ABB were researched but are NOT suitable for Generac-style ZIP code scraping.

---

## Option 1: Pivot to Better OEMs (RECOMMENDED)

Replace Delta/Tigo/ABB with OEMs that likely have ZIP-searchable locators:

### Top Candidates

#### 1. SolarEdge (Highest Priority)
- **Why**: Major commercial inverter player, has "Find an Installer" tool mentioned in search results
- **URL**: https://www.solaredge.com/us/find-an-installer
- **Expected**: ZIP code-based search
- **Capabilities**: Inverters, Optimizers, Solar, Commercial, Residential
- **Market Share**: Top 3 global inverter manufacturer

#### 2. SMA America
- **Why**: Large commercial/industrial inverter manufacturer
- **URL**: Search for "SMA installer locator" or "SMA partner portal"
- **Expected**: Partner/installer directory
- **Capabilities**: Inverters, Solar, Commercial, Industrial
- **Market Share**: Top 5 global

#### 3. Fronius USA
- **Why**: Commercial inverter manufacturer with US presence
- **URL**: Search for "Fronius installer locator USA"
- **Expected**: Dealer/installer search tool
- **Capabilities**: Inverters, Solar, Commercial, Residential
- **Market Share**: Strong in commercial segment

#### 4. Schneider Electric (Conext)
- **Why**: Large electrical contractor network, Conext inverter line
- **URL**: Search for "Schneider Electric solar installer"
- **Expected**: Distributor/installer locator
- **Capabilities**: Inverters, Solar, Commercial, Electrical

### Research Process (15-30 minutes per OEM)

1. **Navigate to OEM website**
2. **Search for**: "installer locator", "find installer", "dealer locator", "partner locator"
3. **Test with ZIP 94102** (San Francisco)
4. **Verify**:
   - Has ZIP code input field?
   - Returns AJAX results?
   - DOM structure scrapable?
5. **If YES**: Proceed to build scraper
6. **If NO**: Document and try next candidate

---

## Option 2: Custom Tigo Scraper (High Effort)

If Tigo Energy is critical (optimizer market leader), build custom architecture:

### Requirements
1. **Full page scraper**: Load https://www.tigoenergy.com/installers/list
2. **Parse all installers**: Extract 40K+ tokens of data (hundreds/thousands globally)
3. **Geocoding service**: Convert addresses to lat/long (Google Maps API, Nominatim, etc.)
4. **ZIP code index**: Create own geographic matching system
5. **US filtering**: Filter to US states only (SREC priority)

### Complexity Estimate
- **Development**: 5-10x more than Generac scraper (40-80 hours vs 8 hours)
- **Dependencies**: Geocoding API (costs money), address parsing library
- **Maintenance**: Higher (geocoding accuracy issues, API changes)

### Cost-Benefit Analysis
- **Benefit**: Access to Tigo-certified installer network (optimizers are important for Coperniq)
- **Cost**: 40-80 hours development + ongoing geocoding API costs
- **Alternative**: Skip Tigo for MVP, add later if customer demand exists

---

## Option 3: Research FIMER (ABB Successor)

ABB sold solar inverter business to FIMER in 2020. FIMER may have inherited ABB's installer network.

### Research Tasks
1. **Find FIMER website**: www.fimer.com or similar
2. **Search for installer locator**: May have kept ABB's network
3. **Check compatibility**: ZIP-searchable or static list?
4. **Assess value**: Is FIMER relevant to Coperniq's market?

### Decision Criteria
- If FIMER has ZIP-searchable locator → Build scraper
- If FIMER has static list → Skip (same issue as Tigo)
- If FIMER has no locator → Skip (same issue as Delta)

---

## Option 4: Third-Party Platform Scraping

Scrape installer databases that aggregate multiple OEMs:

### Platforms
1. **EnergySage**: https://www.energysage.com
   - Aggregates installers across multiple OEMs
   - Has search by location
   - Lists OEM certifications (Delta, Tigo, etc.)
   - Can filter by solar equipment brands

2. **Solar Reviews**: https://www.solarreviews.com
   - Similar to EnergySage
   - Installer reviews and certifications

3. **Google Places API**:
   - Search for "solar installer" + location
   - Filter by mentions of specific OEM brands in reviews/descriptions

### Pros
- Single scraper for multiple OEMs
- More installer coverage
- Customer reviews available

### Cons
- Different scraping architecture (not OEM-specific)
- May not have OEM certification validation
- Data quality varies

---

## Recommended Path Forward

### Phase 1: Quick Wins (This Week)
1. **Research SolarEdge locator** (30 minutes)
   - If YES → Build scraper (4-8 hours)
2. **Research SMA locator** (30 minutes)
   - If YES → Build scraper (4-8 hours)
3. **Research Fronius locator** (30 minutes)
   - If YES → Build scraper (4-8 hours)

**Goal**: Get 2-3 commercial inverter OEM scrapers working

### Phase 2: Complete MVP (Next Week)
4. **Finish Tesla + Enphase scrapers** (8-16 hours)
   - Write extraction scripts
   - Test with SREC ZIPs
5. **Run multi-OEM scrape** (Generac + Tesla + Enphase + SolarEdge + SMA)
6. **Test cross-reference detector** (find 2-3 OEM contractors)
7. **Validate Coperniq scoring** (multi-OEM = 40 pts)

**Goal**: Full multi-OEM lead generation pipeline

### Phase 3: Optional Enhancements (Later)
8. **Custom Tigo scraper** (if customer demand exists)
9. **FIMER research** (if relevant to market)
10. **EnergySage scraping** (if broader coverage needed)
11. **Apollo enrichment** (employee count, revenue)
12. **Close CRM import** (bulk upload leads)

---

## Decision Matrix

| OEM | Has Locator? | ZIP Search? | Scrapable? | Priority | Effort |
|-----|--------------|-------------|------------|----------|--------|
| **Generac** | ✅ | ✅ | ✅ | HIGH | DONE |
| **Tesla** | ✅ | ? | ? | HIGH | 4-8h |
| **Enphase** | ✅ | ? | ? | HIGH | 4-8h |
| **SolarEdge** | ✅ (likely) | ? | ? | HIGH | Research + 4-8h |
| **SMA** | ? | ? | ? | MEDIUM | Research + 4-8h |
| **Fronius** | ? | ? | ? | MEDIUM | Research + 4-8h |
| **Schneider** | ? | ? | ? | LOW | Research + 4-8h |
| **Delta** | ❌ | N/A | ❌ | LOW | N/A |
| **Tigo** | ✅ | ❌ | ⚠️ | MEDIUM | 40-80h |
| **ABB** | ❌ | N/A | ❌ | NONE | N/A |
| **FIMER** | ? | ? | ? | LOW | Research |

---

## Questions for Stakeholder

1. **Is multi-OEM coverage more important than specific brands?**
   - If YES → Focus on any OEMs with ZIP-searchable locators (SolarEdge, SMA, Fronius)
   - If NO → Invest in custom Tigo scraper (40-80 hours)

2. **Are commercial inverters critical to Coperniq's value prop?**
   - If YES → Prioritize SolarEdge, SMA, Fronius research
   - If NO → Focus on battery (Tesla) and microinverter (Enphase) OEMs

3. **What's the timeline for MVP?**
   - If URGENT → Skip commercial inverters, finish Tesla + Enphase only
   - If FLEXIBLE → Research + build 2-3 commercial inverter scrapers

4. **Is Tigo worth 40-80 hours of development?**
   - Tigo is optimizer market leader (important for Coperniq)
   - But custom architecture required (no ZIP search)
   - Alternative: Add Tigo in Phase 2 if customer demand exists

---

## Ready-to-Use Command

Once you pick your path, use this to start:

```bash
# Option 1: Research SolarEdge (recommended)
python -c "
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Test if SolarEdge has ZIP-searchable locator
# Navigate to: https://www.solaredge.com/us/find-an-installer
# Search ZIP: 94102
# If works: Build SolarEdgeScraper using GeneracScraper as template
"

# Option 2: Finish Tesla + Enphase (MVP completion)
# Use PLAYWRIGHT mode to inspect DOM and write extraction scripts

# Option 3: Custom Tigo scraper (high effort)
# Load full installer list, geocode, create ZIP index
```

---

## Conclusion

**Delta, Tigo, and ABB are NOT suitable for Generac-style scraping.**

**Best path forward**:
1. Research SolarEdge, SMA, Fronius (30 min each)
2. Build scrapers for any with ZIP-searchable locators (4-8 hrs each)
3. Finish Tesla + Enphase scrapers (8-16 hrs)
4. Run multi-OEM lead generation
5. Add Tigo later if customer demand exists (40-80 hrs)

**Expected outcome**: 5-6 OEM scrapers (Generac, Tesla, Enphase, SolarEdge, SMA, Fronius) covering generators, batteries, microinverters, and commercial inverters.
