# SMA Solar Technology Scraper - Completion Guide

## Overview

**Status**: Structure complete, extraction logic TBD
**Priority**: HIGH (SMA installers = commercial contractors, Coperniq's highest-value ICP)
**Target URL**: https://www.sma-america.com/powerupplus/homeowner
**Created**: 2025-01-25

---

## Why SMA is Critical

SMA Solar Technology is one of the world's largest inverter manufacturers, with a focus on **commercial and utility-scale solar projects**. Their installer network represents Coperniq's highest-value prospects:

### Business Value
- **Project Size**: Commercial/utility-scale ($500K-$10M+ projects)
- **Sophistication**: Established businesses with employees, operations teams
- **Multi-Brand**: Often certified across multiple OEM brands (perfect for Coperniq's value prop)
- **ICP Fit**: Managing complex energy systems = need for brand-agnostic monitoring

### Contractor Characteristics
- **Commercial Focus**: SMA's primary market (vs. Generac/Tesla = residential)
- **Larger Businesses**: Typically 10-50+ employees
- **Multi-Trade**: Solar + electrical + often battery storage
- **Operations Teams**: Many have O&M (Operations & Maintenance) capabilities

### Lead Scoring Impact
- Multi-OEM presence: 40 points (likely certified with 2-3+ brands)
- Commercial capability: 20 points (SMA's primary market)
- Geographic value: 10 points (focus on SREC states)
- **Expected Coperniq Score**: 70-100 (HIGH priority tier)

---

## Current Implementation Status

### ✅ Complete
- [x] SMAScraper class structure (`scrapers/sma_scraper.py`)
- [x] Factory registration (auto-registers as "SMA" and "sma")
- [x] Capability detection logic (solar + inverters + commercial focus)
- [x] StandardizedDealer data structure
- [x] PLAYWRIGHT mode inspection workflow
- [x] Error handling for unimplemented modes
- [x] Comprehensive documentation

### ❌ To-Do
- [ ] JavaScript extraction script (get_extraction_script())
- [ ] CSS selectors for search interaction (SELECTORS dict)
- [ ] Testing on 1-2 ZIP codes
- [ ] RUNPOD mode validation (once extraction works)

---

## Technical Challenge

The SMA PowerUP+ installer map uses **Google Maps API** to dynamically load installer markers. The data is NOT in the HTML DOM, which means traditional Playwright extraction won't work.

### Observed Behavior
1. Page loads with empty Google Maps instance
2. User enters ZIP code in search input
3. JavaScript makes API call (likely to Google Maps or SMA backend)
4. Installers rendered as Google Maps markers
5. Data NOT accessible via DOM parsing

### Extraction Approaches

Three potential approaches to extract installer data:

#### **Approach 1: Reverse-Engineer API Calls** (RECOMMENDED)
**How it works:**
- Use browser DevTools Network tab
- Search for a test ZIP code
- Capture XHR/Fetch requests that return installer data
- Extract the API endpoint and parameters
- Replicate the API call in scraper

**Pros:**
- Most reliable (direct data access)
- Fastest execution (no browser needed)
- Easiest to scale

**Cons:**
- Requires finding the right API endpoint
- May need to handle authentication/headers

**Next Steps:**
```
1. Open https://www.sma-america.com/powerupplus/homeowner in browser
2. Open DevTools → Network tab
3. Filter by XHR or Fetch
4. Enter test ZIP code (e.g., 94102)
5. Click search
6. Look for requests containing installer/dealer data
7. Inspect request URL, headers, parameters
8. Replicate in Python with requests library
```

#### **Approach 2: Extract from JavaScript Window Object**
**How it works:**
- Installer data may be stored in a global JavaScript variable
- Use browser_evaluate to access `window` object
- Look for installer arrays/objects

**Pros:**
- No need to reverse-engineer API
- Data already parsed and structured

**Cons:**
- May not exist (depends on SMA implementation)
- Less reliable across site updates

**Next Steps:**
```javascript
// Use browser_evaluate with this script:
() => {
    // Check for installer data in window object
    const potentialKeys = Object.keys(window).filter(k =>
        k.toLowerCase().includes('installer') ||
        k.toLowerCase().includes('dealer') ||
        k.toLowerCase().includes('partner') ||
        k.toLowerCase().includes('map')
    );

    console.log('Potential data keys:', potentialKeys);

    // Try accessing each key
    potentialKeys.forEach(key => {
        const value = window[key];
        console.log(`${key}:`, typeof value, value);
    });

    // Check if Google Maps has marker data
    if (typeof google !== 'undefined' && google.maps) {
        console.log('Google Maps detected');
        // Try to access markers or data layers
    }

    return potentialKeys;
}
```

#### **Approach 3: Google Maps Marker Extraction**
**How it works:**
- Access Google Maps instance
- Extract installer data from map markers
- Parse marker info windows or data attributes

**Pros:**
- Direct access to displayed data

**Cons:**
- Complex (need to understand Google Maps API)
- Fragile (depends on SMA's map implementation)
- Slower (need to wait for markers to render)

**Next Steps:**
```javascript
// Use browser_evaluate to inspect Google Maps
() => {
    if (typeof google === 'undefined' || !google.maps) {
        return { error: 'Google Maps not loaded' };
    }

    // Try to find the map instance
    // SMA may store it in a global variable
    const mapKeys = Object.keys(window).filter(k =>
        k.toLowerCase().includes('map')
    );

    console.log('Potential map instances:', mapKeys);

    // Return map-related info
    return {
        hasGoogleMaps: true,
        mapKeys: mapKeys
    };
}
```

---

## Step-by-Step Completion Workflow

### Phase 1: Manual Inspection (PLAYWRIGHT Mode)

**Goal**: Identify how installer data is loaded and where it's stored

**Steps**:

1. **Navigate to SMA installer map**
   ```
   Use: mcp__playwright__browser_navigate
   URL: https://www.sma-america.com/powerupplus/homeowner
   ```

2. **Take initial snapshot**
   ```
   Use: mcp__playwright__browser_snapshot
   Purpose: See page structure and element refs
   ```

3. **Open DevTools and monitor Network traffic**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Filter by XHR or Fetch

4. **Test search functionality**
   - Enter test ZIP code: 94102 (San Francisco)
   - Click search
   - Watch for API calls in Network tab

5. **Identify data source**
   - Check XHR/Fetch requests for installer data
   - Use browser_evaluate to inspect window object (see Approach 2 above)
   - Look for Google Maps markers (see Approach 3 above)

6. **Document findings**
   - API endpoint URL (if found)
   - Request parameters
   - Response format
   - Data structure

### Phase 2: Develop Extraction Script

**Goal**: Write JavaScript to extract installer data

**Steps**:

1. **Choose extraction approach** (based on Phase 1 findings)
   - API call replication → Update `_scrape_with_runpod()` to make direct API calls
   - Window object → Write JavaScript to access `window.installerData` or similar
   - Google Maps → Write JavaScript to extract from map markers

2. **Write extraction script**
   - Edit `scrapers/sma_scraper.py`
   - Update `get_extraction_script()` method
   - Return JavaScript that extracts installer data

3. **Test extraction locally**
   ```python
   from scrapers.sma_scraper import SMAScraper
   from scrapers.base_scraper import ScraperMode

   scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)
   scraper.scrape_zip_code("94102")
   # Follow printed instructions to test extraction
   ```

4. **Validate data structure**
   - Ensure extracted data has these fields:
     - `name`: Company name
     - `phone`: Phone number
     - `website`: Website URL
     - `street`: Street address
     - `city`: City
     - `state`: State
     - `zip`: ZIP code
     - `distance`: Distance string (e.g., "5.2 mi")
     - `distance_miles`: Distance as float

### Phase 3: Update Selectors

**Goal**: Define CSS selectors for UI interaction

**Steps**:

1. **Identify search elements** (use browser_snapshot)
   - Cookie accept button
   - ZIP code input field
   - Search button
   - Results container

2. **Update SELECTORS dict**
   ```python
   SELECTORS = {
       "cookie_accept": "button:has-text('Okay')",
       "zip_input": "input[placeholder*='location' i]",
       "search_button": "button:has-text('Extended search')",
       # Add more as needed
   }
   ```

3. **Test selectors**
   - Use PLAYWRIGHT mode workflow
   - Verify each selector works
   - Update if element refs change

### Phase 4: Testing

**Goal**: Validate extraction on multiple ZIP codes

**Steps**:

1. **Test on 1 ZIP code**
   ```python
   scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)
   results = scraper.scrape_zip_code("94102")
   print(f"Extracted {len(results)} installers")
   ```

2. **Validate data quality**
   - Check that all required fields are populated
   - Verify phone numbers are valid
   - Confirm addresses are complete
   - Test domain extraction from websites

3. **Test on 2-3 more ZIP codes**
   - Different states (CA, TX, PA)
   - Different result sizes (high/medium/low density)
   - Edge cases (rural ZIP, no results)

4. **Fix issues**
   - Address parsing errors
   - Missing fields
   - Distance calculation
   - Domain extraction

### Phase 5: RUNPOD Integration

**Goal**: Enable production-ready automated scraping

**Steps**:

1. **Update `_scrape_with_runpod()` method**
   - Add 6-step workflow (like Generac)
   - Configure RunPod API call
   - Handle API response

2. **Test RUNPOD mode locally** (if RunPod credentials available)
   ```python
   scraper = SMAScraper(mode=ScraperMode.RUNPOD)
   results = scraper.scrape_zip_code("94102")
   ```

3. **Validate production readiness**
   - Test on 5-10 ZIP codes
   - Measure execution time
   - Check error handling

---

## Expected Data Structure

### Raw Installer Data (from extraction script)
```javascript
{
  "name": "ABC Solar Solutions",
  "phone": "(415) 555-1234",
  "website": "https://abcsolarsolutions.com",
  "domain": "abcsolarsolutions.com",  // Extracted from website URL
  "street": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94102",
  "address_full": "123 Main St, San Francisco, CA 94102",
  "distance": "2.3 mi",
  "distance_miles": 2.3,
  "rating": 4.8,  // If available from SMA/Google
  "review_count": 42,  // If available
  "tier": "PowerUP+ Installer",  // Or other SMA designation
  "certifications": ["PowerUP+ Installer", "Commercial Certified"]
}
```

### StandardizedDealer Output
```python
StandardizedDealer(
    name="ABC Solar Solutions",
    phone="(415) 555-1234",
    website="https://abcsolarsolutions.com",
    domain="abcsolarsolutions.com",
    street="123 Main St",
    city="San Francisco",
    state="CA",
    zip="94102",
    address_full="123 Main St, San Francisco, CA 94102",
    distance="2.3 mi",
    distance_miles=2.3,
    rating=4.8,
    review_count=42,
    tier="PowerUP+ Installer",
    certifications=["PowerUP+ Installer"],
    capabilities=DealerCapabilities(
        has_solar=True,
        has_inverters=True,
        has_electrical=True,
        is_commercial=True,
        is_residential=True,
        oem_certifications={"SMA"},
        inverter_oems={"SMA"}
    ),
    oem_source="SMA",
    scraped_from_zip="94102"
)
```

---

## Alternative Data Sources

If the SMA PowerUP+ map proves too difficult to scrape, consider these alternatives:

### 1. SMA Developer Portal API
- **URL**: https://developer.sma.de/sma-apis
- **Pros**: Official API, reliable, structured data
- **Cons**: May require API key, may not have installer locator endpoint

### 2. EnergySage Installer Directory
- **URL**: https://www.energysage.com/local-data/solar-companies/
- **Pros**: Lists installers by brand, includes SMA-certified contractors
- **Cons**: Third-party data, may be incomplete

### 3. Solar Reviews
- **URL**: https://www.solarreviews.com/
- **Pros**: Comprehensive installer database, includes certifications
- **Cons**: May require scraping multiple pages

### 4. Direct Outreach to SMA
- **Contact**: SMA sales/partner team
- **Request**: Installer database or API access for Coperniq partnership
- **Pros**: Official data, potential partnership opportunity
- **Cons**: Requires business relationship, slower

---

## Success Criteria

The SMA scraper is complete when:

- [x] Scraper class exists and registers with factory
- [ ] `get_extraction_script()` returns working JavaScript
- [ ] SELECTORS dict has correct element references
- [ ] Extracts 10+ installers from ZIP 94102 (San Francisco)
- [ ] All required StandardizedDealer fields are populated
- [ ] Works in PLAYWRIGHT mode (manual testing)
- [ ] Works in RUNPOD mode (automated production)
- [ ] Tested on 5+ different ZIP codes
- [ ] Zero extraction errors on test ZIPs
- [ ] Execution time < 10 seconds per ZIP (RUNPOD mode)

---

## Contact Information

**Developer**: Claude Code
**Date Created**: 2025-01-25
**Project**: Coperniq Partner Prospecting System
**Repository**: dealer-scraper-mvp

---

## Next Action

**Start here**: Use Playwright MCP tools to inspect the SMA installer map

```python
from scrapers.sma_scraper import SMAScraper
from scrapers.base_scraper import ScraperMode

scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)
scraper.scrape_zip_code("94102")

# Follow the printed workflow to:
# 1. Navigate to SMA installer map
# 2. Open DevTools Network tab
# 3. Search for ZIP 94102
# 4. Identify API call or data source
# 5. Write extraction script
```

**Questions?** See main project documentation: `/CLAUDE.md`
