#!/usr/bin/env python3
"""
Test HVACR SearchResults.aspx Page Directly

The user says they can download HVACR data with all pages.
Let me look at the actual SearchResults page more carefully.
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import re
from pathlib import Path
from datetime import datetime

NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey" / "hvacr_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROFESSION = "HVACR"


def parse_html_for_contractors(html_content):
    """Parse HTML using regex - look for ANY contractor pattern."""
    contractors = []

    # Try the standard pattern first
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
        })

    return contractors


async def test_hvacr():
    print("\n" + "="*80)
    print("TESTING HVACR - LOOKING AT SEARCHRESULTS PAGE CAREFULLY")
    print("="*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Step 1: Navigate
            print("\n1. Navigating to portal...")
            await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Step 2: Select HVACR
            print("2. Selecting HVACR profession...")
            await page.select_option("#t_web_lookup__profession_name", label=PROFESSION)
            await asyncio.sleep(2)

            # Step 3: Click search
            print("3. Clicking search...")
            await page.click("input[type='submit'][value='Search']", timeout=5000)

            # Step 4: Wait LONGER for results
            print("4. Waiting for SearchResults.aspx to load...")
            print("   (Waiting up to 60 seconds for page to fully load)")

            # Wait for URL to contain SearchResults.aspx
            try:
                await page.wait_for_url("**/SearchResults.aspx*", timeout=60000)
                print("   ✅ SearchResults.aspx loaded!")
            except:
                print("   ⚠️  URL didn't change to SearchResults.aspx")

            # Wait for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=60000)
                print("   ✅ Network idle")
            except:
                print("   ⚠️  Network still loading, continuing anyway...")

            # Additional wait
            await asyncio.sleep(10)

            # Step 5: Check current URL
            current_url = page.url
            print(f"\n5. Current URL: {current_url}")

            # Step 6: Take screenshot
            await page.screenshot(path=OUTPUT_DIR / "hvacr_results_full.png", full_page=True)
            print(f"   ✅ Full-page screenshot saved")

            # Step 7: Get HTML
            print("\n6. Getting HTML content...")
            html_content = await page.content()
            print(f"   HTML size: {len(html_content):,} bytes")

            # Save HTML
            with open(OUTPUT_DIR / "hvacr_results.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   ✅ HTML saved")

            # Step 8: Analyze
            print("\n7. Analyzing HTML...")

            # Check for table
            has_datagrid = "datagrid_results" in html_content
            print(f"   Results table found: {has_datagrid}")

            # Count rows
            tr_count = html_content.count("<tr")
            print(f"   Total <tr> tags: {tr_count}")

            # Look for license numbers
            license_pattern = r'(34[A-Z]{2}\d{7,8}|13VH\d{7,8}|T-\d+)'
            licenses = re.findall(license_pattern, html_content)
            print(f"   License numbers found: {len(licenses)}")
            if licenses:
                print(f"   Sample: {licenses[:10]}")

            # Look for Details.aspx links
            details_links = re.findall(r'<a[^>]*href="Details\.aspx[^"]*"[^>]*>([^<]+)</a>', html_content)
            print(f"   Details.aspx links: {len(details_links)}")
            if details_links:
                print(f"   Sample names: {details_links[:10]}")

            # Parse contractors
            contractors = parse_html_for_contractors(html_content)
            print(f"\n   Contractors parsed: {len(contractors)}")

            if contractors:
                print(f"\n   ✅ SUCCESS! Found {len(contractors)} contractors")
                for i, c in enumerate(contractors[:5]):
                    print(f"      {i+1}. {c['business_name']} - {c['license_number']}")
            else:
                print(f"\n   ❌ 0 contractors parsed")

            # Step 9: Check for pagination
            print("\n8. Checking for pagination...")
            pagination_html = await page.evaluate("""
                () => {
                    const table = document.querySelector('#datagrid_results');
                    if (!table) return 'NO TABLE';

                    // Look for pagination row
                    const rows = table.querySelectorAll('tr');
                    for (let row of rows) {
                        if (row.innerHTML.includes('__doPostBack')) {
                            return row.innerHTML;
                        }
                    }
                    return 'NO PAGINATION';
                }
            """)

            if '__doPostBack' in pagination_html:
                print("   ✅ Pagination found!")
                # Extract page numbers
                page_numbers = re.findall(r"__doPostBack\('datagrid_results\$_ctl\d+\$_ctl(\d+)",pagination_html)
                if page_numbers:
                    max_ctl = max([int(p) for p in page_numbers])
                    max_page = max_ctl + 2
                    print(f"   Total pages: {max_page}")
            else:
                print("   ℹ️  No pagination found (single page)")

            # Step 10: Keep browser open
            print("\n" + "="*80)
            print("BROWSER STAYING OPEN FOR 60 SECONDS")
            print("="*80)
            print(f"\nFiles saved to: {OUTPUT_DIR}/")
            print("Please inspect the browser to see what's actually there!")

            await asyncio.sleep(60)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


asyncio.run(test_hvacr())
