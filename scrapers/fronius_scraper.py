"""
Fronius Certified Installer Scraper

Scrapes Fronius's certified installer network for string inverter and energy storage installations.
Fronius is an Austrian manufacturer specializing in string inverters, battery storage, and hybrid solutions.

Target URL: https://www.fronius.com/en-us/usa/solar-energy/home-owners/contact/find-installers

Capabilities detected from Fronius certification:
- Solar installation (string inverters are their core product)
- Battery installation (GEN24 Plus hybrid inverters with integrated battery management)
- Electrical work (required for inverter installation)
- Commercial and residential installations
- Energy storage systems (Fronius BYD Battery-Box, Fronius Solar Battery)

Strategic importance for Coperniq:
- Fronius is a premium European brand with strong commercial presence
- GEN24 Plus hybrid inverters combine string inverter + battery management (multi-brand opportunity)
- Many installers carry BOTH Fronius (commercial) AND Enphase/SolarEdge (residential)
- Strong presence in "resimercial" market (residential + commercial contractors)
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


class FroniusScraper(BaseDealerScraper):
    """
    Scraper for Fronius certified installer network.

    Fronius Solutions Partners are certified installers with expertise in:
    - String inverter installation (Fronius SnapINverter, Primo, Symo)
    - Hybrid inverter systems (GEN24 Plus with battery integration)
    - Energy storage solutions (BYD Battery-Box, Solar Battery)
    - Commercial solar installations

    Partner Tiers:
    - Fronius Solutions Partner (standard certification)
    - Fronius Solutions Partner Plus (premium tier with advanced training)
    """

    OEM_NAME = "Fronius"
    DEALER_LOCATOR_URL = "https://www.fronius.com/en-us/usa/solar-energy/home-owners/contact/find-installers"
    PRODUCT_LINES = ["String Inverters", "Hybrid Inverters", "Battery Storage", "Energy Storage", "Commercial"]

    # CSS Selectors (to be verified after site inspection)
    SELECTORS = {
        "search_input": "input[type='text']",           # Address/city search input
        "search_button": "button[type='submit']",       # Search button
        "partner_cards": ".partner-item",               # Partner result cards
        "geolocation_btn": "button.geolocation",        # Use my location button
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
        JavaScript extraction script for Fronius installer data.

        VALIDATED: Tested on https://www.fronius.com/en-us/usa/solar-energy/home-owners/contact/find-installers
        ZIP 94102 (San Francisco) - List view with installer buttons

        Data Pattern:
        Button text has NO SPACES between components:
        "Fronius Solutions PartnerROAM Solar, Inc.20.93 mi40 La Barthe Lane, San ..."
        """

        return """
        () => {
            console.log('[Fronius] Starting extraction from list view...');
            const dealers = [];

            // Find all buttons containing "Fronius Solutions Partner"
            const allButtons = Array.from(document.querySelectorAll('button'));
            const installerButtons = allButtons.filter(btn => {
                const text = btn.textContent || '';
                // Must have company name (letters) followed by distance (numbers + mi/km)
                return text.includes('Fronius Solutions Partner') && 
                       /\\d+\\.\\d+\\s*(mi|km)/.test(text);
            });

            console.log(`[Fronius] Found ${installerButtons.length} installer buttons`);

            installerButtons.forEach(button => {
                try {
                    const buttonText = button.textContent.trim();

                    // Split by "Fronius Solutions Partner" or "Fronius Solutions Partner Plus"
                    let afterTier = '';
                    if (buttonText.includes('Fronius Solutions Partner Plus')) {
                        afterTier = buttonText.split('Fronius Solutions Partner Plus')[1];
                    } else {
                        afterTier = buttonText.split('Fronius Solutions Partner')[1];
                    }

                    if (!afterTier) return;

                    // Extract distance pattern (e.g., "20.93 mi" or "20.93mi")
                    const distanceMatch = afterTier.match(/([\\d.]+)\\s*(mi|km)/);
                    if (!distanceMatch) return;

                    const distance = `${distanceMatch[1]} ${distanceMatch[2]}`;
                    let distance_miles = parseFloat(distanceMatch[1]);
                    if (distanceMatch[2] === 'km') {
                        distance_miles = distance_miles * 0.621371;
                    }

                    // Find where the distance starts in the text
                    const distanceIndex = afterTier.indexOf(distanceMatch[0]);

                    // Company name is everything before the distance (no space separator!)
                    const name = afterTier.substring(0, distanceIndex).trim();
                    if (!name || name.length < 2) return;

                    // Address is everything after the distance
                    const afterDistance = afterTier.substring(distanceIndex + distanceMatch[0].length).trim();
                    const address_full = afterDistance.replace(/\\.\\.\\.$/,  '').trim();

                    // Try to parse address components
                    let street = '', city = '', state = '', zip = '';
                    const addressParts = address_full.split(',').map(p => p.trim());
                    if (addressParts.length >= 1) {
                        street = addressParts[0];
                    }
                    if (addressParts.length >= 2) {
                        city = addressParts[1].replace(/\\.\\.\\.$/,  '').trim();
                    }

                    // Determine tier
                    const tier = buttonText.includes('Plus') ? 'Fronius Solutions Partner Plus' : 'Fronius Solutions Partner';

                    dealers.push({
                        name: name,
                        phone: '',  // Not available in list view
                        email: '',
                        website: '',
                        street: street,
                        city: city,
                        state: state,
                        zip: zip,
                        address_full: address_full,
                        certifications: ['Fronius Certified'],
                        capabilities: ['Solar', 'String Inverters'],
                        rating: 0,
                        review_count: 0,
                        tier: tier,
                        distance: distance,
                        distance_miles: distance_miles,
                        has_commercial: name.toLowerCase().includes('commercial'),
                        has_ops_maintenance: name.toLowerCase().includes('service') || name.toLowerCase().includes('maintenance'),
                        is_resimercial: false
                    });

                } catch (error) {
                    console.error('[Fronius] Error parsing installer:', error);
                }
            });

            console.log(`[Fronius] Extracted ${dealers.length} installers`);
            return dealers;
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Fronius installer data.

        Fronius certifications indicate:
        - All installers: has_solar + has_inverters + has_electrical
        - String inverter expertise (Fronius core product)
        - Battery certified = GEN24 Plus hybrid systems or BYD Battery-Box
        - Partner Plus tier often = commercial capability
        """
        caps = DealerCapabilities()

        # All Fronius installers have these
        caps.has_solar = True
        caps.has_inverters = True  # String inverters (not micro)
        caps.has_electrical = True
        caps.has_roofing = True    # Solar requires roof work

        # Check capabilities list
        capabilities = raw_dealer_data.get("capabilities", [])

        # Battery storage (GEN24 Plus, BYD Battery-Box)
        if "Battery Storage" in capabilities or "Hybrid Systems" in capabilities:
            caps.has_battery = True

        # Commercial capability
        if "Commercial" in capabilities or raw_dealer_data.get("has_commercial"):
            caps.is_commercial = True

        # Check for resimercial (both markets)
        if raw_dealer_data.get("is_resimercial"):
            caps.is_residential = True
            caps.is_commercial = True
        else:
            # Default to residential if not explicitly commercial
            caps.is_residential = True

        # Add Fronius OEM certification
        caps.oem_certifications.add("Fronius")
        caps.inverter_oems.add("Fronius")

        # If battery certified, add to battery OEMs
        if caps.has_battery:
            caps.battery_oems.add("Fronius")

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Fronius installer data to StandardizedDealer format.
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

        # Set O&M and resimercial flags (for GTM targeting)
        has_ops_maintenance = raw_dealer_data.get("has_ops_maintenance", False)
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
            tier=raw_dealer_data.get("tier", "Fronius Solutions Partner"),
            certifications=raw_dealer_data.get("certifications", []),
            distance=distance_str,
            distance_miles=distance_miles,
            capabilities=capabilities,
            oem_source="Fronius",
            scraped_from_zip=zip_code,
            has_ops_maintenance=has_ops_maintenance,
            is_resimercial=is_resimercial
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated browser workflow for Fronius installer search.
        
        Fronius uses address/city input (not strict ZIP code field).
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

                # Navigate to dealer locator
                print(f"  → Navigating to Fronius installer locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(3)

                # Handle cookie consent dialog if it appears
                print(f"  → Checking for cookie consent dialog...")
                try:
                    cookie_selectors = [
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        'button:has-text("OK")',
                        '#onetrust-accept-btn-handler',
                        '.onetrust-close-btn-handler',
                        'button[class*="cookie"]',
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

                # Fill search input (Fronius uses address/city input)
                print(f"  → Filling search input: {zip_code}")
                search_input_selectors = [
                    'input[placeholder*="address" i]',
                    'input[placeholder*="city" i]',
                    'input[placeholder*="zip" i]',
                    'input[type="text"]',
                    'input[name*="search" i]',
                ]

                search_filled = False
                for selector in search_input_selectors:
                    try:
                        search_input = page.locator(selector)
                        if search_input.count() > 0 and search_input.first.is_visible():
                            search_input.first.fill(zip_code)
                            time.sleep(1)
                            search_filled = True
                            break
                    except Exception:
                        continue

                if not search_filled:
                    raise Exception("Could not find search input")

                # Click search button
                print(f"  → Clicking search button...")
                button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Search")',
                    'button:has-text("Find")',
                    'button.search-button',
                    'input[type="submit"]',
                ]

                button_clicked = False
                for selector in button_selectors:
                    try:
                        btn = page.locator(selector)
                        if btn.count() > 0 and btn.first.is_visible():
                            btn.first.click(timeout=5000)
                            button_clicked = True
                            break
                    except Exception:
                        continue

                if not button_clicked:
                    raise Exception("Could not find/click search button")

                # Wait for AJAX results
                print(f"  → Waiting for results...")
                time.sleep(5)

                # Extract dealers using JavaScript
                print(f"  → Extracting installer data...")
                extraction_script = self.get_extraction_script()
                results_json = page.evaluate(extraction_script)

                # Parse results
                if results_json and len(results_json) > 0:
                    print(f"  ✅ Extracted {len(results_json)} installers from Fronius")
                    dealers = self.parse_results(results_json, zip_code)
                else:
                    print(f"  ⚠️  No installers found for ZIP {zip_code}")

                # Close browser
                browser.close()

            except Exception as e:
                print(f"  ❌ Error during Fronius Playwright scraping: {str(e)}")
                import traceback
                traceback.print_exc()

        return dealers

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build workflow for Fronius
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 2000},
            {"action": "fill", "selector": self.SELECTORS["search_input"], "text": zip_code},
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
        PATCHRIGHT mode: Not yet implemented for Fronius.

        Use PLAYWRIGHT mode for manual testing or RUNPOD mode for production.
        """
        raise NotImplementedError(
            "Patchright mode not yet implemented for Fronius scraper. "
            "Use PLAYWRIGHT or RUNPOD mode instead."
        )

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Fronius scraper with factory
ScraperFactory.register("Fronius", FroniusScraper)
ScraperFactory.register("fronius", FroniusScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = FroniusScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = FroniusScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/fronius_installers_sf.json")
