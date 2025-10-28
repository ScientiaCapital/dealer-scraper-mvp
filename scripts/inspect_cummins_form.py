#!/usr/bin/env python3
"""
Inspect Cummins dealer locator form and extract dealer card structure
This script manually completes the form and captures the dealer results HTML
"""
import time
from playwright.sync_api import sync_playwright

TEST_ZIP = "94102"  # San Francisco

def main():
    print("="*70)
    print("CUMMINS DEALER LOCATOR INSPECTION")
    print("="*70)

    with sync_playwright() as p:
        print("\n1. Launching browser (non-headless to see what's happening)...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            print("\n2. Navigating to Cummins dealer locator...")
            page.goto('https://www.cummins.com/na/generators/home-standby/find-a-dealer',
                     timeout=60000, wait_until='domcontentloaded')
            time.sleep(3)

            print("\n3. Finding iframe...")
            iframe = page.frame_locator('iframe[title="Find dealer locations form"]')

            print("\n4. Filling form fields...")

            # PRODUCT: Power Generation
            print("   - Selecting PRODUCT: Power Generation")
            iframe.locator('select').first.select_option(label='Power Generation')
            time.sleep(1)

            # MARKET APPLICATION: Home And Small Business
            print("   - Selecting MARKET APPLICATION: Home And Small Business")
            iframe.locator('select').nth(1).select_option(label='Home And Small Business')
            time.sleep(1)

            # SERVICE LEVEL: First inspect options, then select
            print("   - Inspecting SERVICE LEVEL options...")
            service_select = iframe.locator('select').nth(2)

            # Get all option values and labels
            options = service_select.locator('option').all()
            print(f"     Found {len(options)} options:")
            for opt in options:
                value = opt.get_attribute('value')
                text = opt.inner_text()
                print(f"       - value='{value}', text='{text}'")

            # Try to select first non-empty option (likely "Installation")
            print("   - Selecting first non-empty SERVICE LEVEL option...")
            first_value = options[1].get_attribute('value') if len(options) > 1 else None
            if first_value:
                service_select.select_option(value=first_value)
                time.sleep(2)
            else:
                print("     ✗ No valid options found")
                raise Exception("Cannot find SERVICE LEVEL option")

            # COUNTRY: United States (must be selected before postal code is visible)
            print("   - Selecting COUNTRY: United States")
            country_select = iframe.locator('select').nth(3)
            country_select.select_option(label='United States')
            time.sleep(2)

            # LOCATION: ZIP code (should now be visible after country selection)
            print(f"   - Entering LOCATION: {TEST_ZIP}")
            postal_input = iframe.locator('input[name="postal_code"]')
            postal_input.wait_for(state='visible', timeout=5000)
            postal_input.fill(TEST_ZIP)
            time.sleep(1)

            # DISTANCE: 100 Miles
            print("   - Selecting DISTANCE: 100 Miles")
            iframe.locator('input[value="100"]').check()
            time.sleep(1)

            print("\n5. Taking 'form filled' screenshot...")
            page.screenshot(path='output/cummins_form_filled.png', full_page=True)

            # Click SEARCH button - try multiple selectors
            print("\n6. Clicking SEARCH button...")

            # Try different button selectors
            button_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'input[value*="SEARCH" i]',
                'button:has-text("SEARCH")',
                '.form-submit',
            ]

            button_clicked = False
            for selector in button_selectors:
                try:
                    btn = iframe.locator(selector)
                    if btn.count() > 0:
                        print(f"   Found button with selector: {selector}")
                        btn.first.click(timeout=5000)
                        button_clicked = True
                        break
                except Exception as e:
                    print(f"   Failed with {selector}: {e}")
                    continue

            if not button_clicked:
                print("   ✗ Could not find/click SEARCH button")
                raise Exception("SEARCH button not found")

            print("   Waiting for results to load (10 seconds)...")
            time.sleep(10)

            print("\n7. Taking 'results' screenshot...")
            page.screenshot(path='output/cummins_search_results.png', full_page=True)

            print("\n8. Extracting FULL iframe HTML for easier inspection...")
            # Get the entire iframe body HTML
            iframe_html = iframe.locator('body').inner_html()

            # Save to file
            with open('output/cummins_iframe_full.html', 'w', encoding='utf-8') as f:
                f.write('<!DOCTYPE html>\n')
                f.write('<html>\n<head><meta charset="utf-8"></head>\n<body>\n')
                f.write(iframe_html)
                f.write('\n</body>\n</html>')

            print("   ✓ Saved full iframe HTML to: output/cummins_iframe_full.html")
            print("   (Open this file in a browser to see the full dealer results)")

            # Also get just text content to see what's there
            text_content = iframe.locator('body').inner_text()
            print(f"\n   Text content preview (first 1000 chars):")
            print("   " + "="*66)
            print("   " + text_content[:1000].replace('\n', '\n   '))
            print("   " + "="*66)

            # Try to count dealer results
            print("\n9. Looking for dealer cards...")

            # Common patterns for dealer cards
            selectors_to_try = [
                '.dealer-card',
                '.dealer-result',
                '.location-result',
                '.dealer-item',
                '.dealer',
                '[class*="dealer"]',
                '.result-item',
                'article',
            ]

            for selector in selectors_to_try:
                count = iframe.locator(selector).count()
                if count > 0:
                    print(f"   ✓ Found {count} elements matching: {selector}")

                    # Get HTML of first dealer card as sample
                    first_card_html = iframe.locator(selector).first.inner_html()
                    with open('output/cummins_dealer_card_sample.html', 'w', encoding='utf-8') as f:
                        f.write(first_card_html)
                    print(f"   ✓ Saved first dealer card HTML to: output/cummins_dealer_card_sample.html")
                    break

            print("\n✅ Inspection complete!")
            print("   - Screenshots: output/cummins_*.png")
            print("   - Full iframe HTML: output/cummins_iframe_full.html")
            print("   - Dealer card sample: output/cummins_dealer_card_sample.html (if found)")
            print("\n   → Open cummins_iframe_full.html in a browser to inspect dealer results!")

            print("\n   Press Ctrl+C to close browser...")
            time.sleep(300)  # Keep browser open for 5 minutes to manually inspect

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸ Inspection interrupted")
