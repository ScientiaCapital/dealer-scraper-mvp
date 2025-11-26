"""
Lennox HVAC Dealer Locator Scraper

Scrapes Lennox's dealer network for HVAC contractors (heating, cooling, air quality).
Lennox dealers are typically full-service HVAC contractors who install residential and commercial systems.

Target URL: https://www.lennox.com/residential/locate/

**Commercial Value:**
Lennox dealers represent high-value resimercial prospects because:
- Multi-trade capabilities (HVAC, electrical, often plumbing)
- Both residential and commercial focus
- Premium equipment installations ($10K-$50K+ systems)
- Often multi-brand certified (Coperniq's core ICP)
- O&M services (maintenance contracts = recurring revenue)

Capabilities detected from Lennox certification:
- HVAC installation (furnaces, AC, heat pumps)
- Commercial HVAC (rooftop units, VRF systems)
- Residential HVAC (whole-home comfort systems)
- Air quality (filtration, ventilation, IAQ products)
- Electrical work (required for HVAC install)
- Often also install generators, solar (energy-efficient homes)

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


class LennoxScraper(BaseDealerScraper):
    """
    Scraper for Lennox HVAC dealer network.

    Lennox dealer tiers:
    - Dave Lennox Premier Dealer: Top-tier certification with enhanced service
    - Standard Dealer: Basic Lennox certification

    Lennox is one of the "Big 3" HVAC brands (Lennox, Trane, Carrier).
    Dealers handle both residential and commercial installations.
    """

    OEM_NAME = "Lennox"
    DEALER_LOCATOR_URL = "https://www.lennox.com/residential/locate/"
    PRODUCT_LINES = ["HVAC", "Heating", "Cooling", "Air Quality", "Furnaces", "Air Conditioners", "Heat Pumps"]

    # CSS Selectors - TBD based on site inspection
    SELECTORS = {
        "cookie_accept": "button:has-text('Accept')",
        "zip_input": "input[type='text'], input[placeholder*='ZIP' i], input[placeholder*='location' i]",
        "search_button": "button:has-text('Search'), button[type='submit']",
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
        JavaScript extraction script for Lennox dealer data.

        WORKING VERSION - Tested with ZIP 94102 (San Francisco).
        Extracts from Google Maps-style dealer cards with name, phone, location, rating, tier.

        Example dealer:
        - Name: "Contra Costa Heating & Air Conditioning"
        - Phone: "341-299-3061"
        - Location: "San Leandro | 14.6 miles"
        - Rating: 3.9 (102 reviews)
        - Tier: "lennox premium dealer"
        """
        return """
() => {
  const dealers = [];
  const seen = new Set();

  // FIXED: Find all dealer cards by their wrapper class instead of traversing from phone
  const dealerCards = Array.from(document.querySelectorAll('.lnx-dealer-card'));

  dealerCards.forEach(card => {
    // Extract name using CSS class (CRITICAL FIX: name is in sibling, not phone container)
    const nameElement = card.querySelector('a.dealer-name');
    const name = nameElement ? nameElement.textContent.trim() : '';

    if (!name || name.length < 3) return;

    // Extract phone
    const phoneLink = card.querySelector('a[href^="tel:"]');
    if (!phoneLink) return;

    let phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
    if (phone.length === 11 && phone.startsWith('1')) {
      phone = phone.substring(1);
    }
    if (!phone || phone.length !== 10) return;
    if (seen.has(phone)) return;
    seen.add(phone);

    // Extract city and distance using CSS classes
    const cityElement = card.querySelector('.dealer-city');
    const city = cityElement ? cityElement.textContent.trim() : '';

    const distanceElement = card.querySelector('.dealer-distance');
    const distanceText = distanceElement ? distanceElement.textContent.trim() : '';
    const distanceMatch = distanceText.match(/([\\d.]+)\\s*miles/i);
    const distance_miles = distanceMatch ? parseFloat(distanceMatch[1]) : 0;
    const distance = distance_miles ? `${distance_miles} mi` : '';

    // Extract rating and review count
    const ratingElement = card.querySelector('.dealer-rating');
    const ratingText = ratingElement ? ratingElement.textContent.trim() : '';
    const ratingMatch = ratingText.match(/([\\d.]+)\\s*\\((\\d+)\\)/);
    const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0.0;
    const review_count = ratingMatch ? parseInt(ratingMatch[2]) : 0;

    // Extract tier from image alt text or wrapper class
    let tier = 'Standard Dealer';
    const tierImage = card.querySelector('img.mb-2, img.mb-lg-3');
    if (tierImage && tierImage.alt) {
      const altText = tierImage.alt.toLowerCase();
      if (altText.includes('premier') || altText.includes('premium')) {
        tier = 'Lennox Premier Dealer';
      } else if (altText.includes('elite')) {
        tier = 'Lennox Elite Dealer';
      }
    }

    // Check wrapper class for tier info
    const wrapper = card.closest('.lnx-dealer-card-wrapper');
    if (wrapper) {
      if (wrapper.classList.contains('premier-dealer') || wrapper.classList.contains('premium-dealer')) {
        tier = 'Lennox Premier Dealer';
      } else if (wrapper.classList.contains('elite-dealer')) {
        tier = 'Lennox Elite Dealer';
      }
    }

    // Extract website (if available)
    const websiteLink = card.querySelector('a[href^="http"]:not([href*="tel:"]):not([href*="google.com/maps"]):not([href*="facebook.com"]):not([href*="lennox.com"])');
    let website = '';
    let domain = '';
    if (websiteLink) {
      website = websiteLink.href;
      try {
        const url = new URL(website);
        domain = url.hostname.replace(/^www\\./, '');
      } catch (e) {}
    }

    // Try to extract state (2-letter uppercase)
    const cardText = card.textContent;
    const stateMatch = cardText.match(/\\b([A-Z]{2})\\b/);
    const state = stateMatch ? stateMatch[1] : '';

    dealers.push({
      name: name,
      phone: phone,
      domain: domain,
      website: website,
      street: '',  // Not available in results
      city: city || '',
      state: state || '',
      zip: '',  // Not available in results
      address_full: city && state ? `${city}, ${state}` : city,
      rating: rating,
      review_count: review_count,
      tier: tier,
      certifications: [tier],
      distance: distance,
      distance_miles: distance_miles
    });
  });

  return dealers;
}
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Lennox dealer data.

        Lennox dealers typically have:
        - HVAC installation (all dealers)
        - Electrical work (required for HVAC)
        - Both residential and commercial capabilities
        - Multi-trade skills (especially Premier Dealers)
        """
        caps = DealerCapabilities()

        # All Lennox dealers have HVAC capabilities
        caps.has_hvac = True
        caps.has_electrical = True  # Required for HVAC install

        # Lennox dealers serve both markets
        caps.is_residential = True
        caps.is_commercial = True  # Most Lennox dealers do commercial too

        # Detect high-value contractor types
        dealer_name = raw_dealer_data.get("name", "").lower()
        tier = raw_dealer_data.get("tier", "Standard Dealer")
        certifications = raw_dealer_data.get("certifications", [])

        # Premier Dealers are more sophisticated contractors
        if "premier" in tier.lower():
            caps.is_commercial = True
            caps.is_residential = True

        # Add OEM certification
        caps.oem_certifications.add("Lennox")

        # Detect high-value contractor types (O&M and MEP+R)
        caps.detect_high_value_contractor_types(dealer_name, certifications, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Lennox dealer data to StandardizedDealer format.
        """
        # Detect capabilities
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications/tier
        tier = raw_dealer_data.get("tier", "Standard Dealer")
        certifications = raw_dealer_data.get("certifications", [])
        if not certifications:
            certifications = ["Lennox Dealer"]

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
            oem_source="Lennox",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Automated scraping using local Playwright.

        Lennox has a simple Google Maps-style dealer locator (no iframe, no complex forms).
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
                print(f"  → Navigating to Lennox dealer locator...")
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

                # Fill ZIP code and submit
                print(f"  → Filling ZIP code: {zip_code}")
                zip_input_selectors = [
                    'input[type="text"]',
                    'input[placeholder*="ZIP" i]',
                    'input[placeholder*="location" i]',
                    'input[name*="zip" i]',
                ]

                zip_filled = False
                for selector in zip_input_selectors:
                    try:
                        zip_input = page.locator(selector)
                        if zip_input.count() > 0 and zip_input.first.is_visible():
                            # Fill ZIP and press Enter to trigger search
                            zip_input.first.fill(zip_code)
                            time.sleep(0.5)
                            print(f"  → Pressing Enter to search...")
                            zip_input.first.press('Enter')
                            zip_filled = True
                            break
                    except Exception:
                        continue

                if not zip_filled:
                    # Fallback: Try clicking search icon if Enter didn't work
                    print(f"  → Trying search icon click...")
                    try:
                        search_icon = page.locator('img[alt*="search" i]')
                        if search_icon.count() > 0:
                            search_icon.first.click()
                            time.sleep(1)
                        else:
                            raise Exception("Could not find ZIP input or search icon")
                    except Exception as e:
                        raise Exception(f"Could not submit search: {e}")

                # Wait for results (Google Maps style loads quickly)
                print(f"  → Waiting for results...")
                time.sleep(5)

                # PAGINATION LOOP - Extract dealers from all pages
                all_dealers_data = []
                page_num = 1
                extraction_script = self.get_extraction_script()

                while True:
                    # Extract dealers from current page
                    print(f"  → Extracting dealers from page {page_num}...")
                    dealers_data = page.evaluate(extraction_script)
                    print(f"     Found {len(dealers_data)} dealers on page {page_num}")

                    all_dealers_data.extend(dealers_data)

                    # Check if "Next" button exists and is clickable
                    try:
                        next_btn = page.locator('#next-group')
                        if next_btn.count() > 0 and next_btn.is_visible():
                            # Check if button is disabled (last page)
                            is_disabled = next_btn.evaluate('el => el.classList.contains("disabled") || el.hasAttribute("disabled")')
                            if not is_disabled:
                                print(f"     Clicking Next to page {page_num + 1}...")
                                next_btn.click(timeout=5000)
                                time.sleep(3)  # Wait for new page to load
                                page_num += 1
                                continue
                    except Exception:
                        pass

                    # No more pages - break loop
                    print(f"  → Pagination complete: {page_num} pages, {len(all_dealers_data)} total dealers")
                    break

                # Parse into StandardizedDealer objects
                dealers = self.parse_results(all_dealers_data, zip_code)

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
        """RUNPOD mode: Execute automated scraping via serverless API."""
        if not self.runpod_api_key or not self.runpod_endpoint_id:
            raise ValueError(
                "Missing RunPod credentials. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env"
            )

        # Build workflow for Lennox (simple 6-step)
        workflow = [
            {"action": "navigate", "url": self.DEALER_LOCATOR_URL},
            {"action": "click", "selector": self.SELECTORS["cookie_accept"]},
            {"action": "fill", "selector": self.SELECTORS["zip_input"], "text": zip_code},
            {"action": "click", "selector": self.SELECTORS["search_button"]},
            {"action": "wait", "timeout": 5000},  # 5 seconds for results
            {"action": "evaluate", "script": self.get_extraction_script()},
        ]

        # Make HTTP request to RunPod API
        payload = {"input": {"workflow": workflow}}
        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"[RunPod] Scraping Lennox dealers for ZIP {zip_code}...")

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

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """PATCHRIGHT mode: Stealth browser automation (future implementation)."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_results(self, results_json: List[Dict], zip_code: str) -> List[StandardizedDealer]:
        """
        Helper method to parse PLAYWRIGHT results.

        Args:
            results_json: Array of dealer objects from browser_evaluate
            zip_code: ZIP code that was searched

        Returns:
            List of StandardizedDealer objects
        """
        dealers = [self.parse_dealer_data(d, zip_code) for d in results_json]
        self.dealers.extend(dealers)
        return dealers


# Register Lennox scraper with factory
ScraperFactory.register("Lennox", LennoxScraper)
ScraperFactory.register("lennox", LennoxScraper)
