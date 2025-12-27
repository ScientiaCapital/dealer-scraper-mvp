#!/usr/bin/env python3
"""
Test Kohler scraper with Patchright stealth browser.

Patchright is a stealth fork of Playwright that bypasses bot detection.
Kohler uses Akamai EdgeSuite which blocks standard Playwright.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from patchright.sync_api import sync_playwright


def test_kohler_zip(zip_code: str, page) -> dict:
    """Test a single ZIP code."""
    print(f"\n🔍 Testing Kohler with ZIP: {zip_code}")

    page.goto('https://www.kohlerpower.com/na/en/home-generators/find-a-dealer', timeout=30000)
    time.sleep(3)

    # Check if page loaded (not blocked)
    page_text = page.evaluate('() => document.body.innerText')
    if 'Access Denied' in page_text or 'access denied' in page_text.lower():
        print("  ❌ Blocked by Akamai")
        return {"status": "blocked"}

    # Fill ZIP using JavaScript injection (Patchright locators may fail on some elements)
    fill_script = f"""
    () => {{
        const input = document.querySelector('input[name="zipcode"]');
        if (!input) return {{error: 'No input found'}};
        input.scrollIntoView({{block: 'center'}});
        input.focus();
        input.value = '{zip_code}';
        input.dispatchEvent(new Event('input', {{bubbles: true}}));
        input.dispatchEvent(new Event('change', {{bubbles: true}}));
        return {{success: true}};
    }}
    """
    result = page.evaluate(fill_script)
    print(f"  → Fill result: {result}")
    time.sleep(1)

    # Click search button
    click_script = """
    () => {
        const btn = document.querySelector('button[type="submit"]');
        if (btn) {
            btn.click();
            return {clicked: true};
        }
        return {clicked: false};
    }
    """
    click_result = page.evaluate(click_script)
    print(f"  → Click result: {click_result}")
    time.sleep(4)

    # Check for results
    page_text = page.evaluate('() => document.body.innerText')

    if 'No results found' in page_text or 'no results' in page_text.lower():
        print(f"  ❌ No dealers for ZIP {zip_code}")
        return {"status": "no_results", "zip": zip_code}

    # Look for phone numbers as indicator of dealer data
    phone_script = r"""
    () => {
        const text = document.body.innerText;
        const phoneMatch = text.match(/\(\d{3}\)\s*\d{3}-\d{4}/g) || [];
        return phoneMatch.slice(0, 10);
    }
    """
    phones = page.evaluate(phone_script)

    # Look for dealer names
    name_script = """
    () => {
        const cards = document.querySelectorAll('[class*="dealer"], [class*="result"], [class*="location"], .card, article, [class*="list-item"]');
        const names = [];
        cards.forEach(c => {
            const h = c.querySelector('h1, h2, h3, h4, h5, strong, [class*="name"], [class*="title"]');
            if (h && h.textContent.trim().length > 3) {
                names.push(h.textContent.trim().substring(0, 60));
            }
        });
        return names.slice(0, 10);
    }
    """
    names = page.evaluate(name_script)

    if phones or names:
        print(f"  ✅ Found dealers for ZIP {zip_code}")
        print(f"     Phones: {phones[:5]}")
        print(f"     Names: {names[:5]}")
        return {"status": "success", "zip": zip_code, "phones": phones, "names": names}
    else:
        # Get a snippet of page text for debugging
        snippet = page_text[:500].replace('\n', ' ')
        print(f"  ⚠️ Unclear result for ZIP {zip_code}")
        print(f"     Snippet: {snippet[:200]}...")
        return {"status": "unclear", "zip": zip_code, "snippet": snippet[:200]}


def main():
    # Test ZIPs: Wisconsin (near Kohler HQ), California, Texas
    test_zips = [
        '53044',  # Kohler, WI (HQ)
        '53081',  # Sheboygan, WI
        '53202',  # Milwaukee, WI
        '60601',  # Chicago, IL
        '90210',  # Beverly Hills, CA
    ]

    print("=" * 60)
    print("KOHLER PATCHRIGHT STEALTH TEST")
    print("=" * 60)
    print("Using Patchright (stealth Playwright) in HEADED mode")
    print("to bypass Akamai bot detection")

    results = []

    with sync_playwright() as p:
        # Launch in HEADED mode (required for Akamai bypass)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        for zip_code in test_zips:
            try:
                result = test_kohler_zip(zip_code, page)
                results.append(result)

                # If we found dealers, we're done
                if result.get("status") == "success":
                    print(f"\n✅ SUCCESS: Kohler scraper works with ZIP {zip_code}")
                    break

            except Exception as e:
                print(f"  ❌ Error testing ZIP {zip_code}: {e}")
                results.append({"status": "error", "zip": zip_code, "error": str(e)})

        browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    successes = [r for r in results if r.get("status") == "success"]
    no_results = [r for r in results if r.get("status") == "no_results"]
    blocked = [r for r in results if r.get("status") == "blocked"]

    if successes:
        print(f"✅ SUCCESS: {len(successes)} ZIPs have dealers")
        for s in successes:
            print(f"   - {s['zip']}: {len(s.get('phones', []))} phones, {len(s.get('names', []))} names")
    elif blocked:
        print("❌ BLOCKED: Akamai detection not bypassed")
    elif no_results:
        print(f"⚠️ NO DEALERS: Tested {len(no_results)} ZIPs but no dealers found")
        print("   This may be a Kohler dealer coverage issue, not a scraper issue")
    else:
        print("❓ UNCLEAR: Need to investigate further")

    return results


if __name__ == "__main__":
    main()
