#!/usr/bin/env python3
"""
NYC Department of Buildings (DOB) License Scraper

Scrapes contractor licenses from NYC DOB BIS portal:
https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet

Target License Types:
- A: ELECTRICAL CONTRACTOR (solar/battery electrical)
- B: ELECTRICAL FIRM (commercial electrical)
- P: MASTER PLUMBER (geothermal, radiant heating)
- O: OIL BURNER INSTALLER (HVAC, heat pumps)
- G: GENERAL CONTRACTOR (resimercial)
- F: FIRE SUPPRESSION CONTRACTOR (commercial)

For Coperniq ICP: Multi-license contractors = self-performing, asset-centric
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import csv
from datetime import datetime
import re

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_york" / "nyc_dob"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# NYC DOB License Types
LICENSE_TYPES = {
    "A": "ELECTRICAL CONTRACTOR",
    "P": "MASTER PLUMBER",
    "O": "OIL BURNER INSTALLER",
    "G": "GENERAL CONTRACTOR",
    "F": "FIRE SUPPRESSION CONTRACTOR",
    "B": "ELECTRICAL FIRM",
}

# NYC ZIP codes - wealthy areas + high commercial activity
NYC_ZIPS = [
    # Manhattan (high commercial)
    "10001", "10011", "10012", "10013", "10014", "10016", "10017", "10018", "10019", "10020",
    "10021", "10022", "10023", "10024", "10025", "10028", "10029", "10036", "10038", "10065",
    # Brooklyn (high residential + commercial)
    "11201", "11205", "11211", "11215", "11217", "11222", "11231", "11238", "11249",
    # Queens
    "11101", "11102", "11103", "11104", "11105", "11106", "11354", "11355", "11360",
    # Bronx
    "10451", "10452", "10453", "10454", "10455", "10456", "10458", "10460", "10461",
    # Staten Island
    "10301", "10302", "10303", "10304", "10305", "10306", "10307", "10308", "10309", "10310",
]

BASE_URL = "https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet?vlfirst=N"


async def extract_contractor_from_row(row):
    """Extract contractor data from a table row"""
    cells = row.query_selector_all("td")
    if len(cells) < 3:
        return None

    data = {}
    for i, cell in enumerate(cells):
        text = (await cell.inner_text()).strip()
        data[f"col_{i}"] = text

    return data


async def scrape_license_type_by_zip(page, license_code: str, license_name: str, zip_code: str):
    """Scrape contractors for a specific license type and ZIP"""
    contractors = []

    try:
        # Navigate to search page
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Find the ZIP code search form (form 2)
        # Select license type
        await page.select_option('select[name="licensetype"]', license_code)

        # Fill ZIP code
        zip_input = page.locator('input[name="zipcode"]')
        await zip_input.fill(zip_code)

        # Submit
        submit_btn = page.locator('input[name="go5"], input[name="go6"]').first
        await submit_btn.click()
        await asyncio.sleep(3)

        # Check for results
        content = await page.content()

        if "No records found" in content or "No data found" in content:
            return []

        # Extract results table
        rows = await page.query_selector_all("table tr")

        for row in rows[1:]:  # Skip header
            cells = await row.query_selector_all("td")
            if len(cells) >= 2:
                row_data = []
                for cell in cells:
                    text = (await cell.inner_text()).strip()
                    row_data.append(text)

                if row_data and any(row_data):
                    contractors.append({
                        "license_type_code": license_code,
                        "license_type": license_name,
                        "zip_searched": zip_code,
                        "raw_data": " | ".join(row_data),
                        "cells": row_data
                    })

    except Exception as e:
        print(f"      Error scraping {license_code}/{zip_code}: {e}")

    return contractors


async def scrape_by_business_name_letter(page, license_code: str, license_name: str, letter: str):
    """Scrape by searching business names starting with a letter"""
    contractors = []

    try:
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Select the contractor search section (not licensee search)
        # This is the "Business Name" search

        # Find business name input (second search option)
        biz_input = page.locator('input[name="bizname"]').first
        await biz_input.fill(f"{letter}")  # Search names starting with letter

        # Submit
        submit_btns = page.locator('input[value=" GO "]')
        # The business name search is usually the 5th GO button
        await submit_btns.nth(4).click()
        await asyncio.sleep(3)

        # Check for results
        content = await page.content()

        if "No records found" in content or "No data found" in content:
            return []

        # Extract results
        rows = await page.query_selector_all("table tr")

        for row in rows[1:]:
            cells = await row.query_selector_all("td")
            if len(cells) >= 2:
                row_data = []
                for cell in cells:
                    text = (await cell.inner_text()).strip()
                    row_data.append(text)

                if row_data and any(row_data):
                    contractors.append({
                        "license_type_code": license_code,
                        "license_type": license_name,
                        "search_letter": letter,
                        "raw_data": " | ".join(row_data),
                        "cells": row_data
                    })

    except Exception as e:
        print(f"      Error: {e}")

    return contractors


async def scrape_all_licenses():
    """Main scraping function - scrape all license types"""

    print("\n" + "="*80)
    print("NYC DEPARTMENT OF BUILDINGS - LICENSE SCRAPER")
    print("="*80)
    print(f"\nTarget: {len(LICENSE_TYPES)} license types")
    print(f"ZIPs: {len(NYC_ZIPS)} NYC ZIP codes")
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

        # Try alphabet search for each license type (more comprehensive)
        for license_code, license_name in LICENSE_TYPES.items():
            print(f"\n{'='*60}")
            print(f"License Type: {license_code} - {license_name}")
            print('='*60)

            license_contractors = []

            # Try first few letters as search (A, B, C, etc.)
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                print(f"   Searching businesses starting with '{letter}'...", end=" ")

                try:
                    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(1)

                    # Look for business name search input
                    biz_inputs = await page.query_selector_all('input[name="bizname"]')

                    if biz_inputs:
                        await biz_inputs[0].fill(letter)

                        # Find and click submit for contractor search
                        go_buttons = await page.query_selector_all('input[value=" GO "]')
                        if len(go_buttons) >= 5:
                            await go_buttons[4].click()  # 5th GO button is contractor search
                            await asyncio.sleep(2)

                            content = await page.content()

                            if "No records found" not in content and "No data found" not in content:
                                # Extract table data
                                rows = await page.query_selector_all("table.content tr, tr.content")

                                found = 0
                                for row in rows:
                                    cells = await row.query_selector_all("td")
                                    if len(cells) >= 2:
                                        row_data = []
                                        for cell in cells:
                                            text = (await cell.inner_text()).strip()
                                            row_data.append(text)

                                        if row_data and any(t for t in row_data if t):
                                            license_contractors.append({
                                                "license_type_code": license_code,
                                                "license_type": license_name,
                                                "search_letter": letter,
                                                "raw_data": " | ".join(row_data),
                                            })
                                            found += 1

                                print(f"found {found}")
                            else:
                                print("0")
                        else:
                            print("no form")
                    else:
                        print("no input")

                except Exception as e:
                    print(f"error: {e}")

                await asyncio.sleep(0.5)  # Be nice to server

            print(f"\n   Total for {license_name}: {len(license_contractors)}")
            all_contractors.extend(license_contractors)

        await browser.close()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save raw JSON
    json_file = OUTPUT_DIR / f"nyc_contractors_raw_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_contractors, f, indent=2)
    print(f"\n✅ Saved raw JSON: {json_file}")

    # Save CSV
    if all_contractors:
        csv_file = OUTPUT_DIR / f"nyc_contractors_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['license_type_code', 'license_type', 'search_letter', 'raw_data'])
            writer.writeheader()
            writer.writerows(all_contractors)
        print(f"✅ Saved CSV: {csv_file}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print(f"Total contractors found: {len(all_contractors)}")

    # Count by license type
    by_type = {}
    for c in all_contractors:
        lt = c['license_type']
        by_type[lt] = by_type.get(lt, 0) + 1

    for lt, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {lt}: {count}")

    return all_contractors


if __name__ == "__main__":
    asyncio.run(scrape_all_licenses())
