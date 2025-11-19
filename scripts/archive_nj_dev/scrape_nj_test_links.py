#!/usr/bin/env python3
"""
Quick test to see if we can extract data using the clickable links as anchors
"""

import asyncio
from playwright.async_api import async_playwright

NJ_PORTAL_URL = "https://newjersey.mylicense.com/verification/Search.aspx?facility=Y"

async def test_link_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Navigate and search for Electrical Contractors
        await page.goto(NJ_PORTAL_URL, wait_until="networkidle")
        await asyncio.sleep(2)

        # Select profession
        await page.select_option("#t_web_lookup__profession_name", label="Electrical Contractors")
        await asyncio.sleep(1)

        # Click search
        await page.click("input[type='submit'][value='Search']")
        await asyncio.sleep(10)  # Wait for results

        # Extract using links as anchors
        contractors = await page.evaluate("""
            () => {
                const results = [];

                // Find all links that go to detail pages
                const links = document.querySelectorAll('a[href*="LicSearchDetail"]');
                console.log(`Found ${links.length} detail links`);

                links.forEach(link => {
                    const businessName = link.textContent.trim();

                    // Get the parent row
                    let row = link.closest('tr');
                    if (!row) return;

                    // Get all text from the row
                    const rowText = row.textContent.trim();
                    console.log(`Row text: ${rowText}`);

                    // Try to extract license number pattern from row text
                    const licenseMatch = rowText.match(/(34[A-Z]{2}\\d{7,8}|13VH\\d{7,8})/);
                    const licenseNumber = licenseMatch ? licenseMatch[1] : '';

                    // Try to extract status
                    const statusMatch = rowText.match(/(Active|Closed|Pending|Expired)/);
                    const status = statusMatch ? statusMatch[1] : '';

                    // Try to extract state code (2 capital letters at end)
                    const stateMatch = rowText.match(/\\b([A-Z]{2})\\s*$/);
                    const state = stateMatch ? stateMatch[1] : '';

                    if (businessName && licenseNumber) {
                        results.push({
                            business_name: businessName,
                            license_number: licenseNumber,
                            status: status,
                            state: state,
                            row_text: rowText.substring(0, 200)  // First 200 chars for debugging
                        });
                    }
                });

                return results;
            }
        """)

        print(f"\\nExtracted {len(contractors)} contractors")
        for i, c in enumerate(contractors[:5], 1):
            print(f"\\n{i}. {c['business_name']}")
            print(f"   License: {c['license_number']}")
            print(f"   Status: {c['status']}")
            print(f"   State: {c['state']}")
            print(f"   Row text: {c['row_text'][:100]}...")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_link_extraction())
