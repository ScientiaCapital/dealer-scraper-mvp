"""
Growatt Installer/Distributor Scraper

⚠️  IMPORTANT LIMITATION:
Growatt does NOT have a US-based ZIP code dealer locator like Generac.
They do not provide a public searchable installer directory.

Main URL: https://us.growatt.com/
Products: https://us.growatt.com/products

This scraper provides a FRAMEWORK ONLY for when Growatt adds a dealer locator.
Currently returns empty results with instructions to use alternative data sources.

Capabilities detected from Growatt certification:
- Inverter installation (residential + commercial string inverters)
- Solar PV system installation
- Battery energy storage (Growatt hybrid inverters + battery systems)
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


class GrowattScraper(BaseDealerScraper):
    """
    Scraper for Growatt installer network.

    ⚠️  CURRENT STATUS: NON-FUNCTIONAL
    Growatt does not provide a searchable dealer locator OR public installer directory.

    Growatt product lines in US:
    - Residential inverters (MIN series, MIC series)
    - Hybrid inverters (SPH series, MOD series)
    - Battery systems (ARK series)
    - Commercial inverters (MAX series)
    - Off-grid systems (SPF series)

    Growatt certification:
    - Accredited Installer Training Program exists
    - Required for warranty support
    - BUT: No public directory of certified installers

    Alternative data sources:
    1. Contact Growatt USA directly for installer referrals
    2. Contact US distributors (Signature Solar, ShopSolar, CSE Solar USA)
    3. Use third-party solar installer databases (EnergySage, NABCEP, etc.)
    4. LinkedIn search for "Growatt installer" or "Growatt distributor"
    """

    OEM_NAME = "Growatt"
    DEALER_LOCATOR_URL = "https://us.growatt.com/"  # No actual dealer locator exists
    PRODUCT_LINES = ["Residential Inverters", "Hybrid Inverters", "Commercial Inverters", "Battery Systems", "Off-Grid"]

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
        JavaScript extraction script for Growatt installer data.

        ⚠️  NOT IMPLEMENTED
        Growatt does not have a searchable dealer locator OR public installer directory.

        Returns placeholder that returns empty array.
        """
        return """
        (() => {
            // Growatt does not have a dealer locator tool
            // They do not provide a public installer directory
            console.log('Growatt scraper: No dealer locator or installer directory available');
            return [];
        })();
        """

    def detect_capabilities(self, raw_dealer_data: Dict) -> DealerCapabilities:
        """
        Detect capabilities from Growatt installer/distributor data.

        Growatt certifications indicate:
        - All installers: has_inverters + has_solar + has_electrical
        - Hybrid inverter certified: has_battery
        - Off-grid systems: has_battery (critical for off-grid)
        - Commercial inverters: is_commercial
        """
        caps = DealerCapabilities()

        # All Growatt installers have inverter, solar, and electrical capabilities
        caps.has_inverters = True
        caps.has_solar = True
        caps.has_electrical = True

        # Check for battery/hybrid capabilities
        products = raw_dealer_data.get("products", [])
        certifications_str = " ".join(raw_dealer_data.get("certifications", [])).lower()

        if any(keyword in certifications_str for keyword in ["hybrid", "battery", "ark", "sph", "off-grid"]):
            caps.has_battery = True

        # Check for commercial/residential
        if "commercial" in certifications_str or "max series" in certifications_str:
            caps.is_commercial = True

        if "residential" in certifications_str or "min series" in certifications_str or "mic series" in certifications_str:
            caps.is_residential = True

        # Default to residential (most Growatt installations)
        if not caps.is_commercial and not caps.is_residential:
            caps.is_residential = True

        # Add Growatt OEM certification
        caps.oem_certifications.add("Growatt")
        caps.inverter_oems.add("Growatt")

        # Battery OEMs (if hybrid/storage certified)
        if caps.has_battery:
            caps.battery_oems.add("Growatt")

        # Detect high-value contractor types
        dealer_name = raw_dealer_data.get("name", "")
        certifications_list = raw_dealer_data.get("certifications", [])
        tier = raw_dealer_data.get("tier", "Standard")
        caps.detect_high_value_contractor_types(dealer_name, certifications_list, tier)

        return caps

    def parse_dealer_data(self, raw_dealer_data: Dict, zip_code: str) -> StandardizedDealer:
        """
        Convert raw Growatt installer data to StandardizedDealer format.

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
            oem_source="Growatt",
            scraped_from_zip=zip_code,
        )

        return dealer

    def _scrape_with_playwright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PLAYWRIGHT mode: Print limitation notice.

        Growatt does not have a ZIP code-based dealer locator OR public installer directory.
        """
        print(f"\n{'='*60}")
        print(f"Growatt Installer Scraper - LIMITATION NOTICE")
        print(f"ZIP Code: {zip_code}")
        print(f"{'='*60}\n")

        print("⚠️  Growatt does NOT have a US dealer locator tool OR public installer directory\n")

        print("Alternative approaches:\n")

        print("1. Contact Growatt USA directly:")
        print("   Website: https://us.growatt.com/")
        print("   Email: service.na@growatt.com")
        print("   Request: Certified installer referrals for your ZIP code\n")

        print("2. Contact US distributors for installer referrals:")
        print("   - Signature Solar (signaturesolar.com) - Phone: TBD")
        print("   - ShopSolar (shopsolarkits.com) - Phone: (877) 242-2792")
        print("   - CSE Solar USA (csesolarusa.com) - Phone: (702) 608-8385")
        print("   - Meico Solar (meicosolar.com)")
        print("   - Growatt USA Distribution Center (Ontario, CA)\n")

        print("3. Use third-party solar installer databases:")
        print("   - EnergySage (energysage.com)")
        print("   - NABCEP (nabcep.org)")
        print("   - Solar Power World Top Contractors\n")

        print("4. LinkedIn Sales Navigator search:")
        print('   Query: "Growatt installer" OR "Growatt distributor" OR "Growatt certified"')
        print("   Filter by location (state/city)\n")

        print("5. Check DIY solar forums/communities:")
        print("   - DIY Solar Power Forum (diysolarforum.com)")
        print("   - Growatt community support")
        print("   Ask: \"Who are reputable Growatt installers in [your state]?\"\n")

        print(f"{'='*60}\n")
        print("✅ If Growatt adds a dealer locator, update get_extraction_script()")
        print(f"{'='*60}\n")

        return []

    def _scrape_with_runpod(self, zip_code: str) -> List[StandardizedDealer]:
        """
        RUNPOD mode: Return empty list with warning.

        Growatt does not provide a searchable dealer locator.
        """
        print(f"[Growatt] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_browserbase(self, zip_code: str) -> List[StandardizedDealer]:
        """
        BROWSERBASE mode: Not implemented (no dealer locator exists).
        """
        print(f"[Growatt] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []

    def _scrape_with_patchright(self, zip_code: str) -> List[StandardizedDealer]:
        """
        PATCHRIGHT mode: Not implemented (no dealer locator exists).
        """
        print(f"[Growatt] ⚠️  No dealer locator available - skipping ZIP {zip_code}")
        return []


# Register Growatt scraper with factory
ScraperFactory.register("Growatt", GrowattScraper)
ScraperFactory.register("growatt", GrowattScraper)


# Example usage
if __name__ == "__main__":
    # PLAYWRIGHT mode (shows limitation notice)
    scraper = GrowattScraper(mode=ScraperMode.PLAYWRIGHT)
    scraper.scrape_zip_code("94102")  # San Francisco

    print("\n⚠️  RECOMMENDATION:")
    print("Do not use Growatt scraper until they add a dealer locator tool.")
    print("Focus on OEMs with working dealer locators: Generac, Tesla (TBD), Enphase (TBD)")
    print("\nAlternative: Contact Growatt distributors (Signature Solar, ShopSolar, CSE Solar USA)")
    print("for installer referrals by region.")
