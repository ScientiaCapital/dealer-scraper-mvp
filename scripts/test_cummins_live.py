#!/usr/bin/env python3
"""
Test Cummins scraper end-to-end with live scraping
"""
import json
from scrapers.cummins_scraper import CumminsScraper
from scrapers.base_scraper import ScraperMode

def test_live_scrape():
    print("="*70)
    print("CUMMINS LIVE SCRAPING TEST")
    print("="*70)

    # Create scraper
    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)

    # Test ZIP code
    test_zip = "94102"  # San Francisco

    print(f"\n1. Testing Cummins scraper on ZIP: {test_zip}")
    print("="*70)

    # Scrape dealers
    dealers = scraper.scrape_zip_code(test_zip)

    print(f"\n2. Results:")
    print(f"   Found {len(dealers)} dealers")

    if dealers:
        # Save to JSON
        output_file = f"output/cummins_live_test_{test_zip}.json"
        dealers_dict = [d.to_dict() for d in dealers]

        with open(output_file, 'w') as f:
            json.dump(dealers_dict, f, indent=2)

        print(f"   ✓ Saved to: {output_file}")

        # Show sample
        print(f"\n3. Sample dealers:")
        for i, dealer in enumerate(dealers[:3], 1):
            print(f"\n   Dealer {i}:")
            print(f"      Name: {dealer.name}")
            print(f"      Phone: {dealer.phone}")
            print(f"      Address: {dealer.address_full}")
            print(f"      City: {dealer.city}, {dealer.state} {dealer.zip}")
            print(f"      Website: {dealer.website or 'N/A'}")
            print(f"      Tier: {dealer.tier}")

        # Validation
        print(f"\n4. Validation:")
        with_name = sum(1 for d in dealers if d.name)
        with_phone = sum(1 for d in dealers if d.phone)
        with_zip = sum(1 for d in dealers if d.zip)

        print(f"   - With name: {with_name}/{len(dealers)}")
        print(f"   - With phone: {with_phone}/{len(dealers)}")
        print(f"   - With ZIP: {with_zip}/{len(dealers)}")

        if with_name == len(dealers) and with_phone == len(dealers):
            print(f"\n   ✅ LIVE TEST PASSED!")
            return True
        else:
            print(f"\n   ⚠️  Some dealers missing required fields")
            return False
    else:
        print(f"\n   ✗ No dealers found")
        return False

if __name__ == "__main__":
    success = test_live_scrape()
    exit(0 if success else 1)
