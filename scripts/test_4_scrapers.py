#!/usr/bin/env python3
"""
Quick test of 4 production-ready OEM scrapers
Tests: Briggs, Fronius, Sol-Ark, SimpliPhi
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

# Import the 4 working scrapers
from scrapers.briggs_scraper import BriggsScraper
from scrapers.fronius_scraper import FroniusScraper  
from scrapers.solark_scraper import SolArkScraper
from scrapers.simpliphi_scraper import SimpliPhiScraper
from scrapers.base_scraper import ScraperMode

def test_scraper(scraper_class, oem_name, test_zip="94102"):
    """Test a single scraper with one ZIP code"""
    print(f"\n{'='*60}")
    print(f"Testing {oem_name} Scraper")
    print(f"{'='*60}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            scraper = scraper_class(mode=ScraperMode.PLAYWRIGHT, page=page)
            dealers = scraper.scrape_zip(test_zip)
            
            browser.close()
            
        print(f"✅ {oem_name}: Found {len(dealers)} dealers in ZIP {test_zip}")
        
        if dealers:
            print(f"\nSample dealer:")
            d = dealers[0]
            print(f"  Name: {d.name}")
            print(f"  Phone: {d.phone}")
            print(f"  City: {d.city}, {d.state}")
            print(f"  Capabilities: Generator={d.capabilities.has_generator}, Battery={d.capabilities.has_battery}")
        
        return len(dealers) > 0
        
    except Exception as e:
        print(f"❌ {oem_name}: ERROR - {e}")
        return False

def main():
    """Test all 4 working scrapers"""
    print("\n" + "="*60)
    print("🧪 TESTING 4 PRODUCTION-READY SCRAPERS")
    print("="*60)
    print("OEMs: Briggs, Fronius, Sol-Ark, SimpliPhi")
    print("Test ZIP: 94102 (San Francisco)")
    print("="*60)
    
    results = {}
    
    # Test each scraper
    results['Briggs'] = test_scraper(BriggsScraper, "Briggs & Stratton")
    results['Fronius'] = test_scraper(FroniusScraper, "Fronius")
    results['Sol-Ark'] = test_scraper(SolArkScraper, "Sol-Ark")
    results['SimpliPhi'] = test_scraper(SimpliPhiScraper, "SimpliPhi")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for oem, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {oem:12s}: {status}")
    
    print(f"\nResults: {passed}/{total} scrapers working")
    
    if passed == total:
        print("\n🎉 ALL SCRAPERS READY FOR PRODUCTION!")
    else:
        print(f"\n⚠️  {total - passed} scrapers need attention")

if __name__ == "__main__":
    main()
