"""
Enphase Certified Installer Scraper

Scrapes Enphase's certified installer network for microinverter and battery installations.
Enphase installers typically specialize in solar with microinverters and increasingly batteries (IQ Battery).

Target URL: https://enphase.com/installer-locator

Capabilities detected from Enphase certification:
- Solar installation (microinverters are their core product)
- Battery installation (IQ Battery systems)
- Electrical work (required for solar/battery)
- Often roofing work (solar roof penetrations)
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
    
    Enphase Installer Network (EIN) has three tiers based on volume,
    customer satisfaction, and product exclusivity:
    
    - Platinum: Longest track record, highest customer satisfaction, IQ Battery certified
    - Gold: Long track record, great experience, IQ Battery certified  
    - Silver: Sizable installations, some IQ Battery certified
    
    All tiers indicate solar expertise with Enphase microinverter systems.
    """
    
    OEM_NAME = "Enphase"
    DEALER_LOCATOR_URL = "https://enphase.com/installer-locator"
    PRODUCT_LINES = ["Microinverters", "IQ Battery", "Solar", "EV Chargers"]
    
    # CSS Selectors (to be filled in after site inspection)
    SELECTORS = {
        "address_input": "input[name='address']",    # TODO: Verify selector
        "zip_input": "input[name='zip']",            # TODO: Verify selector
        "search_button": "button[type='submit']",    # TODO: Verify selector
        "installer_cards": ".installer-card",        # TODO: Verify selector
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
        JavaScript extraction script for Enphase installer data.
        
        TODO: This needs to be written after inspecting Enphase's actual DOM structure
        using Playwright browser_snapshot and browser_evaluate.
        
        Expected output format:
        [
          {
            "name": "INSTALLER NAME",
            "phone": "(555) 555-5555",
            "website": "https://example.com",
            "street": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94102",
            "distance": "3.4 mi",
            "tier": "Platinum",
            "certifications": ["Microinverters", "IQ Battery", "EV Chargers"],
            "years_experience": 10,
            "rating": 4.9,
            "review_count": 156
          }
        ]
        """
        
        # JavaScript extraction script - focuses on Platinum/Gold tiers with Commercial capability
        extraction_script = """
        () => {
            const dealers = [];

            // Find all installer list items
            const installerElements = document.querySelectorAll('ul > li');

            installerElements.forEach(element => {
                try {
                    // Find the main content container
                    const contentDiv = element.querySelector('div');
                    if (!contentDiv) return;

                    // Extract tier from image alt text
                    const tierImg = element.querySelector('img[alt*="platinum"], img[alt*="gold"], img[alt*="silver"]');
                    let tier = 'Standard';
                    if (tierImg) {
                        const altText = tierImg.alt.toLowerCase();
                        if (altText.includes('platinum')) tier = 'Platinum';
                        else if (altText.includes('gold')) tier = 'Gold';
                        else if (altText.includes('silver')) tier = 'Silver';
                    }

                    // FILTER: Only Platinum and Gold tiers (per user requirement)
                    if (tier !== 'Platinum' && tier !== 'Gold') {
                        console.log(`Skipping Silver/Standard tier installer`);
                        return;
                    }

                    // Extract capabilities to check for Commercial
                    const capabilities = [];
                    const capabilityElements = element.querySelectorAll('ul li div');
                    let hasCommercial = false;
                    capabilityElements.forEach(cap => {
                        const text = cap.textContent?.trim();
                        if (text && ['Solar', 'Storage', 'Commercial', 'EV Charger', 'Ops & Maintenance'].includes(text)) {
                            capabilities.push(text);
                            if (text === 'Commercial') {
                                hasCommercial = true;
                            }
                        }
                    });

                    // Extract dealer name
                    const nameElements = contentDiv.querySelectorAll('div');
                    let name = '';
                    for (let div of nameElements) {
                        const text = div.textContent?.trim();
                        if (text && !text.includes('mi') && !text.includes(',') &&
                            text !== 'Solar' && text !== 'Storage' && text !== 'Commercial' &&
                            text !== 'EV Charger' && text !== 'Ops & Maintenance' &&
                            !text.match(/^[0-9.]+$/) && text.length > 3) {
                            // This is likely the company name
                            name = text;
                            break;
                        }
                    }

                    if (!name) return; // Skip if no name found

                    // Extract address (comes after the name, usually two text nodes)
                    const addressTexts = [];
                    const allTexts = Array.from(contentDiv.querySelectorAll('*'))
                        .map(el => el.textContent?.trim())
                        .filter(text => text && text.includes(','));

                    // Address usually has comma-separated parts
                    const address_full = allTexts.slice(0, 2).join(' ').replace(/\\s+/g, ' ').trim();

                    // Parse address components
                    let street = '', city = '', state = '', zip = '';
                    if (address_full) {
                        const parts = address_full.split(',').map(p => p.trim());
                        if (parts.length >= 2) {
                            street = parts[0];
                            const lastPart = parts[parts.length - 1];
                            const stateZipMatch = lastPart.match(/([A-Z]{2})\\s+(\\d{5})/);
                            if (stateZipMatch) {
                                state = stateZipMatch[1];
                                zip = stateZipMatch[2];
                                city = parts[parts.length - 2] || '';
                            }
                        }
                    }

                    // Extract rating (if available)
                    let rating = 0;
                    const ratingElements = Array.from(contentDiv.querySelectorAll('div'))
                        .filter(el => el.textContent?.match(/^[0-9]\\.[0-9]$/) || el.textContent?.match(/^[0-9]$/));
                    if (ratingElements.length > 0) {
                        rating = parseFloat(ratingElements[0].textContent) || 0;
                    }

                    // Phone number - Enphase doesn't display phone numbers on the locator
                    // Will need enrichment via Apollo or other sources
                    const phone = '';

                    // Add tier to certifications list
                    const certifications = ['Enphase Certified', tier + ' Partner'];
                    // Add specific product certifications
                    if (capabilities.includes('Storage')) certifications.push('IQ Battery Certified');
                    if (capabilities.includes('EV Charger')) certifications.push('EV Charger Certified');
                    if (capabilities.includes('Commercial')) certifications.push('Commercial Certified');

                    const dealer = {
                        name: name,
                        phone: phone,
                        street: street,
                        city: city,
                        state: state,
                        zip: zip,
                        address_full: address_full,
                        tier: tier,
                        certifications: certifications,
                        capabilities: capabilities,
                        rating: rating,
                        review_count: 0, // Not displayed on Enphase site
                        website: '', // Not directly available, would need enrichment
                        domain: '', // Will be extracted from website if found
                        distance: '',
                        distance_miles: 0,
                        has_commercial: hasCommercial  // Flag for commercial capability
                    };

                    // Add dealer with priority for commercial installers
                    // Commercial installers are most valuable for Coperniq
                    if (hasCommercial) {
                        // Add to front of array (higher priority)
                        dealers.unshift(dealer);
                    } else {
                        // Add to end (still valuable but lower priority)
                        dealers.push(dealer);
                    }

                    console.log(`Added ${tier} installer: ${name} (Commercial: ${hasCommercial})`);
                } catch (error) {
                    console.error('Error parsing dealer element:', error);
                }
            });

            console.log(`Found ${dealers.length} Platinum/Gold installers (${dealers.filter(d => d.has_commercial).length} with Commercial capability)`);
            return dealers;
        }
        """
        
        return extraction_script
    
    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Enphase installer data.
        
        Enphase certifications indicate:
        - All installers: has_solar + has_microinverters + has_electrical
        - Platinum/Gold: Always IQ Battery certified = has_battery
        - Silver: Sometimes IQ Battery certified = check certifications
        - Solar work typically includes has_roofing (roof penetrations)
        
        Enphase installers are pure-play solar specialists, often doing residential.
        """
        caps = DealerCapabilities()
        
        # All Enphase installers have these capabilities
        caps.has_solar = True
        caps.has_microinverters = True
        caps.has_electrical = True
        caps.has_roofing = True  # Solar installations require roof work
        
        # Check tier and certifications
        tier = raw_dealer_data.get("tier", "")
        certifications = raw_dealer_data.get("certifications", [])
        
        # Platinum and Gold always have IQ Battery certification
        if tier in ["Platinum", "Gold"]:
            caps.has_battery = True
        
        # Silver tier - check if IQ Battery certified
        elif tier == "Silver":
            if "IQ Battery" in certifications or "Battery" in certifications:
                caps.has_battery = True
        
        # EV charger certification
        if "EV Charger" in certifications or "EV" in certifications:
            # EV charger installation also indicates electrical capability (already set)
            pass
        
        # Enphase installers are typically residential focused
        caps.is_residential = True
        
        # Platinum tier often does commercial work (larger volume)
        if tier == "Platinum":
            caps.is_commercial = True  # May be updated via Apollo enrichment
        
        # Add Enphase OEM certification
        caps.oem_certifications.add("Enphase")
        
        return caps
    
    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Enphase installer data to StandardizedDealer format.
        
        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched
        
        Returns:
            StandardizedDealer object
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
        distance_miles = 0.0
        if distance_str:
            try:
                distance_miles = float(distance_str.replace(" mi", "").replace(",", ""))
            except:
                distance_miles = 0.0
        
        # Build full address
        street = raw_dealer_data.get("street", "")
        city = raw_dealer_data.get("city", "")
        state = raw_dealer_data.get("state", "")
        zip_val = raw_dealer_data.get("zip", "")
        address_full = f"{street}, {city}, {state} {zip_val}" if all([street, city, state, zip_val]) else ""
        
        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)
        
        # Enphase tier normalization
        tier = raw_dealer_data.get("tier", "Silver")  # Default to Silver if not specified
        
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
            tier=tier,
            certifications=raw_dealer_data.get("certifications", []),
            distance=distance_str,
            distance_miles=distance_miles,
            capabilities=capabilities,
            oem_source="Enphase",
            scraped_from_zip=zip_code,
        )
        
        return dealer
    
    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        
        Returns empty list and prints workflow instructions for manual execution.
        """
        print(f"\n{'='*60}")
        print(f"Enphase Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")
        
        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")
        
        print("1. Navigate to Enphase installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')
        
        print("2. Take snapshot to get current element refs:")
        print('   mcp__playwright__browser_snapshot({})\n')
        
        print("3. Handle cookie dialog (if present):")
        print('   mcp__playwright__browser_click({"element": "Accept Cookies", "ref": "[from snapshot]"})\n')
        
        print("4. Fill ZIP code or address input:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code or address input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}",')
        print(f'       "submit": False')
        print(f'   }})\n')
        
        print("5. Click search button:")
        print('   mcp__playwright__browser_click({"element": "Search button", "ref": "[from snapshot]"})\n')
        
        print("6. Wait for results to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')
        
        print("7. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')
        
        print("8. Copy the results JSON and pass to parse_results():")
        print(f'   enphase_scraper.parse_results(results_json, "{zip_code}")\n')
        
        print(f"{'='*60}\n")
        print("⚠️  TODO: Extraction script needs to be written after inspecting site DOM")
        print(f"{'='*60}\n")
        
        return []
    
    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.
        
        Sends 6-step workflow to RunPod Playwright API.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )
        
        # Build 6-step workflow for Enphase
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": 'button:has-text("Accept")'},  # Cookie dialog
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 3000},  # Wait for AJAX results
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
                timeout=60  # 60 second timeout
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
        
        Args:
            results_json: Array of installer objects from browser_evaluate
            zip_code: ZIP code that was searched
        
        Returns:
            List of StandardizedDealer objects
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Enphase scraper with factory
ScraperFactory.register("Enphase", EnphaseScraper)
ScraperFactory.register("enphase", EnphaseScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = EnphaseScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco
    
    # RUNPOD mode (automated)
    # scraper = EnphaseScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/enphase_installers_sf.json")
