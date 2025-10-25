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

        Fronius uses a PartnerSearch component with map and list views.
        This script extracts from the list view results.
        """

        extraction_script = """
        () => {
            const dealers = [];

            // Fronius uses a PartnerSearch component - try multiple selectors
            const partnerElements = document.querySelectorAll(
                '.partner-item, .partner-card, .installer-item, [data-partner], .search-result-item'
            );

            console.log(`Found ${partnerElements.length} potential partner elements`);

            partnerElements.forEach(element => {
                try {
                    // Extract partner name
                    const nameElement = element.querySelector(
                        '.partner-name, .installer-name, .company-name, h3, h4, strong, .title'
                    );
                    const name = nameElement?.textContent?.trim() || '';

                    if (!name || name.length < 2) return;

                    // Extract phone number
                    const phoneElement = element.querySelector(
                        'a[href^="tel:"], .phone, .telephone, .contact-phone, [class*="phone"]'
                    );
                    let phone = '';
                    if (phoneElement) {
                        phone = phoneElement.textContent?.trim() || phoneElement.href?.replace('tel:', '') || '';
                        phone = phone.replace(/[^\\d]/g, ''); // Normalize to digits only
                    }

                    // Extract website/email
                    const websiteElement = element.querySelector(
                        'a[href^="http"]:not([href*="fronius"]), .website, .url, [class*="website"]'
                    );
                    const website = websiteElement?.href || '';

                    // Extract email (Fronius sometimes shows email instead of website)
                    const emailElement = element.querySelector('a[href^="mailto:"], .email');
                    const email = emailElement?.href?.replace('mailto:', '') || '';

                    // Extract address (Fronius shows full address in one element)
                    const addressElement = element.querySelector(
                        '.address, .location, .partner-address, [class*="address"]'
                    );
                    const address_full = addressElement?.textContent?.trim() || '';

                    // Parse address components
                    let street = '', city = '', state = '', zip = '';
                    if (address_full) {
                        // Format: "123 Main St, City, ST 12345" or variations
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

                    // Extract partner tier/status
                    let tier = 'Fronius Solutions Partner';
                    const tierElement = element.querySelector(
                        '.partner-status, .tier, .badge, .certification-level, [class*="status"]'
                    );
                    if (tierElement) {
                        const tierText = tierElement.textContent?.trim() || '';
                        if (tierText.toLowerCase().includes('plus') || tierText.toLowerCase().includes('premium')) {
                            tier = 'Fronius Solutions Partner Plus';
                        }
                    }

                    // Extract certifications and capabilities
                    const certifications = ['Fronius Certified'];
                    const capabilities = [];

                    // Default capabilities for all Fronius installers
                    capabilities.push('Solar');
                    capabilities.push('String Inverters');

                    // Check for specific certifications/badges
                    const badges = element.querySelectorAll(
                        '.badge, .certification, .capability, .tag, [class*="cert"]'
                    );

                    badges.forEach(badge => {
                        const text = badge.textContent?.trim().toLowerCase() || '';

                        if (text.includes('battery') || text.includes('storage') || text.includes('gen24')) {
                            capabilities.push('Battery Storage');
                            certifications.push('Battery Storage Certified');
                        }
                        if (text.includes('commercial')) {
                            capabilities.push('Commercial');
                            certifications.push('Commercial Certified');
                        }
                        if (text.includes('hybrid')) {
                            capabilities.push('Hybrid Systems');
                            certifications.push('Hybrid Inverter Certified');
                        }
                        if (text.includes('service') || text.includes('maintenance') || text.includes('o&m')) {
                            capabilities.push('O&M Services');
                            certifications.push('Service Provider');
                        }
                    });

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

                    // Check for commercial indicators
                    const has_commercial = capabilities.includes('Commercial') ||
                                          name.toLowerCase().includes('commercial') ||
                                          name.toLowerCase().includes('solar systems') ||
                                          name.toLowerCase().includes('energy solutions');

                    // Check for O&M services
                    const has_ops_maintenance = capabilities.includes('O&M Services') ||
                                               name.toLowerCase().includes('service') ||
                                               name.toLowerCase().includes('maintenance');

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
                        rating: 0,              // Fronius doesn't show ratings on locator
                        review_count: 0,
                        tier: tier,
                        distance: distance,
                        distance_miles: distance_miles,
                        has_commercial: has_commercial,
                        has_ops_maintenance: has_ops_maintenance,
                        is_resimercial: capabilities.includes('Commercial') // Commercial-capable likely does both
                    };

                    // Prioritize by tier and capabilities
                    if (tier.includes('Plus') && has_commercial) {
                        dealers.unshift(dealer); // Highest priority
                    } else if (has_commercial || tier.includes('Plus')) {
                        dealers.push(dealer);     // Medium priority
                    } else {
                        dealers.push(dealer);     // Standard priority
                    }

                } catch (error) {
                    console.error('Error parsing Fronius partner:', error);
                }
            });

            console.log(`Extracted ${dealers.length} Fronius installers`);
            console.log(`Partner Plus: ${dealers.filter(d => d.tier.includes('Plus')).length}`);
            console.log(`Commercial: ${dealers.filter(d => d.has_commercial).length}`);
            console.log(`Battery Storage: ${dealers.filter(d => d.capabilities.includes('Battery Storage')).length}`);

            return dealers;
        }
        """

        return extraction_script

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
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*60}")
        print(f"Fronius Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Fronius installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Take snapshot to get current element refs:")
        print('   mcp__playwright__browser_snapshot({})\n')

        print("3. Handle cookie consent (if present):")
        print('   mcp__playwright__browser_click({"element": "Accept", "ref": "[from snapshot]"})\n')

        print("4. Enter ZIP code or address:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "Search input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')

        print("5. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search", "ref": "[from snapshot]"})\n')

        print("6. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("7. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("8. Process results with:")
        print(f'   fronius_scraper.parse_results(results_json, "{zip_code}")\n')

        print(f"{'='*60}\n")

        return []

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
