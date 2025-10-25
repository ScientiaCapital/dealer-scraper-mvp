"""
GoodWe Installer/Distributor Scraper

⚠️  IMPORTANT LIMITATION:
GoodWe does NOT have a ZIP code-based dealer locator like Generac.
They provide a static regional distributor directory without search functionality.

URL: https://us.goodwe.com/where-to-buy
Installer Program: https://us.goodwe.com/goodwe-plus-customer-program

This scraper provides a FRAMEWORK ONLY for when GoodWe adds a dealer locator.
Currently returns empty results with instructions to use alternative data sources.

Capabilities detected from GoodWe certification:
- Inverter installation (residential + commercial hybrid inverters)
- Solar PV system installation
- Battery energy storage (GoodWe hybrid + battery systems)
- Electrical work (required for inverter install)
"""

import os
import json
import requests
from typing import Dict, List
from scrapers.base_scraper import (
    BaseDealerScraper,
    DealerCapabilities,
    StandardizedDealer,
    ScraperMode
)
from scrapers.scraper_factory import ScraperFactory


class GoodWeScraper(BaseDealerScraper):
    """
    Scraper for GoodWe installer network.

    ⚠️  CURRENT STATUS: NON-FUNCTIONAL
    GoodWe does not provide a searchable dealer locator tool.
    They have a "Where to Buy" page with static regional distributor lists.

    GoodWe product lines in US:
    - Residential hybrid inverters (GW5000-EH, GW6000-EH, etc.)
    - Commercial inverters (MT series, SMT series)
    - Battery systems (Lynx Home series)
    - Smart energy management (SEMS portal)

    GoodWe PLUS+ Installer Program:
    - Tiered certification: PLUS+, Silver, Gold
    - Based on installation volumes and training completion
    - Installer directory is NOT publicly searchable

    Alternative data sources:
    1. Scrape static distributor list from us.goodwe.com/where-to-buy
    2. Contact GoodWe USA distributors for installer referrals
    3. Use third-party solar installer databases (EnergySage, NABCEP, etc.)
    4. LinkedIn search for "GoodWe PLUS+ installer" (requires Sales Navigator)
    """

    OEM_NAME = "GoodWe"
    DEALER_LOCATOR_URL = "https://us.goodwe.com/where-to-buy"
    PRODUCT_LINES = ["Residential Hybrid Inverters", "Commercial Inverters", "Battery Systems", "Smart Energy"]

    # Note: No selectors available (no dealer locator tool exists)
    SELECTORS = {}

    def __init__(self, mode: ScraperMode = ScraperMode.PLAYWRIGHT):
        super().__init__(mode)

        # Load RunPod config if in RUNPOD mode
        if mode == ScraperMode.RUNPOD:
            self.runpod_api_key = os.getenv("RUNPOD_API_KEY")
            self.runpod_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
            self.runpod_api_url = os.getenv(
                "RUNPOD_API_URL",
                f"https://api.runpod.ai/v2/{self.runpod_endpoint_id}/runsync"
            )

    def get_extraction_script(self) -> str:
        """
        JavaScript extraction script for GoodWe installer data.

        ⚠️  NOT IMPLEMENTED
        GoodWe does not have a searchable dealer locator.

        Returns placeholder that returns empty array.
        """
        return """
        (() => {
            // GoodWe does not have a dealer locator tool
            // They only have a static "Where to Buy" distributor directory
            console.log('GoodWe scraper: No dealer locator available');
            return [];
        })();
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from GoodWe installer/distributor data.

        GoodWe certifications indicate:
        - All installers: has_inverters + has_solar + has_electrical
        - Hybrid inverter certified: has_battery
        - GoodWe PLUS+ tiers indicate installation volume/experience:
          - PLUS+: Basic certification
          - Silver: Higher volume
          - Gold: Highest volume, premium service
        """
        caps = DealerCapabilities()

        # All GoodWe installers have inverter, solar, and electrical capabilities
        caps.has_inverters = True
        caps.has_solar = True
        caps.has_electrical = True

        # GoodWe specializes in hybrid inverters - assume battery capability
        caps.has_battery = True

        # Check for tier/certification level
        tier = raw_dealer_data.get("tier", "Standard")
        certifications_str = " ".join(raw_dealer_data.get("certifications", [])).lower()

        # Gold tier = high-volume, likely commercial capability
        if tier == "Gold" or "gold" in certifications_str:
            caps.is_commercial = True
            caps.is_residential = True

        # Silver tier = medium-volume, likely residential focus
        elif tier == "Silver" or "silver" in certifications_str:
            caps.is_residential = True

        # All GoodWe installers do residential at minimum
        caps.is_residential = True

        # Add GoodWe OEM certification
        caps.oem_certifications.add("GoodWe")
        caps.inverter_oems.add("GoodWe")
        caps.battery_oems.add("GoodWe")  # Hybrid inverters include battery

        # Detect high-value contractor types
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = raw_dealer_data.get("certifications", [])
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw GoodWe installer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script (currently empty)
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications
        certifications = raw_dealer_data.get("certifications", [])
        tier = raw_dealer_data.get("tier", "Standard")

        # Add GoodWe PLUS+ tier if present
        if tier in ["PLUS+", "Silver", "Gold"]:
            certifications.append(f"GoodWe PLUS+ {tier}")

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
            tier=tier,
            certifications=certifications,
            distance=raw_dealer_data.get("distance", ""),
            distance_miles=raw_dealer_data.get("distance_miles", 0.0),
            capabilities=capabilities,
            oem_source="GoodWe",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print limitation notice.

        GoodWe does not have a ZIP code-based dealer locator.
        """
        print(f"\n{'='*60}")
        print(f"GoodWe Installer Scraper - LIMITATION NOTICE")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  GoodWe does NOT have a US dealer locator tool\n")

        print("Alternative approaches:\n")

        print("1. Scrape static distributor directory:")
        print("   URL: https://us.goodwe.com/where-to-buy")
        print("   Returns: List of regional distributors (US, Canada, etc.)\n")

        print("2. GoodWe PLUS+ installer program (not publicly searchable):")
        print("   URL: https://us.goodwe.com/goodwe-plus-customer-program")
        print("   Tiers: PLUS+, Silver, Gold")
        print("   Note: Installer directory requires SEMS portal access\n")

        print("3. Contact GoodWe USA distributors for installer referrals:")
        print("   - Find distributors at us.goodwe.com/where-to-buy")
        print("   - Ask for certified GoodWe PLUS+ installers in your area\n")

        print("4. Use third-party solar installer databases:")
        print("   - EnergySage (energysage.com)")
        print("   - NABCEP (nabcep.org)")
        print("   - Solar Power World Top Contractors\n")

        print("5. LinkedIn Sales Navigator search:")
        print('   Query: "GoodWe PLUS+ installer" OR "GoodWe certified"')
        print("   Filter by location (state/city)\n")

        print(f"{'='*60}\n")
        print("✅ If GoodWe adds a dealer locator, update get_extraction_script()")
        print(f"{'='*60}\n")

        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Return empty list with warning.

        GoodWe does not provide a searchable dealer locator.
        """
        print(f"[GoodWe] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Not implemented (no dealer locator exists).
        """
        print(f"[GoodWe] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Not implemented (no dealer locator exists).
        """
        print(f"[GoodWe] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []


# Register GoodWe scraper with factory
ScraperFactory.register("GoodWe", GoodWeScraper)
ScraperFactory.register("goodwe", GoodWeScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (shows limitation notice)
    scraper = GoodWeScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    print("\n⚠️  RECOMMENDATION:")
    print("Do not use GoodWe scraper until they add a dealer locator tool.")
    print("Focus on OEMs with working dealer locators: Generac, Tesla (TBD), Enphase (TBD)")
    print("\nAlternative: Scrape static distributor list from us.goodwe.com/where-to-buy")
    print("Then contact distributors for installer referrals by region.")
