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

    # CSS Selectors (to be verified after site inspection)
    SELECTORS = {
        "country_select": "select#country",              # Country dropdown
        "zip_input": "input[name='zip']",                # ZIP code input
        "search_button": "button[type='submit']",        # Search button
        "dealer_cards": ".dealer-item",                  # Dealer result cards
        "product_filter": "input[type='checkbox']",      # Product type checkboxes
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

        extraction_script = """
        () => {
            const dealers = [];

            // Briggs & Stratton uses dealer cards with contact info
            const dealerElements = document.querySelectorAll(
                '.dealer-item, .dealer-card, .installer-item, [data-dealer], .location-card, .result-item'
            );

            console.log(`Found ${dealerElements.length} dealer elements`);

            dealerElements.forEach(element => {
                try {
                    // Extract dealer name
                    const nameElement = element.querySelector(
                        '.dealer-name, .company-name, .installer-name, h3, h4, strong, .title'
                    );
                    const name = nameElement?.textContent?.trim() || '';

                    if (!name || name.length < 2) return;

                    // Skip placeholders
                    if (name.toLowerCase().includes('loading') || name.toLowerCase().includes('search')) {
                        return;
                    }

                    // Extract phone number
                    const phoneElement = element.querySelector(
                        'a[href^="tel:"], .phone, .telephone, .contact-phone, [class*="phone"]'
                    );
                    let phone = '';
                    if (phoneElement) {
                        phone = phoneElement.textContent?.trim() || phoneElement.href?.replace('tel:', '') || '';
                        phone = phone.replace(/[^\\d]/g, ''); // Normalize to digits only
                    }

                    // Extract website
                    const websiteElement = element.querySelector(
                        'a[href^="http"]:not([href*="briggsandstratton"]):not([href*="simpliphi"]), .website, .url, [class*="website"]'
                    );
                    const website = websiteElement?.href || '';

                    // Extract email
                    const emailElement = element.querySelector('a[href^="mailto:"], .email');
                    const email = emailElement?.href?.replace('mailto:', '') || '';

                    // Extract address
                    const addressElement = element.querySelector(
                        '.address, .location, .dealer-address, [class*="address"]'
                    );
                    const address_full = addressElement?.textContent?.trim() || '';

                    // Parse address components
                    let street = '', city = '', state = '', zip = '';
                    if (address_full) {
                        // Format: "123 Main St, City, ST 12345"
                        const parts = address_full.split(',').map(p => p.trim());

                        if (parts.length >= 2) {
                            street = parts[0];

                            // Last part usually has state + ZIP
                            const lastPart = parts[parts.length - 1];
                            const stateZipMatch = lastPart.match(/([A-Z]{2})\\s+(\\d{5})/);

                            if (stateZipMatch) {
                                state = stateZipMatch[1];
                                zip = stateZipMatch[2];

                                // City is second-to-last part
                                if (parts.length >= 3) {
                                    city = parts[parts.length - 2];
                                } else {
                                    city = parts[0];
                                }
                            } else {
                                // Try alternate format: "City ST 12345"
                                const altMatch = lastPart.match(/(.+?)\\s+([A-Z]{2})\\s+(\\d{5})/);
                                if (altMatch) {
                                    city = altMatch[1];
                                    state = altMatch[2];
                                    zip = altMatch[3];
                                }
                            }
                        }
                    }

                    // Extract certifications and capabilities
                    const certifications = ['SimpliPhi Authorized'];
                    const capabilities = [];

                    // All SimpliPhi installers have battery capability
                    capabilities.push('Battery Storage');
                    capabilities.push('Energy Storage Systems');

                    // Check for product offerings
                    const productElements = element.querySelectorAll(
                        '.product, .service, .offering, .capability, [class*="product"]'
                    );

                    let has_generators = false;
                    let has_solar = false;

                    productElements.forEach(prod => {
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
                        if (text.includes('commercial')) {
                            capabilities.push('Commercial');
                            certifications.push('Commercial Systems');
                        }
                    });

                    // Check name for capability indicators
                    const nameLower = name.toLowerCase();
                    if (!has_solar) {
                        if (nameLower.includes('solar') || nameLower.includes('renewable')) {
                            capabilities.push('Solar');
                            has_solar = true;
                        }
                    }
                    if (!has_generators) {
                        if (nameLower.includes('generator') || nameLower.includes('power')) {
                            capabilities.push('Generators');
                            has_generators = true;
                        }
                    }

                    const has_commercial = capabilities.includes('Commercial') ||
                                          nameLower.includes('commercial') ||
                                          nameLower.includes('solutions') ||
                                          nameLower.includes('systems');

                    // Extract distance if shown
                    const distanceElement = element.querySelector(
                        '.distance, [class*="distance"], [data-distance]'
                    );
                    let distance = '';
                    let distance_miles = 0;
                    if (distanceElement) {
                        distance = distanceElement.textContent?.trim() || '';
                        const distMatch = distance.match(/([\\d.]+)\\s*(mi|km)/);
                        if (distMatch) {
                            distance_miles = parseFloat(distMatch[1]);
                            if (distMatch[2] === 'km') {
                                distance_miles = distance_miles * 0.621371; // Convert km to miles
                            }
                        }
                    }

                    const dealer = {
                        name: name,
                        phone: phone,
                        email: email,
                        website: website,
                        street: street,
                        city: city,
                        state: state,
                        zip: zip,
                        address_full: address_full,
                        certifications: certifications,
                        capabilities: capabilities,
                        rating: 0,              // Briggs & Stratton dealer locator doesn't show ratings
                        review_count: 0,
                        tier: 'SimpliPhi Authorized Installer',
                        distance: distance,
                        distance_miles: distance_miles,
                        has_commercial: has_commercial,
                        has_generators: has_generators,
                        has_solar: has_solar,
                        is_multi_product: has_generators && has_solar,  // Both generator + solar = premium
                        is_resimercial: has_commercial
                    };

                    // Prioritize multi-product dealers (generators + solar + batteries)
                    if (dealer.is_multi_product && has_commercial) {
                        dealers.unshift(dealer); // Highest priority - triple threat
                    } else if (dealer.is_multi_product) {
                        dealers.push(dealer);     // High priority - multi-product
                    } else {
                        dealers.push(dealer);     // Standard priority
                    }

                } catch (error) {
                    console.error('Error parsing SimpliPhi dealer:', error);
                }
            });

            console.log(`Extracted ${dealers.length} SimpliPhi installers`);
            console.log(`Multi-product (Gen+Solar+Battery): ${dealers.filter(d => d.is_multi_product).length}`);
            console.log(`Solar capable: ${dealers.filter(d => d.has_solar).length}`);
            console.log(`Generator capable: ${dealers.filter(d => d.has_generators).length}`);

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
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*60}")
        print(f"SimpliPhi Power Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Briggs & Stratton dealer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to get current element refs:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. Handle cookie consent (if present):")
        print('   mcp__playwright__browser_click({"element": "Accept", "ref": "[from snapshot]"})\n')

        print("4. Select country (USA):")
        print('   mcp__playwright__browser_select_option({')
        print('       "element": "Country dropdown",')
        print('       "ref": "[from snapshot]",')
        print('       "values": ["USA"]')
        print('   })\n')

        print("5. Enter ZIP code:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')

        print("6. Check 'Battery Energy Storage' checkbox:")
        print('   mcp__playwright__browser_click({"element": "Battery Energy Storage", "ref": "[from snapshot]"})\n')

        print("7. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search", "ref": "[from snapshot]"})\n')

        print("8. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("9. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("10. Process results with:")
        print(f'   simpliphi_scraper.parse_results(results_json, "{zip_code}")\n')

        print(f"{'='*60}\n")
        print("NOTE: Briggs & Stratton dealer locator allows filtering by:")
        print("      - Product type (Standby Generators, Battery Energy Storage)")
        print("      - Search radius (50, 75, 100, 150 miles)")
        print("      Extraction script captures dealers offering Battery Energy Storage.\n")

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
