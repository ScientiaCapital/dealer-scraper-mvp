"""
Quick test of SolarEdge solar inverter scraper.
Tests the complex AJAX + click-through extraction workflow.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

def test_solaredge():
    """Test SolarEdge scraper on 3 diverse ZIP codes."""

    print("\n" + "="*80)
    print("TESTING SOLAREDGE SOLAR INVERTER SCRAPER")
    print("="*80 + "\n")

    scraper = ScraperFactory.create("SolarEdge", mode=ScraperMode.PLAYWRIGHT)

    # Test with 3 diverse ZIPs (per execution plan)
    test_zips = [
        ("94102", "San Francisco, CA"),
        ("78701", "Austin, TX"),
        ("19103", "Philadelphia, PA")
    ]

    total_dealers = 0
    total_with_phone = 0
    total_with_website = 0

    for zip_code, location in test_zips:
        print(f"\nTesting ZIP: {zip_code} ({location})")
        print("-" * 80)

        try:
            dealers = scraper.scrape_zip_code(zip_code)

            print(f"✅ Found {len(dealers)} SolarEdge dealers")
            total_dealers += len(dealers)

            if len(dealers) > 0:
                # Count data quality
                dealers_with_phone = sum(1 for d in dealers if d.phone)
                dealers_with_website = sum(1 for d in dealers if d.website)

                total_with_phone += dealers_with_phone
                total_with_website += dealers_with_website

                print(f"   Phone numbers: {dealers_with_phone}/{len(dealers)} ({dealers_with_phone/len(dealers)*100:.1f}%)")
                print(f"   Websites: {dealers_with_website}/{len(dealers)} ({dealers_with_website/len(dealers)*100:.1f}%)")

                print(f"\n   Sample dealers (first 2):")
                for i, dealer in enumerate(dealers[:2], 1):
                    print(f"      {i}. {dealer.name}")
                    print(f"         Location: {dealer.city}, {dealer.state} {dealer.zip}")
                    print(f"         Phone: {dealer.phone if dealer.phone else '(none)'}")
                    if dealer.website:
                        print(f"         Website: {dealer.website}")
                    if dealer.certifications:
                        print(f"         Services: {', '.join(dealer.certifications[:3])}")
                    print()
            else:
                print("   ❌ No dealers found - check if extraction is working")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total dealers extracted: {total_dealers}")
    print(f"Average per ZIP: {total_dealers/len(test_zips):.1f}")

    if total_dealers > 0:
        print(f"Phone coverage: {total_with_phone}/{total_dealers} ({total_with_phone/total_dealers*100:.1f}%)")
        print(f"Website coverage: {total_with_website}/{total_dealers} ({total_with_website/total_dealers*100:.1f}%)")

        # Validation thresholds (from execution plan)
        if total_dealers >= 15:  # 5 per ZIP minimum
            print("\n✅ PASS: Extracted ≥5 dealers per ZIP")
        else:
            print(f"\n⚠️  WARNING: Only {total_dealers/len(test_zips):.1f} dealers per ZIP (expected ≥5)")

        if total_with_phone / total_dealers >= 0.9:
            print("✅ PASS: >90% have phone numbers")
        else:
            print(f"⚠️  WARNING: Only {total_with_phone/total_dealers*100:.1f}% have phone numbers")

    print("="*80 + "\n")


if __name__ == "__main__":
    test_solaredge()
