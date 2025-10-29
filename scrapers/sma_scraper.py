"""
SMA Solar Technology Installer Locator Scraper

Scrapes SMA's PowerUP+ installer network for commercial solar contractors.
SMA installers are typically commercial/utility-scale solar integrators - Coperniq's highest-value ICP.

Target URL: https://www.sma-america.com/powerupplus/homeowner
Alternative: https://www.sma-america.com/where-to-buy

**CRITICAL NOTE**: SMA PowerUP+ installer map uses Google Maps API with dynamic JavaScript.
The installer data is loaded via Google Maps markers, NOT static HTML.
This makes traditional Playwright extraction challenging without reverse-engineering the Google Maps API.

**Commercial Focus**: SMA is one of the largest commercial/utility-scale inverter manufacturers.
Their installers represent sophisticated contractors doing large commercial solar projects.

**Why SMA is Priority**:
- Commercial/utility-scale focus (vs residential)
- Large project sizes (higher contract values)
- Sophisticated contractors (established businesses with employees)
- Multi-trade capabilities (solar + electrical + often battery storage)
- Perfect fit for Coperniq's brand-agnostic monitoring platform

Capabilities detected from SMA certification:
- Solar inverter installation (core product)
- Commercial solar projects (SMA's primary market)
- Electrical work (required for inverter/solar install)
- Battery storage (many SMA installers also do energy storage)
"""

import os
import json
import requests
from typing import Dict, List
from scrapers.base_scraper import (
    BaseDealerScraper,
    DealerCapabilities,
    StandardizedDealer,
    ScraperMode
)
from scrapers.scraper_factory import ScraperFactory


class SMAScraper(BaseDealerScraper):
    """
    Scraper for SMA Solar installer network.

    **STATUS**: Structure ready, extraction logic TBD

    **IMPLEMENTATION CHALLENGE**:
    The SMA PowerUP+ installer map (https://www.sma-america.com/powerupplus/homeowner)
    uses Google Maps API to dynamically load installer markers. The data is NOT in the HTML DOM.

    **NEXT STEPS**:
    1. Manual inspection with Playwright MCP:
       - Navigate to URL
       - Open browser DevTools (Network tab)
       - Search for a ZIP code
       - Look for API calls that return installer data
       - Identify the endpoint and parameters

    2. Alternative approaches:
       a) Reverse-engineer Google Maps API calls (check Network tab for XHR/Fetch)
       b) Extract data from `window` object if installers are stored in JavaScript
       c) Contact SMA for official API access (https://developer.sma.de/sma-apis)
       d) Use alternative data sources (EnergySage, Solar Reviews, local business directories)

    3. Once extraction method is identified:
       - Update get_extraction_script() with working JavaScript
       - Test on 1-2 ZIP codes
       - Update SELECTORS dict with correct element references

    **COMMERCIAL VALUE**:
    SMA installers are HIGH PRIORITY prospects because:
    - SMA dominates commercial/utility-scale solar (not residential)
    - These contractors handle large projects ($500K-$10M+)
    - Sophisticated businesses with established operations
    - Multi-brand capabilities (often also install battery storage, other inverters)
    - Perfect ICP for Coperniq (managing complex energy systems across multiple brands)
    """

    OEM_NAME = "SMA"
    DEALER_LOCATOR_URL = "https://www.sma-america.com/powerupplus/homeowner"
    PRODUCT_LINES = ["Solar Inverters", "Hybrid Inverters", "Battery Inverters", "Commercial PV", "Utility-Scale"]

    # CSS Selectors (TBD - need manual inspection)
    # Note: SMA uses Google Maps, so traditional CSS selectors may not work
    # May need to use Google Maps API or extract from window object
    SELECTORS = {
        "cookie_accept": "button:has-text('Okay')",  # Cookie consent button
        "zip_input": "input[placeholder*='location' i]",  # ZIP/location search input
        "search_button": "button:has-text('Extended search')",  # Search button (TBD)
        # Additional selectors TBD after manual inspection
    }

    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT):
        super().__init__(mode)

        # Load RunPod config if in RUNPOD mode
        if mode == ScraperMode.RUNPOD:
            self.runpod_api_key = os.getenv("RUNPOD_API_KEY")
            self.runpod_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
            self.runpod_api_url = os.getenv(
                "RUNPOD_API_URL",
                f"https://api.runpod.ai/v2/{self.runpod_endpoint_id}/runsync"
            )

        # Load Browserbase config if in BROWSERBASE mode
        if mode == ScraperMode.BROWSERBASE:
            self.browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
            self.browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction script for SMA POWERUP+ installer data.
        
        Extracts installer data from the SMA installer locator page.
        Data is rendered to DOM in .address-wrapper containers (not Google Maps API markers).
        
        Returns array of installer objects with:
        - name: Company name
        - phone: Phone number  
        - website: Website URL
        - street: Street address
        - city: City
        - state: State abbreviation
        - zip: ZIP code
        - distance: Distance string (e.g., "21 mi")
        - distance_miles: Distance as float
        """
        return """
        () => {
          // Extract SMA POWERUP+ installers - only those with address-wrapper
          const installers = [];
          const seen = new Set();
          
          // Find containers with address-wrapper (actual installer results)
          const addressWrappers = document.querySelectorAll('.address-wrapper');
          
          addressWrappers.forEach(wrapper => {
            // Find the parent container that has all installer data
            const container = wrapper.closest('.ng-scope');
            if (!container) return;
            
            // Get company name from H3
            const nameEl = container.querySelector('h3');
            if (!nameEl) return;
            const name = nameEl.textContent.trim();
            if (!name) return;
            
            // Get address
            const addressDiv = wrapper.querySelector('.address');
            let street = '';
            let city = '';
            let state = '';
            let zip = '';
            
            if (addressDiv) {
              // Address format: "40 La Barthe Ln<br>San Carlos, CA 94070"
              const addressHTML = addressDiv.innerHTML;
              const parts = addressHTML.split('<br>');
              
              if (parts.length >= 2) {
                street = parts[0].trim();
                
                // Parse "San Carlos, CA 94070"
                const cityStateZip = parts[1].trim();
                const match = cityStateZip.match(/^(.+?),\\s+([A-Z]{2})\\s+(\\d{5})$/);
                if (match) {
                  city = match[1];
                  state = match[2];
                  zip = match[3];
                }
              }
            }
            
            // Get distance
            const distanceEl = wrapper.querySelector('.distance-unit') || 
                              container.querySelector('[class*="distance"]');
            let distance = '';
            let distance_miles = 0;
            
            if (distanceEl) {
              distance = distanceEl.textContent.trim();
              const milesMatch = distance.match(/(\\d+(?:\\.\\d+)?)\\s*mi/);
              if (milesMatch) {
                distance_miles = parseFloat(milesMatch[1]);
              }
            }
            
            // Get phone
            let phone = '';
            const phoneLink = container.querySelector('a[href^="tel:"]');
            if (phoneLink) {
              phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
              // Normalize: remove country code if present
              if (phone.length === 11 && phone.startsWith('1')) {
                phone = phone.substring(1);
              }
            }
            
            // Get website
            let website = '';
            const links = container.querySelectorAll('a[href]');
            for (const link of links) {
              const href = link.href;
              // Skip tel links, Google Maps links, and SMA's own domain
              if (href && !href.includes('tel:') && 
                  !href.includes('google') && 
                  !href.includes('sma-america.com') &&
                  (href.startsWith('http://') || href.startsWith('https://'))) {
                website = href;
                break;
              }
            }
            
            // Extract domain from website
            let domain = '';
            if (website) {
              try {
                const url = new URL(website);
                domain = url.hostname.replace(/^www\\./, '');
              } catch (e) {
                // Invalid URL, skip domain extraction
              }
            }
            
            // Deduplicate by phone (primary) or name (fallback)
            const key = phone || name;
            if (seen.has(key)) return;
            seen.add(key);
            
            installers.push({
              name,
              phone,
              domain,
              website,
              street,
              city,
              state,
              zip,
              distance,
              distance_miles
            });
          });
          
          return installers;
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from SMA installer data.

        SMA certifications indicate:
        - All installers: has_solar + has_inverters + has_electrical (minimum for solar install)
        - Commercial focus: SMA's primary market is commercial/utility-scale
        - Battery capability: Many SMA installers also do energy storage (SMA makes hybrid inverters)

        **HIGH VALUE INDICATORS**:
        - SMA installers are typically larger, more sophisticated contractors
        - Commercial focus = higher project values
        - Multi-brand capabilities likely (will be detected by multi-OEM detector)
        """
        caps = DealerCapabilities()

        # All SMA installers have solar, inverter, and electrical capabilities
        caps.has_solar = True
        caps.has_inverters = True
        caps.has_electrical = True

        # SMA's primary market is commercial/utility-scale
        # Default to commercial=True for SMA installers
        # (will be validated/updated via Apollo enrichment with employee count)
        caps.is_commercial = True

        # Many SMA installers also offer residential
        # Check if installer name/data indicates residential focus
        dealer_name = raw_dealer_data.get("name", "").lower()
        if "residential" in dealer_name or "home" in dealer_name:
            caps.is_residential = True
        else:
            # Default to both commercial and residential
            caps.is_residential = True

        # SMA makes hybrid inverters and battery inverters
        # Check if installer is certified for battery/hybrid products
        certifications = raw_dealer_data.get("certifications", [])
        if any("battery" in str(cert).lower() or "hybrid" in str(cert).lower() for cert in certifications):
            caps.has_battery = True

        # Add SMA OEM certification
        caps.oem_certifications.add("SMA")
        caps.inverter_oems.add("SMA")

        # Detect high-value contractor types (O&M and MEP+R)
        tier = raw_dealer_data.get("tier", "Standard")
        caps.detect_high_value_contractor_types(dealer_name, certifications, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw SMA installer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object

        **NOTE**: Data structure TBD based on actual SMA API/extraction method
        """
        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications/tier (TBD based on SMA data structure)
        tier = raw_dealer_data.get("tier", "PowerUP+ Installer")
        certifications = raw_dealer_data.get("certifications", [])
        if not certifications:
            certifications = ["PowerUP+ Installer"]

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=raw_dealer_data.get("domain", ""),
            website=raw_dealer_data.get("website", ""),
            street=raw_dealer_data.get("street", ""),
            city=raw_dealer_data.get("city", ""),
            state=raw_dealer_data.get("state", ""),
            zip=raw_dealer_data.get("zip", ""),
            address_full=raw_dealer_data.get("address_full", ""),
            rating=raw_dealer_data.get("rating", 0.0),
            review_count=raw_dealer_data.get("review_count", 0),
            tier=tier,
            certifications=certifications,
            distance=raw_dealer_data.get("distance", ""),
            distance_miles=raw_dealer_data.get("distance_miles", 0.0),
            capabilities=capabilities,
            oem_source="SMA",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Execute automated scraping using local Playwright.
        
        Workflow:
        1. Navigate to SMA POWERUP+ installer map
        2. Wait for map to load (JavaScript initialization)
        3. Fill ZIP code in search input
        4. Press Enter to trigger search (Google autocomplete)
        5. Wait for results to load (.address-wrapper elements)
        6. Execute JavaScript extraction
        7. Parse results into StandardizedDealer objects
        """
        from playwright.sync_api import sync_playwright
        import time
        
        print(f"\n{'='*60}")
        print(f"SMA Solar Installer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")
        
        try:
            with sync_playwright() as p:
                print(f"  → Launching Playwright browser...")
                # Launch with stealth settings to bypass bot detection
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                # Create context with realistic browser fingerprint
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                # Add extra headers
                context.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                page = context.new_page()
                
                # Navigate to SMA installer map
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=30000, wait_until='domcontentloaded')
                
                # Wait for Angular to bootstrap  
                print(f"  → Waiting for Angular app to initialize...")
                time.sleep(10)  # Give Angular time to fully load
                
                # Click into the input field first to focus it
                print(f"  → Clicking location input...")
                click_script = """
                () => {
                    const input = document.querySelector('input[placeholder*="location" i]') ||
                                 document.querySelector('input[type="text"]');
                    if (input) {
                        input.focus();
                        input.click();
                        return true;
                    }
                    return false;
                }
                """
                clicked = page.evaluate(click_script)
                
                if not clicked:
                    print(f"     ⚠️  Could not find input field")
                    browser.close()
                    return []
                
                print(f"     ✓ Input focused")
                time.sleep(1)
                
                # Type the ZIP code (this triggers autocomplete better than setting value)
                print(f"  → Typing ZIP code: {zip_code}")
                page.keyboard.type(zip_code, delay=100)  # Type with delays like a human
                time.sleep(3)  # Wait for Google autocomplete to appear
                
                # Press Enter to submit (this selects autocomplete and triggers search)
                print(f"  → Submitting search (Enter)...")
                page.keyboard.press('Enter')
                
                # Wait longer for results - the search can be slow
                print(f"  → Waiting for results (10s)...")
                time.sleep(10)
                
                # Wait for results to load - check for address-wrapper elements
                print(f"  → Waiting for results...")
                try:
                    # Wait for at least one address-wrapper to appear (actual installer results)
                    page.wait_for_selector('.address-wrapper', timeout=15000)
                    print(f"     ✓ Results loaded successfully")
                except Exception as e:
                    print(f"     Warning: Results not found")
                    print(f"     Current URL: {page.url}")
                    # Check if any results loaded
                    address_count = page.evaluate('() => document.querySelectorAll(".address-wrapper").length')
                    print(f"     Address wrappers found: {address_count}")
                    
                    if address_count == 0:
                        print(f"     No installers found for ZIP {zip_code}")
                        browser.close()
                        return []
                
                # Extract installer data using JavaScript
                print(f"  → Extracting installer data...")
                extraction_script = self.get_extraction_script()
                installers_data = page.evaluate(extraction_script)
                
                print(f"  → Found {len(installers_data)} POWERUP+ installers")
                
                # Parse into StandardizedDealer objects
                dealers = self.parse_results(installers_data, zip_code)
                
                browser.close()
                
                return dealers
                
        except Exception as e:
            print(f"  ✗ Error scraping with Playwright: {e}")
            import traceback
            traceback.print_exc()
            try:
                if 'browser' in locals():
                    browser.close()
            except:
                pass  # Ignore browser close errors
            return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.

        **STATUS**: NOT FUNCTIONAL - Extraction script not implemented

        This will work once get_extraction_script() returns valid extraction logic.
        """
        print(f"\n⚠️  SMA scraper not ready for RUNPOD mode")
        print(f"⚠️  Extraction script must be implemented first")
        print(f"⚠️  Use PLAYWRIGHT mode to develop extraction logic\n")

        raise NotImplementedError(
            "SMA scraper extraction logic not implemented yet. "
            "Use PLAYWRIGHT mode to inspect site and develop extraction script. "
            "See scrapers/sma_scraper.py docstring for next steps."
        )

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Execute automated scraping via Browserbase cloud browser.

        **STATUS**: NOT FUNCTIONAL - Extraction script not implemented

        This will work once get_extraction_script() returns valid extraction logic.
        """
        raise NotImplementedError(
            "SMA scraper extraction logic not implemented yet. "
            "Use PLAYWRIGHT mode to inspect site and develop extraction script."
        )

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Stealth browser automation with bot detection bypass.

        **STATUS**: NOT FUNCTIONAL - Extraction script not implemented

        This will work once get_extraction_script() returns valid extraction logic.
        """
        raise NotImplementedError(
            "SMA scraper extraction logic not implemented yet. "
            "Use PLAYWRIGHT mode to inspect site and develop extraction script."
        )

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.

        Args:
            results_json: Array of installer objects from browser_evaluate
            zip_code: ZIP code that was searched

        Returns:
            List of StandardizedDealer objects
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register SMA scraper with factory
ScraperFactory.register("SMA", SMAScraper)
ScraperFactory.register("sma", SMAScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual inspection and development)
    print("\n" + "="*60)
    print("SMA Solar Installer Scraper - Development Mode")
    print("="*60 + "\n")

    print("This scraper is NOT YET FUNCTIONAL.")
    print("Use PLAYWRIGHT mode to inspect the SMA installer map and develop extraction logic.\n")

    scraper = SMAScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco (commercial solar market)

    print("\nNext steps:")
    print("1. Use the Playwright MCP workflow printed above")
    print("2. Identify how installer data is loaded (API/JavaScript/Google Maps)")
    print("3. Update get_extraction_script() with working extraction logic")
    print("4. Test on 1-2 ZIP codes")
    print("5. Switch to RUNPOD mode for production scraping\n")
