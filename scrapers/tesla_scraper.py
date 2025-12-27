"""
Tesla Powerwall Certified Installer Scraper

Scrapes Tesla's Powerwall certified installer network for battery + solar installations.
Tesla Powerwall installers are strategic targets because they handle premium battery storage
systems and often manage complex residential + commercial energy projects.

Target URL: https://www.tesla.com/en_us/support/certified-installers
(Updated Dec 2025 - uses /en_us/ locale to prevent geo-redirect)

**GEO-REDIRECT FIX**: Tesla redirects based on IP geolocation (e.g., UK users get /en_gb/).
We force US locale by using `/en_us/` in the URL path. For automated scraping, use
BROWSERBASE mode with US residential proxy to ensure US results.

**BOT DETECTION**: Tesla uses enterprise-grade Akamai EdgeSuite protection.
TESTED Dec 27, 2025:
- ❌ Playwright headless/headed: Blocked (Access Denied)
- ❌ Patchright headless/headed: Blocked (Access Denied)
- ❌ Puppeteer MCP: Blocked (Access Denied)
- ❌ Firecrawl: Blocked (Access Denied)
- ❌ Browserbase basic stealth + residential proxy: Blocked (Access Denied)
- ⚠️ Browserbase Advanced Stealth: Requires Enterprise plan ($$$)

**CURRENT STATUS**: Tesla's /support/certified-installers page is protected by
Akamai's most aggressive bot detection. Even Browserbase with residential proxy
gets blocked. The homepage (tesla.com) works, but installer pages are locked down.

**OPTIONS**:
1. Upgrade to Browserbase Enterprise plan (Advanced Stealth with custom Chromium)
2. Use alternative scraping service specializing in Akamai bypass
3. Manual data collection
4. Partner API (if Tesla offers one)

Capabilities detected from Tesla certification:
- Battery installation (Powerwall is their core product)
- Solar installation (many installers are Tesla Energy Certified for Solar Roof + panels)
- Electrical work (required for Powerwall installation)
- Premium residential and increasingly commercial installations

Strategic importance for Coperniq:
- Tesla Powerwall installers are premium contractors (high-value customers)
- Battery + solar expertise = ideal Coperniq platform users
- Many also install generators (full energy resilience solution)
- Premier Installer tier indicates high volume + quality (best prospects)
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

    Tesla Powerwall is the premium residential/commercial battery storage system.
    Installers certified by Tesla represent high-quality contractors who can
    handle complex energy storage + solar installations.

    All Tesla installers are "Premier Installers" - representing the highest tier.

    **GEO-REDIRECT FIX**: Tesla redirects based on IP geolocation. We force US locale
    by using `/en_us/` in the URL path. For automated scraping, use BROWSERBASE mode
    with US residential proxy to ensure US results.
    """

    OEM_NAME = "Tesla"
    # CRITICAL: Use /en_us/ locale to prevent geo-redirect to UK/EU sites
    DEALER_LOCATOR_URL = "https://www.tesla.com/en_us/support/certified-installers"
    PRODUCT_LINES = ["Powerwall", "Solar Roof", "Solar Panels", "Wall Connector", "Powershare"]

    # NOTE: Tesla requires Playwright with stealth mode due to bot detection (403 without it)

    # CSS Selectors (validated via Playwright MCP)
    SELECTORS = {
        "zip_input": "input[placeholder*='Zip code']",
        "search_button": "button[type='submit']",  # Not needed - autocomplete handles search
        "installer_cards": "div",  # Tesla uses generic div with "Premier Installer" text
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
        JavaScript extraction script for Tesla Powerwall installer data.

        VALIDATED: Tested on ZIP 94102 (14 dealers) and ZIP 77002 (8 dealers visible).

        Data Pattern:
        Tesla concatenates all dealer info without spaces:
        "Premier InstallerLuminalt Energy Corporation4156414000https://luminalt.com/powerwall@luminalt.com"

        Extraction Strategy:
        1. Find all <div> elements containing exactly 1 "Premier Installer" text
        2. Extract phone (10 digits) as anchor point
        3. Extract email (standard pattern with @)
        4. Extract website (https:// OR www.domain patterns)
        5. Extract name (everything before phone, cleaned)
        6. Deduplicate by phone number
        """

        # Read the validated extraction.js script
        extraction_script_path = os.path.join(
            os.path.dirname(__file__),
            "tesla",
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
                    if 'function extractTeslaDealers()' in line:
                        in_function = True
                        continue
                    if in_function:
                        function_lines.append(line)

                # Join and wrap in IIFE
                return "() => {\n" + "".join(function_lines) + "\n}"

        # Fallback inline version (validated)
        return """
        () => {
          function extractTeslaDealers() {
            console.log('[Tesla] Starting dealer extraction...');

            // Find all <div> elements that contain exactly one "Premier Installer" badge
            const allDivs = Array.from(document.querySelectorAll('div'));
            const dealerCards = allDivs.filter(div => {
              const text = div.textContent;
              const badgeCount = (text.match(/Premier Installer/g) || []).length;
              return badgeCount === 1 && text.length > 20 && text.length < 500;
            });

            console.log(`[Tesla] Found ${dealerCards.length} potential dealer cards`);

            const dealers = [];
            const seenPhones = new Set();

            dealerCards.forEach((card, index) => {
              let text = card.textContent.trim();
              text = text.replace(/Premier Installer/g, '').trim();

              // Extract phone number (10 digits) - ANCHOR POINT
              const phoneMatch = text.match(/(\\d{10})/);
              if (!phoneMatch) {
                console.log(`[Tesla] Card ${index + 1}: No phone found, skipping`);
                return;
              }
              const phone = phoneMatch[1];

              // Deduplicate by phone
              if (seenPhones.has(phone)) {
                console.log(`[Tesla] Card ${index + 1}: Duplicate phone ${phone}, skipping`);
                return;
              }
              seenPhones.add(phone);

              // Extract email (standard pattern with @)
              const emailMatch = text.match(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/);
              const email = emailMatch ? emailMatch[1] : '';

              // Extract website - handle both https:// and www. patterns
              let website = '';
              if (email) {
                const emailPrefix = email.split('@')[0];
                const httpsPattern = new RegExp('(https?://[^@]+?)' + emailPrefix + '@');
                const httpsMatch = text.match(httpsPattern);

                if (httpsMatch) {
                  website = httpsMatch[1];
                } else {
                  const wwwPattern = new RegExp('(www\\\\.[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,})' + emailPrefix + '@');
                  const wwwMatch = text.match(wwwPattern);
                  if (wwwMatch) {
                    website = 'https://' + wwwMatch[1];
                  } else {
                    const emailDomain = email.split('@')[1];
                    website = 'https://' + emailDomain;
                  }
                }
              } else {
                const match = text.match(/(https?:\\/\\/[^\\d\\s]+?)(?=\\d{10}|$)/);
                if (match) website = match[1];
              }

              website = website.replace(/\\/$/, '').trim();

              // Extract name (everything before phone number)
              let name = text.substring(0, text.indexOf(phone)).trim();
              if (website) {
                name = name.replace(website, '').trim();
                name = name.replace(website.replace('https://', ''), '').trim();
              }
              if (email) name = name.replace(email, '').trim();
              name = name.replace(/https?:\\/\\/[^\\s]+/g, '').trim();
              name = name.replace(/www\\.[^\\s]+/g, '').trim();

              // Only add if we have at least name and phone
              if (name && phone) {
                dealers.push({
                  name: name,
                  phone: phone,
                  website: website,
                  email: email,
                  tier: 'Premier Installer',
                  oem_source: 'Tesla'
                });
              }
            });

            console.log(`[Tesla] Successfully extracted ${dealers.length} unique dealers`);
            return dealers;
          }

          return extractTeslaDealers();
        }
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Tesla Powerwall installer data.

        Tesla Powerwall certifications indicate:
        - All installers: has_battery + has_solar + has_electrical
        - Premier Installer tier = high-volume contractor
        - Many also install Solar Roof/Panels (has_solar + has_roofing)
        - Battery storage expertise = likely commercial capability
        """
        caps = DealerCapabilities()

        # All Tesla Powerwall installers have these
        caps.has_battery = True  # Powerwall is core product
        caps.has_solar = True    # Many also do Tesla Solar
        caps.has_electrical = True
        caps.has_roofing = True  # Solar Roof requires roofing work

        # Tesla installers often do both residential and commercial
        caps.is_residential = True
        caps.is_commercial = True  # Powerwall is used in both markets

        # Add Tesla OEM certification
        caps.oem_certifications.add("Tesla")
        caps.battery_oems.add("Tesla")

        # If they have solar capability (most do)
        if caps.has_solar:
            caps.inverter_oems.add("Tesla")  # Tesla Solar uses integrated inverters

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Tesla installer data to StandardizedDealer format.
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

        # If no domain but have email, extract from email
        if not domain:
            email = raw_dealer_data.get("email", "")
            if email and "@" in email:
                domain = email.split("@")[1]
                website = f"https://{domain}"

        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # All Tesla installers are Premier tier
        tier = raw_dealer_data.get("tier", "Premier Installer")

        # Get certifications
        certifications = ["Tesla Powerwall Certified", "Premier Installer"]

        # Create StandardizedDealer
        dealer = StandardizedDealer(
            name=raw_dealer_data.get("name", ""),
            phone=raw_dealer_data.get("phone", ""),
            domain=domain,
            website=website,
            street="",  # Tesla doesn't provide street address in initial results
            city="",
            state="",
            zip="",
            address_full="",
            rating=0.0,  # Tesla doesn't show ratings in results
            review_count=0,
            tier=tier,
            certifications=certifications,
            distance="",
            distance_miles=0.0,
            capabilities=capabilities,
            oem_source="Tesla",
            scraped_from_zip=zip_code,
            has_ops_maintenance=False,  # Can't determine from Tesla data
            is_resimercial=True  # Tesla Powerwall used in both markets
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print manual MCP Playwright instructions.
        """
        print(f"\n{'='*70}")
        print(f"Tesla Powerwall Installer Network Scraper - PLAYWRIGHT Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*70}\n")

        print("⚠️  MANUAL WORKFLOW - Execute these MCP Playwright tools in order:\n")

        print("1. Navigate to Tesla Powerwall installer locator:")
        print(f'   mcp__playwright__browser_navigate({{"url": "{self.DEALER_LOCATOR_URL}"}})\n')

        print("2. Wait for page to load:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("3. Enter ZIP code:")
        print(f'   mcp__playwright__browser_type({{')
        print(f'       "element": "ZIP code input",')
        print(f'       "ref": "[from snapshot]",')
        print(f'       "text": "{zip_code}"')
        print(f'   }})\n')

        print("4. Press Enter to trigger autocomplete:")
        print('   mcp__playwright__browser_press_key({"key": "Enter"})\n')

        print("5. Wait for autocomplete and results:")
        print('   mcp__playwright__browser_wait_for({"time": 3})\n')

        print("6. Scroll to load all results (Tesla uses lazy loading):")
        print('   mcp__playwright__browser_evaluate({"function": "() => window.scrollTo(0, document.body.scrollHeight)"})\n')

        print("7. Wait for lazy-loaded results:")
        print('   mcp__playwright__browser_wait_for({"time": 2})\n')

        print("8. Extract installer data:")
        extraction_script = self.get_extraction_script()
        print(f'   mcp__playwright__browser_evaluate({{"function": """{extraction_script}"""}})\n')

        print("9. Process results with:")
        print(f'   tesla_scraper.parse_results(results_json, "{zip_code}")\n')

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

        # Build workflow for Tesla
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "wait", "timeout": 3000},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "keyboard", "key": "Enter"},
            {"action": "wait", "timeout": 3000},
            # Scroll to trigger lazy loading
            {"action": "evaluate", "script": "() => window.scrollTo(0, document.body.scrollHeight)"},
            {"action": "wait", "timeout": 2000},
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

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Cloud browser with US residential proxy.

        Tesla uses enterprise-grade Akamai EdgeSuite protection AND geo-redirect.
        Browserbase with US residential proxy + fingerprint settings solves both:
        - US IP = US version of site
        - Residential proxy = bypass Akamai bot detection
        - Browser fingerprinting = avoid detection patterns

        Requires BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID in .env
        """
        from browserbase import Browserbase
        from patchright.sync_api import sync_playwright
        import time
        import random

        browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
        browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

        if not browserbase_api_key:
            raise ValueError("Missing BROWSERBASE_API_KEY in .env")
        if not browserbase_project_id:
            raise ValueError("Missing BROWSERBASE_PROJECT_ID in .env")

        print(f"\n{'='*60}")
        print(f"Tesla Powerwall Installer Scraper - BROWSERBASE Mode")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        try:
            # Initialize Browserbase client
            bb = Browserbase(api_key=browserbase_api_key, timeout=60.0)

            # Create session with residential proxy and US fingerprint
            print(f"  → Creating Browserbase session with residential proxy...")
            session = bb.sessions.create(
                project_id=browserbase_project_id,
                proxies=True,  # Enable residential proxy
                browser_settings={
                    "fingerprint": {
                        "locales": ["en-US"],
                        "screen": {"max_width": 1920, "max_height": 1080}
                    },
                    "viewport": {"width": 1920, "height": 1080}
                }
            )
            print(f"  ✓ Session created: {session.id}")

            # Connect with Patchright (stealth Playwright)
            with sync_playwright() as p:
                print(f"  → Connecting to Browserbase cloud browser...")

                # Connect via CDP using session's connect_url (official method)
                browser = p.chromium.connect_over_cdp(session.connect_url)

                # Get default context and page
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                print(f"  ✓ Connected to Browserbase (US residential proxy + stealth)")

                # Human-like delay before navigation
                time.sleep(random.uniform(1.5, 3.0))

                # Navigate to Tesla installer locator with US locale
                print(f"  → Navigating to {self.DEALER_LOCATOR_URL}")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')

                # Check for Access Denied (Akamai block)
                page_text = page.evaluate('() => document.body.innerText')
                if 'Access Denied' in page_text or 'access denied' in page_text.lower():
                    print(f"  ❌ Blocked by Akamai (Access Denied)")
                    browser.close()
                    return []

                # Wait for page to stabilize
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except:
                    pass

                time.sleep(random.uniform(3.0, 5.0))

                # Handle cookie consent if present
                print(f"  → Checking for cookie consent...")
                try:
                    accept_btn = page.locator("button:has-text('Accept'), button:has-text('Got it')").first
                    if accept_btn.is_visible(timeout=3000):
                        accept_btn.click()
                        print(f"  ✓ Accepted cookies")
                        time.sleep(1)
                except:
                    pass

                # Find and fill ZIP code input
                print(f"  → Filling ZIP code: {zip_code}")
                try:
                    zip_input = page.locator("input[placeholder*='Zip' i], input[placeholder*='ZIP' i]").first
                    zip_input.fill(zip_code, timeout=10000)
                    time.sleep(random.uniform(0.5, 1.0))
                except Exception as e:
                    print(f"  ❌ Error filling ZIP code: {e}")
                    browser.close()
                    return []

                # Press Enter to trigger autocomplete search
                print(f"  → Triggering search...")
                page.keyboard.press("Enter")

                # Wait for results to load
                print(f"  → Waiting for results...")
                time.sleep(random.uniform(4.0, 6.0))

                # Scroll to trigger lazy loading (Tesla uses infinite scroll)
                print(f"  → Scrolling to load all results...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(2.0, 3.0))

                # Execute extraction script
                print(f"  → Extracting installer data...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ⚠️ No installers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = [self.parse_dealer_data(d, zip_code) for d in raw_results]
                print(f"  ✅ Found {len(dealers)} Tesla Powerwall installers")

                browser.close()
                return dealers

        except Exception as e:
            print(f"  ❌ Browserbase error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Use Google Maps as fallback for Tesla installers.

        Since Tesla's certified installer page is blocked by Akamai (even with
        Browserbase residential proxy), we use Google Maps search as alternative.
        This finds solar/energy companies that install Tesla Powerwall.
        """
        from browserbase import Browserbase
        from patchright.sync_api import sync_playwright
        import time
        import re

        browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
        browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

        if not browserbase_api_key or not browserbase_project_id:
            print("⚠️ Browserbase credentials not set, cannot use Google Maps fallback")
            return []

        print(f"\n{'='*60}")
        print(f"Tesla Installer Scraper - GOOGLE MAPS FALLBACK")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        try:
            bb = Browserbase(api_key=browserbase_api_key)
            session = bb.sessions.create(project_id=browserbase_project_id, proxies=True)
            print(f"  ✓ Browserbase session: {session.id}")

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(session.connect_url)
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                # Search Google Maps for Tesla Powerwall installers
                url = f'https://www.google.com/maps/search/Tesla+Powerwall+certified+installer+near+{zip_code}'
                print(f"  → Searching Google Maps...")
                page.goto(url, timeout=60000)
                time.sleep(5)

                # Scroll to load more results
                for _ in range(3):
                    page.evaluate('document.querySelector("div[role=main]")?.scrollBy(0, 800)')
                    time.sleep(1)

                # Extract text content
                text = page.evaluate('() => document.body.innerText')

                # Parse phone numbers
                phones = re.findall(r'\(\d{3}\)\s*\d{3}-\d{4}', text)
                print(f"  ✓ Found {len(phones)} phone numbers")

                # Parse business data from text
                dealers = []
                lines = text.split('\n')

                current_business = {}
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue

                    # Check for business type indicators
                    if any(x in line.lower() for x in ['solar', 'power', 'energy', 'electric', 'battery']):
                        # Look for phone in nearby lines
                        phone = ''
                        for j in range(max(0, i-3), min(len(lines), i+5)):
                            phone_match = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', lines[j])
                            if phone_match:
                                phone = phone_match.group()
                                break

                        # Look for rating
                        rating = ''
                        rating_match = re.search(r'(\d+\.\d+)\s*\(\d+\)', ' '.join(lines[max(0,i-2):i+3]))
                        if rating_match:
                            rating = rating_match.group(1)

                        # Get name (usually line before business type)
                        name = lines[i-1].strip() if i > 0 else line

                        if name and len(name) > 3 and len(name) < 100:
                            if not any(x in name.lower() for x in ['search', 'map', 'google', 'directions']):
                                dealers.append({
                                    'name': name,
                                    'phone': phone.replace('(', '').replace(')', '').replace(' ', '').replace('-', ''),
                                    'rating': rating,
                                    'tier': 'Google Maps Result',
                                    'oem_source': 'Tesla (via Google Maps)'
                                })

                # Deduplicate
                seen = set()
                unique_dealers = []
                for d in dealers:
                    if d['name'] not in seen:
                        seen.add(d['name'])
                        unique_dealers.append(d)

                browser.close()

                # Convert to StandardizedDealer
                result = [self.parse_dealer_data(d, zip_code) for d in unique_dealers[:20]]
                print(f"  ✅ Found {len(result)} Tesla/Solar installers from Google Maps")

                return result

        except Exception as e:
            print(f"  ❌ Google Maps fallback error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse manual PLAYWRIGHT results.
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Tesla scraper with factory
ScraperFactory.register("Tesla", TeslaScraper)
ScraperFactory.register("tesla", TeslaScraper)
ScraperFactory.register("Tesla Powerwall", TeslaScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = TeslaScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    # RUNPOD mode (automated)
    # scraper = TeslaScraper(mode=ScraperMode.RUNPOD)
    # dealers = scraper.scrape_zip_code("94102")
    # scraper.save_json("output/tesla_installers_sf.json")
