"""
SimpliPhi Power Battery Installer Scraper

Scrapes SimpliPhi Power's (now Briggs & Stratton Energy Solutions) installer network.
SimpliPhi specializes in non-toxic, cobalt-free lithium ferrophosphate (LFP) batteries for energy storage.

Target URL: https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html

Capabilities detected from SimpliPhi certification:
- Battery installation (SimpliPhi's core product - PHI batteries)
- Solar integration (batteries pair with solar systems)
- Electrical work (required for battery installation)
- Energy storage systems (residential and commercial)
- Off-grid and backup power systems

Strategic importance for Coperniq:
- SimpliPhi batteries are brand-agnostic (work with any inverter brand) - perfect for Coperniq's platform
- Premium LFP battery technology (longer lifespan than NMC batteries)
- Strong focus on resilience and backup power (monitoring use case)
- Installers often carry multiple battery brands (SimpliPhi + Tesla + Enphase) - high multi-OEM probability
- Now part of Briggs & Stratton (generator company) - potential generator integration opportunities
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


class SimpliPhiScraper(BaseDealerScraper):
    """
    Scraper for SimpliPhi Power installer network (now Briggs & Stratton Energy Solutions).

    SimpliPhi installers specialize in:
    - Lithium ferrophosphate (LFP) battery installation
    - Energy storage system design and installation
    - Solar + battery integration
    - Off-grid and backup power systems
    - Residential and commercial energy storage

    Product Range:
    - SimpliPHI 6.6 Battery (modular 6.65 kWh, stackable up to 3 for 19.95 kWh)
    - PHI 3.8 Battery (residential backup power)
    - PHI 1.4 Battery (small-scale applications)
    - AmpliPHI (commercial-scale battery systems)

    Note: SimpliPhi is now part of Briggs & Stratton Energy Solutions (acquired 2021).
    """

    OEM_NAME = "SimpliPhi"
    DEALER_LOCATOR_URL = "https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html"
    PRODUCT_LINES = ["Battery Storage", "LFP Batteries", "Energy Storage Systems", "Backup Power", "Commercial"]

    # CSS Selectors (verified December 2025)
    SELECTORS = {
        "country_select": "select[name='dealercountry']",  # Country dropdown
        "zip_input": "input[name='zipcode']",              # ZIP code input
        "product_select": "select[name='productOfInterest']",  # Product dropdown
        "search_button": ".dealer-search-textbox button",  # Search button
        "dealer_cards": ".dealer-info-container",          # Dealer result cards
        "dealer_name": ".dealer-name",                     # Dealer name
        "dealer_phone": ".dealer-phone-number",            # Phone number
        "dealer_address": ".dealer-address",               # Street address
        "dealer_city_state": ".dealer-city-state-zip",     # City, State ZIP
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

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction script for SimpliPhi installer data.

        Briggs & Stratton dealer locator allows filtering by:
        - Product type (Standby Generators, Battery Energy Storage)
        - Search radius (50, 75, 100, 150 miles)

        This script extracts dealers who offer Battery Energy Storage.
        """

        extraction_script = r"""
() => {
  const dealers = [];

  // Find all dealer containers using the correct selector
  const containers = document.querySelectorAll('.dealer-info-container');
  console.log(`[SimpliPhi] Found ${containers.length} dealer containers`);

  containers.forEach((container, idx) => {
    try {
      // Extract dealer name
      const name = container.querySelector('.dealer-name')?.textContent?.trim() || '';
      if (!name || name.length < 2) return;

      // Extract phone number
      let phone = container.querySelector('.dealer-phone-number')?.textContent?.trim() || '';
      phone = phone.replace('Call:', '').trim();

      // Extract address
      const street = container.querySelector('.dealer-address')?.textContent?.trim() || '';
      const cityStateZip = container.querySelector('.dealer-city-state-zip')?.textContent?.trim() || '';

      // Parse city, state, zip from combined field
      let city = '', state = '', zip = '';
      if (cityStateZip) {
        const match = cityStateZip.match(/(.+),\s*([A-Z]{2})\s*(\d{5})?/);
        if (match) {
          city = match[1] || '';
          state = match[2] || '';
          zip = match[3] || '';
        }
      }

      // Construct full address
      const address_full = [street, cityStateZip].filter(p => p).join(', ');

      // Extract certifications and capabilities
      const certifications = ['SimpliPhi Authorized'];
      const capabilities = ['Battery Storage', 'Energy Storage Systems'];

      // Check for product offerings
      let has_generators = false;
      let has_solar = false;

      container.querySelectorAll('.dealer-info-sales-content, .dealer-product-line-icon').forEach(prod => {
        const text = prod.textContent?.trim().toLowerCase() || '';

        if (text.includes('generator') || text.includes('standby')) {
          capabilities.push('Generators');
          certifications.push('Generator Certified');
          has_generators = true;
        }
        if (text.includes('solar') || text.includes('pv')) {
          capabilities.push('Solar');
          certifications.push('Solar Installation');
          has_solar = true;
        }
      });

      // Check name for capability indicators
      const nameLower = name.toLowerCase();
      if (!has_solar && (nameLower.includes('solar') || nameLower.includes('renewable') || nameLower.includes('energy'))) {
        capabilities.push('Solar');
        has_solar = true;
      }
      if (!has_generators && (nameLower.includes('generator') || nameLower.includes('power'))) {
        capabilities.push('Generators');
        has_generators = true;
      }

      // Check for commercial indicators
      const has_commercial = nameLower.includes('commercial') ||
                            nameLower.includes('solutions') ||
                            nameLower.includes('systems') ||
                            nameLower.includes('inc') ||
                            nameLower.includes('llc');

      dealers.push({
        name: name,
        phone: phone,
        email: '',
        website: '',
        street: street,
        city: city,
        state: state,
        zip: zip,
        address_full: address_full,
        certifications: certifications,
        capabilities: capabilities,
        rating: 0,
        review_count: 0,
        tier: 'SimpliPhi Elite IQ Installer',
        distance: '',
        distance_miles: 0,
        has_commercial: has_commercial,
        has_generators: has_generators,
        has_solar: has_solar,
        is_multi_product: has_generators || has_solar,
        is_resimercial: has_commercial,
        oem_source: 'SimpliPhi'
      });
    } catch (error) {
      console.log(`[SimpliPhi] Error parsing dealer: ${error.message}`);
    }
  });

  console.log(`[SimpliPhi] Extracted ${dealers.length} installers`);
  return dealers;
}
"""

        return extraction_script

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from SimpliPhi installer data.

        SimpliPhi installers indicate:
        - All installers: has_battery + has_electrical
        - Many also do solar (batteries integrate with solar systems)
        - Some also install Briggs & Stratton generators (same parent company)
        - Commercial battery systems (AmpliPHI) = commercial capability
        """
        caps = DealerCapabilities()

        # All SimpliPhi installers have battery capability (core product)
        caps.has_battery = True
        caps.has_electrical = True

        # Check capabilities list
        capabilities = raw_dealer_data.get("capabilities", [])

        # Solar capability
        if "Solar" in capabilities or raw_dealer_data.get("has_solar"):
            caps.has_solar = True
            caps.has_inverters = True  # Solar systems need inverters
            caps.has_roofing = True    # Solar requires roof work

        # Generator capability (Briggs & Stratton parent company)
        if "Generators" in capabilities or raw_dealer_data.get("has_generators"):
            caps.has_generator = True

        # Commercial capability
        if "Commercial" in capabilities or raw_dealer_data.get("has_commercial"):
            caps.is_commercial = True

        # Check for multi-product (generators + solar + batteries)
        if raw_dealer_data.get("is_multi_product"):
            caps.is_residential = True
            caps.is_commercial = True
        else:
            # Default to residential if not explicitly commercial
            caps.is_residential = True

        # Add SimpliPhi OEM certifications
        caps.oem_certifications.add("SimpliPhi")
        caps.battery_oems.add("SimpliPhi")

        # If they also do Briggs & Stratton generators
        if caps.has_generator:
            caps.oem_certifications.add("Briggs & Stratton")

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw SimpliPhi installer data to StandardizedDealer format.
        """
        # Extract domain from website
        website = raw_dealer_data.get("website", "")
        domain = ""
        if website:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(website)
                domain = parsed.netloc.replace("www.", "")
            except:
                domain = ""

        # Parse distance
        distance_str = raw_dealer_data.get("distance", "")
        distance_miles = raw_dealer_data.get("distance_miles", 0.0)

        # Get address components
        street = raw_dealer_data.get("street", "")
        city = raw_dealer_data.get("city", "")
        state = raw_dealer_data.get("state", "")
        zip_val = raw_dealer_data.get("zip", "")

        address_full = raw_dealer_data.get("address_full", "")
        if not address_full and all([street, city, state, zip_val]):
            address_full = f"{street}, {city}, {state} {zip_val}"

        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Set special flags (for GTM targeting)
        is_multi_product = raw_dealer_data.get("is_multi_product", False)  # Gen + Solar + Battery
        is_resimercial = raw_dealer_data.get("is_resimercial", False)

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=domain,
            website=website,
            street=street,
            city=city,
            state=state,
            zip=zip_val,
            address_full=address_full,
            rating=raw_dealer_data.get("rating", 0.0),
            review_count=raw_dealer_data.get("review_count", 0),
            tier=raw_dealer_data.get("tier", "SimpliPhi Authorized Installer"),
            certifications=raw_dealer_data.get("certifications", []),
            distance=distance_str,
            distance_miles=distance_miles,
            capabilities=capabilities,
            oem_source="SimpliPhi",
            scraped_from_zip=zip_code,
            is_resimercial=is_resimercial
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated scraping using Playwright.
        """
        from playwright.sync_api import sync_playwright
        import time

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔋 SIMPLIPHI: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to dealer locator
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000)
                time.sleep(3)

                # Select United States
                print(f"  → Selecting United States")
                try:
                    page.locator(self.SELECTORS["country_select"]).select_option("United States")
                    time.sleep(1)
                except Exception as e:
                    print(f"  ⚠️  Country select: {e}")

                # Select Battery Storage product
                print(f"  → Selecting Battery Storage product")
                try:
                    page.locator(self.SELECTORS["product_select"]).select_option("Battery Storage")
                    time.sleep(1)
                except Exception as e:
                    print(f"  ⚠️  Product select: {e}")

                # Fill ZIP code
                print(f"  → Filling ZIP code: {zip_code}")
                try:
                    zip_input = page.locator(self.SELECTORS["zip_input"])
                    zip_input.fill(zip_code)
                    time.sleep(1)
                except Exception as e:
                    print(f"  ❌ ZIP input error: {e}")
                    browser.close()
                    return []

                # Click search button
                print(f"  → Clicking search button")
                try:
                    search_btn = page.locator(self.SELECTORS["search_button"]).first
                    search_btn.click()
                except Exception as e:
                    print(f"  ⚠️  Search button: {e}, trying Enter key")
                    page.locator(self.SELECTORS["zip_input"]).press("Enter")

                # Wait for results to load
                print(f"  → Waiting for results...")
                time.sleep(8)

                # Check for dealer results
                dealer_count = page.locator(self.SELECTORS["dealer_cards"]).count()
                if dealer_count == 0:
                    print(f"  ⚠️  No dealers found for ZIP {zip_code}")
                    browser.close()
                    return []

                print(f"  → Found {dealer_count} dealer cards, extracting...")

                # Execute extraction script
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ Extraction returned no results")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} SimpliPhi installers")

                # Count multi-trade
                solar_count = sum(1 for d in dealers if d.capabilities.has_solar)
                if solar_count > 0:
                    print(f"     ({solar_count} also do solar)")

                browser.close()
                return dealers

            except Exception as e:
                print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
                return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build workflow for SimpliPhi
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 2000},
            {"action": "select", "selector": self.SELECTORS["country_select"], "value": "USA"},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": f'{self.SELECTORS["product_filter"]}[value="battery"]'},
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

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Not yet implemented for SimpliPhi.

        Use PLAYWRIGHT mode for manual testing or RUNPOD mode for production.
        """
        raise NotImplementedError(
            "Patchright mode not yet implemented for SimpliPhi scraper. "
            "Use PLAYWRIGHT or RUNPOD mode instead."
        )

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register SimpliPhi scraper with factory
ScraperFactory.register("SimpliPhi", SimpliPhiScraper)
ScraperFactory.register("simpliphi", SimpliPhiScraper)
ScraperFactory.register("SimpliPhi Power", SimpliPhiScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = SimpliPhiScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = SimpliPhiScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/simpliphi_installers_sf.json")
