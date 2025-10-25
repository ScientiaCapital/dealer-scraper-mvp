"""
ABB Solar Inverter Scraper
Status: ABB EXITED SOLAR INVERTER BUSINESS (2020)

ABB sold their solar inverter division to FIMER SpA in 2020.
There is no ABB solar inverter dealer network to scrape.

Research Date: 2025-10-25
Research Summary: See /docs/commercial_inverter_oems_research.md

Key Facts:
- ABB completed divestment of solar inverter business to FIMER in 2020
- Former ABB solar inverters now sold under FIMER brand
- ABB still sells other solar products (surge protection, electrical components)
  but not inverters
- No ABB installer locator exists for solar inverters

Press Release:
https://new.abb.com/news/detail/57766/abb-completes-divestment-of-solar-inverter-business-to-fimer-spa

Next Steps (if ABB/FIMER inverters are priority):
1. Research FIMER dealer locator (separate investigation needed)
2. FIMER may have inherited ABB's former installer network
3. Check if FIMER has ZIP-searchable locator tool
"""

from typing import List
from scrapers.base_scraper import (
    BaseDealerScraper,
    DealerCapabilities,
    StandardizedDealer,
    ScraperMode
)


class ABBScraper(BaseDealerScraper):
    """
    Placeholder scraper for ABB solar inverters.

    ABB sold their solar inverter business to FIMER in 2020.
    This class exists for documentation purposes only.

    If you need FIMER inverter installers, create a separate FIMERScraper.
    """

    OEM_NAME = "ABB (Divested to FIMER 2020)"
    DEALER_LOCATOR_URL = None  # No longer exists
    PRODUCT_LINES = ["Solar Inverters (Discontinued)"]

    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT):
        """Initialize ABB scraper (will fail - business divested)"""
        # Skip parent __init__ to avoid validation error for missing DEALER_LOCATOR_URL
        self.mode = mode
        self.dealers = []

    def get_extraction_script(self) -> str:
        """Not implemented - ABB exited solar inverter business"""
        raise NotImplementedError(
            "ABB sold their solar inverter business to FIMER in 2020. "
            "No ABB solar inverter dealer network exists. "
            "\n\nSee /docs/commercial_inverter_oems_research.md for details."
            "\n\nIf you need FIMER installers, research FIMER dealer locator separately."
        )

    def detect_capabilities(self, raw_dealer_data: dict) -> DealerCapabilities:
        """Not implemented - no dealer network exists"""
        raise NotImplementedError(
            "ABB sold their solar inverter business to FIMER in 2020."
        )

    def parse_dealer_data(self, raw_dealer_data: dict, zip_code: str) -> StandardizedDealer:
        """Not implemented - no dealer network exists"""
        raise NotImplementedError(
            "ABB sold their solar inverter business to FIMER in 2020."
        )

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """Not implemented - ABB exited solar inverter business"""
        raise NotImplementedError(
            "ABB sold their solar inverter business to FIMER in 2020."
            "\n\nPress Release: https://new.abb.com/news/detail/57766/"
            "abb-completes-divestment-of-solar-inverter-business-to-fimer-spa"
            "\n\nABB no longer maintains a solar inverter installer network."
            "\n\nIf you need FIMER inverter installers:"
            "\n1. Research FIMER dealer locator (www.fimer.com or similar)"
            "\n2. FIMER may have inherited ABB's former network"
            "\n3. Create separate FIMERScraper if locator exists"
            "\n\nSee /docs/commercial_inverter_oems_research.md for details."
        )

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """Not implemented - business divested"""
        return self._scrape_with_playwright(zip_code)

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """Not implemented - business divested"""
        return self._scrape_with_playwright(zip_code)


# DO NOT register with ScraperFactory - ABB exited solar inverter business
# ScraperFactory.register("ABB", ABBScraper)

if __name__ == "__main__":
    print("=" * 80)
    print("ABB Solar Inverter Scraper")
    print("=" * 80)
    print("\nSTATUS: ABB EXITED SOLAR INVERTER BUSINESS (2020)")
    print("\nABB sold their solar inverter division to FIMER SpA in 2020.")
    print("ABB no longer maintains a solar inverter installer network.")
    print("\nPress Release:")
    print("https://new.abb.com/news/detail/57766/")
    print("abb-completes-divestment-of-solar-inverter-business-to-fimer-spa")
    print("\nIf you need FIMER inverter installers:")
    print("  1. Research FIMER dealer locator (separate investigation)")
    print("  2. FIMER may have inherited ABB's former network")
    print("  3. Create FIMERScraper if locator exists")
    print("\nSee /docs/commercial_inverter_oems_research.md for details.")
    print("=" * 80)
