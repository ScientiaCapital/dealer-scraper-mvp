# Illinois Contractor Licensing Research

**Research Date**: 2025-12-24
**Status**: ❌ **NOT VIABLE for bulk migration**
**Reason**: No bulk data access, state-level licensing limited to plumbing only

---

## Executive Summary

Illinois does **NOT** have a bulk-downloadable contractor license database comparable to Colorado DORA. Contractor licensing in Illinois is fragmented across state agencies and local jurisdictions.

**Recommendation**: **SKIP Illinois** for Phase 3. Instead, use alternative state with better data access (e.g., Washington, Maryland, or Pennsylvania).

---

## Licensing Structure by Trade

### ⚡ Electrical Contractors
- **State-Level Licensing**: ❌ **NONE**
- **Authority**: Cities and counties (e.g., Chicago, Cook County)
- **Data Access**: Individual municipal databases only
- **Bulk Download**: ❌ Not available

**Source**: [ServiceTitan Illinois HVAC Guide](https://www.servicetitan.com/licensing/hvac/illinois)

---

### 🚰 Plumbing Contractors
- **State-Level Licensing**: ✅ **YES**
- **Authority**: Illinois Department of Public Health (IDPH)
- **Database**: [IDPH Plumber License Search](https://ildohplmprod.glsuite.us/GLSuiteWeb/Clients/ILDOHPLM/PUBLIC/Verification/Plumber_License_Verification.aspx)

**Available Fields**:
- Last Name (individual plumber)
- Business Name (contractor)
- License ID
- Street, City, State, County

**Data Access**:
- ❌ **No bulk download**
- ❌ **No API**
- ✅ Web search form only (one-by-one lookup)
- ✅ Wildcard search supported (e.g., "And*" for Anderson, Andrews)

**Source**: [IDPH Plumber License Verification](https://ildohplmprod.glsuite.us/GLSuiteWeb/Clients/ILDOHPLM/PUBLIC/Verification/Plumber_License_Verification.aspx)

---

### 🌡️ HVAC Contractors
- **State-Level Licensing**: ❌ **NONE**
- **Authority**: No state requirement for HVAC professionals
- **Data Access**: Not applicable

**Source**: [ServiceTitan Illinois HVAC Guide](https://www.servicetitan.com/licensing/hvac/illinois)

---

## IDFPR Professional Licensing Dataset

**Dataset**: [Professional Licensing](https://data.illinois.gov/Business-and-Workforce/Professional-Licensing/pzzh-kp68)
**API Endpoint**: `https://data.illinois.gov/resource/pzzh-kp68.json`
**Dataset ID**: `pzzh-kp68`

**Available License Types** (61 total):
- Medical professionals (doctors, nurses, therapists)
- Legal professionals (attorneys, notaries)
- Financial professionals (accountants, real estate agents)
- Roofing Contractor (ONLY contractor type found)

**❌ NOT FOUND**:
- Electrical Contractor
- Plumbing Contractor
- HVAC Contractor
- General Contractor

**Conclusion**: IDFPR dataset is for **professional licenses** (medical, legal, financial), NOT contractor trades.

**Source**: [Illinois Open Data - Professional Licensing](https://data.illinois.gov/Business-and-Workforce/Professional-Licensing/pzzh-kp68/about_data)

---

## Cook County Registered Contractors

**Database**: [Cook County Department of Building and Zoning](https://secure.cookcountyil.gov/b_z/contractors_info.php)
**Coverage**: Cook County only (Chicago area)
**Data Access**: Web search only

**Limitation**: County-level, not statewide.

**Source**: [Cook County Contractor Search](https://secure.cookcountyil.gov/b_z/contractors_info.php)

---

## Why Illinois is NOT Viable for Bulk Migration

| **Requirement** | **Status** | **Details** |
|----------------|-----------|-------------|
| Bulk download available | ❌ | No bulk data access for plumbers; none for electrical/HVAC |
| SODA API access | ❌ | IDFPR API excludes contractor trades |
| State-level licensing | ⚠️ | Plumbing only (electrical/HVAC at local level) |
| Multi-trade detection | ❌ | Can't compare EC+PC if electrical isn't state-licensed |
| Business entity data | ⚠️ | IDPH has business names, but no bulk export |

---

## Alternative States for Phase 3

### Recommended: Washington State

**Why Washington?**
- State-level licensing for electrical, plumbing, HVAC
- Washington Department of Labor & Industries (L&I) has public data
- Known for data transparency

**Research Required**:
- Check if L&I has bulk download or SODA API
- Identify license types for EC, PC, HVAC

---

### Alternative: Maryland

**Why Maryland?**
- Maryland Department of Labor has contractor licensing
- Known for open data initiatives

---

### Alternative: Pennsylvania

**Why Pennsylvania?**
- Pennsylvania Department of State professional licensing
- Large contractor population (Pittsburgh, Philadelphia markets)

---

## Conclusion

**Phase 3 should SKIP Illinois** due to:
1. No bulk data access for plumbers (web search only)
2. No state-level electrical licensing
3. No state-level HVAC licensing
4. IDFPR dataset excludes contractor trades

**Recommended Action**: Research Washington State L&I for Phase 3 bulk migration instead.

---

## Sources

- [IDFPR Check License](https://idfpr.illinois.gov/checklicense.html)
- [Illinois Open Data - Professional Licensing](https://data.illinois.gov/Business-and-Workforce/Professional-Licensing/pzzh-kp68/about_data)
- [IDPH Plumber License Search](https://ildohplmprod.glsuite.us/GLSuiteWeb/Clients/ILDOHPLM/PUBLIC/Verification/Plumber_License_Verification.aspx)
- [ServiceTitan Illinois HVAC Licensing Guide](https://www.servicetitan.com/licensing/hvac/illinois)
- [ServiceTitan Illinois Plumbing Licensing Guide](https://www.servicetitan.com/licensing/plumbing/illinois)
- [Cook County Contractor Search](https://secure.cookcountyil.gov/b_z/contractors_info.php)
