# OEM Coverage Analysis - November 2025

**Purpose**: Comprehensive review of current OEM scraper coverage, gaps, and recommendations for Coperniq's resimercial contractor targeting strategy.

---

## Current OEM Coverage (24 Total Scrapers)

### ✅ FULLY FUNCTIONAL & AUTOMATED (14 OEMs)

**Generators (5 OEMs)**:
1. ✅ **Generac** - Market leader, PowerPro Premier tier
2. ✅ **Cummins** - Commercial/industrial focus
3. ✅ **Kohler** - Residential + commercial generators
4. ✅ **Briggs & Stratton** - Residential generators + battery storage
5. ⏳ **Tesla Powerwall** - Batteries + solar (originally tested, need revalidation)

**Solar Inverters (3 OEMs - working)**:
6. ✅ **SMA** - Commercial solar inverters (POWERUP+ installers)
7. ✅ **Fronius** - String inverters + hybrid systems
8. ⏳ **Enphase** - Microinverters + batteries (originally tested, need revalidation)

**HVAC - Resimercial Signal (6 OEMs)**:
9. ✅ **Carrier** - Factory Authorized dealers (47 dealers/ZIP avg)
10. ✅ **Trane** - Comfort Specialists (2,805 dealers - full directory!)
11. ✅ **Lennox** - Premier Dealers (1 dealer/ZIP avg)
12. ✅ **Rheem** - Professional contractors (11 dealers/ZIP avg)
13. ✅ **York** - Commercial contractors (4 dealers/ZIP avg, **just fixed!**)
14. ✅ **Mitsubishi** - Diamond Commercial VRF (37 dealers/ZIP avg, **HIGHEST ICP VALUE**)

### 🔒 BLOCKED BY ANTIBOT (1 OEM - Defer to Tomorrow)

15. 🔒 **SolarEdge** - Major solar inverter brand, strong antibot protection
   - **Status**: Requires Browserbase/residential proxies
   - **Business Impact**: HIGH - major US inverter brand
   - **Next Step**: Tackle with advanced antibot bypass tomorrow

### 📋 MANUAL WORKFLOW (2 OEMs - Not Automated)

16. 📋 **SimpliPhi** - LFP battery storage
   - **Status**: Requires manual MCP Playwright workflow
   - **Reason**: Complex Briggs & Stratton dealer locator (dropdowns, checkboxes)

17. 📋 **Sol-Ark** - Hybrid inverters + battery storage
   - **Status**: Requires manual MCP Playwright workflow
   - **Reason**: Distributor map without ZIP search

### ❌ NO DEALER LOCATOR (7 OEMs - Cannot Scrape)

**Chinese Inverter Brands (3 OEMs)**:
18. ❌ **Sungrow** - Static distributor list only
19. ❌ **GoodWe** - GoodWe PLUS+ program not publicly searchable
20. ❌ **Growatt** - No public installer directory

**Commercial Inverter Brands (3 OEMs)**:
21. ❌ **Delta Electronics** - No public installer locator
22. ❌ **Tigo Energy** - Static global installer list (not ZIP-searchable)
23. ❌ **ABB** - Sold solar business to FIMER in 2020, no longer in market

24. ❌ **FIMER** (ABB successor) - Not yet investigated

---

## Gap Analysis: What Are We Missing?

### Category 1: Battery Storage (HIGH PRIORITY)

**Currently Have**:
- Tesla Powerwall ✅
- Enphase (microinverters + batteries) ✅
- SimpliPhi (manual workflow) 📋
- Sol-Ark (manual workflow) 📋

**MISSING MAJOR BRANDS**:
1. **LG Chem / LG Energy Solution** ⭐⭐⭐
   - Market leader in residential batteries (ESS Home series)
   - Powers many non-Tesla battery systems
   - **High ICP value**: Multi-brand battery installers = sophisticated contractors
   - **URL to investigate**: https://www.lgessbattery.com/us/home-battery/dealers

2. **Panasonic EverVolt** ⭐⭐
   - Partnered with Tesla originally, now independent
   - Strong residential + small commercial battery presence
   - **URL to investigate**: https://na.panasonic.com/us/evervolt/find-an-installer

3. **Sonnen** ⭐⭐
   - Premium German battery brand (intelligent energy storage)
   - High-end residential + small commercial
   - **URL to investigate**: https://sonnenusa.com/en/find-installer

4. **Fortress Power** ⭐
   - Lithium battery systems (eFlex series)
   - Growing US market share
   - **URL to investigate**: https://fortresspower.com/where-to-buy/

### Category 2: More Solar Inverters (MEDIUM PRIORITY)

**Currently Have**:
- SolarEdge (blocked) 🔒
- SMA ✅
- Fronius ✅
- Enphase ✅

**MISSING BRANDS**:
5. **Generac PWRcell** ⭐⭐⭐
   - Generac's solar inverter + battery combo
   - **CRITICAL**: Can cross-reference with Generac generator dealers for **multi-product signal**
   - **URL**: https://www.generac.com/all-products/energy-storage/pwrcell-solar-plus-battery-storage-system (check for installer locator)

6. **Schneider Electric (Conext series)** ⭐⭐
   - Commercial inverters + energy management
   - Strong commercial/industrial presence
   - **URL to investigate**: https://www.se.com/us/en/work/solutions/for-business/solar-power/

7. **Huawei (FusionSolar)** ⭐
   - Major global player, growing US presence
   - Commercial + utility-scale focus
   - **URL to investigate**: https://solar.huawei.com/en-US/professionals

### Category 3: More HVAC (LOW PRIORITY - Already Have 6)

**Currently Have 6 HVAC OEMs** - Good coverage for MEP capability detection

**Potential Additions** (only if pursuing deeper MEP+R scoring):
8. **American Standard** ⭐
   - Sister brand to Trane (same dealer network?)
   - **URL**: https://www.americanstandardair.com/find-a-dealer

9. **Daikin** ⭐
   - VRF systems (competitor to Mitsubishi)
   - Commercial focus
   - **URL**: https://www.daikincomfort.com/find-a-dealer

### Category 4: Electrical Panels / Energy Management (NEW OPPORTUNITY)

**Currently Have**: NONE

**HIGH-VALUE ADDITIONS**:
10. **Span (Smart Electrical Panels)** ⭐⭐⭐
   - Cutting-edge smart panel technology
   - **Perfect Coperniq fit**: Brand-agnostic energy monitoring at panel level
   - Installers are sophisticated electrical contractors
   - **URL to investigate**: https://www.span.io/find-installer

11. **Schneider Electric (Square D + Wiser Energy)** ⭐⭐
   - Smart panels + energy management
   - Commercial + residential
   - **URL**: https://www.se.com/us/en/product-range/61451-square-d-qo-and-homeline-load-centers/

---

## Strategic Recommendations by Priority

### TIER 1: CRITICAL ADDITIONS (Implement This Week)

**1. LG Energy Solution (LG Chem batteries)** ⭐⭐⭐
- **Why**: Market leader in residential batteries, huge network
- **ICP value**: Multi-brand battery installers = high sophistication
- **Estimated dealers**: 2,000-3,000 US installers
- **Effort**: Medium (if dealer locator exists)

**2. Generac PWRcell** ⭐⭐⭐
- **Why**: Cross-reference with existing Generac generator dealers
- **ICP signal**: Generator + Solar + Battery from same OEM = **UNICORN contractor**
- **Estimated dealers**: 1,500-2,000 (subset of Generac generator dealers)
- **Effort**: Low (already have Generac scraper pattern)

**3. Span Smart Panels** ⭐⭐⭐
- **Why**: Perfect alignment with Coperniq's brand-agnostic monitoring value prop
- **ICP value**: Cutting-edge electrical contractors
- **Estimated dealers**: 200-500 (small, selective network = high quality)
- **Effort**: Medium

### TIER 2: HIGH VALUE (Implement Next Week)

**4. Panasonic EverVolt**
- Residential + small commercial batteries
- Estimated dealers: 800-1,200

**5. Schneider Electric (Solar + Panels)**
- Commercial inverters + smart panels
- Estimated dealers: 1,000-1,500

**6. Sonnen (Premium batteries)**
- High-end residential market
- Estimated dealers: 300-500

### TIER 3: NICE TO HAVE (Implement If Time Permits)

**7. Fix SimpliPhi & Sol-Ark automation**
- Convert manual workflows to automated
- Low business value (small networks)

**8. SolarEdge antibot bypass**
- Already scheduled for tomorrow
- High business value (major brand)

**9. Chinese inverter alternatives**
- Skip scraping, use distributor outreach instead
- Alternative: LinkedIn Sales Navigator search

---

## Expected Business Impact

### Current State (14 Automated OEMs)
- **Estimated unique contractors**: 8,000-10,000
- **Multi-OEM contractors (2-3 brands)**: ~800-1,200
- **Resimercial signal strength**: Medium (HVAC presence)

### After TIER 1 Additions (+3 OEMs)
- **Estimated unique contractors**: 11,000-14,000 (**+30-40%**)
- **Multi-OEM contractors (2-3 brands)**: ~1,500-2,000 (**+75%**)
- **Resimercial signal strength**: HIGH (Battery + Panel sophistication)

### After TIER 2 Additions (+3 more OEMs)
- **Estimated unique contractors**: 14,000-18,000 (**+70% from current**)
- **Multi-OEM contractors (3-4+ brands)**: ~2,500-3,500 (**+200%**)
- **PLATINUM ICP contractors (80-100 score)**: 50-100 unicorns

---

## Implementation Plan

### This Week (Nov 1-3)

**Friday Evening (Tonight)**:
1. ✅ Complete current 14 OEM validation (DONE!)
2. 🔍 Investigate LG Energy Solution dealer locator
3. 🔍 Investigate Generac PWRcell installer finder
4. 🔍 Investigate Span panel installer locator

**Saturday-Sunday**:
1. Build LG Chem scraper (if locator exists)
2. Build Generac PWRcell scraper (if separate from generator dealers)
3. Build Span scraper (if locator exists)

### Next Week (Nov 4-8)

**Monday-Wednesday**:
1. Fix SolarEdge antibot issue (Browserbase/proxies)
2. Build Panasonic EverVolt scraper
3. Build Schneider Electric scrapers (if locators exist)

**Thursday-Friday**:
1. Run full production (17-20 OEMs × 140 ZIPs)
2. Aggregate grandmaster list
3. Multi-OEM cross-reference
4. ICP scoring refresh

---

## Key Insights for ICP Refinement

### Multi-Brand Battery Signal (NEW OPPORTUNITY)
Contractors certified with 2-3 battery brands (Tesla + LG + SimpliPhi) = **HIGH sophistication**:
- They're technology-agnostic (not locked to one vendor)
- They serve diverse customer needs (different budgets, use cases)
- They're likely doing commercial work (multiple brands = bigger projects)

### Smart Panel Signal (NEW OPPORTUNITY)
Span + Schneider smart panel installers = **cutting-edge electrical contractors**:
- Early adopters of new technology
- Likely doing whole-home energy management (high-value projects)
- Perfect fit for Coperniq's brand-agnostic monitoring pitch

### Generator + Solar + Battery from Same OEM (UNICORN)
Generac PWRcell dealers who ALSO do Generac generators = **complete energy solution providers**:
- Selling backup power + solar + storage = sophisticated sales process
- Higher revenue per project ($60K-$100K+)
- Commercial + residential capability

---

## Questions to Investigate

1. **LG Energy Solution**: Does dealer locator exist? ZIP-searchable?
2. **Generac PWRcell**: Separate installer network or same as generator dealers?
3. **Span**: Installer locator publicly available?
4. **Panasonic EverVolt**: How large is US installer network?
5. **Schneider Electric**: Multiple dealer locators (solar vs. panels)?

---

**Next Action**: Investigate TIER 1 OEMs (LG, Generac PWRcell, Span) dealer locator URLs tonight before building scrapers.
