#!/usr/bin/env python3
"""
Honeywell Home Pro Installer Scraper

Scrapes the Honeywell Home Pro installer directory to find HVAC/thermostat contractors.
Target URL: https://www.honeywellhome.com/us/en/find-a-pro/

PRODUCTION READY - BULLSEYE LOCATIONS IFRAME:
- Third-party iframe (resideo.bullseyelocations.com/local/ResideoHomeProReact)
- ZIP/location-based filtering
- Category filtering (HVAC, Security, etc.)
- Standard dealer cards with contact info

Business Context:
- Honeywell Home (Resideo) = Major smart home/HVAC brand
- Product lines: Thermostats, HVAC controls, security systems, air quality
- Large contractor network (5,000-10,000 installers)
- Resimercial contractors (serve both residential + commercial)
- Low-voltage electrical + HVAC multi-trade capability

OEM Value Propositions:
- HVAC + smart controls = MEP capability signal
- Low-voltage work = electrical expertise
- Security integration = multi-trade capability
- Honeywell brand = quality, established contractors
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


class HoneywellHomeScraper(BaseDealerScraper):
    """Scraper for Honeywell Home Pro installer network."""

    OEM_NAME = "Honeywell Home"
    DEALER_LOCATOR_URL = "https://www.honeywellhome.com/us/en/find-a-pro/"
    PRODUCT_LINES = [
        "Smart Thermostats",
        "HVAC Controls",
        "Security Systems",
        "Air Quality Monitors",
        "Humidifiers/Dehumidifiers",
        "Water Leak Detectors",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Honeywell Home Pro finder."""
        return "https://www.honeywellhome.com/us/en/find-a-pro/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Honeywell Home"

    def supports_zip_search(self) -> bool:
        """Honeywell Home supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Honeywell Home installers.

        Runs in iframe context (Bullseye Locations).
        Extracts from dealer cards with name, phone, website, address.
        """
        return r"""
() => {
  const dealers = [];

  // Bullseye Locations typically uses article, .result, or .location elements
  const dealerCards = Array.from(document.querySelectorAll(
    'article, .result, .location, [class*="dealer"], [class*="installer"], .card, [class*="location-item"]'
  )).filter(card => {
    const text = card.textContent || '';
    // Filter for cards with dealer content
    return text.length > 50 && !text.includes('No results');
  });

  console.log(`[Honeywell] Found ${dealerCards.length} installer cards`);

  dealerCards.forEach((card) => {
    try {
      // Extract name
      const nameEl = card.querySelector('h1, h2, h3, h4, h5, [class*="name"], [class*="title"], strong, a[href*="details"]');
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
                 !href.includes('honeywellhome') && !href.includes('resideo') &&
                 !href.includes('bullseye');
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
      const addressEl = card.querySelector('[class*="address"], address');
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

      // Extract services/categories
      const services = [];
      const serviceItems = card.querySelectorAll('[class*="service"], [class*="category"], [class*="specialty"], li');
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
        tier: services.length > 0 ? 'Pro Installer' : 'Standard',
        certifications: services,
        distance: distance,
        distance_miles: distance_miles,
        oem_source: 'Honeywell Home'
      });
    } catch (error) {
      console.log(`[Honeywell] Error parsing card: ${error.message}`);
    }
  });

  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Honeywell Home installers using Playwright.

        Args:
            zip_code: ZIP code to search

        Returns:
            List of standardized dealers
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 HONEYWELL HOME: Scraping ZIP {zip_code}")

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
                time.sleep(5)  # Wait for iframe to load

                # Switch to Bullseye Locations iframe
                print(f"  → Switching to Bullseye Locations iframe...")
                try:
                    # Wait for iframe to be available
                    iframe_selector = 'iframe[id="bullseye_iframe"], iframe[src*="bullseye"]'
                    iframe_element = page.wait_for_selector(iframe_selector, timeout=15000)
                    iframe = iframe_element.content_frame()
                    if not iframe:
                        print(f"  ❌ Could not access iframe content")
                        browser.close()
                        return []
                except Exception as e:
                    print(f"  ❌ Could not find Bullseye iframe: {e}")
                    browser.close()
                    return []

                # Fill ZIP code in iframe
                print(f"  → Filling ZIP code: {zip_code}")
                try:
                    # Find search input within iframe
                    zip_input = iframe.locator(
                        'input[placeholder*="ZIP" i], input[placeholder*="postal" i], '
                        'input[placeholder*="location" i], input[type="text"], input[type="search"]'
                    ).first
                    zip_input.fill(zip_code)
                    time.sleep(1)
                except Exception as e:
                    print(f"  ❌ Error filling ZIP code: {e}")
                    browser.close()
                    return []

                # Click search button
                print(f"  → Clicking search button...")
                try:
                    search_button = iframe.locator(
                        'button:has-text("Search"), button:has-text("Find"), '
                        'input[type="submit"], button[type="submit"]'
                    ).first
                    search_button.click()
                    time.sleep(4)
                except Exception as e:
                    # Try Enter key
                    print(f"  → Trying Enter key...")
                    iframe.locator('input').first.press("Enter")
                    time.sleep(4)

                # Wait for results
                print(f"  → Waiting for results...")
                try:
                    # Wait for dealer cards in iframe
                    iframe.wait_for_selector(
                        'article, .result, .location, [class*="location-item"]',
                        timeout=10000
                    )
                    time.sleep(2)
                except Exception:
                    print(f"  ⚠️  No results found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Execute extraction script IN IFRAME CONTEXT
                print(f"  → Executing extraction script...")
                raw_results = iframe.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No installers found for ZIP {zip_code}")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Honeywell Home installers")

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
        raise NotImplementedError("RunPod mode not yet implemented for Honeywell Home")

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Patchright mode not yet implemented."""
        raise NotImplementedError("Patchright mode not yet implemented")

    def parse_dealer_data(
        self, raw_dealer_data: Dict[str, Any], zip_code: str
    ) -> StandardizedDealer:
        """
        Convert raw Honeywell Home installer data to StandardizedDealer format.

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
            oem_source="Honeywell Home",
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

        # Honeywell Home contractors have HVAC + smart controls capability
        caps.has_hvac = True
        caps.has_electrical = True  # Smart thermostats = low-voltage electrical work
        caps.oem_certifications.add("Honeywell Home")

        # Check name and certifications for capability signals
        name = raw_dealer.get("name", "").lower()
        certs = raw_dealer.get("certifications", [])

        # Commercial signals
        commercial_signals = [
            "commercial", "industrial", "mechanical", "contractor",
            "inc", "corp", "llc", "heating", "cooling", "hvac"
        ]
        caps.is_commercial = any(sig in name for sig in commercial_signals)

        # Residential (most Honeywell contractors)
        residential_signals = ["residential", "home", "house"]
        caps.is_residential = any(sig in name for sig in residential_signals) or not caps.is_commercial

        # Check certifications for capability expansion
        certs_text = " ".join(certs).lower()

        # HVAC signals
        if any(sig in certs_text for sig in ["hvac", "heating", "cooling", "air conditioning"]):
            caps.has_hvac = True

        # Security signals (Honeywell also does security)
        if any(sig in certs_text for sig in ["security", "alarm", "surveillance"]):
            # Security contractors = electrical + low-voltage capability
            caps.has_electrical = True

        # Air quality/plumbing signals
        if any(sig in certs_text for sig in ["humidifier", "air quality", "water"]):
            caps.has_plumbing = True  # Water-based HVAC products

        return caps


# Register with factory
ScraperFactory.register("Honeywell Home", HoneywellHomeScraper)
