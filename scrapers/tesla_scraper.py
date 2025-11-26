"""
Tesla Powerwall Certified Installer Scraper

Scrapes Tesla's Powerwall certified installer network for battery + solar installations.
Tesla Powerwall installers are strategic targets because they handle premium battery storage
systems and often manage complex residential + commercial energy projects.

Target URL: https://www.tesla.com/support/certified-installers
(Updated Nov 2025 - old URL /certified-installers-powerwall redirects to new URL)

**BOT DETECTION**: Tesla uses Cloudflare/bot protection. Requires Playwright with:
- Stealth user agent
- JavaScript execution
- Realistic browsing patterns

Capabilities detected from Tesla certification:
- Battery installation (Powerwall is their core product)
- Solar installation (many installers are Tesla Energy Certified for Solar Roof + panels)
- Electrical work (required for Powerwall installation)
- Premium residential and increasingly commercial installations

Strategic importance for Coperniq:
- Tesla Powerwall installers are premium contractors (high-value customers)
- Battery + solar expertise = ideal Coperniq platform users
- Many also install generators (full energy resilience solution)
- Premier Installer tier indicates high volume + quality (best prospects)
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


class TeslaScraper(BaseDealerScraper):
    """
    Scraper for Tesla Powerwall certified installer network.

    Tesla Powerwall is the premium residential/commercial battery storage system.
    Installers certified by Tesla represent high-quality contractors who can
    handle complex energy storage + solar installations.

    All Tesla installers are "Premier Installers" - representing the highest tier.
    """

    OEM_NAME = "Tesla"
    DEALER_LOCATOR_URL = "https://www.tesla.com/support/certified-installers"
    PRODUCT_LINES = ["Powerwall", "Solar Roof", "Solar Panels", "Wall Connector", "Powershare"]

    # NOTE: Tesla requires Playwright with stealth mode due to bot detection (403 without it)

    # CSS Selectors (validated via Playwright MCP)
    SELECTORS = {
        "zip_input": "input[placeholder*='Zip code']",
        "search_button": "button[type='submit']",  # Not needed - autocomplete handles search
        "installer_cards": "div",  # Tesla uses generic div with "Premier Installer" text
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
        JavaScript extraction script for Tesla Powerwall installer data.

        VALIDATED: Tested on ZIP 94102 (14 dealers) and ZIP 77002 (8 dealers visible).

        Data Pattern:
        Tesla concatenates all dealer info without spaces:
        "Premier InstallerLuminalt Energy Corporation4156414000https://luminalt.com/powerwall@luminalt.com"

        Extraction Strategy:
        1. Find all <div> elements containing exactly 1 "Premier Installer" text
        2. Extract phone (10 digits) as anchor point
        3. Extract email (standard pattern with @)
        4. Extract website (https:// OR www.domain patterns)
        5. Extract name (everything before phone, cleaned)
        6. Deduplicate by phone number
        """

        # Read the validated extraction.js script
        extraction_script_path = os.path.join(
            os.path.dirname(__file__),
            "tesla",
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
                    if 'function extractTeslaDealers()' in line:
                        in_function = True
                        continue
                    if in_function:
                        function_lines.append(line)

                # Join and wrap in IIFE
                return "() => {\n" + "".join(function_lines) + "\n}"

        # Fallback inline version (validated)
        return """
        () => {
          function extractTeslaDealers() {
            console.log('[Tesla] Starting dealer extraction...');

            // Find all <div> elements that contain exactly one "Premier Installer" badge
            const allDivs = Array.from(document.querySelectorAll('div'));
            const dealerCards = allDivs.filter(div => {
              const text = div.textContent;
              const badgeCount = (text.match(/Premier Installer/g) || []).length;
              return badgeCount === 1 && text.length > 20 && text.length < 500;
            });

            console.log(`[Tesla] Found ${dealerCards.length} potential dealer cards`);

            const dealers = [];
            const seenPhones = new Set();

            dealerCards.forEach((card, index) => {
              let text = card.textContent.trim();
              text = text.replace(/Premier Installer/g, '').trim();

              // Extract phone number (10 digits) - ANCHOR POINT
              const phoneMatch = text.match(/(\\d{10})/);
              if (!phoneMatch) {
                console.log(`[Tesla] Card ${index + 1}: No phone found, skipping`);
                return;
              }
              const phone = phoneMatch[1];

              // Deduplicate by phone
              if (seenPhones.has(phone)) {
                console.log(`[Tesla] Card ${index + 1}: Duplicate phone ${phone}, skipping`);
                return;
              }
              seenPhones.add(phone);

              // Extract email (standard pattern with @)
              const emailMatch = text.match(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/);
              const email = emailMatch ? emailMatch[1] : '';

              // Extract website - handle both https:// and www. patterns
              let website = '';
              if (email) {
                const emailPrefix = email.split('@')[0];
                const httpsPattern = new RegExp('(https?://[^@]+?)' + emailPrefix + '@');
                const httpsMatch = text.match(httpsPattern);

                if (httpsMatch) {
                  website = httpsMatch[1];
                } else {
                  const wwwPattern = new RegExp('(www\\\\.[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,})' + emailPrefix + '@');
                  const wwwMatch = text.match(wwwPattern);
                  if (wwwMatch) {
                    website = 'https://' + wwwMatch[1];
                  } else {
                    const emailDomain = email.split('@')[1];
                    website = 'https://' + emailDomain;
                  }
                }
              } else {
                const match = text.match(/(https?:\\/\\/[^\\d\\s]+?)(?=\\d{10}|$)/);
                if (match) website = match[1];
              }

              website = website.replace(/\\/$/, '').trim();

              // Extract name (everything before phone number)
              let name = text.substring(0, text.indexOf(phone)).trim();
              if (website) {
                name = name.replace(website, '').trim();
                name = name.replace(website.replace('https://', ''), '').trim();
              }
              if (email) name = name.replace(email, '').trim();
              name = name.replace(/https?:\\/\\/[^\\s]+/g, '').trim();
              name = name.replace(/www\\.[^\\s]+/g, '').trim();

              // Only add if we have at least name and phone
              if (name && phone) {
                dealers.push({
                  name: name,
                  phone: phone,
                  website: website,
                  email: email,
                  tier: 'Premier Installer',
                  oem_source: 'Tesla'
                });
              }
            });

            console.log(`[Tesla] Successfully extracted ${dealers.length} unique dealers`);
            return dealers;
          }

          return extractTeslaDealers();
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Tesla Powerwall installer data.

        Tesla Powerwall certifications indicate:
        - All installers: has_battery + has_solar + has_electrical
        - Premier Installer tier = high-volume contractor
        - Many also install Solar Roof/Panels (has_solar + has_roofing)
        - Battery storage expertise = likely commercial capability
        """
        caps = DealerCapabilities()

        # All Tesla Powerwall installers have these
        caps.has_battery = True  # Powerwall is core product
        caps.has_solar = True    # Many also do Tesla Solar
        caps.has_electrical = True
        caps.has_roofing = True  # Solar Roof requires roofing work

        # Tesla installers often do both residential and commercial
        caps.is_residential = True
        caps.is_commercial = True  # Powerwall is used in both markets

        # Add Tesla OEM certification
        caps.oem_certifications.add("Tesla")
        caps.battery_oems.add("Tesla")

        # If they have solar capability (most do)
        if caps.has_solar:
            caps.inverter_oems.add("Tesla")  # Tesla Solar uses integrated inverters

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Tesla installer data to StandardizedDealer format.
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

        # If no domain but have email, extract from email
        if not domain:
            email = raw_dealer_data.get("email", "")
            if email and "@" in email:
                domain = email.split("@")[1]
                website = f"https://{domain}"

        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # All Tesla installers are Premier tier
        tier = raw_dealer_data.get("tier", "Premier Installer")

        # Get certifications
        certifications = ["Tesla Powerwall Certified", "Premier Installer"]

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=domain,
            website=website,
            street="",  # Tesla doesn't provide street address in initial results
            city="",
            state="",
            zip="",
            address_full="",
            rating=0.0,  # Tesla doesn't show ratings in results
            review_count=0,
            tier=tier,
            certifications=certifications,
            distance="",
            distance_miles=0.0,
            capabilities=capabilities,
            oem_source="Tesla",
            scraped_from_zip=zip_code,
            has_ops_maintenance=False,  # Can't determine from Tesla data
            is_resimercial=True  # Tesla Powerwall used in both markets
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*70}")
        print(f"Tesla Powerwall Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*70}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Tesla Powerwall installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Wait for page to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("3. Enter ZIP code:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}"')
        print(f'   }})\n')

        print("4. Press Enter to trigger autocomplete:")
        print('   mcp__playwright__browser_press_key({"key": "Enter"})\n')

        print("5. Wait for autocomplete and results:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("6. Scroll to load all results (Tesla uses lazy loading):")
        print('   mcp__playwright__browser_evaluate({"function": "() => window.scrollTo(0, document.body.scrollHeight)"})\n')

        print("7. Wait for lazy-loaded results:")
        print('   mcp__playwright__browser_wait_for({"time": 2})\n')

        print("8. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("9. Process results with:")
        print(f'   tesla_scraper.parse_results(results_json, "{zip_code}")\n')

        print(f"{'='*70}\n")

        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build workflow for Tesla
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 3000},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "keyboard", "key": "Enter"},
            {"action": "wait", "timeout": 3000},
            # Scroll to trigger lazy loading
            {"action": "evaluate", "script": "() => window.scrollTo(0, document.body.scrollHeight)"},
            {"action": "wait", "timeout": 2000},
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
        PATCHRIGHT mode: Not implemented yet.
        """
        raise NotImplementedError("Patchright mode not yet implemented for Tesla")

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Tesla scraper with factory
ScraperFactory.register("Tesla", TeslaScraper)
ScraperFactory.register("tesla", TeslaScraper)
ScraperFactory.register("Tesla Powerwall", TeslaScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = TeslaScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = TeslaScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/tesla_installers_sf.json")
