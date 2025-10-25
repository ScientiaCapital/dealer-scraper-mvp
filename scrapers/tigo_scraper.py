"""
Tigo Energy Installer Scraper
Status: STATIC LIST (NOT ZIP-SEARCHABLE)

Tigo Energy provides a static global installer list at:
https://www.tigoenergy.com/installers/list

This list is NOT searchable by ZIP code and contains 40,000+ tokens of data
(hundreds/thousands of installers globally in one page).

Research Date: 2025-10-25
Research Summary: See /docs/commercial_inverter_oems_research.md

Why Generac-Style Scraper Won't Work:
- No ZIP code input field
- No AJAX search workflow
- All installers loaded at once (massive payload)
- Global list (all countries mixed)

Alternative Approaches:
1. Full page scrape → extract all installers → geocode → create ZIP index
2. Contact Tigo sales for local installer referrals
3. Use Tigo Academy training records (if accessible)

If Tigo installer data is critical, would need custom scraper architecture
(5-10x more complex than Generac approach).
"""

from typing import List
from scrapers.base_scraper import (
    BaseDealerScraper,
    DealerCapabilities,
    StandardizedDealer,
    ScraperMode
)


class TigoScraper(BaseDealerScraper):
    """
    Placeholder scraper for Tigo Energy optimizers/inverters.

    Tigo has an installer list but it's not ZIP-searchable (static global list).
    This class exists for API consistency but current methods raise NotImplementedError.

    Future Implementation:
    - Scrape full list from https://www.tigoenergy.com/installers/list
    - Parse all installers (global)
    - Geocode addresses → lat/long
    - Create ZIP code index
    - Filter by US states (SREC targeting)
    """

    OEM_NAME = "Tigo Energy"
    DEALER_LOCATOR_URL = "https://www.tigoenergy.com/installers/list"
    PRODUCT_LINES = ["TS4 Flex MLPE", "Optimizers", "EI Residential Solution", "GO Battery"]

    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT):
        """Initialize Tigo scraper"""
        super().__init__(mode)

    def get_extraction_script(self) -> str:
        """
        Not implemented - static list requires different extraction approach.

        Tigo's installer list is not ZIP-searchable. Would need to:
        1. Load entire page (40K+ tokens)
        2. Extract all installer cards
        3. Parse company name, location, contact info
        4. Geocode addresses
        5. Create own ZIP code index
        """
        raise NotImplementedError(
            "Tigo Energy installer list is not ZIP-searchable. "
            "Requires custom full-page scraping approach. "
            "See /docs/commercial_inverter_oems_research.md for details."
        )

    def detect_capabilities(self, raw_dealer_data: dict) -> DealerCapabilities:
        """
        Detect capabilities from Tigo installer data.

        Tigo-certified installers have:
        - Solar installation (core)
        - Optimizer/MLPE installation
        - Often electrical contractors
        - May have battery installation (EI Residential Solution)
        """
        caps = DealerCapabilities()

        # All Tigo installers have solar and optimizer capabilities
        caps.has_solar = True
        caps.has_inverters = True  # Tigo optimizers work with inverters
        caps.has_electrical = True  # Required for solar/optimizer install

        # Check for battery capability (EI Residential Solution)
        # This would need to be parsed from installer profile if available
        certifications = raw_dealer_data.get("certifications", [])
        if "EI Residential" in str(certifications) or "battery" in str(certifications).lower():
            caps.has_battery = True

        # Add Tigo OEM certification
        caps.oem_certifications.add("Tigo Energy")
        caps.inverter_oems.add("Tigo Energy")

        # Detect high-value contractor types
        dealer_name = raw_dealer_data.get("name", "")
        caps.detect_high_value_contractor_types(dealer_name, certifications, "")

        return caps

    def parse_dealer_data(self, raw_dealer_data: dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Tigo installer data to StandardizedDealer format.

        Note: Tigo's list doesn't provide ZIP-based search, so zip_code parameter
        would need to be matched post-scrape via geocoding.
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

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
            tier="Tigo Certified",  # Tigo doesn't have public tier system
            certifications=raw_dealer_data.get("certifications", []),
            distance="",  # Would need to calculate from geocoded data
            distance_miles=0.0,
            capabilities=capabilities,
            oem_source="Tigo Energy",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        Not implemented - Tigo list is not ZIP-searchable.

        Current implementation would require:
        1. Navigate to installer list page (one-time)
        2. Extract ALL installers (40K+ tokens of data)
        3. Parse into structured format
        4. Geocode all addresses
        5. Filter to requested ZIP code (post-scrape)

        This is fundamentally different from Generac's ZIP-search approach.
        """
        raise NotImplementedError(
            "Tigo Energy installer list is not ZIP-searchable.\n"
            "\nCurrent URL: https://www.tigoenergy.com/installers/list"
            "\nStructure: Static global list (all installers in one page)"
            "\nPage size: 40,000+ tokens"
            "\n\nTo implement:"
            "\n1. Scrape full list (one-time operation)"
            "\n2. Extract all installers globally"
            "\n3. Geocode addresses → lat/long"
            "\n4. Create ZIP code index"
            "\n5. Filter by US states (SREC targeting)"
            "\n\nComplexity: 5-10x more than Generac approach"
            "\n\nSee /docs/commercial_inverter_oems_research.md for details."
        )

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """Not implemented - see _scrape_with_playwright"""
        return self._scrape_with_playwright(zip_code)

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Not implemented - see _scrape_with_playwright"""
        return self._scrape_with_playwright(zip_code)


# DO NOT register with ScraperFactory - not functional yet
# ScraperFactory.register("Tigo", TigoScraper)

if __name__ == "__main__":
    print("=" * 80)
    print("Tigo Energy Installer Scraper")
    print("=" * 80)
    print("\nSTATUS: STATIC LIST (NOT ZIP-SEARCHABLE)")
    print("\nTigo provides installer list at:")
    print("https://www.tigoenergy.com/installers/list")
    print("\nLimitations:")
    print("  - Not searchable by ZIP code")
    print("  - Global list (all countries)")
    print("  - 40,000+ tokens of data (hundreds/thousands of installers)")
    print("\nTo implement ZIP-searchable scraper:")
    print("  1. Scrape full list (one-time)")
    print("  2. Geocode all addresses")
    print("  3. Create ZIP code index")
    print("  4. Filter by US states")
    print("\nComplexity: 5-10x more than Generac approach")
    print("\nSee /docs/commercial_inverter_oems_research.md for details.")
    print("=" * 80)
