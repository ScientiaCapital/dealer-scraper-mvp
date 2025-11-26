#!/usr/bin/env python3
"""
Debug Master Plumbers Scraper - Ultra Methodical

Takes screenshots at every step.
Saves HTML at every step.
Prints detailed debugging info.

ONE profession. Get it working. Verify data. Then move on.
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import re
from pathlib import Path
from datetime import datetime

NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey" / "debug_master_plumbers"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROFESSION = "Master Plumbers"


def parse_html_for_contractors(html_content):
    """Parse HTML using regex to extract contractor data."""
    contractors = []

    # NJ HTML structure pattern (same as worked for Electrical)
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


async def debug_master_plumbers():
    """Debug Master Plumbers scrape step by step."""

    print(f"\n{'='*80}")
    print(f"DEBUG: MASTER PLUMBERS - STEP BY STEP")
    print(f"{'='*80}\n")

    async with async_playwright() as p:
        print("STEP 1: Launching browser...")
        browser = await p.chromium.launch(
            headless=False,  # Keep visible so we can see what's happening
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        try:
            # STEP 2: Navigate to portal
            print("\nSTEP 2: Navigating to portal...")
            print(f"   URL: {NJ_PORTAL_URL}")
            await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Screenshot: Initial page
            await page.screenshot(path=OUTPUT_DIR / "01_initial_page.png")
            print("   ✅ Screenshot saved: 01_initial_page.png")

            # STEP 3: Check dropdown
            print("\nSTEP 3: Checking profession dropdown...")
            dropdown_html = await page.evaluate("""
                () => {
                    const select = document.querySelector('#t_web_lookup__profession_name');
                    return select ? select.outerHTML : 'NOT FOUND';
                }
            """)
            print(f"   Dropdown exists: {' FOUND' if 'NOT FOUND' not in dropdown_html else 'NOT FOUND'}")

            # Get all available options
            options = await page.evaluate("""
                () => {
                    const select = document.querySelector('#t_web_lookup__profession_name');
                    if (!select) return [];
                    return Array.from(select.options).map(opt => ({
                        value: opt.value,
                        text: opt.text
                    }));
                }
            """)
            print(f"   Total options available: {len(options)}")

            # Check if Master Plumbers is in the list
            master_plumbers_option = [opt for opt in options if 'Master Plumbers' in opt['text']]
            if master_plumbers_option:
                print(f"   ✅ 'Master Plumbers' found in dropdown:")
                print(f"      value: '{master_plumbers_option[0]['value']}'")
                print(f"      text: '{master_plumbers_option[0]['text']}'")
            else:
                print(f"   ❌ 'Master Plumbers' NOT found in dropdown!")
                print(f"   Available options containing 'Plumb': {[opt['text'] for opt in options if 'lumb' in opt['text'].lower()]}")

            # STEP 4: Select profession
            print(f"\nSTEP 4: Selecting profession: {PROFESSION}")
            try:
                await page.select_option("#t_web_lookup__profession_name", label=PROFESSION)
                print(f"   ✅ Selection successful")
            except Exception as e:
                print(f"   ❌ Selection failed: {e}")
                await browser.close()
                return

            await asyncio.sleep(2)

            # Verify selection
            selected_value = await page.evaluate("""
                () => {
                    const select = document.querySelector('#t_web_lookup__profession_name');
                    return select ? select.value : null;
                }
            """)
            print(f"   Selected value: '{selected_value}'")

            # Screenshot: After selection
            await page.screenshot(path=OUTPUT_DIR / "02_profession_selected.png")
            print("   ✅ Screenshot saved: 02_profession_selected.png")

            # STEP 5: Click search
            print("\nSTEP 5: Clicking search button...")
            try:
                await page.click("input[type='submit'][value='Search']", timeout=5000)
                print("   ✅ Search button clicked")
            except Exception as e:
                print(f"   ⚠️  Click error (may be normal): {e}")

            # STEP 6: Wait for results
            print("\nSTEP 6: Waiting for results to load...")
            print("   Waiting for network idle (30 seconds max)...")
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
                print("   ✅ Network idle reached")
            except:
                print("   ⚠️  Network idle timeout, falling back to 15 second wait")
                await asyncio.sleep(15)

            # Additional wait to ensure page settled
            print("   Additional 5 second settle wait...")
            await asyncio.sleep(5)

            # Screenshot: After search
            await page.screenshot(path=OUTPUT_DIR / "03_search_results.png")
            print("   ✅ Screenshot saved: 03_search_results.png")

            # STEP 7: Get HTML content
            print("\nSTEP 7: Getting HTML content...")
            html_content = await page.content()
            html_size = len(html_content)
            print(f"   HTML size: {html_size:,} bytes")

            # Save HTML
            html_file = OUTPUT_DIR / "search_results.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   ✅ HTML saved: search_results.html")

            # STEP 8: Analyze HTML
            print("\nSTEP 8: Analyzing HTML content...")

            # Check for results table
            has_datagrid = "datagrid_results" in html_content
            print(f"   Results table ('datagrid_results'): {'FOUND' if has_datagrid else 'NOT FOUND'}")

            # Check for error messages
            has_error = "error" in html_content.lower()
            print(f"   Error messages: {'FOUND' if has_error else 'NOT FOUND'}")

            # Check for "no records"
            no_records_msgs = [
                "no records",
                "0 records",
                "no results",
                "no licenses found"
            ]
            no_records = any(msg in html_content.lower() for msg in no_records_msgs)
            print(f"   'No records' message: {'FOUND' if no_records else 'NOT FOUND'}")

            # Count <tr> tags
            tr_count = html_content.count("<tr")
            print(f"   HTML <tr> tags: {tr_count}")

            # Try to find license numbers
            license_pattern = r'(34[A-Z]{2}\d{7,8}|13VH\d{7,8}|T-\d+)'
            licenses = re.findall(license_pattern, html_content)
            print(f"   License numbers found: {len(licenses)}")

            if licenses:
                print(f"   Sample licenses: {licenses[:5]}")

            # STEP 9: Parse contractors
            print("\nSTEP 9: Parsing contractors...")
            contractors = parse_html_for_contractors(html_content)
            print(f"   Contractors parsed: {len(contractors)}")

            if contractors:
                print(f"\n   ✅ FOUND {len(contractors)} contractors!")
                print(f"   Sample:")
                for i, c in enumerate(contractors[:3]):
                    print(f"      {i+1}. {c['business_name']} ({c['license_number']})")
            else:
                print(f"\n   ❌ NO contractors found")

                # Additional debugging
                print("\n   Additional debugging info:")

                # Look for any table content
                table_matches = re.findall(r'<table[^>]*>(.*?)</table>', html_content, re.DOTALL)
                print(f"   Total <table> tags found: {len(table_matches)}")

                # Look for any links to Details.aspx
                details_links = re.findall(r'<a[^>]*href="Details\.aspx[^"]*"[^>]*>([^<]+)</a>', html_content)
                print(f"   Details.aspx links found: {len(details_links)}")
                if details_links:
                    print(f"   Sample links: {details_links[:5]}")

            # STEP 10: Keep browser open for inspection
            print("\n" + "="*80)
            print("PAUSING FOR MANUAL INSPECTION")
            print("="*80)
            print(f"\nBrowser will stay open for 60 seconds so you can inspect.")
            print(f"Files saved to: {OUTPUT_DIR}/")
            print(f"\nPress Ctrl+C to close browser early...")

            await asyncio.sleep(60)

        except KeyboardInterrupt:
            print("\n\n⏭️  Manual inspection ended")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print("\n✅ Browser closed")


async def main():
    await debug_master_plumbers()

    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)
    print(f"\n📁 Check files in: {OUTPUT_DIR}/")
    print(f"   - 01_initial_page.png")
    print(f"   - 02_profession_selected.png")
    print(f"   - 03_search_results.png")
    print(f"   - search_results.html")


if __name__ == "__main__":
    asyncio.run(main())
