"""
Kohler Dealer Locator Scraper

Scrapes Kohler's dealer network for home generators.
Kohler dealers are typically electrical contractors who specialize in residential backup power.

Target URL: https://kohlerpower.com/en/residential/generators/dealer-locator
Alternative: https://www.kohlerhomeenergy.rehlko.com/find-a-dealer

Capabilities detected from Kohler certification:
- Generator installation (home standby systems)
- Electrical work (required for generator install)
- Residential focus (Kohler emphasizes premium home generators)

NOTE: Extraction script needs manual DOM inspection to complete.
The site structure must be analyzed via PLAYWRIGHT mode first.
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


class KohlerScraper(BaseDealerScraper):
    """
    Scraper for Kohler dealer network.

    **STATUS**: ⚠️ BROWSERBASE RECOMMENDED (bot detection in headless mode)

    The Kohler/Rehlko site has bot detection that blocks headless Playwright.
    The extraction script works correctly (verified via MCP Playwright Dec 2024).
    For automated bulk scraping, use BROWSERBASE or PATCHRIGHT mode.

    **IMPLEMENTATION**:
    The Kohler/Rehlko dealer locator (kohlerhomeenergy.rehlko.com/find-a-dealer)
    uses a modern React-based UI with dealer cards in list items.

    **EXTRACTION APPROACH**:
    1. Navigate to dealer locator page
    2. Type ZIP code in search input
    3. Press Enter to trigger search
    4. Wait for dealer list to load
    5. Extract dealer data from DOM (name, address, phone, tier, website, distance)

    **TESTED EXTRACTION** (ZIP 94102 - San Francisco):
    - CD & POWER (Gold Dealer): Martinez, CA 94553 (60.3 miles)
    - STATE ELECTRIC GENERATOR (Silver Dealer): Scotts Valley, CA 95066 (111.7 miles)
    - FITCH ELECTRIC INC: Pleasanton, CA 94588 (58.3 miles)
    - VIERRA ELECTRIC: Santa Clara, CA 95054 (79.8 miles)

    **DEALER TIERS**:
    - Gold Dealer: Highest tier certification
    - Silver Dealer: Mid-tier certification
    - Bronze Dealer: Entry-level certification
    - Certified Installer: Basic certification
    """

    OEM_NAME = "Kohler"
    # Note: Kohler Energy rebranded to Rehlko in 2024
    DEALER_LOCATOR_URL = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
    PRODUCT_LINES = ["Home Generators", "Residential", "Standby", "Whole Home Backup"]

    # CSS Selectors - Based on Rehlko/Kohler site structure
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept')",
        "zip_input": "input[type='text']",  # ZIP code input field
        "search_button": "button:has-text('Go')",
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

        # Load Browserbase config if in BROWSERBASE mode
        if mode == ScraperMode.BROWSERBASE:
            self.browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
            self.browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction script for Kohler dealer data.

        TESTED: 2024-12-25 against kohlerhomeenergy.rehlko.com/find-a-dealer
        ZIP 94102 - Extracted 4 dealers: CD & POWER (Gold), STATE ELECTRIC (Silver),
        FITCH ELECTRIC, VIERRA ELECTRIC with name, phone, address, tier, website, distance.
        """
        return """
() => {
  const dealers = [];
  const seen = new Set();
  const phoneLinks = document.querySelectorAll('a[href^="tel:"]');

  phoneLinks.forEach(phoneLink => {
    const phone = phoneLink.textContent?.trim().replace(/[^0-9]/g, '') || '';
    // Skip main 844 number, short numbers, and duplicates
    if (phone.startsWith('844') || phone.length < 10) return;
    if (seen.has(phone)) return;
    seen.add(phone);

    // Trace up to find the li container
    let container = phoneLink;
    while (container && container.tagName !== 'LI') {
      container = container.parentElement;
    }
    if (!container) return;

    // Get all paragraphs
    const paragraphs = container.querySelectorAll('p');
    const name = paragraphs[0]?.textContent?.trim() || '';

    // Distance is in second paragraph
    const distanceText = paragraphs[1]?.textContent?.trim() || '';
    const distanceMatch = distanceText.match(/([\\d.]+)\\s*miles/i);
    const distance_miles = distanceMatch ? parseFloat(distanceMatch[1]) : 0;
    const distance = distanceMatch ? `${distanceMatch[1]} miles` : '';

    // Tier from text content
    const fullText = container.textContent || '';
    let tier = 'Certified Installer';
    if (fullText.includes('Gold Dealer')) tier = 'Gold Dealer';
    else if (fullText.includes('Silver Dealer')) tier = 'Silver Dealer';
    else if (fullText.includes('Bronze Dealer')) tier = 'Bronze Dealer';

    // Address - find paragraph with address pattern
    let street = '', city = '', state = '', zip = '';
    for (const p of paragraphs) {
      const text = p.textContent || '';
      const addrMatch = text.match(/^(\\d+[^,]+),\\s*([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
      if (addrMatch) {
        street = addrMatch[1].trim();
        city = addrMatch[2].trim();
        state = addrMatch[3];
        zip = addrMatch[4];
        break;
      }
    }

    const address_full = street ? `${street}, ${city}, ${state} ${zip}` : '';

    // Website link (skip rehlko.com links)
    let website = '', domain = '';
    const websiteLinks = container.querySelectorAll('a[href^="http"]');
    for (const link of websiteLinks) {
      if (!link.href.includes('rehlko.com')) {
        website = link.href;
        try {
          domain = new URL(website).hostname.replace('www.', '');
        } catch (e) {}
        break;
      }
    }

    dealers.push({
      name,
      phone,
      website,
      domain,
      street,
      city,
      state,
      zip,
      address_full,
      tier,
      distance,
      distance_miles,
      certifications: [tier],
      rating: 0,
      review_count: 0
    });
  });

  return dealers;
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Kohler dealer data.

        Kohler certifications indicate:
        - All dealers: has_generator + has_electrical (minimum for install)
        - Kohler focuses on premium residential generators
        - Many dealers are electrical contractors specializing in backup power
        """
        caps = DealerCapabilities()

        # All Kohler dealers have generator and electrical capabilities
        caps.has_generator = True
        caps.has_electrical = True
        caps.generator_oems.add("Kohler")

        # Extract tier
        tier = raw_dealer_data.get("tier", "Certified Installer")

        # Premier/Elite tiers indicate higher capability (if Kohler uses these)
        if tier in ["Premier", "Premier Dealer", "Elite", "Elite Dealer"]:
            caps.is_residential = True
            caps.is_commercial = False  # Kohler is primarily residential-focused

        # Kohler has strong residential focus
        caps.is_residential = True

        # Add Kohler OEM certification
        caps.oem_certifications.add("Kohler")

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = []
        if tier != "Certified Installer":
            certifications_list.append(tier)
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Kohler dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications from tier
        tier = raw_dealer_data.get("tier", "Certified Installer")
        certifications = raw_dealer_data.get("certifications", [tier])

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=raw_dealer_data.get("domain", ""),
            website=raw_dealer_data.get("website", ""),
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
            oem_source="Kohler",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Execute automated scraping using local Playwright.

        Workflow:
        1. Navigate to Kohler/Rehlko dealer locator
        2. Type ZIP code in search input
        3. Press Enter to trigger search
        4. Wait for dealer list to load
        5. Execute JavaScript extraction
        6. Parse results into StandardizedDealer objects
        """
        from playwright.sync_api import sync_playwright
        import time

        print(f"\n{'='*60}")
        print(f"Kohler Dealer Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        try:
            with sync_playwright() as p:
                print(f"  → Launching Playwright browser...")
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )

                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )

                page = context.new_page()

                # Navigate to Kohler dealer locator
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='networkidle')

                # Wait for React app to fully initialize
                print(f"  → Waiting for page to fully load...")
                time.sleep(8)

                # Find and fill ZIP code input
                # Try multiple selector strategies (site has bot detection)
                print(f"  → Filling ZIP code: {zip_code}")

                # Strategy 1: Label-based selector
                zip_selectors = [
                    'input[placeholder*="ZIP"]',
                    'input[aria-label*="ZIP"]',
                    'input[type="text"]',
                    'input[type="search"]',
                ]

                zip_input = None
                for selector in zip_selectors:
                    try:
                        loc = page.locator(selector).first
                        if loc.is_visible(timeout=3000):
                            zip_input = loc
                            print(f"     ✓ Found input with: {selector}")
                            break
                    except:
                        continue

                if not zip_input:
                    # Fallback: role-based
                    zip_input = page.get_by_role("textbox", name="ZIP Code")

                zip_input.fill(zip_code, timeout=10000)

                # Click Go button to submit
                print(f"  → Clicking Go button...")
                go_button = page.locator('button:has-text("Go")').first
                go_button.click(timeout=10000)

                # Wait for results to load
                print(f"  → Waiting for results (5s)...")
                time.sleep(5)

                # Wait for dealer list items to appear
                try:
                    page.wait_for_selector('a[href^="tel:"]', timeout=10000)
                    print(f"     ✓ Results loaded successfully")
                except Exception as e:
                    print(f"     Warning: Results may not have loaded")
                    phone_count = page.evaluate('() => document.querySelectorAll(\'a[href^="tel:"]\').length')
                    print(f"     Phone links found: {phone_count}")

                    if phone_count <= 1:  # Only the main 844 number
                        print(f"     No dealers found for ZIP {zip_code}")
                        browser.close()
                        return []

                # Extract dealer data using JavaScript
                print(f"  → Extracting dealer data...")
                extraction_script = self.get_extraction_script()
                dealers_data = page.evaluate(extraction_script)

                print(f"  → Found {len(dealers_data)} Kohler dealers")

                # Parse into StandardizedDealer objects
                dealers = self.parse_results(dealers_data, zip_code)

                browser.close()

                return dealers

        except Exception as e:
            print(f"  ✗ Error scraping with Playwright: {e}")
            import traceback
            traceback.print_exc()
            try:
                if 'browser' in locals():
                    browser.close()
            except:
                pass
            return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Execute automated scraping via serverless API.

        Uses the tested extraction script to scrape Kohler dealers.
        """
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build 6-step workflow for Kohler
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
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
            print(f"[RunPod] Scraping Kohler dealers for ZIP {zip_code}...")

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
                print(f"[RunPod] Extracted {len(raw_dealers)} dealers")

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
        BROWSERBASE mode: Cloud browser with residential proxy.

        Browserbase provides:
        - Residential proxy IPs (bypass datacenter IP blocking)
        - Pre-patched stealth (bypass JavaScript bot detection)
        - Session isolation (fresh fingerprint per session)

        Requires BROWSERBASE_API_KEY in .env
        """
        from playwright.sync_api import sync_playwright
        import time
        import random
        import os

        browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
        if not browserbase_api_key:
            raise ValueError("Missing BROWSERBASE_API_KEY in .env")

        print(f"\n{'='*60}")
        print(f"Kohler Dealer Scraper - BROWSERBASE Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        try:
            with sync_playwright() as p:
                print(f"  → Connecting to Browserbase cloud browser...")

                # WebSocket connection with residential proxy enabled
                ws_endpoint = f'wss://connect.browserbase.com?apiKey={browserbase_api_key}&enableProxy=true'
                browser = p.chromium.connect_over_cdp(ws_endpoint)

                # Get default context and page
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                print(f"  ✓ Connected to Browserbase")

                # Human-like delay before navigation
                time.sleep(random.uniform(1.5, 3.0))

                # Navigate to Kohler dealer locator
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')

                # Wait for page to stabilize
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except:
                    pass

                # Extra wait for React app to initialize
                time.sleep(random.uniform(5.0, 8.0))

                # Handle cookie consent if present
                try:
                    accept_btn = page.locator("button:has-text('Accept')").first
                    if accept_btn.is_visible(timeout=3000):
                        accept_btn.click()
                        print(f"  ✓ Accepted cookies")
                        time.sleep(1)
                except:
                    pass

                # Find and fill ZIP code input
                print(f"  → Filling ZIP code: {zip_code}")
                zip_input = page.get_by_role("textbox", name="ZIP Code")
                zip_input.fill(zip_code, timeout=15000)

                # Human-like typing delay
                time.sleep(random.uniform(0.5, 1.0))

                # Click Go button
                print(f"  → Clicking search button...")
                go_button = page.locator('button:has-text("Go")').first
                go_button.click(timeout=10000)

                # Wait for results to load
                print(f"  → Waiting for results...")
                time.sleep(random.uniform(5.0, 8.0))

                # Execute extraction script
                print(f"  → Extracting dealer data...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ⚠️ No dealers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = [self.parse_dealer_data(d, zip_code) for d in raw_results]
                print(f"  ✅ Found {len(dealers)} Kohler dealers")

                browser.close()
                return dealers

        except Exception as e:
            print(f"  ❌ Browserbase error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """PATCHRIGHT mode: Stealth browser automation (future implementation)."""
        raise NotImplementedError("Patchright mode not yet implemented")

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


# Register Kohler scraper with factory
ScraperFactory.register("Kohler", KohlerScraper)
ScraperFactory.register("kohler", KohlerScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode - tested and working
    print("\n" + "="*60)
    print("Kohler Dealer Scraper - PLAYWRIGHT Mode")
    print("="*60 + "\n")

    scraper = KohlerScraper(mode=ScraperMode.PLAYWRIGHT)
    dealers = scraper.scrape_zip_code("94102")  # San Francisco

    print(f"\n✓ Found {len(dealers)} Kohler dealers")
    for dealer in dealers:
        print(f"  - {dealer.name} ({dealer.tier}): {dealer.city}, {dealer.state} ({dealer.distance})")
        if dealer.phone:
            print(f"    Phone: {dealer.phone}")
        if dealer.website:
            print(f"    Website: {dealer.website}")
