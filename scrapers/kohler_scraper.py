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

        VALIDATED: Tested on https://www.kohlerhomeenergy.rehlko.com/find-a-dealer
        ZIP 94102 (San Francisco) - 3 dealers extracted successfully

        Data Pattern:
        Kohler uses list-based dealer locator with dealer cards:
        - Dealer cards: ul > li (list items, found by searching for ul with phone links)
        - Name: First paragraph
        - Distance: Second paragraph (format: "51.5 miles")
        - Tier badges: Gold Dealer, Silver Dealer, Bronze Dealer, Titan Certified
        - Address: Paragraph (format: "150 NARDI LANE, Martinez, CA 94553")
        - Phone: a[href^="tel:"]
        - Website: a with text "Website"
        - Services: Paragraph with "Sales, Installation, and Service up to XkW"
        """

        # Read the validated extraction.js script
        extraction_script_path = os.path.join(
            os.path.dirname(__file__),
            "kohler",
            "extraction.js"
        )

        # If extraction.js exists, read it; otherwise use inline version
        if os.path.exists(extraction_script_path):
            with open(extraction_script_path, 'r') as f:
                # Extract just the function body (skip comments and function wrapper)
                lines = f.readlines()
                # Find the function definition and extract its body
                in_function = False
                function_lines = []
                for line in lines:
                    if 'function extractKohlerDealers()' in line:
                        in_function = True
                        continue
                    if in_function:
                        function_lines.append(line)

                # Join and wrap in IIFE
                return "() => {\n" + "".join(function_lines) + "\n}"

        # Fallback inline version (validated)
        return """
() => {
  console.log('[Kohler] Starting dealer extraction...');

  // Find the dealer results list (contains phone links)
  const allLists = Array.from(document.querySelectorAll('ul'));
  let dealerList = null;

  for (const list of allLists) {
    const phoneLinks = list.querySelectorAll('a[href^="tel:"]');
    if (phoneLinks.length > 0) {
      dealerList = list;
      break;
    }
  }

  if (!dealerList) {
    console.log('[Kohler] No dealer list found');
    return [];
  }

  const dealerCards = Array.from(dealerList.querySelectorAll('li'));
  console.log(`[Kohler] Found ${dealerCards.length} dealer cards`);

  const dealers = dealerCards.map((card, index) => {
    try {
      const paragraphs = Array.from(card.querySelectorAll('p'));
      const name = paragraphs[0] ? paragraphs[0].textContent.trim() : '';

      let distance = '';
      let distance_miles = 0;
      if (paragraphs[1]) {
        distance = paragraphs[1].textContent.trim();
        const milesMatch = distance.match(/([\\d.]+)\\s*miles?/i);
        if (milesMatch) {
          distance_miles = parseFloat(milesMatch[1]);
          distance = `${distance_miles} mi`;
        }
      }

      const cardText = card.textContent;
      let tier = 'Certified Installer';
      const certifications = [];

      if (cardText.includes('Gold Dealer')) {
        tier = 'Gold Dealer';
        certifications.push('Gold Dealer');
      } else if (cardText.includes('Silver Dealer')) {
        tier = 'Silver Dealer';
        certifications.push('Silver Dealer');
      } else if (cardText.includes('Bronze Dealer')) {
        tier = 'Bronze Dealer';
        certifications.push('Bronze Dealer');
      }

      if (cardText.includes('Titan Certified')) {
        certifications.push('Titan Certified');
        if (tier === 'Certified Installer') {
          tier = 'Titan Certified';
        }
      }

      if (certifications.length === 0) {
        certifications.push('Certified Installer');
      }

      const phoneLink = card.querySelector('a[href^="tel:"]');
      const phone = phoneLink ? phoneLink.textContent.trim() : '';

      const websiteLinks = Array.from(card.querySelectorAll('a[href^="http"]'));
      let website = '';
      let domain = '';

      for (const link of websiteLinks) {
        if (link.textContent.trim().toLowerCase() === 'website') {
          website = link.href;
          break;
        }
      }

      if (website) {
        try {
          const url = new URL(website);
          domain = url.hostname.replace('www.', '');
        } catch (e) {
          console.log(`[Kohler] Card ${index + 1}: Invalid website URL`);
        }
      }

      let street = '';
      let city = '';
      let state = '';
      let zip = '';
      let address_full = '';

      for (const p of paragraphs) {
        const text = p.textContent.trim();
        if (text.match(/\\d+\\s+[^,]+,\\s*[^,]+,\\s*[A-Z]{2}\\s+\\d{5}/)) {
          address_full = text;
          const addressMatch = text.match(/^(.+),\\s*([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
          if (addressMatch) {
            street = addressMatch[1].trim();
            city = addressMatch[2].trim();
            state = addressMatch[3].trim();
            zip = addressMatch[4].trim();
          }
          break;
        }
      }

      let services = '';
      for (const p of paragraphs) {
        const text = p.textContent.trim();
        if (text.includes('Sales') || text.includes('Installation') || text.includes('Service')) {
          services = text;
          break;
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
        rating: 0,
        review_count: 0,
        tier: tier,
        certifications: certifications,
        distance: distance,
        distance_miles: distance_miles,
        services: services,
        oem_source: 'Kohler'
      };
    } catch (e) {
      console.error(`[Kohler] Error extracting dealer card ${index + 1}:`, e);
      return null;
    }
  });

  const validDealers = dealers.filter(d => d && d.name && d.phone);
  console.log(`[Kohler] Successfully extracted ${validDealers.length} valid dealers`);
  return validDealers;
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
