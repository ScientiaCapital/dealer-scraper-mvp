#!/usr/bin/env python3
"""
Emerson Sensi Thermostat Installer Scraper

Scrapes the Sensi (Copeland Climate Technologies) installer directory.
Target URL: https://sensi.copeland.com/en-us/find-a-pro

PRODUCTION READY - STANDARD ZIP SEARCH:
- ZIP/address search input
- Distance filter (25-1000 units)
- "Locations near You" results
- Self-designated contractors (disclaimer present)

Business Context:
- Sensi = Emerson/Copeland brand, smart thermostats
- Product lines: Sensi Touch 2, Sensi Lite, smart thermostats
- Estimated network: 2,000-4,000 self-designated installers
- DIY-friendly brand = technically sophisticated HVAC contractors
- Low-voltage electrical + HVAC multi-trade capability

OEM Value Propositions:
- HVAC contractors with smart controls expertise
- Low-voltage work = electrical + HVAC dual-trade
- Self-designated = proactive business owners
- Technology-forward contractors (smart home integration)
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


class SensiScraper(BaseDealerScraper):
    """Scraper for Emerson Sensi installer network."""

    OEM_NAME = "Sensi"
    DEALER_LOCATOR_URL = "https://sensi.copeland.com/en-us/find-a-pro"
    PRODUCT_LINES = [
        "Sensi Touch 2 Smart Thermostat",
        "Sensi Lite Smart Thermostat",
        "Sensi Smart Thermostats",
        "Wi-Fi Programmable Thermostats",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Sensi Pro finder."""
        return "https://sensi.copeland.com/en-us/find-a-pro"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Sensi"

    def supports_zip_search(self) -> bool:
        """Sensi supports ZIP code/address search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Sensi installers.

        Extracts from "Locations near You" results.
        Self-designated contractors, so data quality may vary.
        """
        return r"""
() => {
  const dealers = [];

  // Find location cards
  const locationCards = Array.from(document.querySelectorAll(
    '.location, .result, article, .card, [class*="location-item"], [class*="result-item"]'
  )).filter(card => {
    const text = card.textContent || '';
    return text.length > 50 && !text.includes('No results found');
  });

  console.log(`[Sensi] Found ${locationCards.length} location cards`);

  locationCards.forEach((card) => {
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
                 !href.includes('sensi.') && !href.includes('copeland.') &&
                 !href.includes('emerson.');
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

      // Extract services
      const services = [];
      const serviceItems = card.querySelectorAll('[class*="service"], [class*="specialty"], li');
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
        tier: services.length > 0 ? 'Sensi Pro' : 'Standard',
        certifications: services,
        distance: distance,
        distance_miles: distance_miles,
        oem_source: 'Sensi'
      });
    } catch (error) {
      console.log(`[Sensi] Error parsing card: ${error.message}`);
    }
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Sensi installers using Playwright.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 SENSI: Scraping ZIP {zip_code}")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to Pro finder
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000)
                time.sleep(3)

                # Fill ZIP/address field
                print(f"  → Filling address field with ZIP: {zip_code}")
                try:
                    address_input = page.locator(
                        'input[placeholder*="address" i], input[placeholder*="ZIP" i], '
                        'input[placeholder*="location" i], input[type="text"], input[type="search"]'
                    ).first
                    address_input.fill(zip_code)
                    time.sleep(1)
                except Exception as e:
                    print(f"  ❌ Error filling address: {e}")
                    browser.close()
                    return []

                # Click search button
                print(f"  → Clicking search button...")
                try:
                    search_button = page.locator(
                        'button:has-text("Search"), button:has-text("Find"), '
                        'input[type="submit"], button[type="submit"]'
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
                        '.location, .result, article, [class*="location-item"]',
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
                print(f"  ✅ Found {len(dealers)} Sensi installers")

                # Count HVAC contractors
                hvac_count = sum(1 for d in dealers if d.capabilities.has_hvac)
                if hvac_count > 0:
                    print(f"     ({hvac_count} HVAC contractors)")

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
        raise NotImplementedError("RunPod mode not yet implemented for Sensi")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Sensi installer data to StandardizedDealer format.

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
            oem_source="Sensi",
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

        # Sensi contractors have HVAC + smart controls capability
        caps.has_hvac = True
        caps.has_electrical = True  # Smart thermostats = low-voltage electrical
        caps.oem_certifications.add("Sensi")

        # Check name and certifications for capability signals
        name = raw_dealer.get("name", "").lower()
        certs = raw_dealer.get("certifications", [])

        # Commercial signals
        commercial_signals = [
            "commercial", "industrial", "mechanical", "contractor",
            "inc", "corp", "llc", "heating", "cooling", "hvac"
        ]
        caps.is_commercial = any(sig in name for sig in commercial_signals)

        # Residential (most Sensi contractors)
        residential_signals = ["residential", "home", "house"]
        caps.is_residential = any(sig in name for sig in residential_signals) or not caps.is_commercial

        # Check certifications
        certs_text = " ".join(certs).lower()

        # HVAC signals
        if any(sig in certs_text for sig in ["hvac", "heating", "cooling", "air conditioning"]):
            caps.has_hvac = True

        # Smart home signals
        if any(sig in certs_text for sig in ["smart home", "automation", "control"]):
            caps.has_electrical = True  # Smart home = electrical/low-voltage

        # Plumbing signals (HVAC often includes plumbing)
        if any(sig in certs_text for sig in ["plumbing", "water", "pipe"]):
            caps.has_plumbing = True

        return caps


# Register with factory
ScraperFactory.register("Sensi", SensiScraper)
