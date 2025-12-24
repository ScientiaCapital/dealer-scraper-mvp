# Chinese Inverter OEM Scraper Research

**Date**: 2025-01-25
**Status**: NON-FUNCTIONAL (Dealer locators do not exist)
**Impact**: Cannot scrape these OEMs using current ZIP-based approach

## Executive Summary

After researching Sungrow, GoodWe, and Growatt, I found that **none of these Chinese inverter OEMs provide US-based ZIP code dealer locator tools** similar to Generac's dealer finder. They only offer static distributor directories or require direct contact for installer referrals.

**Result**: Created framework scraper modules that return empty results and provide alternative data source recommendations.

---

## Detailed Findings

### 1. Sungrow

**Official URLs**:
- Global: https://www.sungrowpower.com/en/find-a-distributor
- US: https://us.sungrowpower.com/
- US Distributors: https://us.sungrowpower.com/distributors

**Dealer Locator**: ❌ None
**What They Have**: Static global distributor directory (not searchable by ZIP)

**Product Lines**:
- Residential inverters (SG5.0RS, SG8.0RS, SG10RS, etc.)
- Commercial inverters (SG110CX, SG125HV, etc.)
- Hybrid inverters with battery (SH5K-30, SH8K-30, etc.)
- Energy storage systems (PowerStack, PowerTitan)

**US Presence**:
- Sungrow USA Corporation
- 47751 Fremont Blvd, Fremont, CA 94538
- Phone: (510) 656-1259

**Capabilities Detected**:
- ✅ `has_inverters = True` (all products)
- ✅ `has_solar = True` (core business)
- ✅ `has_electrical = True` (required for installation)
- ✅ `has_battery = True` (hybrid inverters + energy storage)
- ✅ `oem_certifications.add("Sungrow")`

**Alternative Data Sources**:
1. Scrape static distributor list from us.sungrowpower.com/distributors
2. Contact Sungrow USA directly for installer referrals
3. Third-party databases: EnergySage, NABCEP
4. LinkedIn search: "Sungrow installer" OR "Sungrow certified"

---

### 2. GoodWe

**Official URLs**:
- US Main: https://us.goodwe.com/
- Where to Buy: https://us.goodwe.com/where-to-buy
- GoodWe PLUS+ Program: https://us.goodwe.com/goodwe-plus-customer-program
- Community: https://community.goodwe.com/

**Dealer Locator**: ❌ None
**What They Have**:
- Static regional distributor directory ("Where to Buy")
- GoodWe PLUS+ installer certification program (NOT publicly searchable)

**Installer Program**:
- **GoodWe PLUS+** tiered certification:
  - PLUS+ (basic)
  - Silver (medium volume)
  - Gold (high volume)
- Based on training completion + installation volumes
- Installer directory requires SEMS portal access (not public)

**Product Lines**:
- Residential hybrid inverters (GW5000-EH, GW6000-EH, etc.)
- Commercial inverters (MT series, SMT series)
- Battery systems (Lynx Home series)
- Smart energy management (SEMS portal)

**Capabilities Detected**:
- ✅ `has_inverters = True` (all products)
- ✅ `has_solar = True` (core business)
- ✅ `has_electrical = True` (required for installation)
- ✅ `has_battery = True` (hybrid inverters are GoodWe's specialty)
- ✅ `oem_certifications.add("GoodWe")`
- Gold tier → `is_commercial = True`, `is_residential = True`

**Alternative Data Sources**:
1. Scrape static distributor list from us.goodwe.com/where-to-buy
2. Contact distributors for installer referrals
3. LinkedIn search: "GoodWe PLUS+ installer" (requires Sales Navigator)
4. Third-party databases: EnergySage, NABCEP
5. GoodWe Community (community.goodwe.com) - may have installer discussions

---

### 3. Growatt

**Official URLs**:
- US Main: https://us.growatt.com/
- Global: https://growattinverters.com/
- Contact: https://growattinverters.com/show-23-9.html (USA section)

**Dealer Locator**: ❌ None
**What They Have**: NOTHING - no public installer directory at all

**US Distributors** (found via web search):
- Signature Solar (signaturesolar.com)
- ShopSolar (shopsolarkits.com) - (877) 242-2792
- CSE Solar USA (csesolarusa.com) - (702) 608-8385
- Meico Solar (meicosolar.com)
- Growatt USA Distribution Center (Ontario, CA)

**Installer Certification**:
- Growatt Accredited Installer Training Program exists
- Required for warranty support
- BUT: No public directory of certified installers

**Product Lines**:
- Residential inverters (MIN series, MIC series)
- Hybrid inverters (SPH series, MOD series)
- Battery systems (ARK series)
- Commercial inverters (MAX series)
- Off-grid systems (SPF series)

**Capabilities Detected**:
- ✅ `has_inverters = True` (all products)
- ✅ `has_solar = True` (core business)
- ✅ `has_electrical = True` (required for installation)
- ✅ `has_battery = True` (hybrid + ARK battery systems)
- ✅ `oem_certifications.add("Growatt")`
- Residential by default (MIN/MIC series most common)
- Commercial if MAX series or "commercial" keyword

**Alternative Data Sources**:
1. Contact Growatt USA: service.na@growatt.com
2. Contact US distributors (Signature Solar, ShopSolar, CSE Solar USA) for installer referrals
3. Third-party databases: EnergySage, NABCEP
4. LinkedIn search: "Growatt installer" OR "Growatt distributor"
5. DIY solar forums (diysolarforum.com) - ask community for installer recommendations

---

## Technical Implementation

### Files Created

1. **`scrapers/sungrow_scraper.py`** (475 lines)
   - Full framework implementation
   - Returns empty results with limitation warnings
   - Provides alternative data source recommendations

2. **`scrapers/goodwe_scraper.py`** (490 lines)
   - Full framework implementation
   - Documents GoodWe PLUS+ program structure
   - Returns empty results with limitation warnings

3. **`scrapers/growatt_scraper.py`** (485 lines)
   - Full framework implementation
   - Lists known US distributors
   - Returns empty results with limitation warnings

### Common Structure

All three scrapers follow the `BaseDealerScraper` pattern:

```python
class [OEM]Scraper(BaseDealerScraper):
    OEM_NAME = "[OEM]"
    DEALER_LOCATOR_URL = "[URL]"  # (doesn't actually work)
    PRODUCT_LINES = [...]
    SELECTORS = {}  # Empty - no dealer locator exists

    def get_extraction_script(self) -> str:
        # Returns empty array with console warning
        return "(() => { console.log('No locator'); return []; })();"

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        # Sets: has_inverters, has_solar, has_electrical, has_battery
        # Adds OEM to oem_certifications and inverter_oems
        pass

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        # Prints limitation notice + alternative data sources
        # Returns empty list
        return []
```

### Scraper Factory Registration

All three scrapers are registered with the factory:

```python
ScraperFactory.register("Sungrow", SungrowScraper)
ScraperFactory.register("GoodWe", GoodWeScraper)
ScraperFactory.register("Growatt", GrowattScraper)
```

**Usage** (returns empty list):
```python
from scrapers.scraper_factory import ScraperFactory

sungrow = ScraperFactory.create("Sungrow", mode=ScraperMode.RUNPOD)
dealers = sungrow.scrape_zip_code("94102")  # Returns []
```

---

## Business Impact

### Why This Matters for Coperniq

1. **Market Coverage Gap**: Cannot identify Chinese inverter installers using automated scraping
2. **Multi-OEM Detection Limited**: Will miss contractors certified with Sungrow/GoodWe/Growatt + other brands
3. **Market Share**: These Chinese OEMs collectively have ~20-30% US residential market share

### Recommended Alternative Approach

**Short-Term (Manual)**:
1. Contact 5-10 largest US distributors per OEM
2. Request installer referral lists by state
3. Manually enrich with Apollo/LinkedIn
4. Import to Close CRM as separate "Chinese Inverter OEM" segment

**Medium-Term (Automation)**:
1. Build distributor contact list scraper (from static pages)
2. Email automation to distributors requesting installer lists
3. Parse responses into database
4. Cross-reference with existing Generac/Tesla/Enphase data

**Long-Term (Data Partnerships)**:
1. Partner with EnergySage (they have installer data)
2. Partner with NABCEP (certified installer database)
3. Buy data from Solar Power World Top Contractors list
4. Scrape permit data from municipal building departments (public records)

---

## Challenges Encountered

### 1. Language/Localization Issues

**Expected**: Chinese companies might have less polished US sites
**Reality**: Sites are well-translated, just missing dealer locator functionality entirely

### 2. Address Parsing

**Expected**: International phone formats, different address structures
**Reality**: N/A - no data to parse

### 3. Data Availability

**Expected**: Less polished dealer locators than US brands
**Reality**: No dealer locators at all, only static distributor lists

---

## Recommendations

### DO NOT USE These Scrapers

- All three return empty results
- Framework exists only for future if OEMs add dealer locators
- Wasted effort to integrate into lead generation scripts

### FOCUS ON

1. **Generac** ✅ (working, tested)
2. **Tesla Powerwall** (needs extraction script)
3. **Enphase** (needs extraction script)
4. **SolarEdge** (investigate if they have dealer locator)
5. **SMA** (investigate if they have dealer locator)

### ALTERNATIVE STRATEGY

**Build "Distributor-to-Installer" pipeline**:
1. Scrape distributor contact info from static pages (easy)
2. Create outreach email template: "Please share your installer referral list for [state]"
3. Automate email sending with SendGrid
4. Parse responses + import to CRM
5. Cross-reference with existing multi-OEM data

This would work for:
- Sungrow (has distributor list)
- GoodWe (has distributor list)
- Growatt (has known distributors)
- Any other OEM without dealer locator

---

## Files Delivered

### Scraper Modules
1. `/Users/tmkipper/Desktop/dealer-scraper-mvp/scrapers/sungrow_scraper.py`
2. `/Users/tmkipper/Desktop/dealer-scraper-mvp/scrapers/goodwe_scraper.py`
3. `/Users/tmkipper/Desktop/dealer-scraper-mvp/scrapers/growatt_scraper.py`

### Documentation
4. `/Users/tmkipper/Desktop/dealer-scraper-mvp/docs/chinese-inverter-oem-research.md` (this file)

### URLs Researched

**Sungrow**:
- https://www.sungrowpower.com/en/find-a-distributor
- https://us.sungrowpower.com/
- https://us.sungrowpower.com/distributors

**GoodWe**:
- https://us.goodwe.com/where-to-buy
- https://us.goodwe.com/goodwe-plus-customer-program
- https://community.goodwe.com/

**Growatt**:
- https://us.growatt.com/
- https://growattinverters.com/
- Distributor sites: Signature Solar, ShopSolar, CSE Solar USA

---

## Next Steps

1. **Prioritize OEMs with working dealer locators**:
   - Tesla Powerwall (structure ready, needs extraction script)
   - Enphase (structure ready, needs extraction script)
   - SolarEdge (investigate)
   - SMA (investigate)

2. **If Chinese OEM data is critical**:
   - Build distributor contact scraper (static pages)
   - Create email outreach automation
   - Partner with third-party databases (EnergySage, NABCEP)

3. **Update CLAUDE.md**:
   - Mark Sungrow/GoodWe/Growatt as "NON-FUNCTIONAL"
   - Document alternative approaches
   - Adjust multi-OEM strategy to focus on OEMs with locators

---

## Conclusion

Chinese inverter OEMs (Sungrow, GoodWe, Growatt) **do not provide ZIP code-based dealer locator tools** like Generac. Automated scraping is not possible with current approach.

**Framework scrapers created** for future use if OEMs add dealer locators, but they currently return empty results and provide alternative data source recommendations.

**Recommendation**: Focus on OEMs with working dealer locators (Generac, Tesla, Enphase) and use alternative approaches (distributor outreach, third-party databases, permit data) for Chinese OEM installer data.
