#!/usr/bin/env python3
"""Test the enhanced multi-signal deduplication"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.base_scraper import StandardizedDealer, DealerCapabilities, BaseDealerScraper, ScraperMode

class TestScraper(BaseDealerScraper):
    """Mock scraper for testing"""
    OEM_NAME = "Test"
    DEALER_LOCATOR_URL = "test"

    def _scrape_with_playwright(self, zip_code):
        return []

    def _scrape_with_runpod(self, zip_code):
        return []

    def _scrape_with_patchright(self, zip_code):
        return []

    def detect_capabilities(self, dealer):
        """Mock implementation"""
        return dealer.capabilities

    def get_extraction_script(self):
        """Mock implementation"""
        return ""

    def parse_dealer_data(self, raw_data):
        """Mock implementation"""
        return []

def test_tri_state_dedup():
    """Test that TRI-STATE POWER & PUMP duplicates are caught"""

    scraper = TestScraper(mode=ScraperMode.PLAYWRIGHT)

    # Create the two TRI-STATE dealers from the user's example
    dealer1 = StandardizedDealer(
        name="TRI-STATE POWER & PUMP LLC",
        phone="9738753459",
        domain="",
        website="",
        street="127 PELLETOWN RD",
        city="LAFAYETTE",
        state="NJ",
        zip="07848",
        address_full="127 PELLETOWN RD LAFAYETTE, NJ 07848",
        rating=0.0,
        review_count=0,
        tier="Standard",
        certifications=[],
        distance="52.51 mi",
        distance_miles=52.51,
        oem_source="Briggs & Stratton",
        scraped_from_zip="10001",
        capabilities=DealerCapabilities()
    )

    dealer2 = StandardizedDealer(
        name="TRI-STATE POWER & PUMP",
        phone="8456745069",
        domain="tristatepowerpump.com",
        website="http://tristatepowerpump.com/",
        street="165 HARDSCRABBLE RD",
        city="PORT JERVIS",
        state="NY",
        zip="12771",
        address_full="165 HARDSCRABBLE RD PORT JERVIS, NY 12771",
        rating=0.0,
        review_count=0,
        tier="Standard",
        certifications=[],
        distance="59.8 mi",
        distance_miles=59.8,
        oem_source="Briggs & Stratton",
        scraped_from_zip="10001",
        capabilities=DealerCapabilities()
    )

    # Add more test cases
    dealer3 = StandardizedDealer(
        name="POWER SOLUTIONS INC",
        phone="5551234567",
        domain="powersolutions.com",
        website="http://powersolutions.com",
        street="123 MAIN ST",
        city="SPRINGFIELD",
        state="NJ",
        zip="07001",
        address_full="123 MAIN ST SPRINGFIELD, NJ 07001",
        rating=4.5,
        review_count=50,
        tier="Premier",
        certifications=[],
        distance="10 mi",
        distance_miles=10.0,
        oem_source="Briggs & Stratton",
        scraped_from_zip="10001",
        capabilities=DealerCapabilities()
    )

    dealer4 = StandardizedDealer(
        name="POWER SOLUTIONS INCORPORATED",  # Should match dealer3 by fuzzy name
        phone="5559876543",  # Different phone
        domain="",  # No domain
        website="",
        street="456 ELM ST",
        city="NEWARK",
        state="NJ",  # Same state
        zip="07002",
        address_full="456 ELM ST NEWARK, NJ 07002",
        rating=0.0,
        review_count=0,
        tier="Standard",
        certifications=[],
        distance="15 mi",
        distance_miles=15.0,
        oem_source="Briggs & Stratton",
        scraped_from_zip="10001",
        capabilities=DealerCapabilities()
    )

    scraper.dealers = [dealer1, dealer2, dealer3, dealer4]

    print("=" * 70)
    print("TESTING ENHANCED MULTI-SIGNAL DEDUPLICATION")
    print("=" * 70)
    print(f"\nBefore deduplication: {len(scraper.dealers)} dealers")
    print("\nDealers:")
    for i, d in enumerate(scraper.dealers, 1):
        print(f"  {i}. {d.name} | {d.state} | phone={d.phone} | domain={d.domain}")

    # Run enhanced deduplication
    scraper.deduplicate_by_phone()

    print(f"\nAfter deduplication: {len(scraper.dealers)} dealers")
    print("\nRemaining unique dealers:")
    for i, d in enumerate(scraper.dealers, 1):
        print(f"  {i}. {d.name} | {d.state} | phone={d.phone} | domain={d.domain}")

if __name__ == "__main__":
    test_tri_state_dedup()
