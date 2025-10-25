#!/usr/bin/env python3
"""
Local Playwright Automation - Coperniq Lead Generation
Runs headless browser locally to scrape dealer networks
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
from analysis.multi_oem_detector import MultiOEMMatch
from targeting.srec_itc_filter import SRECITCFilter
from targeting.coperniq_lead_scorer import CoperniqLeadScorer
from config import (
    ZIP_CODES_CALIFORNIA, ZIP_CODES_TEXAS, ZIP_CODES_PENNSYLVANIA,
    ZIP_CODES_MASSACHUSETTS, ZIP_CODES_NEW_JERSEY, ZIP_CODES_FLORIDA
)

# Tested extraction script from extraction.js
EXTRACTION_SCRIPT = """
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


def scrape_generac_zip(page, zip_code: str) -> list:
    """Scrape Generac dealers for a single ZIP code"""
    try:
        print(f"  [ZIP {zip_code}] Navigating to dealer locator...")
        page.goto("https://www.generac.com/dealer-locator/", timeout=30000)

        # Wait for page to fully load
        page.wait_for_timeout(2000)

        # ALWAYS try cookie dismissal on every navigation (website reloads cookie banner)
        print(f"  [ZIP {zip_code}] Handling cookie banner...")

        # Try multiple approaches to dismiss cookie banner
        cookie_accepted = False

        # 1. First try JavaScript API (most reliable)
        print(f"  [ZIP {zip_code}] Trying OneTrust API...")
        try:
            result = page.evaluate("""
                () => {
                    // Try OneTrust API
                    if (typeof OneTrust !== 'undefined' && OneTrust.AllowAll) {
                        OneTrust.AllowAll();
                        return 'OneTrust.AllowAll() called';
                    }
                    // Also try closing the banner
                    const banner = document.querySelector('#onetrust-consent-sdk');
                    if (banner) {
                        banner.style.display = 'none';
                        return 'Banner hidden';
                    }
                    // Remove dark overlay
                    const overlay = document.querySelector('.onetrust-pc-dark-filter');
                    if (overlay) {
                        overlay.remove();
                        return 'Overlay removed';
                    }
                    return 'OneTrust not found';
                }
            """)
            print(f"  [ZIP {zip_code}] JavaScript result: {result}")
            if "called" in result or "hidden" in result or "removed" in result:
                cookie_accepted = True
            page.wait_for_timeout(1000)
        except:
            pass

        # 2. Try clicking buttons (even if JavaScript worked, as backup)
        if not cookie_accepted:
            print(f"  [ZIP {zip_code}] Trying button clicks...")
            cookie_selectors = [
                'button#onetrust-accept-btn-handler',
                'button:has-text("Accept All Cookies")',
                'button:has-text("Accept All")',
                'button:has-text("Accept Cookies")',
                'button:has-text("Accept")',
                'button.onetrust-close-btn-handler',
                'button[aria-label*="Accept"]',
                'button[title*="Accept"]'
            ]

            for selector in cookie_selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=200):
                        button.click(force=True)  # Force click through overlays
                        print(f"  [ZIP {zip_code}] Clicked cookie button: {selector}")
                        cookie_accepted = True
                        page.wait_for_timeout(1000)
                        break
                except:
                    continue

        # 3. Force remove overlay as last resort
        if not cookie_accepted:
            print(f"  [ZIP {zip_code}] Force removing overlay...")
            try:
                page.evaluate("""
                    () => {
                        // Remove all OneTrust elements
                        const elements = document.querySelectorAll('[id*="onetrust"], [class*="onetrust"]');
                        elements.forEach(el => el.remove());
                        // Remove any overlays
                        const overlays = document.querySelectorAll('.ot-fade-in, .onetrust-pc-dark-filter');
                        overlays.forEach(el => el.remove());
                        // Restore body scrolling
                        document.body.style.overflow = 'auto';
                    }
                """)
            except:
                pass

        print(f"  [ZIP {zip_code}] Cookie handling complete")

        # Fill ZIP code input
        print(f"  [ZIP {zip_code}] Filling ZIP code...")
        zip_input = page.locator('input[name*="zip" i], input[placeholder*="zip" i]').first
        zip_input.fill(zip_code)

        # Click search button with enhanced error handling
        print(f"  [ZIP {zip_code}] Clicking search...")
        try:
            # Try normal click first
            search_button = page.locator('button:has-text("Search"), button[type="submit"]').first
            search_button.click(timeout=5000)
        except:
            # If normal click fails, try JavaScript click
            print(f"  [ZIP {zip_code}] Normal click failed, trying JavaScript click...")
            page.evaluate("""
                () => {
                    const button = document.querySelector('button[type="submit"]') ||
                                   document.querySelector('button.btn-find-dealer');
                    if (button) button.click();
                }
            """)

        # Wait for AJAX results to load (increased wait time)
        print(f"  [ZIP {zip_code}] Waiting for results...")
        page.wait_for_timeout(5000)

        # Extract dealer data
        print(f"  [ZIP {zip_code}] Extracting dealer data...")
        dealers = page.evaluate(EXTRACTION_SCRIPT)

        print(f"  [ZIP {zip_code}] ✓ Found {len(dealers)} dealers")
        return dealers

    except Exception as e:
        print(f"  [ZIP {zip_code}] ✗ Error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Local Playwright Lead Generation")
    parser.add_argument("--states", nargs="+", default=["CA", "TX", "PA", "MA", "NJ", "FL"],
                        help="States to scrape (default: all SREC states)")
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

    print("=" * 70)
    print("🚀 COPERNIQ LEAD GENERATION - Local Playwright Automation")
    print("=" * 70)
    print(f"States: {', '.join(args.states)}")
    print(f"Total ZIPs: {len(zip_codes)}")
    print("=" * 70)
    print()

    # Launch browser
    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Scrape all ZIPs
        all_dealers = []
        start_time = time.time()

        for i, zip_code in enumerate(zip_codes, 1):
            print(f"[{i}/{len(zip_codes)}] Scraping ZIP {zip_code}...")
            dealers = scrape_generac_zip(page, zip_code)

            # Convert to StandardizedDealer objects
            for dealer in dealers:
                all_dealers.append(StandardizedDealer(
                    name=dealer["name"],
                    phone=dealer["phone"],
                    domain=dealer["domain"],
                    website=dealer["website"],
                    street=dealer["street"],
                    city=dealer["city"],
                    state=dealer["state"],
                    zip=dealer["zip"],
                    address_full=dealer["address_full"],
                    rating=dealer["rating"],
                    review_count=dealer["review_count"],
                    tier=dealer["tier"],
                    certifications=[],
                    distance=dealer["distance"],
                    distance_miles=dealer["distance_miles"],
                    oem_source="Generac",
                    scraped_from_zip=zip_code
                ))

        browser.close()

        elapsed = time.time() - start_time
        print()
        print(f"✓ Scraping complete in {elapsed/60:.1f} minutes")
        print(f"✓ Total dealers found: {len(all_dealers)}")
        print()

    # Deduplicate by phone
    print("STEP 2: Deduplicating by phone number...")
    seen_phones = set()
    unique_dealers = []
    for dealer in all_dealers:
        phone_digits = ''.join(c for c in dealer.phone if c.isdigit())
        if phone_digits and phone_digits not in seen_phones:
            seen_phones.add(phone_digits)
            unique_dealers.append(dealer)

    print(f"  ✓ {len(unique_dealers)} unique dealers (removed {len(all_dealers) - len(unique_dealers)} duplicates)")
    print()

    # Convert to MultiOEMMatch format
    print("STEP 3: Converting to MultiOEMMatch format...")
    matches = []
    for dealer in unique_dealers:
        # Create single-OEM match for Coperniq scoring
        match = MultiOEMMatch(
            primary_dealer=dealer,
            oem_sources={"Generac"},
            dealer_records=[dealer],
            match_confidence=100,  # Single source = 100% confidence
            match_signals=["single_oem"],
        )
        match.multi_oem_score = match.calculate_multi_oem_score()
        matches.append(match)
    print(f"  ✓ {len(matches)} matches created")
    print()

    # Filter to SREC states and tag with ITC urgency
    print("STEP 4: Filtering to SREC states and tagging ITC urgency...")
    srec_filter = SRECITCFilter()
    result = srec_filter.filter_contractors(matches)
    matches = result.contractors  # Get filtered contractors from result
    print(f"  ✓ {len(matches)} dealers in SREC states with ITC urgency tags applied")
    print()

    # Score with Coperniq algorithm
    print("STEP 5: Scoring with Coperniq algorithm...")
    scorer = CoperniqLeadScorer()
    scores = scorer.score_contractors(matches)
    print(f"  ✓ Coperniq scores calculated (0-100)")
    print()

    # Generate CSV
    print("STEP 6: Generating master lead list CSV...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"output/coperniq_leads_{timestamp}.csv"

    os.makedirs("output", exist_ok=True)
    scorer.export_csv(scores, csv_path)

    print(f"  ✓ CSV saved to: {csv_path}")
    print()

    # Summary statistics
    print("=" * 70)
    print("📊 LEAD GENERATION SUMMARY")
    print("=" * 70)
    print(f"Total leads: {len(scores)}")
    print()

    high = len([m for m in scores if m.total_score >= 80])
    medium = len([m for m in scores if 50 <= m.total_score < 80])
    low = len([m for m in scores if m.total_score < 50])

    print("Priority breakdown:")
    print(f"  HIGH (80-100):   {high:4d} leads  ← Call first!")
    print(f"  MEDIUM (50-79):  {medium:4d} leads")
    print(f"  LOW (<50):       {low:4d} leads")
    print()

    print(f"✅ Master lead list ready: {csv_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
