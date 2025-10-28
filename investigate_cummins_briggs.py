#!/usr/bin/env python3
"""
Deep investigation of Cummins and Briggs & Stratton dealer locators
Manual testing to understand form behavior and extraction possibilities
"""
import time
from playwright.sync_api import sync_playwright

SITES = {
    "Cummins": "https://www.cummins.com/na/generators/home-standby/find-a-dealer",
    "Briggs_Stratton": "https://www.briggsandstratton.com/na/en_us/support/dealer-locator/standby.html"
}

TEST_ZIP = "94102"  # San Francisco

def investigate_site(browser, name, url):
    """Manually investigate a site's form"""
    print(f"\n{'='*70}")
    print(f"INVESTIGATING: {name}")
    print(f"{'='*70}")

    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = context.new_page()

    try:
        print(f"1. Navigating to {name}...")
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        time.sleep(5)

        print(f"2. Taking initial screenshot...")
        page.screenshot(path=f'output/{name.lower()}_initial.png')

        print(f"3. Checking page structure...")

        # Try to find any input fields
        all_inputs = page.locator('input').all()
        print(f"   Found {len(all_inputs)} input elements total")

        # Check for iframes (common with custom widgets)
        iframes = page.locator('iframe').all()
        if iframes:
            print(f"   ⚠️ Found {len(iframes)} iframes - may be embedded widget")
            for i, iframe in enumerate(iframes[:3]):
                src = iframe.get_attribute('src')
                print(f"      iframe {i+1}: {src[:80] if src else 'no src'}")

        print(f"\n4. Attempting to interact with form...")

        # For Cummins - look for any visible inputs
        if name == "Cummins":
            print(f"   Looking for Cummins-specific selectors...")

            # Try different input selectors
            selectors_to_try = [
                'input[type="text"]',
                'input[type="search"]',
                'input[placeholder*="zip" i]',
                'input[placeholder*="code" i]',
                'input[id*="zip" i]',
                'input[name*="zip" i]',
            ]

            for selector in selectors_to_try:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        print(f"   ✓ Found {selector}: {count} elements")
                        # Try to interact with first one
                        inp = page.locator(selector).first
                        if inp.is_visible():
                            print(f"      First one is VISIBLE - can interact!")
                            inp.click()
                            time.sleep(0.5)
                            inp.fill(TEST_ZIP)
                            print(f"      ✓ Successfully filled with ZIP {TEST_ZIP}")
                            time.sleep(2)
                            page.screenshot(path=f'output/{name.lower()}_filled.png')
                            break
                        else:
                            print(f"      First one is HIDDEN")
                except Exception as e:
                    pass

        # For B&S - test autocomplete handling
        elif name == "Briggs_Stratton":
            print(f"   Looking for B&S ZIP input with autocomplete...")

            try:
                # Find the ZIP input
                zip_input = page.locator('input[placeholder*="ZIP" i]').first
                if zip_input.is_visible():
                    print(f"   ✓ Found visible ZIP input")
                    zip_input.click()
                    time.sleep(1)

                    # Type ZIP slowly to trigger autocomplete
                    print(f"   Typing ZIP {TEST_ZIP} slowly...")
                    for char in TEST_ZIP:
                        zip_input.type(char, delay=200)

                    time.sleep(2)

                    # Check if autocomplete dropdown appeared
                    dropdown = page.locator('[role="listbox"], [class*="autocomplete"], [class*="suggestions"]')
                    if dropdown.count() > 0:
                        print(f"   ✓ Autocomplete dropdown appeared!")
                        options = dropdown.locator('[role="option"]').all()
                        print(f"   Found {len(options)} autocomplete options")

                        if options:
                            print(f"   Clicking first option...")
                            options[0].click()
                            time.sleep(2)
                            page.screenshot(path=f'output/{name.lower()}_autocomplete_selected.png')
                            print(f"   ✓ Selected autocomplete option")
                        else:
                            print(f"   ⚠️ No options found in dropdown")
                    else:
                        print(f"   ⚠️ No autocomplete dropdown detected")

                else:
                    print(f"   ✗ ZIP input not visible")

            except Exception as e:
                print(f"   ✗ Error: {e}")

        print(f"\n5. Looking for search/submit button...")
        button_selectors = [
            'button:has-text("Search")',
            'button:has-text("Find")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]

        for selector in button_selectors:
            try:
                count = page.locator(selector).count()
                if count > 0:
                    print(f"   ✓ Found {selector}: {count} buttons")
                    btn = page.locator(selector).first
                    if btn.is_visible():
                        print(f"      Button is VISIBLE - clicking...")
                        btn.click()
                        time.sleep(5)
                        page.screenshot(path=f'output/{name.lower()}_results.png')
                        print(f"      ✓ Clicked and took results screenshot")
                        break
            except:
                pass

        print(f"\n✅ {name} investigation complete")
        print(f"   Screenshots saved to output/")

    except Exception as e:
        print(f"✗ Error investigating {name}: {e}")

    finally:
        context.close()

def main():
    """Run investigation"""
    print("="*70)
    print("CUMMINS & BRIGGS & STRATTON DEEP INVESTIGATION")
    print("="*70)
    print("Goal: Understand form behavior and find automation approach")
    print()

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)

        # Investigate each site
        for name, url in SITES.items():
            investigate_site(browser, name, url)
            time.sleep(2)

        browser.close()

    print("\n" + "="*70)
    print("INVESTIGATION COMPLETE")
    print("="*70)
    print("Check output/ folder for screenshots")
    print("Review findings above for automation feasibility")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸ Investigation interrupted")
