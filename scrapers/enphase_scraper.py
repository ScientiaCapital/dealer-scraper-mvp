"""
Enphase Certified Installer Scraper

Scrapes Enphase's certified installer network for microinverter + battery storage installations.
Enphase installers are strategic targets because they handle cutting-edge solar microinverter
systems and increasingly battery storage (IQ Battery, Encharge).

Target URL: https://enphase.com/installer-locator

Capabilities detected from Enphase certification:
- Microinverters (Enphase IQ series is core product)
- Solar installation (microinverters are solar components)
- Battery storage (Enphase IQ Battery / Encharge systems)
- Electrical work (required for microinverter + battery installation)
- EV Charger installation (some installers)
- Commercial installations (some installers)

Strategic importance for Coperniq:
- Enphase microinverter installers are tech-forward contractors (high-value customers)
- Microinverter + battery expertise = ideal Coperniq platform users
- Tier system (Platinum, Gold, Silver) indicates quality + volume
- Many also install generators (full energy resilience solution)
- O&M capability flag = strong signal for Coperniq's monitoring platform
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


class EnphaseScraper(BaseDealerScraper):
    """
    Scraper for Enphase certified installer network.

    Enphase is the world's leading microinverter manufacturer. Installers certified
    by Enphase represent high-quality solar contractors who can handle advanced
    microinverter systems + battery storage.

    Tier system: Platinum (highest), Gold (mid), Silver (base)
    """

    OEM_NAME = "Enphase"
    DEALER_LOCATOR_URL = "https://enphase.com/installer-locator"
    PRODUCT_LINES = ["IQ Microinverters", "IQ Battery", "Encharge", "Ensemble", "EV Charger"]

    # CSS Selectors (validated via Playwright MCP)
    SELECTORS = {
        "zip_input": "input[name='location']",
        "search_button": "button[type='submit']",  # "Find an installer" button
        "installer_cards": ".installer-info-box, div[data-installer-id]",
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
        JavaScript extraction script for Enphase certified installer data.

        VALIDATED: Tested on ZIP 94102 (27 dealers).

        Data Pattern:
        Enphase uses clean semantic HTML with proper CSS classes:
        - Company name: <h3 class="installer-info-box__title">
        - Address: <p class="installer-info-box__description"> (concatenated format)
        - Rating: data-google-reviews-rating attribute
        - Tier: <img alt="platinum|gold|silver">
        - Capabilities: Text includes "Solar", "Storage", "O&M", "EV Charger", "Commercial"

        Extraction Strategy:
        1. Find all installer boxes (.installer-info-box or [data-installer-id])
        2. Extract company name from .installer-info-box__title
        3. Parse concatenated address (street+city, STATE ZIP)
        4. Extract rating from data attribute
        5. Extract tier from img alt attribute
        6. Detect capabilities from text content
        7. Deduplicate by company name
        """

        # Read the validated extraction.js script
        extraction_script_path = os.path.join(
            os.path.dirname(__file__),
            "enphase",
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
                    if 'function extractEnphaseDealers()' in line:
                        in_function = True
                        continue
                    if in_function:
                        function_lines.append(line)

                # Join and wrap in IIFE
                return "() => {\n" + "".join(function_lines) + "\n}"

        # Fallback inline version (validated)
        return """
        () => {
          function extractEnphaseDealers() {
            console.log('[Enphase] Starting dealer extraction...');

            const installerBoxes = Array.from(
              document.querySelectorAll('.installer-info-box, div[data-installer-id]')
            );
            console.log(`[Enphase] Found ${installerBoxes.length} installer boxes`);

            const dealers = [];
            const seenNames = new Set();

            installerBoxes.forEach((box, index) => {
              const nameEl = box.querySelector('.installer-info-box__title');
              const name = nameEl ? nameEl.textContent.trim() : '';

              if (!name || seenNames.has(name)) return;
              seenNames.add(name);

              const addressEl = box.querySelector('.installer-info-box__description');
              let addressText = addressEl ? addressEl.textContent.trim() : '';

              // Parse: "290 Rickenbacker CircleLivermore, CA 94551"
              let street = '', city = '', state = '', zip = '';
              const addressMatch = addressText.match(/^(.+?)([A-Z][a-z\\s]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
              if (addressMatch) {
                street = addressMatch[1].trim();
                city = addressMatch[2].trim();
                state = addressMatch[3];
                zip = addressMatch[4];
              }

              const rating = parseFloat(box.getAttribute('data-google-reviews-rating')) || 0.0;
              const tierImg = box.querySelector('img[alt]');
              let tier = '';
              if (tierImg) {
                const tierAlt = tierImg.alt.toLowerCase();
                tier = tierAlt.charAt(0).toUpperCase() + tierAlt.slice(1);
              }

              const fullText = box.textContent;
              const capabilities = [];
              if (fullText.includes('Solar')) capabilities.push('Solar');
              if (fullText.includes('Storage')) capabilities.push('Storage');
              if (fullText.includes('Ops & Maintenance')) capabilities.push('O&M');
              if (fullText.includes('EV Charger')) capabilities.push('EV Charger');
              if (fullText.includes('Commercial')) capabilities.push('Commercial');

              dealers.push({
                name, street, city, state, zip,
                address_full: addressText,
                tier: tier,
                rating: rating,
                capabilities: capabilities,
                oem_source: 'Enphase'
              });
            });

            console.log(`[Enphase] Successfully extracted ${dealers.length} unique dealers`);
            return dealers;
          }

          return extractEnphaseDealers();
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Enphase certified installer data.

        Enphase certifications indicate:
        - All installers: has_microinverters + has_solar + has_electrical
        - "Storage" capability: has_battery
        - "O&M" capability: has_ops_maintenance (Coperniq monitoring platform fit)
        - "EV Charger" capability: has_electrical (already covered)
        - "Commercial" capability: is_commercial
        - Tier (Platinum/Gold/Silver) = quality + volume signal
        """
        caps = DealerCapabilities()

        # All Enphase installers have these
        caps.has_microinverters = True  # Enphase is THE microinverter OEM
        caps.has_solar = True            # Microinverters are solar components
        caps.has_electrical = True       # Required for microinverter installation

        # Parse capabilities from raw data
        capabilities = raw_dealer_data.get("capabilities", [])

        if "Storage" in capabilities:
            caps.has_battery = True
            caps.battery_oems.add("Enphase")

        if "O&M" in capabilities:
            caps.has_ops_maintenance = True  # HIGH VALUE for Coperniq

        if "Commercial" in capabilities:
            caps.is_commercial = True

        # Default to residential (all installers do residential)
        caps.is_residential = True

        # Add Enphase OEM certification
        caps.oem_certifications.add("Enphase")
        caps.inverter_oems.add("Enphase")

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Enphase installer data to StandardizedDealer format.
        """
        # Extract domain from website (Enphase doesn't provide website in initial results)
        # We'll leave domain blank for now, can enrich later via Apollo/Clay
        domain = ""
        website = ""

        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Get tier (Platinum, Gold, Silver)
        tier = raw_dealer_data.get("tier", "")

        # Get certifications
        certifications = ["Enphase Certified Installer"]
        if tier:
            certifications.append(f"{tier} Installer")

        # Add capability-based certifications
        raw_capabilities = raw_dealer_data.get("capabilities", [])
        if "Storage" in raw_capabilities:
            certifications.append("Enphase Storage Certified")
        if "O&M" in raw_capabilities:
            certifications.append("Operations & Maintenance")
        if "Commercial" in raw_capabilities:
            certifications.append("Commercial Installer")

        # Check for O&M capability (high value for Coperniq)
        has_om = "O&M" in raw_capabilities

        # Check for resimercial (both residential + commercial)
        is_resimercial = "Commercial" in raw_capabilities  # All do residential by default

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone="",  # Enphase doesn't provide phone in initial results
            domain=domain,
            website=website,
            street=raw_dealer_data.get("street", ""),
            city=raw_dealer_data.get("city", ""),
            state=raw_dealer_data.get("state", ""),
            zip=raw_dealer_data.get("zip", ""),
            address_full=raw_dealer_data.get("address_full", ""),
            rating=raw_dealer_data.get("rating", 0.0),
            review_count=0,  # Enphase doesn't show review count
            tier=tier,
            certifications=certifications,
            distance="",
            distance_miles=0.0,
            capabilities=capabilities,
            oem_source="Enphase",
            scraped_from_zip=zip_code,
            has_ops_maintenance=has_om,
            is_resimercial=is_resimercial
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*70}")
        print(f"Enphase Certified Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*70}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Enphase installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Wait for page to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("3. Accept cookie consent (if present):")
        print('   mcp__playwright__browser_click({')
        print('       "element": "Accept cookies button",')
        print('       "ref": "[from snapshot - look for Accept/OK button]"')
        print('   })\n')

        print("4. Enter ZIP code:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}"')
        print(f'   }})\n')

        print("5. Click 'Find an installer' button:")
        print('   mcp__playwright__browser_click({')
        print('       "element": "Find an installer button",')
        print('       "ref": "[from snapshot]"')
        print('   })\n')

        print("6. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("7. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("8. Process results with:")
        print(f'   enphase_scraper.parse_results(results_json, "{zip_code}")\n')

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

        # Build workflow for Enphase
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 3000},
            # Accept cookies if present (may not be needed for all visitors)
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
        raise NotImplementedError("Patchright mode not yet implemented for Enphase")

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Enphase scraper with factory
ScraperFactory.register("Enphase", EnphaseScraper)
ScraperFactory.register("enphase", EnphaseScraper)
ScraperFactory.register("Enphase Energy", EnphaseScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = EnphaseScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = EnphaseScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/enphase_installers_sf.json")
