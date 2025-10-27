#!/usr/bin/env python3
"""
Kohler Automated Collection - Local Playwright
Fully automated collection using local browser with proper timing

Following the proven Generac automation pattern:
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
from config import ZIP_CODES_SREC_ALL

# Configuration
KOHLER_URL = "https://www.kohlerhomeenergy.rehlko.com/find-a-dealer"
ZIP_INPUT_SELECTOR = "input[placeholder*='ZIP' i]"
SEARCH_BUTTON_SELECTOR = "button[type='submit']"
PROGRESS_FILE = "output/kohler_progress.json"
OUTPUT_DIR = "output"
BATCH_SIZE = 20

# All 140 SREC state ZIPs (15 states: CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
ZIP_CODES = list(ZIP_CODES_SREC_ALL)

# Kohler extraction script - to be refined after testing
EXTRACTION_SCRIPT = """
() => {
    // Extract all dealer cards from the page
    const dealerCards = Array.from(document.querySelectorAll('[class*="dealer"], [class*="result"], [class*="card"]'));

    return dealerCards.map(card => {
        const text = card.textContent;

        // Extract name (usually first heading or strong text)
        const nameEl = card.querySelector('h3, h4, h2, strong, [class*="name"]');
        const name = nameEl ? nameEl.textContent.trim() : '';

        // Extract phone
        const phoneEl = card.querySelector('a[href^="tel:"]');
        const phone = phoneEl ? phoneEl.textContent.trim() : '';

        // Extract website
        const websiteEl = card.querySelector('a[href^="http"]');
        const website = websiteEl ? websiteEl.href : '';

        // Extract domain from website
        let domain = '';
        if (website) {
            try {
                const url = new URL(website);
                domain = url.hostname.replace('www.', '');
            } catch (e) {
                domain = '';
            }
        }

        // Extract address
        const addressEl = card.querySelector('[class*="address"]');
        const address = addressEl ? addressEl.textContent.trim() : '';

        // Try to parse city/state from address
        let city = '';
        let state = '';
        let zip = '';
        if (address) {
            const parts = address.split(',');
            if (parts.length >= 2) {
                city = parts[parts.length - 2].trim();
                const lastPart = parts[parts.length - 1].trim().split(/\\s+/);
                state = lastPart[0] || '';
                zip = lastPart[1] || '';
            }
        }

        return {
            name: name,
            phone: phone,
            website: website,
            domain: domain,
            street: '',
            city: city,
            state: state,
            zip: zip,
            address_full: address,
            rating: 0,
            review_count: 0,
            tier: 'Authorized Kohler Dealer',
            certifications: 'Kohler Home Energy Dealer',
            distance: '',
            distance_miles: 0
        };
    }).filter(dealer => dealer.name && dealer.phone);
}
"""


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
    filename = f"{OUTPUT_DIR}/kohler_batch_{batch_num:03d}.csv"

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
    batch_files = sorted(Path(OUTPUT_DIR).glob("kohler_batch_*.csv"))

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
        final_filename = f"{OUTPUT_DIR}/kohler_dealers_{timestamp}.csv"

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
    """Scrape Kohler dealers for a single ZIP"""
    try:
        # Navigate to Kohler dealer locator
        print(f"    Navigating to Kohler dealer locator...")
        page.goto(KOHLER_URL, timeout=60000, wait_until='domcontentloaded')
        # Skip networkidle wait - Kohler page has continuous background activity
        time.sleep(random.uniform(4.0, 6.0))

        # Wait for ZIP input
        print(f"    Waiting for ZIP input...")
        page.wait_for_selector(ZIP_INPUT_SELECTOR, state='visible', timeout=60000)
        time.sleep(random.uniform(1.0, 2.0))

        # Fill ZIP code
        zip_input = page.locator(ZIP_INPUT_SELECTOR).first
        zip_input.click()
        time.sleep(random.uniform(0.5, 1.0))

        print(f"    Filling ZIP: {zip_code}")
        zip_input.fill(zip_code)
        time.sleep(random.uniform(1.0, 2.0))

        # Click search button
        print(f"    Clicking search button...")
        search_button = page.locator(SEARCH_BUTTON_SELECTOR).first
        search_button.click()

        # Wait for AJAX results to load
        print(f"    Waiting for results...")
        time.sleep(random.uniform(5.0, 7.0))

        # Extract dealers using extraction script
        print(f"    Extracting dealers...")
        dealers = page.evaluate(EXTRACTION_SCRIPT)

        # Add metadata to each dealer
        for dealer in dealers:
            dealer['scraped_from_zip'] = zip_code
            dealer['oem_source'] = 'Kohler'

        print(f"    ✓ Found {len(dealers)} dealers")
        return dealers

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def run_collection():
    """Main collection workflow"""
    print("=" * 70)
    print("KOHLER LOCAL PLAYWRIGHT COLLECTION - ALL SREC STATES")
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
    print("KOHLER COLLECTION COMPLETE")
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
