#!/usr/bin/env python3
"""
Explore NYC Department of Buildings License Search
https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet?vlfirst=N

This is the main NYC contractor licensing portal
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

NYC_DOB_URL = "https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet?vlfirst=N"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_york" / "nyc_dob"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def explore_nyc_dob():
    print("\n" + "="*80)
    print("EXPLORING NYC DEPARTMENT OF BUILDINGS LICENSE PORTAL")
    print("="*80)

    async with async_playwright() as p:
        print(f"\nLaunching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Navigate
            print(f"\n1. Navigating to {NYC_DOB_URL}...")
            await page.goto(NYC_DOB_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Screenshot
            await page.screenshot(path=OUTPUT_DIR / "01_initial_page.png", full_page=True)
            print(f"   ✅ Screenshot saved")

            # Get page content
            html_content = await page.content()
            with open(OUTPUT_DIR / "page_content.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   ✅ HTML saved")

            # Look for license type options
            print(f"\n2. Looking for license types...")

            # Check for dropdowns
            dropdowns = await page.evaluate("""
                () => {
                    const selects = document.querySelectorAll('select');
                    return Array.from(selects).map(select => ({
                        id: select.id,
                        name: select.name,
                        label: select.previousElementSibling?.textContent || select.getAttribute('aria-label') || 'Unknown',
                        optionCount: select.options.length,
                        firstFewOptions: Array.from(select.options).slice(0, 10).map(opt => opt.text)
                    }));
                }
            """)

            if dropdowns:
                print(f"   ✅ Found {len(dropdowns)} dropdown(s)!")
                for i, dd in enumerate(dropdowns, 1):
                    print(f"\n   Dropdown {i}:")
                    print(f"      ID: {dd['id']}")
                    print(f"      Name: {dd['name']}")
                    print(f"      Options: {dd['optionCount']}")
                    print(f"      First options: {dd['firstFewOptions']}")

            # Look for links to license types
            license_links = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a');
                    const licenseLinks = [];

                    for (let link of links) {
                        const text = link.textContent.trim();
                        const href = link.href;

                        // Look for contractor/trade related keywords
                        const keywords = ['electric', 'plumb', 'hvac', 'contractor', 'master', 'journeyman', 'trade', 'license'];
                        if (keywords.some(kw => text.toLowerCase().includes(kw)) ||
                            text.length > 5) {  // Capture any substantial links
                            licenseLinks.push({
                                text: text,
                                href: href
                            });
                        }
                    }

                    return licenseLinks.slice(0, 30);  // First 30 links
                }
            """)

            if license_links:
                print(f"\n3. Found {len(license_links)} license-related links:")
                for i, link in enumerate(license_links, 1):
                    print(f"   {i}. {link['text']}")

                # Save to JSON
                with open(OUTPUT_DIR / "license_links.json", 'w') as f:
                    json.dump(license_links, f, indent=2)

            # Look for any form fields
            print(f"\n4. Looking for search forms...")
            forms = await page.evaluate("""
                () => {
                    const forms = document.querySelectorAll('form');
                    return Array.from(forms).map(form => ({
                        action: form.action,
                        method: form.method,
                        inputCount: form.querySelectorAll('input, select').length
                    }));
                }
            """)

            if forms:
                print(f"   ✅ Found {len(forms)} form(s):")
                for i, form in enumerate(forms, 1):
                    print(f"      Form {i}: {form['inputCount']} fields, action={form['action']}")

            # Keep browser open
            print(f"\n{'='*80}")
            print("BROWSER STAYING OPEN FOR 2 MINUTES")
            print("="*80)
            print("\nPlease inspect the page!")
            print(f"Files saved to: {OUTPUT_DIR}/")

            await asyncio.sleep(120)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


asyncio.run(explore_nyc_dob())
