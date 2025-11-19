#!/usr/bin/env python3
"""
NJ Home Improvement Contractors - FULL Pagination Scrape

Dedicated scraper for Home Improvement Contractors only.
Runs through all pages to get complete dataset.
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import re
from pathlib import Path
from datetime import datetime

NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATE_SUFFIX = datetime.now().strftime("%Y%m%d")


def parse_html_for_contractors(html_content):
    """Parse HTML using regex to extract contractor data."""

    contractors = []

    # NJ HTML structure pattern
    record_pattern = r'<a[^>]+href="Details\.aspx[^"]*">([^<]+)</a>.*?</td><td><span>(34[A-Z]{2}\d{7,8}|13VH\d{7,8}|T-\d+)</span></td><td><span>([^<]+)</span></td><td><span>([^<]*)</span></td><td><span>(Active|Closed|Pending|Expired|Deleted)</span></td><td><span>([^<]*)</span></td><td><span>([A-Z]{2})</span></td>'

    matches = re.findall(record_pattern, html_content, re.DOTALL)

    for match in matches:
        business_name, license_number, profession, license_type, status, city, state = match

        contractors.append({
            'business_name': business_name.strip(),
            'license_number': license_number.strip(),
            'profession': profession.strip(),
            'license_type': license_type.strip(),
            'license_status': status.strip(),
            'city': city.strip(),
            'state': state.strip(),
            'phone': None,
            'source': 'NJ-MyLicense'
        })

    return contractors


def find_max_page(html_content):
    """Find the maximum page number from pagination links."""

    # Find all __doPostBack pagination links
    page_pattern = r"__doPostBack\('datagrid_results\$_ctl44\$_ctl(\d+)',''\)"
    page_numbers = re.findall(page_pattern, html_content)

    if not page_numbers:
        return 1  # Single page

    # Convert to integers and find max
    # _ctl0 = page 2, _ctl1 = page 3, so actual_page = ctl_number + 2
    ctl_numbers = [int(p) for p in page_numbers]
    max_page = max(ctl_numbers) + 2  # +2 because _ctl0 = page 2

    return max_page


async def scrape_home_improvement():
    """Scrape ALL pages of Home Improvement Contractors."""

    profession = "Home Improvement Contractors"

    print(f"\n{'='*80}")
    print(f"NJ HOME IMPROVEMENT CONTRACTORS - FULL SCRAPE")
    print(f"{'='*80}\n")

    all_contractors = []

    async with async_playwright() as p:
        print(f"   Launching browser...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        try:
            # Navigate and search
            print(f"   Navigating to portal...")
            await page.goto(NJ_PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            print(f"   Selecting profession: {profession}")
            await page.select_option("#t_web_lookup__profession_name", label=profession)
            await asyncio.sleep(2)

            print(f"   Clicking search...")
            try:
                await page.click("input[type='submit'][value='Search']", timeout=5000)
            except:
                pass

            # Wait for navigation to complete
            print(f"   Waiting for results to load...")
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except:
                await asyncio.sleep(15)  # Fallback wait

            # Get PAGE 1 data
            print(f"   📄 Scraping page 1...")

            # Wait a bit more to ensure page is fully settled
            await asyncio.sleep(3)
            html_content = await page.content()
            contractors_page_1 = parse_html_for_contractors(html_content)
            all_contractors.extend(contractors_page_1)
            print(f"      Found {len(contractors_page_1)} contractors")

            # Find total pages
            max_page = find_max_page(html_content)

            if max_page > 1:
                print(f"   📚 Found {max_page} total pages, scraping pages 2-{max_page}...")

                # Scrape pages 2 through max_page
                for page_num in range(2, max_page + 1):
                    print(f"   📄 Scraping page {page_num}...")

                    # Execute __doPostBack with correct parameters
                    # _ctl0 = page 2, _ctl1 = page 3, so ctl_number = page_num - 2
                    ctl_number = page_num - 2
                    postback_target = f"datagrid_results$_ctl44$_ctl{ctl_number}"

                    try:
                        # Execute the postback JavaScript
                        await page.evaluate(f"__doPostBack('{postback_target}', '')")

                        # Wait for navigation to complete
                        try:
                            await page.wait_for_load_state("networkidle", timeout=30000)
                        except:
                            await asyncio.sleep(10)  # Fallback wait

                        # Wait a bit more to ensure page is fully settled
                        await asyncio.sleep(3)

                        # Get HTML and extract contractors
                        html_content = await page.content()
                        contractors_this_page = parse_html_for_contractors(html_content)
                        all_contractors.extend(contractors_this_page)
                        print(f"      Found {len(contractors_this_page)} contractors")

                    except Exception as e:
                        print(f"      ⚠️  Error on page {page_num}: {e}")
                        continue

            else:
                print(f"   ℹ️  Single page results")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print(f"   Browser closed")

    # Filter to Active only
    active_contractors = [c for c in all_contractors if c['license_status'].lower() == 'active']

    print(f"\n   ✅ TOTAL: {len(all_contractors):,} contractors across all pages")
    print(f"   ✅ Active licenses: {len(active_contractors):,}")

    if active_contractors:
        print(f"   📋 Sample:")
        sample = active_contractors[0]
        print(f"      Name: {sample['business_name']}")
        print(f"      License: {sample['license_number']}")

    # Save to CSV
    output_file = OUTPUT_DIR / f"nj_home_improvement_contractors_full_{DATE_SUFFIX}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if active_contractors:
            writer = csv.DictWriter(f, fieldnames=active_contractors[0].keys())
            writer.writeheader()
            writer.writerows(active_contractors)

    print(f"   📄 Saved to: {output_file.name}")

    return active_contractors


async def main():
    contractors = await scrape_home_improvement()

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print(f"\n✅ Total active Home Improvement contractors: {len(contractors):,}")
    print(f"📁 File: output/state_licenses/new_jersey/nj_home_improvement_contractors_full_{DATE_SUFFIX}.csv")


if __name__ == "__main__":
    asyncio.run(main())
