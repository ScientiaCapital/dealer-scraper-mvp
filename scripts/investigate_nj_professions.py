#!/usr/bin/env python3
"""
NJ Profession Investigation - Manual Portal Inspection

Investigates why Master Plumbers and HVACR return 0 results.
Takes screenshots and saves HTML to understand portal behavior.
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from datetime import datetime

NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey" / "investigation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROBLEM_PROFESSIONS = [
    "Master Plumbers",
    "HVACR",
]


async def investigate_profession(profession):
    """Investigate a profession manually."""

    print(f"\n{'='*80}")
    print(f"INVESTIGATING: {profession}")
    print(f"{'='*80}\n")

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

            # Screenshot 1: Initial page
            safe_name = profession.replace(" ", "_").lower()
            await page.screenshot(path=OUTPUT_DIR / f"{safe_name}_01_initial.png")
            print(f"   📸 Screenshot: 01_initial")

            # Select profession
            print(f"   Selecting profession: {profession}")
            await page.select_option("#t_web_lookup__profession_name", label=profession)
            await asyncio.sleep(2)

            # Screenshot 2: After selection
            await page.screenshot(path=OUTPUT_DIR / f"{safe_name}_02_selected.png")
            print(f"   📸 Screenshot: 02_selected")

            # Get dropdown value to verify selection
            dropdown_value = await page.evaluate("""
                () => {
                    const select = document.querySelector('#t_web_lookup__profession_name');
                    return select ? select.value : null;
                }
            """)
            print(f"   ✓ Dropdown value: {dropdown_value}")

            # Click search
            print("   Clicking search...")
            try:
                await page.click("input[type='submit'][value='Search']", timeout=5000)
            except:
                pass

            # Wait longer for results
            print("   Waiting 15 seconds for results...")
            await asyncio.sleep(15)

            # Screenshot 3: After search
            await page.screenshot(path=OUTPUT_DIR / f"{safe_name}_03_results.png")
            print(f"   📸 Screenshot: 03_results")

            # Get HTML
            html_content = await page.content()

            # Save HTML
            html_file = OUTPUT_DIR / f"{safe_name}_results.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   💾 HTML saved ({len(html_content):,} bytes)")

            # Check for results table
            has_table = "datagrid_results" in html_content
            print(f"   ℹ️  Results table present: {has_table}")

            # Check for "no records" message
            has_no_records = "no records" in html_content.lower() or "0 records" in html_content.lower()
            print(f"   ℹ️  'No records' message: {has_no_records}")

            # Count table rows
            row_count = html_content.count("<tr")
            print(f"   ℹ️  HTML <tr> tags found: {row_count}")

            # Check for license numbers (34XX or 13VH patterns)
            import re
            license_pattern = r'(34[A-Z]{2}\d{7,8}|13VH\d{7,8}|T-\d+)'
            licenses_found = re.findall(license_pattern, html_content)
            print(f"   ℹ️  License numbers found: {len(licenses_found)}")

            if licenses_found:
                print(f"   📋 Sample licenses: {licenses_found[:5]}")

            # Keep browser open for manual inspection
            print(f"\n   🔍 Browser staying open for manual inspection...")
            print(f"   📁 Files saved to: {OUTPUT_DIR}/")
            print(f"   Press Ctrl+C to close browser and continue")

            # Wait for manual inspection
            await asyncio.sleep(60)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print(f"   Browser closed\n")


async def main():
    print("\n" + "="*80)
    print("NJ PROFESSION INVESTIGATION")
    print("="*80)
    print("\nInvestigating professions that returned 0 results")
    print("Will take screenshots and save HTML for manual analysis\n")

    for profession in PROBLEM_PROFESSIONS:
        try:
            await investigate_profession(profession)

            # Pause between professions
            if profession != PROBLEM_PROFESSIONS[-1]:
                print(f"\n⏸️  Pausing 5 seconds before next profession...")
                await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n\n⏭️  Skipping to next profession...")
            continue
        except Exception as e:
            print(f"\n❌ Error investigating {profession}: {e}")
            continue

    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)
    print(f"\n📁 Screenshots and HTML saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
