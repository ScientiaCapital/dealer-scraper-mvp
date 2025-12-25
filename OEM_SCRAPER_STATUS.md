# OEM Scraper Status Report

**Generated:** December 25, 2025
**Tests Passing:** 152/152 (100%)
**Structure Validation:** 20/20 scrapers pass

---

## Summary

| Category | Active | Archived | Total |
|----------|--------|----------|-------|
| HVAC | 8 | 1 | 9 |
| Generator | 4 | 0 | 4 |
| Solar/Inverter | 6 | 6 | 12 |
| Battery | 1 | 1 | 2 |
| Building Automation | 1 | 0 | 1 |
| **Total** | **20** | **8** | **28** |

---

## Active Scrapers (20)

### HVAC Systems (8)

| OEM | File | Status | Notes |
|-----|------|--------|-------|
| Carrier | `carrier_scraper.py` | Production | 65 dealers/ZIP tested |
| Trane | `trane_scraper.py` | Production | Detail page enrichment |
| Lennox | `lennox_scraper.py` | Production | API-based extraction |
| York | `york_scraper.py` | Browserbase | Bot detection in headless mode |
| Rheem | `rheem_scraper.py` | Production | - |
| Mitsubishi | `mitsubishi_scraper.py` | Production | Modal handling |
| Honeywell | `honeywell_scraper.py` | Production | 25 contractors/ZIP tested, Bullseye iframe |
| Sensi | `sensi_scraper.py` | Production | 500+ locations, Contractor/Distributor types |

### Generators (4)

| OEM | File | Status | Notes |
|-----|------|--------|-------|
| Generac | `generac_scraper.py` | Production | 78 dealers/ZIP tested |
| Briggs & Stratton | `briggs_scraper.py` | Production | BriggsStrattonScraper class |
| Cummins | `cummins_scraper.py` | Production | Iframe form handling |
| Kohler | `kohler_scraper.py` | Browserbase | Bot detection in headless mode |

### Solar Inverters (6)

| OEM | File | Status | Notes |
|-----|------|--------|-------|
| Tesla | `tesla_scraper.py` | Browserbase | US locale fixed (/en_us/), Browserbase mode |
| Enphase | `enphase_scraper.py` | Production | 27 installers/ZIP, tiers, ratings |
| Fronius | `fronius_scraper.py` | Production | Angular app |
| SMA | `sma_scraper.py` | Production | 2 dealers/ZIP tested Dec 2024 |
| Sol-Ark | `solark_scraper.py` | Production | Authorized Installers + Distributors |
| SolarEdge | `solaredge_scraper.py` | Production | 5 installers/ZIP, O&M support |

### Battery Storage (1)

| OEM | File | Status | Notes |
|-----|------|--------|-------|
| SimpliPhi | `simpliphi_scraper.py` | Production | Elite IQ Installers (contractors) |

### Building Automation (1)

| OEM | File | Status | Notes |
|-----|------|--------|-------|
| Schneider Electric | `schneider_scraper.py` | Production | EcoXpert system integrators (contractors) |

---

## Archived Scrapers (8)

Location: `scrapers/_archived/`

| OEM | File | Reason |
|-----|------|--------|
| ABB | `abb_scraper.py` | Divested residential solar 2020 |
| Delta | `delta_scraper.py` | No public ZIP-searchable locator |
| GoodWe | `goodwe_scraper.py` | No public ZIP-searchable locator |
| Growatt | `growatt_scraper.py` | No public ZIP-searchable locator |
| Johnson Controls | `johnson_controls_scraper.py` | Returns corporate offices only (not contractor ICPs) |
| Sungrow | `sungrow_scraper.py` | No public ZIP-searchable locator |
| Tigo | `tigo_scraper.py` | No public ZIP-searchable locator |

---

## Validation Results

### Structure Validation (December 25, 2025)

```
Total scrapers: 20
Passed: 20/20 (100%)
Warnings: 2 (SMA - minor JS pattern, Schneider - text parsing)
Failed: 0
```

All scrapers validated for:
- Import success
- Factory registration
- Required class attributes (OEM_NAME, DEALER_LOCATOR_URL)
- Required methods (get_extraction_script, detect_capabilities, parse_dealer_data)
- JavaScript extraction script syntax

### Live Tests (December 25, 2025)

| OEM | ZIP | Dealers | Phone % | Status |
|-----|-----|---------|---------|--------|
| SMA | 94102 | 2 | 100% | Working |
| Carrier | 75201 | 65 | 100% | Working |
| Generac | 77001 | 78 | 100% | Working |
| Enphase | 94102 | 27 | N/A | Working (tiers: Platinum/Gold/Silver) |
| SolarEdge | 94102 | 5 | N/A | Working (O&M capabilities) |
| York | 94102 | - | - | Browserbase mode implemented |
| Kohler | 53202 | - | - | Browserbase mode implemented |
| Tesla | 94102 | - | - | Browserbase mode + US locale fixed |
| Honeywell | 94102 | 25 | Yes | Working (Bullseye Locations iframe) |
| Sensi | 45202 | 500+ | Yes | Working (Contractors + Distributors) |
| Sol-Ark | 85001 | 10+ | Yes | Working (Authorized Installers) |
| SimpliPhi | 90210 | 5+ | Yes | Working (Elite IQ Installers) |
| Schneider Electric | 94102 | 2 | Yes | Working (EcoXpert integrators) |

---

## Architecture

### Base Classes
- `BaseDealerScraper` - Abstract base class
- `ScraperFactory` - Factory pattern for instantiation
- `DealerCapabilities` - Capability detection
- `StandardizedDealer` - Normalized output format

### Execution Modes
1. **PLAYWRIGHT** - Local browser automation (tested)
2. **RUNPOD** - Serverless API (production)
3. **BROWSERBASE** - Cloud browsers (available)
4. **PATCHRIGHT** - Stealth mode (bot detection bypass)

### Data Flow
```
ZIP Code Input
    |
ScraperFactory.create(oem_name)
    |
scraper.scrape_zip_code(zip)
    |
get_extraction_script() -> JS evaluation
    |
parse_dealer_data() -> StandardizedDealer
    |
detect_capabilities() -> DealerCapabilities
    |
Output: List[StandardizedDealer]
```

---

## Test Commands

```bash
# Run all tests
pytest tests/ -v

# Structure validation (no network)
python3 scripts/validate_scraper_structure.py

# Live audit (specific OEMs)
python3 scripts/audit_all_scrapers.py --oems carrier generac sma

# Quick audit (first 3)
python3 scripts/audit_all_scrapers.py --quick
```

---

## Next Steps

1. ~~**Fix Kohler selector**~~ Done - Bot detection, use Browserbase
2. ~~**Test York iframe**~~ Done - Bot detection, use Browserbase
3. ~~**Validate Enphase, SolarEdge**~~ Done - Working in MCP Playwright
4. ~~**Browserbase setup**~~ Done - Implemented for York, Kohler, Tesla
5. ~~**Tesla US locale**~~ Done - Fixed with /en_us/ locale in URL
6. ~~**Validate remaining 5**~~ Done - Honeywell, Sensi, Sol-Ark, SimpliPhi, Schneider all working
7. ~~**Johnson Controls**~~ Archived - Returns corporate offices, not ICPs
8. **Deploy to RunPod** - Production bulk scraping
9. **Test Browserbase scrapers** - Validate York, Kohler, Tesla with BROWSERBASE_API_KEY

---

## Tier 1 OEMs for Future Development

High-value OEMs for finding multi-trade MEP contractors:

| OEM | Category | ICP Signal |
|-----|----------|------------|
| Daikin | Heat Pumps/Mini-Splits | HVAC + Electrical |
| ChargePoint | EV Chargers | Electrical + Solar |
| Span | Smart Panels | Electrical + Solar + Storage |
| WaterFurnace | Geothermal | HVAC + Plumbing + Electrical |
| Sonnen | Battery Storage | Premium installers |
| Rinnai | Tankless Water Heaters | Plumbing + Gas |

---

## Files

| File | Purpose |
|------|---------|
| `scrapers/__init__.py` | Module exports, auto-import |
| `scrapers/base_scraper.py` | Base classes |
| `scrapers/scraper_factory.py` | Factory pattern |
| `scrapers/*_scraper.py` | OEM-specific implementations |
| `scripts/validate_scraper_structure.py` | Structure validation |
| `scripts/audit_all_scrapers.py` | Live testing |
