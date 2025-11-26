#!/usr/bin/env python3
"""
Debug Master Plumbers - PERSON License Search

Trying PERSON search instead of BUSINESS search!
facility=N instead of facility=Y
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

# PERSON search portal (facility=N, not facility=Y)
NJ_PERSON_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx"  # No ?facility=Y
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey" / "debug_person_search"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def test_person_search():
    print("\n" + "="*80)
    print("TESTING PERSON LICENSE SEARCH (not business)")
    print("="*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Navigate to PERSON portal (no ?facility=Y)
        print(f"\n1. Navigating to PERSON portal...")
        print(f"   URL: {NJ_PERSON_PORTAL_URL}")
        await page.goto(NJ_PERSON_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Screenshot
        await page.screenshot(path=OUTPUT_DIR / "01_person_portal.png")
        print("   ✅ Screenshot: 01_person_portal.png")

        # Check what professions are available in PERSON search
        print("\n2. Checking profession dropdown...")
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

        print(f"   Total options: {len(options)}")

        # Look for Master Plumbers
        master_plumbers = [opt for opt in options if 'Master Plumbers' in opt['text'] or 'Plumb' in opt['text']]
        print(f"\n   Plumbing-related options:")
        for opt in master_plumbers:
            print(f"      - {opt['text']} (value: '{opt['value']}')")

        # Look for HVAC
        hvac_options = [opt for opt in options if 'HVAC' in opt['text'] or 'Heat' in opt['text'] or 'Refriger' in opt['text']]
        print(f"\n   HVAC-related options:")
        for opt in hvac_options:
            print(f"      - {opt['text']} (value: '{opt['value']}')")

        print("\n" + "="*80)
        print("KEEPING BROWSER OPEN FOR 60 SECONDS")
        print("="*80)
        print("\nInspect the portal to see what professions are available for PERSON search!")

        await asyncio.sleep(60)

        await browser.close()

asyncio.run(test_person_search())
