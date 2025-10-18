# Generac Dealer Scraper MVP

Scrapes dealer information from the Generac dealer locator using MCP Playwright tools.

## Features

- ✅ Extract dealer name, rating, reviews, tier, address, phone, website, domain
- ✅ Identify PowerPro Premier dealers
- ✅ Support for multiple ZIP codes
- ✅ Deduplication by phone number
- ✅ Export to JSON and CSV
- ⏳ Playwright (local) mode via MCP tools
- ⏳ Browserbase (cloud) mode for scaling

## Project Structure

```
dealer-scraper-mvp/
├── scraper.py           # Main scraper class
├── config.py            # Selectors, extraction script, ZIP lists
├── extraction.js        # JavaScript extraction function
├── FINDINGS.md          # Research documentation
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Data Schema

Each dealer record contains:

```python
{
  "name": "CURRENT ELECTRIC CO.",              # Dealer name (ALL CAPS)
  "rating": 4.3,                               # Float (0-5)
  "review_count": 6,                           # Integer
  "tier": "Premier",                           # Premier | Elite Plus | Elite | Standard
  "is_power_pro_premier": True,                # Boolean
  "street": "2942 n 117th st",                 # Street address
  "city": "wauwatosa",                         # City
  "state": "WI",                               # 2-letter state code
  "zip": "53222",                              # 5-digit ZIP
  "address_full": "...",                       # Combined address
  "phone": "(262) 786-5885",                   # Formatted phone
  "website": "https://currentelectricco.com/", # Full URL
  "domain": "currentelectricco.com",           # Extracted domain
  "distance": "8.3 mi",                        # Distance string
  "distance_miles": 8.3                        # Distance numeric
}
```

## Dealer Tiers

- **Premier**: Highest level of commitment and service
- **Elite Plus**: Elevated level of service
- **Elite**: Installation and basic service support
- **Standard**: No special designation

## Usage

### Manual Mode (MCP Playwright)

Current implementation uses MCP Playwright tools manually:

1. Navigate to dealer locator
2. Accept cookies
3. Fill ZIP code
4. Click search
5. Wait for results
6. Extract data with JavaScript

```python
from scraper import DealerScraper, ScraperMode

scraper = DealerScraper(mode=ScraperMode.PLAYWRIGHT)
# Execute MCP tool calls manually
```

### Automated Mode (Future)

Will support automated multi-ZIP scraping:

```python
from scraper import DealerScraper
from config import ZIP_CODES_TEST

scraper = DealerScraper()
dealers = scraper.scrape_multiple(ZIP_CODES_TEST)
scraper.deduplicate()
scraper.save_json("dealers.json")
scraper.save_csv("dealers.csv")

# Get top-rated dealers
top = scraper.get_top_rated(min_reviews=5, limit=10)
```

## MCP Playwright Workflow

```python
# 1. Navigate
mcp__playwright__browser_navigate({"url": "https://www.generac.com/dealer-locator/"})

# 2. Accept cookies
mcp__playwright__browser_click({"element": "Accept Cookies", "ref": "e180"})

# 3. Fill ZIP
mcp__playwright__browser_type({
    "element": "zip code input",
    "ref": "e88",
    "text": "53202",
    "submit": False
})

# 4. Search
mcp__playwright__browser_click({"element": "Search button", "ref": "e109"})

# 5. Wait
mcp__playwright__browser_wait_for({"time": 3})

# 6. Extract (using extraction.js)
mcp__playwright__browser_evaluate({"function": EXTRACTION_SCRIPT})
```

## Performance

- Page load: ~2-3 seconds
- Search results: ~2-3 seconds
- Extraction: Instant
- **Total per ZIP**: ~5-6 seconds
- **100 ZIPs**: ~10 minutes

## Testing Progress

- ✅ ZIP 53202 (Milwaukee, WI) - 59 dealers extracted
- ⏳ Additional ZIP codes pending
- ⏳ Multi-ZIP automation pending
- ⏳ Browserbase integration pending

## Next Steps

1. Test extraction with 3-5 more ZIP codes
2. Implement full automation wrapper
3. Add Browserbase support for scaling
4. Build deduplication logic
5. Create output directory structure
6. Add error handling and retries

## Sample Results (ZIP 53202)

**Total**: 59 dealers

**Top Rated**:
1. MR. HOLLAND'S HOME SERVICES, LLC - 5.0★ (24 reviews) - Premier
2. YOUNG GUNS ELECTRIC, LLC - 4.9★ (49 reviews) - Elite
3. PIEPER POWER INC. - 4.8★ (20 reviews) - Elite Plus

**Tier Breakdown**:
- Premier: 2 dealers
- Elite Plus: 2 dealers
- Elite: 9 dealers
- Standard: 46 dealers

## License

MIT
