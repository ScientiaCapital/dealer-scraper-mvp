"""
Briggs & Stratton Dealer Locator Scraper

Scrapes Briggs & Stratton's dealer network for standby generators and battery storage installations.
Briggs dealers are typically electrical contractors who install home backup power systems.

Target URL: https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html

Capabilities detected from Briggs & Stratton certification:
- Generator installation (standby generators)
- Battery storage systems
- Electrical work (required for installations)
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


class BriggsStrattonScraper(BaseDealerScraper):
    """
    Scraper for Briggs & Stratton dealer network.

    Briggs & Stratton dealer tiers:
    - Platinum Pro Dealer: Highest tier with advanced training and support
    - Platinum Dealer: Premium dealer with elevated service level
    - Elite IQ Installer: Battery storage specialist with advanced certification
    - Standard: Basic authorized dealer

    Note: Briggs dealers may specialize in either standby generators OR battery storage,
    unlike Generac which is generator-only. Check product type badges.
    """

    OEM_NAME = "Briggs & Stratton"
    DEALER_LOCATOR_URL = "https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html"
    PRODUCT_LINES = ["Standby Generator", "Battery Storage", "Energy Storage", "Transfer Switches"]

    # CSS Selectors
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept All')",
        "zip_input": "input[placeholder*='Zip' i], input[placeholder*='City' i]",
        "search_button": "#dealer-form button",
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
        JavaScript extraction script for Briggs & Stratton dealer data.

        Briggs uses a different DOM structure than Generac:
        - Dealer cards are in generic containers (not using phone links as anchors)
        - Tier badges show as images with alt text ("PLATINUM PRO DEALER", "ELITE IQ INSTALLER")
        - Product type shown as separate badges (Standby Generators, Battery Storage)
        - Distance shown in h5 heading (e.g., "10.46 Miles")
        """
        return """
() => {
  // Find all dealer cards by looking for headings with dealer names
  const dealerHeadings = Array.from(document.querySelectorAll('h5')).filter(h5 => {
    const text = h5.textContent.trim();
    // Filter for dealer names (all caps or title case, not "Miles" or other system text)
    return text.length > 3 &&
           !text.includes('Miles') &&
           !text.includes('Filters') &&
           !text.includes('Distance');
  });

  const dealers = dealerHeadings.map(heading => {
    // Find the dealer card container (go up to parent generic elements)
    let container = heading;
    for (let i = 0; i < 10; i++) {
      container = container.parentElement;
      if (!container) break;

      // Look for container that has both dealer info and distance
      const hasDistance = container.textContent.includes('Miles');
      const hasPhone = container.querySelector('a[href^="tel:"]');
      if (hasDistance && hasPhone) break;
    }

    if (!container) return null;

    const fullText = container.textContent;
    const dealerName = heading.textContent.trim();

    // Extract phone from tel: link
    const phoneLink = container.querySelector('a[href^="tel:"]');
    const phoneText = phoneLink ? phoneLink.textContent.trim() : '';

    // Extract address from paragraph after heading
    const addressPara = heading.nextElementSibling;
    let street = '';
    let city = '';
    let state = '';
    let zip = '';

    if (addressPara && addressPara.tagName === 'P') {
      const addressLines = addressPara.textContent.trim().split('\\n').map(l => l.trim()).filter(l => l);
      if (addressLines.length >= 2) {
        street = addressLines[0];
        // Second line is "CITY, ST ZIP"
        const cityStateZip = addressLines[1].match(/([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
        if (cityStateZip) {
          city = cityStateZip[1].trim();
          state = cityStateZip[2];
          zip = cityStateZip[3];
        }
      }
    }

    // Extract website from non-phone links
    const websiteLink = container.querySelector('a[href^="http"]:not([href*="tel:"]):not([href*="google"]):not([href*="facebook"])');
    const website = websiteLink?.href || '';

    let domain = '';
    if (website) {
      try {
        const url = new URL(website);
        domain = url.hostname.replace('www.', '');
      } catch (e) {
        domain = '';
      }
    }

    // Extract distance from h5 heading with "Miles"
    const distanceHeadings = Array.from(container.querySelectorAll('h5'));
    const distanceH5 = distanceHeadings.find(h => h.textContent.includes('Miles'));
    const distance = distanceH5 ? distanceH5.textContent.trim() : '';
    const distanceMiles = parseFloat(distance) || 0;

    // Extract tier from badge images
    let tier = 'Standard';
    const tierImages = Array.from(container.querySelectorAll('img'));
    for (const img of tierImages) {
      const alt = img.alt || '';
      const src = img.src || '';

      if (alt.includes('PLATINUM PRO') || src.includes('Platinum_Pro')) {
        tier = 'Platinum Pro Dealer';
        break;
      } else if (alt.includes('PLATINUM') || src.includes('Platinum_Dealer')) {
        tier = 'Platinum Dealer';
        break;
      } else if (alt.includes('ELITE IQ') || src.includes('Elite_IQ')) {
        tier = 'Elite IQ Installer';
        break;
      }
    }

    // Extract product types from badge images
    const hasStandbyGenerators = fullText.includes('Standby Generators');
    const hasBatteryStorage = fullText.includes('Battery Storage');

    // Briggs doesn't show ratings/reviews in dealer locator
    const rating = 0;
    const reviewCount = 0;

    // Build certifications array
    const certifications = [];
    if (tier !== 'Standard') {
      certifications.push(tier);
    }
    if (hasStandbyGenerators) {
      certifications.push('Standby Generators Certified');
    }
    if (hasBatteryStorage) {
      certifications.push('Battery Storage Certified');
    }

    return {
      name: dealerName,
      rating: rating,
      review_count: reviewCount,
      tier: tier,
      has_standby_generators: hasStandbyGenerators,
      has_battery_storage: hasBatteryStorage,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
      phone: phoneText,
      website: website,
      domain: domain,
      distance: distance,
      distance_miles: distanceMiles
    };
  });

  return dealers.filter(d => d && d.name && d.phone);
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Briggs & Stratton dealer data.

        Briggs certifications indicate:
        - All dealers: has_electrical (minimum for generator/battery install)
        - Standby Generators badge: has_generator
        - Battery Storage badge: has_battery
        - Platinum Pro/Elite IQ tiers: Higher service commitment

        Unlike Generac (generator-only), Briggs dealers may specialize in:
        1. Standby generators only
        2. Battery storage only
        3. Both (highest value for Coperniq)
        """
        caps = DealerCapabilities()

        # All Briggs dealers have electrical capability
        caps.has_electrical = True

        # Check product type badges
        has_standby = raw_dealer_data.get("has_standby_generators", False)
        has_battery = raw_dealer_data.get("has_battery_storage", False)

        if has_standby:
            caps.has_generator = True
            caps.generator_oems.add("Briggs & Stratton")

        if has_battery:
            caps.has_battery = True
            caps.battery_oems.add("Briggs & Stratton")

        # Extract tier
        tier = raw_dealer_data.get("tier", "Standard")

        # Platinum Pro and Elite IQ indicate higher capability
        if tier in ["Platinum Pro Dealer", "Elite IQ Installer"]:
            caps.is_residential = True
            # Elite IQ specifically for battery storage
            if tier == "Elite IQ Installer":
                caps.has_battery = True
                caps.battery_oems.add("Briggs & Stratton")

        # Platinum dealers indicate solid residential service
        if "Platinum" in tier:
            caps.is_residential = True

        # Add Briggs & Stratton OEM certification
        caps.oem_certifications.add("Briggs & Stratton")

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = []
        if tier != "Standard":
            certifications_list.append(tier)
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Briggs & Stratton dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications from tier and product types
        tier = raw_dealer_data.get("tier", "Standard")
        certifications = []

        if tier != "Standard":
            certifications.append(tier)

        if raw_dealer_data.get("has_standby_generators"):
            certifications.append("Standby Generators Certified")

        if raw_dealer_data.get("has_battery_storage"):
            certifications.append("Battery Storage Certified")

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
            oem_source="Briggs & Stratton",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.

        Returns empty list and prints workflow instructions for manual execution.
        """
        print(f"\n{'='*60}")
        print(f"Briggs & Stratton Dealer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Briggs & Stratton dealer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to get current element refs:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. Click Accept All cookies button:")
        print('   mcp__playwright__browser_click({"element": "Accept All", "ref": "[from snapshot]"})\n')

        print("4. Fill ZIP code input:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code search input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')

        print("5. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search button", "ref": "[from snapshot]"})\n')

        print("6. Wait for AJAX results to load (3 seconds):")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("7. Extract dealer data using tested extraction script:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("8. Copy the results JSON and pass to parse_results():")
        print(f'   briggs_scraper.parse_results(results_json, "{zip_code}")\n')

        print(f"{'='*60}\n")
        print("✅ Extraction script is ready for testing")
        print("⚠️  Element refs change between page loads - always take fresh snapshot")
        print(f"{'='*60}\n")

        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.

        Sends 6-step workflow to RunPod Playwright API.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build 6-step workflow for Briggs & Stratton
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 3000},  # 3 seconds for AJAX
            {"action": "evaluate", "script": self.get_extraction_script()},
        ]

        # Make HTTP request to RunPod API
        payload = {"input": {"workflow": workflow}}
        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping Briggs & Stratton dealers for ZIP {zip_code}...")

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


# Register Briggs & Stratton scraper with factory
ScraperFactory.register("Briggs & Stratton", BriggsStrattonScraper)
ScraperFactory.register("briggs", BriggsStrattonScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = BriggsStrattonScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco
