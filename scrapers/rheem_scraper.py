#!/usr/bin/env python3
"""
Rheem HVAC Professional Scraper

Scrapes Rheem's "Find a Pro" dealer locator for HVAC contractors.
Target URL: https://www.rheem.com/find-a-pro/

PRODUCTION READY - Includes BOTH residential AND commercial contractors:
- Clean h3 headings for contractor names
- Standard phone links (tel: format)
- Distance in miles
- Ratings and review counts
- Default URL parameters include commercial: bACComm=true, bWHComm=true

Business Context:
- Rheem is a major HVAC + water heating brand
- "Find a Pro" locator includes residential + commercial contractors
- Target markets: HVAC systems, water heaters, tankless, hybrid systems
- Commercial contractors = resimercial signal for Coperniq
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


class RheemScraper(BaseDealerScraper):
    """Scraper for Rheem HVAC professional network."""

    OEM_NAME = "Rheem"
    DEALER_LOCATOR_URL = "https://www.rheem.com/find-a-pro/"
    PRODUCT_LINES = [
        "HVAC Systems",
        "Air Conditioners",
        "Heat Pumps",
        "Furnaces",
        "Water Heaters",
        "Tankless Water Heaters",
        "Hybrid Water Heaters",
        "Commercial HVAC",
        "Commercial Water Heating",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Rheem dealer locator."""
        return "https://www.rheem.com/find-a-pro/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Rheem"

    def supports_zip_search(self) -> bool:
        """Rheem dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Rheem professionals.

        Based on manual testing (71 professionals for ZIP 30309).
        Clean h3 structure similar to Carrier.

        URL parameters for commercial inclusion (already default):
        - bACComm=true (Commercial Air Conditioning)
        - bWHComm=true (Commercial Water Heating)
        """
        return r"""
() => {
  const professionals = [];

  // Find all professional cards - they contain h3 headings with contractor names
  const professionalCards = Array.from(document.querySelectorAll('h3')).map(h3 => {
    // Get parent container that has all contractor info
    let container = h3.parentElement;
    let depth = 0;
    // Go up to find the full professional card container
    while (container && depth < 10) {
      const hasPhone = container.querySelector('a[href^="tel:"]');
      const hasDistance = container.textContent.includes('miles');
      if (hasPhone && hasDistance) break;
      container = container.parentElement;
      depth++;
    }
    return container;
  }).filter(c => c !== null);

  // Remove duplicates by comparing phone numbers
  const seen = new Set();
  const uniqueCards = professionalCards.filter(card => {
    const phoneLink = card.querySelector('a[href^="tel:"]');
    if (!phoneLink) return false;
    const phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
    if (seen.has(phone)) return false;
    seen.add(phone);
    return true;
  });

  uniqueCards.forEach(card => {
    // Extract name from h3 heading
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

    if (!phone || phone.length !== 10) return;  // Skip if no valid phone

    // Extract distance (format: "16.26 miles")
    let distance = '', distance_miles = 0;
    const distanceMatch = card.textContent.match(/([\d.]+)\s*miles?/i);
    if (distanceMatch) {
      distance = distanceMatch[0];
      distance_miles = parseFloat(distanceMatch[1]);
    }

    // Extract website (look for http/https links that aren't tel or internal Rheem links)
    const links = Array.from(card.querySelectorAll('a[href^="http"]'));
    let website = '', domain = '';
    for (const link of links) {
      const href = link.href;
      // Skip Rheem internal links
      if (href.includes('rheem.com/find-a-pro')) continue;
      if (href.includes('rheem.com/booking')) continue;

      // This should be the contractor's website
      website = href;
      try {
        const url = new URL(website);
        domain = url.hostname.replace(/^www\./, '');
      } catch(e) {}
      break;
    }

    // Extract rating and review count (format: "(4.96) 1237 reviews")
    let rating = 0.0;
    let reviewCount = 0;

    // Look for rating pattern: "(4.96) 1237 reviews"
    const ratingMatch = card.textContent.match(/\(([\d.]+)\)\s*(\d+)\s*reviews?/i);
    if (ratingMatch) {
      rating = parseFloat(ratingMatch[1]);
      reviewCount = parseInt(ratingMatch[2]);
    }

    // Extract booking URL (format: "/find-a-pro/booking/contractor-name-city-state")
    let bookingUrl = '';
    const bookingLink = card.querySelector('a[href*="/booking/"]');
    if (bookingLink) {
      bookingUrl = bookingLink.href;
    }

    // Detect if contractor does commercial work from name
    const nameLower = name.toLowerCase();
    const isCommercial = nameLower.includes('commercial') ||
                        nameLower.includes('industrial') ||
                        nameLower.includes('mechanical');

    professionals.push({
      name: name,
      phone: phone,
      domain: domain,
      website: website,
      street: '',  // Not available in results
      city: '',    // Not available in results (could parse from booking URL)
      state: '',   // Not available in results
      zip: '',     // Not available in results
      address_full: '',
      rating: rating,
      review_count: reviewCount,
      tier: rating >= 4.5 ? 'Highly Rated' : 'Standard',
      certifications: [],  // Not explicitly shown in Rheem results
      distance: distance,
      distance_miles: distance_miles,
      booking_url: bookingUrl,
      is_commercial: isCommercial,
      oem_source: 'Rheem'
    });
  });

  return professionals;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Rheem professionals using Playwright (local automation).

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 RHEEM: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Build URL with all parameters (residential + commercial)
                # These params are from the default "All Contractors" preset
                url_params = {
                    'PostalCode': zip_code,
                    'Radius': '25',
                    'bHeatCool': 'true',      # Residential Heating & Cooling
                    'bWHRes': 'true',         # Residential Water Heating
                    'bACComm': 'true',        # COMMERCIAL Air Conditioning
                    'bWHComm': 'true',        # COMMERCIAL Water Heating
                    'bWHTankless': 'true',    # Tankless Water Heaters
                    'bSolarWH': 'true',       # Solar Water Heaters
                    'bHybridWH': 'true',      # Hybrid Water Heaters
                    'bPoolSpa': 'true',       # Pool & Spa
                    'preset': 'all'
                }

                # Construct full URL
                param_string = '&'.join([f"{k}={v}" for k, v in url_params.items()])
                full_url = f"{self.get_base_url()}?{param_string}"

                # Navigate to dealer locator
                print(f"  → Navigating to Rheem dealer locator with ZIP {zip_code}")
                page.goto(full_url, timeout=60000)
                time.sleep(3)  # Wait for results to load

                # Wait for professional results to appear
                print(f"  → Waiting for professional results...")
                try:
                    # Wait for h3 headings (contractor names)
                    page.wait_for_selector('h3', timeout=10000)
                except Exception:
                    print(f"  ⚠️  No professionals found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Execute extraction script
                print(f"  → Executing extraction script...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No professionals found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Rheem professionals")

                # Count commercial contractors
                commercial_count = sum(1 for d in dealers if d.capabilities.is_commercial)
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
        """
        Scrape Rheem professionals using RunPod cloud browser.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        raise NotImplementedError("RunPod mode not yet implemented for Rheem")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """PATCHRIGHT mode: Stealth browser automation (future implementation)."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Rheem professional data to StandardizedDealer format.

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
            oem_source="Rheem",
            scraped_from_zip=zip_code,
        )

        return dealer

    def parse_results(
        self, raw_results: List[Dict[str, Any]], zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Convert raw extraction results to StandardizedDealer objects.

        Args:
            raw_results: Raw professional data from JavaScript extraction
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
                print(f"    ⚠️  Error parsing professional: {e}")
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

        # HVAC capability (all Rheem professionals)
        caps.has_hvac = True
        caps.oem_certifications.add("Rheem")

        # Check name for capability signals
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

        # Use flag from extraction if available
        if raw_dealer.get("is_commercial"):
            caps.is_commercial = True

        # Residential signals (most Rheem pros do residential)
        caps.is_residential = True  # Default to True

        # Check if they're also plumbing (Rheem does water heaters)
        plumbing_signals = ["plumbing", "plumber"]
        caps.has_plumbing = any(sig in name for sig in plumbing_signals)

        # Check if they're also electrical
        electrical_signals = ["electric", "electrical"]
        caps.has_electrical = any(sig in name for sig in electrical_signals)

        # High ratings suggest established/larger business
        rating = raw_dealer.get("rating", 0.0)
        review_count = raw_dealer.get("review_count", 0)
        if rating >= 4.5 and review_count >= 100:
            caps.is_commercial = True  # High-rated with many reviews likely do commercial

        return caps


# Register with factory
ScraperFactory.register("Rheem", RheemScraper)
