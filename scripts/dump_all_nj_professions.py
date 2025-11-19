#!/usr/bin/env python3
"""
Dump ALL profession options from both PERSON and BUSINESS portals
To find where HVACR and plumbing contractors actually are
"""

import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PERSON_URL = "https://newjersey.mylicense.com/verification/Search.aspx"
BUSINESS_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"


async def get_professions(url, portal_type):
    """Get all profession options from a portal"""
    print(f"\n{'='*80}")
    print(f"{portal_type} PORTAL - {url}")
    print('='*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Get all options from profession dropdown
            options = await page.evaluate("""
                () => {
                    const select = document.querySelector('#t_web_lookup__profession_name');
                    if (!select) return [];

                    return Array.from(select.options).map(opt => ({
                        value: opt.value,
                        text: opt.text.trim()
                    })).filter(opt => opt.value !== '');  // Remove blank option
                }
            """)

            print(f"\nFound {len(options)} profession options:\n")
            for i, opt in enumerate(options, 1):
                print(f"  {i:2}. {opt['text']}")

            # Save to JSON
            output_file = OUTPUT_DIR / f"professions_{portal_type.lower()}.json"
            with open(output_file, 'w') as f:
                json.dump(options, f, indent=2)

            print(f"\n✅ Saved to: {output_file.name}")

            return options

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await browser.close()


async def main():
    print("\n" + "="*80)
    print("NJ LICENSE PORTAL PROFESSION DUMPER")
    print("="*80)
    print("\nDumping ALL profession options from both portals...")

    # Get from both portals
    person_profs = await get_professions(PERSON_URL, "PERSON")
    business_profs = await get_professions(BUSINESS_URL, "BUSINESS")

    # Compare
    print(f"\n{'='*80}")
    print("COMPARISON:")
    print('='*80)
    print(f"\nPERSON portal: {len(person_profs)} professions")
    print(f"BUSINESS portal: {len(business_profs)} professions")

    # Find HVAC/plumbing related options in both
    keywords = ['hvac', 'plumb', 'mechanical', 'heat', 'cool', 'air', 'fire', 'refriger']

    print(f"\n{'='*80}")
    print("HVAC/PLUMBING RELATED PROFESSIONS:")
    print('='*80)

    print("\nPERSON portal:")
    found_person = False
    for prof in person_profs:
        if any(kw in prof['text'].lower() for kw in keywords):
            print(f"  - {prof['text']}")
            found_person = True
    if not found_person:
        print("  (none found)")

    print("\nBUSINESS portal:")
    found_business = False
    for prof in business_profs:
        if any(kw in prof['text'].lower() for kw in keywords):
            print(f"  - {prof['text']}")
            found_business = True
    if not found_business:
        print("  (none found)")

    print(f"\n{'='*80}")
    print("FILES SAVED:")
    print('='*80)
    print(f"  - {OUTPUT_DIR / 'professions_person.json'}")
    print(f"  - {OUTPUT_DIR / 'professions_business.json'}")


if __name__ == "__main__":
    asyncio.run(main())
