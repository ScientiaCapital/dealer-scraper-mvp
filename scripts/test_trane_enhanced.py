#!/usr/bin/env python3
"""
Test script for enhanced Trane scraper.

Tests the new directory table + detail page approach with a small sample.
Run locally with Playwright (no Browserbase needed for testing).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.trane_scraper import TraneScraper
from scrapers.base_scraper import ScraperMode


def test_capability_detection():
    """Test multi-trade capability detection."""
    print("\n" + "="*60)
    print("TEST 1: Capability Detection")
    print("="*60)

    scraper = TraneScraper(mode=ScraperMode.PLAYWRIGHT)

    # Test case 1: HVAC only (basic dealer)
    basic_dealer = {
        'name': 'ABC Heating & Cooling',
        'certifications': ['Trane Dealer'],
        'areas_of_expertise': ['HVAC repair', 'AC installation']
    }
    caps1 = scraper.detect_capabilities(basic_dealer)
    print(f"\n1. Basic HVAC Dealer: {basic_dealer['name']}")
    print(f"   has_hvac: {caps1.has_hvac}")
    print(f"   is_multi_trade: {caps1.is_multi_trade}")
    print(f"   mep_e_trade_count: {caps1.mep_e_trade_count}")
    assert caps1.has_hvac == True
    assert caps1.is_multi_trade == False  # Only HVAC
    print("   ✓ PASSED")

    # Test case 2: HVAC + Plumbing (MEP signal)
    mep_dealer = {
        'name': 'Best Mechanical & Plumbing Inc',
        'certifications': ['Trane Comfort Specialist', 'NATE Certified'],
        'areas_of_expertise': ['HVAC repair', 'Plumbing services', 'Water heater installation']
    }
    caps2 = scraper.detect_capabilities(mep_dealer)
    print(f"\n2. MEP Dealer: {mep_dealer['name']}")
    print(f"   has_hvac: {caps2.has_hvac}")
    print(f"   has_plumbing: {caps2.has_plumbing}")
    print(f"   is_multi_trade: {caps2.is_multi_trade}")
    print(f"   multi_trade_combo: {caps2.multi_trade_combo}")
    assert caps2.has_hvac == True
    assert caps2.has_plumbing == True
    assert caps2.is_multi_trade == True  # HVAC + Plumbing = 2 trades
    print("   ✓ PASSED")

    # Test case 3: HVAC + Fire/Security (GOLD!)
    gold_dealer = {
        'name': 'Premier Fire & HVAC Solutions LLC',
        'certifications': ['Trane Comfort Specialist', 'NATE Certified'],
        'areas_of_expertise': ['HVAC installation', 'Fire alarm systems', 'Sprinkler maintenance']
    }
    caps3 = scraper.detect_capabilities(gold_dealer)
    print(f"\n3. GOLD Dealer: {gold_dealer['name']}")
    print(f"   has_hvac: {caps3.has_hvac}")
    print(f"   has_fire_security: {caps3.has_fire_security}")
    print(f"   is_multi_trade: {caps3.is_multi_trade}")
    print(f"   multi_trade_combo: {caps3.multi_trade_combo}")
    assert caps3.has_hvac == True
    assert caps3.has_fire_security == True
    assert caps3.is_multi_trade == True  # HVAC + Fire/Security = GOLD
    print("   ✓ PASSED")

    # Test case 4: HVAC + Electrical + Plumbing (Full MEP!)
    full_mep = {
        'name': 'Complete Mechanical Contractors Corp',
        'certifications': ['Trane Dealer of Excellence'],
        'areas_of_expertise': ['HVAC', 'Electrical work', 'Plumbing', 'Commercial service']
    }
    caps4 = scraper.detect_capabilities(full_mep)
    print(f"\n4. Full MEP: {full_mep['name']}")
    print(f"   has_hvac: {caps4.has_hvac}")
    print(f"   has_electrical: {caps4.has_electrical}")
    print(f"   has_plumbing: {caps4.has_plumbing}")
    print(f"   is_multi_trade: {caps4.is_multi_trade}")
    print(f"   mep_e_trade_count: {caps4.mep_e_trade_count}")
    print(f"   multi_trade_combo: {caps4.multi_trade_combo}")
    assert caps4.has_hvac == True
    assert caps4.has_electrical == True
    assert caps4.has_plumbing == True
    assert caps4.mep_e_trade_count >= 3
    print("   ✓ PASSED")

    print("\n" + "="*60)
    print("ALL CAPABILITY TESTS PASSED!")
    print("="*60)


def test_phone_validation():
    """Test phone number validation (exclude toll-free)."""
    print("\n" + "="*60)
    print("TEST 2: Phone Validation")
    print("="*60)

    from scrapers.base_scraper import BaseDealerScraper

    test_cases = [
        ("2145551234", True, "Local Dallas phone"),
        ("8005551234", False, "Toll-free 800"),
        ("8885551234", False, "Toll-free 888"),
        ("8775551234", False, "Toll-free 877"),
        ("8665551234", False, "Toll-free 866 (Trane call center prefix)"),
        ("8555551234", False, "Toll-free 855"),
        ("8445551234", False, "Toll-free 844"),
        ("8335551234", False, "Toll-free 833"),
        ("4155551234", True, "Local SF phone"),
        ("18005551234", False, "1-800 with country code"),
        ("12125551234", True, "1-212 NYC with country code"),
        ("", False, "Empty string"),
        ("12345", False, "Too short"),
    ]

    all_passed = True
    for phone, expected, description in test_cases:
        result = BaseDealerScraper._is_valid_phone(phone)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"   {status} {description}: {phone} → {result} (expected: {expected})")

    if all_passed:
        print("\n" + "="*60)
        print("ALL PHONE VALIDATION TESTS PASSED!")
        print("="*60)
    else:
        print("\n⚠️ SOME TESTS FAILED!")


def test_playwright_mode():
    """Test local Playwright scraping (ZIP search mode)."""
    print("\n" + "="*60)
    print("TEST 3: Playwright Mode (ZIP Search)")
    print("="*60)

    scraper = TraneScraper(mode=ScraperMode.PLAYWRIGHT)

    # Test with Dallas ZIP (should have dealers)
    zip_code = "75201"
    print(f"\nSearching Trane dealers near ZIP {zip_code}...")

    try:
        dealers = scraper.scrape_zip_code(zip_code)
        print(f"\n  Found {len(dealers)} dealers")

        if dealers:
            print("\n  Sample dealers:")
            for d in dealers[:3]:
                print(f"    • {d.name}")
                print(f"      City: {d.city}, State: {d.state}")
                print(f"      Phone: {d.phone or 'N/A'}")
                print(f"      Rating: {d.rating or 'N/A'}")
                print(f"      Multi-trade: {d.capabilities.is_multi_trade}")
                print(f"      Trade combo: {d.capabilities.multi_trade_combo or 'Single trade'}")
                print()

        print("="*60)
        print("PLAYWRIGHT TEST COMPLETED!")
        print("="*60)

    except Exception as e:
        print(f"\n⚠️ Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  TRANE ENHANCED SCRAPER - TEST SUITE")
    print("="*60)

    # Test 1: Capability detection
    test_capability_detection()

    # Test 2: Phone validation
    test_phone_validation()

    # Test 3: Playwright mode (requires browser)
    print("\n" + "-"*60)
    run_playwright = input("Run Playwright test? (y/n): ").strip().lower()
    if run_playwright == 'y':
        test_playwright_mode()
    else:
        print("Skipping Playwright test.")

    print("\n" + "="*60)
    print("  ALL TESTS COMPLETED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
