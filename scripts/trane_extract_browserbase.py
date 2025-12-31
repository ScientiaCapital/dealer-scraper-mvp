#!/usr/bin/env python3
"""Extract Trane dealers using Browserbase cloud browser."""

import json
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# Load .env manually
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

BROWSERBASE_API_KEY = os.getenv('BROWSERBASE_API_KEY')
BROWSERBASE_PROJECT_ID = os.getenv('BROWSERBASE_PROJECT_ID')

def extract_trane_dealers():
    """Extract all Trane dealers from directory page."""
    print(f"Starting Trane extraction at {datetime.now().isoformat()}")
    print(f"Browserbase Project: {BROWSERBASE_PROJECT_ID}")

    # Create session using SDK
    from browserbase import Browserbase
    bb = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
    print(f"Session ID: {session.id}")

    ws_url = session.connect_url
    print(f"Connecting to cloud browser...")

    dealers = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        try:
            print("Navigating to Trane dealer directory...")
            page.goto('https://www.trane.com/residential/en/dealers/', timeout=90000)
            print("Page loaded, waiting for content...")
            time.sleep(5)

            # Take screenshot to debug
            screenshot_path = 'output/trane/trane_page_debug.png'
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

            # Try multiple selectors for the table
            print("Looking for dealer table...")

            # Try to find any table on page
            table_count = page.locator('table').count()
            print(f"Found {table_count} tables on page")

            # Wait longer and scroll
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(3)

            # Try clicking cookie accept if present
            try:
                cookie_btns = page.locator('button:has-text("Accept"), button:has-text("agree"), button:has-text("Continue")').all()
                if cookie_btns:
                    print(f"Found {len(cookie_btns)} cookie buttons, clicking first...")
                    cookie_btns[0].click(timeout=5000)
                    time.sleep(2)
            except Exception as e:
                print(f"Cookie handling: {e}")

            # Wait for table rows
            try:
                page.wait_for_selector('table tbody tr', timeout=60000)
                print("Table rows found!")
            except:
                print("No table rows yet, checking page content...")
                # Get page HTML to inspect
                html_sample = page.evaluate("document.body.innerHTML.substring(0, 3000)")
                print(f"Page HTML sample (first 1000 chars):\n{html_sample[:1000]}")

            # Extract dealer links and data
            print("Extracting dealer data...")
            dealers = page.evaluate("""
            () => {
                const dealers = [];

                // Try multiple table selectors
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const rows = table.querySelectorAll('tbody tr');
                    if (rows.length > 10) {
                        console.log('Found dealers table with ' + rows.length + ' rows');
                        rows.forEach((tr) => {
                            const cells = tr.querySelectorAll('td');
                            if (cells.length >= 3) {
                                const link = tr.querySelector('a[href*="/dealers/"]');
                                dealers.push({
                                    name: cells[0]?.textContent?.trim() || '',
                                    city: cells[1]?.textContent?.trim() || '',
                                    state: cells[2]?.textContent?.trim() || '',
                                    zip: cells[3]?.textContent?.trim() || '',
                                    detail_url: link?.href || ''
                                });
                            }
                        });
                    }
                }

                // Also try to find dealer links anywhere on page
                if (dealers.length === 0) {
                    const links = document.querySelectorAll('a[href*="/dealers/"]');
                    links.forEach(link => {
                        const url = link.href;
                        if (url.match(/dealers\/[^/]+\/?$/)) {
                            dealers.push({
                                name: link.textContent?.trim() || '',
                                detail_url: url
                            });
                        }
                    });
                }

                return dealers;
            }
            """)

            print(f"Extracted {len(dealers)} dealers")

            # If we got very few, try "Show All" dropdown
            if len(dealers) < 50 and len(dealers) > 0:
                print("Trying to show all entries...")
                try:
                    select = page.locator('select[name*="length"]').first
                    if select.count() > 0:
                        select.select_option('-1')
                        time.sleep(10)
                        # Re-extract
                        dealers = page.evaluate("""
                        () => {
                            const dealers = [];
                            document.querySelectorAll('table tbody tr').forEach((tr) => {
                                const cells = tr.querySelectorAll('td');
                                if (cells.length >= 3) {
                                    const link = tr.querySelector('a[href*="/dealers/"]');
                                    dealers.push({
                                        name: cells[0]?.textContent?.trim() || '',
                                        city: cells[1]?.textContent?.trim() || '',
                                        state: cells[2]?.textContent?.trim() || '',
                                        zip: cells[3]?.textContent?.trim() || '',
                                        detail_url: link?.href || ''
                                    });
                                }
                            });
                            return dealers;
                        }
                        """)
                        print(f"After 'Show All': {len(dealers)} dealers")
                except Exception as e:
                    print(f"Show all failed: {e}")

        finally:
            browser.close()
            # Mark session as complete
            try:
                bb.sessions.update(session.id, status="COMPLETED")
            except:
                pass

    return dealers

def main():
    try:
        dealers = extract_trane_dealers()

        if not dealers:
            print("ERROR: No dealers extracted!")
            return

        # Save to JSON
        output = {
            'extracted_at': datetime.now().isoformat(),
            'total_count': len(dealers),
            'dealers': dealers
        }

        output_path = 'output/trane/trane_dealers.json'
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✓ Saved {len(dealers)} dealers to {output_path}")

        # Show sample
        print("\nSample dealers:")
        for d in dealers[:5]:
            print(f"  - {d.get('name', 'N/A')} | {d.get('city', 'N/A')}, {d.get('state', 'N/A')}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
