# Generac Dealer Locator - Scraping Findings

## Page Structure

**URL**: https://www.generac.com/dealer-locator/

### How It Works
1. User fills in ZIP code input field
2. Optionally selects product type, radius, and service filters
3. Clicks Search button (or submits via Enter)
4. Results load dynamically (JavaScript-rendered)
5. ~57 dealers shown for a typical ZIP code (25-mile radius)

### Key Selectors

#### Form Elements
- **ZIP Input**: `textbox "City & State or ZIP"` (ref varies)
- **Search Button**: `button "Search"` (ref varies)
- **Cookie Dialog**: `button "Accept Cookies"` (must dismiss first)

#### Result Elements
- **Phone Links**: `a[href^="tel:"]` (59 results for ZIP 53202)
- **Distance**: `.ms-auto.text-end.text-nowrap` (e.g., "8.3 mi")
- **Website Links**: `a[href^="http"]` (filter out Google/Facebook)

### Data Extracted Per Dealer

```javascript
{
  name: "CURRENT ELECTRIC CO.",              // ALL CAPS dealer name
  rating: 4.3,                               // Float (0-5)
  review_count: 6,                           // Integer
  tier: "Premier",                           // Premier | Elite Plus | Elite | Standard
  is_power_pro_premier: true,                // Boolean
  street: "2942 n 117th st",                 // Street address
  city: "wauwatosa",                         // City (lowercase)
  state: "WI",                               // 2-letter state code
  zip: "53222",                              // 5-digit ZIP
  address_full: "...",                       // Combined address
  phone: "(262) 786-5885",                   // Formatted phone
  website: "https://currentelectricco.com/", // Full URL
  domain: "currentelectricco.com",           // Extracted domain
  distance: "8.3 mi",                        // Distance string
  distance_miles: 8.3                        // Distance numeric
}
```

### Dealer Tiers

- **Premier**: "Premier Dealers demonstrate the highest level of commitment..."
- **Elite Plus**: "Elite Plus Dealers provide an elevated level of service..."
- **Elite**: "Elite Dealers offer both installation and basic service support..."
- **Standard**: No special designation

### Sample Results (ZIP 53202)

Total dealers: 59
- **Premier**: 2 dealers
- **Elite Plus**: 2 dealers
- **Elite**: 9 dealers
- **Standard**: 46 dealers

**Top Rated**:
1. MR. HOLLAND'S HOME SERVICES, LLC - 5.0★ (24 reviews) - Premier
2. YOUNG GUNS ELECTRIC, LLC - 4.9★ (49 reviews) - Elite
3. PIEPER POWER INC. - 4.8★ (20 reviews) - Elite Plus

### Extraction Challenges

1. **Address Parsing**: Text includes ratings/distance mixed in
   - Solution: Regex cleaning of "X out of 5 stars" patterns

2. **Dynamic Content**: Results load via AJAX
   - Solution: Wait 3 seconds after search submission

3. **Cookie Consent**: Dialog blocks interaction
   - Solution: Click "Accept Cookies" button first

4. **Large Result Sets**: 57+ dealers cause token limit issues
   - Solution: Extract data with JavaScript, not full DOM snapshot

### MCP Playwright Tools Used

```javascript
// Navigate
mcp__playwright__browser_navigate({ url: "..." })

// Accept cookies
mcp__playwright__browser_click({ element: "Accept Cookies", ref: "e180" })

// Fill ZIP and search
mcp__playwright__browser_type({
  element: "zip code input",
  ref: "e88",
  text: "53202",
  submit: false
})

// Click search button
mcp__playwright__browser_click({ element: "Search button", ref: "e109" })

// Wait for results
mcp__playwright__browser_wait_for({ time: 3 })

// Extract data
mcp__playwright__browser_evaluate({ function: extractionScript })
```

### Next Steps

1. ✅ Test extraction with ZIP 53202 - **59 dealers extracted**
2. ⏳ Test with 3-5 more ZIP codes to verify consistency
3. ⏳ Build Python automation script
4. ⏳ Scale to multiple ZIP codes
5. ⏳ Add deduplication logic
6. ⏳ Export to JSON/CSV

## Performance Notes

- Page load: ~2-3 seconds
- Search submission: ~2-3 seconds for results to load
- Extraction: Instant (JavaScript runs in browser)
- Total per ZIP: ~5-6 seconds

**Estimated time for 100 ZIPs**: ~10 minutes (with 3s delays)
