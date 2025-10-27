#!/usr/bin/env python3
"""
Generac Automated Collection - Local Playwright
Fully automated collection using local browser with proper timing

This follows the proven Tesla automation pattern:
- Slower, more human-like timing
- Explicit wait conditions
- Better error handling
- Progress tracking with resume support
"""

import sys
import os
import json
import csv
import time
import random
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from config import EXTRACTION_SCRIPT, ZIP_CODES_SREC_ALL

# Configuration
GENERAC_URL = "https://www.generac.com/dealer-locator/"
COOKIE_ACCEPT_SELECTOR = "button:has-text('Accept Cookies')"
ZIP_INPUT_SELECTOR = "input[placeholder*='ZIP' i]"
SEARCH_BUTTON_SELECTOR = "button:has-text('Search')"
PROGRESS_FILE = "output/generac_progress.json"
OUTPUT_DIR = "output"
BATCH_SIZE = 20

# All 140 SREC state ZIPs (15 states: CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
ZIP_CODES = list(ZIP_CODES_SREC_ALL)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_zips": [], "failed_zips": [], "current_batch": 0, "total_collected": 0}


def save_progress(progress):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def save_batch_csv(batch_num, dealers):
    filename = f"{OUTPUT_DIR}/generac_batch_{batch_num:03d}.csv"

    if not dealers:
        return filename

    fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                  'state', 'zip', 'address_full', 'rating', 'review_count',
                  'tier', 'certifications', 'distance', 'distance_miles',
                  'scraped_from_zip', 'oem_source']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dealers)

    print(f"  ✓ Saved {len(dealers)} dealers to {filename}")
    return filename


def merge_all_batches():
    batch_files = sorted(Path(OUTPUT_DIR).glob("generac_batch_*.csv"))

    if not batch_files:
        print("⚠ No batch files to merge")
        return 0, None

    all_dealers = []
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            all_dealers.extend(list(reader))

    # Deduplicate by phone number (digits only)
    unique_dealers = {}
    for dealer in all_dealers:
        phone = dealer.get('phone', '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        if phone and phone not in unique_dealers:
            unique_dealers[phone] = dealer

    final_dealers = list(unique_dealers.values())

    if final_dealers:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{OUTPUT_DIR}/generac_dealers_{timestamp}.csv"

        fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                      'state', 'zip', 'address_full', 'rating', 'review_count',
                      'tier', 'certifications', 'distance', 'distance_miles',
                      'scraped_from_zip', 'oem_source']

        with open(final_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_dealers)

        print(f"\n✓ Merged {len(batch_files)} batch files")
        print(f"  Total unique dealers: {len(final_dealers)}")
        print(f"  Output: {final_filename}")
        return len(final_dealers), final_filename

    return 0, None


def scrape_zip(page, zip_code):
    """Scrape Generac dealers for a single ZIP"""
    try:
        # Navigate to Generac dealer locator
        print(f"    Navigating to Generac dealer locator...")
        page.goto(GENERAC_URL, timeout=60000, wait_until='domcontentloaded')
        time.sleep(random.uniform(3.0, 4.0))

        # Wait for network idle
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(random.uniform(2.0, 3.0))

        # CRITICAL: Remove cookie banner FIRST (more reliable than clicking)
        print(f"    Removing cookie banner...")
        page.evaluate("""
            () => {
                const banner = document.querySelector('#onetrust-consent-sdk');
                if (banner) banner.remove();
                const overlays = document.querySelectorAll('[class*="overlay"], [class*="modal"]');
                overlays.forEach(o => o.remove());
            }
        """)
        time.sleep(random.uniform(1.0, 2.0))

        # Wait for ZIP input
        print(f"    Waiting for ZIP input...")
        page.wait_for_selector(ZIP_INPUT_SELECTOR, state='visible', timeout=60000)
        time.sleep(random.uniform(1.0, 2.0))

        # Fill ZIP code
        zip_input = page.locator(ZIP_INPUT_SELECTOR)
        zip_input.click()
        time.sleep(random.uniform(0.5, 1.0))

        print(f"    Filling ZIP: {zip_code}")
        zip_input.fill(zip_code)
        time.sleep(random.uniform(1.0, 2.0))

        # Click search button
        print(f"    Clicking search button...")
        search_button = page.locator(SEARCH_BUTTON_SELECTOR)
        search_button.click()

        # Wait for AJAX results to load (3-5 seconds)
        print(f"    Waiting for results...")
        time.sleep(random.uniform(3.0, 5.0))

        # Wait for results to be visible
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(1.0, 2.0))

        # Extract dealers using proven extraction script
        print(f"    Extracting dealers...")
        dealers = page.evaluate(EXTRACTION_SCRIPT)

        # Add metadata to each dealer
        for dealer in dealers:
            dealer['scraped_from_zip'] = zip_code
            dealer['oem_source'] = 'Generac'

            # Format certifications from tier
            tier = dealer.get('tier', 'Standard')
            certifications = []
            if tier == 'Premier':
                certifications.append('Premier Dealer')
            elif tier == 'Elite Plus':
                certifications.append('Elite Plus Dealer')
            elif tier == 'Elite':
                certifications.append('Elite Dealer')

            if dealer.get('is_power_pro_premier'):
                certifications.append('PowerPro Premier')

            dealer['certifications'] = '; '.join(certifications) if certifications else ''

            # Remove is_power_pro_premier (internal flag)
            dealer.pop('is_power_pro_premier', None)

        print(f"    ✓ Found {len(dealers)} dealers")
        return dealers

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def run_collection():
    """Main collection workflow"""
    print("=" * 70)
    print("GENERAC LOCAL PLAYWRIGHT COLLECTION - ALL SREC STATES")
    print("=" * 70)
    print(f"Total ZIPs: {len(ZIP_CODES)} (15 SREC states)")
    print()

    # Load progress
    progress = load_progress()
    remaining_zips = [z for z in ZIP_CODES if z not in progress["completed_zips"]]

    if len(remaining_zips) < len(ZIP_CODES):
        print(f"📋 RESUMING: {len(progress['completed_zips'])} ZIPs completed")
        print(f"   Remaining: {len(remaining_zips)} ZIPs")
        if progress.get('failed_zips'):
            print(f"   Failed: {len(progress['failed_zips'])} ZIPs")
        print()

    if not remaining_zips:
        print("✅ All ZIPs completed!")
        merge_all_batches()
        return

    # Start browser
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        batch_dealers = []
        batch_num = progress["current_batch"] + 1

        try:
            for i, zip_code in enumerate(remaining_zips):
                print(f"\n[{i + 1}/{len(remaining_zips)}] Scraping ZIP {zip_code}...")

                dealers = scrape_zip(page, zip_code)

                if dealers:
                    batch_dealers.extend(dealers)
                    progress["completed_zips"].append(zip_code)
                    progress["total_collected"] += len(dealers)
                else:
                    # Mark as completed but track as failed
                    progress["completed_zips"].append(zip_code)
                    progress["failed_zips"].append(zip_code)

                save_progress(progress)

                # Save batch every 20 dealers
                if len(batch_dealers) >= BATCH_SIZE:
                    save_batch_csv(batch_num, batch_dealers)
                    batch_dealers = []
                    batch_num += 1
                    progress["current_batch"] = batch_num
                    save_progress(progress)

                # Random delay between ZIPs (human-like behavior)
                if i < len(remaining_zips) - 1:
                    delay = random.uniform(3.0, 6.0)
                    print(f"  ⏱  Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Save final batch
            if batch_dealers:
                save_batch_csv(batch_num, batch_dealers)

        finally:
            browser.close()

    # Merge results
    print("\n" + "=" * 70)
    print("MERGING RESULTS")
    print("=" * 70)
    total, final_file = merge_all_batches()

    print("\n" + "=" * 70)
    print("GENERAC COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs processed: {len(progress['completed_zips'])}")
    if progress.get('failed_zips'):
        print(f"Failed ZIPs: {len(progress['failed_zips'])} - {', '.join(progress['failed_zips'])}")
    print(f"Unique dealers: {total}")
    print(f"Output: {final_file}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_collection()
    except KeyboardInterrupt:
        print("\n\n⏸ Collection paused - progress saved")
        print("Run again to resume")
