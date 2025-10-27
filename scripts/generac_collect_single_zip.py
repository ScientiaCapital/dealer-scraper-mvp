#!/usr/bin/env python3
"""
Generac Single ZIP Collector
Extracts ALL dealers from results page in one shot
"""
import asyncio
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

PROGRESS_FILE = "output/generac_progress.json"
OUTPUT_CSV = "output/generac_dealers.csv"
BASE_URL = "https://www.generac.com/dealer-locator/"

CSV_HEADERS = [
    "name", "phone", "website", "domain", "email",
    "tier", "certifications", "oem_source",
    "scraped_from_zip", "state", "collection_date",
    "address_full", "city", "rating", "review_count"
]

def extract_domain(website):
    if not website:
        return ""
    domain = re.sub(r'https?://', '', website)
    domain = re.sub(r'^www\.', '', domain)
    return domain.split('/')[0]

def parse_city_state(address):
    if not address:
        return "", ""
    parts = address.split(',')
    if len(parts) >= 2:
        city = parts[-2].strip()
        state = parts[-1].strip().split()[0] if parts[-1].strip() else ""
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
    async with async_playwright() as p:
        print(f"\n🚀 Launching browser for ZIP {zip_code}...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            print(f"📍 Navigating to {BASE_URL}")
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            
            # Remove cookie banner
            print("🍪 Removing cookie banner...")
            await page.evaluate("""
                () => {
                    const banner = document.querySelector('#onetrust-consent-sdk');
                    if (banner) banner.remove();
                    const overlays = document.querySelectorAll('[class*="overlay"], [class*="modal"]');
                    overlays.forEach(o => o.remove());
                }
            """)
            await asyncio.sleep(2)

            # Enter ZIP and search
            print(f"🔍 Searching for ZIP {zip_code}...")
            await page.fill("input[placeholder*='ZIP' i]", zip_code)
            await asyncio.sleep(1)
            await page.click("button:has-text('Search')", force=True)
            await asyncio.sleep(8)

            # Extract ALL dealers from results page in one shot
            print("📋 Extracting all dealer data from results page...")
            dealers_json = await page.evaluate("""
                () => {
                    // Simple approach: Find ALL listitems that contain phone links (dealer cards)
                    const allListItems = Array.from(document.querySelectorAll('li'));
                    const dealerCards = allListItems.filter(li => li.querySelector('a[href^="tel:"]'));

                    console.log(`Found ${dealerCards.length} dealer cards with phone numbers`);

                    return dealerCards.map(li => {
                        const text = li.textContent || '';

                        // Phone from tel: link
                        const phoneEl = li.querySelector('a[href^="tel:"]');
                        const phone = phoneEl ? phoneEl.textContent.trim() : '';

                        // Website - find HTTP links that aren't Google Maps
                        const links = Array.from(li.querySelectorAll('a[href^="http"]'));
                        const websiteLink = links.find(a =>
                            !a.href.includes('google.com') &&
                            !a.href.includes('maps.google') &&
                            a.textContent.toLowerCase().includes('.')
                        );
                        const website = websiteLink ? websiteLink.href : '';

                        // Name - extract from text, avoiding numbers/distances/ratings
                        const textLines = text.split('\\n').map(l => l.trim()).filter(l => l);
                        let name = '';
                        for (const line of textLines) {
                            // Skip pure numbers, distances ("15 mi"), ratings, addresses
                            if (line &&
                                !line.match(/^\\d+$/) &&  // pure number
                                !line.match(/^\\d+\\.?\\d* mi/) &&  // distance
                                !line.includes('out of') &&  // ratings
                                !line.includes('stars') &&
                                !phone.includes(line) &&  // not the phone
                                line.length > 3 &&
                                line.length < 100) {  // reasonable length
                                name = line;
                                break;
                            }
                        }

                        // Address - look for street indicators
                        let address = '';
                        for (const line of textLines) {
                            if (line && (
                                line.toLowerCase().includes(' blvd') ||
                                line.toLowerCase().includes(' st') ||
                                line.toLowerCase().includes(' ave') ||
                                line.toLowerCase().includes(' rd') ||
                                line.toLowerCase().includes(' dr') ||
                                line.toLowerCase().includes(' way') ||
                                line.toLowerCase().includes(' lane')
                            )) {
                                address = line;
                                break;
                            }
                        }

                        // Tier
                        let tier = 'Standard';
                        if (text.includes('Premier') || text.includes('PowerPro')) tier = 'Premier';
                        else if (text.includes('Elite Plus')) tier = 'Elite Plus';
                        else if (text.includes('Elite')) tier = 'Elite';

                        return {
                            name: name,
                            phone: phone,
                            website: website,
                            address: address,
                            tier: tier
                        };
                    }).filter(d => d.name && d.phone);
                }
            """)

            print(f"✅ Found {len(dealers_json)} dealers")

            # Save all dealers to CSV
            collected = []
            for dealer in dealers_json:
                save_single_dealer(dealer, zip_code)
                collected.append(dealer)
                print(f"   ✅ {dealer['name']} ({dealer['tier']})")

            print(f"\n✅ Collected {len(collected)} dealers from ZIP {zip_code}")

        finally:
            await browser.close()

    return len(collected)

def save_single_dealer(dealer, zip_code):
    csv_path = Path(OUTPUT_CSV)
    write_header = not csv_path.exists()

    city, state = parse_city_state(dealer.get('address', ''))
    domain = extract_domain(dealer.get('website', ''))

    row = {
        "name": dealer.get('name', ''),
        "phone": dealer.get('phone', ''),
        "website": dealer.get('website', ''),
        "domain": domain,
        "email": "",
        "tier": dealer.get('tier', ''),
        "certifications": f"{dealer.get('tier', '')} Dealer" if dealer.get('tier') else "",
        "oem_source": "Generac",
        "scraped_from_zip": zip_code,
        "state": state,
        "collection_date": datetime.now().strftime('%Y-%m-%d'),
        "address_full": dealer.get('address', ''),
        "city": city,
        "rating": "",
        "review_count": 0
    }

    with open(OUTPUT_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def update_progress(zip_code, count):
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
    else:
        progress = {"completed_zips": [], "remaining_zips": [], "total_collected": 0}

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
        print("Usage: python3 generac_collect_single_zip.py <ZIP_CODE>")
        sys.exit(1)

    zip_code = sys.argv[1]
    
    # CHECK CSV FIRST - single source of truth!
    if is_zip_already_collected(zip_code):
        print(f"⚠️  ZIP {zip_code} already collected (found in CSV)")
        print(f"   Skipping to avoid duplicating work")
        sys.exit(0)

    print("=" * 80)
    print("🏭 GENERAC SINGLE ZIP COLLECTOR")
    print("=" * 80)
    print(f"ZIP Code: {zip_code}")
    print("=" * 80)

    count = await collect_zip_code(zip_code)
    update_progress(zip_code, count)

    print("\n" + "=" * 80)
    print("✅ COLLECTION COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
