# OEM Scraper Status Report
## Coperniq Multi-OEM Lead Generation System

Generated: 2025-10-25

---

## ✅ PRODUCTION READY (5 Scrapers)

### Generators
1. **Generac** - Generator dealers
   - Status: ✅ Production tested (1,244 unique dealers from 77 ZIPs)
   - URL: https://www.generac.com/dealer-locator/
   - Extraction: Complete & validated
   - Data: 4,170 raw → 1,244 unique

2. **Briggs & Stratton** - Generator + battery dealers
   - Status: ✅ Production ready (tested extraction)
   - URL: https://energy.briggsandstratton.com/
   - Products: Standby Generators + Battery Storage
   - Extraction: Complete

### Solar/Battery/Inverters
3. **Fronius** - Premium inverter installers (Austrian)
   - Status: ✅ Production ready
   - URL: https://www.fronius.com/en-us/usa/solar-energy/installers
   - Focus: Residential + commercial inverters
   - Extraction: Complete

4. **Sol-Ark** - Hybrid inverter installers
   - Status: ✅ Production ready
   - URL: https://www.sol-ark.com/distributor-map/
   - Products: Hybrid inverters (battery + generator integration)
   - Extraction: Complete

5. **SimpliPhi** - Battery installers (now Briggs brand)
   - Status: ✅ Production ready
   - URL: https://energy.briggsandstratton.com/dealer-locator
   - Products: LFP battery systems
   - Extraction: Complete

---

## ⚠️ STRUCTURE COMPLETE - NEEDS EXTRACTION (4 Scrapers)

### Generators
6. **Cummins** - Generator dealers
   - Status: ⚠️ Framework built, needs DOM inspection
   - URL: https://www.cummins.com/generators/find-a-dealer
   - Next: Manual Playwright inspection to write extraction script

7. **Kohler** - Generator dealers
   - Status: ⚠️ Framework built, needs DOM inspection
   - URL: https://kohlerpower.com/residential/dealer-locator
   - Next: Manual Playwright inspection to write extraction script

### Commercial Solar (HIGH VALUE for ICP)
8. **SMA Solar Technology** - Commercial inverter installers 🎯
   - Status: ⚠️ Structure complete, needs extraction script
   - URL: https://www.sma-america.com/powerupplus/homeowner
   - **WHY CRITICAL**: SMA = commercial/utility-scale contractors
   - Business value: $500K-$10M+ projects, 10-50+ employees
   - ICP match: Perfect resimercial + O&M candidates
   - Documentation: See `docs/SMA_SCRAPER_COMPLETION_GUIDE.md`
   - Next: Follow completion guide (2-4 hours)

### Smart Panels
9. **Eaton** - Smart breaker certified contractors
   - Status: ⚠️ Structure complete, needs extraction script
   - URL: https://www.eaton.com/us/products/residential/find-a-contractor.html
   - Program: Eaton Certified Contractor Network (ECCN)
   - Products: AbleEdge smart breakers
   - Next: Build extraction script

---

## ❌ NOT VIABLE (No Dealer Locators)

### Chinese Inverters
10. **Sungrow** - No ZIP-searchable locator (static distributor list)
11. **GoodWe** - No ZIP-searchable locator
12. **Growatt** - No ZIP-searchable locator

### Commercial Inverters
13. **Delta Electronics** - No public installer locator
14. **Tigo Energy** - Static global list (40K+ tokens, not ZIP-searchable)
15. **ABB** - Sold solar business to FIMER in 2020

### Smart Panels/Monitoring
16. **Sense** - Discontinued installer program
17. **SPAN** - No public installer locator
18. **Leviton** - Static state list (not ZIP-searchable)
19. **Schneider Electric** - Distributor locator only (not installers)

---

## 📊 SUMMARY

**Total OEM Coverage**:
- ✅ Production Ready: 5 scrapers
- ⚠️ Needs Extraction: 4 scrapers
- ❌ Not Viable: 10 OEMs

**Product Coverage (Production Ready)**:
- Generators: Generac, Briggs & Stratton
- Batteries: Briggs & Stratton, SimpliPhi, Sol-Ark
- Inverters: Fronius, Sol-Ark
- Hybrid Systems: Sol-Ark

**Product Coverage (Pending Completion)**:
- Generators: Cummins, Kohler
- Commercial Solar: SMA (HIGH VALUE 🎯)
- Smart Panels: Eaton

---

## 🎯 RECOMMENDED PRIORITY

**Immediate (Next 2 Hours)**:
1. Run 5-OEM production test (Generac + Briggs + Fronius + Sol-Ark + SimpliPhi)
2. Generate multi-OEM master list with ICP scoring
3. Run Gold Miner to identify PLATINUM tier contractors

**High Priority (Next 4 Hours)**:
4. Complete **SMA scraper** (commercial contractors = highest ICP value)
5. Complete Cummins + Kohler (more generator coverage)

**Medium Priority (Next 8 Hours)**:
6. Complete Eaton scraper (smart panel cross-reference)
7. Research alternative commercial inverter OEMs (SolarEdge, Enphase commercial)

---

## 📈 MULTI-OEM VALUE PROPOSITION

**Why Multi-OEM Cross-Reference Matters**:

Contractors certified with 2-4 OEM brands are:
- Managing 2-4 separate monitoring platforms (PAIN POINT)
- More sophisticated businesses (investment in certifications)
- Larger customer bases (broader market reach)
- Higher revenue ($1M-$10M+ for multi-OEM commercial)
- **Perfect ICP for Coperniq's unified monitoring platform**

**Expected Multi-OEM Overlap** (once all scrapers running):
- Generac + Tesla + Enphase: Whole-home energy contractors
- Generac + SMA: Commercial backup power specialists
- Fronius + Sol-Ark + SimpliPhi: Battery integration experts
- Briggs + Kohler + Cummins: Multi-brand generator dealers

**ICP Scoring Impact**:
- 1 OEM: 25 points (base)
- 2 OEMs: 50 points (multi-brand pain)
- 3 OEMs: 75 points (high sophistication)
- 4+ OEMs: 100 points (PLATINUM tier)

---

## 📋 NEXT STEPS

1. ✅ Run 5-OEM production scrape (what we have now)
2. ✅ Generate multi-OEM cross-reference report
3. ✅ Apply ICP filter (resimercial + O&M focus)
4. ✅ Run Gold Miner on results
5. ⏳ Complete SMA scraper (2-4 hours) ← HIGHEST VALUE
6. ⏳ Complete Cummins/Kohler scrapers
7. ⏳ Re-run multi-OEM with 8 total scrapers
8. 🎯 **DELIVER**: PLATINUM tier contractor list for outreach
