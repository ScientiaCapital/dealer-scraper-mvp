#!/usr/bin/env python3
"""
NYC DOB Active License Scraper

Extracts ACTIVE contractor licenses from NYC Department of Buildings.
Focus on MEP trades for Coperniq ICP matching.

License Types:
- P: MASTER PLUMBER (geothermal, radiant, solar thermal)
- A: ELECTRICAL CONTRACTOR (solar, battery, EV)
- O: OIL BURNER INSTALLER (HVAC, heat pumps)
- G: GENERAL CONTRACTOR (resimercial signal)
- F: FIRE SUPPRESSION CONTRACTOR (commercial signal)
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import csv
from datetime import datetime
import re

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_york" / "nyc_dob"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Priority license types for MEP+Energy ICP
LICENSE_TYPES = {
    "P": "MASTER PLUMBER",
    "A": "ELECTRICAL CONTRACTOR",
    "O": "OIL BURNER INSTALLER",
    "G": "GENERAL CONTRACTOR",
    "F": "FIRE SUPPRESSION CONTRACTOR",
}

BASE_URL = "https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet?vlfirst=N"


async def scrape_license_type_by_letter(page, license_code: str, license_name: str, letter: str) -> list:
    """Scrape licenses for a specific type and starting letter"""
    contractors = []

    try:
        # Navigate to search page
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1.5)

        # Select license type (use first dropdown)
        selects = await page.query_selector_all('select[name="licensetype"]')
        if selects:
            await selects[0].select_option(license_code)

        # Fill last name search
        name_inputs = await page.query_selector_all('input[name="licname"]')
        if name_inputs:
            await name_inputs[0].fill(letter)

        # Click first GO button
        go_buttons = await page.query_selector_all('input[value=" GO "]')
        if go_buttons:
            await go_buttons[0].click()
            await asyncio.sleep(2)

        # Check for results
        content = await page.content()
        if "No records" in content or "No data" in content:
            return []

        # Extract table rows
        rows = await page.query_selector_all('tr')

        for row in rows:
            cells = await row.query_selector_all('td')
            if len(cells) >= 5:
                row_data = []
                for cell in cells:
                    text = (await cell.inner_text()).strip()
                    row_data.append(text)

                # Check if this is a data row (not header)
                if row_data[0] and row_data[0] not in ['Licensee', 'BIS Menu', 'Last Name']:
                    # Check for ACTIVE status
                    status = row_data[2] if len(row_data) > 2 else ""

                    if "ACTIVE" in status.upper():
                        contractor = {
                            "licensee_name": row_data[0] if len(row_data) > 0 else "",
                            "license_number": row_data[1] if len(row_data) > 1 else "",
                            "status": row_data[2] if len(row_data) > 2 else "",
                            "expiration_date": row_data[3] if len(row_data) > 3 else "",
                            "business_1": row_data[4] if len(row_data) > 4 else "",
                            "business_2": row_data[5] if len(row_data) > 5 else "",
                            "license_type_code": license_code,
                            "license_type": license_name,
                            "search_letter": letter,
                            "source": "NYC_DOB",
                            "state": "NY",
                            "scraped_date": datetime.now().isoformat(),
                        }
                        contractors.append(contractor)

    except Exception as e:
        print(f"      Error: {e}")

    return contractors


async def main():
    print("\n" + "=" * 80)
    print("NYC DOB ACTIVE LICENSE SCRAPER")
    print("=" * 80)
    print(f"\nTarget license types: {len(LICENSE_TYPES)}")
    print("Searching A-Z for each license type...")
    print(f"Output: {OUTPUT_DIR}/")

    all_contractors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for license_code, license_name in LICENSE_TYPES.items():
            print(f"\n{'=' * 60}")
            print(f"LICENSE TYPE: {license_code} - {license_name}")
            print("=" * 60)

            license_total = 0

            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                print(f"   {letter}...", end=" ", flush=True)

                contractors = await scrape_license_type_by_letter(
                    page, license_code, license_name, letter
                )

                print(f"{len(contractors)} active", flush=True)
                license_total += len(contractors)
                all_contractors.extend(contractors)

                await asyncio.sleep(0.5)  # Be nice to server

            print(f"\n   TOTAL {license_name}: {license_total} active licenses")

        await browser.close()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_file = OUTPUT_DIR / f"nyc_active_licenses_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_contractors, f, indent=2)
    print(f"\n✅ JSON: {json_file}")

    # CSV
    if all_contractors:
        csv_file = OUTPUT_DIR / f"nyc_active_licenses_{timestamp}.csv"
        fieldnames = [
            'licensee_name', 'license_number', 'status', 'expiration_date',
            'business_1', 'business_2', 'license_type_code', 'license_type',
            'source', 'state', 'scraped_date'
        ]
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_contractors)
        print(f"✅ CSV: {csv_file}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal ACTIVE licenses: {len(all_contractors)}")

    # By license type
    by_type = {}
    for c in all_contractors:
        lt = c['license_type']
        by_type[lt] = by_type.get(lt, 0) + 1

    print("\nBy License Type:")
    for lt, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {lt}: {count}")

    # Unique businesses
    businesses = set()
    for c in all_contractors:
        if c.get('business_1'):
            businesses.add(c['business_1'].upper())
        if c.get('business_2'):
            businesses.add(c['business_2'].upper())

    print(f"\nUnique business names: {len(businesses)}")

    return all_contractors


if __name__ == "__main__":
    asyncio.run(main())
