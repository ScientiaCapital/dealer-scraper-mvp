#!/usr/bin/env python3
"""
Test Tesla scraper with BROWSERBASE mode
"""

from scrapers.tesla_scraper import TeslaScraper, ScraperMode
import json

def test_tesla_browserbase(zip_code="94102"):
    """Test Tesla scraper with BROWSERBASE mode"""
    print(f"\n{'='*60}")
    print(f"Testing Tesla Scraper - BROWSERBASE Mode")
    print(f"ZIP Code: {zip_code} (San Francisco)")
    print(f"{'='*60}\n")

    try:
        # Create scraper in BROWSERBASE mode
        scraper = TeslaScraper(mode=ScraperMode.BROWSERBASE)

        # Scrape single ZIP
        print(f"[Test] Scraping ZIP {zip_code}...")
        dealers = scraper.scrape_zip_code(zip_code)

        # Display results
        print(f"\n{'='*60}")
        print(f"Results: {len(dealers)} Premier Certified Installers found")
        print(f"{'='*60}\n")

        if dealers:
            for i, dealer in enumerate(dealers, 1):
                print(f"{i}. {dealer.name}")
                print(f"   Phone: {dealer.phone}")
                print(f"   Website: {dealer.website}")
                print(f"   Tier: {dealer.tier}")
                print(f"   Certifications: {', '.join(dealer.certifications)}")
                print()

            # Save results
            scraper.save_json("output/test_tesla_browserbase.json")
            print(f"\n✅ Saved results to output/test_tesla_browserbase.json")
        else:
            print("⚠️  No dealers found - this might indicate an extraction issue")

        return dealers

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    dealers = test_tesla_browserbase("94102")

    if dealers:
        print(f"\n✅ Test PASSED - Tesla BROWSERBASE scraper working!")
    else:
        print(f"\n❌ Test FAILED - No dealers extracted")
