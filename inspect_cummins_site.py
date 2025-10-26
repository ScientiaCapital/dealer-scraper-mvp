"""
Quick script to inspect Cummins dealer locator DOM structure.
Runs in headed mode so we can see what's happening.
"""
from playwright.sync_api import sync_playwright
import json

def inspect_cummins():
    with sync_playwright() as p:
        # Launch browser in headless mode for automation
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("="*70)
        print("Navigating to Cummins dealer locator...")
        print("="*70)

        # Try the alternative URL first (likely less restrictive)
        url = "https://locator.cummins.com/"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=10000)
        except:
            print(f"Failed to load {url}, trying main URL...")
            url = "https://www.cummins.com/na/generators/home-standby/find-a-dealer"
            page.goto(url, wait_until="domcontentloaded", timeout=10000)

        print(f"\nPage loaded: {url}")
        print(f"Title: {page.title()}")

        # Wait a bit for any JavaScript to render
        page.wait_for_timeout(3000)

        print("\n" + "="*70)
        print("INSPECTING PAGE STRUCTURE")
        print("="*70)

        # Find all input elements
        inputs = page.locator('input').all()
        print(f"\nFound {len(inputs)} input elements:")
        for i, input_el in enumerate(inputs):
            try:
                attrs = {
                    'type': input_el.get_attribute('type'),
                    'id': input_el.get_attribute('id'),
                    'name': input_el.get_attribute('name'),
                    'class': input_el.get_attribute('class'),
                    'placeholder': input_el.get_attribute('placeholder'),
                    'aria-label': input_el.get_attribute('aria-label'),
                }
                # Filter out None values
                attrs = {k: v for k, v in attrs.items() if v}
                if attrs:
                    print(f"  [{i}] {json.dumps(attrs, indent=6)}")
            except:
                pass

        # Find all buttons
        buttons = page.locator('button').all()
        print(f"\nFound {len(buttons)} button elements:")
        for i, btn in enumerate(buttons):
            try:
                text = btn.text_content()
                attrs = {
                    'text': text.strip() if text else '',
                    'id': btn.get_attribute('id'),
                    'class': btn.get_attribute('class'),
                    'type': btn.get_attribute('type'),
                }
                attrs = {k: v for k, v in attrs.items() if v}
                if attrs:
                    print(f"  [{i}] {json.dumps(attrs, indent=6)}")
            except:
                pass

        # Check for iframes (dealer locators often use iframes)
        iframes = page.locator('iframe').all()
        print(f"\nFound {len(iframes)} iframe elements:")
        for i, iframe in enumerate(iframes):
            try:
                attrs = {
                    'src': iframe.get_attribute('src'),
                    'id': iframe.get_attribute('id'),
                    'class': iframe.get_attribute('class'),
                }
                attrs = {k: v for k, v in attrs.items() if v}
                if attrs:
                    print(f"  [{i}] {json.dumps(attrs, indent=6)}")
            except:
                pass

        print("\n" + "="*70)
        print("INSPECTION COMPLETE")
        print("="*70)

        browser.close()

if __name__ == "__main__":
    inspect_cummins()
