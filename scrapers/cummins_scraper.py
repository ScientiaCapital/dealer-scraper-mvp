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

        ⚠️ PLACEHOLDER - Needs manual DOM inspection ⚠️

        To complete this script:
        1. Run this scraper in PLAYWRIGHT mode
        2. Navigate to dealer locator and search a ZIP code
        3. Inspect the dealer cards in browser DevTools
        4. Identify selectors for: name, address, phone, website, tier, distance
        5. Update this script with correct DOM traversal logic

        Expected return format:
        [
          {
            name: "DEALER NAME",
            phone: "(555) 555-5555",
            website: "https://example.com",
            domain: "example.com",
            street: "123 Main St",
            city: "City",
            state: "ST",
            zip: "12345",
            address_full: "123 Main St, City, ST 12345",
            rating: 4.5,
            review_count: 42,
            tier: "Authorized Dealer",
            certifications: ["Certified Installer"],
            distance: "5.2 mi",
            distance_miles: 5.2
          }
        ]
        """
        return """
() => {
  // TODO: Inspect Cummins dealer locator DOM structure
  // This is a PLACEHOLDER extraction script

  console.warn("Cummins extraction script needs manual DOM inspection");

  // Example pattern (update based on actual site structure):
  const dealerCards = Array.from(document.querySelectorAll('.dealer-card, [class*="dealer"]'));

  const dealers = dealerCards.map(card => {
    // Extract dealer name
    const nameEl = card.querySelector('h3, h4, .dealer-name, [class*="name"]');
    const name = nameEl ? nameEl.textContent.trim() : '';

    // Extract phone
    const phoneLink = card.querySelector('a[href^="tel:"]');
    const phone = phoneLink ? phoneLink.textContent.trim() : '';

    // Extract address
    const addressEl = card.querySelector('.address, [class*="address"]');
    const addressText = addressEl ? addressEl.textContent.trim() : '';

    // Parse address components (adjust regex based on format)
    const streetMatch = addressText.match(/(\\d+\\s+[^,\\n]+)/);
    const street = streetMatch ? streetMatch[1].trim() : '';

    const cityStateZip = addressText.match(/([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
    const city = cityStateZip ? cityStateZip[1].trim() : '';
    const state = cityStateZip ? cityStateZip[2] : '';
    const zip = cityStateZip ? cityStateZip[3] : '';

    // Extract website
    const websiteLink = card.querySelector('a[href^="http"]:not([href*="tel:"]):not([href*="google"])');
    const website = websiteLink ? websiteLink.href : '';

    let domain = '';
    if (website) {
      try {
        const url = new URL(website);
        domain = url.hostname.replace('www.', '');
      } catch (e) {}
    }

    // Extract distance
    const distanceEl = card.querySelector('.distance, [class*="distance"]');
    const distance = distanceEl ? distanceEl.textContent.trim() : '';
    const distanceMiles = parseFloat(distance) || 0;

    // Extract tier (may not be shown on Cummins site)
    const tier = 'Authorized Dealer';

    return {
      name: name,
      phone: phone,
      website: website,
      domain: domain,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
      rating: 0,  // Cummins may not show ratings
      review_count: 0,
      tier: tier,
      certifications: [tier],
      distance: distance,
      distance_miles: distanceMiles
    };
  });

  return dealers.filter(d => d && d.name && d.phone);
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
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.

        ⚠️ IMPORTANT: Extraction script is incomplete. You must:
        1. Follow these steps to navigate the site
        2. Inspect the dealer card DOM structure
        3. Update get_extraction_script() with correct selectors
        4. Test the extraction script before using RUNPOD mode
        """
        print(f"\n{'='*60}")
        print(f"Cummins Dealer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  EXTRACTION SCRIPT INCOMPLETE - MANUAL DOM INSPECTION REQUIRED\n")
        print("⚠️  MANUAL WORKFLOW - Execute these steps:\n")

        print("1. Navigate to Cummins dealer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to inspect page structure:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. If cookie dialog appears, click Accept:")
        print('   mcp__playwright__browser_click({"element": "Accept/I Agree button", "ref": "[from snapshot]"})\n')

        print("4. Fill ZIP code input (find selector in snapshot):")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')

        print("5. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search button", "ref": "[from snapshot]"})\n')

        print("6. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("7. Take another snapshot to see dealer cards:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("8. Inspect dealer card structure and update get_extraction_script()")
        print("   Look for:")
        print("   - Dealer name element (h3, h4, .dealer-name)")
        print("   - Phone link (a[href^='tel:'])")
        print("   - Address element (.address, [class*='address'])")
        print("   - Distance element (.distance, [class*='distance'])")
        print("   - Website link (a[href^='http'])")
        print("   - Tier/certification badges (if any)\n")

        print("9. After updating extraction script, test it:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("10. Parse results:")
        print(f'   cummins_scraper.parse_results(results_json, "{zip_code}")\n')

        print(f"{'='*60}\n")
        print("❌ Extraction script is INCOMPLETE")
        print("⚠️  Must inspect DOM and update get_extraction_script() before production use")
        print(f"{'='*60}\n")

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
