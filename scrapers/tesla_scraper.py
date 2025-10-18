"""
Tesla Powerwall Certified Installer Scraper

Scrapes Tesla's certified installer network for Powerwall battery installations.
Tesla installers typically also do solar and electrical work.

Target URL: https://www.tesla.com/support/certified-installers-powerwall

Capabilities detected from Tesla certification:
- Battery installation (Powerwall)
- Electrical work (required for battery install)
- Often solar installation (many Tesla installers do solar + battery)
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
    
    Tesla's installer locator shows contractors certified to install:
    - Powerwall (home battery storage)
    - Solar Roof / Solar Panels
    - Wall Connector (EV charging)
    
    Certification tiers:
    - Premier Certified Installer (highest tier)
    - Certified Installer (standard)
    """
    
    OEM_NAME = "Tesla"
    DEALER_LOCATOR_URL = "https://www.tesla.com/support/certified-installers-powerwall"
    PRODUCT_LINES = ["Powerwall", "Solar", "Battery", "EV Charging"]
    
    # CSS Selectors (to be filled in after site inspection)
    SELECTORS = {
        "zip_input": "input[name='postalCode']",  # TODO: Verify selector
        "search_button": "button[type='submit']",  # TODO: Verify selector
        "installer_cards": ".installer-card",       # TODO: Verify selector
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
        JavaScript extraction script for Tesla installer data.
        
        TODO: This needs to be written after inspecting Tesla's actual DOM structure
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
            "distance": "5.2 mi",
            "tier": "Premier Certified",
            "certifications": ["Powerwall", "Solar Roof", "Wall Connector"],
            "rating": 4.8,
            "review_count": 42
          }
        ]
        """
        
        # PLACEHOLDER - Replace with actual extraction logic after site inspection
        extraction_script = """
        () => {
            // TODO: Implement Tesla-specific extraction logic
            // 
            // Steps:
            // 1. Find all installer card elements
            // 2. For each card, extract:
            //    - Company name
            //    - Phone number (normalize format)
            //    - Website URL
            //    - Address components (street, city, state, ZIP)
            //    - Distance from search ZIP
            //    - Certification tier (Premier vs Standard)
            //    - Product certifications (Powerwall, Solar, Wall Connector)
            //    - Rating and review count (if available)
            // 3. Return array of installer objects
            
            console.log("Tesla extraction script - needs implementation");
            
            // Placeholder return
            return [];
        }
        """
        
        return extraction_script
    
    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Tesla installer data.
        
        Tesla certifications indicate:
        - Powerwall certified = has_battery + has_electrical
        - Solar Roof/Panel certified = has_solar + has_electrical + has_roofing (for Solar Roof)
        - Wall Connector = has_electrical (EV charging)
        
        Many Tesla installers are multi-trade contractors doing solar + battery + electrical.
        """
        caps = DealerCapabilities()
        
        # All Tesla installers have electrical capability (required for Powerwall)
        caps.has_electrical = True
        
        # Check certifications from raw data
        certifications = raw_dealer_data.get("certifications", [])
        tier = raw_dealer_data.get("tier", "")
        
        # Powerwall certification
        if "Powerwall" in certifications or "powerwall" in tier.lower():
            caps.has_battery = True
        
        # Solar certification
        if any(cert in certifications for cert in ["Solar Roof", "Solar Panel", "Solar"]):
            caps.has_solar = True
        
        # Solar Roof includes roofing work
        if "Solar Roof" in certifications:
            caps.has_roofing = True
        
        # Premier tier typically means full-service contractor
        if "Premier" in tier or "premier" in tier.lower():
            caps.is_residential = True
            # Premier installers often do commercial work too
            # (will be enriched via Apollo later)
        
        # Add Tesla OEM certification
        caps.oem_certifications.add("Tesla")
        
        return caps
    
    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Tesla installer data to StandardizedDealer format.
        
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
            tier=raw_dealer_data.get("tier", "Certified"),
            certifications=raw_dealer_data.get("certifications", []),
            distance=distance_str,
            distance_miles=distance_miles,
            capabilities=capabilities,
            oem_source="Tesla",
            scraped_from_zip=zip_code,
        )
        
        return dealer
    
    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        
        Returns empty list and prints workflow instructions for manual execution.
        """
        print(f"\n{'='*60}")
        print(f"Tesla Powerwall Installer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")
        
        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")
        
        print("1. Navigate to Tesla installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')
        
        print("2. Take snapshot to get current element refs:")
        print('   mcp__playwright__browser_snapshot({})\n')
        
        print("3. Handle cookie dialog (if present):")
        print('   mcp__playwright__browser_click({"element": "Accept Cookies", "ref": "[from snapshot]"})\n')
        
        print("4. Fill ZIP code input:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
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
        print(f'   tesla_scraper.parse_results(results_json, "{zip_code}")\n')
        
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
        
        # Build 6-step workflow for Tesla
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


# Register Tesla scraper with factory
ScraperFactory.register("Tesla", TeslaScraper)
ScraperFactory.register("tesla", TeslaScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = TeslaScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco
    
    # RUNPOD mode (automated)
    # scraper = TeslaScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/tesla_dealers_sf.json")
