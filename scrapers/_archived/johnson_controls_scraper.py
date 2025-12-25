#!/usr/bin/env python3
"""
Johnson Controls Representative Finder Scraper

Scrapes the Johnson Controls rep/dealer locator to find commercial HVAC/building automation contractors.
Target URL: https://www.johnsoncontrols.com/find-a-rep

PRODUCTION READY - AUTOCOMPLETE LOCATION SEARCH:
- Automated location search with autocomplete (US/Canada only)
- JCI-US branded locations filtering
- Commercial HVAC + building automation focus
- Representative/dealer contact info

Business Context:
- Johnson Controls = Fortune 500 global building technologies leader
- Product lines: HVAC equipment, building automation, controls, fire safety, security
- Different from York (JCI residential division) - this targets COMMERCIAL
- Estimated network: 3,000-5,000 commercial reps/dealers
- Large-scale commercial/industrial projects ($100K-$1M+)

OEM Value Propositions:
- **COMMERCIAL HVAC = resimercial contractors** (high ICP value)
- Building automation = MEP+R multi-trade systems integrators
- Controls = electrical + HVAC + networking capability
- JCI projects = ongoing O&M service contracts
- Technology sophistication = cutting-edge MEP firms
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


class JohnsonControlsScraper(BaseDealerScraper):
    """Scraper for Johnson Controls commercial representative network."""

    OEM_NAME = "Johnson Controls"
    DEALER_LOCATOR_URL = "https://www.johnsoncontrols.com/find-a-rep"
    PRODUCT_LINES = [
        "Commercial HVAC Equipment",
        "Building Automation Systems",
        "HVAC Controls",
        "Fire Safety Systems",
        "Security Systems",
        "Energy Management",
        "Industrial Refrigeration",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Johnson Controls rep finder."""
        return "https://www.johnsoncontrols.com/find-a-rep"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Johnson Controls"

    def supports_zip_search(self) -> bool:
        """Johnson Controls supports location search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Johnson Controls representatives.

        Extracts from location cards with name, phone, website, address.
        JCI-US branded locations only (US/Canada filtering).
        """
        return r"""
() => {
  const dealers = [];

  // Find location/representative cards
  const repCards = Array.from(document.querySelectorAll(
    '.location, .rep, .result, article, .card, [class*="location-item"], [class*="rep-card"]'
  )).filter(card => {
    const text = card.textContent || '';
    return text.length > 50 && !text.includes('No locations found');
  });

  console.log(`[JCI] Found ${repCards.length} representative cards`);

  repCards.forEach((card) => {
    try {
      // Extract name
      const nameEl = card.querySelector('h1, h2, h3, h4, h5, [class*="name"], [class*="title"], strong');
      const name = nameEl ? nameEl.textContent.trim() : '';

      if (!name || name.length < 3) return;

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

      // Extract website
      const websiteLink = Array.from(card.querySelectorAll('a[href^="http"]'))
        .find(link => {
          const href = link.href;
          return !href.includes('google') && !href.includes('facebook') &&
                 !href.includes('johnsoncontrols.com');
        });
      const website = websiteLink ? websiteLink.href : '';
      let domain = '';
      if (website) {
        try {
          const url = new URL(website);
          domain = url.hostname.replace(/^www\./, '');
        } catch(e) {}
      }

      // Extract address
      let street = '', city = '', state = '', zip = '';
      const addressEl = card.querySelector('[class*="address"], address, [class*="location-address"]');
      if (addressEl) {
        const addressText = addressEl.textContent.trim();
        // Parse address patterns
        const addressMatch = addressText.match(/^(.+?),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\s*(\d{5})/);
        if (addressMatch) {
          street = addressMatch[1].trim();
          city = addressMatch[2];
          state = addressMatch[3];
          zip = addressMatch[4];
        } else {
          // Fallback: city, state, ZIP
          const cityStateMatch = addressText.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\s*(\d{5})/);
          if (cityStateMatch) {
            city = cityStateMatch[1];
            state = cityStateMatch[2];
            zip = cityStateMatch[3];
          }
        }
      }

      // Extract services/specialties
      const services = [];
      const serviceItems = card.querySelectorAll('[class*="service"], [class*="specialty"], [class*="product"], li');
      serviceItems.forEach(item => {
        const text = item.textContent.trim();
        if (text && text.length < 100 && !text.includes('miles') && !text.includes('km')) {
          services.push(text);
        }
      });

      // Extract distance
      let distance = '', distance_miles = 0;
      const distanceMatch = card.textContent.match(/([\d.]+)\s*(mi|miles|km)/i);
      if (distanceMatch) {
        const value = parseFloat(distanceMatch[1]);
        const unit = distanceMatch[2].toLowerCase();
        if (unit.includes('km')) {
          distance_miles = value * 0.621371;
          distance = `${distance_miles.toFixed(1)} mi`;
        } else {
          distance_miles = value;
          distance = `${value} mi`;
        }
      }

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
        rating: 0.0,
        review_count: 0,
        tier: services.length > 0 ? 'JCI Representative' : 'Standard',
        certifications: services,
        distance: distance,
        distance_miles: distance_miles,
        oem_source: 'Johnson Controls'
      });
    } catch (error) {
      console.log(`[JCI] Error parsing card: ${error.message}`);
    }
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Johnson Controls representatives using Playwright.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 JOHNSON CONTROLS: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to rep finder
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000)
                time.sleep(4)  # Wait for location search tool to load

                # Fill location search
                print(f"  → Filling location search with ZIP: {zip_code}")
                try:
                    # Find search input (may have autocomplete)
                    search_input = page.locator(
                        'input[placeholder*="location" i], input[placeholder*="ZIP" i], '
                        'input[placeholder*="search" i], input[type="text"], input[type="search"]'
                    ).first
                    search_input.fill(zip_code)
                    time.sleep(2)  # Wait for autocomplete suggestions
                except Exception as e:
                    print(f"  ❌ Error filling location: {e}")
                    browser.close()
                    return []

                # Click search button or submit
                print(f"  → Clicking search button...")
                try:
                    search_button = page.locator(
                        'button:has-text("Search"), button:has-text("Find"), '
                        'input[type="submit"], button[type="submit"], button[class*="search"]'
                    ).first
                    search_button.click()
                    time.sleep(4)
                except Exception as e:
                    # Try Enter key
                    print(f"  → Trying Enter key...")
                    page.keyboard.press("Enter")
                    time.sleep(4)

                # Wait for results
                print(f"  → Waiting for results...")
                try:
                    page.wait_for_selector(
                        '.location, .rep, .result, article, [class*="location-item"]',
                        timeout=10000
                    )
                    time.sleep(2)
                except Exception:
                    print(f"  ⚠️  No results found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Execute extraction script
                print(f"  → Executing extraction script...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No representatives found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Johnson Controls representatives")

                # Count commercial contractors
                commercial_count = sum(1 for d in dealers if d.capabilities.is_commercial)
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

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """RunPod mode not yet implemented."""
        raise NotImplementedError("RunPod mode not yet implemented for Johnson Controls")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Johnson Controls rep data to StandardizedDealer format.

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
            oem_source="Johnson Controls",
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

        # Johnson Controls = commercial HVAC + building automation
        caps.has_hvac = True
        caps.has_electrical = True  # Building controls = electrical work
        caps.is_commercial = True  # JCI is commercial-focused
        caps.oem_certifications.add("Johnson Controls")

        # Check name and certifications for capability signals
        name = raw_dealer.get("name", "").lower()
        certs = raw_dealer.get("certifications", [])

        # Commercial/industrial signals (JCI is commercial by default)
        commercial_signals = [
            "commercial", "industrial", "mechanical", "contractor",
            "systems", "solutions", "building", "automation"
        ]
        if any(sig in name for sig in commercial_signals):
            caps.is_commercial = True  # Reinforce

        # Residential (rare for JCI, but possible)
        if "residential" in name or "home" in name:
            caps.is_residential = True

        # Check certifications for capability expansion
        certs_text = " ".join(certs).lower()

        # Building automation signals
        if any(sig in certs_text for sig in ["automation", "control", "BAS", "BMS"]):
            caps.has_electrical = True  # Controls = electrical
            caps.is_commercial = True  # Building automation = commercial

        # Fire safety signals
        if any(sig in certs_text for sig in ["fire", "safety", "alarm"]):
            caps.has_electrical = True  # Fire systems = electrical/low-voltage

        # Security signals
        if any(sig in certs_text for sig in ["security", "access control"]):
            caps.has_electrical = True  # Security = electrical/low-voltage

        # Energy management signals
        if any(sig in certs_text for sig in ["energy", "efficiency", "management"]):
            caps.has_hvac = True  # Energy management includes HVAC optimization
            caps.has_electrical = True  # Energy management includes electrical systems

        # HVAC equipment signals
        if any(sig in certs_text for sig in ["hvac", "heating", "cooling", "refrigeration"]):
            caps.has_hvac = True

        return caps


# Register with factory
ScraperFactory.register("Johnson Controls", JohnsonControlsScraper)
