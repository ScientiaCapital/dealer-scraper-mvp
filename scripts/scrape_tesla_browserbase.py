#!/usr/bin/env python3
"""
Tesla Powerwall Installer Scraper - Browserbase Cloud Browser

Uses Browserbase cloud browsers with built-in:
- Residential proxy IPs (bypass datacenter IP blocking)
- Pre-patched stealth (bypass JavaScript bot detection)
- Session isolation (each batch gets fresh fingerprint)

Browserbase automatically handles:
✓ navigator.webdriver hiding
✓ WebGL/Canvas fingerprinting
✓ Browser plugin mocking
✓ Realistic HTTP headers
✓ Residential IP rotation

Usage:
    # Test with 3 ZIPs
    python3 scripts/scrape_tesla_browserbase.py --test

    # Full production (179 ZIPs)
    python3 scripts/scrape_tesla_browserbase.py --production

    # Resume from failure
    python3 scripts/scrape_tesla_browserbase.py --production --resume
"""

import sys
import os
import json
import csv
import random
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, Page
from config import WEALTHY_ZIPS_NATIONWIDE

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Browserbase credentials
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
BROWSERBASE_API_URL = "https://www.browserbase.com/v1/sessions"

# Configuration
BATCH_SIZE = 20  # ZIPs per batch before session recreation
BATCH_PAUSE_SECONDS = 30  # Pause between batches
ZIP_DELAY_MIN = 5  # Min seconds between ZIPs
ZIP_DELAY_MAX = 10  # Max seconds between ZIPs
PROGRESS_FILE = "output/tesla_browserbase_progress.json"
OUTPUT_DIR = "output"

# Tesla URLs and selectors
TESLA_URL = "https://www.tesla.com/support/certified-installers?productType=powerwall"
ZIP_INPUT_SELECTOR = 'input[role="combobox"]'
LISTBOX_SELECTOR = 'div[role="listbox"]'
INSTALLER_CARD_SELECTOR = '.styles_ciContainer__58zW_'


def get_tesla_extraction_script() -> str:
    """JavaScript extraction script for Tesla installer data"""
    return """
    () => {
        const cards = document.querySelectorAll('.styles_ciContainer__58zW_');

        const installers = Array.from(cards).map(card => {
            const text = card.innerText;
            const lines = text.split('\\n').filter(l => l.trim());

            // Extract data from card lines
            const tier = lines[0] || '';
            const name = lines[1] || '';
            const phone = lines[2] || '';
            const website = lines[3] || '';
            const email = lines[4] || '';

            // Extract domain from website URL
            let domain = '';
            if (website && website.startsWith('http')) {
                try {
                    const url = new URL(website);
                    domain = url.hostname.replace('www.', '');
                } catch (e) {
                    domain = '';
                }
            }

            // Format phone number
            let formattedPhone = phone;
            if (phone && phone.length === 10 && /^\\d{10}$/.test(phone)) {
                formattedPhone = `(${phone.substring(0,3)}) ${phone.substring(3,6)}-${phone.substring(6,10)}`;
            }

            // Determine certifications
            const certifications = [];
            if (tier.includes('Premier')) {
                certifications.push('Premier Certified Installer');
                certifications.push('Powerwall');
            } else {
                certifications.push('Certified Installer');
                certifications.push('Powerwall');
            }

            return {
                name: name,
                phone: formattedPhone,
                website: website,
                domain: domain,
                email: email,
                tier: tier,
                certifications: certifications.join('; '),
                oem_source: 'Tesla'
            };
        });

        return installers;
    }
    """


def create_browserbase_connection(playwright_instance):
    """
    Connect to Browserbase via WebSocket (simplified approach per official docs)

    Returns: (browser, context, page) tuple
    """
    if not BROWSERBASE_API_KEY:
        print("❌ ERROR: Missing BROWSERBASE_API_KEY in .env")
        return None, None, None

    try:
        print("  Connecting to Browserbase...")

        # Direct WebSocket connection (no session creation needed)
        ws_endpoint = f'wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&enableProxy=true'

        browser = playwright_instance.chromium.connect_over_cdp(ws_endpoint)

        # Get default context and page (Browserbase creates these automatically)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        print(f"  ✓ Connected to Browserbase")

        return browser, context, page

    except Exception as e:
        print(f"  ❌ Failed to connect to Browserbase: {e}")
        return None, None, None


def scrape_tesla_zip(page: Page, zip_code: str) -> List[Dict]:
    """
    Scrape Tesla installers for a single ZIP code

    Returns: List of installer dicts
    """
    try:
        # Human-like delay before navigation
        time.sleep(random.uniform(1.0, 2.5))

        # Navigate to Tesla installer page
        print(f"    Navigating to Tesla page...")
        page.goto(TESLA_URL, timeout=60000, wait_until='domcontentloaded')
        time.sleep(random.uniform(3.0, 5.0))

        # Wait for network idle
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(random.uniform(2.0, 3.5))

        # Simulate human scrolling
        page.evaluate("window.scrollBy(0, 100)")
        time.sleep(random.uniform(0.5, 1.0))

        # Wait for ZIP input
        print(f"    Waiting for ZIP input...")
        page.wait_for_selector(ZIP_INPUT_SELECTOR, state='visible', timeout=60000)
        time.sleep(random.uniform(0.8, 1.5))

        # Locate and interact with ZIP input
        zip_input = page.locator(ZIP_INPUT_SELECTOR)

        # Hover (human behavior)
        try:
            zip_input.hover()
            time.sleep(random.uniform(0.3, 0.7))
        except:
            pass

        # Click to focus
        zip_input.click()
        time.sleep(random.uniform(0.5, 1.2))

        # Type ZIP with delays
        print(f"    Typing ZIP: {zip_code}")
        for char in zip_code:
            zip_input.type(char, delay=random.randint(80, 200))

        time.sleep(random.uniform(0.8, 1.5))

        # Try autocomplete
        try:
            page.wait_for_selector(LISTBOX_SELECTOR, state='visible', timeout=8000)
            time.sleep(random.uniform(0.6, 1.2))

            first_option = page.locator('div[role="listbox"] div[role="option"]').first
            first_option.hover()
            time.sleep(random.uniform(0.3, 0.6))
            first_option.click()
            print(f"    Clicked autocomplete")
        except:
            print(f"    Pressing Enter")
            zip_input.press('Enter')
            time.sleep(random.uniform(1.2, 2.0))

        # Wait for results
        print(f"    Waiting for results...")
        time.sleep(random.uniform(5.0, 7.0))

        # Scroll to trigger lazy loading
        page.evaluate("window.scrollBy(0, 300)")
        time.sleep(random.uniform(1.0, 2.0))
        page.evaluate("window.scrollBy(0, 300)")
        time.sleep(random.uniform(1.0, 1.5))

        # Extract installer data
        print(f"    Extracting installers...")
        extraction_script = get_tesla_extraction_script()
        installers = page.evaluate(extraction_script)

        # Add ZIP code to each
        for installer in installers:
            installer['scraped_from_zip'] = zip_code

        print(f"    ✓ Found {len(installers)} installers")
        return installers

    except Exception as e:
        print(f"    ✗ Error scraping ZIP {zip_code}: {e}")
        return []


def load_progress() -> Dict:
    """Load progress from JSON file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_zips": [], "current_batch": 0, "total_scraped": 0}


def save_progress(progress: Dict):
    """Save progress to JSON file"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def save_batch_csv(batch_num: int, installers: List[Dict]) -> str:
    """Save batch results to CSV"""
    filename = f"{OUTPUT_DIR}/tesla_bb_batch_{batch_num:03d}.csv"

    if not installers:
        print(f"  ⚠ No installers for batch {batch_num}")
        return filename

    fieldnames = ['name', 'phone', 'website', 'domain', 'email', 'tier',
                  'certifications', 'scraped_from_zip', 'oem_source']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(installers)

    print(f"  ✓ Saved {len(installers)} installers to {filename}")
    return filename


def merge_batch_files(output_filename: str) -> int:
    """Merge all batch CSV files into single output"""
    batch_files = sorted(Path(OUTPUT_DIR).glob("tesla_bb_batch_*.csv"))

    if not batch_files:
        print("  ⚠ No batch files to merge")
        return 0

    all_installers = []
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            all_installers.extend(list(reader))

    # Deduplicate by phone
    unique_installers = {}
    for installer in all_installers:
        phone = installer.get('phone', '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        if phone and phone not in unique_installers:
            unique_installers[phone] = installer

    final_installers = list(unique_installers.values())

    if final_installers:
        fieldnames = ['name', 'phone', 'website', 'domain', 'email', 'tier',
                      'certifications', 'scraped_from_zip', 'oem_source']

        with open(output_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_installers)

        print(f"\n✓ Merged {len(batch_files)} batch files into {output_filename}")
        print(f"  Total unique installers: {len(final_installers)}")

    return len(final_installers)


def scrape_tesla_production(test_mode=False, resume=False):
    """
    Main scraping with Browserbase cloud browsers

    Args:
        test_mode: Only scrape 3 ZIPs for testing
        resume: Resume from previous progress
    """
    # Get all wealthy ZIPs
    all_zips = []
    for state_zips in WEALTHY_ZIPS_NATIONWIDE.values():
        all_zips.extend(state_zips)

    if test_mode:
        all_zips = all_zips[:3]
        print("=" * 70)
        print("TESLA BROWSERBASE TEST MODE - 3 ZIP CODES")
        print("=" * 70)
    else:
        print("=" * 70)
        print("TESLA BROWSERBASE PRODUCTION - NATIONWIDE")
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
    batch_installers = []

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
                        if batch_installers:
                            save_batch_csv(batch_num - 1, batch_installers)
                            progress["total_scraped"] += len(batch_installers)
                            batch_installers = []

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
                print(f"\n[{i + 1}/{len(remaining_zips)}] Scraping Tesla - ZIP {zip_code}...")
                installers = scrape_tesla_zip(page, zip_code)

                batch_installers.extend(installers)
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
            if batch_installers:
                save_batch_csv(batch_num, batch_installers)
                progress["total_scraped"] += len(batch_installers)

        finally:
            # Cleanup
            if browser:
                try:
                    browser.close()
                except:
                    pass

    # Merge results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"{OUTPUT_DIR}/tesla_browserbase_{timestamp}.csv"
    total = merge_batch_files(final_filename)

    print("\n" + "=" * 70)
    print("TESLA BROWSERBASE SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs: {len(progress['completed_zips'])}")
    print(f"Unique installers: {total}")
    print(f"Output: {final_filename}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tesla Browserbase Scraper")
    parser.add_argument("--test", action="store_true", help="Test mode (3 ZIPs)")
    parser.add_argument("--production", action="store_true", help="Production (all ZIPs)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress")

    args = parser.parse_args()

    if args.test:
        scrape_tesla_production(test_mode=True, resume=False)
    elif args.production:
        scrape_tesla_production(test_mode=False, resume=args.resume)
    else:
        print("Usage:")
        print("  python3 scripts/scrape_tesla_browserbase.py --test")
        print("  python3 scripts/scrape_tesla_browserbase.py --production")
        print("  python3 scripts/scrape_tesla_browserbase.py --production --resume")
