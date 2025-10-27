#!/usr/bin/env python3
"""
Tesla Automated Collection - Local Playwright
Fully automated collection using local browser with proper timing

This bypasses Browserbase issues and uses local Playwright with:
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
TESLA_URL = "https://www.tesla.com/support/certified-installers?productType=powerwall"
ZIP_INPUT_SELECTOR = 'input[role="combobox"]'
LISTBOX_SELECTOR = 'div[role="listbox"]'
INSTALLER_CARD_SELECTOR = '.styles_ciContainer__58zW_'
PROGRESS_FILE = "output/tesla_local_progress.json"
OUTPUT_DIR = "output"
BATCH_SIZE = 20

# Extraction script
EXTRACTION_SCRIPT = """
() => {
    const cards = document.querySelectorAll('.styles_ciContainer__58zW_');

    const installers = Array.from(cards).map(card => {
        const text = card.innerText;
        const lines = text.split('\\n').filter(l => l.trim());

        const tier = lines[0] || '';
        const name = lines[1] || '';
        const phone = lines[2] || '';
        const website = lines[3] || '';
        const email = lines[4] || '';

        let domain = '';
        if (website && website.startsWith('http')) {
            try {
                const url = new URL(website);
                domain = url.hostname.replace('www.', '');
            } catch (e) {
                domain = '';
            }
        }

        let formattedPhone = phone;
        if (phone && phone.length === 10 && /^\\d{10}$/.test(phone)) {
            formattedPhone = `(${phone.substring(0,3)}) ${phone.substring(3,6)}-${phone.substring(6,10)}`;
        }

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


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_zips": [], "current_batch": 0, "total_collected": 0}


def save_progress(progress):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def save_batch_csv(batch_num, installers):
    filename = f"{OUTPUT_DIR}/tesla_local_batch_{batch_num:03d}.csv"

    if not installers:
        return filename

    fieldnames = ['name', 'phone', 'website', 'domain', 'email', 'tier',
                  'certifications', 'scraped_from_zip', 'oem_source']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(installers)

    print(f"  ✓ Saved {len(installers)} installers to {filename}")
    return filename


def merge_all_batches():
    batch_files = sorted(Path(OUTPUT_DIR).glob("tesla_local_batch_*.csv"))

    if not batch_files:
        print("⚠ No batch files to merge")
        return 0

    all_installers = []
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            all_installers.extend(list(reader))

    unique_installers = {}
    for installer in all_installers:
        phone = installer.get('phone', '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        if phone and phone not in unique_installers:
            unique_installers[phone] = installer

    final_installers = list(unique_installers.values())

    if final_installers:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{OUTPUT_DIR}/tesla_local_{timestamp}.csv"

        fieldnames = ['name', 'phone', 'website', 'domain', 'email', 'tier',
                      'certifications', 'scraped_from_zip', 'oem_source']

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
    """Scrape Tesla installers for a single ZIP"""
    try:
        # Navigate to Tesla page
        print(f"    Navigating to Tesla page...")
        page.goto(TESLA_URL, timeout=60000, wait_until='domcontentloaded')
        time.sleep(random.uniform(3.0, 4.0))

        # Wait for network idle
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(random.uniform(2.0, 3.0))

        # Select United States if it appears
        try:
            us_button = page.locator('button:has-text("United States")')
            if us_button.is_visible(timeout=3000):
                print(f"    Selecting United States...")
                us_button.click()
                time.sleep(random.uniform(2.0, 3.0))
                page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass

        # Wait for ZIP input
        print(f"    Waiting for ZIP input...")
        page.wait_for_selector(ZIP_INPUT_SELECTOR, state='visible', timeout=60000)
        time.sleep(random.uniform(1.0, 2.0))

        # Type ZIP code slowly
        zip_input = page.locator(ZIP_INPUT_SELECTOR)
        zip_input.click()
        time.sleep(random.uniform(0.5, 1.0))

        print(f"    Typing ZIP: {zip_code}")
        for char in zip_code:
            zip_input.type(char, delay=random.randint(100, 250))

        time.sleep(random.uniform(1.0, 2.0))

        # Try autocomplete first
        try:
            page.wait_for_selector(LISTBOX_SELECTOR, state='visible', timeout=5000)
            time.sleep(random.uniform(0.5, 1.0))

            first_option = page.locator('div[role="listbox"] div[role="option"]').first
            first_option.click()
            print(f"    Clicked autocomplete")
        except:
            print(f"    Pressing Enter")
            zip_input.press('Enter')

        # Wait for results to load
        print(f"    Waiting for results...")
        time.sleep(random.uniform(6.0, 8.0))

        # Scroll to trigger lazy loading
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(random.uniform(2.0, 3.0))
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(random.uniform(2.0, 3.0))

        # Extract installers
        print(f"    Extracting installers...")
        installers = page.evaluate(EXTRACTION_SCRIPT)

        # Add ZIP to each
        for installer in installers:
            installer['scraped_from_zip'] = zip_code

        print(f"    ✓ Found {len(installers)} installers")
        return installers

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def run_collection():
    """Main collection workflow"""
    # Use all 140 SREC state ZIPs
    all_zips = list(ZIP_CODES_SREC_ALL)

    print("=" * 70)
    print("TESLA LOCAL PLAYWRIGHT COLLECTION - ALL SREC STATES")
    print("=" * 70)
    print(f"Total ZIPs: {len(all_zips)} (15 SREC states)")
    print()

    # Load progress
    progress = load_progress()
    remaining_zips = [z for z in all_zips if z not in progress["completed_zips"]]

    if len(remaining_zips) < len(all_zips):
        print(f"📋 RESUMING: {len(progress['completed_zips'])} ZIPs completed")
        print(f"   Remaining: {len(remaining_zips)} ZIPs")
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

                batch_installers.extend(installers)
                progress["completed_zips"].append(zip_code)
                progress["total_collected"] += len(installers)

                save_progress(progress)

                # Save batch every 20 ZIPs
                if len(batch_installers) >= BATCH_SIZE:
                    save_batch_csv(batch_num, batch_installers)
                    batch_installers = []
                    batch_num += 1
                    progress["current_batch"] = batch_num
                    save_progress(progress)

                # Random delay between ZIPs
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
    print("TESLA COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Total ZIPs: {len(progress['completed_zips'])}")
    print(f"Unique installers: {total}")
    print(f"Output: {final_file}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_collection()
    except KeyboardInterrupt:
        print("\n\n⏸ Collection paused - progress saved")
        print("Run again to resume")
