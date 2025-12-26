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

        Extracts from DDL location finder cards.
        Structure: ddl-location-finder-card with info-left, info-right, tags
        """
        return r"""
() => {
  const dealers = [];

  // Find DDL location finder cards
  const cards = document.querySelectorAll('.ddl-location-finder-card');
  console.log(`[Sensi] Found ${cards.length} installer cards`);

  cards.forEach((card) => {
    try {
      // Get info sections
      const infoLeft = card.querySelector('.ddl-location-finder-card__info-left');
      const infoRight = card.querySelector('.ddl-location-finder-card__info-right');
      const tagsEl = card.querySelector('.ddl-location-finder-card__tags');

      if (!infoLeft) return;

      // Parse the info-left section (name + address)
      const leftText = infoLeft.innerText || '';
      const lines = leftText.split('\n').map(l => l.trim()).filter(l => l);

      // First line is the company name
      const name = lines[0] || '';
      if (!name || name.length < 3) return;

      // Address parsing from remaining lines
      let street = '', city = '', state = '', zip = '';
      if (lines.length >= 2) {
        street = lines[1] || '';
      }
      if (lines.length >= 3) {
        city = lines[2] || '';
      }
      // Last line typically has "State, US ZIP" format
      const lastLine = lines[lines.length - 1] || '';
      const stateMatch = lastLine.match(/([A-Za-z]+),?\s*US?\s*(\d{5})/);
      if (stateMatch) {
        // Map state name to abbreviation
        const stateNames = {
          'Kentucky': 'KY', 'Ohio': 'OH', 'Indiana': 'IN', 'Tennessee': 'TN',
          'Texas': 'TX', 'California': 'CA', 'Florida': 'FL', 'New York': 'NY',
          'Pennsylvania': 'PA', 'Illinois': 'IL', 'Michigan': 'MI', 'Georgia': 'GA'
        };
        const stateName = stateMatch[1];
        state = stateNames[stateName] || stateName.substring(0, 2).toUpperCase();
        zip = stateMatch[2];
      }

      // Extract distance from info-right
      let distance = '', distance_miles = 0;
      if (infoRight) {
        const rightText = infoRight.innerText || '';
        const distMatch = rightText.match(/([\d.]+)\s*mi/);
        if (distMatch) {
          distance_miles = parseFloat(distMatch[1]);
          distance = `${distance_miles} mi`;
        }
      }

      // Extract tags (Contractor, Distributor, etc.)
      const tags = [];
      if (tagsEl) {
        const tagSpans = tagsEl.querySelectorAll('span, div');
        tagSpans.forEach(span => {
          const tag = span.textContent.trim();
          if (tag && tag.length > 2 && tag.length < 50) {
            tags.push(tag);
          }
        });
      }

      // Determine tier based on tags
      const isContractor = tags.some(t => t.toLowerCase().includes('contractor'));
      const isDistributor = tags.some(t => t.toLowerCase().includes('distributor'));
      let tier = 'Standard';
      if (isContractor && isDistributor) {
        tier = 'Contractor + Distributor';
      } else if (isContractor) {
        tier = 'Contractor';
      } else if (isDistributor) {
        tier = 'Distributor';
      }

      dealers.push({
        name: name,
        phone: '',  // Phone not visible in list view
        domain: '',
        website: '',
        street: street,
        city: city,
        state: state,
        zip: zip,
        address_full: `${street}, ${city}, ${state} ${zip}`.replace(/^,\s*/, ''),
        rating: 0.0,
        review_count: 0,
        tier: tier,
        certifications: tags,
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
                    # Target the visible "Enter Location" input specifically
                    # The page has hidden search inputs that match before the visible one
                    address_input = page.locator(
                        'input[placeholder="Enter Location"], '
                        'input[placeholder*="Location" i]:visible, '
                        'input[placeholder*="address" i]:visible, '
                        'input[placeholder*="ZIP" i]:visible'
                    ).first
                    address_input.wait_for(state='visible', timeout=10000)
                    address_input.fill(zip_code)
                    time.sleep(1)
                except Exception as e:
                    print(f"  ❌ Error filling address: {e}")
                    browser.close()
                    return []

                # Handle Google Places autocomplete
                print(f"  → Waiting for autocomplete suggestions...")
                try:
                    # Wait for Google Places autocomplete to appear
                    autocomplete = page.locator('.pac-container .pac-item').first
                    autocomplete.wait_for(state='visible', timeout=5000)
                    time.sleep(0.5)

                    # Click the first suggestion
                    print(f"  → Selecting first autocomplete suggestion...")
                    autocomplete.click()
                    time.sleep(2)
                except Exception as e:
                    # Fallback: Try search button or Enter key
                    print(f"  → Autocomplete not found, trying search button...")
                    try:
                        search_button = page.locator(
                            'button:has-text("Search"), button:has-text("Find"), '
                            'input[type="submit"], button[type="submit"]'
                        ).first
                        search_button.click()
                        time.sleep(4)
                    except Exception:
                        print(f"  → Trying Enter key...")
                        page.keyboard.press("Enter")
                        time.sleep(4)

                # Wait for results
                print(f"  → Waiting for results...")
                try:
                    page.wait_for_selector(
                        '.ddl-location-finder-card, .ddl-location-finder__result-cards',
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
