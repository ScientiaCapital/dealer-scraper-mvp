#!/usr/bin/env python3
"""
NJ Scraper - Get ALL Contractors at Once

Selects "All" professions to avoid pagination, then filters for MEP+Energy trades.
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

# Target professions for filtering
TARGET_PROFESSIONS = [
    "Electrical Contractors",
    "Master Plumbers",
    "HVACR",
    "Home Improvement Contractors"
]


def parse_html_for_contractors(html_content):
    """Parse HTML content using regex."""

    contractors = []

    # NJ HTML pattern
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
            'source': 'NJ-MyLicense'
        })

    return contractors


async def scrape_all_contractors():
    """Scrape ALL contractors by selecting 'All' professions."""

    print("🔍 Scraping ALL NJ Contractors...")

    async with async_playwright() as p:
        print("   Launching browser...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        try:
            # Navigate
            print("   Navigating to portal...")
            await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Select "All" professions (value="")
            print("   Selecting 'All' professions...")
            await page.select_option("#t_web_lookup__profession_name", value="")
            await asyncio.sleep(2)

            # Click search
            print("   Clicking search...")
            try:
                await page.click("input[type='submit'][value='Search']", timeout=5000)
            except:
                pass

            await asyncio.sleep(15)  # Wait for massive result set

            # Screenshot
            await page.screenshot(path=OUTPUT_DIR / "nj_all_contractors.png")
            print("   📸 Screenshot saved")

            # Get HTML
            print("   Getting HTML content...")
            html_content = await page.content()

            with open(OUTPUT_DIR / "nj_all_contractors.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   💾 HTML saved ({len(html_content):,} bytes)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            await browser.close()
            return []

        await browser.close()

    # Parse HTML
    print("   Parsing HTML...")
    all_contractors = parse_html_for_contractors(html_content)

    print(f"\n   ✅ Found {len(all_contractors):,} total contractors")

    # Filter to MEP+Energy professions
    mep_contractors = [c for c in all_contractors if c['profession'] in TARGET_PROFESSIONS]
    print(f"   ✅ Filtered to {len(mep_contractors):,} MEP+Energy contractors")

    # Filter to Active only
    active_contractors = [c for c in mep_contractors if c['license_status'].lower() == 'active']
    print(f"   ✅ Active licenses: {len(active_contractors):,}")

    # Breakdown by profession
    profession_counts = {}
    for c in active_contractors:
        prof = c['profession']
        profession_counts[prof] = profession_counts.get(prof, 0) + 1

    print(f"\n   📊 Breakdown:")
    for prof, count in sorted(profession_counts.items()):
        print(f"      - {prof}: {count:,}")

    # Save to CSV
    output_file = OUTPUT_DIR / f"nj_mep_contractors_{DATE_SUFFIX}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if active_contractors:
            writer = csv.DictWriter(f, fieldnames=active_contractors[0].keys())
            writer.writeheader()
            writer.writerows(active_contractors)

    print(f"\n   📄 Saved to: {output_file.name}")

    return active_contractors


async def main():
    print("=" * 80)
    print("NEW JERSEY MEP+ENERGY CONTRACTOR SCRAPER")
    print("=" * 80)

    contractors = await scrape_all_contractors()

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\n✅ Total active MEP+Energy contractors: {len(contractors):,}")


if __name__ == "__main__":
    asyncio.run(main())
