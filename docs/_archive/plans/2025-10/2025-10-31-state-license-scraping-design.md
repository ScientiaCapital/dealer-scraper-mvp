# State Contractor License Database Scraping System

**Author**: Claude Code
**Date**: October 31, 2025
**Status**: Approved Design
**Implementation Timeline**: 10 weeks

---

## Executive Summary

This system scrapes contractor license databases from all 50 US states to enrich Coperniq's OEM contractor data and identify license-only leads. We target three license types: Electrical, Low Voltage, and HVAC. The system uses a three-tier architecture optimized for each state's data access method (bulk downloads, APIs, or browser automation).

**Primary Goal**: Improve ICP scoring accuracy by 10%+ using license metadata (trade classifications, license age, business details).

**Secondary Goal**: Achieve 20%+ cross-reference hit rate between license data and existing OEM contractor database.

---

## Business Context

### Current State
- **OEM Database**: 8,277 contractors from 10 OEM networks (Generac, Tesla, Enphase, SolarEdge, etc.)
- **Coverage**: 15 SREC states (CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
- **ICP Scoring**: Year 1 GTM-aligned scoring (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)

### Gap Analysis
State license databases reveal trade capabilities and business maturity signals that OEM dealer locators lack:
- **Trade classifications**: Multi-trade licenses indicate MEP+R capabilities
- **License age**: Original issue date reveals established businesses (O&M potential)
- **License status**: Active/expired status validates contractor legitimacy
- **Business details**: Insurance, worker counts, specialty codes enrich ICP scoring

### Target Outcomes
1. **Enrich 8K+ OEM contractors** with license metadata to improve ICP accuracy
2. **Discover 50K-200K+ license-only contractors** not in OEM networks (greenfield adoption targets)
3. **Identify multi-trade contractors** via license classifications (Electrical + HVAC = MEP+R signal)
4. **Validate contractor legitimacy** via active license status (reduce outreach waste)

---

## Architecture Overview

### Three-Tier Data Acquisition Model

The system organizes states into three tiers based on data access methods. Each tier uses optimized scraping strategies.

#### Tier 1: Bulk Download States (10-15 states)
**States**: California, Florida, Texas, and others with public data portals
**Method**: HTTP downloads of CSV/Excel exports
**Complexity**: LOW
**Data Quality**: HIGHEST (official datasets, comprehensive fields)
**Example**: California CSLB Public Data Portal provides contractor lists by classification

**Implementation**:
```python
class BulkDownloadScraper(BaseLicenseScraper):
    def scrape_licenses(self, license_types):
        # 1. HTTP GET to download bulk file
        # 2. Parse CSV/Excel with pandas
        # 3. Filter to requested license_types
        # 4. Normalize to StandardizedLicensee schema
```

#### Tier 2: API-Enabled States (5-10 states)
**States**: Massachusetts and others with REST APIs
**Method**: Paginated API requests with JSON responses
**Complexity**: MEDIUM
**Data Quality**: HIGH (structured schemas, consistent formats)
**Example**: Massachusetts Professional Licensing API returns JSON with license status, expiration, contractor details

**Implementation**:
```python
class APIClientScraper(BaseLicenseScraper):
    def scrape_licenses(self, license_types):
        # 1. Paginate through API endpoints
        # 2. Filter by license type (if supported)
        # 3. Parse JSON responses
        # 4. Normalize to StandardizedLicensee schema
        # 5. Respect rate limits
```

#### Tier 3: Custom Scraper States (30-35 states)
**States**: Remaining states requiring browser automation
**Method**: Playwright-based web scraping (reuses OEM scraper patterns)
**Complexity**: HIGH
**Data Quality**: VARIABLE (depends on HTML structure, form design)
**Example**: State-specific search forms with pagination, AJAX results, or infinite scroll

**Implementation**:
```python
class PlaywrightLicenseScraper(BaseLicenseScraper):
    def scrape_licenses(self, license_types):
        # 1. Navigate to search form
        # 2. Fill license type filter
        # 3. Submit search or paginate results
        # 4. Execute JavaScript extraction
        # 5. Handle pagination/infinite scroll
```

### Factory Pattern

```python
class LicenseScraperFactory:
    @classmethod
    def create(cls, state_code: str, mode: ScraperMode) -> BaseLicenseScraper:
        config = STATE_CONFIGS[state_code]

        if config["tier"] == "BULK":
            return BulkDownloadScraper(config["download_url"], config["format"])
        elif config["tier"] == "API":
            return APIClientScraper(config["api_url"], config.get("api_key"))
        else:  # SCRAPER tier
            return PlaywrightLicenseScraper(config["search_url"], mode)
```

---

## Data Schema

### StandardizedLicensee

We create a new data model parallel to `StandardizedDealer` (OEM contractors). This separation preserves existing OEM data while enabling cross-reference operations.

```python
@dataclass
class StandardizedLicensee:
    # Core identity
    licensee_name: str              # Individual or business name
    business_name: Optional[str]    # DBA / company name (if different)
    license_number: str
    license_type: str               # "C-10 Electrical", "HVAC Contractor"

    # License metadata
    license_status: str             # "Active", "Expired", "Suspended", "Revoked"
    issue_date: Optional[date]
    expiration_date: Optional[date]
    original_issue_date: Optional[date]  # First licensed (growth signal)

    # Contact information
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]

    # Location
    street: Optional[str]
    city: str
    state: str                      # Two-letter code
    zip: str
    county: Optional[str]

    # Business details (rich states only - CA, TX, FL)
    trade_classifications: List[str]     # ["Electrical", "Low Voltage", "Solar"]
    insurance_info: Optional[str]
    worker_count: Optional[int]
    business_type: Optional[str]         # "Corporation", "LLC", "Sole Proprietor"

    # Source tracking
    source_state: str               # "CA", "TX", "FL"
    source_tier: str                # "BULK", "API", "SCRAPER"
    scraped_date: datetime

    # Cross-reference (populated by integration script)
    matched_oem_contractors: List[str]   # OEM contractor IDs
    match_confidence: Optional[float]    # 0.0-1.0
```

### Data Normalization

Each tier's raw data flows through normalization functions that map state-specific fields to this schema:

**Examples**:
- California "C-10" → `license_type="Electrical Contractor"`
- Florida "ER" → `license_type="Electrical Contractor"`
- Texas "Electrical Contractor" → `license_type="Electrical Contractor"`

This ensures consistent comparisons across all 50 states.

### Output Files

The system produces three CSV outputs:

1. **`license_contractors_YYYYMMDD.csv`**
   All license data (separate from OEM grandmaster list)
   Columns: All `StandardizedLicensee` fields

2. **`license_oem_crossreference_YYYYMMDD.csv`**
   Contractors found in BOTH license databases AND OEM networks
   Columns: licensee_id, oem_contractor_id, match_type (phone/domain/fuzzy_name), confidence_score

3. **`license_enriched_oem_YYYYMMDD.csv`**
   Existing OEM contractors with added license metadata
   Columns: All `StandardizedDealer` fields + license_number, license_status, license_type, original_issue_date

---

## Cross-Reference & ICP Enrichment

### Multi-Signal Matching Algorithm

We reuse the proven deduplication logic from the OEM system (97.3% accuracy on 25,800 Cummins records) and extend it for license-to-OEM matching.

#### Phase 1: Phone Normalization Match (95% confidence)
1. Strip phone numbers to 10 digits (remove country code, formatting)
2. Create hash table: `phone_hash → [oem_contractor_ids]`
3. Direct lookup for instant matches
4. **Rationale**: Phone is strongest unique identifier for businesses

#### Phase 2: Domain Matching (85% confidence)
1. Extract root domains from websites: `example.com` from `www.example.com/contact`
2. Normalize to lowercase, remove subdomains
3. Create hash table: `domain_hash → [oem_contractor_ids]`
4. Cross-reference for matches
5. **Rationale**: Domains are unique but not all contractors have websites

#### Phase 3: Fuzzy Name + Location (70% confidence, validation only)
1. Normalize company names (remove "LLC", "Inc", case-insensitive)
2. Calculate Levenshtein distance (85%+ similarity threshold)
3. Require same state/county for match
4. **Rationale**: Validates Phase 1/2 matches, doesn't create new ones (high false positive risk)

### ICP Enrichment Logic

When a license match is found for an existing OEM contractor, we enhance ICP scoring:

#### License-Based Scoring Boosts

**1. MEP+R Dimension** (Multi-trade capabilities)
- Electrical + HVAC licenses → MEP+R score +20 points
- Low Voltage or Communications license → MEP+R score +10 points
- **Signal**: Multi-trade licenses reveal self-performing contractors (platform power users)

**2. Resimercial Dimension** (Market served)
- "Commercial Contractor" or "Commercial Electrical" classification → Commercial flag = TRUE
- Both residential + commercial classifications → Resimercial score +15 points
- **Signal**: License classifications hint at market served

**3. O&M Dimension** (Business maturity)
- `original_issue_date` > 10 years ago → O&M score +10 points (established, likely has service contracts)
- Recent license (<2 years) → Growth flag = TRUE (expanding, acquisition-ready)
- **Signal**: License age indicates business maturity and O&M potential

**4. Multi-OEM Validation Boost**
- Licensed contractors in OEM networks → Overall ICP score +5 points
- **Signal**: License validation confirms legitimate, active businesses

#### License-Only Contractor Scoring

Contractors found ONLY in license databases (not in OEM networks) receive separate ICP scoring focused on "adoption potential" rather than "platform consolidation":

- **Electrical license only** → 30/100 (qualified installer, no platform yet)
- **HVAC + Electrical licenses** → 50/100 (multi-trade, adoption target)
- **Commercial classification** → +15 points (larger projects, higher ACV)
- **Established (10+ years)** → +10 points (stable business, lower churn risk)

---

## Implementation Details

### File Structure

```
dealer-scraper-mvp/
├── scrapers/
│   └── license/
│       ├── __init__.py
│       ├── base_license_scraper.py      # Abstract base class
│       ├── bulk_download_scraper.py     # Tier 1 implementation
│       ├── api_client_scraper.py        # Tier 2 implementation
│       ├── playwright_scraper.py        # Tier 3 implementation
│       └── license_scraper_factory.py   # Factory pattern
├── config/
│   └── state_license_configs.py         # 50 state configurations
├── targeting/
│   ├── license_cross_reference.py       # Multi-signal matching
│   └── license_icp_enrichment.py        # ICP scoring boosts
├── scripts/
│   ├── run_state_license_scraping.py    # Orchestration script
│   ├── integrate_license_with_oem.py    # Cross-reference + enrichment
│   └── test_license_scraper.py          # Single-state testing
└── docs/
    └── plans/
        └── 2025-10-31-state-license-scraping-design.md  # This file
```

### State Configuration Example

```python
# config/state_license_configs.py
STATE_CONFIGS = {
    "CA": {
        "tier": "BULK",
        "download_url": "https://www.cslb.ca.gov/onlineservices/dataportal/",
        "format": "csv",
        "license_types": {
            "Electrical": ["C-10"],
            "LowVoltage": ["C-7"],
            "HVAC": ["C-20"]
        },
        "estimated_volume": 50000,
        "notes": "CSLB Public Data Portal - downloadable CSV by classification"
    },
    "MA": {
        "tier": "API",
        "api_url": "https://licensing.api.secure.digital.mass.gov/",
        "api_key": None,  # Public API
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "HVAC": ["HVAC Contractor"]
        },
        "estimated_volume": 8000,
        "notes": "REST API with JSON responses, pagination required"
    },
    "TX": {
        "tier": "BULK",
        "download_url": "https://www.tdlr.texas.gov/apps/",
        "format": "xlsx",
        "license_types": {
            "Electrical": ["Electrical Contractor"],
            "LowVoltage": ["Low Voltage Contractor"],
            "HVAC": ["Air Conditioning Contractor"]
        },
        "estimated_volume": 35000,
        "notes": "TDLR databases - multiple Excel files per license type"
    },
    # ... 47 more states
}
```

### Orchestration Script

```python
# scripts/run_state_license_scraping.py
"""
Orchestrates scraping across all 50 states in priority order.
Usage:
  python3 run_state_license_scraping.py --states ALL --license-types Electrical LowVoltage HVAC
  python3 run_state_license_scraping.py --states CA TX FL --license-types Electrical
"""

def main(states: List[str], license_types: List[str], mode: ScraperMode):
    results = []
    checkpoint_file = "output/license_scraping_checkpoint.json"

    # Resume from checkpoint if exists
    completed_states = load_checkpoint(checkpoint_file)
    remaining = [s for s in states if s not in completed_states]

    # Phase 1: Bulk download states (fastest, highest quality)
    bulk_states = [s for s in remaining if STATE_CONFIGS[s]["tier"] == "BULK"]
    logger.info(f"Starting Tier 1 (Bulk): {len(bulk_states)} states")

    for state in bulk_states:
        try:
            scraper = LicenseScraperFactory.create(state, mode)
            licensees = scraper.scrape_licenses(license_types)
            results.extend(licensees)
            completed_states.add(state)

            # Checkpoint every 5 states for Tier 1
            if len(completed_states) % 5 == 0:
                save_checkpoint(checkpoint_file, completed_states, results)

        except Exception as e:
            logger.error(f"State {state} failed: {e}")
            continue  # Don't halt entire run

    # Phase 2: API states (fast, structured data)
    api_states = [s for s in remaining if STATE_CONFIGS[s]["tier"] == "API"]
    logger.info(f"Starting Tier 2 (API): {len(api_states)} states")

    for state in api_states:
        try:
            scraper = LicenseScraperFactory.create(state, mode)
            licensees = scraper.scrape_licenses(license_types)
            results.extend(licensees)
            completed_states.add(state)

            # Checkpoint every 3 states for Tier 2
            if len(completed_states) % 3 == 0:
                save_checkpoint(checkpoint_file, completed_states, results)

        except Exception as e:
            logger.error(f"State {state} failed: {e}")
            continue

    # Phase 3: Scraper states (slow, high effort)
    scraper_states = [s for s in remaining if STATE_CONFIGS[s]["tier"] == "SCRAPER"]
    logger.info(f"Starting Tier 3 (Scraper): {len(scraper_states)} states")

    for state in scraper_states:
        try:
            scraper = LicenseScraperFactory.create(state, mode)
            licensees = scraper.scrape_licenses(license_types)
            results.extend(licensees)
            completed_states.add(state)

            # Checkpoint every 1 state for Tier 3 (most fragile)
            save_checkpoint(checkpoint_file, completed_states, results)

        except Exception as e:
            logger.error(f"State {state} failed: {e}")
            continue

    # Final deduplication and output
    deduped = deduplicate_licensees(results)
    save_to_csv(deduped, f"output/license_contractors_{datetime.now().strftime('%Y%m%d')}.csv")

    logger.info(f"Complete: {len(deduped)} contractors from {len(completed_states)} states")
```

### Cross-Reference Integration Script

```python
# scripts/integrate_license_with_oem.py
"""
Cross-references license data with existing OEM contractor database.
Enriches OEM contractors with license metadata and applies ICP scoring boosts.
"""

def main():
    # Load both datasets
    oem_contractors = load_csv("output/grandmaster_list_expanded_20251029.csv")
    license_contractors = load_csv("output/license_contractors_20251031.csv")

    logger.info(f"OEM contractors: {len(oem_contractors)}")
    logger.info(f"License contractors: {len(license_contractors)}")

    # Multi-signal matching
    matches = cross_reference_contractors(oem_contractors, license_contractors)
    logger.info(f"Cross-reference matches: {len(matches)} ({len(matches)/len(oem_contractors)*100:.1f}%)")

    # Enrich OEM contractors with license metadata
    enriched_oem = enrich_oem_with_licenses(oem_contractors, matches)

    # Apply ICP scoring boosts
    scored_oem = apply_license_icp_boosts(enriched_oem)

    # Calculate improvement metrics
    old_avg_score = np.mean([c.coperniq_score for c in oem_contractors])
    new_avg_score = np.mean([c.coperniq_score for c in scored_oem])
    improvement = (new_avg_score - old_avg_score) / old_avg_score * 100

    logger.info(f"ICP score improvement: {improvement:.1f}%")

    # Output files
    timestamp = datetime.now().strftime('%Y%m%d')
    save_csv(matches, f"output/license_oem_crossreference_{timestamp}.csv")
    save_csv(enriched_oem, f"output/license_enriched_oem_{timestamp}.csv")
    save_csv(license_contractors, f"output/license_contractors_{timestamp}.csv")

    logger.info("Integration complete")
```

---

## Error Handling & Quality Assurance

### Tier-Specific Error Handling

#### Tier 1: Bulk Downloads
- **HTTP errors (404, 500)**: Retry with exponential backoff (3 attempts, 2s → 4s → 8s)
- **File format changes**: Schema validation, alert on unexpected columns
- **Corrupted downloads**: MD5 checksum verification before parsing
- **Mitigation**: Download failures are critical but rare; manual intervention acceptable

#### Tier 2: APIs
- **Rate limiting (429)**: Exponential backoff, respect `Retry-After` headers
- **API key expiration**: Alert to refresh credentials, cache last successful response
- **JSON schema changes**: Version API requests, validate response structure
- **Mitigation**: APIs are most stable tier; graceful degradation to cached data

#### Tier 3: Playwright Scrapers
- **CAPTCHA detection**: Switch to RUNPOD mode (residential IPs), add human-like delays
- **Form selector changes**: CSS selector fallback chains (ID → class → XPath)
- **AJAX timeout**: Configurable wait times (3s default, 10s max)
- **Bot detection**: Stealth mode (from SMA Solar breakthrough), rotate user agents
- **Mitigation**: Most fragile tier; checkpoint saves after every state

### Checkpoint & Resume Pattern

```python
def scrape_with_checkpoints(states: List[str], checkpoint_file: str):
    completed = load_checkpoint(checkpoint_file)
    remaining = [s for s in states if s not in completed]
    results = load_checkpoint_data(checkpoint_file)

    for state in remaining:
        try:
            licensees = scrape_state(state)
            results.extend(licensees)
            completed.add(state)
            save_checkpoint(checkpoint_file, completed, results)
        except Exception as e:
            logger.error(f"State {state} failed: {e}")
            continue  # Resume with next state

    return results
```

### Testing Strategy

#### Unit Tests (per scraper tier)
- **Bulk downloaders**: Mock HTTP responses with sample CSV/Excel files
- **API clients**: Mock API responses with sample JSON payloads
- **Playwright scrapers**: Screenshot tests to detect form selector changes

#### Integration Tests
- **End-to-end test**: Scrape 3 states (1 per tier) → cross-reference → enrich → validate output
- **Cross-reference accuracy**: Test against 100 known OEM contractors with licenses
- **Schema validation**: Ensure all 50 states map to `StandardizedLicensee` without errors

#### Data Quality Validation
- **Phone normalization**: >95% valid 10-digit US numbers
- **License status distribution**: Expect 80%+ "Active", alert if <50%
- **Contact info completeness**: Track % with phone, email, address per state
- **Cross-reference hit rate**: Target 20%+, alert if <10%

### Quality Metrics Dashboard

Track per state:
- **Contractors scraped**: Actual vs estimated volume
- **Fields populated**: % with phone, email, license_type, license_status
- **Match rate**: % found in OEM database
- **Scrape duration**: Seconds per contractor
- **Error rate**: Failed records / total records

---

## Timeline & Milestones

### Phase 1: Foundation (Weeks 1-2)
**Deliverables**:
- Base classes: `BaseLicenseScraper`, `StandardizedLicensee`
- Factory pattern: `LicenseScraperFactory`
- State configs: All 50 states classified into tiers
- Tier 1 scrapers: CA, FL, TX bulk downloaders

**Output**: 50K-100K contractors from 3 high-value states

### Phase 2: API Integration (Week 3)
**Deliverables**:
- Tier 2 API client scraper
- Massachusetts implementation
- Identify 5-10 additional API states

**Output**: +10K-20K contractors from API states

### Phase 3: Custom Scrapers (Weeks 4-8)
**Deliverables**:
- Tier 3 Playwright scraper base class
- 30-35 state-specific scrapers (5-7 per week)
- Checkpoint/resume system
- Error handling for bot detection, CAPTCHAs

**Output**: +50K-200K contractors from remaining states

### Phase 4: Cross-Reference Engine (Week 9)
**Deliverables**:
- Multi-signal matching algorithm (phone, domain, fuzzy name)
- Cross-reference integration script
- ICP enrichment logic
- Quality validation tests

**Output**: Cross-reference dataset, enriched OEM contractors

### Phase 5: Validation & GTM (Week 10)
**Deliverables**:
- ICP scoring accuracy analysis
- GTM deliverable updates (top prospects, customer match lists)
- Documentation and runbooks
- Production deployment

**Output**: Production-ready system with validated ICP improvements

---

## Success Criteria

### Primary: ICP Enrichment Accuracy (+10%)
**Measurement**: Compare ICP scores before/after license enrichment
- **Baseline**: Current ICP scoring without license data
- **Target**: 10%+ improvement in scoring accuracy via license metadata
- **Validation**: Manual review of 100 contractors to confirm improved quality

### Secondary: Cross-Reference Hit Rate (20%+)
**Measurement**: % of license contractors found in OEM database
- **Formula**: `(license_oem_matches / total_license_contractors) * 100`
- **Target**: 20%+ hit rate (validates both datasets)
- **Benchmark**: OEM deduplication achieved 97.3% accuracy

### Tertiary: Data Completeness (80%+ for Tier 1 & 2)
**Measurement**: % of contractors with phone + license metadata
- **Tier 1 (Bulk)**: 90%+ completeness (official datasets)
- **Tier 2 (API)**: 85%+ completeness (structured schemas)
- **Tier 3 (Scraper)**: 60%+ completeness (variable HTML)
- **Critical fields**: phone, license_type, license_status, license_number

---

## Risk Mitigation

### Technical Risks

**Risk**: State websites change structure, breaking scrapers
**Mitigation**: CSS selector fallback chains, screenshot tests, checkpoint saves

**Risk**: Bot detection blocks Tier 3 scrapers
**Mitigation**: Stealth mode, residential IPs (RUNPOD), human-like delays

**Risk**: API rate limits slow Tier 2 scraping
**Mitigation**: Exponential backoff, cache responses, spread requests over days

**Risk**: Bulk download portals require authentication
**Mitigation**: Manual download fallback, document login procedures

### Operational Risks

**Risk**: 10-week timeline too aggressive for 50 states
**Mitigation**: Phased rollout (Tier 1 → Tier 2 → Tier 3), prioritize high-value states

**Risk**: License data quality varies by state
**Mitigation**: Quality metrics per state, focus ICP enrichment on high-quality states

**Risk**: Cross-reference hit rate <20%
**Mitigation**: Phone normalization accuracy already proven at 96.5%, domain matching adds backup

---

## Future Enhancements

### Automated Refresh (Post-MVP)
- Monthly scheduled scraping (cron job or Airflow DAG)
- Incremental updates (only new licenses since last run)
- Historical tracking (license expirations, status changes)

### Advanced Enrichment (Year 2)
- Apollo API integration for employee count, revenue estimates
- LinkedIn scraping for company size signals
- Yelp/Google Reviews for reputation scoring

### Machine Learning (Year 2+)
- Predict contractor ICP tier from license data alone
- Identify high-value acquisition targets (growing, multi-trade)
- Forecast license renewal likelihood (churn risk)

---

## Conclusion

This system extends Coperniq's lead generation capability from 10 OEM networks to all 50 state license databases. The three-tier architecture optimizes for each state's data access method while maintaining a consistent data model. Cross-reference matching enriches existing OEM contractors with license metadata, improving ICP scoring accuracy by 10%+.

The phased rollout (Tier 1 → Tier 2 → Tier 3) validates the approach on easy states before tackling custom scrapers. Checkpoint/resume patterns and tier-specific error handling ensure robust execution across heterogeneous state systems.

**Key Innovation**: License data reveals trade capabilities (MEP+R), business maturity (O&M), and market served (resimercial) that OEM dealer locators lack. This enrichment transforms raw contractor lists into scored, qualified leads.

**Next Steps**: Create git worktree, implement base classes, build Tier 1 scrapers for CA/FL/TX.
