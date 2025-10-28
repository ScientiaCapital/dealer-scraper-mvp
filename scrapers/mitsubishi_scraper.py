"""
Mitsubishi Electric Diamond Commercial Contractor Locator Scraper

Scrapes Mitsubishi Electric's Diamond Commercial contractor network for VRF (Variable Refrigerant Flow)
HVAC systems. These are the highest-tier commercial HVAC contractors specializing in large-scale
commercial and resimercial projects.

Target URL: https://www.mitsubishi

comfort.com/get-started?get-started-tab=1

Capabilities detected from Mitsubishi Diamond Commercial certification:
- VRF system installation (commercial-grade multi-zone HVAC)
- CITY MULTI® systems (Mitsubishi's commercial VRF product line)
- Commercial HVAC expertise
- Resimercial projects ($500K-$2M+ installation value)
- 12-year extended warranty eligibility (Diamond Commercial exclusive)
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


class MitsubishiScraper(BaseDealerScraper):
    """
    Scraper for Mitsubishi Electric Diamond Commercial contractor network.

    Mitsubishi Diamond Commercial contractors are VRF (Variable Refrigerant Flow) specialists
    who install CITY MULTI® systems for commercial and large residential projects.

    Tier structure:
    - Diamond Commercial: TOP TIER - VRF/commercial specialists (THIS SCRAPER)
    - Diamond Contractor: Residential ductless experts (not targeted)
    - Elite Diamond Contractor: Advanced residential (not targeted)
    - Standard contractors: Basic certification (not targeted)

    Key indicators:
    - Diamond Commercial = strong commercial signal
    - VRF installation capability = $500K-$2M+ project values
    - 12-year warranty = exclusive to Diamond Commercial tier
    - Resimercial market focus = ideal Coperniq ICP
    """

    OEM_NAME = "Mitsubishi Electric"
    DEALER_LOCATOR_URL = "https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor"
    PRODUCT_LINES = ["VRF Systems", "CITY MULTI®", "Commercial HVAC", "Heat Pumps"]

    # CSS Selectors (modern React/Next.js site)
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept All Cookies')",
        "commercial_tab": "tab:has-text('Commercial building')",  # Select the Commercial tab
        "zip_input": "input[placeholder*='Zip']",  # ZIP code input in the commercial form
        "search_button": "button:has-text('Search')",  # Search button
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
        """JavaScript extraction for Mitsubishi Diamond Commercial contractors"""
        return """
() => {
  const contractors = [];
  const seen = new Set();
  const nameElements = document.querySelectorAll('h3');
  
  nameElements.forEach(h3 => {
    const name = h3.textContent.trim();
    
    // Skip non-contractor h3 elements
    if (name.toLowerCase().includes('training') || 
        name.toLowerCase().includes('warranty') ||
        name.toLowerCase().includes('hire with confidence') ||
        name.toLowerCase().includes('advanced training') ||
        name.toLowerCase().includes('extended warranty') ||
        name.toLowerCase().includes('manage consent') ||
        name.toLowerCase().includes('cookie list') ||
        name.length < 5) {
      return;
    }
    
    // Find container with phone link (Card_contractorCard class)
    let container = h3.parentElement;
    let iterations = 0;
    while (container && !container.querySelector('a[href^="tel:"]') && iterations < 10) {
      container = container.parentElement;
      iterations++;
      if (container === document.body) {
        container = null;
        break;
      }
    }
    
    if (!container) return;
    
    // Extract phone
    let phone = '';
    const phoneLink = container.querySelector('a[href^="tel:"]');
    if (phoneLink) {
      phone = phoneLink.href.replace(/[^0-9]/g, '');
      // Remove leading 1 (country code)
      if (phone.length === 11 && phone[0] === '1') {
        phone = phone.substring(1);
      }
    }

    // Extract location - look for the first occurrence of City, ST ZIP pattern
    let city = '', state = '', zip = '';
    const containerText = container.innerText || container.textContent || '';
    // Match "City, ST ZIP" where city starts after word boundary or newline
    const locationMatch = containerText.match(/(?:^|[\\n\\r])([A-Za-z][A-Za-z ]+?), *([A-Z]{2}) +([0-9]{5})/);
    if (locationMatch) {
      city = locationMatch[1].trim();
      state = locationMatch[2];
      zip = locationMatch[3];
    }
    
    // Extract website
    let website = '';
    const links = container.querySelectorAll('a[href^="http"]');
    for (const link of links) {
      const href = link.href;
      if (!href.includes('tel:') && 
          !href.includes('google.com') && 
          !href.includes('mitsubishicomfort.com') &&
          !href.includes('policies.google')) {
        website = href;
        break;
      }
    }
    
    // Only add if we have required fields
    const key = `${name}|${phone}|${city}|${state}|${zip}`;
    if (!seen.has(key) && phone && city && state && zip) {
      seen.add(key);
      contractors.push({
        name: name,
        phone: phone,
        website: website || '',
        street: '',  // Not available in results
        city: city,
        state: state,
        zip: zip,
        address_full: `${city}, ${state} ${zip}`,
        rating: 0.0,
        review_count: 0,
        tier: 'Diamond Commercial',
        certifications: ['Diamond Commercial Contractor', 'VRF Certified', '12-Year Warranty Eligible'],
        distance: '',  // Will be calculated if needed
        distance_miles: 0.0
      });
    }
  });
  
  return contractors;
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Mitsubishi Diamond Commercial contractor data.

        Diamond Commercial certification indicates:
        - Commercial HVAC expertise (VRF systems)
        - Multi-zone HVAC installation (CITY MULTI®)
        - Electrical work (required for VRF installation)
        - Mechanical trade expertise
        - Resimercial project capability ($500K-$2M+)
        - O&M potential (VRF systems require ongoing maintenance)
        """
        caps = DealerCapabilities()

        # All Mitsubishi Diamond Commercial contractors have HVAC + electrical
        caps.has_hvac = True
        caps.has_electrical = True

        # VRF contractors are typically commercial or resimercial
        caps.is_commercial = True

        # Many Diamond Commercial contractors also do residential (resimercial)
        dealer_name = raw_dealer_data.get("name", "").upper()
        if any(keyword in dealer_name for keyword in ["COOLING", "HEATING", "AIR", "COMFORT"]):
            caps.is_residential = True  # Resimercial signal

        # Add Mitsubishi OEM certification
        caps.oem_certifications.add("Mitsubishi Electric")

        # Detect high-value contractor types (O&M and MEP+R)
        certifications_list = ["Diamond Commercial", "VRF Certified"]
        tier = "Diamond Commercial"
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Mitsubishi contractor data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # All Diamond Commercial contractors have same tier + certifications
        tier = "Diamond Commercial"
        certifications = [
            "Diamond Commercial Contractor",
            "VRF Systems Certified",
            "CITY MULTI® Installer",
            "12-Year Extended Warranty"
        ]

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
            oem_source="Mitsubishi Electric",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated scraping using local Playwright.

        Mitsubishi uses a modern React/Next.js site with:
        - Direct URL to Diamond Commercial contractor page (no tab navigation needed)
        - AJAX-loaded results (need to wait for dynamic content)
        - Clean semantic HTML (easy extraction)
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

                # Navigate to Diamond Commercial contractor locator (redirects to get-started)
                print(f"  → Navigating to Mitsubishi contractor locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(3)

                # Handle cookie consent dialog if it appears
                print(f"  → Checking for cookie consent dialog...")
                try:
                    cookie_selectors = [
                        'button:has-text("Accept All Cookies")',
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
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

                # Click "Commercial building" tab to reveal ZIP search form
                print(f"  → Clicking 'Commercial building' tab...")
                try:
                    # The "Commercial building" tab text
                    page.click('text=Commercial building', timeout=5000)
                    time.sleep(2)
                    print(f"     Commercial tab clicked successfully")
                except Exception as e:
                    print(f"     Warning: Could not click Commercial tab: {e}")
                    raise Exception("Could not find/click Commercial building tab")

                # Fill ZIP code
                print(f"  → Filling ZIP code: {zip_code}")
                zip_input_selectors = [
                    'input[placeholder*="Zip" i]',
                    'textbox[name*="Zip" i]',
                    'input[type="text"]',
                ]

                zip_filled = False
                for selector in zip_input_selectors:
                    try:
                        zip_input = page.locator(selector)
                        # Get the one that's actually visible (commercial form, not residential)
                        visible_inputs = [zip_input.nth(i) for i in range(zip_input.count()) if zip_input.nth(i).is_visible()]
                        if visible_inputs:
                            visible_inputs[0].fill(zip_code)
                            time.sleep(1)
                            zip_filled = True
                            break
                    except Exception:
                        continue

                if not zip_filled:
                    raise Exception("Could not find ZIP code input")

                # Click search button
                print(f"  → Clicking search button...")
                button_selectors = [
                    'button:has-text("Search")',
                    'button[type="submit"]',
                ]

                button_clicked = False
                for selector in button_selectors:
                    try:
                        btns = page.locator(selector)
                        # Get visible search button (commercial form)
                        for i in range(btns.count()):
                            btn = btns.nth(i)
                            if btn.is_visible():
                                btn.click(timeout=5000)
                                button_clicked = True
                                break
                        if button_clicked:
                            break
                    except Exception:
                        continue

                if not button_clicked:
                    raise Exception("Could not find/click search button")

                # Wait for AJAX results to load
                print(f"  → Waiting for results...")
                time.sleep(5)

                # Extract dealers using JavaScript
                print(f"  → Extracting dealer data...")
                extraction_script = self.get_extraction_script()
                dealers_data = page.evaluate(extraction_script)

                print(f"  → Found {len(dealers_data)} Diamond Commercial contractors")

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

        Sends 7-step workflow to RunPod Playwright API (extra step for tab click).
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build 7-step workflow for Mitsubishi
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
            {"action": "click", "selector": self.SELECTORS["commercial_tab"]},  # Click Commercial tab
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 5000},  # 5 seconds for AJAX
            {"action": "evaluate", "script": self.get_extraction_script()},
        ]

        # Make HTTP request to RunPod API
        payload = {"input": {"workflow": workflow}}
        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping Mitsubishi Diamond Commercial contractors for ZIP {zip_code}...")

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
                print(f"[RunPod] Extracted {len(raw_dealers)} contractors")

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
            results_json: Array of contractor objects from browser_evaluate
            zip_code: ZIP code that was searched

        Returns:
            List of StandardizedDealer objects
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Mitsubishi scraper with factory
ScraperFactory.register("Mitsubishi Electric", MitsubishiScraper)
ScraperFactory.register("Mitsubishi", MitsubishiScraper)
ScraperFactory.register("mitsubishi", MitsubishiScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = MitsubishiScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("10001")  # New York (Diamond Commercial test)
