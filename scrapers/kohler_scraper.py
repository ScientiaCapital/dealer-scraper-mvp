"""
Kohler Dealer Locator Scraper

Scrapes Kohler's dealer network for home generators.
Kohler dealers are typically electrical contractors who specialize in residential backup power.

Target URL: https://kohlerpower.com/en/residential/generators/dealer-locator
Alternative: https://www.kohlerhomeenergy.rehlko.com/find-a-dealer

Capabilities detected from Kohler certification:
- Generator installation (home standby systems)
- Electrical work (required for generator install)
- Residential focus (Kohler emphasizes premium home generators)

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


class KohlerScraper(BaseDealerScraper):
    """
    Scraper for Kohler dealer network.

    Kohler dealer tiers (typical for premium home generator OEMs):
    - Certified Installer: Basic certification
    - Premier Dealer: Higher service commitment (if applicable)

    Kohler is known for premium residential generators with quiet operation
    and whole-home backup power solutions.
    """

    OEM_NAME = "Kohler"
    # Note: Kohler Energy rebranded to Rehlko in 2024
    DEALER_LOCATOR_URL = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
    PRODUCT_LINES = ["Home Generators", "Residential", "Standby", "Whole Home Backup"]

    # CSS Selectors - Based on Rehlko/Kohler site structure
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept')",
        "zip_input": "input[type='text']",  # ZIP code input field
        "search_button": "button:has-text('Go')",
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
        JavaScript extraction script for Kohler dealer data.

        Validated 2025-11-28 against kohlerhomeenergy.rehlko.com/find-a-dealer
        Tested on ZIP 94102 - extracts name, phone, address, tier, website, distance.
        """
        return """
() => {
  // Find dealer cards by Tailwind class
  const dealerCards = document.querySelectorAll('li.list-none');

  const dealers = [];
  const seen = new Set(); // Track unique dealers by phone

  dealerCards.forEach(card => {
    // Skip cards that don't have a phone link (not dealer cards)
    const phoneLink = card.querySelector('a[href^="tel:"]');
    if (!phoneLink) return;

    // Skip the header phone number (844 main line)
    const phone = phoneLink.textContent?.trim() || '';
    if (phone.includes('844')) return;

    // Dedupe by phone
    if (seen.has(phone)) return;
    seen.add(phone);

    // Get all text content
    const fullText = card.textContent || '';

    // Extract company name (first line before distance)
    const nameMatch = fullText.match(/^([A-Z][A-Z\\s&\\.]+?)(\\d+\\.?\\d*\\s*miles)/);
    const name = nameMatch ? nameMatch[1].trim() : '';

    // Extract distance
    const distanceMatch = fullText.match(/(\\d+\\.?\\d*)\\s*miles/);
    const distanceMiles = distanceMatch ? parseFloat(distanceMatch[1]) : 0;
    const distance = distanceMatch ? `${distanceMatch[1]} miles` : '';

    // Extract tier (Gold, Silver, Bronze)
    let tier = '';
    if (fullText.includes('Gold Dealer')) tier = 'Gold Dealer';
    else if (fullText.includes('Silver Dealer')) tier = 'Silver Dealer';
    else if (fullText.includes('Bronze Dealer')) tier = 'Bronze Dealer';

    // Extract address - find address after tier info or miles
    const addressMatch = fullText.match(/(?:Certified|miles)(\\d+[^,]+),\\s*([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
    let street = '', city = '', state = '', zip = '';

    if (addressMatch) {
      street = addressMatch[1].trim();
      city = addressMatch[2].trim();
      state = addressMatch[3];
      zip = addressMatch[4];
    } else {
      // Fallback: find any address pattern
      const fallbackMatch = fullText.match(/(\\d+\\s+[A-Za-z0-9\\s\\.]+(?:Lane|Road|Ave|St|Cir|Dr|Way|Blvd)[^,]*),\\s*([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/i);
      if (fallbackMatch) {
        street = fallbackMatch[1].trim();
        city = fallbackMatch[2].trim();
        state = fallbackMatch[3].toUpperCase();
        zip = fallbackMatch[4];
      }
    }

    const addressFull = street ? `${street}, ${city}, ${state} ${zip}` : '';

    // Extract website
    const websiteLink = card.querySelector('a[href^="http"]');
    const website = websiteLink?.href || '';
    let domain = '';
    if (website) {
      try {
        const url = new URL(website);
        domain = url.hostname.replace('www.', '');
      } catch (e) {}
    }

    if (name && phone) {
      dealers.push({
        name,
        phone,
        website,
        domain,
        street,
        city,
        state,
        zip,
        address_full: addressFull,
        tier: tier || 'Certified Installer',
        distance,
        distance_miles: distanceMiles,
        certifications: tier ? [tier] : ['Certified Installer'],
        rating: 0,
        review_count: 0
      });
    }
  });

  return dealers;
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Kohler dealer data.

        Kohler certifications indicate:
        - All dealers: has_generator + has_electrical (minimum for install)
        - Kohler focuses on premium residential generators
        - Many dealers are electrical contractors specializing in backup power
        """
        caps = DealerCapabilities()

        # All Kohler dealers have generator and electrical capabilities
        caps.has_generator = True
        caps.has_electrical = True
        caps.generator_oems.add("Kohler")

        # Extract tier
        tier = raw_dealer_data.get("tier", "Certified Installer")

        # Premier/Elite tiers indicate higher capability (if Kohler uses these)
        if tier in ["Premier", "Premier Dealer", "Elite", "Elite Dealer"]:
            caps.is_residential = True
            caps.is_commercial = False  # Kohler is primarily residential-focused

        # Kohler has strong residential focus
        caps.is_residential = True

        # Add Kohler OEM certification
        caps.oem_certifications.add("Kohler")

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = []
        if tier != "Certified Installer":
            certifications_list.append(tier)
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Kohler dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications from tier
        tier = raw_dealer_data.get("tier", "Certified Installer")
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
            oem_source="Kohler",
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
        print(f"Kohler Dealer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  EXTRACTION SCRIPT INCOMPLETE - MANUAL DOM INSPECTION REQUIRED\n")
        print("⚠️  MANUAL WORKFLOW - Execute these steps:\n")

        print("1. Navigate to Kohler dealer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to inspect page structure:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. If cookie dialog appears, click Accept:")
        print('   mcp__playwright__browser_click({"element": "Accept/OK button", "ref": "[from snapshot]"})\n')

        print("4. Fill ZIP code input (find selector in snapshot):")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')

        print("5. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search/Find button", "ref": "[from snapshot]"})\n')

        print("6. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("7. Take another snapshot to see dealer cards:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("8. Inspect dealer card structure and update get_extraction_script()")
        print("   Look for:")
        print("   - Dealer name element (h2, h3, .dealer-name, .location-name)")
        print("   - Phone link (a[href^='tel:'])")
        print("   - Address element (.address, [class*='address'])")
        print("   - Distance element (.distance, [class*='miles'])")
        print("   - Website link (a[href^='http'])")
        print("   - Tier/certification badges (if any)\n")

        print("9. After updating extraction script, test it:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("10. Parse results:")
        print(f'   kohler_scraper.parse_results(results_json, "{zip_code}")\n')

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

        print("⚠️  WARNING: Kohler extraction script needs manual DOM inspection")
        print("⚠️  Results may be empty or incorrect until script is updated")

        # Build 6-step workflow for Kohler
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
            print(f"[RunPod] Scraping Kohler dealers for ZIP {zip_code}...")

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


# Register Kohler scraper with factory
ScraperFactory.register("Kohler", KohlerScraper)
ScraperFactory.register("kohler", KohlerScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    print("⚠️  Kohler scraper needs manual DOM inspection before use")
    print("⚠️  Run in PLAYWRIGHT mode to inspect site structure")
    scraper = KohlerScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco
