#!/usr/bin/env python3
"""
Debug Mitsubishi Diamond Commercial scraper by inspecting the actual DOM structure.

This script:
1. Opens browser in HEADED mode (visible)
2. Navigates through the Commercial tab workflow
3. Takes screenshots at each step
4. Saves the final results page HTML
5. Prints DOM structure analysis (first 5 H3 elements and containers)
6. Prints all clickable elements to understand the structure
"""

import os
import time
from playwright.sync_api import sync_playwright


def debug_mitsubishi_dom():
    """Debug the Mitsubishi scraper DOM structure"""

    # Create output directory for debug files
    output_dir = "/Users/tmkipper/Desktop/dealer-scraper-mvp/output/mitsubishi_debug"
    os.makedirs(output_dir, exist_ok=True)

    url = "https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor"
    test_zip = "10001"  # New York

    print(f"=" * 80)
    print(f"DEBUGGING MITSUBISHI DIAMOND COMMERCIAL SCRAPER")
    print(f"=" * 80)
    print(f"URL: {url}")
    print(f"ZIP: {test_zip}")
    print(f"Output Directory: {output_dir}")
    print(f"=" * 80)

    with sync_playwright() as p:
        # Launch browser in HEADED mode (visible)
        print("\n[1] Launching browser in HEADED mode...")
        browser = p.chromium.launch(
            headless=False,  # VISIBLE BROWSER
            slow_mo=500      # Slow down actions by 500ms for visibility
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Step 1: Navigate to contractor locator
            print(f"\n[2] Navigating to: {url}")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            time.sleep(3)

            # Take screenshot 1
            screenshot1_path = f"{output_dir}/01_initial_page.png"
            page.screenshot(path=screenshot1_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot1_path}")

            # Step 2: Handle cookie consent
            print(f"\n[3] Checking for cookie consent dialog...")
            cookie_selectors = [
                'button:has-text("Accept All Cookies")',
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
            ]

            for selector in cookie_selectors:
                try:
                    cookie_btn = page.locator(selector)
                    if cookie_btn.count() > 0 and cookie_btn.first.is_visible():
                        print(f"    ✓ Found cookie dialog, clicking: {selector}")
                        cookie_btn.first.click(timeout=2000)
                        time.sleep(2)
                        break
                except Exception as e:
                    continue

            # Take screenshot 2
            screenshot2_path = f"{output_dir}/02_after_cookies.png"
            page.screenshot(path=screenshot2_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot2_path}")

            # Step 3: Click "Commercial building" tab
            print(f"\n[4] Clicking 'Commercial building' tab...")
            try:
                page.click('text=Commercial building', timeout=5000)
                time.sleep(2)
                print(f"    ✓ Commercial tab clicked successfully")
            except Exception as e:
                print(f"    ✗ Error clicking Commercial tab: {e}")
                raise

            # Take screenshot 3
            screenshot3_path = f"{output_dir}/03_commercial_tab.png"
            page.screenshot(path=screenshot3_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot3_path}")

            # Step 4: Fill ZIP code
            print(f"\n[5] Filling ZIP code: {test_zip}")
            zip_input_selectors = [
                'input[placeholder*="Zip" i]',
                'input[placeholder*="zip code" i]',
                'input[type="text"]',
            ]

            zip_filled = False
            for selector in zip_input_selectors:
                try:
                    zip_input = page.locator(selector)
                    # Get visible inputs only
                    for i in range(zip_input.count()):
                        if zip_input.nth(i).is_visible():
                            print(f"    ✓ Found visible ZIP input: {selector} (index {i})")
                            zip_input.nth(i).fill(test_zip)
                            time.sleep(1)
                            zip_filled = True
                            break
                    if zip_filled:
                        break
                except Exception as e:
                    continue

            if not zip_filled:
                print(f"    ✗ Could not find ZIP code input!")
                raise Exception("ZIP input not found")

            # Take screenshot 4
            screenshot4_path = f"{output_dir}/04_zip_filled.png"
            page.screenshot(path=screenshot4_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot4_path}")

            # Step 5: Click search button
            print(f"\n[6] Clicking search button...")
            button_selectors = [
                'button:has-text("Search")',
                'button[type="submit"]',
            ]

            button_clicked = False
            for selector in button_selectors:
                try:
                    btns = page.locator(selector)
                    for i in range(btns.count()):
                        btn = btns.nth(i)
                        if btn.is_visible():
                            print(f"    ✓ Found visible search button: {selector} (index {i})")
                            btn.click(timeout=5000)
                            button_clicked = True
                            break
                    if button_clicked:
                        break
                except Exception as e:
                    continue

            if not button_clicked:
                print(f"    ✗ Could not find search button!")
                raise Exception("Search button not found")

            # Step 6: Wait for results
            print(f"\n[7] Waiting 5 seconds for AJAX results to load...")
            time.sleep(5)

            # Take screenshot 5 (RESULTS PAGE - KEY!)
            screenshot5_path = f"{output_dir}/05_results_page.png"
            page.screenshot(path=screenshot5_path, full_page=True)
            print(f"    ✓ Screenshot saved: {screenshot5_path}")

            # Step 7: Save full HTML of results page
            print(f"\n[8] Saving results page HTML...")
            html_path = f"{output_dir}/results_page.html"
            html_content = page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"    ✓ HTML saved: {html_path}")
            print(f"    ℹ HTML length: {len(html_content):,} characters")

            # Step 8: Analyze DOM structure
            print(f"\n[9] Analyzing DOM structure...")

            # Count H3 elements
            h3_analysis = page.evaluate("""
                () => {
                    const h3s = document.querySelectorAll('h3');
                    return {
                        total_h3s: h3s.length,
                        h3_texts: Array.from(h3s).slice(0, 10).map(h3 => h3.textContent.trim())
                    };
                }
            """)

            print(f"\n    H3 ELEMENTS FOUND: {h3_analysis['total_h3s']}")
            print(f"    First 10 H3 texts:")
            for i, text in enumerate(h3_analysis['h3_texts'], 1):
                print(f"      {i}. {text[:80]}...")

            # Analyze contractor card structure
            print(f"\n[10] Looking for contractor card patterns...")

            card_analysis = page.evaluate("""
                () => {
                    const analysis = {
                        phone_links: 0,
                        website_links: 0,
                        distance_elements: 0,
                        contractor_cards: []
                    };

                    // Count phone links
                    analysis.phone_links = document.querySelectorAll('a[href^="tel:"]').length;

                    // Count website links (external, not mitsubishi domains)
                    const externalLinks = document.querySelectorAll('a[href*="://"]');
                    externalLinks.forEach(link => {
                        const href = link.href;
                        if (!href.includes('mitsubishi') &&
                            !href.includes('google') &&
                            !href.includes('tel:') &&
                            !href.includes('mailto:')) {
                            analysis.website_links++;
                        }
                    });

                    // Look for "miles away" elements
                    const allText = document.body.innerText;
                    const milesMatches = allText.match(/\\d+\\.?\\d*\\s*miles?\\s*away/gi);
                    analysis.distance_elements = milesMatches ? milesMatches.length : 0;

                    // Try to find contractor cards (first 3)
                    const h3s = document.querySelectorAll('h3');

                    for (let i = 0; i < Math.min(3, h3s.length); i++) {
                        const h3 = h3s[i];
                        const name = h3.textContent.trim();

                        // Skip obviously non-contractor headings
                        if (name.toLowerCase().includes('training') ||
                            name.toLowerCase().includes('warranty') ||
                            name.toLowerCase().includes('cookie') ||
                            name.length < 3) {
                            continue;
                        }

                        // Find parent container
                        const container = h3.closest('div[class*="Card"]') ||
                                        h3.parentElement?.parentElement ||
                                        h3.parentElement;

                        if (!container) continue;

                        // Get phone
                        let phone = '';
                        const phoneLink = container.querySelector('a[href^="tel:"]');
                        if (phoneLink) {
                            phone = phoneLink.href.replace('tel:', '');
                        }

                        // Get class names of container hierarchy
                        const containerClasses = container.className;
                        const parentClasses = container.parentElement?.className || '';
                        const grandparentClasses = container.parentElement?.parentElement?.className || '';

                        analysis.contractor_cards.push({
                            name: name,
                            phone: phone,
                            container_classes: containerClasses,
                            parent_classes: parentClasses,
                            grandparent_classes: grandparentClasses,
                            container_tag: container.tagName,
                            has_phone_link: !!phoneLink,
                            container_html: container.outerHTML.substring(0, 500)
                        });
                    }

                    return analysis;
                }
            """)

            print(f"\n    CONTRACTOR CARD ANALYSIS:")
            print(f"      Phone links found: {card_analysis['phone_links']}")
            print(f"      Website links found: {card_analysis['website_links']}")
            print(f"      'miles away' elements: {card_analysis['distance_elements']}")
            print(f"      Sample contractor cards: {len(card_analysis['contractor_cards'])}")

            for i, card in enumerate(card_analysis['contractor_cards'], 1):
                print(f"\n      === CARD {i} ===")
                print(f"      Name: {card['name']}")
                print(f"      Phone: {card['phone']}")
                print(f"      Has phone link: {card['has_phone_link']}")
                print(f"      Container tag: {card['container_tag']}")
                print(f"      Container classes: {card['container_classes'][:100]}")
                print(f"      Parent classes: {card['parent_classes'][:100]}")
                print(f"      HTML preview: {card['container_html'][:200]}...")

            # Save detailed analysis to file
            print(f"\n[11] Saving detailed analysis...")
            analysis_path = f"{output_dir}/dom_analysis.txt"
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write("MITSUBISHI DIAMOND COMMERCIAL DOM ANALYSIS\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"H3 Elements Found: {h3_analysis['total_h3s']}\n\n")
                f.write("First 10 H3 Texts:\n")
                for i, text in enumerate(h3_analysis['h3_texts'], 1):
                    f.write(f"  {i}. {text}\n")
                f.write("\n" + "=" * 80 + "\n\n")
                f.write("Card Analysis:\n")
                f.write(f"  Phone links: {card_analysis['phone_links']}\n")
                f.write(f"  Website links: {card_analysis['website_links']}\n")
                f.write(f"  Distance elements: {card_analysis['distance_elements']}\n")
                f.write("\nSample Cards:\n")
                for i, card in enumerate(card_analysis['contractor_cards'], 1):
                    f.write(f"\n  === CARD {i} ===\n")
                    f.write(f"  Name: {card['name']}\n")
                    f.write(f"  Phone: {card['phone']}\n")
                    f.write(f"  Container: {card['container_tag']}\n")
                    f.write(f"  Classes: {card['container_classes']}\n")
                    f.write(f"  HTML:\n{card['container_html']}\n")

            print(f"    ✓ Analysis saved: {analysis_path}")

            # Keep browser open for manual inspection
            print(f"\n[12] Browser will stay open for 30 seconds for manual inspection...")
            print(f"     Use this time to inspect the page in DevTools!")
            time.sleep(30)

            browser.close()

            print(f"\n{'=' * 80}")
            print(f"DEBUG COMPLETE!")
            print(f"{'=' * 80}")
            print(f"\nOutput files:")
            print(f"  1. Screenshots: {output_dir}/01_*.png through 05_*.png")
            print(f"  2. Results HTML: {output_dir}/results_page.html")
            print(f"  3. DOM Analysis: {output_dir}/dom_analysis.txt")
            print(f"\nNext steps:")
            print(f"  1. Review screenshot 05_results_page.png to see what's actually displayed")
            print(f"  2. Open results_page.html in a browser and use DevTools to inspect")
            print(f"  3. Check dom_analysis.txt for H3 and container structure")
            print(f"  4. Update extraction script based on findings")

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

            # Take error screenshot
            error_screenshot = f"{output_dir}/error_state.png"
            page.screenshot(path=error_screenshot, full_page=True)
            print(f"\n✓ Error state screenshot saved: {error_screenshot}")

            browser.close()
            return False

    return True


if __name__ == "__main__":
    debug_mitsubishi_dom()
