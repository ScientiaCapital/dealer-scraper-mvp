# Smart Panel & Energy Monitoring Research

**Date**: 2025-10-25
**Status**: Research Complete

## Executive Summary

After researching Sense energy monitoring and the top smart panel manufacturers, I found that **only one manufacturer has a viable, scrapable installer locator**: Eaton with their Certified Contractor Network.

**Recommendation**: Build a scraper for **Eaton Certified Contractor Network** only. The other manufacturers either discontinued their programs, don't have public locators, or only offer distributor locators (not installer/contractor locators).

---

## 1. Sense Energy Monitor

**Website**: https://sense.com
**Product**: Sense Home Energy Monitor (consumer energy monitoring device)

### Findings

- **Installer Program Status**: DISCONTINUED
- **Former Program**: "Sense Pro" partner program
- **Current Status**:
  - Sense Pro Store closed
  - Fleet Manager being decommissioned in stages
  - No longer signing up new Sense Pro partners
  - Company pivoting to utility-scale deployments with smart meter partnerships (Landis+Gyr, Itron, Sensus)

### Consumer Purchase Options

- Devices available on Amazon for DIY installation
- No installer locator available

### Why No Scraper Needed

Sense has exited the professional installer channel entirely. They're focusing on embedding their technology into utility smart meters rather than standalone consumer devices installed by electricians.

---

## 2. SPAN Smart Panels

**Website**: https://www.span.io
**Product**: SPAN Panel (smart electrical panel with circuit-level control)

### Findings

- **Installer Program**: SPAN Authorized Installer Program (active)
- **Program Features**:
  - Authorization takes 45 minutes
  - Free leads provided to installers in their area
  - Tech Portal access for training and support
  - Marketing and sales support
- **Public Installer Locator**: NO

### Why No Scraper Possible

SPAN has an active installer program but does **not** provide a public installer locator for consumers. They focus on B2B relationships with contractors who "get authorized" to sell SPAN, rather than a consumer-facing "find an installer" tool.

The `/get-started` URL redirected to an SMA Solar inverter installer locator (unrelated partnership).

---

## 3. Leviton Load Centers

**Website**: https://leviton.com
**Product**: Leviton Load Center (modern electrical panel with plug-on neutral breakers)

### Findings

- **Installer Programs**:
  - EV-Pro Certified Contractors (for EV charging installations)
  - Contractor Connect Portal (B2B resources)
  - Network Solutions Certified Installers (for network/data installations)
- **Public Installer Locator**: Limited

### Installer Locator Details

- **URL**: https://leviton.com/products/commercial/ev-charging-commercial/ev-pro-contractor-certification-program/ev-pro-certified-contractors
- **Type**: State-by-state list of EV-Pro certified contractors
- **Format**: Large static page (40,407 tokens - too large for single page load)
- **Scope**: EV charging installers only (not load center specific)

### Why Limited Value

While Leviton has an EV-Pro installer list, it's:
1. **Not searchable by ZIP code** - appears to be a static state-by-state list
2. **EV charging focused** - not specifically for Load Center installations
3. **Extremely large page** - suggests it's a comprehensive list rather than a locator tool
4. **No geographic search** - can't filter to specific areas

This is more of a "certified contractor directory" than a true dealer locator.

---

## 4. Eaton (AbleEdge Smart Breakers)

**Website**: https://www.eaton.com
**Product**: AbleEdge Smart Breakers + Energy Management System (formerly "Smart Type BR")

### Findings ✅

- **Installer Program**: Eaton Certified Contractor Network (ECCN) - ACTIVE
- **Public Installer Locator**: YES - SCRAPABLE

### Installer Locator Details

- **URL**: https://www.eaton.com/us/en-us/products/residential/my-home/find-a-contractor.html
- **Title**: "Find a local Eaton Certified electrician you can trust"
- **Technology**: iframe-based map locator (similar to our existing Generac scraper structure)
- **Locator Provider**: Bullseye Locations (`eaton-canada.bullseyelocations.com`)
- **Search Type**: Geographic (ZIP code, address, or proximity-based)

### Products Covered

Eaton's smart panel ecosystem includes:
- **AbleEdge Smart Breakers**: Wi-Fi enabled circuit breakers for energy management
- **BR Loadcenters**: Standard electrical panels compatible with smart breakers
- **Home Energy Management System**: Mobile app for monitoring and control

### Contractor Certification

- Technicians attend certification training
- Company name added to public locator after certification
- Consumer access via myhome.eaton.com or direct locator URL
- Support: 1-888-328-6624

### Why This is SCRAPABLE ✅

1. **Public-facing locator** - consumers can search by ZIP code
2. **iframe architecture** - similar to Generac's dealer locator (proven scrapable pattern)
3. **Geographic search** - ZIP code input returns nearby contractors
4. **Active program** - contractors are being added continuously
5. **JavaScript extraction possible** - same approach as our existing OEM scrapers

---

## 5. Schneider Electric (Square D Energy Center)

**Website**: https://www.se.com
**Product**: Square D Energy Center (smart panel for solar and backup power)

### Findings

- **Products**:
  - Square D Energy Center (full smart panel)
  - Square D Control Relays (retrofit solution for existing panels)
  - Schneider Energy Monitor
- **Installer Resources**:
  - Distributor Locator (not installer locator)
  - Contractor Portal for existing partners
- **Public Installer Locator**: NO

### Locator Details

- **URL**: https://www.se.com/us/en/work/support/locator/
- **Type**: Multi-category locator for:
  - Electrical distributors
  - System integrators (EcoXperts for building management)
  - Process instrumentation partners
  - IT resellers (APC products)
  - Retail locations (Home Depot, Lowe's, etc.)

### Why No Scraper Possible

Schneider Electric provides a **distributor locator**, not an **installer/contractor locator**. Consumers are directed to:
1. Find electrical distributors who sell Square D products
2. Contact any licensed electrician to install (no certification required)
3. Use the contractor portal if they're already a partner

This is B2B focused (finding product suppliers) rather than B2C (finding installers).

---

## Market Analysis: Smart Panel Landscape

### Smart Panel vs. Smart Breaker Distinction

1. **Full Smart Panels** (panel replacement):
   - SPAN Panel (SPAN)
   - Square D Energy Center (Schneider Electric)
   - Leviton Load Center (traditional panel with modern features)

2. **Smart Breaker Retrofit** (works with existing panels):
   - AbleEdge Smart Breakers (Eaton)
   - Square D Control Relays (Schneider Electric)

### Market Leaders by Installer Network Size

Based on research:

1. **Eaton** - Largest certified contractor network with public locator
2. **Leviton** - Large EV-Pro network (EV charging focus, not smart panels specifically)
3. **SPAN** - Growing authorized installer base (no public locator)
4. **Schneider Electric** - Relies on distributor channel + any licensed electrician

### Why Eaton is the Clear Choice

1. **Only manufacturer with searchable public locator**
2. **Active, growing certification program** (ECCN)
3. **Broad product coverage** (smart breakers work in most BR panels - very common)
4. **Geographic search capability** (essential for lead generation)
5. **Proven technology stack** (iframe-based like our existing scrapers)

---

## Recommendation: Build Eaton Scraper Only

### Why One Scraper Instead of Two?

**Original Request**: "Build scrapers for Sense energy monitoring and the top 2 smart panel manufacturers."

**Reality Check**:
- **Sense**: Program discontinued - nothing to scrape
- **Top 5 Smart Panel Manufacturers**:
  1. Eaton - ✅ Has scrapable locator
  2. SPAN - ❌ No public locator
  3. Leviton - ⚠️ Static list only (not scrapable by ZIP)
  4. Schneider Electric - ❌ Distributor locator only (not installers)
  5. (Other manufacturers have even less presence)

**Conclusion**: Only **Eaton** has a viable, scrapable installer locator for smart panel technology.

### Business Value of Eaton Scraper

**Target Contractors**: Electricians certified in modern energy management systems

**Capability Flags**:
- `has_electrical = True` (all Eaton certified contractors are electricians)
- `has_battery = True` (if involved in energy storage installations)
- `has_solar = False` (unless cross-certified with solar OEMs)

**Market Alignment with Coperniq**:
- Eaton contractors work with battery backup systems
- Smart breakers integrate with energy storage (Tesla Powerwall, etc.)
- Energy management expertise = understanding of monitoring platforms
- Overlap potential with solar/battery contractors in our existing database

**Lead Quality**:
- Certified professionals (training requirement)
- Active in modern electrification (smart panels, EV charging, energy management)
- Consumer-facing (residential installations)
- Technology-savvy (required for smart panel commissioning)

---

## Next Steps

### Immediate Action Items

1. ✅ Research complete - findings documented
2. ⏭️ Build `EatonScraper` class in `scrapers/eaton_scraper.py`
3. ⏭️ Test with ZIP 94102 (San Francisco)
4. ⏭️ Add to `ScraperFactory`
5. ⏭️ Update `config.py` if new ZIP codes needed

### Scraper Implementation Notes

**Base Class**: Inherit from `BaseDealerScraper`

**OEM Source**: `"Eaton"`

**Target URL**: https://www.eaton.com/us/en-us/products/residential/my-home/find-a-contractor.html

**Locator Technology**: iframe from Bullseye Locations (similar to SMA Solar redirect we encountered)

**Data Structure**: `StandardizedDealer` with electrical capability flags

**Capabilities**:
```python
capabilities = DealerCapabilities(
    has_electrical=True,  # All ECCN contractors are electricians
    has_battery=True,     # If energy storage work indicated
    has_solar=False,      # Unless cross-certified
    is_residential=True,
    is_commercial=True,   # Many do both
)
```

### Testing Strategy

1. **Single ZIP test**: 94102 (San Francisco, high smart home adoption)
2. **Multi-ZIP test**: CA high-value ZIPs from existing config
3. **Cross-reference check**: Match Eaton contractors against existing Generac/Tesla/Enphase databases
4. **Data quality validation**: Check for phone/domain/address completeness

### Success Criteria

- ✅ Extract at least 10 contractors from test ZIP
- ✅ Complete StandardizedDealer fields (name, phone, location)
- ✅ Proper capability flags set
- ✅ Integration with multi-OEM detector
- ✅ No duplicate entries in cross-reference database

---

## Alternative Manufacturers Investigated But Not Recommended

### Square D (Schneider Electric)
**Why Not**: Only distributor locator, not installer locator

### Leviton
**Why Not**: EV-Pro list is not ZIP-searchable; extremely large static page

### SPAN
**Why Not**: No public installer locator despite active program

### Sense
**Why Not**: Installer program discontinued entirely

---

## Appendix: Locator URLs for Reference

- **Eaton ECCN**: https://www.eaton.com/us/en-us/products/residential/my-home/find-a-contractor.html
- **Leviton EV-Pro**: https://leviton.com/products/commercial/ev-charging-commercial/ev-pro-contractor-certification-program/ev-pro-certified-contractors
- **SPAN Installer Info**: https://www.span.io/installers (no locator)
- **Schneider Electric**: https://www.se.com/us/en/work/support/locator/ (distributors only)
- **Sense**: https://sense.com/partners/sense-pro/ (program discontinued)
