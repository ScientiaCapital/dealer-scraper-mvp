#!/usr/bin/env python3
"""
Test Cummins extraction script against captured HTML
"""
import json
from playwright.sync_api import sync_playwright

def test_extraction():
    print("="*70)
    print("TESTING CUMMINS EXTRACTION SCRIPT")
    print("="*70)

    # Get the extraction script from the scraper
    from scrapers.cummins_scraper import CumminsScraper
    from scrapers.base_scraper import ScraperMode

    scraper = CumminsScraper(mode=ScraperMode.PLAYWRIGHT)
    extraction_script = scraper.get_extraction_script()

    print("\n1. Loading captured HTML file...")
    with open('output/cummins_iframe_full.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    print("   ✓ Loaded HTML file")

    print("\n2. Running extraction script in Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML content
        page.set_content(html_content)

        # Run the extraction script
        try:
            dealers = page.evaluate(extraction_script)

            print(f"\n3. Extraction Results:")
            print(f"   ✓ Found {len(dealers)} dealers")

            if dealers:
                # Show first 3 dealers
                print(f"\n   Sample dealers:")
                for i, dealer in enumerate(dealers[:3], 1):
                    print(f"\n   Dealer {i}:")
                    print(f"      Name: {dealer.get('name', 'N/A')}")
                    print(f"      Phone: {dealer.get('phone', 'N/A')}")
                    print(f"      Address: {dealer.get('address_full', 'N/A')}")
                    print(f"      City: {dealer.get('city', 'N/A')}, {dealer.get('state', 'N/A')} {dealer.get('zip', 'N/A')}")
                    print(f"      Website: {dealer.get('website', 'N/A')}")
                    print(f"      Domain: {dealer.get('domain', 'N/A')}")
                    print(f"      Tier: {dealer.get('tier', 'N/A')}")
                    print(f"      Distance: {dealer.get('distance', 'N/A')}")

                # Save full results to JSON
                with open('output/cummins_test_extraction.json', 'w') as f:
                    json.dump(dealers, f, indent=2)
                print(f"\n   ✓ Saved full results to: output/cummins_test_extraction.json")

                # Validation checks
                print(f"\n4. Validation:")
                dealers_with_name = sum(1 for d in dealers if d.get('name'))
                dealers_with_phone = sum(1 for d in dealers if d.get('phone'))
                dealers_with_address = sum(1 for d in dealers if d.get('address_full'))
                dealers_with_zip = sum(1 for d in dealers if d.get('zip'))

                print(f"   - Dealers with name: {dealers_with_name}/{len(dealers)}")
                print(f"   - Dealers with phone: {dealers_with_phone}/{len(dealers)}")
                print(f"   - Dealers with address: {dealers_with_address}/{len(dealers)}")
                print(f"   - Dealers with ZIP: {dealers_with_zip}/{len(dealers)}")

                if dealers_with_name == len(dealers) and dealers_with_phone == len(dealers):
                    print(f"\n   ✅ Extraction script PASSED all validation checks!")
                    return True
                else:
                    print(f"\n   ⚠️  Some dealers missing required fields")
                    return False
            else:
                print(f"\n   ✗ No dealers found - extraction may have failed")
                return False

        except Exception as e:
            print(f"\n   ✗ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_extraction()
    exit(0 if success else 1)
