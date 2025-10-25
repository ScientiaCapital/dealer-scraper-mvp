#!/usr/bin/env python3
"""
Multi-OEM Lead Generation - Find contractors certified with 2-4 brands

This script:
1. Scrapes dealers from all 4 OEMs (Generac, Tesla, Enphase, SolarEdge)
2. Cross-references to find multi-OEM contractors
3. Scores leads with Coperniq algorithm
4. Generates prioritized CSV sorted by value

Target: Contractors managing 2-4 monitoring platforms (prime Coperniq prospects)
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from scrapers.base_scraper import StandardizedDealer
from scrapers.generac_scraper import GeneracScraper
from scrapers.tesla_scraper import TeslaScraper
from scrapers.enphase_scraper import EnphaseScraper
from scrapers.solaredge_scraper import SolarEdgeScraper
from analysis.multi_oem_detector import MultiOEMDetector, MultiOEMMatch
from targeting.srec_itc_filter import SRECITCFilter
from targeting.coperniq_lead_scorer import CoperniqLeadScorer
from targeting.icp_filter import ICPFilter
from config import (
    ZIP_CODES_CALIFORNIA, ZIP_CODES_TEXAS, ZIP_CODES_PENNSYLVANIA,
    ZIP_CODES_MASSACHUSETTS, ZIP_CODES_NEW_JERSEY, ZIP_CODES_FLORIDA
)


# Generac extraction script (tested and working)
GENERAC_EXTRACTION_SCRIPT = """
() => {
  const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'));

  const dealers = phoneLinks.map(phoneLink => {
    // Find the dealer card container
    let container = phoneLink;
    for (let i = 0; i < 10; i++) {
      container = container.parentElement;
      if (!container) break;
      const hasDistance = container.querySelector('.ms-auto.text-end.text-nowrap');
      if (hasDistance) break;
    }

    if (!container) return null;

    // Extract dealer name (ALL CAPS text)
    const allDivs = Array.from(container.querySelectorAll('div'));
    let dealerName = '';
    for (const div of allDivs) {
      const text = div.textContent.trim();
      if (text && text.length > 5 && text.length < 100 &&
          !text.includes('(') && !text.includes('http') &&
          !text.includes('mi') && text === text.toUpperCase()) {
        dealerName = text;
        break;
      }
    }

    const fullText = container.textContent;
    const phoneText = phoneLink.textContent.trim();
    const beforePhone = fullText.substring(0, fullText.indexOf(phoneText));

    // Extract rating - pattern like "4.3(6)" or "5.0(24)"
    const ratingMatch = fullText.match(/(\\d+\\.\\d+)\\s*\\((\\d+)\\)/);
    const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
    const reviewCount = ratingMatch ? parseInt(ratingMatch[2]) : 0;

    // Extract dealer tier
    const isPremier = fullText.includes('Premier Dealers demonstrate');
    const isElitePlus = fullText.includes('Elite Plus');
    const isElite = fullText.includes('Elite Dealers offer');

    let tier = 'Standard';
    if (isPremier) tier = 'Premier';
    else if (isElitePlus) tier = 'Elite Plus';
    else if (isElite) tier = 'Elite';

    const isPowerProPremier = fullText.includes('PowerPro') || fullText.includes('Premier');

    // Extract street address
    const streetMatch = beforePhone.match(/(\\d+\\s+[nsew]?\\d*\\s*[^\\n,]*(?:st|street|dr|drive|rd|road|ave|avenue|ct|court|blvd|ln|way|pl)\\.?)/i);
    let street = streetMatch ? streetMatch[1].trim() : '';
    street = street.replace(/^.*?out of \\d+ stars\\.\\s*\\d*\\s*reviews?\\s*/i, '');
    street = street.replace(/^\\d+\\.\\d+\\s*\\(\\d+\\)/, '');
    street = street.replace(/^\\d+\\.\\d+\\s*mi/, '');

    // Extract city, state, ZIP
    const afterStreet = street ? beforePhone.substring(beforePhone.lastIndexOf(street) + street.length) : beforePhone;
    const cityStateZip = afterStreet.match(/([a-z\\s]+),?\\s*([A-Z]{2})\\s+(\\d{5})/i);

    const city = cityStateZip ? cityStateZip[1].trim() : '';
    const state = cityStateZip ? cityStateZip[2] : '';
    const zip = cityStateZip ? cityStateZip[3] : '';

    // Extract website and domain
    const websiteLink = container.querySelector('a[href^="http"]:not([href*="google"]):not([href*="facebook"])');
    const website = websiteLink?.href || '';

    let domain = '';
    if (website) {
      try {
        const url = new URL(website);
        domain = url.hostname.replace('www.', '');
      } catch (e) {
        domain = '';
      }
    }

    // Extract distance
    const distanceEl = container.querySelector('.ms-auto.text-end.text-nowrap');
    const distance = distanceEl?.textContent?.trim() || '';
    const distanceMiles = parseFloat(distance) || 0;

    return {
      name: dealerName,
      rating: rating,
      review_count: reviewCount,
      tier: tier,
      is_power_pro_premier: isPowerProPremier,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
      phone: phoneText,
      website: website,
      domain: domain,
      distance: distance,
      distance_miles: distanceMiles
    };
  });

  return dealers.filter(d => d && d.name);
}
"""


def scrape_oem_dealers(page, oem_name: str, zip_codes: list) -> list:
    """
    Scrape dealers from a specific OEM across multiple ZIP codes.

    Args:
        page: Playwright page object
        oem_name: "Generac", "Tesla", "Enphase", or "SolarEdge"
        zip_codes: List of ZIP codes to scrape

    Returns:
        List of StandardizedDealer objects
    """
    all_dealers = []

    print(f"\n{'='*70}")
    print(f"🔍 SCRAPING {oem_name.upper()} DEALERS")
    print(f"{'='*70}")
    print(f"ZIP codes: {len(zip_codes)}")
    print()

    for i, zip_code in enumerate(zip_codes, 1):
        print(f"[{i}/{len(zip_codes)}] Scraping {oem_name} - ZIP {zip_code}...")

        try:
            if oem_name == "Generac":
                dealers = scrape_generac_zip(page, zip_code)
            elif oem_name == "Tesla":
                dealers = scrape_tesla_zip(page, zip_code)
            elif oem_name == "Enphase":
                dealers = scrape_enphase_zip(page, zip_code)
            elif oem_name == "SolarEdge":
                dealers = scrape_solaredge_zip(page, zip_code)
            else:
                print(f"  ✗ Unknown OEM: {oem_name}")
                continue

            # Convert to StandardizedDealer objects
            for dealer in dealers:
                all_dealers.append(StandardizedDealer(
                    name=dealer["name"],
                    phone=dealer.get("phone", ""),
                    domain=dealer.get("domain", ""),
                    website=dealer.get("website", ""),
                    street=dealer.get("street", ""),
                    city=dealer.get("city", ""),
                    state=dealer.get("state", ""),
                    zip=dealer.get("zip", ""),
                    address_full=dealer.get("address_full", ""),
                    rating=dealer.get("rating", 0.0),
                    review_count=dealer.get("review_count", 0),
                    tier=dealer.get("tier", "Standard"),
                    certifications=dealer.get("certifications", []),
                    distance=dealer.get("distance", ""),
                    distance_miles=dealer.get("distance_miles", 0.0),
                    oem_source=oem_name,
                    scraped_from_zip=zip_code
                ))

            print(f"  ✓ Found {len(dealers)} dealers")

        except Exception as e:
            print(f"  ✗ Error scraping {oem_name} ZIP {zip_code}: {e}")
            continue

    print(f"\n✓ {oem_name} scraping complete: {len(all_dealers)} dealers found")
    return all_dealers


def scrape_generac_zip(page, zip_code: str) -> list:
    """Scrape Generac dealers for a single ZIP code (tested and working)"""
    try:
        page.goto("https://www.generac.com/dealer-locator/", timeout=30000)
        page.wait_for_timeout(2000)

        # Handle cookie banner
        try:
            result = page.evaluate("""
                () => {
                    if (typeof OneTrust !== 'undefined' && OneTrust.AllowAll) {
                        OneTrust.AllowAll();
                        return 'OneTrust.AllowAll() called';
                    }
                    const banner = document.querySelector('#onetrust-consent-sdk');
                    if (banner) {
                        banner.style.display = 'none';
                        return 'Banner hidden';
                    }
                    return 'OneTrust not found';
                }
            """)
            page.wait_for_timeout(1000)
        except:
            pass

        # Fill ZIP and search
        zip_input = page.locator('input[name*="zip" i], input[placeholder*="zip" i]').first
        zip_input.fill(zip_code)

        try:
            search_button = page.locator('button:has-text("Search"), button[type="submit"]').first
            search_button.click(timeout=5000)
        except:
            page.evaluate("""
                () => {
                    const button = document.querySelector('button[type="submit"]') ||
                                   document.querySelector('button.btn-find-dealer');
                    if (button) button.click();
                }
            """)

        page.wait_for_timeout(5000)
        dealers = page.evaluate(GENERAC_EXTRACTION_SCRIPT)
        return dealers

    except Exception as e:
        print(f"    Error in Generac scraper: {e}")
        return []


def scrape_tesla_zip(page, zip_code: str) -> list:
    """Scrape Tesla Powerwall installers for a single ZIP code"""
    try:
        scraper = TeslaScraper()
        extraction_script = scraper.get_extraction_script()

        page.goto("https://www.tesla.com/support/certified-installers-powerwall", timeout=30000)
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Fill ZIP code
        page.wait_for_selector('input[role="combobox"]', state='visible', timeout=30000)
        zip_input = page.locator('input[role="combobox"]')
        zip_input.fill(zip_code)
        print(f"    Filled ZIP code: {zip_code}")

        # Try autocomplete or press Enter
        try:
            page.wait_for_selector('div[role="listbox"]', state='visible', timeout=3000)
            page.wait_for_timeout(500)
            page.click('div[role="listbox"] div[role="option"]:first-child')
        except:
            zip_input.press('Enter')
            page.wait_for_timeout(1000)

        page.wait_for_timeout(4000)
        dealers = page.evaluate(extraction_script)
        return dealers

    except Exception as e:
        print(f"    Error in Tesla scraper: {e}")
        return []


def scrape_enphase_zip(page, zip_code: str) -> list:
    """Scrape Enphase installers for a single ZIP code"""
    try:
        scraper = EnphaseScraper()
        extraction_script = scraper.get_extraction_script()

        page.goto("https://enphase.com/installer-locator", timeout=30000)
        page.wait_for_timeout(2000)

        # Find and fill ZIP input (Enphase uses address autocomplete)
        # Try multiple selectors
        try:
            zip_input = page.locator('input[placeholder*="zip" i], input[placeholder*="address" i], input[type="text"]').first
            zip_input.fill(zip_code)
            zip_input.press('Enter')
        except:
            print(f"    Could not find Enphase ZIP input")
            return []

        page.wait_for_timeout(5000)
        dealers = page.evaluate(extraction_script)
        return dealers

    except Exception as e:
        print(f"    Error in Enphase scraper: {e}")
        return []


def scrape_solaredge_zip(page, zip_code: str) -> list:
    """Scrape SolarEdge installers for a single ZIP code"""
    try:
        scraper = SolarEdgeScraper()
        extraction_script = scraper.get_extraction_script()

        page.goto("https://www.solaredge.com/us/find-installer", timeout=30000)
        page.wait_for_timeout(2000)

        # Find and fill ZIP input
        try:
            zip_input = page.locator('input[placeholder*="zip" i]').first
            zip_input.fill(zip_code)

            search_button = page.locator('button[type="submit"]').first
            search_button.click()
        except:
            print(f"    Could not find SolarEdge ZIP input")
            return []

        page.wait_for_timeout(5000)
        dealers = page.evaluate(extraction_script)
        return dealers

    except Exception as e:
        print(f"    Error in SolarEdge scraper: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Multi-OEM Lead Generation")
    parser.add_argument("--oems", nargs="+", default=["Generac"],
                        help="OEMs to scrape (default: Generac only - add more as ready)")
    parser.add_argument("--states", nargs="+", default=["CA", "TX", "PA", "MA", "NJ", "FL"],
                        help="States to scrape (default: HIGH priority SREC states)")
    parser.add_argument("--limit-zips", type=int, default=None,
                        help="Limit number of ZIPs per state (for testing)")
    args = parser.parse_args()

    # Build ZIP code list
    state_zips = {
        "CA": ZIP_CODES_CALIFORNIA,
        "TX": ZIP_CODES_TEXAS,
        "PA": ZIP_CODES_PENNSYLVANIA,
        "MA": ZIP_CODES_MASSACHUSETTS,
        "NJ": ZIP_CODES_NEW_JERSEY,
        "FL": ZIP_CODES_FLORIDA
    }

    zip_codes = []
    for state in args.states:
        if state in state_zips:
            zips = state_zips[state]
            if args.limit_zips:
                zips = zips[:args.limit_zips]
            zip_codes.extend(zips)

    print("="*70)
    print("🚀 COPERNIQ MULTI-OEM LEAD GENERATION")
    print("="*70)
    print(f"OEMs: {', '.join(args.oems)}")
    print(f"States: {', '.join(args.states)}")
    print(f"Total ZIPs: {len(zip_codes)}")
    print("="*70)
    print()

    # Launch browser
    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Scrape all OEMs
        all_dealers_by_oem = {}
        start_time = time.time()

        for oem_name in args.oems:
            dealers = scrape_oem_dealers(page, oem_name, zip_codes)
            all_dealers_by_oem[oem_name] = dealers

        browser.close()

        elapsed = time.time() - start_time
        print()
        print(f"✓ All OEM scraping complete in {elapsed/60:.1f} minutes")
        print()

    # Print OEM breakdown
    print("="*70)
    print("📊 OEM BREAKDOWN")
    print("="*70)
    for oem_name, dealers in all_dealers_by_oem.items():
        print(f"{oem_name:15s}: {len(dealers):4d} dealers")
    print(f"{'TOTAL':15s}: {sum(len(d) for d in all_dealers_by_oem.values()):4d} dealers")
    print()

    # Combine all dealers for multi-OEM detection
    all_dealers = []
    for dealers in all_dealers_by_oem.values():
        all_dealers.extend(dealers)

    # Deduplicate within each OEM first (by phone)
    print("STEP 1: Deduplicating within each OEM...")
    for oem_name in all_dealers_by_oem:
        seen_phones = set()
        unique_dealers = []
        for dealer in all_dealers_by_oem[oem_name]:
            phone_digits = ''.join(c for c in dealer.phone if c.isdigit())
            if phone_digits and phone_digits not in seen_phones:
                seen_phones.add(phone_digits)
                unique_dealers.append(dealer)

        removed = len(all_dealers_by_oem[oem_name]) - len(unique_dealers)
        all_dealers_by_oem[oem_name] = unique_dealers
        print(f"  {oem_name}: {len(unique_dealers)} unique ({removed} duplicates removed)")
    print()

    # Multi-OEM cross-reference
    print("STEP 2: Cross-referencing across OEMs...")
    detector = MultiOEMDetector()

    # Combine all dealers from all OEMs
    all_dealers_combined = []
    for dealers in all_dealers_by_oem.values():
        all_dealers_combined.extend(dealers)

    # Add all dealers to detector at once
    detector.add_dealers(all_dealers_combined)

    # Find matches (min_oem_count=1 includes all contractors)
    matches = detector.find_multi_oem_contractors(min_oem_count=1)
    print(f"  ✓ {len(matches)} unique contractors identified")
    print()

    # Print multi-OEM breakdown
    multi_oem_counts = {
        "4_oems": len([m for m in matches if len(m.oem_sources) >= 4]),
        "3_oems": len([m for m in matches if len(m.oem_sources) == 3]),
        "2_oems": len([m for m in matches if len(m.oem_sources) == 2]),
        "1_oem": len([m for m in matches if len(m.oem_sources) == 1]),
    }

    print("  Multi-OEM breakdown:")
    print(f"    4 OEMs (GOLD):   {multi_oem_counts['4_oems']:4d} contractors  ← HIGHEST VALUE!")
    print(f"    3 OEMs (GOLD):   {multi_oem_counts['3_oems']:4d} contractors  ← HIGH VALUE")
    print(f"    2 OEMs (SILVER): {multi_oem_counts['2_oems']:4d} contractors  ← MEDIUM VALUE")
    print(f"    1 OEM (BRONZE):  {multi_oem_counts['1_oem']:4d} contractors")
    print()

    # Filter to SREC states and tag with ITC urgency
    print("STEP 3: Filtering to SREC states and tagging ITC urgency...")
    srec_filter = SRECITCFilter()
    result = srec_filter.filter_contractors(matches)
    matches = result.contractors
    print(f"  ✓ {len(matches)} contractors in SREC states")
    print()

    # Score with Coperniq algorithm
    print("STEP 4: Scoring with Coperniq algorithm...")
    scorer = CoperniqLeadScorer()
    scores = scorer.score_contractors(matches)
    print(f"  ✓ Coperniq scores calculated (0-100)")
    print()

    # ICP Analysis (Resimercial + O&M focus)
    print("STEP 5: Analyzing ICP fit (Resimercial + O&M)...")
    icp_filter = ICPFilter()
    icp_scores = icp_filter.score_contractors(matches)
    print(f"  ✓ ICP scores calculated")
    print()

    # Print ICP breakdown
    ideal_icp_count = len([s for s in icp_scores if s.is_ideal_icp])
    print("  ICP Tier Breakdown:")
    print(f"    PLATINUM (80-100): {len(icp_filter.platinum_contractors):4d} contractors  ← IDEAL ICP!")
    print(f"    GOLD (60-79):      {len(icp_filter.gold_contractors):4d} contractors  ← High priority")
    print(f"    SILVER (40-59):    {len(icp_filter.silver_contractors):4d} contractors")
    print(f"    BRONZE (<40):      {len(icp_filter.bronze_contractors):4d} contractors")
    print()
    print(f"  🎯 Perfect ICP Fit (all 4 dimensions): {ideal_icp_count} contractors")
    print()

    # Generate CSVs
    print("STEP 6: Generating master lead list CSV...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"output/coperniq_multi_oem_leads_{timestamp}.csv"
    icp_csv_path = f"output/icp_analysis_{timestamp}.csv"

    os.makedirs("output", exist_ok=True)
    scorer.export_csv(scores, csv_path)
    icp_filter.export_icp_report(icp_scores, icp_csv_path)

    print(f"  ✓ Coperniq CSV saved to: {csv_path}")
    print(f"  ✓ ICP Analysis CSV saved to: {icp_csv_path}")
    print()

    # Summary statistics
    print("="*70)
    print("📊 FINAL LEAD GENERATION SUMMARY")
    print("="*70)
    print(f"Total contractors: {len(scores)}")
    print()

    high = len([m for m in scores if m.total_score >= 80])
    medium = len([m for m in scores if 50 <= m.total_score < 80])
    low = len([m for m in scores if m.total_score < 50])

    print("Priority breakdown:")
    print(f"  HIGH (80-100):   {high:4d} contractors  ← Call first!")
    print(f"  MEDIUM (50-79):  {medium:4d} contractors")
    print(f"  LOW (<50):       {low:4d} contractors")
    print()

    # Multi-OEM gold list
    gold_contractors = [m for m in scores if len(m.contractor.capabilities.oem_certifications) >= 2]
    if gold_contractors:
        print(f"🏆 GOLD CONTRACTORS (Multi-OEM): {len(gold_contractors)}")
        print()

        # Show top 10
        print("Top 10 Multi-OEM Contractors:")
        for i, contractor in enumerate(gold_contractors[:10], 1):
            oems = ", ".join(contractor.contractor.capabilities.oem_certifications)
            print(f"  {i:2d}. {contractor.contractor.name[:50]:50s}")
            print(f"      OEMs: {oems}")
            print(f"      Score: {contractor.total_score}/100")
            print(f"      Phone: {contractor.contractor.phone}")
            print()

    print(f"✅ Master multi-OEM lead list ready: {csv_path}")
    print("="*70)


if __name__ == "__main__":
    main()
