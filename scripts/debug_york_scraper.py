#!/usr/bin/env python3
"""
Debug York scraper by taking screenshots and inspecting page structure.
"""
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright

def debug_york():
    """Debug York scraper step by step with screenshots."""

    with sync_playwright() as p:
        # Launch browser (NON-headless so we can see what's happening)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Navigate to dealer locator
        print("Step 1: Navigating to York dealer locator...")
        page.goto("https://www.york.com/residential-equipment/find-a-dealer", timeout=60000)
        time.sleep(3)
        page.screenshot(path="debug_york_1_initial.png")
        print("  ✅ Screenshot saved: debug_york_1_initial.png")

        # Find iframe
        print("\nStep 2: Finding iframe...")
        iframe_selector = 'iframe[name="locator_iframe16959"]'
        try:
            iframe_element = page.wait_for_selector(iframe_selector, timeout=10000)
            iframe = iframe_element.content_frame()
            print(f"  ✅ Found iframe: {iframe_selector}")

            # Take screenshot of iframe
            iframe_element.screenshot(path="debug_york_2_iframe.png")
            print("  ✅ Screenshot saved: debug_york_2_iframe.png")
        except Exception as e:
            print(f"  ❌ Could not find iframe: {e}")
            browser.close()
            return

        # Check for country dropdown
        print("\nStep 3: Looking for country dropdown...")
        try:
            country_button = iframe.locator('button[data-id="country"]')
            if country_button.count() > 0:
                print(f"  ✅ Found country dropdown button")
                country_button.screenshot(path="debug_york_3_country_button.png")
                print("  ✅ Screenshot saved: debug_york_3_country_button.png")

                # Click it
                print("  → Clicking country dropdown...")
                country_button.click()
                time.sleep(2)
                page.screenshot(path="debug_york_4_dropdown_open.png")
                print("  ✅ Screenshot saved: debug_york_4_dropdown_open.png")

                # Look for United States option
                print("  → Looking for 'United States' option...")
                us_option = iframe.locator('.dropdown-menu.show li span:has-text("United States")').first
                if us_option.count() > 0:
                    print("  ✅ Found 'United States' option")
                    us_option.screenshot(path="debug_york_5_us_option.png")
                    print("  ✅ Screenshot saved: debug_york_5_us_option.png")

                    # Click it
                    us_option.click()
                    time.sleep(2)
                    page.screenshot(path="debug_york_6_us_selected.png")
                    print("  ✅ Screenshot saved: debug_york_6_us_selected.png")
                else:
                    print("  ❌ Could not find 'United States' option")
                    print("  → Available options:")
                    options = iframe.locator('.dropdown-menu.show li span').all_text_contents()
                    for opt in options:
                        print(f"     - {opt}")

            else:
                print("  ❌ Could not find country dropdown button")
        except Exception as e:
            print(f"  ❌ Error with country dropdown: {e}")
            import traceback
            traceback.print_exc()

        # Fill ZIP code
        print("\nStep 4: Filling ZIP code...")
        try:
            zip_input = iframe.locator('input[placeholder*="postal" i], input[placeholder*="ZIP" i], input[type="text"]').first
            if zip_input.count() > 0:
                print("  ✅ Found ZIP input")
                zip_input.fill("33109")
                time.sleep(1)
                zip_input.screenshot(path="debug_york_7_zip_filled.png")
                print("  ✅ Screenshot saved: debug_york_7_zip_filled.png")
            else:
                print("  ❌ Could not find ZIP input")
        except Exception as e:
            print(f"  ❌ Error filling ZIP: {e}")

        # Click search
        print("\nStep 5: Clicking search button...")
        try:
            search_button = iframe.locator('button:has-text("Search"), input[type="submit"]').first
            if search_button.count() > 0:
                print("  ✅ Found search button")
                search_button.click()
                time.sleep(5)
                page.screenshot(path="debug_york_8_results.png")
                print("  ✅ Screenshot saved: debug_york_8_results.png")
            else:
                print("  ❌ Could not find search button")
        except Exception as e:
            print(f"  ❌ Error clicking search: {e}")

        # Check for dealer results
        print("\nStep 6: Checking for dealer results...")
        try:
            h3_elements = iframe.locator('h3').all()
            print(f"  ✅ Found {len(h3_elements)} h3 elements")

            if len(h3_elements) > 0:
                print("  → First 5 h3 texts:")
                for i, h3 in enumerate(h3_elements[:5]):
                    print(f"     {i+1}. {h3.text_content()}")
            else:
                print("  ❌ No h3 elements found (no dealers)")

                # Check what IS on the page
                print("\n  → Dumping iframe HTML to debug_york_iframe.html...")
                iframe_html = iframe.content()
                with open("debug_york_iframe.html", "w") as f:
                    f.write(iframe_html)
                print("  ✅ HTML saved: debug_york_iframe.html")

        except Exception as e:
            print(f"  ❌ Error checking results: {e}")

        print("\n\n🛑 Pausing for 30 seconds so you can inspect the browser...")
        print("   Check the screenshots in the current directory.")
        time.sleep(30)

        browser.close()
        print("\n✅ Debug complete!")

if __name__ == "__main__":
    debug_york()
