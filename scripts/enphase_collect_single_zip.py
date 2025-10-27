#!/usr/bin/env python3
"""
Enphase Single ZIP Collector
Automated Playwright script to collect all tiers (Platinum, Gold, Silver) from one ZIP
"""
import asyncio
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Configuration
PROGRESS_FILE = "output/enphase_platinum_gold_progress.json"
OUTPUT_CSV = "output/enphase_platinum_gold_installers.csv"
BASE_URL = "https://enphase.com/installer-locator"

CSV_HEADERS = [
    "name", "phone", "website", "domain", "email",
    "tier", "certifications", "oem_source",
    "scraped_from_zip", "state", "collection_date",
    "address_full", "city", "rating", "years_experience", "warranty_years",
    "has_solar", "has_storage", "has_commercial", "has_ev_charger", "has_ops_maintenance"
]

def extract_domain(website):
    """Extract root domain from URL"""
    if not website:
        return ""
    domain = re.sub(r'https?://', '', website)
    domain = re.sub(r'^www\.', '', domain)
    domain = domain.split('/')[0]
    return domain

def parse_city_state(address):
    """Parse city and state from full address"""
    if not address:
        return "", ""
    parts = address.split(',')
    if len(parts) >= 2:
        city = parts[-2].strip()
        state_zip = parts[-1].strip().split()
        state = state_zip[0] if state_zip else ""
        return city, state
    return "", ""

def is_zip_already_collected(zip_code):
    """
    Check if ZIP was already collected by reading the CSV directly
    Single source of truth: what's in the CSV
    """
    csv_path = Path(OUTPUT_CSV)
    if not csv_path.exists():
        return False
    
    with open(OUTPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('scraped_from_zip', '').strip() == zip_code:
                return True
    return False

async def collect_zip_code(zip_code):
    """Collect all installers from a single ZIP code"""

    async with async_playwright() as p:
        # Launch browser
        print(f"\n🚀 Launching browser for ZIP {zip_code}...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Navigate to Enphase installer locator
            print(f"📍 Navigating to {BASE_URL}")
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')

            # Enter ZIP code
            print(f"🔍 Searching for ZIP {zip_code}...")
            await page.get_by_role('textbox', name='Enter your ZIP').fill(zip_code)
            await page.get_by_role('button', name='Find an installer').click()
            await asyncio.sleep(3)  # Wait for results

            # Extract installer IDs and tiers from list view
            print("📋 Extracting installer IDs...")
            installer_list = await page.evaluate("""
                () => {
                    const cards = Array.from(document.querySelectorAll('[data-installer-id]'));
                    return cards.map(card => {
                        const id = card.getAttribute('data-installer-id');
                        const tierImg = card.querySelector('img[alt="platinum"], img[alt="gold"], img[alt="silver"]');
                        const tier = tierImg ? tierImg.getAttribute('alt') : '';
                        return { id, tier };
                    }).filter(inst => inst.id && inst.tier);
                }
            """)

            print(f"✅ Found {len(installer_list)} installers:")
            tier_counts = {}
            for inst in installer_list:
                tier_counts[inst['tier']] = tier_counts.get(inst['tier'], 0) + 1
            for tier, count in tier_counts.items():
                print(f"   - {tier.capitalize()}: {count}")

            # Collect data from each installer
            collected = []
            for idx, installer in enumerate(installer_list, 1):
                print(f"\n[{idx}/{len(installer_list)}] Processing {installer['tier']} installer (ID: {installer['id']})...")

                # Click on installer card to open detail modal
                cards = await page.query_selector_all('[data-installer-id]')
                target_card = None
                for card in cards:
                    card_id = await card.get_attribute('data-installer-id')
                    if card_id == installer['id']:
                        target_card = card
                        break

                if not target_card:
                    print(f"   ⚠️  Could not find card for ID {installer['id']}, skipping...")
                    continue

                # Try to click the card with error handling
                try:
                    # Scroll card into view first
                    await target_card.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await target_card.click(timeout=10000)
                except Exception as e:
                    print(f"   ⚠️  Could not click card for ID {installer['id']} ({str(e)[:50]}...), skipping...")
                    continue

                # Wait for detail modal to fully load with actual data (not just structure)
                await asyncio.sleep(4)  # Initial wait
                
                # Wait for phone link with actual data (not "tel:null")
                try:
                    await page.wait_for_function(
                        """() => {
                            const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
                            for (const link of phoneLinks) {
                                if (link.href && link.href !== 'tel:null' && link.offsetParent !== null) {
                                    return true;  // Found visible phone link with real data
                                }
                            }
                            return false;
                        }""",
                        timeout=15000  # 15 seconds for Vue.js data binding
                    )
                except Exception as e:
                    print(f"      ⚠️  Modal data didn't load in time, skipping this installer...")
                    await page.keyboard.press('Escape')  # Close modal
                    await asyncio.sleep(1)
                    continue
                
                await asyncio.sleep(1)  # Extra buffer for all content

                # Extract data from detail page
                data = await page.evaluate("""
                    () => {
                        const allText = document.body.textContent;

                        // Name - from heading
                        const nameMatch = allText.match(/Back\\s+([\\w\\s&,\\.\\-()]+?)\\s+https:/);
                        const name = nameMatch ? nameMatch[1].trim() : '';

                        // Address
                        const addressEl = Array.from(document.querySelectorAll('generic')).find(el =>
                            el.textContent.includes('Road') || el.textContent.includes('Street') ||
                            el.textContent.includes('Avenue') || el.textContent.includes('Drive')
                        );
                        const address = addressEl ? addressEl.textContent.trim().split('\\n')[0] : '';

                        // Phone
                        const phoneLink = document.querySelector('a[href^="tel:"]');
                        const phone = phoneLink ? phoneLink.textContent.trim() : '';

                        // Website
                        const websiteLink = Array.from(document.querySelectorAll('a')).find(a =>
                            a.textContent.trim() === 'Website'
                        );
                        const website = websiteLink ? websiteLink.href : '';

                        // Email
                        const emailLink = document.querySelector('a[href^="mailto:"]');
                        const email = emailLink ? emailLink.href.replace('mailto:', '') : '';

                        // Rating
                        const ratingMatch = allText.match(/(\\d+\\.\\d+)\\s*\\/\\s*\\d+\\s*reviews?/i);
                        const rating = ratingMatch ? ratingMatch[1] : '';

                        // Years experience
                        const expMatch = allText.match(/(\\d+)\\s*years?\\s*experience/i);
                        const years_experience = expMatch ? parseInt(expMatch[1]) : 0;

                        // Warranty
                        const warMatch = allText.match(/(\\d+)\\s*years?\\s*labor\\s*warranty/i);
                        const warranty_years = warMatch ? parseInt(warMatch[1]) : 0;

                        // Services
                        const has_solar = allText.includes('Solar installation');
                        const has_storage = allText.includes('Storage installation');
                        const has_commercial = allText.includes('Commercial installation');
                        const has_ev_charger = allText.includes('EV charger');
                        const has_ops_maintenance = allText.includes('Ops & Maintenance');

                        return {
                            name, phone, website, email, address, rating,
                            years_experience, warranty_years,
                            has_solar, has_storage, has_commercial, has_ev_charger, has_ops_maintenance
                        };
                    }
                """)

                # Add tier and ZIP
                data['tier'] = installer['tier']
                data['id'] = installer['id']

                # Save immediately after extraction
                save_single_installer(data, zip_code)

                print(f"   ✅ {data['name']} - {data['phone']}")
                collected.append(data)

                # Wait a bit before going back
                await asyncio.sleep(2)

                # Go back to list view
                await page.get_by_role('button', name='Back', exact=True).click()
                await asyncio.sleep(3)  # Wait for list to reload

            # All installers already saved individually
            print(f"\n✅ Successfully collected {len(collected)} installers from ZIP {zip_code}")

        finally:
            await browser.close()

    return len(collected)

def save_single_installer(installer, zip_code):
    """Save a single installer to CSV immediately after extraction"""
    csv_path = Path(OUTPUT_CSV)
    write_header = not csv_path.exists()

    city, state = parse_city_state(installer.get('address', ''))
    domain = extract_domain(installer.get('website', ''))

    row = {
        "name": installer.get('name', ''),
        "phone": installer.get('phone', ''),
        "website": installer.get('website', ''),
        "domain": domain,
        "email": installer.get('email', ''),
        "tier": installer.get('tier', ''),
        "certifications": f"{installer.get('tier', '').capitalize()} Certified Installer",
        "oem_source": "Enphase",
        "scraped_from_zip": zip_code,
        "state": state,
        "collection_date": datetime.now().strftime('%Y-%m-%d'),
        "address_full": installer.get('address', ''),
        "city": city,
        "rating": installer.get('rating', ''),
        "years_experience": installer.get('years_experience', 0),
        "warranty_years": installer.get('warranty_years', 0),
        "has_solar": installer.get('has_solar', False),
        "has_storage": installer.get('has_storage', False),
        "has_commercial": installer.get('has_commercial', False),
        "has_ev_charger": installer.get('has_ev_charger', False),
        "has_ops_maintenance": installer.get('has_ops_maintenance', False)
    }

    with open(OUTPUT_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def save_to_csv(installers, zip_code):
    """Save installers to CSV file"""
    csv_path = Path(OUTPUT_CSV)
    write_header = not csv_path.exists()

    with open(OUTPUT_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
            writer.writeheader()

        for inst in installers:
            city, state = parse_city_state(inst.get('address', ''))
            domain = extract_domain(inst.get('website', ''))

            row = {
                "name": inst.get('name', ''),
                "phone": inst.get('phone', ''),
                "website": inst.get('website', ''),
                "domain": domain,
                "email": inst.get('email', ''),
                "tier": inst.get('tier', ''),
                "certifications": f"{inst.get('tier', '').capitalize()} Certified Installer",
                "oem_source": "Enphase",
                "scraped_from_zip": zip_code,
                "state": state,
                "collection_date": datetime.now().strftime('%Y-%m-%d'),
                "address_full": inst.get('address', ''),
                "city": city,
                "rating": inst.get('rating', ''),
                "years_experience": inst.get('years_experience', 0),
                "warranty_years": inst.get('warranty_years', 0),
                "has_solar": inst.get('has_solar', False),
                "has_storage": inst.get('has_storage', False),
                "has_commercial": inst.get('has_commercial', False),
                "has_ev_charger": inst.get('has_ev_charger', False),
                "has_ops_maintenance": inst.get('has_ops_maintenance', False)
            }
            writer.writerow(row)

def update_progress(zip_code, count):
    """Update progress tracker"""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
    else:
        progress = {
            "completed_zips": [],
            "remaining_zips": [],
            "current_batch": 0,
            "total_collected": 0
        }

    if zip_code not in progress['completed_zips']:
        progress['completed_zips'].append(zip_code)

    if zip_code in progress['remaining_zips']:
        progress['remaining_zips'].remove(zip_code)

    progress['total_collected'] = progress.get('total_collected', 0) + count

    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

    print(f"\n📊 Progress: {len(progress['completed_zips'])} ZIPs completed, {len(progress['remaining_zips'])} remaining")

async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 enphase_collect_single_zip.py <ZIP_CODE>")
        print("Example: python3 enphase_collect_single_zip.py 02482")
        sys.exit(1)

    zip_code = sys.argv[1]

    # CHECK CSV FIRST - single source of truth!
    if is_zip_already_collected(zip_code):
        print(f"⚠️  ZIP {zip_code} already collected (found in CSV)")
        print(f"   Skipping to avoid duplicating work")
        sys.exit(0)

    print("=" * 80)
    print("🔆 ENPHASE SINGLE ZIP COLLECTOR")
    print("=" * 80)
    print(f"ZIP Code: {zip_code}")
    print(f"Collecting: Platinum, Gold, Silver tiers")
    print("=" * 80)

    count = await collect_zip_code(zip_code)
    update_progress(zip_code, count)

    print("\n" + "=" * 80)
    print("✅ COLLECTION COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
