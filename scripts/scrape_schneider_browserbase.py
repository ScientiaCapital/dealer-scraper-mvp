#!/usr/bin/env python3
"""
Schneider Electric Installer Scraper - Browserbase Cloud Browser

Uses Browserbase cloud browsers with built-in:
- Residential proxy IPs (bypass datacenter IP blocking)
- Pre-patched stealth (bypass JavaScript bot detection)
- Session isolation (each batch gets fresh fingerprint)

Schneider Specifics:
- Simple ZIP/address search form
- AJAX-loaded results
- Commercial/industrial solar focus

Usage:
    # Test with 3 ZIPs
    python3 scripts/scrape_schneider_browserbase.py --test

    # Full production
    python3 scripts/scrape_schneider_browserbase.py --production

    # Resume from failure
    python3 scripts/scrape_schneider_browserbase.py --production --resume
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

from playwright.sync_api import sync_playwright, Page

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
BATCH_SIZE = 20
BATCH_PAUSE_SECONDS = 30
ZIP_DELAY_MIN = 5
ZIP_DELAY_MAX = 10
PROGRESS_FILE = "output/schneider_browserbase_progress.json"
OUTPUT_DIR = "output"

# Schneider URLs
SCHNEIDER_URL = "https://solar.se.com/us/en/find-a-preferred-installer/"


def get_schneider_extraction_script() -> str:
    """JavaScript extraction script for Schneider Electric installer data."""
    return r"""
    () => {
        const dealers = [];

        // Find all installer cards
        const installerCards = Array.from(document.querySelectorAll(
            '.installer-card, [class*="installer"], [class*="result-item"], .result-card, article, .card'
        )).filter(card => {
            const text = card.textContent || '';
            return text.length > 100 && !text.includes('No results');
        });

        console.log(`[Schneider] Found ${installerCards.length} installer cards`);

        installerCards.forEach((card) => {
            try {
                // Extract name
                const nameEl = card.querySelector('h1, h2, h3, h4, h5, [class*="name"], [class*="title"], strong');
                const name = nameEl ? nameEl.textContent.trim() : '';

                if (!name || name.length < 3) return;

                // Extract phone
                const phoneLink = card.querySelector('a[href^="tel:"]');
                let phone = '';
                if (phoneLink) {
                    phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
                    if (phone.length === 11 && phone.startsWith('1')) {
                        phone = phone.substring(1);
                    }
                }

                // Extract website
                const websiteLink = Array.from(card.querySelectorAll('a[href^="http"]'))
                    .find(link => {
                        const href = link.href;
                        return !href.includes('google') && !href.includes('facebook') &&
                               !href.includes('se.com') && !href.includes('schneider');
                    });
                const website = websiteLink ? websiteLink.href : '';
                let domain = '';
                if (website) {
                    try {
                        const url = new URL(website);
                        domain = url.hostname.replace(/^www\./, '');
                    } catch(e) {}
                }

                // Extract address
                let street = '', city = '', state = '', zip = '';
                const addressEl = card.querySelector('[class*="address"]');
                if (addressEl) {
                    const addressText = addressEl.textContent.trim();
                    const addressMatch = addressText.match(/^(.+?),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\s*(\d{5})/);
                    if (addressMatch) {
                        street = addressMatch[1].trim();
                        city = addressMatch[2];
                        state = addressMatch[3];
                        zip = addressMatch[4];
                    } else {
                        const cityStateMatch = addressText.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\s*(\d{5})/);
                        if (cityStateMatch) {
                            city = cityStateMatch[1];
                            state = cityStateMatch[2];
                            zip = cityStateMatch[3];
                        }
                    }
                }

                // Extract services
                const services = [];
                const serviceItems = card.querySelectorAll('li, [class*="service"], [class*="certification"]');
                serviceItems.forEach(item => {
                    const text = item.textContent.trim();
                    if (text && text.length < 100) {
                        services.push(text);
                    }
                });

                // Extract distance
                let distance = '', distance_miles = 0;
                const distanceMatch = card.textContent.match(/([\d.]+)\s*(mi|miles|km)/i);
                if (distanceMatch) {
                    const value = parseFloat(distanceMatch[1]);
                    const unit = distanceMatch[2].toLowerCase();
                    if (unit.includes('km')) {
                        distance_miles = value * 0.621371;
                        distance = `${distance_miles.toFixed(1)} mi`;
                    } else {
                        distance_miles = value;
                        distance = `${value} mi`;
                    }
                }

                dealers.push({
                    name: name,
                    phone: phone,
                    domain: domain,
                    website: website,
                    street: street,
                    city: city,
                    state: state,
                    zip: zip,
                    address_full: street && city && state ? `${street}, ${city}, ${state} ${zip}` : `${city}, ${state} ${zip}`,
                    tier: services.length > 0 ? 'Preferred Installer' : 'Standard',
                    certifications: services.join('; '),
                    distance: distance,
                    distance_miles: distance_miles,
                    oem_source: 'Schneider Electric'
                });
            } catch (error) {
                console.log(`[Schneider] Error parsing card: ${error.message}`);
            }
        });

        return dealers;
    }
    """


def create_browserbase_connection(playwright_instance):
    """Connect to Browserbase via WebSocket with residential proxy."""
    if not BROWSERBASE_API_KEY:
        print("❌ ERROR: Missing BROWSERBASE_API_KEY in .env")
        return None, None, None

    try:
        print("  Connecting to Browserbase...")
        ws_endpoint = f'wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&enableProxy=true'
        browser = playwright_instance.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        print(f"  ✓ Connected to Browserbase")
        return browser, context, page

    except Exception as e:
        print(f"  ❌ Failed to connect to Browserbase: {e}")
        return None, None, None


def scrape_schneider_zip(page: Page, zip_code: str) -> List[Dict]:
    """
    Scrape Schneider Electric installers for a single ZIP code.

    Returns: List of installer dicts
    """
    try:
        # Human-like delay before navigation
        time.sleep(random.uniform(1.5, 3.0))

        # Navigate to Schneider installer page
        print(f"    Navigating to Schneider page...")
        page.goto(SCHNEIDER_URL, timeout=60000, wait_until='domcontentloaded')
        time.sleep(random.uniform(3.0, 5.0))

        # Accept cookies if dialog appears
        try:
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                '#onetrust-accept-btn-handler',
                '[class*="accept"]',
            ]
            for selector in cookie_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                        print(f"    Dismissing cookie dialog...")
                        btn.first.click(timeout=3000)
                        time.sleep(1)
                        break
                except:
                    continue
        except:
            pass

        # Find and fill address input
        print(f"    Entering ZIP: {zip_code}")
        try:
            address_selectors = [
                'input[placeholder*="address" i]',
                'input[placeholder*="ZIP" i]',
                'input[placeholder*="location" i]',
                'input[type="text"]',
                'input[name*="address"]',
            ]

            address_input = None
            for selector in address_selectors:
                try:
                    inp = page.locator(selector).first
                    if inp.is_visible(timeout=3000):
                        address_input = inp
                        break
                except:
                    continue

            if not address_input:
                print(f"    ✗ Could not find address input")
                return []

            address_input.click()
            time.sleep(random.uniform(0.5, 1.0))
            address_input.fill(zip_code)
            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(f"    ✗ Error filling address: {e}")
            return []

        # Click search button or press Enter
        print(f"    Clicking Search...")
        try:
            search_selectors = [
                'button:has-text("Search")',
                'button:has-text("Find")',
                'input[type="submit"]',
                'button[type="submit"]',
            ]

            clicked = False
            for selector in search_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                print(f"    Pressing Enter...")
                page.keyboard.press("Enter")

        except Exception as e:
            print(f"    Pressing Enter...")
            page.keyboard.press("Enter")

        # Wait for results
        print(f"    Waiting for results...")
        time.sleep(random.uniform(5.0, 8.0))

        # Scroll to trigger lazy loading
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(random.uniform(1.5, 2.5))

        # Extract installer data
        print(f"    Extracting installers...")
        extraction_script = get_schneider_extraction_script()
        dealers = page.evaluate(extraction_script)

        # Add ZIP code to each
        for dealer in dealers:
            dealer['scraped_from_zip'] = zip_code

        print(f"    ✓ Found {len(dealers)} installers")
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
    filename = f"{OUTPUT_DIR}/schneider_bb_batch_{batch_num:03d}.csv"

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
    batch_files = sorted(Path(OUTPUT_DIR).glob("schneider_bb_batch_*.csv"))

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
        print(f"  Total unique installers: {len(final_dealers)}")

    return len(final_dealers)


def scrape_schneider_production(test_mode=False, resume=False):
    """
    Main scraping with Browserbase cloud browsers.
    """
    # Get all ZIPs from master list
    all_zips = []
    for state_zips in MASTER_ZIP_CODES.values():
        all_zips.extend(state_zips)

    if test_mode:
        all_zips = all_zips[:3]
        print("=" * 70)
        print("SCHNEIDER BROWSERBASE TEST MODE - 3 ZIP CODES")
        print("=" * 70)
    else:
        print("=" * 70)
        print("SCHNEIDER BROWSERBASE PRODUCTION - NATIONWIDE")
        print("=" * 70)
        print(f"Total ZIPs: {len(all_zips)}")
        print(f"Batch size: {BATCH_SIZE}")
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

                        if i < len(remaining_zips):
                            print(f"\n  ⏸  Pausing {BATCH_PAUSE_SECONDS}s...")
                            time.sleep(BATCH_PAUSE_SECONDS)

                    print(f"\n{'='*70}")
                    print(f"BATCH {batch_num} (ZIPs {i + 1}-{min(i + BATCH_SIZE, len(remaining_zips))})")
                    print(f"{'='*70}")

                    browser, context, page = create_browserbase_connection(p)
                    if not browser:
                        print("❌ Failed to connect to Browserbase - aborting")
                        return

                # Scrape ZIP
                print(f"\n[{i + 1}/{len(remaining_zips)}] Scraping Schneider - ZIP {zip_code}...")
                dealers = scrape_schneider_zip(page, zip_code)

                batch_dealers.extend(dealers)
                progress["completed_zips"].append(zip_code)
                progress["current_batch"] = batch_num

                save_progress(progress)

                # Random delay
                if i < len(remaining_zips) - 1:
                    delay = random.uniform(ZIP_DELAY_MIN, ZIP_DELAY_MAX)
                    print(f"  ⏱  Waiting {delay:.1f}s...")
                    time.sleep(delay)

                if (i + 1) % BATCH_SIZE == 0:
                    batch_num += 1

            # Save final batch
            if batch_dealers:
                save_batch_csv(batch_num, batch_dealers)
                progress["total_scraped"] += len(batch_dealers)

        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass

    # Merge results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"{OUTPUT_DIR}/schneider_browserbase_{timestamp}.csv"
    total = merge_batch_files(final_filename)

    print("\n" + "=" * 70)
    print("SCHNEIDER BROWSERBASE SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs: {len(progress['completed_zips'])}")
    print(f"Unique installers: {total}")
    print(f"Output: {final_filename}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Schneider Browserbase Scraper")
    parser.add_argument("--test", action="store_true", help="Test mode (3 ZIPs)")
    parser.add_argument("--production", action="store_true", help="Production (all ZIPs)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress")

    args = parser.parse_args()

    if args.test:
        scrape_schneider_production(test_mode=True, resume=False)
    elif args.production:
        scrape_schneider_production(test_mode=False, resume=args.resume)
    else:
        print("Usage:")
        print("  python3 scripts/scrape_schneider_browserbase.py --test")
        print("  python3 scripts/scrape_schneider_browserbase.py --production")
        print("  python3 scripts/scrape_schneider_browserbase.py --production --resume")
