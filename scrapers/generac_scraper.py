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

        # Updated extraction script (Nov 28, 2025) - matches current Generac DOM
        return """
        () => {
          function extractGeneracDealers() {
            console.log('[Generac] Starting dealer extraction v2...');

            // Find dealer list items - they are li elements containing phone links
            const listItems = Array.from(document.querySelectorAll('li'))
              .filter(li => {
                const phoneLink = li.querySelector('a[href^="tel:"]');
                // Exclude footer phone links and ensure it's in the results area
                return phoneLink && !li.closest('footer') && !li.closest('[class*="footer"]');
              });

            console.log(`[Generac] Found ${listItems.length} dealer list items`);

            const dealers = listItems.map((li) => {
              try {
                // Get all text content for parsing
                const fullText = li.textContent || '';

                // Extract dealer name - look for ALL CAPS text
                const allDivs = Array.from(li.querySelectorAll('div'));
                let dealerName = '';
                for (const div of allDivs) {
                  const text = div.textContent.trim();
                  // Dealer name is ALL CAPS, 3-100 chars, first substantial all-caps block
                  if (text && text.length >= 3 && text.length < 100 &&
                      text === text.toUpperCase() &&
                      !/^\\d/.test(text) &&  // Not starting with number
                      !/mi$/.test(text) &&   // Not a distance
                      !text.includes('(') && !text.includes('http') &&
                      !text.includes('STAR') && !text.includes('REVIEW')) {
                    dealerName = text;
                    break;
                  }
                }

                // Extract phone number
                const phoneLink = li.querySelector('a[href^="tel:"]');
                const phoneText = phoneLink ? phoneLink.textContent.trim() : '';

                // Extract rating and review count - pattern like "4.4" and "(54)"
                const ratingMatch = fullText.match(/(\\d+\\.\\d+)\\s*out of\\s*\\d+\\s*stars/i);
                const reviewMatch = fullText.match(/(\\d+)\\s*reviews?/i) || fullText.match(/\\((\\d+)\\)/);
                const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
                const reviewCount = reviewMatch ? parseInt(reviewMatch[1]) : 0;

                // Extract distance
                const distanceMatch = fullText.match(/(\\d+\\.?\\d*)\\s*mi/);
                const distance = distanceMatch ? distanceMatch[0] : '';
                const distanceMiles = distanceMatch ? parseFloat(distanceMatch[1]) : 0;

                // Detect tier from badge description text
                let tier = 'Select';  // Default tier
                const isPrestige = fullText.includes('Prestige dealers provide');
                const isPremier = fullText.includes('Premier Dealers demonstrate');
                const isElitePlus = fullText.includes('Elite Plus Dealers provide');
                const isElite = fullText.includes('Elite Dealers offer');

                if (isPrestige) tier = 'Prestige';
                else if (isPremier) tier = 'Premier';
                else if (isElitePlus) tier = 'Elite Plus';
                else if (isElite) tier = 'Elite';

                // PowerPro designation
                const isPowerProPremier = fullText.includes('PowerPro');

                // Extract address - find street, city, state, zip
                // Street typically has numbers and common suffixes
                const streetMatch = fullText.match(/(\\d+[^,\\n]*(?:st|street|dr|drive|rd|road|ave|avenue|ct|court|blvd|boulevard|ln|lane|way|pl|place|pkwy|parkway|hwy|highway|fwy|freeway)[^,\\n]*)/i);
                let street = streetMatch ? streetMatch[1].trim().toLowerCase() : '';

                // Clean up street - remove numbers that are actually other data
                street = street.replace(/^"/, '').replace(/"$/, '');

                // City, State, ZIP pattern
                const cityStateZipMatch = fullText.match(/([a-z][a-z\\s]+),\\s*([A-Z]{2})\\s+(\\d{5})/i);
                const city = cityStateZipMatch ? cityStateZipMatch[1].trim().toLowerCase() : '';
                const state = cityStateZipMatch ? cityStateZipMatch[2].toUpperCase() : '';
                const zip = cityStateZipMatch ? cityStateZipMatch[3] : '';

                // Extract website (exclude social media and google)
                const websiteLink = li.querySelector('a[href^="http"]:not([href*="google"]):not([href*="facebook"]):not([href*="twitter"]):not([href*="linkedin"])');
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

                // Build address_full
                const addressFull = street && city ? `${street}, ${city}, ${state} ${zip}`.trim() : '';

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
                  address_full: addressFull,
                  phone: phoneText,
                  website: website,
                  domain: domain,
                  distance: distance,
                  distance_miles: distanceMiles,
                  oem_source: 'Generac'
                };
              } catch (e) {
                console.log('[Generac] Error parsing dealer:', e);
                return null;
              }
            });

            const validDealers = dealers.filter(d => d && d.name && d.name.length > 2);
            console.log(`[Generac] Successfully extracted ${validDealers.length} dealers`);
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
        PLAYWRIGHT mode: Automated headless browser scraping.

        Launches a real Chromium browser, navigates to Generac dealer locator,
        enters ZIP code, and extracts dealer data using the validated extraction script.
        """
        import time
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                # Launch headless browser with stealth settings
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                )
                page = context.new_page()

                # Navigate to Generac dealer locator
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000)
                time.sleep(3)

                # Remove cookie banner (OneTrust) if present
                try:
                    page.evaluate("() => { const banner = document.querySelector('#onetrust-consent-sdk'); if (banner) banner.remove(); }")
                except Exception:
                    pass  # No banner

                time.sleep(1)

                # Find and fill ZIP input
                zip_input_selectors = [
                    'input[placeholder*="ZIP" i]',
                    'input[placeholder*="zip" i]',
                    'input[type="text"][placeholder*="location" i]',
                    'input[type="text"]',
                ]

                zip_filled = False
                for selector in zip_input_selectors:
                    try:
                        zip_input = page.locator(selector)
                        if zip_input.count() > 0 and zip_input.first.is_visible():
                            zip_input.first.fill(zip_code)
                            time.sleep(0.5)
                            zip_filled = True
                            break
                    except Exception:
                        continue

                if not zip_filled:
                    # Try to find any text input
                    try:
                        zip_input = page.locator('input[type="text"]').first
                        zip_input.fill(zip_code)
                        zip_filled = True
                    except Exception:
                        pass

                if not zip_filled:
                    browser.close()
                    return []

                # Click Search button
                search_selectors = [
                    'button:has-text("Search")',
                    'button:has-text("Find")',
                    'button[type="submit"]',
                    'input[type="submit"]',
                ]

                search_clicked = False
                for selector in search_selectors:
                    try:
                        search_btn = page.locator(selector)
                        if search_btn.count() > 0 and search_btn.first.is_visible():
                            search_btn.first.click()
                            search_clicked = True
                            break
                    except Exception:
                        continue

                if not search_clicked:
                    # Try pressing Enter as fallback
                    try:
                        page.keyboard.press('Enter')
                    except Exception:
                        pass

                # Wait for results to load
                time.sleep(4)

                # Execute extraction script
                raw_results = page.evaluate(self.get_extraction_script())

                browser.close()

                if not raw_results:
                    return []

                # Parse results into StandardizedDealer objects
                dealers = [self.parse_dealer_data(d, zip_code) for d in raw_results]

                return dealers

            except Exception as e:
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
