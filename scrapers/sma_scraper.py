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
        JavaScript extraction script for SMA installer data.

        **STATUS**: NOT IMPLEMENTED - Requires manual site inspection

        **TASK**: Use Playwright MCP tools to:
        1. Navigate to https://www.sma-america.com/powerupplus/homeowner
        2. Open DevTools Network tab
        3. Search for a test ZIP code (e.g., 94102)
        4. Look for API calls that return installer data
        5. Inspect window object for installer data: console.log(Object.keys(window))
        6. Check Google Maps markers: google.maps markers or similar

        **EXPECTED DATA STRUCTURE** (based on typical installer locators):
        - name: Company name
        - phone: Phone number
        - website: Website URL
        - street: Street address
        - city: City
        - state: State
        - zip: ZIP code
        - distance: Distance from search location
        - certifications: SMA certifications/tier
        - rating: Google/SMA rating (if available)

        **PLACEHOLDER** (will be replaced with actual extraction script):
        """
        return """
        () => {
            // TODO: Implement SMA-specific extraction logic
            // This placeholder returns empty array

            console.log("WARNING: SMA extraction script not implemented yet");
            console.log("Next steps:");
            console.log("1. Inspect Network tab for API calls");
            console.log("2. Check window object for installer data");
            console.log("3. Look for Google Maps markers");
            console.log("4. Update this script with actual extraction logic");

            // Check if Google Maps data is available
            if (typeof google !== 'undefined' && google.maps) {
                console.log("Google Maps detected - may need to extract from map markers");
            }

            // Check for common installer data patterns in window object
            const potentialDataKeys = Object.keys(window).filter(key =>
                key.toLowerCase().includes('installer') ||
                key.toLowerCase().includes('dealer') ||
                key.toLowerCase().includes('partner')
            );

            if (potentialDataKeys.length > 0) {
                console.log("Potential installer data found in window object:", potentialDataKeys);
            }

            return [];  // Return empty array until extraction logic is implemented
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
        PLAYWRIGHT mode: Print manual MCP Playwright inspection instructions.

        **IMPORTANT**: This mode is for MANUAL INSPECTION to develop extraction logic.
        The extraction script is NOT YET IMPLEMENTED.

        Use this mode to:
        1. Inspect the SMA installer map
        2. Identify how installer data is loaded (API? JavaScript? Google Maps?)
        3. Develop extraction script
        4. Test extraction on 1-2 ZIP codes
        """
        print(f"\n{'='*60}")
        print(f"SMA Solar Installer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  EXTRACTION SCRIPT NOT IMPLEMENTED - MANUAL INSPECTION REQUIRED\n")

        print("🔍 STEP 1: Navigate and Inspect Site Structure\n")
        print("1. Navigate to SMA installer map:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to see page structure:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. Open DevTools and inspect Network tab:")
        print("   (Look for API calls when searching for installers)\n")

        print("4. Try entering a ZIP code:")
        print(f'   - Type "{zip_code}" in the location input')
        print(f'   - Click search')
        print(f'   - Watch Network tab for XHR/Fetch requests\n')

        print("🔍 STEP 2: Identify Data Source\n")
        print("Use browser_evaluate to inspect JavaScript environment:")
        print("""
   mcp__playwright__browser_evaluate({
       "function": "() => {
           // Check for Google Maps
           console.log('Has Google Maps:', typeof google !== 'undefined');

           // Check window object for installer data
           const installerKeys = Object.keys(window).filter(k =>
               k.toLowerCase().includes('installer') ||
               k.toLowerCase().includes('dealer')
           );
           console.log('Potential data keys:', installerKeys);

           // Return results
           return {
               hasGoogleMaps: typeof google !== 'undefined',
               potentialDataKeys: installerKeys
           };
       }"
   })
        """)

        print("\n🔍 STEP 3: Develop Extraction Logic\n")
        print("Based on findings from Step 2:")
        print("- If data is in Google Maps markers: Extract from map.markers or similar")
        print("- If data is in window object: Access the data structure directly")
        print("- If data comes from API: Capture the API endpoint and reverse-engineer")
        print("- If data is in HTML: Use DOM traversal (like Generac scraper)\n")

        print("🔍 STEP 4: Update Extraction Script\n")
        print("Once you identify the data source:")
        print("1. Edit scrapers/sma_scraper.py")
        print("2. Update get_extraction_script() method")
        print("3. Test on 1-2 ZIP codes")
        print("4. Validate data structure matches StandardizedDealer format\n")

        print(f"{'='*60}\n")
        print("❌ Extraction script is NOT IMPLEMENTED")
        print("✅ Use PLAYWRIGHT mode to develop extraction logic")
        print("✅ Once working, test with RUNPOD mode for production")
        print(f"{'='*60}\n")

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
