#!/usr/bin/env python3
"""
Explore the RGB Portal - rgbportal.dca.njoag.gov

This might be THE portal with all the contractors!
Let's see what's available here.
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

RGB_PORTAL_URL = "https://rgbportal.dca.njoag.gov/public-view/"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey" / "rgb_portal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def explore_rgb_portal():
    print("\n" + "="*80)
    print("EXPLORING RGB PORTAL - rgbportal.dca.njoag.gov")
    print("="*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Navigate
            print(f"\n1. Navigating to {RGB_PORTAL_URL}...")
            await page.goto(RGB_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Screenshot
            await page.screenshot(path=OUTPUT_DIR / "01_initial_page.png", full_page=True)
            print("   ✅ Screenshot saved")

            # Get page content
            html_content = await page.content()
            with open(OUTPUT_DIR / "page_content.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("   ✅ HTML saved")

            # Check for dropdowns/search fields
            print("\n2. Looking for search fields and dropdowns...")

            # Try to find license type dropdown
            license_type_options = await page.evaluate("""
                () => {
                    // Look for any select element that might contain license types
                    const selects = document.querySelectorAll('select');
                    let results = [];

                    for (let select of selects) {
                        const label = select.previousElementSibling?.textContent ||
                                     select.parentElement?.textContent ||
                                     select.getAttribute('aria-label') ||
                                     select.getAttribute('id') ||
                                     select.getAttribute('name') ||
                                     'Unknown';

                        const options = Array.from(select.options).map(opt => ({
                            value: opt.value,
                            text: opt.text
                        }));

                        if (options.length > 0) {
                            results.push({
                                label: label.trim(),
                                id: select.id,
                                name: select.name,
                                options: options
                            });
                        }
                    }
                    return results;
                }
            """)

            if license_type_options:
                print(f"   ✅ Found {len(license_type_options)} dropdown(s)!")

                for i, dropdown in enumerate(license_type_options):
                    print(f"\n   Dropdown {i+1}:")
                    print(f"      Label: {dropdown['label'][:100]}")
                    print(f"      ID: {dropdown['id']}")
                    print(f"      Name: {dropdown['name']}")
                    print(f"      Options: {len(dropdown['options'])}")

                    # Save to JSON
                    with open(OUTPUT_DIR / f"dropdown_{i+1}_options.json", 'w') as f:
                        json.dump(dropdown['options'], f, indent=2)

                    # Show first 20 options
                    print(f"      First 20 options:")
                    for opt in dropdown['options'][:20]:
                        print(f"         - {opt['text']}")

                    if len(dropdown['options']) > 20:
                        print(f"         ... and {len(dropdown['options']) - 20} more")
            else:
                print("   ⚠️  No dropdowns found")

            # Check for input fields
            input_fields = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input[type="text"], input[type="search"]');
                    return Array.from(inputs).map(inp => ({
                        id: inp.id,
                        name: inp.name,
                        placeholder: inp.placeholder,
                        label: inp.previousElementSibling?.textContent || inp.getAttribute('aria-label') || 'Unknown'
                    }));
                }
            """)

            if input_fields:
                print(f"\n   ✅ Found {len(input_fields)} input field(s):")
                for inp in input_fields:
                    print(f"      - {inp['label']}: {inp['id']} (placeholder: {inp['placeholder']})")

            # Keep browser open
            print("\n" + "="*80)
            print("BROWSER STAYING OPEN FOR 2 MINUTES")
            print("="*80)
            print("\nPlease inspect the page!")
            print("Tell me what professions you see in the dropdown!")
            print(f"\nFiles saved to: {OUTPUT_DIR}/")

            await asyncio.sleep(120)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


asyncio.run(explore_rgb_portal())
