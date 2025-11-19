#!/usr/bin/env python3
"""
New Jersey Contractor License Portal Exploration

Tests the NJ MyLicense portal to understand:
1. Search form structure
2. Results table structure
3. Pagination
4. Data fields available

Usage:
    python3 scripts/test_nj_portal.py
"""

import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

# Target URL
NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def explore_nj_portal():
    """Explore NJ contractor licensing portal."""

    async with async_playwright() as p:
        print("🌐 Launching browser...")
        browser = await p.chromium.launch(headless=False)  # Non-headless to see what's happening
        page = await browser.new_page()

        print(f"\n📄 Navigating to: {NJ_PORTAL_URL}")
        await page.goto(NJ_PORTAL_URL, wait_until="networkidle")
        await asyncio.sleep(2)

        print("\n📸 Taking screenshot of search form...")
        await page.screenshot(path=OUTPUT_DIR / "nj_search_form.png")

        # Step 1: Explore profession dropdown
        print("\n🔍 Exploring Profession dropdown...")
        profession_selector = "#t_web_lookup__profession_name"

        # Get all profession options
        professions = await page.evaluate(f"""
            () => {{
                const select = document.querySelector('{profession_selector}');
                if (!select) return [];
                return Array.from(select.options).map(opt => ({{
                    value: opt.value,
                    text: opt.text
                }}));
            }}
        """)

        print(f"   Found {len(professions)} profession options")

        # Find our target professions
        target_professions = ["Electrical Contractors", "HVACR", "Home Improvement Contractors"]
        found_professions = []

        for prof in professions:
            if prof['text'] in target_professions:
                found_professions.append(prof)
                print(f"   ✅ Found: {prof['text']} (value: {prof['value']})")

        # Save profession list
        with open(OUTPUT_DIR / "nj_professions.json", 'w') as f:
            json.dump(professions, f, indent=2)

        # Step 2: Test search for Electrical Contractors
        print("\n🔍 Testing search for Electrical Contractors...")

        # Select "Electrical Contractors" from dropdown
        await page.select_option(profession_selector, label="Electrical Contractors")
        await asyncio.sleep(1)

        # Click search button
        print("   Clicking search button...")
        search_button_selector = "input[type='submit'][value='Search']"
        await page.click(search_button_selector)

        # Wait for results
        print("   Waiting for results...")
        await asyncio.sleep(5)  # Give it time to load

        print("\n📸 Taking screenshot of results...")
        await page.screenshot(path=OUTPUT_DIR / "nj_electrical_results.png")

        # Step 3: Analyze results structure
        print("\n📊 Analyzing results structure...")

        # Check if there's a results table
        results_table = await page.query_selector("table")

        if results_table:
            print("   ✅ Found results table!")

            # Get table HTML structure
            table_html = await results_table.inner_html()

            # Extract headers
            headers = await page.evaluate("""
                () => {
                    const table = document.querySelector('table');
                    if (!table) return [];
                    const headerRow = table.querySelector('thead tr, tbody tr:first-child');
                    if (!headerRow) return [];
                    return Array.from(headerRow.querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                }
            """)

            print(f"   Table headers: {headers}")

            # Extract first 5 rows of data
            rows = await page.evaluate("""
                () => {
                    const table = document.querySelector('table');
                    if (!table) return [];
                    const dataRows = table.querySelectorAll('tbody tr');
                    const results = [];

                    for (let i = 0; i < Math.min(5, dataRows.length); i++) {
                        const cells = dataRows[i].querySelectorAll('td');
                        const row = {};
                        cells.forEach((cell, idx) => {
                            row[`col_${idx}`] = cell.textContent.trim();
                        });
                        results.push(row);
                    }

                    return results;
                }
            """)

            print(f"\n   Sample data (first 5 rows):")
            for i, row in enumerate(rows, 1):
                print(f"   Row {i}: {row}")

            # Save results structure
            results_data = {
                'headers': headers,
                'sample_rows': rows,
                'table_html_preview': table_html[:500]  # First 500 chars
            }

            with open(OUTPUT_DIR / "nj_results_structure.json", 'w') as f:
                json.dump(results_data, f, indent=2)

            # Check for pagination
            pagination = await page.evaluate("""
                () => {
                    const paginationLinks = document.querySelectorAll('a[href*="Page"], .pagination a, a:contains("Next")');
                    return Array.from(paginationLinks).map(link => ({
                        text: link.textContent.trim(),
                        href: link.getAttribute('href')
                    }));
                }
            """)

            if pagination:
                print(f"\n   📄 Pagination found: {len(pagination)} links")
                for link in pagination[:5]:
                    print(f"      {link}")
            else:
                print("\n   ⚠️  No pagination found (might be single page or different structure)")

            # Count total results
            total_results = await page.evaluate("""
                () => {
                    const table = document.querySelector('table');
                    if (!table) return 0;
                    return table.querySelectorAll('tbody tr').length;
                }
            """)

            print(f"\n   Total results on page: {total_results}")

        else:
            print("   ⚠️  No results table found")
            print("   Checking for error messages or alternative structure...")

            # Get all text content to see what's there
            page_text = await page.evaluate("() => document.body.textContent")
            print(f"   Page text preview: {page_text[:500]}")

        # Step 4: Check for detail links
        print("\n🔗 Checking for detail links...")
        detail_links = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('table tbody tr a');
                return Array.from(links).slice(0, 5).map(link => ({
                    text: link.textContent.trim(),
                    href: link.getAttribute('href')
                }));
            }
        """)

        if detail_links:
            print(f"   Found {len(detail_links)} detail links (showing first 5):")
            for link in detail_links:
                print(f"      {link['text']} -> {link['href']}")

            # Click first detail link to see detail page structure
            if detail_links:
                print("\n🔍 Exploring detail page...")
                first_link = detail_links[0]
                await page.click(f"table tbody tr a:text('{first_link['text']}')")
                await asyncio.sleep(2)

                print("   📸 Taking screenshot of detail page...")
                await page.screenshot(path=OUTPUT_DIR / "nj_detail_page.png")

                # Extract all visible text fields
                detail_fields = await page.evaluate("""
                    () => {
                        const fields = {};
                        const labels = document.querySelectorAll('label, th, .label, .field-label');
                        labels.forEach(label => {
                            const text = label.textContent.trim();
                            const nextElement = label.nextElementSibling;
                            if (nextElement) {
                                fields[text] = nextElement.textContent.trim();
                            }
                        });
                        return fields;
                    }
                """)

                print(f"   Detail page fields:")
                for key, value in list(detail_fields.items())[:10]:
                    print(f"      {key}: {value}")

                # Save detail structure
                with open(OUTPUT_DIR / "nj_detail_structure.json", 'w') as f:
                    json.dump(detail_fields, f, indent=2)
        else:
            print("   No detail links found in results table")

        print("\n✅ Exploration complete!")
        print(f"   Screenshots saved to: {OUTPUT_DIR}")
        print(f"   Structure data saved as JSON files")

        # Keep browser open for manual inspection
        print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)

        await browser.close()


async def main():
    print("=" * 80)
    print("NEW JERSEY CONTRACTOR PORTAL EXPLORATION")
    print("=" * 80)

    await explore_nj_portal()

    print("\n" + "=" * 80)
    print("EXPLORATION COMPLETE")
    print("=" * 80)
    print(f"\nNext steps:")
    print(f"1. Review screenshots in: {OUTPUT_DIR}")
    print(f"2. Check JSON files for structure details")
    print(f"3. Build production scraper based on findings")


if __name__ == "__main__":
    asyncio.run(main())
