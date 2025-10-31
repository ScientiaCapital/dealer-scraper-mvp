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
    
    # CSS Selectors (verified from site inspection)
    SELECTORS = {
        "zip_input": "input[role='combobox']",  # Combobox for ZIP/address
        "autocomplete_option": "div[role='option']",  # Autocomplete dropdown options
        "installer_cards": ".styles_ciContainer__58zW_",  # Individual installer cards
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
        
        # Tested extraction logic for Tesla installer data
        extraction_script = """
        () => {
            const cards = document.querySelectorAll('.styles_ciContainer__58zW_');

            const installers = Array.from(cards).map(card => {
                const text = card.innerText;
                const lines = text.split('\\n').filter(l => l.trim());

                // Extract data from card lines
                const tier = lines[0] || '';
                const name = lines[1] || '';
                const phone = lines[2] || '';
                const website = lines[3] || '';
                const email = lines[4] || '';

                // Extract domain from website URL
                let domain = '';
                if (website && website.startsWith('http')) {
                    try {
                        const url = new URL(website);
                        domain = url.hostname.replace('www.', '');
                    } catch (e) {
                        domain = '';
                    }
                }

                // Format phone number (Tesla provides 10 digits without formatting)
                let formattedPhone = phone;
                if (phone && phone.length === 10 && /^\\d{10}$/.test(phone)) {
                    formattedPhone = `(${phone.substring(0,3)}) ${phone.substring(3,6)}-${phone.substring(6,10)}`;
                }

                // Determine certifications based on tier
                const certifications = [];
                if (tier.includes('Premier')) {
                    certifications.push('Premier Certified Installer');
                    certifications.push('Powerwall');
                } else {
                    certifications.push('Certified Installer');
                    certifications.push('Powerwall');
                }

                return {
                    name: name,
                    phone: formattedPhone,
                    website: website,
                    domain: domain,
                    // Tesla doesn't provide address data - will use ZIP from search
                    street: '',
                    city: '',
                    state: '',
                    zip: '',
                    distance: '',
                    distance_miles: 0.0,
                    tier: tier,
                    certifications: certifications,
                    rating: 0.0,
                    review_count: 0
                };
            });

            // Filter to only Premier Certified Installers (highest quality)
            return installers.filter(installer => installer.tier.includes('Premier'));
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

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        caps.detect_high_value_contractor_types(dealer_name, certifications, tier)

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

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Execute automated scraping via Browserbase cloud browser.

        Tesla's installer locator workflow:
        1. Navigate to page
        2. Type ZIP code in autocomplete input
        3. Click on autocomplete suggestion
        4. Wait for results to load
        5. Extract installer data

        Requires: playwright Python package (pip install playwright)
        """
        if not hasattr(self, 'browserbase_api_key') or not hasattr(self, 'browserbase_project_id'):
            # Load from env if not already loaded
            self.browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
            self.browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

        if not self.browserbase_api_key or not self.browserbase_project_id:
            raise ValueError(
                "Missing Browserbase credentials. Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID in .env"
            )

        try:
            # Import playwright (only imported when BROWSERBASE mode is used)
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise ImportError(
                    "Browserbase mode requires 'playwright' package. "
                    "Install with: pip install playwright && playwright install chromium"
                )

            print(f"[Browserbase] Creating session for ZIP {zip_code}...")

            # Step 1: Create Browserbase session
            create_session_url = f"https://api.browserbase.com/v1/sessions"
            headers = {
                "X-BB-API-Key": self.browserbase_api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "projectId": self.browserbase_project_id,
            }

            response = requests.post(create_session_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            session_data = response.json()

            session_id = session_data["id"]
            connect_url = session_data["connectUrl"]  # WebSocket URL for CDP

            print(f"[Browserbase] Session created: {session_id}")
            print(f"[Browserbase] Connecting to remote browser...")

            # Step 2: Connect to Browserbase via Playwright CDP
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(connect_url)
                context = browser.contexts[0]  # Browserbase provides a default context
                page = context.pages[0] if context.pages else context.new_page()

                print(f"[Browserbase] Connected! Navigating to Tesla installer locator...")

                # Step 3: Execute Tesla workflow
                # 1. Navigate
                page.goto(self.DEALER_LOCATOR_URL, wait_until="load", timeout=30000)

                # 2. Wait for page to be fully ready (Tesla loads a lot of resources)
                print(f"[Browserbase] Waiting for page to load...")
                page.wait_for_timeout(3000)  # Initial wait for scripts to load
                page.wait_for_load_state("networkidle", timeout=30000)  # Wait for network idle
                page.wait_for_timeout(2000)  # Additional wait for dynamic content

                # 3. Fill ZIP code - Tesla uses an input with combobox role
                # Use getByRole instead of CSS selector (more reliable)
                print(f"[Browserbase] Filling ZIP code...")
                try:
                    zip_input = page.get_by_role('combobox', name='Zip code or address')
                    zip_input.fill(zip_code)
                    print(f"[Browserbase] Filled ZIP code: {zip_code}")
                except Exception as e:
                    print(f"[Browserbase] getByRole failed, trying CSS selector: {e}")
                    # Fallback to CSS selector
                    page.wait_for_selector('input[role="combobox"]', state='visible', timeout=30000)
                    zip_input = page.locator('input[role="combobox"]')
                    zip_input.fill(zip_code)
                    print(f"[Browserbase] Filled ZIP code with CSS selector: {zip_code}")

                # Try autocomplete first, but fallback to Enter key if it doesn't appear
                print(f"[Browserbase] Waiting for autocomplete dropdown...")
                try:
                    # Wait for Google Places autocomplete listbox
                    page.wait_for_selector('div[role="listbox"]', state='visible', timeout=3000)
                    page.wait_for_timeout(500)
                    print(f"[Browserbase] Clicking first autocomplete option...")
                    page.click('div[role="listbox"] div[role="option"]:first-child')
                except Exception:
                    # Autocomplete didn't appear - press Enter instead
                    print(f"[Browserbase] Autocomplete not appearing, pressing Enter...")
                    zip_input.press('Enter')
                    page.wait_for_timeout(1000)

                # 5. Wait for results to load
                page.wait_for_timeout(4000)

                # 6. Extract installer data
                print(f"[Browserbase] Extracting installer data...")
                raw_dealers = page.evaluate(self.get_extraction_script())

                print(f"[Browserbase] Extracted {len(raw_dealers)} installers")

                # Close browser connection
                browser.close()

            # Step 4: Close Browserbase session
            delete_session_url = f"https://api.browserbase.com/v1/sessions/{session_id}"
            requests.delete(delete_session_url, headers=headers, timeout=10)
            print(f"[Browserbase] Session closed")

            # Step 5: Parse results
            dealers = [self.parse_dealer_data(d, zip_code) for d in raw_dealers]
            return dealers

        except requests.exceptions.Timeout:
            raise Exception(f"Browserbase API timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Browserbase API request failed: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse Browserbase API response as JSON")
        except Exception as e:
            raise Exception(f"Browserbase scraping failed: {str(e)}")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Stealth browser automation with bot detection bypass.

        Uses Patchright (patched Playwright) to bypass Tesla's bot detection:
        - Patches 20+ automation fingerprints (navigator.webdriver, CDP, etc.)
        - Uses real Chrome browser (not Chromium)
        - Persistent context for realistic browser profile
        - Headless=False to avoid headless detection

        Workflow:
        1. Launch persistent Chrome context (max stealth)
        2. Type ZIP code in autocomplete input
        3. Click on autocomplete suggestion
        4. Wait for results to load
        5. Extract installer data

        Requires: patchright Python package (pip install patchright)
        """
        try:
            # Import patchright (only imported when PATCHRIGHT mode is used)
            try:
                from patchright.sync_api import sync_playwright
            except ImportError:
                raise ImportError(
                    "Patchright mode requires 'patchright' package. "
                    "Install with: pip install patchright && patchright install chromium"
                )

            print(f"[Patchright] Launching stealth browser for ZIP {zip_code}...")

            # Step 1: Launch Patchright with persistent context (max stealth)
            with sync_playwright() as p:
                # Use persistent context for realistic browser profile
                # headless=False = avoid headless detection
                # Patchright's patched chromium has 20+ fingerprint fixes built-in
                context = p.chromium.launch_persistent_context(
                    user_data_dir="./patchright-chrome-profile",
                    headless=False,  # Visible mode (required for stealth)
                    no_viewport=True,  # Natural viewport
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )

                page = context.pages[0] if context.pages else context.new_page()

                print(f"[Patchright] Navigating to Tesla installer locator...")

                # Step 2: Execute Tesla workflow
                # 1. Navigate
                page.goto(self.DEALER_LOCATOR_URL, wait_until="load", timeout=30000)

                # 2. Wait for page to be fully ready
                page.wait_for_timeout(2000)
                page.wait_for_load_state("networkidle", timeout=15000)

                # 3. Fill ZIP code - Tesla uses an input with combobox role
                # Wait for the input to be visible first
                print(f"[Patchright] Waiting for ZIP input...")
                page.wait_for_selector('input[role="combobox"]', state='visible', timeout=15000)

                # Click to focus, then type (not fill) to trigger search
                zip_input = page.locator('input[role="combobox"]')
                zip_input.click()
                page.wait_for_timeout(500)
                zip_input.type(zip_code, delay=100)  # Type with delay
                print(f"[Patchright] Typed ZIP code: {zip_code}")

                # Try autocomplete first, but fallback to Enter key if it doesn't appear
                print(f"[Patchright] Waiting for autocomplete dropdown...")
                try:
                    # Wait for Google Places autocomplete listbox
                    page.wait_for_selector('div[role="listbox"]', state='visible', timeout=3000)
                    page.wait_for_timeout(500)
                    print(f"[Patchright] Clicking first autocomplete option...")
                    page.click('div[role="listbox"] div[role="option"]:first-child')
                except Exception:
                    # Autocomplete didn't appear - press Enter instead
                    print(f"[Patchright] Autocomplete not appearing, pressing Enter...")
                    zip_input.press('Enter')
                    page.wait_for_timeout(1000)

                # 5. Wait for results to load
                page.wait_for_timeout(4000)

                # 6. Extract installer data
                print(f"[Patchright] Extracting installer data...")
                raw_dealers = page.evaluate(self.get_extraction_script())

                print(f"[Patchright] Extracted {len(raw_dealers)} installers")

                # Close browser
                context.close()

            # Step 3: Parse results
            dealers = [self.parse_dealer_data(d, zip_code) for d in raw_dealers]
            return dealers

        except Exception as e:
            raise Exception(f"Patchright scraping failed: {str(e)}")

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
