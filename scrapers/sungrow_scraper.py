"""
Sungrow Installer/Distributor Scraper

⚠️  IMPORTANT LIMITATION:
Sungrow does NOT have a US-based ZIP code dealer locator like Generac.
They provide a static global distributor directory without search functionality.

URL: https://www.sungrowpower.com/en/find-a-distributor
Alternative: https://us.sungrowpower.com/distributors

This scraper provides a FRAMEWORK ONLY for when Sungrow adds a dealer locator.
Currently returns empty results with instructions to use alternative data sources.

Capabilities detected from Sungrow certification:
- Inverter installation (residential + commercial string inverters)
- Solar PV system installation
- Battery energy storage (hybrid inverters)
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


class SungrowScraper(BaseDealerScraper):
    """
    Scraper for Sungrow installer network.

    ⚠️  CURRENT STATUS: NON-FUNCTIONAL
    Sungrow does not provide a searchable dealer locator tool.

    Sungrow product lines in US:
    - Residential inverters (SG5.0RS, SG8.0RS, SG10RS, etc.)
    - Commercial inverters (SG110CX, SG125HV, etc.)
    - Hybrid inverters with battery integration (SH5K-30, SH8K-30, etc.)
    - Energy storage systems (PowerStack, PowerTitan)

    Alternative data sources:
    1. Scrape static distributor list from us.sungrowpower.com/distributors
    2. Contact Sungrow USA directly for installer referrals
    3. Use third-party solar installer databases (EnergySage, NABCEP, etc.)
    """

    OEM_NAME = "Sungrow"
    DEALER_LOCATOR_URL = "https://www.sungrowpower.com/en/find-a-distributor"
    PRODUCT_LINES = ["Residential Inverters", "Commercial Inverters", "Hybrid Inverters", "Energy Storage"]

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
        JavaScript extraction script for Sungrow installer data.

        ⚠️  NOT IMPLEMENTED
        Sungrow does not have a searchable dealer locator.

        Returns placeholder that returns empty array.
        """
        return """
        (() => {
            // Sungrow does not have a dealer locator tool
            // Return empty array
            console.log('Sungrow scraper: No dealer locator available');
            return [];
        })();
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Sungrow installer/distributor data.

        Sungrow certifications indicate:
        - All installers: has_inverters + has_solar + has_electrical
        - Hybrid inverter certified: has_battery
        - Commercial inverters: is_commercial
        - Residential inverters: is_residential
        """
        caps = DealerCapabilities()

        # All Sungrow installers have inverter, solar, and electrical capabilities
        caps.has_inverters = True
        caps.has_solar = True
        caps.has_electrical = True

        # Check for battery/hybrid capabilities
        products = raw_dealer_data.get("products", [])
        certifications_str = " ".join(raw_dealer_data.get("certifications", [])).lower()

        if "hybrid" in certifications_str or "battery" in certifications_str or "energy storage" in certifications_str:
            caps.has_battery = True

        # Check for commercial/residential
        if "commercial" in certifications_str:
            caps.is_commercial = True

        if "residential" in certifications_str:
            caps.is_residential = True

        # Add Sungrow OEM certification
        caps.oem_certifications.add("Sungrow")
        caps.inverter_oems.add("Sungrow")

        # Battery OEMs (if hybrid/storage certified)
        if caps.has_battery:
            caps.battery_oems.add("Sungrow")

        # Detect high-value contractor types
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = raw_dealer_data.get("certifications", [])
        tier = raw_dealer_data.get("tier", "Standard")
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Sungrow installer data to StandardizedDealer format.

        Args:
            raw_dealer_data: Dict from extraction script (currently empty)
            zip_code: ZIP code that was searched

        Returns:
            StandardizedDealer object
        """
        capabilities = self.detect_capabilities(raw_dealer_data)

        # Extract certifications
        certifications = raw_dealer_data.get("certifications", [])

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
            tier=raw_dealer_data.get("tier", "Standard"),
            certifications=certifications,
            distance=raw_dealer_data.get("distance", ""),
            distance_miles=raw_dealer_data.get("distance_miles", 0.0),
            capabilities=capabilities,
            oem_source="Sungrow",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print limitation notice.

        Sungrow does not have a ZIP code-based dealer locator.
        """
        print(f"\n{'='*60}")
        print(f"Sungrow Installer Scraper - LIMITATION NOTICE")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  Sungrow does NOT have a US dealer locator tool\n")

        print("Alternative approaches:\n")

        print("1. Scrape static distributor directory:")
        print("   URL: https://us.sungrowpower.com/distributors")
        print("   Returns: List of regional distributors (not searchable by ZIP)\n")

        print("2. Contact Sungrow USA for installer referrals:")
        print("   Phone: (510) 656-1259")
        print("   Address: 47751 Fremont Blvd, Fremont, CA 94538\n")

        print("3. Use third-party solar installer databases:")
        print("   - EnergySage (energysage.com)")
        print("   - NABCEP (nabcep.org)")
        print("   - Solar Power World Top Contractors\n")

        print(f"{'='*60}\n")
        print("✅ If Sungrow adds a dealer locator, update get_extraction_script()")
        print(f"{'='*60}\n")

        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Return empty list with warning.

        Sungrow does not provide a searchable dealer locator.
        """
        print(f"[Sungrow] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Not implemented (no dealer locator exists).
        """
        print(f"[Sungrow] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Not implemented (no dealer locator exists).
        """
        print(f"[Sungrow] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []


# Register Sungrow scraper with factory
ScraperFactory.register("Sungrow", SungrowScraper)
ScraperFactory.register("sungrow", SungrowScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (shows limitation notice)
    scraper = SungrowScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    print("\n⚠️  RECOMMENDATION:")
    print("Do not use Sungrow scraper until they add a dealer locator tool.")
    print("Focus on OEMs with working dealer locators: Generac, Tesla (TBD), Enphase (TBD)")
