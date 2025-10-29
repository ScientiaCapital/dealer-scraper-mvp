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
    DEALER_LOCATOR_URL = "https://www.trane.com/residential/en/dealers/"
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
        return "https://www.trane.com/residential/en/dealers/"

    def get_brand_name(self) -> str:
        """Return the brand name."""
        return "Trane"

    def supports_zip_search(self) -> bool:
        """Trane dealer locator supports ZIP code search."""
        return True

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction for Trane dealers from TABLE format.
        
        Trane lists ALL dealers (~1,138) in a sortable table on page load.
        No ZIP search needed - extracts complete national dealer list.
        
        Table columns: Dealer Name | State | City | Zip/Postal Code | Country
        Phone numbers NOT included in table (enrichment needed).
        """
        return r"""
() => {
  const dealers = [];
  
  // Trane uses a TABLE with columns: Dealer Name | State | City | Zip/Postal Code | Country
  // No ZIP search needed - all dealers loaded on page
  const rows = Array.from(document.querySelectorAll('tr'));
  
  rows.forEach((row) => {
    const cells = Array.from(row.querySelectorAll('td, th'));
    
    // Need at least 4 cells: name, state, city, zip
    if (cells.length >= 4) {
      // First cell should have a dealer name link
      const nameLink = cells[0]?.querySelector('a');
      
      if (nameLink) {
        const name = nameLink.textContent.trim();
        
        // Skip header row
        if (name === 'Dealer Name' || name.length < 3) return;
        
        const state = cells[1]?.textContent.trim() || '';
        const city = cells[2]?.textContent.trim() || '';
        const zip = cells[3]?.textContent.trim() || '';
        const country = cells[4]?.textContent.trim() || 'US';
        
        dealers.push({
          name: name,
          phone: '',  // Not available in table view
          domain: '',
          website: '',
          street: '',
          city: city,
          state: state,
          zip: zip,
          address_full: city && state ? `${city}, ${state} ${zip}` : '',
          rating: 0.0,
          review_count: 0,
          tier: 'Standard',
          certifications: [],
          distance: '',
          distance_miles: 0,
          oem_source: 'Trane',
          country: country
        });
      }
    }
  });
  
  return dealers;
}
"""

    def _scrape_with_playwright(
        self, zip_code: str
    ) -> List[StandardizedDealer]:
        """
        Scrape Trane dealers using Playwright (local automation).
        
        NOTE: Trane lists ALL dealers in one table (no ZIP search).
        This method ignores zip_code and returns the full dealer list.
        
        Args:
            zip_code: Ignored (kept for interface compatibility)
        
        Returns:
            List of ALL Trane dealers (~1,138 dealers)
        """
        from playwright.sync_api import sync_playwright

        dealers = []

        with sync_playwright() as p:
            try:
                print(f"\n🔧 TRANE: Loading full dealer directory (ZIP search not used)")

                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navigate to dealer directory
                print(f"  → Navigating to {self.get_base_url()}")
                page.goto(self.get_base_url(), timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)  # Wait for table to fully render

                # Execute extraction script (no search needed)
                print(f"  → Extracting all dealers from table...")
                raw_results = page.evaluate(self.get_extraction_script())

                if not raw_results:
                    print(f"  ❌ No dealers found in table")
                    browser.close()
                    return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Extracted {len(dealers)} Trane dealers")

                browser.close()
                return dealers

            except Exception as e:
                print(f"  ❌ Error loading Trane dealer directory: {e}")
                import traceback
                traceback.print_exc()
                if 'browser' in locals():
                    browser.close()
                return []

                # Parse results
                dealers = self.parse_results(raw_results, zip_code)
                print(f"  ✅ Found {len(dealers)} Trane dealers")

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
