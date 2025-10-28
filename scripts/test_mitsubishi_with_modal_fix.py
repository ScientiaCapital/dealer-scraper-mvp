#!/usr/bin/env python3
"""
Test Mitsubishi scraper with modal dismissal fix.

The issue: A "Search and support" modal pops up after clicking search,
blocking the contractor results from loading.

Fix: Dismiss the modal by clicking the X button or pressing Escape.
"""

import os
import time
from playwright.sync_api import sync_playwright


def test_mitsubishi_with_modal_fix():
    """Test scraping with proper modal handling"""

    url = "https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor"
    test_zip = "10001"

    print(f"\n{'=' * 80}")
    print(f"TESTING MITSUBISHI SCRAPER WITH MODAL FIX")
    print(f"{'=' * 80}")
    print(f"URL: {url}")
    print(f"ZIP: {test_zip}")
    print(f"{'=' * 80}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Navigate
            print(f"[1] Navigating to contractor locator...")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            time.sleep(3)

            # Handle cookies
            print(f"[2] Handling cookie consent...")
            cookie_selectors = [
                'button:has-text("Accept All Cookies")',
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
            ]
            for selector in cookie_selectors:
                try:
                    cookie_btn = page.locator(selector)
                    if cookie_btn.count() > 0 and cookie_btn.first.is_visible():
                        cookie_btn.first.click(timeout=2000)
                        time.sleep(2)
                        break
                except Exception:
                    continue

            # Click Commercial tab
            print(f"[3] Clicking Commercial building tab...")
            page.click('text=Commercial building', timeout=5000)
            time.sleep(2)

            # Fill ZIP
            print(f"[4] Filling ZIP code: {test_zip}")
            zip_input = page.locator('input[placeholder*="Zip" i]')
            for i in range(zip_input.count()):
                if zip_input.nth(i).is_visible():
                    zip_input.nth(i).fill(test_zip)
                    time.sleep(1)
                    break

            # Click search
            print(f"[5] Clicking search button...")
            btns = page.locator('button:has-text("Search")')
            for i in range(btns.count()):
                btn = btns.nth(i)
                if btn.is_visible():
                    btn.click(timeout=5000)
                    break

            # Wait a moment for modal or results
            print(f"[6] Waiting for modal or results...")
            time.sleep(3)

            # CRITICAL FIX: Dismiss "Search and support" modal if it appears
            print(f"[7] Checking for 'Search and support' modal...")
            modal_dismissed = False

            # Try multiple methods to dismiss modal
            dismiss_methods = [
                ("button[aria-label='Close']", "Close button"),
                ("button:has-text('×')", "X button"),
                ("div[role='dialog'] button", "Dialog close button"),
            ]

            for selector, description in dismiss_methods:
                try:
                    close_btn = page.locator(selector)
                    if close_btn.count() > 0 and close_btn.first.is_visible():
                        print(f"    ✓ Found {description}, clicking to dismiss modal...")
                        close_btn.first.click(timeout=2000)
                        time.sleep(2)
                        modal_dismissed = True
                        break
                except Exception as e:
                    continue

            # If no close button found, try pressing Escape key
            if not modal_dismissed:
                print(f"    → No close button found, trying Escape key...")
                page.keyboard.press('Escape')
                time.sleep(2)
                modal_dismissed = True

            print(f"    ✓ Modal handling complete")

            # Wait for contractor results to load
            print(f"[8] Waiting for contractor results to load...")
            time.sleep(3)

            # Take screenshot of results
            output_dir = "/Users/tmkipper/Desktop/dealer-scraper-mvp/output/mitsubishi_debug"
            screenshot_path = f"{output_dir}/06_after_modal_dismiss.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot_path}")

            # Analyze results
            print(f"\n[9] Analyzing contractor results...")
            results = page.evaluate("""
                () => {
                    const analysis = {
                        h3_count: 0,
                        h3_texts: [],
                        phone_links: 0,
                        miles_away_count: 0,
                        contractor_names: []
                    };

                    // Count H3s
                    const h3s = document.querySelectorAll('h3');
                    analysis.h3_count = h3s.length;
                    analysis.h3_texts = Array.from(h3s).map(h3 => h3.textContent.trim());

                    // Count phone links
                    analysis.phone_links = document.querySelectorAll('a[href^="tel:"]').length;

                    // Look for "miles away"
                    const bodyText = document.body.innerText;
                    const milesMatches = bodyText.match(/\\d+\\.?\\d*\\s*miles?\\s*away/gi);
                    analysis.miles_away_count = milesMatches ? milesMatches.length : 0;

                    // Try to find contractor names (look for patterns)
                    const allText = document.body.innerText;
                    const lines = allText.split('\\n');

                    // Look for lines that might be contractor names
                    // (before "miles away" or near phone numbers)
                    for (let i = 0; i < lines.length && analysis.contractor_names.length < 5; i++) {
                        const line = lines[i].trim();
                        const nextLine = lines[i + 1] ? lines[i + 1].trim() : '';

                        // If this line is followed by "X.X miles away", it's likely a contractor name
                        if (nextLine.match(/\\d+\\.?\\d*\\s*miles?\\s*away/i)) {
                            analysis.contractor_names.push(line);
                        }
                    }

                    return analysis;
                }
            """)

            print(f"\n    RESULTS ANALYSIS:")
            print(f"      H3 elements: {results['h3_count']}")
            print(f"      Phone links: {results['phone_links']}")
            print(f"      'miles away' elements: {results['miles_away_count']}")
            print(f"      Contractor names found: {len(results['contractor_names'])}")

            if results['contractor_names']:
                print(f"\n    First 5 contractor names:")
                for i, name in enumerate(results['contractor_names'][:5], 1):
                    print(f"      {i}. {name}")
            else:
                print(f"\n    ⚠ No contractor names detected")
                print(f"\n    First 10 H3 texts on page:")
                for i, text in enumerate(results['h3_texts'][:10], 1):
                    print(f"      {i}. {text[:80]}")

            # Keep browser open for inspection
            print(f"\n[10] Browser will stay open for 30 seconds...")
            time.sleep(30)

            browser.close()

            # Summary
            print(f"\n{'=' * 80}")
            if results['miles_away_count'] > 0:
                print(f"✓ SUCCESS! Found {results['miles_away_count']} contractors")
            else:
                print(f"✗ ISSUE: Still finding 0 contractors after modal dismissal")
                print(f"   → Check screenshot: {screenshot_path}")
                print(f"   → There may be additional modals or the page structure is different")
            print(f"{'=' * 80}\n")

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            browser.close()


if __name__ == "__main__":
    test_mitsubishi_with_modal_fix()
