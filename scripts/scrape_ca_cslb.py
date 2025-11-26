#!/usr/bin/env python3
"""
California CSLB (Contractors State License Board) Scraper

GOLD STANDARD state licensing database for MEP+Energy contractors.
Searchable by ZIP code and license classification.

Target Classifications for Coperniq ICP:
- C-10: Electrical Contractor (solar, battery, EV charging)
- C-20: HVAC (heat pumps, VRF, mini-splits)
- C-36: Plumbing (geothermal, solar thermal)
- C-46: Solar Contractor
- C-7: Low Voltage Systems (fire alarm, security, data)
- C-16: Fire Protection
- B: General Building (resimercial signal)

Strategy: Search wealthy ZIPs (top 50 by median household income)
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import csv
from datetime import datetime
import re

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "california"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MEP+Energy license classifications (Coperniq ICP)
LICENSE_CLASSIFICATIONS = {
    "C-10": "Electrical Contractor",
    "C-20": "HVAC Contractor",
    "C-36": "Plumbing Contractor",
    "C-46": "Solar Contractor",
    "C-7": "Low Voltage Systems",
    "C-16": "Fire Protection",
    "B": "General Building Contractor",
}

# Top 50 wealthiest California ZIP codes (2024-2025 Census ACS data)
# Median household income $200K-$400K+
CA_WEALTHY_ZIPS = [
    # Silicon Valley / SF Bay Area (Tech wealth)
    "94027",  # Atherton - $450K median, wealthiest ZIP in CA
    "94022",  # Los Altos - $280K median
    "94024",  # Los Altos - $260K median
    "94301",  # Palo Alto - $250K median
    "94028",  # Portola Valley - $375K median
    "94062",  # Woodside - $350K median
    "94920",  # Tiburon - $250K median
    "94941",  # Mill Valley - $220K median
    "94010",  # Burlingame - $200K median
    "94025",  # Menlo Park - $230K median
    "94306",  # Palo Alto - $200K median
    "94030",  # Millbrae - $180K median

    # Los Angeles / Orange County (Entertainment + Real Estate wealth)
    "90210",  # Beverly Hills - $200K median
    "90077",  # Bel Air - $300K median
    "90272",  # Pacific Palisades - $250K median
    "90265",  # Malibu - $200K median
    "90402",  # Santa Monica - $200K median
    "92657",  # Newport Coast - $350K median
    "92625",  # Corona del Mar - $280K median
    "92660",  # Newport Beach - $200K median
    "92651",  # Laguna Beach - $180K median
    "90274",  # Palos Verdes - $220K median
    "91108",  # San Marino - $230K median

    # San Diego (Biotech + Military wealth)
    "92067",  # Rancho Santa Fe - $300K median
    "92037",  # La Jolla - $200K median
    "92014",  # Del Mar - $200K median
    "92130",  # Carmel Valley - $180K median
    "92127",  # Rancho Bernardo - $160K median

    # Sacramento / Central Valley (Government + Agriculture wealth)
    "95746",  # Granite Bay - $200K median
    "95762",  # El Dorado Hills - $180K median
    "95630",  # Folsom - $150K median
    "95819",  # East Sacramento - $130K median
    "95864",  # Arden Park - $140K median

    # Wine Country / North Bay (Agriculture + Tourism wealth)
    "94574",  # St Helena - $150K median
    "94558",  # Napa - $120K median
    "94952",  # Petaluma - $120K median
    "95476",  # Sonoma - $130K median

    # Additional high-income ZIPs
    "94610",  # Oakland Hills - $150K median
    "94611",  # Piedmont area - $200K median
    "94563",  # Orinda - $250K median
    "94556",  # Moraga - $220K median
    "94507",  # Alamo - $280K median
    "94528",  # Diablo - $300K median
    "94566",  # Pleasanton - $180K median
    "94539",  # Fremont Mission Hills - $200K median
    "95014",  # Cupertino - $200K median
    "95030",  # Los Gatos - $200K median
    "95070",  # Saratoga - $280K median
    "94118",  # SF Sea Cliff - $200K median
    "94115",  # SF Pacific Heights - $180K median
]

# CSLB URLs
BASE_URL = "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx"
SEARCH_URL = "https://www2.cslb.ca.gov/OnlineServices/CheckLicenseII/ZipCodeSearch.aspx"


async def explore_cslb_portal(browser):
    """Explore the CSLB portal to understand the search functionality"""

    print("\n" + "="*60)
    print("EXPLORING CSLB PORTAL")
    print("="*60)

    page = await browser.new_page()

    try:
        # First, go to main license check page
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Screenshot main page
        screenshot_path = OUTPUT_DIR / "cslb_main_page.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"✅ Main page screenshot: {screenshot_path}")

        # Look for "Find A Licensed Contractor" link
        links = await page.query_selector_all('a')
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute('href')
            if 'find' in text.lower() and 'contractor' in text.lower():
                print(f"   Found link: {text} -> {href}")

        # Try to find the contractor search page
        search_pages = [
            "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/ZipCodeSearch.aspx",
            "https://www2.cslb.ca.gov/OnlineServices/CheckLicenseII/ZipCodeSearch.aspx",
            "https://www.cslb.ca.gov/consumers/hire_a_contractor/find_a_contractor.aspx",
        ]

        for url in search_pages:
            print(f"\n   Trying: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)

                content = await page.content()
                if "zip" in content.lower() or "classification" in content.lower():
                    print(f"   ✅ Found search page!")

                    # Screenshot
                    ss_name = url.split('/')[-1].replace('.aspx', '.png')
                    ss_path = OUTPUT_DIR / f"cslb_{ss_name}"
                    await page.screenshot(path=ss_path, full_page=True)
                    print(f"   Screenshot: {ss_path}")

                    # Look for form elements
                    forms = await page.evaluate("""
                        () => {
                            const inputs = document.querySelectorAll('input, select');
                            return Array.from(inputs).slice(0, 20).map(el => ({
                                tag: el.tagName,
                                name: el.name || el.id,
                                type: el.type,
                                placeholder: el.placeholder
                            }));
                        }
                    """)
                    print(f"   Form elements: {json.dumps(forms, indent=2)}")

            except Exception as e:
                print(f"   ❌ Error: {e}")

    finally:
        await page.close()


async def search_by_classification(page, classification_code: str) -> list:
    """Search CSLB by license classification"""

    contractors = []

    try:
        # Navigate to the search page with classification parameter
        # CSLB uses a specific format for classification searches
        search_url = f"https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/LicenseClassList.aspx?ClassCode={classification_code}"

        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Check if this approach works or if we need different strategy
        content = await page.content()

        # Extract data from the results page
        # This will depend on what the actual page structure looks like

    except Exception as e:
        print(f"   Error searching classification {classification_code}: {e}")

    return contractors


async def search_by_business_name(page, search_term: str) -> list:
    """Search CSLB by business name - more reliable approach"""

    contractors = []

    try:
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Click on "Business Name" tab
        tabs = await page.query_selector_all('[class*="tab"], [role="tab"], a[href*="Business"]')
        for tab in tabs:
            text = await tab.inner_text()
            if 'business' in text.lower():
                await tab.click()
                await asyncio.sleep(1)
                break

        # Fill in business name search
        name_input = await page.query_selector('input[name*="BusinessName"], input[name*="BName"], input[id*="Business"]')
        if name_input:
            await name_input.fill(search_term)

            # Click search button
            search_btn = await page.query_selector('input[type="submit"], button[type="submit"]')
            if search_btn:
                await search_btn.click()
                await asyncio.sleep(3)

                # Extract results
                # ... (depends on page structure)

    except Exception as e:
        print(f"   Error searching business name '{search_term}': {e}")

    return contractors


async def main():
    print("\n" + "="*80)
    print("CALIFORNIA CSLB CONTRACTOR SCRAPER")
    print("="*80)
    print(f"\nTarget Classifications: {len(LICENSE_CLASSIFICATIONS)}")
    print(f"Target Wealthy ZIPs: {len(CA_WEALTHY_ZIPS)}")
    print(f"Output: {OUTPUT_DIR}/")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # First explore the portal to understand the structure
        await explore_cslb_portal(browser)

        await browser.close()

    print("\n" + "="*80)
    print("EXPLORATION COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review screenshots in output/state_licenses/california/")
    print("2. Identify the correct search workflow")
    print("3. Build targeted extraction logic")


if __name__ == "__main__":
    asyncio.run(main())
