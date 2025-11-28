#!/usr/bin/env python3
"""
Tesla Page Structure Diagnostic - Find Updated Selectors

Connects to Browserbase and captures:
1. Full page HTML
2. Screenshots at various stages
3. All inputs and their attributes
"""

import os
import sys
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
TESLA_URL = "https://www.tesla.com/support/certified-installers?productType=powerwall"


def diagnose_tesla():
    """Capture Tesla page structure for debugging"""

    print("=" * 70)
    print("TESLA PAGE DIAGNOSTIC")
    print("=" * 70)

    with sync_playwright() as p:
        # Connect to Browserbase
        print("\n1. Connecting to Browserbase...")
        ws_endpoint = f'wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&enableProxy=true'
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        print("   ✓ Connected")

        try:
            # Navigate
            print(f"\n2. Navigating to {TESLA_URL}...")
            page.goto(TESLA_URL, timeout=60000, wait_until='domcontentloaded')
            time.sleep(5)

            # Screenshot 1: Initial load
            page.screenshot(path="output/tesla_diag_1_initial.png", full_page=False)
            print("   ✓ Screenshot saved: output/tesla_diag_1_initial.png")

            # Wait for network idle
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except:
                print("   ⚠ Network didn't settle (continuing anyway)")
            time.sleep(3)

            # Screenshot 2: After load
            page.screenshot(path="output/tesla_diag_2_loaded.png", full_page=False)
            print("   ✓ Screenshot saved: output/tesla_diag_2_loaded.png")

            # Check for country selector
            print("\n3. Looking for country/region selector...")
            country_buttons = page.query_selector_all('button')
            for btn in country_buttons[:20]:  # Check first 20 buttons
                try:
                    text = btn.inner_text()
                    if 'United States' in text or 'US' in text:
                        print(f"   Found: '{text}'")
                        btn.click()
                        time.sleep(2)
                        break
                except:
                    pass

            # Screenshot 3: After region select
            page.screenshot(path="output/tesla_diag_3_region.png", full_page=False)
            print("   ✓ Screenshot saved: output/tesla_diag_3_region.png")

            # Find ALL inputs
            print("\n4. Finding all inputs...")
            inputs = page.query_selector_all('input')
            print(f"   Found {len(inputs)} input elements:")

            for i, inp in enumerate(inputs[:15]):  # First 15
                try:
                    attrs = page.evaluate("""
                        (el) => ({
                            type: el.type,
                            role: el.role,
                            placeholder: el.placeholder,
                            name: el.name,
                            id: el.id,
                            class: el.className,
                            visible: el.offsetParent !== null
                        })
                    """, inp)
                    print(f"\n   Input {i+1}:")
                    for k, v in attrs.items():
                        if v:
                            print(f"      {k}: {v}")
                except Exception as e:
                    print(f"   Input {i+1}: Error - {e}")

            # Find inputs with placeholder containing "zip" or "location"
            print("\n5. Looking for ZIP/location input specifically...")
            zip_selectors = [
                'input[placeholder*="zip" i]',
                'input[placeholder*="ZIP"]',
                'input[placeholder*="location" i]',
                'input[placeholder*="address" i]',
                'input[placeholder*="postal" i]',
                'input[placeholder*="city" i]',
                'input[aria-label*="zip" i]',
                'input[aria-label*="location" i]',
                'input[type="search"]',
                'input[role="combobox"]',
                'input[role="searchbox"]',
            ]

            for selector in zip_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem and elem.is_visible():
                        print(f"   ✓ FOUND: {selector}")
                        attrs = page.evaluate("""
                            (el) => ({
                                placeholder: el.placeholder,
                                'aria-label': el.getAttribute('aria-label'),
                                className: el.className
                            })
                        """, elem)
                        print(f"      Attributes: {attrs}")
                except:
                    pass

            # Try typing in a visible input
            print("\n6. Attempting to find and use ZIP input...")
            for selector in zip_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem and elem.is_visible():
                        print(f"   Trying selector: {selector}")
                        elem.click()
                        time.sleep(0.5)
                        elem.fill("94027")
                        time.sleep(2)
                        page.screenshot(path="output/tesla_diag_4_typed.png", full_page=False)
                        print("   ✓ Typed ZIP, screenshot: output/tesla_diag_4_typed.png")

                        # Press Enter and wait
                        elem.press("Enter")
                        time.sleep(5)
                        page.screenshot(path="output/tesla_diag_5_results.png", full_page=False)
                        print("   ✓ After Enter, screenshot: output/tesla_diag_5_results.png")
                        break
                except Exception as e:
                    print(f"   ✗ Failed: {e}")

            # Dump page text to find result patterns
            print("\n7. Checking for installer results...")
            body_text = page.evaluate("() => document.body.innerText")

            # Look for patterns
            installer_keywords = ["Premier", "Certified", "installer", "phone", "visit website"]
            found_patterns = []
            lines = body_text.split('\n')
            for i, line in enumerate(lines):
                if any(kw.lower() in line.lower() for kw in installer_keywords):
                    found_patterns.append(f"Line {i}: {line[:80]}")

            if found_patterns:
                print(f"   Found {len(found_patterns)} potential installer lines:")
                for pattern in found_patterns[:10]:
                    print(f"      {pattern}")
            else:
                print("   ⚠ No installer patterns found in page text")

            # Find card containers
            print("\n8. Looking for card containers...")
            card_selectors = [
                '[class*="ciContainer"]',
                '[class*="installer"]',
                '[class*="card"]',
                '[class*="result"]',
                '[data-testid*="installer"]',
            ]

            for selector in card_selectors:
                try:
                    cards = page.query_selector_all(selector)
                    if cards:
                        print(f"   ✓ FOUND {len(cards)} elements: {selector}")
                        if cards:
                            # Get class name of first card
                            cls = page.evaluate("(el) => el.className", cards[0])
                            print(f"      First card class: {cls}")
                except:
                    pass

            # Save full HTML for analysis
            print("\n9. Saving page HTML...")
            html = page.content()
            with open("output/tesla_diag_page.html", "w") as f:
                f.write(html)
            print(f"   ✓ Saved {len(html)} chars to output/tesla_diag_page.html")

            print("\n" + "=" * 70)
            print("DIAGNOSTIC COMPLETE")
            print("=" * 70)
            print("\nCheck screenshots in output/tesla_diag_*.png")
            print("Check HTML in output/tesla_diag_page.html")

        finally:
            browser.close()


if __name__ == "__main__":
    diagnose_tesla()
