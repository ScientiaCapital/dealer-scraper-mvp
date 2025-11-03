#!/usr/bin/env python3
"""
York HVAC Dealer Scraper

Scrapes the York dealer locator to find HVAC contractors.
Target URL: https://www.york.com/residential-equipment/find-a-dealer

PRODUCTION READY - MetaLocator iframe-based dealer locator:
- IFRAME navigation required (locator_iframe16959)
- Country selection required: "United States" dropdown
- Clean h3 headings for dealer names
- Standard phone links (tel: format)
- Locations with Google Maps links
- Certifications: Certified Comfort Expert, Commercial Contractor, 24/7 Service, NATE Certified
- Pagination: 8 dealers per page
- Total network: 3,151 dealers

Business Context:
- York is part of Johnson Controls (same family as Coleman, Luxaire)
- Residential + commercial HVAC contractors
- Large dealer network (3,151 total dealers)
- Strong certification program
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


class YorkScraper(BaseDealerScraper):
    """Scraper for York HVAC dealer network."""

    OEM_NAME = "York"
    DEALER_LOCATOR_URL = "https://www.york.com/residential-equipment/find-a-dealer"
    PRODUCT_LINES = [
        "HVAC Systems",
        "Air Conditioners",
        "Heat Pumps",
        "Furnaces",
        "Air Handlers",
        "Packaged Systems",
        "Indoor Air Quality",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for York dealer locator."""
        return "https://www.york.com/residential-equipment/find-a-dealer"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "York"

    def supports_zip_search(self) -> bool:
        """York dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for York dealers.

        Runs inside iframe context.
        Based on manual testing - clean h3 structure for dealer names.
        """
        return r"""
() => {
  const dealers = [];

  // Find all dealer cards - they have h3 headings with dealer names
  const dealerCards = Array.from(document.querySelectorAll('h3')).map(h3 => {
    // Get parent container with full dealer info
    let container = h3.parentElement;
    let depth = 0;
    while (container && depth < 10) {
      const hasPhone = container.querySelector('a[href^="tel:"]');
      const hasLocation = container.textContent.includes('km') || container.textContent.includes('mi');
      if (hasPhone && hasLocation) break;
      container = container.parentElement;
      depth++;
    }
    return container;
  }).filter(c => c !== null);

  // Remove duplicates by phone
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
    // Extract name from h3
    const nameEl = card.querySelector('h3');
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

    if (!phone || phone.length !== 10) return;

    // Extract location from Google Maps link (format: "3040 Broadway Oakland, California 94611")
    let street = '', city = '', state = '', zip = '';
    const mapsLink = card.querySelector('a[href*="maps.google.com"]');
    if (mapsLink) {
      const locationText = mapsLink.textContent.trim();
      // Parse address: "3040 Broadway Oakland, California 94611"
      const addressMatch = locationText.match(/^(.+?)\s+([A-Z][a-z]+),\s*([A-Z][a-z]+)\s+(\d{5})$/);
      if (addressMatch) {
        street = addressMatch[1].trim();
        city = addressMatch[2];
        state = addressMatch[3];
        zip = addressMatch[4];
      } else {
        // Fallback: try city, state format
        const cityStateMatch = locationText.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d{5})/);
        if (cityStateMatch) {
          city = cityStateMatch[1];
          state = cityStateMatch[2];
          zip = cityStateMatch[3];
        }
      }
    }

    // Extract website (look for contractor's website, not York/Google links)
    const links = Array.from(card.querySelectorAll('a[href^="http"]'));
    let website = '', domain = '';
    for (const link of links) {
      const href = link.href;
      // Skip York and Google links
      if (href.includes('york.com')) continue;
      if (href.includes('google.com')) continue;

      website = href;
      try {
        const url = new URL(website);
        domain = url.hostname.replace(/^www\./, '');
      } catch(e) {}
      break;
    }

    // Extract distance (format: "14.3 km")
    let distance = '', distance_miles = 0;
    const distanceMatch = card.textContent.match(/([\d.]+)\s*(km|mi)/i);
    if (distanceMatch) {
      const distanceValue = parseFloat(distanceMatch[1]);
      const unit = distanceMatch[2].toLowerCase();

      if (unit === 'km') {
        distance_miles = distanceValue * 0.621371;  // Convert km to miles
        distance = `${distance_miles.toFixed(1)} mi`;
      } else {
        distance_miles = distanceValue;
        distance = `${distanceValue} mi`;
      }
    }

    // Extract certifications from list items
    const certifications = [];
    const listItems = card.querySelectorAll('li');
    listItems.forEach(li => {
      const text = li.textContent.trim();
      if (text && text.length > 0 && text.length < 50) {
        certifications.push(text);
      }
    });

    dealers.push({
      name: name,
      phone: phone,
      domain: domain,
      website: website,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: street && city && state ? `${street}, ${city}, ${state} ${zip}` : `${city}, ${state} ${zip}`,
      rating: 0.0,  // Not available in York results
      review_count: 0,
      tier: certifications.length > 0 ? certifications.join(', ') : 'Standard',
      certifications: certifications,
      distance: distance,
      distance_miles: distance_miles,
      oem_source: 'York'
    });
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape York dealers using Playwright (local automation).

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 YORK: Scraping ZIP {zip_code}")

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
                time.sleep(3)

                # CRITICAL: Accept cookie consent (TrustArc overlay blocks all clicks)
                print(f"  → Checking for cookie consent popup...")
                try:
                    # Find cookie consent iframe (separate from dealer locator iframe)
                    cookie_iframe_selector = 'iframe[title="Cookie Consent Notice"]'
                    cookie_iframe_element = page.wait_for_selector(cookie_iframe_selector, timeout=5000)
                    cookie_iframe = cookie_iframe_element.content_frame()

                    # Click "Accept All" button inside cookie iframe
                    accept_button = cookie_iframe.locator('button:has-text("Accept All")').first
                    accept_button.click()
                    time.sleep(2)
                    print(f"  ✅ Cookies accepted")
                except Exception:
                    # Cookie popup might not appear or already accepted
                    print(f"  → No cookie popup (already accepted)")

                # CRITICAL: Switch to iframe context
                print(f"  → Switching to iframe context...")
                iframe_selector = 'iframe[name="locator_iframe16959"]'
                try:
                    iframe_element = page.wait_for_selector(iframe_selector, timeout=10000)
                    iframe = iframe_element.content_frame()
                except Exception as e:
                    print(f"  ❌ Could not find iframe: {e}")
                    browser.close()
                    return []

                # CRITICAL: Select "United States" from country dropdown
                print(f"  → Selecting United States from country dropdown...")
                try:
                    # Use the BUTTON (styled dropdown) instead of the underlying select
                    country_button = iframe.locator('button[data-id="country"]')
                    country_button.click()
                    time.sleep(1)

                    # Select "United States" from Bootstrap dropdown menu (uses <span> in dropdown)
                    # The dropdown creates <li> items with <span> text
                    us_option = iframe.locator('.dropdown-menu.show li span:has-text("United States")').first
                    us_option.click()
                    time.sleep(1)
                    print(f"  → Selected United States")
                except Exception as e:
                    print(f"  ❌ Error selecting country: {e}")
                    browser.close()
                    return []

                # Fill ZIP code
                print(f"  → Filling ZIP code: {zip_code}")
                try:
                    # Find postal code input (within iframe)
                    zip_input = iframe.locator('input[placeholder*="postal" i], input[placeholder*="ZIP" i], input[type="text"]').first
                    zip_input.fill(zip_code)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  ❌ Error filling ZIP code: {e}")
                    browser.close()
                    return []

                # Click Search button
                print(f"  → Clicking Search button...")
                try:
                    search_button = iframe.locator('button:has-text("Search"), input[type="submit"]').first
                    search_button.click()
                    time.sleep(3)
                except Exception as e:
                    print(f"  ❌ Error clicking search: {e}")
                    browser.close()
                    return []

                # Wait for dealer results
                print(f"  → Waiting for dealer results...")
                try:
                    # Wait for h3 headings (dealer names) to appear in iframe
                    iframe.wait_for_selector('h3', timeout=10000)
                    time.sleep(2)
                except Exception:
                    print(f"  ⚠️  No dealers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Execute extraction script IN IFRAME CONTEXT
                print(f"  → Executing extraction script...")
                raw_results = iframe.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No dealers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} York dealers")

                # Count commercial contractors
                commercial_count = sum(1 for d in dealers if 'Commercial Contractor' in d.certifications)
                if commercial_count > 0:
                    print(f"     ({commercial_count} commercial contractors)")

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
        """RunPod mode not yet implemented."""
        raise NotImplementedError("RunPod mode not yet implemented for York")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw York dealer data to StandardizedDealer format.

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
            oem_source="York",
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

    def detect_capabilities(self, raw_dealer: Dict[str, Any]) -> DealerCapabilities:
        """
        Detect dealer capabilities from raw data.

        Args:
            raw_dealer: Raw dealer data

        Returns:
            DealerCapabilities object
        """
        caps = DealerCapabilities()

        # HVAC capability (all York dealers)
        caps.has_hvac = True
        caps.oem_certifications.add("York")

        # Check name and certifications for capability signals
        name = raw_dealer.get("name", "").lower()
        certs = raw_dealer.get("certifications", [])

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

        # Check certifications for commercial contractor badge
        if any("Commercial Contractor" in cert for cert in certs):
            caps.is_commercial = True

        # Residential (most York dealers)
        caps.is_residential = True

        # Check certifications for advanced qualifications
        if any("Certified Comfort Expert" in cert for cert in certs):
            caps.is_commercial = True  # Expert certification suggests larger operation

        # NATE certified (high quality signal)
        if any("NATE" in cert for cert in certs):
            caps.has_hvac = True  # Redundant but emphasizes quality

        # 24/7 Service suggests larger operation
        if any("24/7" in cert for cert in certs):
            caps.is_commercial = True

        # Electrical signals
        electrical_signals = ["electric", "electrical"]
        caps.has_electrical = any(sig in name for sig in electrical_signals)

        return caps


# Register with factory
ScraperFactory.register("York", YorkScraper)
