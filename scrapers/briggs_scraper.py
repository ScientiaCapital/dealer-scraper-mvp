"""
Briggs & Stratton Dealer Locator Scraper

Scrapes Briggs & Stratton's dealer network for standby generators and battery storage installations.
Briggs dealers are typically electrical contractors who install home backup power systems.

Target URL: https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html

Capabilities detected from Briggs & Stratton certification:
- Generator installation (standby generators)
- Battery storage systems
- Electrical work (required for installations)
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


class BriggsStrattonScraper(BaseDealerScraper):
    """
    Scraper for Briggs & Stratton dealer network.

    Briggs & Stratton dealer tiers:
    - Platinum Pro Dealer: Highest tier with advanced training and support
    - Platinum Dealer: Premium dealer with elevated service level
    - Elite IQ Installer: Battery storage specialist with advanced certification
    - Standard: Basic authorized dealer

    Note: Briggs dealers may specialize in either standby generators OR battery storage,
    unlike Generac which is generator-only. Check product type badges.
    """

    OEM_NAME = "Briggs & Stratton"
    DEALER_LOCATOR_URL = "https://energy.briggsandstratton.com/na/en_us/residential/where-to-buy/dealer-locator.html"
    PRODUCT_LINES = ["Standby Generator", "Battery Storage", "Energy Storage", "Transfer Switches"]

    # CSS Selectors
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept All')",
        "country_selector": "#dealer-country",
        "zip_input": "input[placeholder*='Zip' i], input[placeholder*='City' i]",
        "search_button": "#dealer-form button",
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
        JavaScript extraction script for Briggs & Stratton dealer data.

        Briggs uses a two-column dealer card layout:
        - Left column: Name, address, phone
        - Right column: Distance, tier badges, product type badges
        - Uses phone links as anchor points to find dealer cards
        - Address is split across two text nodes with <br> tags
        - Tier badges shown in paragraphs (e.g., "ELITE IQ INSTALLER")
        - Product types shown as img alt text ("Battery Storage", "Standby Generators")
        """
        return """
() => {
  const dealers = [];
  const phoneLinks = document.querySelectorAll('a[href^="tel:"]');

  phoneLinks.forEach(phoneLink => {
    // Find the dealer card container (has both left and right columns)
    let container = phoneLink.closest('div');
    while (container && !container.querySelector('h5')) {
      container = container.parentElement;
    }

    if (!container) return;

    // Go up one more level to get the full dealer card with both columns
    const dealerCard = container.parentElement;

    const nameEl = container.querySelector('h5');
    const phone = phoneLink.href.replace('tel:', '').replace(/\\D/g, '');

    // Get address from paragraph in left column - it has two text nodes split by <br>
    const addressPara = Array.from(container.querySelectorAll('p'))
      .find(p => {
        const text = p.textContent.trim();
        return text && /\\d+.*[A-Z]{2}\\s+\\d{5}/.test(text);
      });

    let street = '', city = '', state = '', zip = '', addressFull = '';

    if (addressPara) {
      const lines = addressPara.innerHTML.split(/<br\\s*\\/?>/i)
        .map(line => line.replace(/<[^>]*>/g, '').trim())
        .filter(line => line);

      if (lines.length >= 2) {
        street = lines[0];
        // Parse second line: "OAKLAND, CA 94608"
        const cityStateZipMatch = lines[1].match(/^([^,]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
        if (cityStateZipMatch) {
          city = cityStateZipMatch[1].trim();
          state = cityStateZipMatch[2].trim();
          zip = cityStateZipMatch[3].trim();
        }
      }

      addressFull = addressPara.textContent.trim().replace(/\\s+/g, ' ');
    }

    // Extract distance from h5 in right column (within dealerCard, not just container)
    const distanceHeading = Array.from(dealerCard.querySelectorAll('h5'))
      .find(h => h.textContent.includes('Miles'));
    const distanceMiles = distanceHeading ?
      parseFloat(distanceHeading.textContent.replace(/[^\\d.]/g, '')) : 0;
    const distance = distanceMiles ? `${distanceMiles} mi` : '';

    // Extract tier badge from all paragraphs in dealerCard
    const tierPara = Array.from(dealerCard.querySelectorAll('p'))
      .find(p => {
        const text = p.textContent.trim();
        return (text.includes('ELITE') || text.includes('IQ')) && text.includes('INSTALLER');
      });
    let tier = tierPara ? tierPara.textContent.trim() : 'Standard';

    // Extract products from img alt text in dealerCard
    const productImgs = Array.from(dealerCard.querySelectorAll('img'))
      .filter(img => img.alt && (img.alt.includes('Battery') || img.alt.includes('Generator')));
    const products = productImgs.map(img => img.alt);

    // Determine product type flags
    const hasStandbyGenerators = products.some(p => p.includes('Standby') || p.includes('Generator'));
    const hasBatteryStorage = products.some(p => p.includes('Battery') || p.includes('Storage'));

    // Extract website from non-phone links
    const websiteLink = dealerCard.querySelector('a[href^="http"]:not([href*="tel:"]):not([href*="google"]):not([href*="facebook"])');
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

    // Briggs doesn't show ratings/reviews in dealer locator
    const rating = 0;
    const reviewCount = 0;

    dealers.push({
      name: nameEl ? nameEl.textContent.trim() : '',
      phone: phone,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: addressFull,
      distance: distance,
      distance_miles: distanceMiles,
      tier: tier,
      has_standby_generators: hasStandbyGenerators,
      has_battery_storage: hasBatteryStorage,
      rating: rating,
      review_count: reviewCount,
      website: website,
      domain: domain
    });
  });

  return dealers.filter(d => d && d.name && d.phone);
}
"""

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Briggs & Stratton dealer data.

        Briggs certifications indicate:
        - All dealers: has_electrical (minimum for generator/battery install)
        - Standby Generators badge: has_generator
        - Battery Storage badge: has_battery
        - Platinum Pro/Elite IQ tiers: Higher service commitment

        Unlike Generac (generator-only), Briggs dealers may specialize in:
        1. Standby generators only
        2. Battery storage only
        3. Both (highest value for Coperniq)
        """
        caps = DealerCapabilities()

        # All Briggs dealers have electrical capability
        caps.has_electrical = True

        # Check product type badges
        has_standby = raw_dealer_data.get("has_standby_generators", False)
        has_battery = raw_dealer_data.get("has_battery_storage", False)

        if has_standby:
            caps.has_generator = True
            caps.generator_oems.add("Briggs & Stratton")

        if has_battery:
            caps.has_battery = True
            caps.battery_oems.add("Briggs & Stratton")

        # Extract tier
        tier = raw_dealer_data.get("tier", "Standard")

        # Platinum Pro and Elite IQ indicate higher capability
        tier_upper = tier.upper()
        if "PLATINUM PRO" in tier_upper or "ELITE IQ" in tier_upper:
            caps.is_residential = True
            # Elite IQ specifically for battery storage
            if "ELITE IQ" in tier_upper:
                caps.has_battery = True
                caps.battery_oems.add("Briggs & Stratton")

        # Platinum dealers indicate solid residential service
        if "PLATINUM" in tier_upper:
            caps.is_residential = True

        # Add Briggs & Stratton OEM certification
        caps.oem_certifications.add("Briggs & Stratton")

        # Detect high-value contractor types (O&M and MEP+R)
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = []
        if tier != "Standard":
            certifications_list.append(tier)
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Briggs & Stratton dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications from tier and product types
        tier = raw_dealer_data.get("tier", "Standard")
        certifications = []

        if tier != "Standard":
            certifications.append(tier)

        if raw_dealer_data.get("has_standby_generators"):
            certifications.append("Standby Generators Certified")

        if raw_dealer_data.get("has_battery_storage"):
            certifications.append("Battery Storage Certified")

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
            oem_source="Briggs & Stratton",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated scraping using local Playwright.
        
        Briggs & Stratton has a simple form (no iframe, no cascading dropdowns).
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
                print(f"  → Navigating to Briggs & Stratton dealer locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(3)

                # Handle cookie consent dialog if it appears
                print(f"  → Checking for cookie consent dialog...")
                try:
                    cookie_selectors = [
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        '#onetrust-accept-btn-handler',
                        '.onetrust-close-btn-handler',
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

                # Select "United States" in country dropdown (defaults to Mexico)
                print(f"  → Setting country to United States...")
                try:
                    country_select = page.locator('#dealer-country')
                    if country_select.count() > 0 and country_select.first.is_visible():
                        country_select.first.select_option('United States')
                        time.sleep(1)
                except Exception as e:
                    print(f"     Warning: Could not find country dropdown: {e}")

                # Fill ZIP code
                print(f"  → Filling ZIP code: {zip_code}")
                zip_input_selectors = [
                    'input[placeholder*="Zip" i]',
                    'input[placeholder*="City" i]',
                    'input[type="text"]',
                    'input[name*="zip" i]',
                ]

                zip_filled = False
                for selector in zip_input_selectors:
                    try:
                        zip_input = page.locator(selector)
                        if zip_input.count() > 0 and zip_input.first.is_visible():
                            zip_input.first.fill(zip_code)
                            time.sleep(1)
                            zip_filled = True
                            break
                    except Exception:
                        continue

                if not zip_filled:
                    raise Exception("Could not find ZIP code input")

                # Click search button
                print(f"  → Clicking search button...")
                button_selectors = [
                    '#dealer-form button',
                    'button:has-text("Search")',
                    'button:has-text("Find")',
                    'button[type="submit"]',
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
                print(f"  → Extracting dealer data...")
                extraction_script = self.get_extraction_script()
                dealers_data = page.evaluate(extraction_script)

                print(f"  → Found {len(dealers_data)} dealers")

                # Parse into StandardizedDealer objects
                dealers = self.parse_results(dealers_data, zip_code)

                browser.close()

                return dealers

            except Exception as e:
                print(f"  ✗ Error scraping with Playwright: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
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

        # Build 7-step workflow for Briggs & Stratton
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
            {"action": "select", "selector": self.SELECTORS["country_selector"], "value": "United States"},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 3000},  # 3 seconds for AJAX
            {"action": "evaluate", "script": self.get_extraction_script()},
        ]

        # Make HTTP request to RunPod API
        payload = {"input": {"workflow": workflow}}
        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping Briggs & Stratton dealers for ZIP {zip_code}...")

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
        """BROWSERBASE mode: Cloud browser automation (future implementation)."""
        raise NotImplementedError("Browserbase mode not yet implemented")

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


# Register Briggs & Stratton scraper with factory
ScraperFactory.register("Briggs & Stratton", BriggsStrattonScraper)
ScraperFactory.register("briggs", BriggsStrattonScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (manual workflow)
    scraper = BriggsStrattonScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco
