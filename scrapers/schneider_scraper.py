#!/usr/bin/env python3
"""
Schneider Electric EcoXpert System Integrator Scraper

Scrapes the Schneider Electric EcoXpert network to find certified contractors/installers.
Target URL: https://www.se.com/us/en/locate/5-find-a-system-integrator-ecoxpert

NOTE (Nov 2025):
- Old solar.se.com URL discontinued (404)
- The /locate/257-us-distributor-locator is for DISTRIBUTORS (suppliers like Graybar, Home Depot)
- EcoXpert locator has actual INSTALLERS/CONTRACTORS who do building automation
- Uses Svelte-based UI with Google Places autocomplete (must click autocomplete result)

Page Structure:
- Svelte-based UI with pl-* class prefixes
- Google Places autocomplete for address search
- Must click autocomplete result (not just Enter) to trigger search
- Results show company name, city, distance

Certifications Available:
- EcoXpert Building Automation (Certified/Master)
- EcoXpert Building Security (Certified/Master)
- EcoXpert Power Distribution (Master)
- EcoXpert Power Management (Certified/Master)
- EcoXpert Critical IT Infrastructure (Master)

Business Context:
- Schneider Electric = Fortune 500, global energy management leader
- EcoXperts are certified system integrators who INSTALL (not just sell)
- Commercial building automation + power management focus
- Strong ICP signals: Multi-trade capability, complex projects, technology leadership

OEM Value Propositions:
- Building automation integration expertise
- Power distribution and management projects
- Commercial/industrial focus = larger projects
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
    """Scraper for Schneider Electric EcoXpert system integrator network."""

    OEM_NAME = "Schneider Electric"
    DEALER_LOCATOR_URL = "https://www.se.com/us/en/locate/5-find-a-system-integrator-ecoxpert"
    PRODUCT_LINES = [
        "Building Automation Systems",
        "Building Security Systems",
        "Power Distribution",
        "Power Management",
        "Critical IT Infrastructure",
        "Energy Monitoring",
    ]

    def get_base_url(self) -> str:
        """Return the base URL for Schneider Electric EcoXpert locator."""
        return "https://www.se.com/us/en/locate/5-find-a-system-integrator-ecoxpert"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Schneider Electric"

    def supports_zip_search(self) -> bool:
        """Schneider Electric supports address/ZIP search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Schneider Electric EcoXpert system integrators.

        EcoXpert page uses Svelte-based UI with company name, city, and distance.
        Results appear as text blocks after search, not structured cards.
        """
        return r"""
() => {
  const dealers = [];
  const body = document.body.innerText;
  const lines = body.split('\n').map(l => l.trim()).filter(l => l);

  // Find where results section starts (after "X Results")
  let resultStartIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\d+\s*Results?$/i.test(lines[i])) {
      resultStartIdx = i;
      break;
    }
  }

  if (resultStartIdx === -1) {
    console.log('[Schneider] No results section found');
    return dealers;
  }

  // Parse results - format is: Company Name, City, Distance
  let i = resultStartIdx + 1;
  while (i < lines.length && dealers.length < 100) {
    const line = lines[i];

    // Skip menu/filter items
    if (line.startsWith('Sort by') || line.startsWith('Search by') ||
        line.startsWith('Filter') || line.startsWith('Zip code') ||
        line.startsWith('Distance') || line.length < 3) {
      i++;
      continue;
    }

    // Check if this looks like a company name
    const isCompanyName = /Inc\.?|LLC|Corp\.?|Associates|Systems|Solutions|Technologies|Integration|Automation/i.test(line) ||
                          (line.length > 5 && /^[A-Z]/.test(line) && !/^\d/.test(line) && !line.includes('EcoXpert'));

    if (isCompanyName && i + 2 < lines.length) {
      const cityLine = lines[i + 1];
      const distanceLine = lines[i + 2];

      // Check if we have city and distance pattern
      // City is typically just a city name, distance is "XX km" or "XX mi"
      const distanceMatch = distanceLine.match(/([\d.]+)\s*(km|mi)/i) ||
                           cityLine.match(/([\d.]+)\s*(km|mi)/i);

      if (distanceMatch || (cityLine && !cityLine.includes('Results') && !cityLine.includes('Sort'))) {
        let distance_miles = 0;
        let distance = '';

        if (distanceMatch) {
          const value = parseFloat(distanceMatch[1]);
          const unit = distanceMatch[2].toLowerCase();
          if (unit === 'km') {
            distance_miles = value * 0.621371;
            distance = `${distance_miles.toFixed(1)} mi`;
          } else {
            distance_miles = value;
            distance = `${value} mi`;
          }
        }

        // Extract city (first line after company that's not a distance)
        let city = '';
        if (!cityLine.match(/^\d/)) {
          city = cityLine.replace(/,.*$/, '').trim();
        }

        dealers.push({
          name: line,
          phone: '',
          domain: '',
          website: '',
          street: '',
          city: city,
          state: '',  // State not shown in results
          zip: '',
          address_full: city,
          rating: 0.0,
          review_count: 0,
          tier: 'EcoXpert',
          certifications: ['EcoXpert Certified'],
          distance: distance,
          distance_miles: distance_miles,
          oem_source: 'Schneider Electric'
        });

        i += 3;
        continue;
      }
    }

    i++;
  }

  console.log(`[Schneider] Extracted ${dealers.length} EcoXpert integrators`);
  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Schneider Electric EcoXpert system integrators using Playwright.

        The EcoXpert page uses a Svelte-based UI with Google Places autocomplete.
        Must click the autocomplete result (not just press Enter) to trigger search.

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

                # Navigate to EcoXpert locator
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000)
                time.sleep(4)

                # Accept cookie banner first (blocks visibility of elements)
                try:
                    cookie_btn = page.query_selector("#onetrust-accept-btn-handler")
                    if cookie_btn and cookie_btn.is_visible():
                        print(f"  → Accepting cookies...")
                        cookie_btn.click()
                        time.sleep(2)
                except Exception:
                    pass  # Cookie banner may not be present

                # Find the VISIBLE search input (class='qds-input')
                print(f"  → Finding search input for ZIP: {zip_code}")
                visible_input = None

                # Try multiple times as Svelte may still be loading
                for attempt in range(3):
                    inputs = page.query_selector_all("input[placeholder='Search by address']")
                    for inp in inputs:
                        if inp.is_visible():
                            visible_input = inp
                            break
                    if visible_input:
                        break
                    time.sleep(2)

                if visible_input:
                    # Fill ZIP code and wait for autocomplete
                    visible_input.click()
                    visible_input.fill(zip_code)
                    print(f"  → Waiting for autocomplete...")
                    time.sleep(2)

                    # Click the autocomplete result (REQUIRED - Enter doesn't work)
                    autocomplete_result = page.query_selector(".pl-result-item button")
                    if autocomplete_result:
                        print(f"  → Clicking autocomplete result...")
                        autocomplete_result.click()
                        time.sleep(5)  # Wait for results to load
                    else:
                        print(f"  ⚠️  No autocomplete result found, trying Enter...")
                        visible_input.press("Enter")
                        time.sleep(5)
                else:
                    print(f"  ⚠️  No search input found, extracting all visible results...")
                    time.sleep(2)  # Allow page to settle

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
