# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web scraper for the Generac dealer locator (https://www.generac.com/dealer-locator/). It extracts dealer information including ratings, tiers, contact details, and locations.

**Current State**: Three operational modes:
1. **PLAYWRIGHT** - Manual MCP Playwright tools (local development)
2. **RUNPOD** - Automated cloud Playwright API (production)
3. **BROWSERBASE** - Alternative cloud option (not yet implemented)

## Architecture

### Two-Phase Design

1. **extraction.js** - JavaScript extraction logic that runs in-browser via `mcp__playwright__browser_evaluate`
   - Uses phone links (`a[href^="tel:"]`) as anchors to find dealer cards
   - Traverses DOM upward to find container with distance element
   - Extracts 15 fields per dealer through DOM parsing and regex
   - Returns filtered array of dealer objects

2. **scraper.py** - Python wrapper with multi-mode architecture
   - `ScraperMode.PLAYWRIGHT` - Local MCP Playwright tools (manual execution)
   - `ScraperMode.RUNPOD` - Cloud Playwright API via HTTP (automated)
   - `ScraperMode.BROWSERBASE` - Alternative cloud option (future)
   - Provides deduplication, export (JSON/CSV), and filtering utilities

### Configuration Separation

**config.py** centralizes all configuration:
- `EXTRACTION_SCRIPT` - The full JavaScript from extraction.js as a Python string
- `SELECTORS` - CSS selectors for form elements
- `ZIP_CODES_*` - Predefined ZIP code lists for different regions
- `WAIT_AFTER_SEARCH` / `WAIT_BETWEEN_ZIPS` - Timing constants
- `RUNPOD_API_KEY` / `RUNPOD_ENDPOINT_ID` / `RUNPOD_API_URL` - RunPod cloud configuration

## MCP Playwright Workflow

The scraper follows a 6-step manual workflow:

```python
# 1. Navigate to dealer locator
mcp__playwright__browser_navigate({"url": "https://www.generac.com/dealer-locator/"})

# 2. Dismiss cookie dialog (MUST do first or interactions will fail)
mcp__playwright__browser_click({"element": "Accept Cookies", "ref": "..."})

# 3. Fill ZIP code input
mcp__playwright__browser_type({
    "element": "zip code input",
    "ref": "...",  # Varies - use browser_snapshot to get current ref
    "text": "53202",
    "submit": False
})

# 4. Click search button
mcp__playwright__browser_click({"element": "Search button", "ref": "..."})

# 5. Wait for AJAX results to load (critical - 3 seconds minimum)
mcp__playwright__browser_wait_for({"time": 3})

# 6. Extract data using the JavaScript from config.EXTRACTION_SCRIPT
mcp__playwright__browser_evaluate({"function": config.EXTRACTION_SCRIPT})
```

**Important**: Element refs (e.g., "e88", "e180") change between page loads. Always take a fresh `browser_snapshot` to get current refs before clicking/typing.

## RunPod Serverless Architecture

The cloud-hosted RunPod mode provides fully automated browser automation via HTTP API.

### Deployment Structure

```
runpod-playwright-api/
├── handler.py              # RunPod serverless entry point
├── playwright_service.py   # Singleton browser service
├── requirements.txt        # runpod>=1.6.0, playwright>=1.48.0
├── Dockerfile             # mcr.microsoft.com/playwright/python:v1.48.0
└── examples/              # Test scripts and workflows
```

### Key Design Patterns

1. **Singleton Browser**: Browser initialized once at worker startup (saves ~2s per request)
2. **Context per Request**: New browser context created for each job (clean state isolation)
3. **Workflow-based API**: Sends JSON array of sequential actions (matches MCP 6-step pattern)
4. **Auto-scaling**: 0→N workers based on demand, pay-per-second pricing

### Usage Example

```python
from scraper import DealerScraper, ScraperMode

# Initialize in RunPod mode
scraper = DealerScraper(mode=ScraperMode.RUNPOD)

# Scrape single ZIP (makes HTTP POST to RunPod API)
dealers = scraper.scrape_zip_code("53202")

# Scrape multiple ZIPs with deduplication
dealers = scraper.scrape_multiple(["53202", "60601", "55401"])
scraper.deduplicate()
scraper.save_json("output/dealers.json")
```

### Workflow Translation

The `_scrape_with_runpod()` method automatically converts the 6-step MCP pattern into an HTTP request:

```python
workflow = [
    {"action": "navigate", "url": DEALER_LOCATOR_URL},
    {"action": "click", "selector": "button:has-text('Accept Cookies')"},
    {"action": "fill", "selector": "input[name*='zip' i]", "text": zip_code},
    {"action": "click", "selector": "button:has-text('Search')"},
    {"action": "wait", "timeout": 3000},  # Converted to milliseconds
    {"action": "evaluate", "script": EXTRACTION_SCRIPT},
]

response = requests.post(RUNPOD_API_URL, json={"input": {"workflow": workflow}})
dealers = response.json()["results"]
```

### Cost Efficiency

- **Per ZIP**: ~$0.001 (6 seconds @ $0.00015/sec)
- **100 ZIPs**: ~$0.50-$1.00 (includes overhead)
- **Auto-scale to zero**: No idle costs between jobs

For detailed deployment instructions, see `runpod-playwright-api/README.md`.

## Data Schema

Each extracted dealer record contains 15 fields:

```python
{
  "name": str,                    # ALL CAPS dealer name
  "rating": float,                # 0-5 scale (0 if no reviews)
  "review_count": int,            # Number of reviews
  "tier": str,                    # "Premier" | "Elite Plus" | "Elite" | "Standard"
  "is_power_pro_premier": bool,   # PowerPro Premier designation
  "street": str,                  # Street address
  "city": str,                    # City name
  "state": str,                   # 2-letter state code
  "zip": str,                     # 5-digit ZIP code
  "address_full": str,            # Combined address string
  "phone": str,                   # Formatted phone number
  "website": str,                 # Full URL or empty string
  "domain": str,                  # Extracted domain or empty string
  "distance": str,                # Distance string (e.g., "8.3 mi")
  "distance_miles": float         # Distance as numeric value
}
```

## Known Issues

### Address Parsing Bug
Dealers with 0 reviews have corrupted street addresses that include the distance prefix:
```python
# Bad example:
"street": "3 mi0.0(0)0.0 out of 5 stars.   7816 frontage rd"

# Should be:
"street": "7816 frontage rd"
```

**Location**: extraction.js lines 72-74 (regex replacements)
**Impact**: Affects ~60% of dealers (those with no reviews)
**Status**: Known issue, low priority (data still usable)

### Token Limit Issues
Using `browser_click` or `browser_snapshot` after search returns 30k+ tokens (exceeds 25k limit).

**Solution**: Use `browser_evaluate` with JavaScript extraction instead of reading full DOM.

## Testing

Validated across 3 metros:
- Milwaukee (53202): 59 dealers
- Chicago (60601): 59 dealers
- Minneapolis (55401): 28 dealers

Performance: ~5-6 seconds per ZIP code

## Adding New ZIP Codes

To test new regions, add ZIP codes to config.py:

```python
ZIP_CODES_CUSTOM = [
    "12345",  # City, State
    "67890",  # City, State
]
```

Use `ZIP_CODES_TEST` for quick 3-ZIP validation runs.

## Deployment Modes

### Local Development (PLAYWRIGHT mode)
- Uses MCP Playwright tools manually
- Good for testing extraction logic
- No cloud costs
- Element refs must be obtained via `browser_snapshot`

### Production (RUNPOD mode)
- Automated cloud Playwright via HTTP API
- Auto-scales from 0→N workers
- Cost: ~$0.001 per ZIP code
- Set `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` in .env
- See `runpod-playwright-api/README.md` for deployment

### Future: Browserbase Alternative
- Alternative cloud browser option
- Implementation placeholder exists in `_scrape_with_browserbase()`
- Set `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` to use

## Adapting for Other Sites

This scraper is designed to be adaptable:

1. **Update URL** in config.py: `DEALER_LOCATOR_URL`
2. **Modify selectors** in config.py: `SELECTORS` dict
3. **Rewrite extraction logic** in extraction.js:
   - Change anchor selector (currently `a[href^="tel:"]`)
   - Adjust container traversal logic
   - Update field extraction patterns
4. **Update data schema** in scraper.py: `fieldnames` list in `save_csv()`

The separation between config.py (selectors), extraction.js (DOM logic), and scraper.py (Python wrapper) makes site-specific changes isolated.
