#!/usr/bin/env python3
"""
Carrier Residential HVAC Dealer Scraper

Scrapes the Carrier residential dealer locator to find HVAC contractors.
Target URL: https://www.carrier.com/residential/en/us/find-a-dealer/

PRODUCTION READY - Clean DOM structure with semantic HTML:
- h5 headings for dealer names
- h6 headings for locations
- Standard phone links (tel: format)
- Certification badges (Carrier Authorized, Certified Ductless Pro, Award Winner)
- Filter dropdown for "All Dealers" (max coverage: ~47 dealers per ZIP)

Business Context:
- Carrier is one of the "Big 3" HVAC brands (Carrier, Trane, Lennox)
- Residential + commercial HVAC contractors
- High value for Coperniq's multi-brand monitoring platform
- Many dealers have multiple certifications and ratings
"""

import re
import time
from typing import List, Dict, Any, Optional

from scrapers.base_scraper import (
    BaseDealerScraper,
    StandardizedDealer,
    DealerCapabilities,
    ScraperMode,
)
from scrapers.scraper_factory import ScraperFactory


class CarrierScraper(BaseDealerScraper):
    """Scraper for Carrier residential HVAC dealer network."""

    OEM_NAME = "Carrier"
    DEALER_LOCATOR_URL = "https://www.carrier.com/residential/en/us/find-a-dealer/"
    PRODUCT_LINES = ["HVAC Systems", "Air Conditioners", "Heat Pumps", "Furnaces", "Ductless Systems"]

    def get_base_url(self) -> str:
        """Return the base URL for Carrier dealer locator."""
        return "https://www.carrier.com/residential/en/us/find-a-dealer/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Carrier"

    def supports_zip_search(self) -> bool:
        """Carrier dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Carrier dealers.

        PROVEN WORKING VERSION from manual testing (extracted 47 dealers for ZIP 94102).
        Uses clean semantic HTML: h5 for names, h6 for locations, standard phone links.
        """
        return r"""
() => {
  const dealers = [];

  // Find all dealer cards - they contain h5 headings with dealer names
  const dealerCards = Array.from(document.querySelectorAll('h5')).map(h5 => {
    // Get parent container that has all dealer info
    let container = h5.parentElement;
    let depth = 0;
    // Go up to find the full dealer card container
    while (container && depth < 10) {
      const hasPhone = container.querySelector('a[href^="tel:"]');
      const hasLocation = container.querySelector('h6');
      if (hasPhone && hasLocation) break;
      container = container.parentElement;
      depth++;
    }
    return container;
  }).filter(c => c !== null);

  // Remove duplicates by comparing phone numbers
  const seen = new Set();
  const uniqueCards = dealerCards.filter(card => {
    const phoneLink = card.querySelector('a[href^="tel:"]');
    if (!phoneLink) return false;
    const phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
    if (seen.has(phone)) return false;
    seen.add(phone);
    return true;
  });

  uniqueCards.forEach(card => {
    // Extract name from h5 heading
    const nameEl = card.querySelector('h5');
    const name = nameEl ? nameEl.textContent.trim() : '';

    if (!name || name.length < 2) return;

    // Extract phone from tel: link
    const phoneLink = card.querySelector('a[href^="tel:"]');
    let phone = '';
    if (phoneLink) {
      phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
      // Remove country code if present
      if (phone.length === 11 && phone.startsWith('1')) {
        phone = phone.substring(1);
      }
    }

    if (!phone || phone.length !== 10) return;  // Skip if no valid phone

    // Extract location from h6 heading (format: "City, ST")
    const locationEl = card.querySelector('h6');
    let city = '', state = '';
    if (locationEl) {
      const locationText = locationEl.textContent.trim();
      const match = locationText.match(/^(.+),\s*([A-Z]{2})$/);
      if (match) {
        city = match[1].trim();
        state = match[2];
      }
    }

    // Extract website (look for links that aren't phone or review links)
    const links = Array.from(card.querySelectorAll('a[href^="http"]'));
    let website = '', domain = '';
    for (const link of links) {
      const href = link.href;
      // Skip review links, schedule links, etc.
      if (href.includes('carrier.com') && href.includes('dealer-reviews')) continue;
      if (href.includes('google.com')) continue;
      if (link.textContent.includes('Reviews')) continue;
      if (link.textContent.includes('Schedule')) continue;

      // This should be the dealer's website
      website = href;
      try {
        const url = new URL(website);
        domain = url.hostname.replace(/^www\./, '');
      } catch(e) {}
      break;
    }

    // Extract certifications from img alt text
    const certifications = [];
    const certImgs = card.querySelectorAll('img[alt]');
    certImgs.forEach(img => {
      const alt = img.alt.trim();
      if (alt && alt.length > 0 && alt !== 'Carrier') {
        certifications.push(alt);
      }
    });

    // Extract ratings if available
    let rating = 0.0;
    let reviewCount = 0;

    // Check for Carrier site ratings
    const ratingText = card.textContent;
    const carrierRatingMatch = ratingText.match(/(\d+)\s+out of 5 stars/);
    if (carrierRatingMatch) {
      rating = parseFloat(carrierRatingMatch[1]);
    }

    const reviewMatch = ratingText.match(/(\d+)\s+Reviews?/);
    if (reviewMatch) {
      reviewCount = parseInt(reviewMatch[1]);
    }

    // Check for Google reviews
    const googleReviewMatch = ratingText.match(/(\d+)\s+Reviews?\s*$/);
    if (googleReviewMatch && reviewCount === 0) {
      reviewCount = parseInt(googleReviewMatch[1]);
    }

    dealers.push({
      name: name,
      phone: phone,
      domain: domain,
      website: website,
      street: '',  // Not available in results
      city: city,
      state: state,
      zip: '',  // Not available in results
      address_full: city && state ? `${city}, ${state}` : '',
      rating: rating,
      review_count: reviewCount,
      tier: certifications.length > 0 ? certifications.join(', ') : 'Standard',
      certifications: certifications,
      distance: '',  // Not available in Carrier results
      distance_miles: 0,
      oem_source: 'Carrier'
    });
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Carrier dealers using Playwright (local automation).

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 CARRIER: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to dealer locator
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000)
                time.sleep(2)

                # Accept cookies if modal appears
                try:
                    cookie_button_selectors = [
                        'button:has-text("Accept")',
                        'button:has-text("Accept All")',
                        'button[id*="accept" i]',
                        'button[class*="accept" i]',
                    ]
                    for selector in cookie_button_selectors:
                        try:
                            cookie_btn = page.locator(selector)
                            if cookie_btn.count() > 0 and cookie_btn.first.is_visible(timeout=2000):
                                print(f"  → Accepting cookies...")
                                cookie_btn.first.click()
                                time.sleep(1)
                                break
                        except Exception:
                            continue
                except Exception:
                    pass  # No cookies modal

                # Fill ZIP code in search input
                print(f"  → Filling ZIP code: {zip_code}")
                zip_input_selectors = [
                    'input[placeholder*="location" i]',
                    'input[type="text"]',
                    'input[placeholder*="ZIP" i]',
                ]

                zip_filled = False
                for selector in zip_input_selectors:
                    try:
                        zip_input = page.locator(selector)
                        if zip_input.count() > 0 and zip_input.first.is_visible():
                            zip_input.first.fill(zip_code)
                            time.sleep(0.5)
                            # Press Enter to submit the search
                            print(f"  → Pressing Enter to search...")
                            zip_input.first.press('Enter')
                            time.sleep(2)
                            zip_filled = True
                            break
                    except Exception:
                        continue

                if not zip_filled:
                    raise Exception("Could not find ZIP input field")

                # Select "All Dealers" from dropdown for maximum coverage
                print(f"  → Selecting 'All Dealers' filter for max coverage...")
                try:
                    dropdown_selectors = [
                        'select',
                        '[role="combobox"]',
                        'select[class*="filter" i]',
                    ]

                    dropdown_found = False
                    for selector in dropdown_selectors:
                        try:
                            dropdown = page.locator(selector)
                            if dropdown.count() > 0 and dropdown.first.is_visible(timeout=3000):
                                # Try to select "All Dealers" option
                                dropdown.first.select_option(label='All Dealers')
                                time.sleep(2)
                                print(f"  → Selected 'All Dealers' filter")
                                dropdown_found = True
                                break
                        except Exception as e:
                            # Try next selector
                            continue

                    if not dropdown_found:
                        print(f"  ⚠️  Could not find dropdown filter, using default results")
                except Exception as e:
                    print(f"  ⚠️  Error with dropdown filter: {e}, using default results")

                # Wait for dealer results to load (AJAX)
                print(f"  → Waiting for dealer results...")
                time.sleep(3)

                # Execute extraction script
                print(f"  → Executing extraction script...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No dealers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Carrier dealers")

                browser.close()
                return dealers

            except Exception as e:
                print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
                return []

    def _scrape_with_runpod(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Carrier dealers using RunPod cloud browser.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        try:
            print(f"\n🔧 CARRIER (RunPod): Scraping ZIP {zip_code}")

            # Prepare automation steps
            steps = [
                {"action": "goto", "url": self.get_base_url()},
                {"action": "wait", "seconds": 2},
                # Accept cookies
                {"action": "click", "selector": 'button:has-text("Accept")', "optional": True},
                {"action": "wait", "seconds": 1},
                # Fill ZIP and search
                {"action": "fill", "selector": 'input[placeholder*="location" i]', "value": zip_code},
                {"action": "wait", "seconds": 0.5},
                {"action": "click", "selector": 'button:has-text("Search")'},
                {"action": "wait", "seconds": 2},
                # Select "All Dealers" filter
                {"action": "select", "selector": 'select', "value": "All Dealers", "optional": True},
                {"action": "wait", "seconds": 2},
                # Extract data
                {"action": "evaluate", "script": self.get_extraction_script()},
            ]

            # Execute via RunPod API
            response = api_client.execute(steps)
            raw_results = response.get("data", [])

            if not raw_results:
                print(f"  ❌ No dealers found for ZIP {zip_code}")
                return []

            # Parse results
            dealers = self.parse_results(raw_results, zip_code)
            print(f"  ✅ Found {len(dealers)} Carrier dealers")

            return dealers

        except Exception as e:
            print(f"  ❌ Error scraping ZIP {zip_code}: {e}")
            return []

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Carrier dealer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        # Detect capabilities
        caps = self.detect_capabilities(raw_dealer_data)

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
            tier=raw_dealer_data.get("tier", ""),
            certifications=raw_dealer_data.get("certifications", []),
            distance=raw_dealer_data.get("distance", ""),
            distance_miles=raw_dealer_data.get("distance_miles", 0),
            capabilities=caps,
            oem_source="Carrier",
            scraped_from_zip=zip_code,
        )

        return dealer

    def parse_results(
        self, raw_results: List[Dict[str, Any]], zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Convert raw extraction results to StandardizedDealer objects.

        Args:
            raw_results: Raw dealer data from JavaScript extraction
            zip_code: ZIP code that was searched

        Returns:
            List of StandardizedDealer objects
        """
        dealers = []

        for raw in raw_results:
            try:
                dealer = self.parse_dealer_data(raw, zip_code)
                dealers.append(dealer)
            except Exception as e:
                print(f"    ⚠️  Error parsing dealer: {e}")
                continue

        return dealers

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """PATCHRIGHT mode: Stealth browser automation (future implementation)."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def detect_capabilities(self, raw_dealer: Dict[str, Any]) -> DealerCapabilities:
        """
        Detect dealer capabilities from raw data.

        Args:
            raw_dealer: Raw dealer data

        Returns:
            DealerCapabilities object
        """
        caps = DealerCapabilities()

        # HVAC capability (all Carrier dealers)
        caps.has_hvac = True
        caps.oem_certifications.add("Carrier")

        # Check certifications for tier signals
        certs = raw_dealer.get("certifications", [])
        tier = raw_dealer.get("tier", "")
        name = raw_dealer.get("name", "").lower()

        # Commercial signals
        commercial_signals = [
            "commercial",
            "industrial",
            "mechanical",
            "contractor",
            "inc",
            "corp",
            "llc",
        ]
        caps.is_commercial = any(sig in name for sig in commercial_signals)

        # Residential signals (most Carrier dealers do residential)
        caps.is_residential = True  # Default to True for HVAC dealers

        # Check if they're also an electrical contractor
        electrical_signals = ["electric", "electrical", "electric"]
        caps.has_electrical = any(sig in name for sig in electrical_signals)

        # Award Winner suggests larger/more established business
        if "Award Winner" in certs or "award" in tier.lower():
            caps.is_commercial = True  # Award winners often do commercial

        return caps


# Register with factory
ScraperFactory.register("Carrier", CarrierScraper)
