"""
Sol-Ark Distributor Scraper

Scrapes Sol-Ark's distributor network for hybrid inverter installations.
Sol-Ark specializes in all-in-one hybrid solar inverters for off-grid, grid-tied, and battery backup systems.

Target URL: https://www.sol-ark.com/solar-installers/distributor-map/

Capabilities detected from Sol-Ark certification:
- Solar installation (hybrid inverters are core product)
- Battery installation (all Sol-Ark systems support battery integration)
- Electrical work (required for inverter installation)
- Off-grid and backup power systems
- Commercial and residential installations (15K, 30K, 60K models)

Strategic importance for Coperniq:
- Sol-Ark focuses on battery-integrated hybrid systems (100% battery-capable installers)
- Strong presence in backup power and resilience market (Coperniq monitoring use case)
- Distributors often carry multiple brands (Generac, Tesla, etc.) - high multi-OEM probability
- Premium tier installers with sophisticated energy storage expertise
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


class SolArkScraper(BaseDealerScraper):
    """
    Scraper for Sol-Ark authorized distributor network.

    Sol-Ark distributors specialize in:
    - Hybrid inverter installation (all-in-one solar + battery systems)
    - Off-grid and grid-tied solar installations
    - Battery backup and energy storage systems
    - Resilience and emergency power solutions
    - Commercial and residential projects

    Product Range:
    - Residential: 8K, 12K, 15K models (48V battery systems)
    - Commercial: 30K, 60K models (high-voltage battery systems)
    - All models include integrated battery management and backup switching
    """

    OEM_NAME = "Sol-Ark"
    DEALER_LOCATOR_URL = "https://www.sol-ark.com/solar-installers/distributor-map/"
    PRODUCT_LINES = ["Hybrid Inverters", "Battery Storage", "Off-Grid Systems", "Backup Power", "Commercial"]

    # CSS Selectors (to be verified after site inspection)
    SELECTORS = {
        "search_input": "input[type='text']",           # Location search input
        "search_button": "button[type='submit']",       # Search button
        "distributor_cards": ".distributor-item",       # Distributor result cards
        "map_markers": ".map-marker",                   # Map markers
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
        JavaScript extraction script for Sol-Ark distributor data.

        Sol-Ark uses an interactive distributor map with featured top distributors.
        This script extracts from both the map markers and featured distributor cards.
        """

        extraction_script = """
        () => {
            const dealers = [];

            // Sol-Ark shows both featured top distributors and map results
            const distributorElements = document.querySelectorAll(
                '.distributor-item, .distributor-card, .dealer-item, [data-distributor], .partner-item, .location-card'
            );

            console.log(`Found ${distributorElements.length} distributor elements`);

            distributorElements.forEach(element => {
                try {
                    // Extract distributor/company name
                    const nameElement = element.querySelector(
                        '.distributor-name, .company-name, .dealer-name, h3, h4, strong, .title'
                    );
                    const name = nameElement?.textContent?.trim() || '';

                    if (!name || name.length < 2) return;

                    // Skip if it's just a placeholder or label
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
                        'a[href^="http"]:not([href*="sol-ark"]), .website, .url, [class*="website"]'
                    );
                    const website = websiteElement?.href || '';

                    // Extract email
                    const emailElement = element.querySelector('a[href^="mailto:"], .email');
                    const email = emailElement?.href?.replace('mailto:', '') || '';

                    // Extract address
                    const addressElement = element.querySelector(
                        '.address, .location, .distributor-address, [class*="address"]'
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
                                }
                            } else {
                                // Try alternate format
                                const altMatch = lastPart.match(/(.+?)\\s+([A-Z]{2})\\s+(\\d{5})/);
                                if (altMatch) {
                                    city = altMatch[1];
                                    state = altMatch[2];
                                    zip = altMatch[3];
                                }
                            }
                        }
                    }

                    // Determine tier based on featured status
                    let tier = 'Sol-Ark Authorized Distributor';
                    const isFeatured = element.classList.contains('featured') ||
                                      element.closest('.top-distributors') !== null ||
                                      element.querySelector('.featured-badge') !== null;

                    if (isFeatured) {
                        tier = 'Sol-Ark Top Distributor';
                    }

                    // Extract certifications and capabilities
                    const certifications = ['Sol-Ark Authorized'];
                    const capabilities = [];

                    // All Sol-Ark distributors have these capabilities
                    capabilities.push('Solar');
                    capabilities.push('Hybrid Inverters');
                    capabilities.push('Battery Storage');  // 100% of Sol-Ark systems support batteries

                    // Check for specific capabilities from badges/tags
                    const badges = element.querySelectorAll(
                        '.badge, .certification, .capability, .tag, [class*="cert"]'
                    );

                    badges.forEach(badge => {
                        const text = badge.textContent?.trim().toLowerCase() || '';

                        if (text.includes('commercial') || text.includes('60k') || text.includes('30k')) {
                            capabilities.push('Commercial');
                            certifications.push('Commercial Systems');
                        }
                        if (text.includes('off-grid') || text.includes('backup')) {
                            capabilities.push('Off-Grid Systems');
                            certifications.push('Off-Grid Certified');
                        }
                        if (text.includes('service') || text.includes('maintenance') || text.includes('o&m')) {
                            capabilities.push('O&M Services');
                            certifications.push('Service Provider');
                        }
                    });

                    // Check name for capability indicators
                    const nameLower = name.toLowerCase();
                    const has_commercial = capabilities.includes('Commercial') ||
                                          nameLower.includes('commercial') ||
                                          nameLower.includes('solar systems') ||
                                          nameLower.includes('energy solutions') ||
                                          nameLower.includes('supply');  // Distribution companies often do commercial

                    const has_ops_maintenance = capabilities.includes('O&M Services') ||
                                               nameLower.includes('service') ||
                                               nameLower.includes('maintenance');

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
                        rating: 0,              // Sol-Ark doesn't show ratings on distributor map
                        review_count: 0,
                        tier: tier,
                        distance: distance,
                        distance_miles: distance_miles,
                        has_commercial: has_commercial,
                        has_ops_maintenance: has_ops_maintenance,
                        is_resimercial: has_commercial,  // Most Sol-Ark distributors serve both markets
                        is_top_distributor: isFeatured
                    };

                    // Prioritize top distributors and commercial-capable
                    if (isFeatured && has_commercial) {
                        dealers.unshift(dealer); // Highest priority
                    } else if (isFeatured || has_commercial) {
                        dealers.push(dealer);     // Medium priority
                    } else {
                        dealers.push(dealer);     // Standard priority
                    }

                } catch (error) {
                    console.error('Error parsing Sol-Ark distributor:', error);
                }
            });

            console.log(`Extracted ${dealers.length} Sol-Ark distributors`);
            console.log(`Top Distributors: ${dealers.filter(d => d.is_top_distributor).length}`);
            console.log(`Commercial: ${dealers.filter(d => d.has_commercial).length}`);
            console.log(`Battery Storage: ${dealers.length} (100% - all Sol-Ark systems support batteries)`);

            return dealers;
        }
        """

        return extraction_script

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Sol-Ark distributor data.

        Sol-Ark distributors indicate:
        - All distributors: has_solar + has_inverters + has_battery + has_electrical
        - 100% have battery capability (Sol-Ark's core focus is hybrid battery systems)
        - Often have generator integration capability (Sol-Ark supports generator inputs)
        - Commercial models available (30K, 60K) = commercial capability
        """
        caps = DealerCapabilities()

        # All Sol-Ark distributors have these (hybrid inverter focus)
        caps.has_solar = True
        caps.has_inverters = True     # Hybrid inverters
        caps.has_battery = True       # 100% - all Sol-Ark systems are battery-ready
        caps.has_electrical = True
        caps.has_roofing = True       # Solar requires roof work

        # Sol-Ark systems support generator inputs (backup power)
        caps.has_generator = True     # Generator integration capability

        # Check capabilities list
        capabilities = raw_dealer_data.get("capabilities", [])

        # Commercial capability
        if "Commercial" in capabilities or raw_dealer_data.get("has_commercial"):
            caps.is_commercial = True

        # Off-grid systems
        # (Note: This is tracked in capabilities list but not a separate flag in DealerCapabilities)

        # Check for resimercial (both markets)
        if raw_dealer_data.get("is_resimercial"):
            caps.is_residential = True
            caps.is_commercial = True
        else:
            # Default to residential if not explicitly commercial
            caps.is_residential = True

        # Add Sol-Ark OEM certifications
        caps.oem_certifications.add("Sol-Ark")
        caps.inverter_oems.add("Sol-Ark")
        caps.battery_oems.add("Sol-Ark")  # All Sol-Ark systems support batteries

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Sol-Ark distributor data to StandardizedDealer format.
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
            tier=raw_dealer_data.get("tier", "Sol-Ark Authorized Distributor"),
            certifications=raw_dealer_data.get("certifications", []),
            distance=distance_str,
            distance_miles=distance_miles,
            capabilities=capabilities,
            oem_source="Sol-Ark",
            scraped_from_zip=zip_code,
            has_ops_maintenance=has_ops_maintenance,
            is_resimercial=is_resimercial
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Scrape Sol-Ark distributors using browser automation.
        """
        import time
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 SOL-ARK: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to distributor map
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000)
                time.sleep(5)

                # Fill search input
                print(f"  → Searching for ZIP: {zip_code}")
                search_input = page.locator('#storelocator-search_location')
                search_input.fill(zip_code)
                time.sleep(1)

                # Handle autocomplete
                try:
                    suggestion = page.locator('.ui-autocomplete li').first
                    suggestion.wait_for(state='visible', timeout=3000)
                    print(f"  → Selecting autocomplete suggestion...")
                    suggestion.click()
                    time.sleep(4)
                except Exception:
                    print(f"  → Pressing Enter to search...")
                    search_input.press('Enter')
                    time.sleep(4)

                # Wait for results
                print(f"  → Waiting for results...")
                try:
                    page.wait_for_selector('.storelocator-store', timeout=10000)
                    time.sleep(2)
                except Exception:
                    print(f"  ⚠️  No results found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Execute extraction script
                print(f"  → Executing extraction script...")
                extraction_script = """
                () => {
                    const dealers = [];
                    const stores = document.querySelectorAll('.storelocator-store');

                    stores.forEach(store => {
                        try {
                            // Extract name
                            const nameEl = store.querySelector('.storelocator-storename');
                            const name = nameEl ? nameEl.textContent.trim() : '';
                            if (!name) return;

                            // Extract address
                            const addressEl = store.querySelector('.storelocator-address');
                            const address_full = addressEl ? addressEl.textContent.trim() : '';

                            // Parse address components
                            let street = '', city = '', state = '', zip = '';
                            if (address_full) {
                                // Format: "38455 State Hwy 22, Monroe, 68647, United States"
                                const parts = address_full.split(',').map(p => p.trim());
                                if (parts.length >= 3) {
                                    street = parts[0];
                                    city = parts[1];
                                    // Extract ZIP from remaining parts
                                    const zipMatch = address_full.match(/(\d{5})/);
                                    if (zipMatch) zip = zipMatch[1];
                                    // State abbreviation might be in the format
                                    const stateMatch = address_full.match(/,\s*([A-Z]{2})\s+\d{5}/);
                                    if (stateMatch) state = stateMatch[1];
                                }
                            }

                            // Extract phone
                            const phoneEl = store.querySelector('.storelocator-phone a[href^="tel:"]');
                            let phone = '';
                            if (phoneEl) {
                                phone = phoneEl.href.replace('tel:', '').replace(/\D/g, '');
                            }

                            // Extract email
                            const emailEl = store.querySelector('.storelocator-email a[href^="mailto:"]');
                            const email = emailEl ? emailEl.href.replace('mailto:', '') : '';

                            // Extract website
                            const websiteEl = store.querySelector('.storelocator-web a[href^="http"]');
                            const website = websiteEl ? websiteEl.href : '';

                            dealers.push({
                                name: name,
                                phone: phone,
                                email: email,
                                website: website,
                                street: street,
                                city: city,
                                state: state,
                                zip: zip,
                                address_full: address_full,
                                certifications: ['Sol-Ark Authorized'],
                                tier: 'Sol-Ark Authorized Distributor',
                                has_commercial: true,
                                is_resimercial: true
                            });
                        } catch (e) {
                            console.error('Error parsing store:', e);
                        }
                    });

                    return dealers;
                }
                """
                raw_results = page.evaluate(extraction_script)

                if not raw_results:
                    print(f"  ❌ No distributors found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = [self.parse_dealer_data(d, zip_code) for d in raw_results]
                print(f"  ✅ Found {len(dealers)} Sol-Ark distributors")

                browser.close()
                return dealers

            except Exception as e:
                print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
                import traceback
                traceback.print_exc()
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

        # Build workflow for Sol-Ark
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
        PATCHRIGHT mode: Not yet implemented for Sol-Ark.

        Use PLAYWRIGHT mode for manual testing or RUNPOD mode for production.
        """
        raise NotImplementedError(
            "Patchright mode not yet implemented for Sol-Ark scraper. "
            "Use PLAYWRIGHT or RUNPOD mode instead."
        )

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Sol-Ark scraper with factory
ScraperFactory.register("Sol-Ark", SolArkScraper)
ScraperFactory.register("solark", SolArkScraper)
ScraperFactory.register("SolArk", SolArkScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = SolArkScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = SolArkScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/solark_distributors_sf.json")
