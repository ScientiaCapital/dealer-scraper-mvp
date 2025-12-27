# Next 10 OEMs - Dealer Locator Research

**Date:** December 27, 2025
**Status:** Research Complete - Ready for Development

---

## Priority Ranking for Multi-Trade MEP Contractors

| Priority | OEM | Category | ICP Signal | Dealer Locator URL | Scrapability |
|----------|-----|----------|------------|-------------------|--------------|
| 1 | **Daikin** | Heat Pumps/Mini-Splits | HVAC + Electrical | https://daikincomfort.com/find-dealer/locator | ✅ ZIP-based |
| 2 | **WaterFurnace** | Geothermal | HVAC + Plumbing + Electrical | https://www.waterfurnace.com/residential/dealer-locator/ | ✅ ZIP-based |
| 3 | **Rinnai** | Tankless Water Heaters | Plumbing + Gas | https://www.rinnai.us/find-pro | ✅ ZIP-based |
| 4 | **Navien** | Tankless/Boilers | Plumbing + HVAC | https://www.navieninc.com/installers | ✅ ZIP-based |
| 5 | **Sonnen** | Battery Storage | Electrical + Solar | https://www.sonnenusa.com/find-installer | ✅ ZIP-based |
| 6 | **LG Energy Solution** | Battery Storage | Electrical + Solar | https://www.lgessbattery.com/m/eu/home-battery/installer-search.lg | ⚠️ Form-based |
| 7 | **Span** | Smart Panels | Electrical + Solar + Storage | https://www.span.io/get-started | ⚠️ Form-based (no public list) |
| 8 | **ChargePoint** | EV Chargers | Electrical + Solar | Uses Qmerit network | ❌ No public locator |
| 9 | **Panasonic** | HVAC/Solar/Battery | Multi-trade | TBD | TBD |
| 10 | **Fujitsu** | Mini-Splits | HVAC + Electrical | TBD | TBD |

---

## Tier 1: Easy to Scrape (ZIP-based API/Form)

### 1. Daikin (HVAC - Heat Pumps/Mini-Splits)
- **URL:** https://daikincomfort.com/find-dealer/locator
- **ICP Value:** HVAC + Electrical (mini-split installers need both trades)
- **Market Size:** Largest HVAC manufacturer globally
- **Scrapability:** High - standard ZIP input form
- **Notes:** Also has distributor locator for B2B: https://daikincomfort.com/find-distributor

### 2. WaterFurnace (Geothermal Heat Pumps)
- **URL:** https://www.waterfurnace.com/residential/dealer-locator/
- **ICP Value:** HVAC + Plumbing + Electrical (geothermal requires all three trades)
- **Market Size:** Leading geothermal brand in US
- **Scrapability:** High - standard ZIP input
- **Notes:** GeoPro dealers are premium tier (5-star = 5+ years experience)

### 3. Rinnai (Tankless Water Heaters)
- **URL:** https://www.rinnai.us/find-pro
- **ICP Value:** Plumbing + Gas (tankless requires gas line work)
- **Market Size:** #1 tankless brand in US
- **Scrapability:** High - "Find a PRO" ZIP locator
- **Notes:** Certified dealers only sell/install/repair

### 4. Navien (Tankless/Boilers)
- **URL:** https://www.navieninc.com/installers
- **ICP Value:** Plumbing + HVAC (boilers = hydronic heating)
- **Market Size:** Major tankless/boiler brand
- **Scrapability:** High - ZIP/radius search
- **Notes:** Also has distributor locator: https://www.navieninc.com/dealers

### 5. Sonnen (Battery Storage)
- **URL:** https://www.sonnenusa.com/find-installer
- **ICP Value:** Electrical + Solar (premium German battery brand)
- **Market Size:** Premium segment, sonnenConnect program
- **Scrapability:** High - should have ZIP search
- **Notes:** Installers must be certified for warranty coverage

---

## Tier 2: Medium Difficulty (Form-based/API)

### 6. LG Energy Solution (RESU Batteries)
- **URL:** https://www.lgessbattery.com/m/eu/home-battery/installer-search.lg
- **ICP Value:** Electrical + Solar
- **Scrapability:** Medium - certified installer search
- **Notes:** US contact: 888-737-8104, resuservice@lgensol-vt.com

### 7. Span (Smart Electrical Panels)
- **URL:** https://www.span.io/get-started
- **ICP Value:** Electrical + Solar + Storage (smart panel = energy ecosystem)
- **Scrapability:** Medium - form-based matching, no public list
- **Notes:** Must be SPAN-authorized + licensed electrician with training

---

## Tier 3: Difficult (No Public Locator)

### 8. ChargePoint (EV Chargers)
- **URL:** N/A - uses Qmerit partner network
- **ICP Value:** Electrical + Solar (EV + solar is common combo)
- **Alternative:** Scrape Qmerit: https://qmerit.com/ev/chargepoint/
- **Notes:** ChargePoint University certifies installers: cpinstaller.learnupon.com

---

## Implementation Order (Sprint 6)

Based on ICP value and scrapability:

1. **Daikin** - Huge market, ZIP-based, HVAC+Electrical signal
2. **WaterFurnace** - Triple-trade signal (HVAC+Plumbing+Electrical)
3. **Rinnai** - Plumbing+Gas signal, easy ZIP locator
4. **Navien** - Similar to Rinnai, complements coverage
5. **Sonnen** - Premium battery installers

---

## Development Notes

### Similar Patterns to Existing Scrapers
- **Daikin/Rinnai/Navien** → Similar to Carrier/Trane (standard ZIP form)
- **WaterFurnace** → May be similar to Generac (specialized contractors)
- **Sonnen** → Similar to Enphase/SolarEdge (solar+battery installers)

### Bot Detection Expected
- Most HVAC sites: Low detection (standard forms)
- Sonnen: May need Patchright (German company, could be strict)
- LG: May need Browserbase (Korean company, could have Cloudflare)

---

## Current Scraper Count

**Before Sprint 6:** 20 active scrapers
**Target After Sprint 6:** 25 active scrapers (+5)
