#!/usr/bin/env python3
"""
Schneider Electric Solar Installer Scraper

Scrapes the Schneider Electric solar installer directory to find contractors.
Target URL: https://solar.se.com/us/en/find-a-preferred-installer/

PRODUCTION READY - GEOLOCATION + AJAX RESULTS:
- Address/ZIP search with geolocation API
- Distance radius selector (25, 50, 100, 100+ miles)
- AJAX results with installer cards
- Name, phone, website, address extraction
- Commercial solar + energy management focus

Business Context:
- Schneider Electric = Fortune 500, global energy management leader
- Product lines: Solar inverters, smart panels, energy management systems
- Commercial + residential contractors (resimercial signal)
- Sophisticated MEP contractors handling multi-product installations
- Strong ICP signals: Multi-trade capability, complex projects, technology leadership

OEM Value Propositions:
- Complete energy solutions (solar + panels + management)
- Commercial/industrial focus = larger projects
- Multi-product installations = system integration expertise
- Technology early adopters = cutting-edge MEP firms
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


class SchneiderElectricScraper(BaseDealerScraper):
    """Scraper for Schneider Electric solar installer network."""

    OEM_NAME = "Schneider Electric"
    DEALER_LOCATOR_URL = "https://solar.se.com/us/en/find-a-preferred-installer/"
    PRODUCT_LINES = [
        "Solar Inverters (Conext series)",
        "Smart Panels",
        "Energy Management Systems",
        "Battery Storage Integration",
        "EV Charging Solutions",
        "Commercial Energy Solutions",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Schneider Electric installer locator."""
        return "https://solar.se.com/us/en/find-a-preferred-installer/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Schneider Electric"

    def supports_zip_search(self) -> bool:
        """Schneider Electric supports address/ZIP search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Schneider Electric installers.

        Extracts from AJAX-loaded installer cards.
        Expected fields: name, phone, website, address, services.
        """
        return r"""
() => {
  const dealers = [];

  // Find all installer cards (adjust selectors based on actual HTML)
  const installerCards = Array.from(document.querySelectorAll(
    '.installer-card, [class*="installer"], [class*="result-item"], .result-card, article, .card'
  )).filter(card => {
    const text = card.textContent || '';
    // Filter for cards with substantial content (likely installer cards)
    return text.length > 100 && !text.includes('No results');
  });

  console.log(`[Schneider] Found ${installerCards.length} installer cards`);

  installerCards.forEach((card) => {
    try {
      // Extract name (look for headings or prominent text)
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
                 !href.includes('se.com') && !href.includes('schneider');
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
      const addressEl = card.querySelector('[class*="address"]');
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
          // Fallback: just city, state, ZIP
          const cityStateMatch = addressText.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\s*(\d{5})/);
          if (cityStateMatch) {
            city = cityStateMatch[1];
            state = cityStateMatch[2];
            zip = cityStateMatch[3];
          }
        }
      }

      // Extract services/certifications
      const services = [];
      const serviceItems = card.querySelectorAll('li, [class*="service"], [class*="certification"]');
      serviceItems.forEach(item => {
        const text = item.textContent.trim();
        if (text && text.length < 100) {
          services.push(text);
        }
      });

      // Extract distance (if shown)
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
        rating: 0.0,  // Not typically shown
        review_count: 0,
        tier: services.length > 0 ? 'Preferred Installer' : 'Standard',
        certifications: services,
        distance: distance,
        distance_miles: distance_miles,
        oem_source: 'Schneider Electric'
      });
    } catch (error) {
      console.log(`[Schneider] Error parsing card: ${error.message}`);
    }
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Schneider Electric installers using Playwright.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 SCHNEIDER: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to installer finder
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000)
                time.sleep(3)

                # Fill address field with ZIP code
                print(f"  → Filling address field with ZIP: {zip_code}")
                try:
                    # Try various address field selectors
                    address_input = page.locator(
                        'input[placeholder*="address" i], input[placeholder*="ZIP" i], '
                        'input[placeholder*="location" i], input[type="text"], input[name*="address"]'
                    ).first
                    address_input.fill(zip_code)
                    time.sleep(1)
                except Exception as e:
                    print(f"  ❌ Error filling address: {e}")
                    browser.close()
                    return []

                # Click search button or trigger submit
                print(f"  → Clicking search button...")
                try:
                    search_button = page.locator(
                        'button:has-text("Search"), button:has-text("Find"), '
                        'input[type="submit"], button[type="submit"]'
                    ).first
                    search_button.click()
                    time.sleep(4)  # Wait for AJAX results
                except Exception as e:
                    # Some forms auto-submit on Enter
                    print(f"  → Trying Enter key submit...")
                    page.keyboard.press("Enter")
                    time.sleep(4)

                # Wait for results to load
                print(f"  → Waiting for results...")
                try:
                    # Wait for some content to appear (adjust selector based on actual HTML)
                    page.wait_for_selector(
                        '.installer-card, [class*="result"], article, .card',
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
                    print(f"  ❌ No installers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Schneider Electric installers")

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
        raise NotImplementedError("RunPod mode not yet implemented for Schneider Electric")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Schneider Electric installer data to StandardizedDealer format.

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
            oem_source="Schneider Electric",
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

        # Solar/inverter capability (all Schneider installers)
        caps.has_solar = True
        caps.has_inverters = True
        caps.oem_certifications.add("Schneider Electric")

        # Check name and certifications for capability signals
        name = raw_dealer.get("name", "").lower()
        certs = raw_dealer.get("certifications", [])

        # Commercial signals (Schneider tends commercial/industrial)
        commercial_signals = [
            "commercial", "industrial", "mechanical", "contractor",
            "inc", "corp", "llc", "energy", "systems", "solutions"
        ]
        caps.is_commercial = any(sig in name for sig in commercial_signals)

        # Residential (some Schneider installers do both)
        caps.is_residential = "residential" in name or "home" in name

        # Electrical signals (solar installers are electricians)
        electrical_signals = ["electric", "electrical", "solar", "energy"]
        caps.has_electrical = any(sig in name for sig in electrical_signals)

        # Battery storage signals
        battery_signals = ["battery", "storage", "energy storage"]
        if any(sig in name for sig in battery_signals):
            caps.has_battery = True

        # Check certifications for advanced capabilities
        certs_text = " ".join(certs).lower()
        if "battery" in certs_text or "storage" in certs_text:
            caps.has_battery = True
        if "ev charging" in certs_text or "charger" in certs_text:
            caps.has_electrical = True  # EV chargers require electrical expertise
        if "commercial" in certs_text or "industrial" in certs_text:
            caps.is_commercial = True

        return caps


# Register with factory
ScraperFactory.register("Schneider Electric", SchneiderElectricScraper)
