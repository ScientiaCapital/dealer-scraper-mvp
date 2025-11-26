"""
Generac Authorized Dealer Scraper

Scrapes Generac's authorized dealer network for backup generator installations.
Generac dealers are strategic targets because they handle premium residential + commercial
backup power systems and increasingly battery storage (PWRcell).

Target URL: https://www.generac.com/dealer-locator/

Capabilities detected from Generac certification:
- Generators (Generac is the leading residential/commercial backup generator OEM)
- Electrical work (required for generator installation + transfer switch)
- Battery storage (Generac PWRcell systems, increasingly popular)
- HVAC (many Generac dealers also do HVAC - common contractor profile)

Strategic importance for Coperniq:
- Generac dealers represent established contractors with electrical + generator expertise
- Tier system (Premier > Elite Plus > Elite > Standard) indicates quality + volume
- PowerPro Premier designation = highest-tier installers (best prospects)
- Many also install solar + batteries (multi-brand contractors)
- Generator + battery combo = full energy resilience solution (Coperniq's value prop)
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


class GeneracScraper(BaseDealerScraper):
    """
    Scraper for Generac authorized dealer network.

    Generac is the world's leading residential/commercial backup generator manufacturer.
    Dealers authorized by Generac represent established contractors who can handle
    complex electrical + generator installations.

    Tier system: Premier (highest), Elite Plus, Elite, Standard
    Special designation: PowerPro Premier (top-tier installers)
    """

    OEM_NAME = "Generac"
    DEALER_LOCATOR_URL = "https://www.generac.com/dealer-locator/"
    PRODUCT_LINES = ["Home Standby Generators", "PWRcell Battery Storage", "Transfer Switches", "Portable Generators"]

    # CSS Selectors (validated via Playwright automation)
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept Cookies')",
        "zip_input": "input[placeholder*='ZIP' i]",
        "search_button": "button:has-text('Search')",
        "dealer_cards": "a[href^='tel:']",  # Phone links identify dealer cards
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
        JavaScript extraction script for Generac authorized dealer data.

        VALIDATED: Tested on ZIP 53202 (59 dealers), 60601 (59 dealers), 55401 (28 dealers).

        Data Pattern:
        Generac uses complex nested HTML with phone links as entry points:
        - Dealer cards identified by phone number links
        - Dealer name is ALL CAPS text
        - Rating pattern: "4.3(6)" or "5.0(24)"
        - Tier badges: "Premier Dealers demonstrate...", "Elite Plus", etc.
        - Distance: .ms-auto.text-end.text-nowrap element

        Extraction Strategy:
        1. Find all phone links EXCLUDING footer (critical!)
        2. Traverse up DOM to find dealer card container (identified by distance element)
        3. Extract dealer name (ALL CAPS text)
        4. Parse rating/review count from "4.3(6)" pattern
        5. Detect tier from badge text (Premier/Elite Plus/Elite/Standard)
        6. Extract address using regex (street suffix pattern)
        7. Parse city, state, ZIP from remaining text
        8. Extract website/domain (excluding social media links)
        9. Extract distance from text-end element
        """

        # Read the validated extraction.js script
        extraction_script_path = os.path.join(
            os.path.dirname(__file__),
            "generac",
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
                    if 'function extractGeneracDealers()' in line:
                        in_function = True
                        continue
                    if in_function:
                        function_lines.append(line)

                # Join and wrap in IIFE
                return "() => {\n" + "".join(function_lines) + "\n}"

        # Fallback inline version (validated)
        return """
        () => {
          function extractGeneracDealers() {
            console.log('[Generac] Starting dealer extraction...');

            const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'))
              .filter(link => !link.closest('footer') && !link.closest('[class*="footer"]'));

            console.log(`[Generac] Found ${phoneLinks.length} phone links (excluding footer)`);

            const dealers = phoneLinks.map((phoneLink, index) => {
              let container = phoneLink;
              for (let i = 0; i < 10; i++) {
                container = container.parentElement;
                if (!container) break;
                const hasDistance = container.querySelector('.ms-auto.text-end.text-nowrap');
                if (hasDistance) break;
              }

              if (!container) return null;

              const allDivs = Array.from(container.querySelectorAll('div'));
              let dealerName = '';
              for (const div of allDivs) {
                const text = div.textContent.trim();
                if (text && text.length > 5 && text.length < 100 &&
                    !text.includes('(') && !text.includes('http') &&
                    !text.includes('mi') && text === text.toUpperCase()) {
                  dealerName = text;
                  break;
                }
              }

              const fullText = container.textContent;
              const phoneText = phoneLink.textContent.trim();
              const beforePhone = fullText.substring(0, fullText.indexOf(phoneText));

              const ratingMatch = fullText.match(/(\\d+\\.\\d+)\\s*\\((\\d+)\\)/);
              const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
              const reviewCount = ratingMatch ? parseInt(ratingMatch[2]) : 0;

              const isPremier = fullText.includes('Premier Dealers demonstrate');
              const isElitePlus = fullText.includes('Elite Plus');
              const isElite = fullText.includes('Elite Dealers offer');

              let tier = 'Standard';
              if (isPremier) tier = 'Premier';
              else if (isElitePlus) tier = 'Elite Plus';
              else if (isElite) tier = 'Elite';

              const isPowerProPremier = fullText.includes('PowerPro') || fullText.includes('Premier');

              const streetMatch = beforePhone.match(/(\\d+\\s+[nsew]?\\d*\\s*[^\\n,]*(?:st|street|dr|drive|rd|road|ave|avenue|ct|court|blvd|ln|way|pl)\\.?)/i);
              let street = streetMatch ? streetMatch[1].trim() : '';
              street = street.replace(/^.*?out of \\d+ stars\\.\\s*\\d*\\s*reviews?\\s*/i, '');
              street = street.replace(/^\\d+\\.\\d+\\s*\\(\\d+\\)/, '');
              street = street.replace(/^\\d+\\.\\d+\\s*mi/, '');

              const afterStreet = street ? beforePhone.substring(beforePhone.lastIndexOf(street) + street.length) : beforePhone;
              const cityStateZip = afterStreet.match(/([a-z\\s]+),?\\s*([A-Z]{2})\\s+(\\d{5})/i);

              const city = cityStateZip ? cityStateZip[1].trim() : '';
              const state = cityStateZip ? cityStateZip[2] : '';
              const zip = cityStateZip ? cityStateZip[3] : '';

              const websiteLink = container.querySelector('a[href^="http"]:not([href*="google"]):not([href*="facebook"])');
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

              const distanceEl = container.querySelector('.ms-auto.text-end.text-nowrap');
              const distance = distanceEl?.textContent?.trim() || '';
              const distanceMiles = parseFloat(distance) || 0;

              return {
                name: dealerName,
                rating: rating,
                review_count: reviewCount,
                tier: tier,
                is_power_pro_premier: isPowerProPremier,
                street: street,
                city: city,
                state: state,
                zip: zip,
                address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
                phone: phoneText,
                website: website,
                domain: domain,
                distance: distance,
                distance_miles: distanceMiles,
                oem_source: 'Generac'
              };
            });

            const validDealers = dealers.filter(d => d && d.name);
            console.log(`[Generac] Successfully extracted ${validDealers.length} unique dealers`);
            return validDealers;
          }

          return extractGeneracDealers();
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Generac authorized dealer data.

        Generac certifications indicate:
        - All dealers: has_generator + has_electrical (core requirements)
        - Premier/Elite tiers: likely has_battery (PWRcell systems)
        - Many dealers also have: has_hvac (common contractor profile)
        - PowerPro Premier: highest-tier, likely multi-trade contractors
        """
        caps = DealerCapabilities()

        # All Generac dealers have these
        caps.has_generator = True     # Generac is THE generator OEM
        caps.has_electrical = True    # Required for generator + transfer switch installation

        # Tier-based capabilities
        tier = raw_dealer_data.get("tier", "Standard")

        if tier in ["Premier", "Elite Plus", "Elite"]:
            caps.has_battery = True   # Higher-tier dealers likely install PWRcell
            caps.battery_oems.add("Generac")

        # PowerPro Premier designation = highest-tier, likely multi-trade
        is_power_pro_premier = raw_dealer_data.get("is_power_pro_premier", False)
        if is_power_pro_premier:
            caps.has_hvac = True      # PowerPro Premier dealers often do HVAC
            caps.has_battery = True   # PowerPro Premier dealers do PWRcell
            caps.battery_oems.add("Generac")

        # Default to both residential + commercial (generators used in both markets)
        caps.is_residential = True
        caps.is_commercial = True

        # Add Generac OEM certification
        caps.oem_certifications.add("Generac")

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Generac dealer data to StandardizedDealer format.
        """
        # Extract domain from website
        website = raw_dealer_data.get("website", "")
        domain = raw_dealer_data.get("domain", "")

        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Get tier (Premier, Elite Plus, Elite, Standard)
        tier = raw_dealer_data.get("tier", "Standard")

        # Get certifications
        certifications = ["Generac Authorized Dealer"]
        if tier != "Standard":
            certifications.append(f"{tier} Dealer")

        # Add PowerPro Premier designation
        is_power_pro_premier = raw_dealer_data.get("is_power_pro_premier", False)
        if is_power_pro_premier:
            certifications.append("PowerPro Premier")

        # Check for resimercial (all Generac dealers serve both markets)
        is_resimercial = True

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=domain,
            website=website,
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
            oem_source="Generac",
            scraped_from_zip=zip_code,
            has_ops_maintenance=False,  # Can't determine from Generac data
            is_resimercial=is_resimercial
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*70}")
        print(f"Generac Authorized Dealer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*70}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Generac dealer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Wait for page to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("3. Remove cookie banner (more reliable than clicking):")
        print('   mcp__playwright__browser_evaluate({')
        print('       "function": "() => { const banner = document.querySelector(\'#onetrust-consent-sdk\'); if (banner) banner.remove(); }"')
        print('   })\n')

        print("4. Wait for ZIP input to be visible:")
        print('   mcp__playwright__browser_wait_for({"time": 2})\n')

        print("5. Enter ZIP code:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}"')
        print(f'   }})\n')

        print("6. Click 'Search' button:")
        print('   mcp__playwright__browser_click({')
        print('       "element": "Search button",')
        print('       "ref": "[from snapshot]"')
        print('   })\n')

        print("7. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("8. Extract dealer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("9. Process results with:")
        print(f'   generac_scraper.parse_results(results_json, "{zip_code}")\n')

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

        # Build workflow for Generac
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 3000},
            # Remove cookie banner
            {"action": "evaluate", "script": "() => { const banner = document.querySelector('#onetrust-consent-sdk'); if (banner) banner.remove(); }"},
            {"action": "wait", "timeout": 2000},
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
        raise NotImplementedError("Patchright mode not yet implemented for Generac")

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Generac scraper with factory
ScraperFactory.register("Generac", GeneracScraper)
ScraperFactory.register("generac", GeneracScraper)
ScraperFactory.register("Generac Power Systems", GeneracScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = GeneracScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("53202")  # Milwaukee

    # RUNPOD mode (automated)
    # scraper = GeneracScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("53202")
    # scraper.save_json("output/generac_dealers_milwaukee.json")
