#!/usr/bin/env python3
"""
Cummins Dealer Scraper - Browserbase Cloud Browser

Uses Browserbase cloud browsers with built-in:
- Residential proxy IPs (bypass datacenter IP blocking)
- Pre-patched stealth (bypass JavaScript bot detection)
- Session isolation (each batch gets fresh fingerprint)

Cummins Specifics:
- Complex iframe-based form with cascading dropdowns
- OneTrust cookie consent dialog
- 6 form fields: PRODUCT → MARKET → SERVICE → COUNTRY → LOCATION → DISTANCE

Usage:
    # Test with 3 ZIPs
    python3 scripts/scrape_cummins_browserbase.py --test

    # Full production
    python3 scripts/scrape_cummins_browserbase.py --production

    # Resume from failure
    python3 scripts/scrape_cummins_browserbase.py --production --resume
"""

import sys
import os
import json
import csv
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, Page, Frame

# Import from config.py - use MASTER_ZIP_CODES (the ONE source of truth)
import config
MASTER_ZIP_CODES = config.MASTER_ZIP_CODES

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

# Browserbase credentials
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

# Configuration
BATCH_SIZE = 15  # Fewer per batch due to complex form
BATCH_PAUSE_SECONDS = 45  # Longer pause for Cummins
ZIP_DELAY_MIN = 8  # Min seconds between ZIPs (form filling takes time)
ZIP_DELAY_MAX = 15  # Max seconds between ZIPs
PROGRESS_FILE = "output/cummins_browserbase_progress.json"
OUTPUT_DIR = "output"

# Cummins URLs and selectors
CUMMINS_URL = "https://www.cummins.com/na/generators/home-standby/find-a-dealer"
IFRAME_SELECTOR = 'iframe[title="Find dealer locations form"]'


def get_cummins_extraction_script() -> str:
    """JavaScript extraction script for Cummins dealer data."""
    return """
    () => {
        // Find all dealer cards
        const dealerCards = Array.from(document.querySelectorAll('.dealer-listing-col.com_locator_entry'));

        console.log(`[Cummins] Found ${dealerCards.length} dealer cards`);

        const dealers = dealerCards.map(card => {
            try {
                // Extract dealer name
                const nameLink = card.querySelector('.title .info h3 a.marker-link');
                const name = nameLink ? nameLink.textContent.trim() : '';

                // Extract tier (e.g., "Dealer")
                const tierSpan = card.querySelector('.title .info .location');
                const tier = tierSpan ? tierSpan.textContent.trim() : 'Authorized Dealer';

                // Extract phone
                const phoneLink = card.querySelector('.phone a[href^="tel:"]');
                const phone = phoneLink ? phoneLink.textContent.trim() : '';

                // Extract website
                const websiteLink = card.querySelector('.website a');
                const website = websiteLink ? websiteLink.href : '';

                // Extract domain from website
                let domain = '';
                if (website) {
                    try {
                        const url = new URL(website);
                        domain = url.hostname.replace('www.', '');
                    } catch (e) {}
                }

                // Extract address
                const addressDiv = card.querySelector('.address .address-info');
                let street = '';
                let city = '';
                let state = '';
                let zip = '';
                let address_full = '';

                if (addressDiv) {
                    const addressHTML = addressDiv.innerHTML;
                    const addressParts = addressHTML.split(/<br\\s*\\/?>/i).map(p => p.trim()).filter(p => p);

                    if (addressParts.length >= 2) {
                        street = addressParts[0].trim();
                        const cityStateZip = addressParts[1].trim();
                        const match = cityStateZip.match(/^([^,]+),\\s*([A-Z]{2,})\\s+(\\d{5})/);

                        if (match) {
                            city = match[1].trim();
                            state = match[2].trim();
                            zip = match[3].trim();
                        } else {
                            city = cityStateZip;
                        }
                    }

                    address_full = addressDiv.textContent.trim().replace(/\\s+/g, ' ');
                }

                // Extract distance
                const distanceP = card.querySelector('p');
                let distance = '';
                let distance_miles = 0;

                if (distanceP) {
                    const distanceText = distanceP.textContent.trim();
                    const milesMatch = distanceText.match(/([\\d.]+)\\s*Mi/i);
                    if (milesMatch) {
                        distance_miles = parseFloat(milesMatch[1]);
                        distance = `${distance_miles} mi`;
                    }
                }

                return {
                    name: name,
                    phone: phone,
                    website: website,
                    domain: domain,
                    street: street,
                    city: city,
                    state: state,
                    zip: zip,
                    address_full: address_full,
                    tier: tier,
                    certifications: tier,
                    distance: distance,
                    distance_miles: distance_miles,
                    oem_source: 'Cummins'
                };
            } catch (e) {
                console.error('[Cummins] Error extracting dealer card:', e);
                return null;
            }
        });

        const validDealers = dealers.filter(d => d && d.name);
        console.log(`[Cummins] Extracted ${validDealers.length} valid dealers`);

        return validDealers;
    }
    """


def create_browserbase_connection(playwright_instance):
    """
    Connect to Browserbase via WebSocket with residential proxy.

    Returns: (browser, context, page) tuple
    """
    if not BROWSERBASE_API_KEY:
        print("❌ ERROR: Missing BROWSERBASE_API_KEY in .env")
        return None, None, None

    try:
        print("  Connecting to Browserbase...")

        # WebSocket connection with proxy enabled
        ws_endpoint = f'wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&enableProxy=true'

        browser = playwright_instance.chromium.connect_over_cdp(ws_endpoint)

        # Get default context and page
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        print(f"  ✓ Connected to Browserbase")

        return browser, context, page

    except Exception as e:
        print(f"  ❌ Failed to connect to Browserbase: {e}")
        return None, None, None


def dismiss_cookie_consent(page: Page):
    """Dismiss OneTrust cookie consent if present."""
    try:
        cookie_selectors = [
            '#onetrust-accept-btn-handler',
            'button:has-text("Accept All")',
            'button:has-text("Accept")',
            '.onetrust-close-btn-handler',
        ]

        for selector in cookie_selectors:
            try:
                btn = page.locator(selector)
                if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                    print(f"    Dismissing cookie dialog...")
                    btn.first.click(timeout=3000)
                    time.sleep(1)
                    return True
            except:
                continue
    except:
        pass
    return False


def fill_cummins_form(page: Page, iframe, zip_code: str) -> bool:
    """
    Fill the Cummins cascading form.

    Form fields:
    1. PRODUCT: Power Generation
    2. MARKET APPLICATION: Home And Small Business
    3. SERVICE LEVEL: (first non-empty option)
    4. COUNTRY: United States
    5. LOCATION: ZIP code
    6. DISTANCE: 100 Miles
    """
    try:
        # PRODUCT: Power Generation
        print(f"    Selecting Product: Power Generation")
        product_select = iframe.locator('select').first
        product_select.select_option(label='Power Generation')
        time.sleep(random.uniform(1.5, 2.5))

        # MARKET APPLICATION: Home And Small Business
        print(f"    Selecting Market: Home And Small Business")
        market_select = iframe.locator('select').nth(1)
        market_select.select_option(label='Home And Small Business')
        time.sleep(random.uniform(1.5, 2.5))

        # SERVICE LEVEL: First non-empty option
        print(f"    Selecting Service Level")
        service_select = iframe.locator('select').nth(2)
        options = service_select.locator('option').all()
        if len(options) > 1:
            first_value = options[1].get_attribute('value')
            service_select.select_option(value=first_value)
        time.sleep(random.uniform(2.0, 3.0))

        # COUNTRY: United States
        print(f"    Selecting Country: United States")
        country_select = iframe.locator('select').nth(3)
        country_select.select_option(label='United States')
        time.sleep(random.uniform(2.0, 3.0))

        # LOCATION: ZIP code
        print(f"    Entering ZIP: {zip_code}")
        postal_input = iframe.locator('input[name="postal_code"]')
        postal_input.wait_for(state='visible', timeout=10000)
        postal_input.fill(zip_code)
        time.sleep(random.uniform(1.0, 1.5))

        # DISTANCE: 100 Miles
        print(f"    Selecting Distance: 100 Miles")
        iframe.locator('input[value="100"]').check()
        time.sleep(random.uniform(0.5, 1.0))

        return True

    except Exception as e:
        print(f"    ✗ Error filling form: {e}")
        return False


def click_search_button(iframe) -> bool:
    """Click the search button in the form."""
    button_selectors = [
        'input[type="submit"]',
        'button[type="submit"]',
        'input[value*="SEARCH" i]',
        'button:has-text("SEARCH")',
        '.form-submit',
    ]

    for selector in button_selectors:
        try:
            btn = iframe.locator(selector)
            if btn.count() > 0:
                btn.first.click(timeout=5000)
                return True
        except:
            continue

    return False


def scrape_cummins_zip(page: Page, zip_code: str) -> List[Dict]:
    """
    Scrape Cummins dealers for a single ZIP code.

    Returns: List of dealer dicts
    """
    try:
        # Human-like delay before navigation
        time.sleep(random.uniform(1.5, 3.0))

        # Navigate to Cummins dealer page
        print(f"    Navigating to Cummins page...")
        page.goto(CUMMINS_URL, timeout=60000, wait_until='domcontentloaded')
        time.sleep(random.uniform(3.0, 5.0))

        # Dismiss cookie consent
        dismiss_cookie_consent(page)
        time.sleep(random.uniform(1.0, 2.0))

        # Find the iframe
        print(f"    Finding form iframe...")
        iframe = page.frame_locator(IFRAME_SELECTOR)

        # Fill the form
        if not fill_cummins_form(page, iframe, zip_code):
            return []

        # Click search button
        print(f"    Clicking Search...")
        if not click_search_button(iframe):
            print(f"    ✗ Could not find Search button")
            return []

        # Wait for results to load
        print(f"    Waiting for results...")
        time.sleep(random.uniform(8.0, 12.0))

        # Find the iframe frame for extraction
        iframe_frame = None
        for frame in page.frames:
            frame_url = frame.url
            if 'locator-interface' in frame_url or frame != page.main_frame:
                iframe_frame = frame
                break

        if not iframe_frame:
            print(f"    ✗ Could not find iframe for extraction")
            return []

        # Extract dealer data
        print(f"    Extracting dealers...")
        extraction_script = get_cummins_extraction_script()
        dealers = iframe_frame.evaluate(extraction_script)

        # Add ZIP code to each
        for dealer in dealers:
            dealer['scraped_from_zip'] = zip_code

        print(f"    ✓ Found {len(dealers)} dealers")
        return dealers

    except Exception as e:
        print(f"    ✗ Error scraping ZIP {zip_code}: {e}")
        return []


def load_progress() -> Dict:
    """Load progress from JSON file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_zips": [], "current_batch": 0, "total_scraped": 0}


def save_progress(progress: Dict):
    """Save progress to JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def save_batch_csv(batch_num: int, dealers: List[Dict]) -> str:
    """Save batch results to CSV."""
    filename = f"{OUTPUT_DIR}/cummins_bb_batch_{batch_num:03d}.csv"

    if not dealers:
        print(f"  ⚠ No dealers for batch {batch_num}")
        return filename

    fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                  'state', 'zip', 'address_full', 'tier', 'certifications',
                  'distance', 'distance_miles', 'scraped_from_zip', 'oem_source']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dealers)

    print(f"  ✓ Saved {len(dealers)} dealers to {filename}")
    return filename


def merge_batch_files(output_filename: str) -> int:
    """Merge all batch CSV files into single output."""
    batch_files = sorted(Path(OUTPUT_DIR).glob("cummins_bb_batch_*.csv"))

    if not batch_files:
        print("  ⚠ No batch files to merge")
        return 0

    all_dealers = []
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            all_dealers.extend(list(reader))

    # Deduplicate by phone
    unique_dealers = {}
    for dealer in all_dealers:
        phone = dealer.get('phone', '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        if phone and phone not in unique_dealers:
            unique_dealers[phone] = dealer

    final_dealers = list(unique_dealers.values())

    if final_dealers:
        fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                      'state', 'zip', 'address_full', 'tier', 'certifications',
                      'distance', 'distance_miles', 'scraped_from_zip', 'oem_source']

        with open(output_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_dealers)

        print(f"\n✓ Merged {len(batch_files)} batch files into {output_filename}")
        print(f"  Total unique dealers: {len(final_dealers)}")

    return len(final_dealers)


def scrape_cummins_production(test_mode=False, resume=False):
    """
    Main scraping with Browserbase cloud browsers.

    Args:
        test_mode: Only scrape 3 ZIPs for testing
        resume: Resume from previous progress
    """
    # Get all ZIPs from master list
    all_zips = []
    for state_zips in MASTER_ZIP_CODES.values():
        all_zips.extend(state_zips)

    if test_mode:
        all_zips = all_zips[:3]
        print("=" * 70)
        print("CUMMINS BROWSERBASE TEST MODE - 3 ZIP CODES")
        print("=" * 70)
    else:
        print("=" * 70)
        print("CUMMINS BROWSERBASE PRODUCTION - NATIONWIDE")
        print("=" * 70)
        print(f"Total ZIPs: {len(all_zips)}")
        print(f"Batch size: {BATCH_SIZE}")
        print(f"Estimated batches: {(len(all_zips) + BATCH_SIZE - 1) // BATCH_SIZE}")
        print("=" * 70)

    # Load progress
    progress = load_progress() if resume else {"completed_zips": [], "current_batch": 0, "total_scraped": 0}

    remaining_zips = [z for z in all_zips if z not in progress["completed_zips"]]

    if resume and len(remaining_zips) < len(all_zips):
        print(f"\n📋 RESUMING: {len(progress['completed_zips'])} ZIPs completed")
        print(f"   Remaining: {len(remaining_zips)} ZIPs\n")

    if not remaining_zips:
        print("✓ All ZIPs completed!")
        return

    # Process in batches
    batch_num = progress["current_batch"] + 1
    batch_dealers = []

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        try:
            for i, zip_code in enumerate(remaining_zips):
                # Create new connection at batch start
                if i % BATCH_SIZE == 0:
                    # Close previous browser
                    if browser:
                        print(f"\n  Saving batch {batch_num - 1}...")
                        if batch_dealers:
                            save_batch_csv(batch_num - 1, batch_dealers)
                            progress["total_scraped"] += len(batch_dealers)
                            batch_dealers = []

                        try:
                            browser.close()
                        except:
                            pass

                        # Pause between batches
                        if i < len(remaining_zips):
                            print(f"\n  ⏸  Pausing {BATCH_PAUSE_SECONDS}s...")
                            time.sleep(BATCH_PAUSE_SECONDS)

                    # Create new connection
                    print(f"\n{'='*70}")
                    print(f"BATCH {batch_num} (ZIPs {i + 1}-{min(i + BATCH_SIZE, len(remaining_zips))})")
                    print(f"{'='*70}")

                    browser, context, page = create_browserbase_connection(p)
                    if not browser:
                        print("❌ Failed to connect to Browserbase - aborting")
                        return

                # Scrape ZIP
                print(f"\n[{i + 1}/{len(remaining_zips)}] Scraping Cummins - ZIP {zip_code}...")
                dealers = scrape_cummins_zip(page, zip_code)

                batch_dealers.extend(dealers)
                progress["completed_zips"].append(zip_code)
                progress["current_batch"] = batch_num

                save_progress(progress)

                # Random delay
                if i < len(remaining_zips) - 1:
                    delay = random.uniform(ZIP_DELAY_MIN, ZIP_DELAY_MAX)
                    print(f"  ⏱  Waiting {delay:.1f}s...")
                    time.sleep(delay)

                # Increment batch at boundary
                if (i + 1) % BATCH_SIZE == 0:
                    batch_num += 1

            # Save final batch
            if batch_dealers:
                save_batch_csv(batch_num, batch_dealers)
                progress["total_scraped"] += len(batch_dealers)

        finally:
            # Cleanup
            if browser:
                try:
                    browser.close()
                except:
                    pass

    # Merge results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"{OUTPUT_DIR}/cummins_browserbase_{timestamp}.csv"
    total = merge_batch_files(final_filename)

    print("\n" + "=" * 70)
    print("CUMMINS BROWSERBASE SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs: {len(progress['completed_zips'])}")
    print(f"Unique dealers: {total}")
    print(f"Output: {final_filename}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cummins Browserbase Scraper")
    parser.add_argument("--test", action="store_true", help="Test mode (3 ZIPs)")
    parser.add_argument("--production", action="store_true", help="Production (all ZIPs)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress")

    args = parser.parse_args()

    if args.test:
        scrape_cummins_production(test_mode=True, resume=False)
    elif args.production:
        scrape_cummins_production(test_mode=False, resume=args.resume)
    else:
        print("Usage:")
        print("  python3 scripts/scrape_cummins_browserbase.py --test")
        print("  python3 scripts/scrape_cummins_browserbase.py --production")
        print("  python3 scripts/scrape_cummins_browserbase.py --production --resume")
