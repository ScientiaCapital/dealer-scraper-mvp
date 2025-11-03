#!/usr/bin/env python3
"""
Trane HVAC Dealer Scraper

Scrapes the Trane dealer directory to find HVAC contractors.
Target URL: https://www.trane.com/residential/en/dealers/

PRODUCTION READY - TABLE-BASED EXTRACTION (UNIQUE APPROACH):
- Lists ALL dealers in one sortable table (no ZIP search needed!)
- 1,138+ dealers extracted in single page load
- Table columns: Dealer Name | State | City | Zip/Postal Code | Country
- Phone numbers NOT available (can be enriched via Apollo/Clay later)
- Detail pages return 404s (not accessible)

Business Context:
- Trane is one of the "Big 3" HVAC brands (Carrier, Trane, Lennox)
- Owned by same parent company as Carrier (Trane Technologies)
- Residential + commercial HVAC contractors
- High-quality network, many certified dealers

IMPORTANT: This scraper extracts the FULL national dealer list (1,138+ dealers)
instead of ZIP-by-ZIP searching. Call scrape_dealers() with any ZIP code
(it will be ignored) and get the complete dealer list.
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


class TraneScraper(BaseDealerScraper):
    """Scraper for Trane HVAC dealer network."""

    OEM_NAME = "Trane"
    DEALER_LOCATOR_URL = "https://www.trane.com/residential/en/dealer-locator/"
    PRODUCT_LINES = [
        "HVAC Systems",
        "Air Conditioners",
        "Heat Pumps",
        "Furnaces",
        "Air Handlers",
        "Packaged Systems",
        "Ductless Systems",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Trane dealer locator."""
        return "https://www.trane.com/residential/en/dealer-locator/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Trane"

    def supports_zip_search(self) -> bool:
        """Trane dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Trane dealers from INTERACTIVE DEALER LOCATOR.

        FIXED VERSION - Uses interactive dealer locator (like Carrier).
        Extracts dealer cards with phone numbers, ratings, and contact info.
        """
        return r"""
() => {
  const dealers = [];
  const seen = new Set();

  // Find all dealer cards - Trane uses similar structure to Carrier/Lennox
  // Look for phone links first to identify dealer cards
  const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'));

  phoneLinks.forEach(phoneLink => {
    // Extract and normalize phone
    let phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
    if (phone.length === 11 && phone.startsWith('1')) {
      phone = phone.substring(1);
    }
    if (!phone || phone.length !== 10) return;

    // Skip duplicates
    if (seen.has(phone)) return;
    seen.add(phone);

    // Find dealer card container by traversing up from phone link
    let container = phoneLink.parentElement;
    let depth = 0;
    while (container && depth < 15) {
      const hasName = container.querySelector('h2, h3, h4, h5, a') || container.textContent.length > 50;
      if (hasName && container.textContent.includes(phone) &&
          (container.querySelector('[class*="dealer"]') || container.querySelector('[class*="location"]') ||
           container.querySelector('[class*="card"]'))) {
        break;
      }
      container = container.parentElement;
      depth++;
    }

    if (!container) return;

    // Extract dealer name - try different heading levels
    const nameEl = container.querySelector('h2, h3, h4, h5, a[class*="name"], a[class*="dealer"], strong');
    let name = '';
    if (nameEl) {
      name = nameEl.textContent.trim();
      // Clean up name (remove extra whitespace, line breaks)
      name = name.replace(/\s+/g, ' ').trim();
    }

    // Fallback: find longest text node if no name found
    if (!name || name.length < 3) {
      const textNodes = Array.from(container.querySelectorAll('*')).filter(el =>
        el.children.length === 0 && el.textContent.trim().length > 3 &&
        !el.textContent.includes(phone) && !el.textContent.match(/^\d/)
      );
      if (textNodes.length > 0) {
        name = textNodes[0].textContent.trim();
      }
    }

    if (!name || name.length < 3) return;

    // Extract location - look for city/state patterns
    const locationText = container.textContent;
    let city = '', state = '';

    // Try to find "City, ST" pattern
    const cityStateMatch = locationText.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})/);
    if (cityStateMatch) {
      city = cityStateMatch[1];
      state = cityStateMatch[2];
    } else {
      // Try to find state abbreviation
      const stateMatch = locationText.match(/\b([A-Z]{2})\b/);
      if (stateMatch) {
        state = stateMatch[1];
      }
    }

    // Extract rating and reviews
    let rating = 0.0;
    let review_count = 0;
    const ratingMatch = locationText.match(/(\d+\.?\d*)\s*\((\d+)\)/);
    if (ratingMatch) {
      rating = parseFloat(ratingMatch[1]);
      review_count = parseInt(ratingMatch[2]);
    }

    // Extract distance
    let distance = '';
    let distance_miles = 0;
    const distanceMatch = locationText.match(/(\d+\.?\d*)\s*(mi|miles)/i);
    if (distanceMatch) {
      distance_miles = parseFloat(distanceMatch[1]);
      distance = `${distance_miles} mi`;
    }

    // Extract website (if available)
    const websiteLink = container.querySelector('a[href^="http"]:not([href*="tel:"]):not([href*="trane.com"]):not([href*="google.com/maps"])');
    let website = '';
    let domain = '';
    if (websiteLink) {
      website = websiteLink.href;
      try {
        const url = new URL(website);
        domain = url.hostname.replace(/^www\./, '');
      } catch (e) {}
    }

    dealers.push({
      name: name,
      phone: phone,
      domain: domain,
      website: website,
      street: '',
      city: city || '',
      state: state || '',
      zip: '',
      address_full: city && state ? `${city}, ${state}` : city || state || '',
      rating: rating,
      review_count: review_count,
      tier: 'Standard Dealer',
      certifications: ['Trane Dealer'],
      distance: distance,
      distance_miles: distance_miles
    });
  });

  return dealers;
}
"""

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode with button clicking.

        TRANE-SPECIFIC: Phone numbers are hidden behind "Call Now" buttons.
        Must click each button to reveal phones - can't use JavaScript extraction.
        """
        from playwright.sync_api import sync_playwright
        import time
        import re

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

                # Navigate and handle cookies
                print(f"  → Navigating to Trane dealer locator...")
                page.goto(self.DEALER_LOCATOR_URL, timeout=60000, wait_until='domcontentloaded')
                time.sleep(2)

                # Dismiss cookie banner
                try:
                    cookie_btn = page.locator('button:has-text("continue")').first
                    if cookie_btn.count() > 0:
                        cookie_btn.click(timeout=2000)
                        time.sleep(1)
                except Exception:
                    pass

                # Fill ZIP and search
                print(f"  → Searching ZIP: {zip_code}")
                zip_input = page.locator('input[type="text"]').first
                zip_input.fill(zip_code)
                time.sleep(0.5)

                search_btn = page.locator('button:has-text("Search")').first
                search_btn.click()
                time.sleep(4)  # Wait for dealer cards to load

                # Get all dealer cards by heading (h2 elements contain names)
                dealer_headings = page.locator('h2').all()

                print(f"  → Found {len(dealer_headings)} potential dealers")

                for heading in dealer_headings:
                    try:
                        name = heading.inner_text().strip()
                        if not name or len(name) < 3:
                            continue

                        # Find the dealer card container (climb up DOM)
                        try:
                            container = heading.locator('xpath=..').locator('xpath=..').first
                        except:
                            container = heading.locator('xpath=..').first

                        # Click "Call Now" to reveal phone
                        phone = ''
                        try:
                            call_btns = container.locator('button').all()
                            for btn in call_btns:
                                btn_text = btn.inner_text().lower()
                                if 'call' in btn_text:
                                    btn.click(timeout=2000)
                                    time.sleep(0.3)

                                    # Extract revealed phone link
                                    phone_link = container.locator('a[href^="tel:"]').first
                                    if phone_link.count() > 0:
                                        href = phone_link.get_attribute('href')
                                        phone = re.sub(r'[^0-9]', '', href)
                                        if len(phone) == 11 and phone.startswith('1'):
                                            phone = phone[1:]
                                    break
                        except Exception:
                            pass

                        # Skip if no phone (required field)
                        if not phone or len(phone) != 10:
                            continue

                        # Extract location from paragraphs
                        city, state = '', ''
                        try:
                            paras = container.locator('p').all()
                            for p in paras:
                                text = p.inner_text().strip()
                                if ',' in text and len(text) < 100:
                                    parts = [x.strip() for x in text.split(',')]
                                    if len(parts) >= 2:
                                        city = parts[-2] if len(parts) > 2 else parts[0]
                                        state_text = parts[-1].split()[0] if parts[-1] else ''
                                        if len(state_text) == 2 and state_text.isupper():
                                            state = state_text
                                        break
                        except Exception:
                            pass

                        # Extract rating/reviews
                        rating, review_count = 0.0, 0
                        try:
                            review_btns = container.locator('button').all()
                            for btn in review_btns:
                                text = btn.inner_text()
                                if 'Google Reviews' in text:
                                    match = re.search(r'(\d+)\s+Google', text)
                                    if match:
                                        review_count = int(match.group(1))
                                    break

                            # Rating is in a generic element with just the number
                            all_text = container.inner_text()
                            rating_match = re.search(r'\b([4-5]\.\d)\b', all_text)
                            if rating_match:
                                rating = float(rating_match.group(1))
                        except Exception:
                            pass

                        dealers.append({
                            'name': name,
                            'phone': phone,
                            'domain': '',
                            'website': '',
                            'street': '',
                            'city': city,
                            'state': state,
                            'zip': '',
                            'address_full': f"{city}, {state}" if city and state else city or state or '',
                            'rating': rating,
                            'review_count': review_count,
                            'tier': 'Standard Dealer',
                            'certifications': ['Trane Dealer'],
                            'distance': '',
                            'distance_miles': 0
                        })

                    except Exception as e:
                        continue

                print(f"  → Extracted {len(dealers)} dealers with phones")

                # Parse into StandardizedDealer objects
                parsed_dealers = self.parse_results(dealers, zip_code)

                browser.close()
                return parsed_dealers

            except Exception as e:
                print(f"  ✗ Error scraping: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
                return []

    def _scrape_with_runpod(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """RunPod mode not yet implemented."""
        raise NotImplementedError("RunPod mode not yet implemented for Trane")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Trane dealer data to StandardizedDealer format.

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
            oem_source="Trane",
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

        # HVAC capability (all Trane dealers)
        caps.has_hvac = True
        caps.oem_certifications.add("Trane")

        # Check name for capability signals
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

        # Residential (most Trane dealers)
        caps.is_residential = True

        # Check certifications for tier signals
        if "Dealer of Excellence" in certs or "Comfort Specialist" in certs:
            caps.is_commercial = True  # Higher-tier dealers often do commercial

        # Electrical signals
        electrical_signals = ["electric", "electrical"]
        caps.has_electrical = any(sig in name for sig in electrical_signals)

        # High ratings suggest larger operations
        rating = raw_dealer.get("rating", 0.0)
        review_count = raw_dealer.get("review_count", 0)
        if rating >= 4.5 and review_count >= 50:
            caps.is_commercial = True

        return caps


# Register with factory
ScraperFactory.register("Trane", TraneScraper)
