#!/usr/bin/env python3
"""
NJ Scraper - Direct HTML Parsing Approach

Since the data is clearly rendering in screenshots, let's get the raw HTML
and parse it with Python regex instead of relying on JavaScript extraction.
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import re
from pathlib import Path
from datetime import datetime

# Configuration
NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATE_SUFFIX = datetime.now().strftime("%Y%m%d")

PROFESSIONS = ["Electrical Contractors", "HVACR", "Home Improvement Contractors"]


def parse_html_for_contractors(html_content):
    """Parse HTML content using regex to extract contractor data."""

    contractors = []

    # Pattern for NJ's actual HTML structure:
    # <a href="Details.aspx...">BUSINESS_NAME</a> ... <td><span>LICENSE</span></td><td><span>PROFESSION</span></td>...
    # Using lookahead to find business name, then match the data fields that follow

    # First, find all contractor records (each starts with a Details.aspx link)
    record_pattern = r'<a[^>]+href="Details\.aspx[^"]*">([^<]+)</a>.*?</td><td><span>(34[A-Z]{2}\d{7,8}|13VH\d{7,8}|T-\d+)</span></td><td><span>([^<]+)</span></td><td><span>([^<]*)</span></td><td><span>(Active|Closed|Pending|Expired|Deleted)</span></td><td><span>([^<]*)</span></td><td><span>([A-Z]{2})</span></td>'

    matches = re.findall(record_pattern, html_content, re.DOTALL)

    for match in matches:
        business_name, license_number, profession, license_type, status, city, state = match

        contractors.append({
            'business_name': business_name.strip(),
            'license_number': license_number.strip(),
            'profession': profession.strip(),
            'license_type': license_type.strip(),
            'license_status': status.strip(),
            'city': city.strip(),
            'state': state.strip(),
            'phone': None,
            'source': 'NJ-MyLicense-HTMLParse'
        })

    return contractors


async def scrape_profession(profession):
    """Scrape contractors for a profession using direct HTML parsing."""

    print(f"\n🔍 Scraping: {profession}")

    # Create FRESH browser instance for each profession to avoid session/rate limiting issues
    async with async_playwright() as p:
        print(f"   Launching fresh browser instance...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )

        # Navigate and search
        print(f"   Navigating to portal...")
        await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # Extra wait for initial page load

        print(f"   Selecting profession: {profession}")
        await page.select_option("#t_web_lookup__profession_name", label=profession)
        await asyncio.sleep(2)

        print(f"   Clicking search...")
        # Use force_click to bypass navigation wait issues
        await page.locator("input[type='submit'][value='Search']").click(force=True)
        await asyncio.sleep(12)  # Wait for AJAX results to load

        # Take screenshot
        safe_prof_name = profession.replace(" ", "_").lower()
        screenshot_path = OUTPUT_DIR / f"htmlparse_{safe_prof_name}.png"
        await page.screenshot(path=screenshot_path)
        print(f"   📸 Screenshot: {screenshot_path.name}")

        # Get the RAW HTML content
        print(f"   Getting HTML content...")
        html_content = await page.content()

        # Save HTML for debugging
        html_file = OUTPUT_DIR / f"htmlparse_{safe_prof_name}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   💾 HTML saved: {html_file.name} ({len(html_content):,} bytes)")

        await browser.close()
        print(f"   Browser closed")

    # Parse HTML with Python regex
    print(f"   Parsing HTML with regex...")
    contractors = parse_html_for_contractors(html_content)

    # Filter to Active only
    active_contractors = [c for c in contractors if c['license_status'].lower() == 'active']

    print(f"   ✅ Found {len(contractors):,} total contractors")
    print(f"   ✅ Filtered to {len(active_contractors):,} Active licenses")

    if active_contractors:
        print(f"   📋 Sample:")
        sample = active_contractors[0]
        print(f"      Name: {sample['business_name']}")
        print(f"      License: {sample['license_number']}")
        print(f"      Status: {sample['license_status']}")

    # Save to CSV
    safe_profession_name = profession.replace(" ", "_").replace("/", "_").lower()
    output_file = OUTPUT_DIR / f"nj_{safe_profession_name}_htmlparse_{DATE_SUFFIX}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if active_contractors:
            writer = csv.DictWriter(f, fieldnames=active_contractors[0].keys())
            writer.writeheader()
            writer.writerows(active_contractors)

    print(f"   📄 Saved to: {output_file.name}")

    return active_contractors


async def main():
    print("=" * 80)
    print("NEW JERSEY CONTRACTOR LICENSE SCRAPER (HTML PARSING)")
    print("=" * 80)

    all_contractors = []

    # Scrape each profession
    for profession in PROFESSIONS:
        try:
            contractors = await scrape_profession(profession)
            all_contractors.extend(contractors)
        except Exception as e:
            print(f"   ❌ Error scraping {profession}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Save combined file
    if all_contractors:
        combined_file = OUTPUT_DIR / f"nj_mep_contractors_combined_htmlparse_{DATE_SUFFIX}.csv"

        with open(combined_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_contractors[0].keys())
            writer.writeheader()
            writer.writerows(all_contractors)

        print(f"\n✅ Combined file: {combined_file.name}")

    # Summary
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   - Total contractors scraped: {len(all_contractors):,}")

    # Breakdown by profession
    profession_counts = {}
    for c in all_contractors:
        prof = c['profession']
        profession_counts[prof] = profession_counts.get(prof, 0) + 1

    for prof, count in profession_counts.items():
        print(f"   - {prof}: {count:,}")

    print(f"\n📁 Files saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
