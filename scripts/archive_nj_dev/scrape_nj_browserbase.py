#!/usr/bin/env python3
"""
New Jersey Contractor License Scraper - Browserbase Version

Uses Browserbase cloud browser to scrape NJ contractor licenses.
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import os
from pathlib import Path
from datetime import datetime

# Configuration
NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATE_SUFFIX = datetime.now().strftime("%Y%m%d")

# Browserbase credentials from .env
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

# Target professions
PROFESSIONS = [
    "Electrical Contractors",
    "HVACR",
    "Home Improvement Contractors"
]


async def scrape_profession_browserbase(profession):
    """Scrape using Browserbase cloud browser."""

    print(f"\n🔍 Scraping: {profession}")

    async with async_playwright() as p:
        # Connect to Browserbase
        print(f"   Connecting to Browserbase...")
        browser = await p.chromium.connect_over_cdp(
            f"wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&projectId={BROWSERBASE_PROJECT_ID}"
        )

        context = browser.contexts[0]
        page = context.pages[0]

        # Navigate to NJ portal
        print(f"   Navigating to: {NJ_PORTAL_URL}")
        await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Select profession
        print(f"   Selecting profession: {profession}")
        await page.select_option("#t_web_lookup__profession_name", label=profession)
        await asyncio.sleep(1)

        # Click search
        print(f"   Clicking search...")
        await page.click("input[type='submit'][value='Search']")
        await asyncio.sleep(10)  # Wait for AJAX results

        # Take screenshot for debugging
        safe_prof_name = profession.replace(" ", "_").lower()
        screenshot_path = OUTPUT_DIR / f"browserbase_{safe_prof_name}.png"
        await page.screenshot(path=screenshot_path)
        print(f"   📸 Screenshot saved: {screenshot_path.name}")

        # Extract contractors using simple table row parsing
        print(f"   Extracting contractors...")
        contractors = await page.evaluate("""
            () => {
                const results = [];

                // Find all table rows
                const rows = document.querySelectorAll('table tbody tr, table tr');

                console.log(`Found ${rows.length} table rows`);

                for (const row of rows) {
                    const cells = row.querySelectorAll('td');

                    // Skip if not enough cells
                    if (cells.length < 7) continue;

                    // Extract text from each cell
                    const cellTexts = Array.from(cells).map(cell => cell.textContent.trim());

                    // Check if this looks like a data row (has a license number pattern in cell 1)
                    const licensePattern = /^(34[A-Z]{2}\\d{7,8}|13VH\\d{7,8}|T-\\d+)$/;

                    if (cellTexts[1] && licensePattern.test(cellTexts[1])) {
                        results.push({
                            business_name: cellTexts[0] || '',
                            license_number: cellTexts[1] || '',
                            profession: cellTexts[2] || '',
                            license_type: cellTexts[3] || '',
                            license_status: cellTexts[4] || '',
                            city: cellTexts[5] || '',
                            state: cellTexts[6] || '',
                            phone: null,
                            source: 'NJ-MyLicense-Browserbase'
                        });
                    }
                }

                return results;
            }
        """)

        # Filter to Active licenses only
        active_contractors = [c for c in contractors if c['license_status'].lower() == 'active']

        print(f"   ✅ Found {len(contractors):,} total contractors")
        print(f"   ✅ Filtered to {len(active_contractors):,} Active licenses")

        # Show sample
        if active_contractors:
            print(f"   📋 Sample:")
            sample = active_contractors[0]
            print(f"      Name: {sample['business_name']}")
            print(f"      License: {sample['license_number']}")
            print(f"      Status: {sample['license_status']}")

        # Save to CSV
        safe_profession_name = profession.replace(" ", "_").replace("/", "_").lower()
        output_file = OUTPUT_DIR / f"nj_{safe_profession_name}_browserbase_{DATE_SUFFIX}.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if active_contractors:
                writer = csv.DictWriter(f, fieldnames=active_contractors[0].keys())
                writer.writeheader()
                writer.writerows(active_contractors)

        print(f"   📄 Saved to: {output_file.name}")

        await browser.close()

        return active_contractors


async def main():
    print("=" * 80)
    print("NEW JERSEY CONTRACTOR LICENSE SCRAPER (BROWSERBASE)")
    print("=" * 80)

    if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
        print("\n❌ Error: Browserbase credentials not found in .env")
        print("   Please set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID")
        return

    print(f"\n✅ Browserbase configured")
    print(f"   Project ID: {BROWSERBASE_PROJECT_ID[:20]}...")
    print(f"\nTarget professions: {len(PROFESSIONS)}")
    for prof in PROFESSIONS:
        print(f"  - {prof}")

    all_contractors = []

    # Scrape each profession
    for profession in PROFESSIONS:
        try:
            contractors = await scrape_profession_browserbase(profession)
            all_contractors.extend(contractors)
        except Exception as e:
            print(f"   ❌ Error scraping {profession}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Save combined file
    if all_contractors:
        combined_file = OUTPUT_DIR / f"nj_mep_contractors_combined_browserbase_{DATE_SUFFIX}.csv"

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
