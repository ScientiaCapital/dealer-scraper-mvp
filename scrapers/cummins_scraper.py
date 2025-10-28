"""
Cummins Dealer Locator Scraper

Scrapes Cummins' dealer network for home standby generators.
Cummins dealers are typically electrical/HVAC contractors who also handle backup power systems.

Target URL: https://www.cummins.com/na/generators/home-standby/find-a-dealer
Alternative: https://locator.cummins.com/

Capabilities detected from Cummins certification:
- Generator installation (home standby systems)
- Electrical work (required for generator install)
- Often HVAC (many dealers are dual-trade contractors)

NOTE: Extraction script needs manual DOM inspection to complete.
The site structure must be analyzed via PLAYWRIGHT mode first.
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


class CumminsScraper(BaseDealerScraper):
    """
    Scraper for Cummins dealer network.

    Cummins dealer tiers (typical for home generator OEMs):
    - Authorized Dealer: Basic certification
    - Premier/Elite: Higher service commitment (if applicable)

    Cummins is known for commercial/industrial generators but also has
    residential home standby systems (QuietConnect series).
    """

    OEM_NAME = "Cummins"
    DEALER_LOCATOR_URL = "https://www.cummins.com/na/generators/home-standby/find-a-dealer"
    PRODUCT_LINES = ["Home Standby", "QuietConnect", "Portable", "Commercial"]

    # CSS Selectors - PLACEHOLDER: Needs manual inspection
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept'), button:has-text('I Agree')",
        "zip_input": "input[placeholder*='ZIP' i], input[placeholder*='postal' i]",
        "search_button": "button:has-text('Search'), button:has-text('Find'), button[type='submit']",
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
        JavaScript extraction script for Cummins dealer data.
        
        Tested on: https://www.cummins.com/na/generators/home-standby/find-a-dealer
        Structure: Dealers in `.dealer-listing-col.com_locator_entry` elements
        """
        return """
() => {
  // Find all dealer cards
  const dealerCards = Array.from(document.querySelectorAll('.dealer-listing-col.com_locator_entry'));
  
  console.log(`Found ${dealerCards.length} Cummins dealer cards`);
  
  const dealers = dealerCards.map(card => {
    try {
      // Extract dealer name
      const nameLink = card.querySelector('.title .info h3 a.marker-link');
      const name = nameLink ? nameLink.textContent.trim() : '';
      
      // Extract tier (e.g., "Dealer")
      const tierSpan = card.querySelector('.title .info .location');
      const tier = tierSpan ? tierSpan.textContent.trim() : 'Authorized Dealer';
      
      // Extract phone
      const phoneLink = card.querySelector('.phone a[href^="tel:"]');
      const phone = phoneLink ? phoneLink.textContent.trim() : '';
      
      // Extract website
      const websiteLink = card.querySelector('.website a');
      const website = websiteLink ? websiteLink.href : '';
      
      // Extract domain from website
      let domain = '';
      if (website) {
        try {
          const url = new URL(website);
          domain = url.hostname.replace('www.', '');
        } catch (e) {}
      }
      
      // Extract address (contains <br> tags)
      const addressDiv = card.querySelector('.address .address-info');
      let street = '';
      let city = '';
      let state = '';
      let zip = '';
      let address_full = '';
      
      if (addressDiv) {
        // Get innerHTML to preserve <br> structure
        const addressHTML = addressDiv.innerHTML;
        
        // Split by <br> tag
        const addressParts = addressHTML.split(/<br\\s*\/?>/i).map(p => p.trim()).filter(p => p);
        
        if (addressParts.length >= 2) {
          // First part: street address
          street = addressParts[0].trim();
          
          // Second part: "City, STATE ZIP"
          const cityStateZip = addressParts[1].trim();
          const match = cityStateZip.match(/^([^,]+),\\s*([A-Z]{2,})\\s+(\\d{5})/);
          
          if (match) {
            city = match[1].trim();
            state = match[2].trim();
            zip = match[3].trim();
          } else {
            // Fallback: just use the text as-is
            city = cityStateZip;
          }
        }
        
        address_full = addressDiv.textContent.trim().replace(/\\s+/g, ' ');
      }
      
      // Extract distance
      const distanceP = card.querySelector('p');
      let distance = '';
      let distance_miles = 0;
      
      if (distanceP) {
        const distanceText = distanceP.textContent.trim();
        // Format: "Approximately 26.26 Mi from 94102"
        const milesMatch = distanceText.match(/([\\d.]+)\\s*Mi/i);
        if (milesMatch) {
          distance_miles = parseFloat(milesMatch[1]);
          distance = `${distance_miles} mi`;
        }
      }
      
      return {
        name: name,
        phone: phone,
        website: website,
        domain: domain,
        street: street,
        city: city,
        state: state,
        zip: zip,
        address_full: address_full,
        rating: 0,  // Cummins doesn't show ratings
        review_count: 0,
        tier: tier,
        certifications: [tier],
        distance: distance,
        distance_miles: distance_miles
      };
    } catch (e) {
      console.error('Error extracting dealer card:', e);
      return null;
    }
  });
  
  // Filter out null/invalid dealers
  const validDealers = dealers.filter(d => d && d.name && d.phone);
  
  console.log(`Extracted ${validDealers.length} valid Cummins dealers`);
  
  return validDealers;
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Cummins dealer data.

        Cummins certifications indicate:
        - All dealers: has_generator + has_electrical (minimum for install)
        - Cummins is generator-focused (like Generac)
        - Many dealers are electrical/HVAC contractors
        """
        caps = DealerCapabilities()

        # All Cummins dealers have generator and electrical capabilities
        caps.has_generator = True
        caps.has_electrical = True
        caps.generator_oems.add("Cummins")

        # Extract tier
        tier = raw_dealer_data.get("tier", "Authorized Dealer")

        # Premier/Elite tiers indicate higher capability (if Cummins uses these)
        if tier in ["Premier", "Elite", "Premier Dealer", "Elite Dealer"]:
            caps.is_residential = True
            caps.is_commercial = True  # May be updated via Apollo enrichment

        # Many Cummins dealers are electrical/HVAC contractors
        # (will be validated via domain/name analysis in multi-OEM detector)

        # Add Cummins OEM certification
        caps.oem_certifications.add("Cummins")

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = []
        if tier != "Authorized Dealer":
            certifications_list.append(tier)
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Cummins dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications from tier
        tier = raw_dealer_data.get("tier", "Authorized Dealer")
        certifications = raw_dealer_data.get("certifications", [tier])

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
            oem_source="Cummins",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated scraping using local Playwright.
        
        Handles Cummins' complex cascading form in iframe:
        1. Navigate to dealer locator
        2. Fill cascading form (PRODUCT → MARKET APPLICATION → SERVICE LEVEL → COUNTRY → LOCATION → DISTANCE)
        3. Submit search
        4. Extract dealers using JavaScript
        5. Parse and return StandardizedDealer objects
        """
        from playwright.sync_api import sync_playwright
        import time

        dealers = []

        with sync_playwright() as p:
            try:
                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to dealer locator
                print(f"  → Navigating to Cummins dealer locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(3)

                # Handle cookie consent dialog if it appears
                print(f"  → Checking for cookie consent dialog...")
                try:
                    # Try to find and dismiss cookie consent
                    # OneTrust common selectors
                    cookie_selectors = [
                        '#onetrust-accept-btn-handler',
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        '.onetrust-close-btn-handler',
                        '#onetrust-reject-all-handler',
                    ]
                    
                    for selector in cookie_selectors:
                        try:
                            cookie_btn = page.locator(selector)
                            if cookie_btn.count() > 0 and cookie_btn.first.is_visible():
                                print(f"     Found cookie dialog, dismissing...")
                                cookie_btn.first.click(timeout=2000)
                                time.sleep(2)
                                break
                        except Exception:
                            continue
                except Exception:
                    pass  # No cookie dialog found, continue

                # Find iframe
                print(f"  → Finding form iframe...")
                iframe = page.frame_locator('iframe[title="Find dealer locations form"]')

                # Fill cascading form
                print(f"  → Filling form for ZIP {zip_code}...")

                # PRODUCT: Power Generation
                iframe.locator('select').first.select_option(label='Power Generation')
                time.sleep(1)

                # MARKET APPLICATION: Home And Small Business
                iframe.locator('select').nth(1).select_option(label='Home And Small Business')
                time.sleep(1)

                # SERVICE LEVEL: Installation (first non-empty option)
                service_select = iframe.locator('select').nth(2)
                options = service_select.locator('option').all()
                if len(options) > 1:
                    first_value = options[1].get_attribute('value')
                    service_select.select_option(value=first_value)
                    time.sleep(2)

                # COUNTRY: United States
                country_select = iframe.locator('select').nth(3)
                country_select.select_option(label='United States')
                time.sleep(2)

                # LOCATION: ZIP code
                postal_input = iframe.locator('input[name="postal_code"]')
                postal_input.wait_for(state='visible', timeout=5000)
                postal_input.fill(zip_code)
                time.sleep(1)

                # DISTANCE: 100 Miles
                iframe.locator('input[value="100"]').check()
                time.sleep(1)

                # Click SEARCH button
                print(f"  → Submitting search...")
                button_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'input[value*="SEARCH" i]',
                    'button:has-text("SEARCH")',
                    '.form-submit',
                ]

                button_clicked = False
                for selector in button_selectors:
                    try:
                        btn = iframe.locator(selector)
                        if btn.count() > 0:
                            btn.first.click(timeout=5000)
                            button_clicked = True
                            break
                    except Exception:
                        continue

                if not button_clicked:
                    raise Exception("Could not find/click SEARCH button")

                # Wait for results to load
                print(f"  → Waiting for results...")
                time.sleep(10)

                # Extract dealers using JavaScript
                print(f"  → Extracting dealer data...")
                extraction_script = self.get_extraction_script()

                # Get the iframe frame (it's usually the second frame on the page)
                iframe_frame = None
                for frame in page.frames:
                    # Check if this is the dealer locator iframe
                    frame_url = frame.url
                    if 'locator-interface' in frame_url or frame != page.main_frame:
                        iframe_frame = frame
                        break

                if not iframe_frame:
                    raise Exception("Could not find dealer locator iframe")

                # Execute extraction script in iframe context
                dealers_data = iframe_frame.evaluate(extraction_script)

                print(f"  → Found {len(dealers_data)} dealers")

                # Parse into StandardizedDealer objects
                dealers = self.parse_results(dealers_data, zip_code)

                browser.close()

                return dealers

            except Exception as e:
                print(f"  ✗ Error scraping with Playwright: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
                return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.

        ⚠️ WARNING: Extraction script is incomplete. Do not use in production
        until get_extraction_script() has been updated with correct DOM selectors.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        print("⚠️  WARNING: Cummins extraction script needs manual DOM inspection")
        print("⚠️  Results may be empty or incorrect until script is updated")

        # Build 6-step workflow for Cummins
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 3000},
            {"action": "evaluate", "script": self.get_extraction_script()},
        ]

        # Make HTTP request to RunPod API
        payload = {"input": {"workflow": workflow}}
        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping Cummins dealers for ZIP {zip_code}...")

            response = requests.post(
                self.runpod_api_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            if result.get("status") == "success":
                raw_dealers = result.get("results", [])
                print(f"[RunPod] Extracted {len(raw_dealers)} dealers")

                dealers = [self.parse_dealer_data(d, zip_code) for d in raw_dealers]
                return dealers
            else:
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"RunPod API error: {error_msg}")

        except requests.exceptions.Timeout:
            raise Exception(f"RunPod API timeout after 60 seconds")
        except requests.exceptions.RequestException as e:
            raise Exception(f"RunPod API request failed: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse RunPod API response as JSON")

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """BROWSERBASE mode: Cloud browser automation (future implementation)."""
        raise NotImplementedError("Browserbase mode not yet implemented")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """PATCHRIGHT mode: Stealth browser automation (future implementation)."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.

        Args:
            results_json: Array of dealer objects from browser_evaluate
            zip_code: ZIP code that was searched

        Returns:
            List of StandardizedDealer objects
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Cummins scraper with factory
ScraperFactory.register("Cummins", CumminsScraper)
ScraperFactory.register("cummins", CumminsScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    print("⚠️  Cummins scraper needs manual DOM inspection before use")
    print("⚠️  Run in PLAYWRIGHT mode to inspect site structure")
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("53202")  # Milwaukee
