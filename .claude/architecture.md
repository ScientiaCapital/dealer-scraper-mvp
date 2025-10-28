# Technical Architecture - Dealer Scraper MVP

**Last Updated**: 2025-10-28

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      DEALER SCRAPER MVP                          │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Scraping   │───▶│ Deduplication│───▶│   Targeting  │      │
│  │   Layer      │    │   & Cross-   │    │  & Scoring   │      │
│  │              │    │   Reference  │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────────────────────────────────────────────┐      │
│  │            Output Layer (CSV/JSON Export)            │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                   │
│  Future Integration:                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Apollo   │  │  Clay    │  │  Close   │  │ Outreach │       │
│  │ Enrich   │  │ Waterfall│  │   CRM    │  │ Automation│      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Core Architecture Patterns

### 1. Factory Pattern (Scraper Creation)

**Location**: `scrapers/scraper_factory.py`

```python
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Single interface for all 18 OEM scrapers
scraper = ScraperFactory.create("Generac", mode=ScraperMode.PLAYWRIGHT)
dealers = scraper.scrape_zip_code("10001")
```

**Design Benefits**:
- Centralized scraper registration
- Consistent interface across all OEMs
- Easy to add new scrapers (register + implement)
- Supports multiple aliases per scraper

**Registration Pattern**:
```python
# In scraper file (e.g., mitsubishi_scraper.py)
ScraperFactory.register("Mitsubishi Electric", MitsubishiScraper)
ScraperFactory.register("Mitsubishi", MitsubishiScraper)  # Alias
```

### 2. Template Method Pattern (Base Scraper)

**Location**: `scrapers/base_scraper.py`

```python
class BaseDealerScraper(ABC):
    """Abstract base class defining scraping workflow"""

    def scrape_zip_code(self, zip_code: str):
        """Template method (implemented in base)"""
        if self.mode == ScraperMode.PLAYWRIGHT:
            return self._scrape_with_playwright(zip_code)
        elif self.mode == ScraperMode.RUNPOD:
            return self._scrape_with_runpod(zip_code)
        # ...

    @abstractmethod
    def _scrape_with_playwright(self, zip_code: str):
        """Subclasses implement specific scraping logic"""
        pass
```

**Workflow Steps** (all scrapers follow same pattern):
1. Navigate to dealer locator URL
2. Handle cookie consent (if needed)
3. Fill ZIP code into search input
4. Click search button
5. Wait for AJAX results to load
6. Execute JavaScript extraction script
7. Parse JSON results into StandardizedDealer objects
8. Deduplicate by phone number
9. Return list of dealers

### 3. Strategy Pattern (Scraping Modes)

**Three execution strategies**:

```python
class ScraperMode(Enum):
    PLAYWRIGHT = "playwright"    # Local browser automation
    RUNPOD = "runpod"             # Cloud serverless
    BROWSERBASE = "browserbase"   # Future cloud option
```

**Mode Selection**:
- **PLAYWRIGHT** (Primary): Local Playwright, manual MCP interaction, free
- **RUNPOD** (Deployed): Cloud HTTP API, auto-scaling, ~$0.001/ZIP
- **BROWSERBASE** (Placeholder): Future integration

## Data Architecture

### Unified Data Model

**StandardizedDealer** - Single schema across all 18 OEMs:

```python
@dataclass
class StandardizedDealer:
    # Core identification (required)
    name: str
    phone: str           # Normalized to 10 digits
    domain: str          # Root domain (no www/subdomain)
    website: str

    # Location (required)
    street: str
    city: str
    state: str
    zip: str
    address_full: str

    # Quality signals (optional)
    rating: float = 0.0           # 0-5 scale
    review_count: int = 0
    tier: str = "Standard"        # OEM-specific tier
    certifications: List[str] = field(default_factory=list)

    # Distance from searched ZIP
    distance: str = ""            # "8.3 mi"
    distance_miles: float = 0.0   # 8.3

    # OEM source tracking
    oem_source: str = ""          # "Generac", "Tesla", etc.
    scraped_from_zip: str = ""

    # Enrichment fields (populated later)
    apollo_enriched: bool = False
    employee_count: int = 0
    estimated_revenue: str = ""
    linkedin_url: str = ""

    # Coperniq ICP scoring
    coperniq_score: int = 0           # 0-100 total
    multi_oem_score: int = 0          # 0-100 (multi-OEM dimension)
    srec_state_priority: str = ""     # "HIGH", "MEDIUM", "LOW"
    itc_urgency: str = ""             # "CRITICAL", "HIGH", "MEDIUM", "LOW"
```

### Capability Tracking

**DealerCapabilities** - Multi-dimensional tracking:

```python
@dataclass
class DealerCapabilities:
    # Product capabilities (auto-detected from OEM)
    has_generator: bool = False
    has_solar: bool = False
    has_battery: bool = False
    has_microinverters: bool = False
    has_inverters: bool = False
    has_hvac: bool = False

    # Trade capabilities (inferred from products)
    has_electrical: bool = False
    has_roofing: bool = False
    has_plumbing: bool = False

    # Business characteristics
    is_commercial: bool = False    # From tier/certifications
    is_residential: bool = False   # Default true
    is_gc: bool = False            # General contractor
    is_sub: bool = False           # Specialized sub

    # OEM certifications (populated by multi-OEM detector)
    oem_certifications: Set[str] = field(default_factory=set)
    capability_count: int = 0
```

**Capability Detection Logic**:
```python
# In scraper implementation
capabilities = DealerCapabilities()
capabilities.has_hvac = True
capabilities.has_electrical = True  # HVAC requires electrical
if tier == "Diamond Commercial":
    capabilities.is_commercial = True
    capabilities.is_residential = True  # VRF = resimercial
```

## Deduplication Architecture

### Multi-Signal Matching Algorithm

**Location**: `scrapers/base_scraper.py:deduplicate_by_phone()`

```python
def deduplicate_by_phone(self):
    """Three-tier matching strategy"""
    seen = {}

    for dealer in self.dealers:
        # Primary signal: Phone (10 digits, normalized)
        phone_key = re.sub(r'[^0-9]', '', dealer.phone or '')

        # Secondary signal: Domain (root only)
        domain = self._extract_root_domain(dealer.domain or dealer.website)

        # Tertiary signal: Fuzzy name matching
        name_normalized = dealer.name.upper().strip()

        # Matching logic
        if phone_key in seen:
            existing = seen[phone_key]

            # Keep better quality (more reviews, higher rating, more data)
            if self._is_better_quality(dealer, existing):
                seen[phone_key] = dealer
        else:
            seen[phone_key] = dealer

    self.dealers = list(seen.values())
```

**Quality Scoring** (for duplicate resolution):
```python
def _is_better_quality(self, new, existing):
    """Prefer dealer with more information/quality signals"""

    # 1. More reviews wins
    if new.review_count != existing.review_count:
        return new.review_count > existing.review_count

    # 2. Higher tier wins
    tier_rank = {"PowerPro Premier": 5, "Platinum": 4, ...}
    if tier_rank.get(new.tier, 0) != tier_rank.get(existing.tier, 0):
        return tier_rank.get(new.tier, 0) > tier_rank.get(existing.tier, 0)

    # 3. More fields populated wins
    new_fields = sum([bool(new.website), bool(new.domain), bool(new.street)])
    existing_fields = sum([bool(existing.website), ...])
    return new_fields > existing_fields
```

### Cross-OEM Reference Detection

**Location**: `analysis/multi_oem_detector.py`

```python
class MultiOEMDetector:
    """Identifies contractors certified with 2-3+ OEM brands"""

    def find_matches(self, dealers: List[StandardizedDealer]):
        """
        Matching strategy:
        1. Primary: Phone number (normalized)
        2. Secondary: Domain (root domain)
        3. Validation: Fuzzy name matching (high threshold)
        """

        matches = defaultdict(list)

        for dealer in dealers:
            phone_key = self._normalize_phone(dealer.phone)
            domain_key = self._extract_root_domain(dealer.domain)

            # Create composite key for matching
            if phone_key:
                matches[('phone', phone_key)].append(dealer)
            if domain_key:
                matches[('domain', domain_key)].append(dealer)

        # Filter to multi-OEM only (2+ different sources)
        multi_oem = []
        for key, dealers_list in matches.items():
            oem_sources = set(d.oem_source for d in dealers_list)
            if len(oem_sources) >= 2:
                multi_oem.append(self._merge_dealers(dealers_list))

        return multi_oem
```

**Confidence Scoring**:
- **100%**: All 3 signals match (phone + domain + fuzzy name)
- **90%**: 2 signals match (phone + domain OR phone + fuzzy name)
- **80%**: Phone only (most common, still reliable)

## Scraping Implementation

### Generic Scraper Pattern

**Used by 13 OEMs**: Briggs, Cummins, Kohler, Fronius, SMA, Sol-Ark, GoodWe, Growatt, Sungrow, ABB, Delta, Tigo, SimpliPhi, Mitsubishi

**Core Implementation** (example: Mitsubishi):

```python
class MitsubishiScraper(BaseDealerScraper):
    OEM_NAME = "Mitsubishi Electric"
    DEALER_LOCATOR_URL = "https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor"

    def _scrape_with_playwright(self, zip_code: str):
        """Playwright automation using MCP"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Navigate
            page.goto(self.DEALER_LOCATOR_URL, timeout=60000)
            time.sleep(3)

            # 2. Cookie consent
            try:
                page.click('button:has-text("Accept")', timeout=3000)
                time.sleep(1)
            except:
                pass

            # 3. Custom navigation (for Mitsubishi: click Commercial tab)
            page.click('text=Commercial building', timeout=5000)
            time.sleep(2)

            # 4. Fill ZIP
            page.fill('[name="zipCode"]', zip_code)
            time.sleep(1)

            # 5. Click search
            page.click('button:has-text("Submit")')
            time.sleep(5)  # Wait for AJAX

            # 6. Execute extraction JavaScript
            extraction_script = self.get_extraction_script()
            dealers_json = page.evaluate(extraction_script)

            # 7. Parse to StandardizedDealer objects
            dealers = [self._json_to_dealer(d, zip_code) for d in dealers_json]

            browser.close()
            return dealers
```

### JavaScript Extraction Pattern

**In-browser extraction** (returns JSON array):

```javascript
() => {
  const contractors = [];
  const seen = new Set();  // In-browser deduplication

  // Find all contractor cards
  const nameElements = document.querySelectorAll('h3');

  nameElements.forEach(h3 => {
    const name = h3.textContent.trim();

    // Skip non-contractor elements
    if (name.includes('training') || name.length < 5) return;

    // Find parent container with all data
    let container = h3.parentElement;
    while (container && !container.querySelector('a[href^="tel:"]')) {
      container = container.parentElement;
    }
    if (!container) return;

    // Extract phone (normalized)
    let phone = '';
    const phoneLink = container.querySelector('a[href^="tel:"]');
    if (phoneLink) {
      phone = phoneLink.href.replace(/[^0-9]/g, '');
      // Remove country code prefix
      if (phone.length === 11 && phone[0] === '1') {
        phone = phone.substring(1);
      }
    }

    // Extract location (avoid badge text contamination)
    const containerText = container.innerText || container.textContent || '';
    const locationMatch = containerText.match(/(?:^|[\\n\\r])([A-Za-z][A-Za-z ]+?), *([A-Z]{2}) +([0-9]{5})/);
    let city = '', state = '', zip = '';
    if (locationMatch) {
      city = locationMatch[1].trim();
      state = locationMatch[2];
      zip = locationMatch[3];
    }

    // Extract website
    let website = '';
    const links = container.querySelectorAll('a[href^="http"]');
    for (const link of links) {
      if (!link.href.includes('tel:') && !link.href.includes('google.com')) {
        website = link.href;
        break;
      }
    }

    // Deduplicate by composite key
    const key = `${name}|${phone}|${city}|${state}|${zip}`;
    if (!seen.has(key) && phone && city && state && zip) {
      seen.add(key);
      contractors.push({
        name, phone, website: website || '',
        street: '',  // Not available in these results
        city, state, zip,
        address_full: `${city}, ${state} ${zip}`,
        rating: 0.0,
        review_count: 0,
        tier: 'Diamond Commercial',
        certifications: ['Diamond Commercial Contractor', 'VRF Certified'],
        distance: '', distance_miles: 0.0
      });
    }
  });

  return contractors;
}
```

**Key Patterns**:
1. **In-browser deduplication**: Use `Set` to avoid duplicates before returning
2. **Defensive parsing**: Check for null/undefined before accessing properties
3. **Regex escaping**: Double-escape backslashes in Python strings (`[\\n\\r]`)
4. **Selective matching**: Skip irrelevant elements early to avoid contamination

### Custom Scraper Pattern

**Used by 4 OEMs**: Generac, Tesla, Enphase, SolarEdge

**Differences from generic**:
- Custom navigation logic (multi-step forms, dropdowns, etc.)
- API-based extraction (some OEMs expose JSON endpoints)
- Complex pagination handling
- Authentication/session management

**Example**: Generac PowerPro Premier has custom tier detection logic

## ICP Scoring Architecture

### Year 1 GTM-Aligned Scoring

**Location**: `targeting/icp_filter.py`

```python
class ICPScorer:
    """Multi-dimensional 0-100 scoring"""

    DIMENSION_WEIGHTS = {
        'resimercial': 0.35,   # Residential + Commercial
        'multi_oem': 0.25,     # 3-4+ OEM certifications
        'mep_r': 0.25,         # Multi-trade (MEP+Roofing)
        'o_m': 0.15            # Operations & Maintenance
    }

    def score_dealer(self, dealer: StandardizedDealer):
        """Calculate 0-100 ICP score"""

        # 1. Resimercial score (0-35 points)
        resimercial = 0
        if dealer.capabilities.is_commercial and dealer.capabilities.is_residential:
            resimercial = 35  # Both = full points
        elif dealer.capabilities.is_commercial:
            resimercial = 20  # Commercial only = partial
        elif dealer.capabilities.is_residential:
            resimercial = 10  # Residential only = low

        # 2. Multi-OEM score (0-25 points)
        oem_count = len(dealer.capabilities.oem_certifications)
        if oem_count >= 3:
            multi_oem = 25
        elif oem_count == 2:
            multi_oem = 15
        else:
            multi_oem = 5

        # 3. MEP+R score (0-25 points)
        trade_count = sum([
            dealer.capabilities.has_electrical,
            dealer.capabilities.has_hvac,
            dealer.capabilities.has_plumbing,
            dealer.capabilities.has_roofing
        ])
        mep_r = min(trade_count * 8, 25)  # 8 points per trade, max 25

        # 4. O&M score (0-15 points)
        # Based on tier, certifications, review count
        o_m = self._calculate_om_score(dealer)

        total = resimercial + multi_oem + mep_r + o_m
        return min(total, 100)
```

**ICP Tiers**:
- **PLATINUM** (80-100): Ideal customers, immediate outreach
- **GOLD** (60-79): Strong fit, high priority
- **SILVER** (40-59): Good fit, nurture campaign
- **BRONZE** (<40): Monitor, low priority

### SREC State Filtering

**Location**: `targeting/srec_itc_filter.py`

```python
SREC_STATES = {
    'HIGH': ['CA', 'TX', 'PA', 'MA', 'NJ', 'FL'],      # Primary focus
    'MEDIUM': ['NY', 'OH', 'MD', 'DC', 'DE', 'NH', 'RI', 'CT', 'IL']
}

ITC_URGENCY = {
    'CRITICAL': 'Commercial (safe harbor by Jun 30, 2026)',
    'HIGH': 'Residential (ITC expires Dec 31, 2025)',
    'MEDIUM': 'SREC state (sustainable post-ITC)',
    'LOW': 'Non-SREC state'
}
```

## Configuration Architecture

### ZIP Code Selection Strategy

**Location**: `config.py`

**Criteria** (from 2024-2025 Census ACS data):
- Median household income: $150K-$250K+
- High property values
- Solar/battery/generator buyer demographics
- SREC state location

**Coverage**:
- **15 SREC states** × **9-10 ZIPs per state** = **140 total ZIPs**
- Balanced: Major metros + wealthy suburbs
- Examples:
  - CA: SF Bay (94102, 94301), LA (90210), SD (92101), SAC (95814)
  - TX: Houston (77002), Dallas (75201), Austin (78701)
  - PA: Philadelphia (19102), Pittsburgh (15222)

### Environment Configuration

**Location**: `.env` (gitignored)

```bash
# Scraping
RUNPOD_API_KEY=...
RUNPOD_ENDPOINT_ID=...

# Enrichment (future)
APOLLO_API_KEY=...
CLAY_WEBHOOK_URL=...

# CRM (future)
CLOSE_API_KEY=...

# Outreach (future)
SENDGRID_API_KEY=...
TWILIO_ACCOUNT_SID=...
```

## Performance Characteristics

### Scraping Performance

**Playwright (Local)**:
- Time per ZIP: ~5-6 seconds
- Concurrency: Sequential (1 ZIP at a time)
- Cost: $0 (local compute)
- Scalability: Limited by local resources

**RunPod (Cloud)**:
- Time per ZIP: ~3-4 seconds (singleton browser pattern)
- Concurrency: Auto-scaling (0→N workers)
- Cost: ~$0.001 per ZIP ($0.14 per 140-ZIP run)
- Scalability: Unlimited (serverless)

### National Scrape Estimates

**Single OEM** (140 ZIPs):
- Playwright: ~12-14 minutes
- RunPod: ~7-8 minutes (with concurrency)

**All 18 OEMs** (140 ZIPs × 18):
- Playwright: ~3.5-4 hours (sequential)
- RunPod: ~1-1.5 hours (parallel workers)

### Memory Usage

- **Per scraper instance**: ~50-100MB
- **Browser instance**: ~200-300MB
- **Data in memory**: ~1-5MB per 100 dealers

## Integration Points (Future)

### Apollo Enrichment

```python
# Planned integration
from enrichment.apollo_enricher import ApolloEnricher

enricher = ApolloEnricher(api_key=os.getenv('APOLLO_API_KEY'))
enriched = enricher.enrich_dealer(dealer)
# Returns: employee_count, estimated_revenue, linkedin_url
```

### Close CRM Import

```python
# Planned integration
from integrations.close_crm import CloseCRMImporter

importer = CloseCRMImporter(api_key=os.getenv('CLOSE_API_KEY'))
importer.bulk_import(dealers, source="Mitsubishi Diamond Commercial")
# Creates leads + Smart Views by ICP tier
```

### Clay Waterfall

```python
# Planned integration
from enrichment.clay_waterfall import ClayWebhook

clay = ClayWebhook(webhook_url=os.getenv('CLAY_WEBHOOK_URL'))
clay.trigger_enrichment(dealers)
# Advanced waterfall: Apollo → Hunter → Clearbit → etc.
```

## Testing Architecture

### Test Harness Pattern

**Location**: `scripts/test_*.py`

```python
#!/usr/bin/env python3
"""Test harness for single-ZIP validation"""

from scrapers.mitsubishi_scraper import MitsubishiScraper
from scrapers.base_scraper import ScraperMode

# Quick test before national run
scraper = MitsubishiScraper(mode=ScraperMode.PLAYWRIGHT)
dealers = scraper.scrape_zip_code("10001")

print(f"Found {len(dealers)} contractors")
for dealer in dealers[:3]:
    print(f"  {dealer.name} | {dealer.phone} | {dealer.tier}")
```

**Purpose**:
- Validate scraper works on single ZIP
- Inspect extraction quality
- Test deduplication logic
- Verify field mapping

### Inspection Scripts

**Location**: `scripts/inspect_*.py`

**Purpose**: Manual Playwright MCP workflow documentation
- Step-by-step instructions for manual inspection
- Expected DOM structure
- Field extraction strategy
- Debugging guidance

## Error Handling

### Graceful Degradation

```python
def _scrape_with_playwright(self, zip_code: str):
    try:
        # Main scraping logic
        dealers = self._extract_dealers(page)
    except TimeoutError:
        self.logger.warning(f"Timeout on {zip_code}, returning empty")
        return []
    except Exception as e:
        self.logger.error(f"Error on {zip_code}: {e}")
        return []
    finally:
        browser.close()
```

### Retry Logic (Future)

```python
@retry(max_attempts=3, backoff=2.0)
def _scrape_with_runpod(self, zip_code: str):
    # Automatic retry on transient failures
    pass
```

## Security & Best Practices

### API Key Management
- ✅ All keys in `.env` (gitignored)
- ✅ Never hardcoded in source
- ✅ Loaded via `os.getenv()`
- ⏳ Future: Secrets manager (AWS Secrets Manager, 1Password)

### Rate Limiting
- ✅ Built-in delays (3-5 seconds between requests)
- ✅ Sequential ZIP processing (no parallel hammering)
- ⏳ Future: Adaptive rate limiting based on response times

### Data Privacy
- ✅ Public dealer locator data only (no scraping of user accounts)
- ✅ Phone numbers normalized but not encrypted (public info)
- ⏳ Future: GDPR compliance flags (for EU contractors)

---

**Architecture Status**: Production-ready for 18 OEMs, scalable to 25+ OEMs 🏗️
