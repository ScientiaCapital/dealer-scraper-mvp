#!/usr/bin/env python3
"""
New Jersey Contractor License Scraper

Scrapes MEP+Energy contractors from NJ Division of Consumer Affairs:
- Electrical Contractors
- HVACR (Master HVACR Contractor)
- Home Improvement Contractors

Key insight: NJ loads ALL results in a single page (massive table), so
one page load = all contractors for that profession!

Usage:
    python3 scripts/scrape_nj_licenses.py

Output:
    output/state_licenses/new_jersey/nj_electrical_contractors_YYYYMMDD.csv
    output/state_licenses/new_jersey/nj_hvacr_contractors_YYYYMMDD.csv
    output/state_licenses/new_jersey/nj_home_improvement_contractors_YYYYMMDD.csv
    output/state_licenses/new_jersey/nj_mep_contractors_combined_YYYYMMDD.csv
"""

import asyncio
from playwright.async_api import async_playwright
import csv
import re
from pathlib import Path
from datetime import datetime

# Configuration
NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "new_jersey"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATE_SUFFIX = datetime.now().strftime("%Y%m%d")

# Target professions
PROFESSIONS = [
    "Electrical Contractors",
    "HVACR",
    "Home Improvement Contractors"
]


def normalize_phone(phone_str):
    """Extract 10-digit phone number."""
    if not phone_str:
        return None

    digits = re.sub(r'\D', '', phone_str)

    # Remove leading 1 for US country code
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]

    if len(digits) == 10:
        return digits

    return None


def parse_results_table(page_html):
    """
    Parse NJ results table structure.

    NJ loads all results in one massive table with repeating column groups:
    - Every 10 columns = 1 contractor record
    - col_5/6: Business name (duplicate)
    - col_9: License number
    - col_10: Profession
    - col_11: License type
    - col_12: Status
    - col_13: City
    - col_14: State

    Returns:
        List of contractor dicts
    """
    contractors = []

    # Pattern: Find all text nodes that match the structure
    # We'll look for license numbers (format: 34EB12345, 34TE12345, etc.)
    license_pattern = r'\b34[A-Z]{2}\d{7,8}\b'

    # Split the HTML into tokens
    tokens = re.split(r'[\n\t]+', page_html)

    # Clean tokens
    tokens = [t.strip() for t in tokens if t.strip()]

    # Find license numbers as anchors
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Check if this looks like a license number
        if re.match(license_pattern, token):
            # Found a license number - extract surrounding fields
            # Look back for business name (should be 1-4 tokens before)
            business_name = None
            for lookback in range(1, 5):
                if i - lookback >= 0:
                    candidate = tokens[i - lookback]
                    # Business names are usually > 3 chars and not just punctuation
                    if len(candidate) > 3 and not re.match(r'^[^a-zA-Z]+$', candidate):
                        business_name = candidate
                        break

            # Look ahead for profession, license type, status, city, state
            profession = tokens[i + 1] if i + 1 < len(tokens) else None
            license_type = tokens[i + 2] if i + 2 < len(tokens) else None
            status = tokens[i + 3] if i + 3 < len(tokens) else None
            city = tokens[i + 4] if i + 4 < len(tokens) else None
            state = tokens[i + 5] if i + 5 < len(tokens) else None

            # Only include if we have the key fields
            if business_name and profession and status:
                contractors.append({
                    'business_name': business_name,
                    'license_number': token,
                    'profession': profession,
                    'license_type': license_type or '',
                    'license_status': status,
                    'city': city or '',
                    'state': state or '',
                    'phone': None,  # No phone in NJ data
                    'source': 'NJ-MyLicense'
                })

        i += 1

    return contractors


async def scrape_profession(page, profession):
    """Scrape all contractors for a given profession."""

    print(f"\n🔍 Scraping: {profession}")
    print(f"   Navigating to: {NJ_PORTAL_URL}")

    # Navigate to search page
    await page.goto(NJ_PORTAL_URL, wait_until="networkidle")
    await asyncio.sleep(2)

    # Select profession from dropdown
    print(f"   Selecting profession: {profession}")
    profession_selector = "#t_web_lookup__profession_name"
    await page.select_option(profession_selector, label=profession)
    await asyncio.sleep(1)

    # Click search button (no navigation wait needed - it's AJAX)
    print(f"   Clicking search...")
    search_button_selector = "input[type='submit'][value='Search']"
    await page.click(search_button_selector)

    # Wait for results to load (simple sleep like test script)
    print(f"   Waiting for results...")
    await asyncio.sleep(10)  # Give plenty of time for AJAX to complete

    # Wait for the results table to have actual data (wait for a link to appear)
    try:
        await page.wait_for_selector('a[href*="LicSearchDetail"]', timeout=10000)
        print(f"   ✅ Results table loaded with data")
    except:
        print(f"   ⚠️  Warning: No detail links found, will try to extract anyway")

    # Debug: Save screenshot and check for results
    safe_prof_name = profession.replace(" ", "_").lower()
    await page.screenshot(path=OUTPUT_DIR / f"debug_{safe_prof_name}.png")

    # Check if results loaded
    result_check = await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a[href*="LicSearchDetail"]');
            const table = document.querySelector('table');
            const allText = document.body.textContent;

            return {
                linkCount: links.length,
                hasTable: !!table,
                hasSearchResults: allText.includes('Search Results'),
                bodyLength: allText.length
            };
        }
    """)

    print(f"   Debug info: {result_check}")

    # Extract data using JavaScript - parse the HTML table directly
    print(f"   Extracting data...")

    contractors = await page.evaluate("""
        () => {
            const results = [];

            // Get all text content from the page
            const allText = document.body.textContent;

            // Split by newlines and tabs, clean up whitespace
            const tokens = allText.split(/[\\n\\t]+/)
                .map(t => t.trim())
                .filter(t => t.length > 0);

            // Pattern to match license numbers:
            // - Electrical/Home Improvement: 34XX######## or 13VH########
            // - HVACR: T-##### format
            const licensePattern = /^(34[A-Z]{2}\\d{7,8}|13VH\\d{7,8}|T-\\d+)$/;

            // Iterate through tokens looking for license numbers
            for (let i = 0; i < tokens.length; i++) {
                const token = tokens[i];

                // Check if this is a license number
                if (licensePattern.test(token)) {
                    const licenseNumber = token;

                    // Look backward for business name (within 10 tokens)
                    // Business name should be before the license number
                    let businessName = '';
                    for (let j = i - 1; j >= Math.max(0, i - 10); j--) {
                        const candidate = tokens[j];

                        // Skip known header text and field labels
                        if (candidate === 'Full Name' ||
                            candidate === 'License Number' ||
                            candidate === 'Profession' ||
                            candidate === 'License Type' ||
                            candidate === 'License Status' ||
                            candidate === 'City' ||
                            candidate === 'State' ||
                            candidate === 'Search Results') {
                            continue;
                        }

                        // Business name should be substantial (> 2 chars) and not a license number
                        if (candidate.length > 2 && !licensePattern.test(candidate)) {
                            businessName = candidate;
                            break;
                        }
                    }

                    // Look forward for: profession, license type, status, city, state (next 5 tokens)
                    const profession = i + 1 < tokens.length ? tokens[i + 1] : '';
                    const licenseType = i + 2 < tokens.length ? tokens[i + 2] : '';
                    const status = i + 3 < tokens.length ? tokens[i + 3] : '';
                    const city = i + 4 < tokens.length ? tokens[i + 4] : '';
                    const state = i + 5 < tokens.length ? tokens[i + 5] : '';

                    // Only add if we got the essentials
                    if (businessName && licenseNumber && status) {
                        results.push({
                            business_name: businessName,
                            license_number: licenseNumber,
                            profession: profession,
                            license_type: licenseType,
                            license_status: status,
                            city: city,
                            state: state,
                            phone: null,
                            source: 'NJ-MyLicense'
                        });
                    }
                }
            }

            return results;
        }
    """)

    # Debug: Show sample of what we extracted
    if contractors:
        print(f"   📋 Sample record:")
        sample = contractors[0]
        for key, value in sample.items():
            print(f"      {key}: '{value}'")

    # Filter to Active licenses only
    active_contractors = [c for c in contractors if c['license_status'].lower() == 'active']

    print(f"   ✅ Found {len(contractors):,} total contractors")
    print(f"   ✅ Filtered to {len(active_contractors):,} Active licenses")

    # Debug: Show unique status values
    if contractors:
        unique_statuses = set(c['license_status'] for c in contractors)
        print(f"   📊 Unique status values: {unique_statuses}")

    # Save to CSV
    safe_profession_name = profession.replace(" ", "_").replace("/", "_").lower()
    output_file = OUTPUT_DIR / f"nj_{safe_profession_name}_{DATE_SUFFIX}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if active_contractors:
            writer = csv.DictWriter(f, fieldnames=active_contractors[0].keys())
            writer.writeheader()
            writer.writerows(active_contractors)

    print(f"   📄 Saved to: {output_file.name}")

    return active_contractors


async def main():
    print("=" * 80)
    print("NEW JERSEY CONTRACTOR LICENSE SCRAPER")
    print("=" * 80)
    print(f"\nTarget professions: {len(PROFESSIONS)}")
    for prof in PROFESSIONS:
        print(f"  - {prof}")

    all_contractors = []

    async with async_playwright() as p:
        print("\n🌐 Launching browser...")
        browser = await p.chromium.launch(
            headless=False,  # Try non-headless to see if NJ has bot detection
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )

        # Capture console logs for debugging
        page.on("console", lambda msg: print(f"   [Browser] {msg.text}"))

        # Scrape each profession
        for profession in PROFESSIONS:
            try:
                contractors = await scrape_profession(page, profession)
                all_contractors.extend(contractors)
            except Exception as e:
                print(f"   ❌ Error scraping {profession}: {e}")
                continue

        await browser.close()

    # Save combined file
    if all_contractors:
        combined_file = OUTPUT_DIR / f"nj_mep_contractors_combined_{DATE_SUFFIX}.csv"

        with open(combined_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_contractors[0].keys())
            writer.writeheader()
            writer.writerows(all_contractors)

        print(f"\n✅ Combined file: {combined_file.name}")

    # Summary
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   - Total contractors scraped: {len(all_contractors):,}")

    # Breakdown by profession
    profession_counts = {}
    for c in all_contractors:
        prof = c['profession']
        profession_counts[prof] = profession_counts.get(prof, 0) + 1

    for prof, count in profession_counts.items():
        print(f"   - {prof}: {count:,}")

    print(f"\n📁 Files saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
