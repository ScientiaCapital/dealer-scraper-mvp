#!/usr/bin/env python3
"""
SolarEdge Automated Collection - Local Playwright
Fully automated collection using local browser with proper timing

This follows the proven Tesla/Generac automation pattern:
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
SOLAREDGE_URL = "https://www.solaredge.com/us/find-installer"
COOKIE_ACCEPT_SELECTOR = "button:has-text('Accept'), button:has-text('I agree')"
ZIP_INPUT_SELECTOR = "input[placeholder*='Address' i], input[placeholder*='ZIP' i]"
SEARCH_BUTTON_SELECTOR = "button:has-text('Find an Installer')"
PROGRESS_FILE = "output/solaredge_progress.json"
OUTPUT_DIR = "output"
BATCH_SIZE = 20

# All 140 SREC state ZIPs (15 states: CA, TX, PA, MA, NJ, FL, NY, OH, MD, DC, DE, NH, RI, CT, IL)
ZIP_CODES = list(ZIP_CODES_SREC_ALL)

# SolarEdge extraction script
EXTRACTION_SCRIPT = """
() => {
    const cards = Array.from(document.querySelectorAll('[class*="installer"], [class*="dealer"], [class*="result"]')).slice(0, 50);

    return cards.map(card => {
        const text = card.textContent;

        const nameEl = card.querySelector('h3, h4, h2, strong, [class*="name"]');
        const name = nameEl ? nameEl.textContent.trim() : '';

        const phoneEl = card.querySelector('a[href^="tel:"]');
        const phone = phoneEl ? phoneEl.textContent.trim() : '';

        const websiteEl = card.querySelector('a[href^="http"]');
        const website = websiteEl ? websiteEl.href : '';

        const addressEl = card.querySelector('[class*="address"]');
        const address = addressEl ? addressEl.textContent.trim() : '';

        // Extract domain
        let domain = '';
        if (website) {
            try {
                const url = new URL(website);
                domain = url.hostname.replace('www.', '');
            } catch (e) {
                domain = '';
            }
        }

        // Parse city/state from address
        let city = '';
        let state = '';
        let zip = '';
        if (address) {
            const parts = address.split(',');
            if (parts.length >= 2) {
                city = parts[parts.length - 2].trim();
                const lastPart = parts[parts.length - 1].trim().split(/\s+/);
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
            tier: 'Certified',
            certifications: 'SolarEdge Certified Installer',
            distance: '',
            distance_miles: 0
        };
    }).filter(i => i.name && i.phone);
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


def save_batch_csv(batch_num, installers):
    filename = f"{OUTPUT_DIR}/solaredge_batch_{batch_num:03d}.csv"

    if not installers:
        return filename

    fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                  'state', 'zip', 'address_full', 'rating', 'review_count',
                  'tier', 'certifications', 'distance', 'distance_miles',
                  'scraped_from_zip', 'oem_source']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(installers)

    print(f"  ✓ Saved {len(installers)} installers to {filename}")
    return filename


def merge_all_batches():
    batch_files = sorted(Path(OUTPUT_DIR).glob("solaredge_batch_*.csv"))

    if not batch_files:
        print("⚠ No batch files to merge")
        return 0, None

    all_installers = []
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            all_installers.extend(list(reader))

    # Deduplicate by phone number (digits only)
    unique_installers = {}
    for installer in all_installers:
        phone = installer.get('phone', '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        if phone and phone not in unique_installers:
            unique_installers[phone] = installer

    final_installers = list(unique_installers.values())

    if final_installers:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{OUTPUT_DIR}/solaredge_installers_{timestamp}.csv"

        fieldnames = ['name', 'phone', 'website', 'domain', 'street', 'city',
                      'state', 'zip', 'address_full', 'rating', 'review_count',
                      'tier', 'certifications', 'distance', 'distance_miles',
                      'scraped_from_zip', 'oem_source']

        with open(final_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_installers)

        print(f"\n✓ Merged {len(batch_files)} batch files")
        print(f"  Total unique installers: {len(final_installers)}")
        print(f"  Output: {final_filename}")
        return len(final_installers), final_filename

    return 0, None


def scrape_zip(page, zip_code):
    """Scrape SolarEdge installers for a single ZIP"""
    try:
        # Navigate to SolarEdge installer finder
        print(f"    Navigating to SolarEdge installer finder...")
        page.goto(SOLAREDGE_URL, timeout=60000, wait_until='domcontentloaded')
        # Note: Skip networkidle wait - Google Maps keeps loading indefinitely
        time.sleep(random.uniform(4.0, 6.0))

        # CRITICAL: Remove cookie banner FIRST (more reliable than clicking)
        print(f"    Removing cookie banner...")
        page.evaluate("""
            () => {
                const banner = document.querySelector('#onetrust-consent-sdk');
                if (banner) banner.remove();
                const overlays = document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="cookie"]');
                overlays.forEach(o => o.remove());
            }
        """)
        time.sleep(random.uniform(1.0, 2.0))

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

        # Click search button with JavaScript (more reliable than Playwright click)
        print(f"    Clicking search button...")
        page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const button = buttons.find(b => b.textContent.includes('Find an Installer'));
                if (button) button.click();
            }
        """)

        # Wait for AJAX results to load
        print(f"    Waiting for results...")
        time.sleep(random.uniform(6.0, 8.0))

        # Extract installers using extraction script
        print(f"    Extracting installers...")
        installers = page.evaluate(EXTRACTION_SCRIPT)

        # Add metadata to each installer
        for installer in installers:
            installer['scraped_from_zip'] = zip_code
            installer['oem_source'] = 'SolarEdge'

        print(f"    ✓ Found {len(installers)} installers")
        return installers

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def run_collection():
    """Main collection workflow"""
    print("=" * 70)
    print("SOLAREDGE LOCAL PLAYWRIGHT COLLECTION - ALL SREC STATES")
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

        batch_installers = []
        batch_num = progress["current_batch"] + 1

        try:
            for i, zip_code in enumerate(remaining_zips):
                print(f"\n[{i + 1}/{len(remaining_zips)}] Scraping ZIP {zip_code}...")

                installers = scrape_zip(page, zip_code)

                if installers:
                    batch_installers.extend(installers)
                    progress["completed_zips"].append(zip_code)
                    progress["total_collected"] += len(installers)
                else:
                    # Mark as completed but track as failed
                    progress["completed_zips"].append(zip_code)
                    progress["failed_zips"].append(zip_code)

                save_progress(progress)

                # Save batch every 20 installers
                if len(batch_installers) >= BATCH_SIZE:
                    save_batch_csv(batch_num, batch_installers)
                    batch_installers = []
                    batch_num += 1
                    progress["current_batch"] = batch_num
                    save_progress(progress)

                # Random delay between ZIPs (human-like behavior)
                if i < len(remaining_zips) - 1:
                    delay = random.uniform(3.0, 6.0)
                    print(f"  ⏱  Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Save final batch
            if batch_installers:
                save_batch_csv(batch_num, batch_installers)

        finally:
            browser.close()

    # Merge results
    print("\n" + "=" * 70)
    print("MERGING RESULTS")
    print("=" * 70)
    total, final_file = merge_all_batches()

    print("\n" + "=" * 70)
    print("SOLAREDGE COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs processed: {len(progress['completed_zips'])}")
    if progress.get('failed_zips'):
        print(f"Failed ZIPs: {len(progress['failed_zips'])} - {', '.join(progress['failed_zips'])}")
    print(f"Unique installers: {total}")
    print(f"Output: {final_file}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_collection()
    except KeyboardInterrupt:
        print("\n\n⏸ Collection paused - progress saved")
        print("Run again to resume")
