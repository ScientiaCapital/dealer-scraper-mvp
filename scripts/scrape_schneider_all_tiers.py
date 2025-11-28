#!/usr/bin/env python3
"""
Schneider Electric EcoXpert Scraper - All Certification Tiers

Scrapes ALL 190 EcoXperts with their certification tiers:
- EcoXpert Building Automation (Certified/Master)
- EcoXpert Building Security (Certified/Master)
- EcoXpert Power Distribution (Master only)
- EcoXpert Power Management (Certified/Master)
- EcoXpert Power Services (Certified/Master)
- EcoXpert Critical IT Infrastructure (Master only)

Outputs:
- JSON file with all contractors and their certifications
- CSV file ready for sales-agent import
"""

import asyncio
import json
import csv
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Certification areas and their available tiers
CERTIFICATION_AREAS = {
    "EcoXpert Building Automation": ["Certified", "Master"],
    "EcoXpert Building Security": ["Certified", "Master"],
    "EcoXpert Power Distribution": ["Master"],  # Only Master available
    "EcoXpert Power Management": ["Certified", "Master"],
    "EcoXpert Power Services": ["Certified", "Master"],
    "EcoXpert Critical IT Infrastructure": ["Master"],  # Only Master available
}

BASE_URL = "https://www.se.com/us/en/locate/5-find-a-system-integrator-ecoxpert"


async def extract_contractors(page) -> list:
    """Extract all visible contractors from the current page state."""
    return await page.evaluate("""
    () => {
        const results = [];
        const detailLinks = document.querySelectorAll('a[href*="/locate/accounts/"]');

        detailLinks.forEach(link => {
            let card = link.parentElement;
            while (card && !card.querySelector('a[href^="tel:"], a[href^="mailto:"]')) {
                card = card.parentElement;
                if (!card || card.tagName === 'BODY') {
                    card = link.parentElement?.parentElement?.parentElement;
                    break;
                }
            }
            if (!card) return;

            // Company name
            const nameDiv = link.previousElementSibling;
            const name = nameDiv ? nameDiv.textContent.trim() : '';

            // Phone
            const phoneLink = card.querySelector('a[href^="tel:"]');
            const phone = phoneLink ? phoneLink.textContent.trim() : '';

            // Email
            const emailLink = card.querySelector('a[href^="mailto:"]');
            const email = emailLink ? emailLink.textContent.trim() : '';

            // Website
            let website = '';
            const allLinks = card.querySelectorAll('a[href^="http"]');
            for (const a of allLinks) {
                if (!a.href.includes('se.com')) { website = a.href; break; }
            }

            // City
            let city = '';
            const divs = card.querySelectorAll('div');
            for (const div of divs) {
                const text = div.textContent?.trim();
                if (text && text.length > 2 && text.length < 30 &&
                    !text.includes('@') && !text.includes('Show') &&
                    !text.includes('Website') && !text.includes('Open') &&
                    !text.includes('Hours') && /^[A-Z][A-Za-z\\s']+$/.test(text)) {
                    city = text;
                    break;
                }
            }

            // Detail URL (unique ID)
            const detailUrl = link.href;
            const accountId = detailUrl.match(/accounts\\/([^/]+)/)?.[1] || '';

            if (name && name.length > 2 && !name.includes('Show Details')) {
                results.push({
                    name,
                    phone,
                    email,
                    website,
                    city,
                    detail_url: detailUrl,
                    account_id: accountId
                });
            }
        });

        // Deduplicate by detail_url
        const seen = new Set();
        return results.filter(c => {
            if (seen.has(c.detail_url)) return false;
            seen.add(c.detail_url);
            return true;
        });
    }
    """)


async def click_show_more_until_done(page, max_clicks=20):
    """Click 'Show more' button until all results are loaded."""
    click_count = 0
    while click_count < max_clicks:
        try:
            show_more = page.locator('button:has-text("Show more")')
            if not await show_more.is_visible(timeout=2000):
                break
            await show_more.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await show_more.click()
            click_count += 1
            await asyncio.sleep(1.2)
        except Exception:
            break
    return click_count


async def clear_all_filters(page):
    """Clear all certification filters."""
    try:
        clear_btn = page.locator('button:has-text("Clear All")')
        if await clear_btn.is_visible(timeout=2000):
            await clear_btn.click()
            await asyncio.sleep(1.5)
    except Exception:
        pass


async def select_certification_tier(page, cert_area: str, tier: str) -> int:
    """Select a specific certification tier and return result count."""
    # First clear all filters
    await clear_all_filters(page)
    await asyncio.sleep(1)

    # Find and click the tier checkbox
    # The structure is: cert_area label -> sibling container with Certified/Master checkboxes
    try:
        # Click on the tier checkbox container (not the input itself due to Svelte overlay)
        tier_checkbox = page.locator(f'text="{tier}"').first

        # Try to find it within the certification area context
        cert_section = page.locator(f'text="{cert_area}"').locator('..').locator('..')
        tier_in_section = cert_section.locator(f'text="{tier}"').first

        if await tier_in_section.is_visible(timeout=3000):
            await tier_in_section.click()
        else:
            await tier_checkbox.click()

        await asyncio.sleep(2)

        # Get result count
        results_text = await page.locator('text=/\\d+ Results?/').first.text_content()
        count = int(results_text.split()[0])
        return count

    except Exception as e:
        print(f"  ⚠️ Error selecting {cert_area} - {tier}: {e}")
        return 0


async def scrape_all_certifications():
    """Main scraping function to get all EcoXperts with certification data."""

    all_contractors = {}  # account_id -> contractor data

    async with async_playwright() as p:
        print("🚀 Starting Schneider Electric EcoXpert scraper...")

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # Navigate to EcoXpert locator
        print(f"📍 Navigating to {BASE_URL}")
        await page.goto(BASE_URL, timeout=60000)
        await asyncio.sleep(4)

        # Accept cookies if present
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        # First, get ALL contractors without filters (baseline)
        print("\n📊 Getting baseline (all 190 EcoXperts)...")
        await click_show_more_until_done(page)
        baseline = await extract_contractors(page)
        print(f"   Found {len(baseline)} total contractors")

        # Store baseline data
        for c in baseline:
            all_contractors[c['account_id']] = {
                **c,
                'certifications': [],
                'is_master': False,
                'certification_areas': []
            }

        # Now iterate through each certification area and tier
        for cert_area, tiers in CERTIFICATION_AREAS.items():
            print(f"\n🔍 Processing: {cert_area}")

            for tier in tiers:
                # Refresh page for clean state
                await page.goto(BASE_URL, timeout=60000)
                await asyncio.sleep(3)

                # Select the certification tier
                print(f"   → Filtering by {tier}...")
                count = await select_certification_tier(page, cert_area, tier)

                if count > 0:
                    print(f"   → Found {count} contractors, loading all...")
                    await click_show_more_until_done(page)
                    contractors = await extract_contractors(page)
                    print(f"   → Extracted {len(contractors)} contractors")

                    # Tag these contractors with their certification
                    cert_label = f"{cert_area} - {tier}"
                    for c in contractors:
                        if c['account_id'] in all_contractors:
                            if cert_label not in all_contractors[c['account_id']]['certifications']:
                                all_contractors[c['account_id']]['certifications'].append(cert_label)
                            if tier == "Master":
                                all_contractors[c['account_id']]['is_master'] = True
                            if cert_area not in all_contractors[c['account_id']]['certification_areas']:
                                all_contractors[c['account_id']]['certification_areas'].append(cert_area)
                else:
                    print(f"   → No contractors found for this filter")

        await browser.close()

    return list(all_contractors.values())


def save_results(contractors: list, output_dir: Path):
    """Save contractors to JSON and CSV files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Calculate stats
    total = len(contractors)
    with_phone = sum(1 for c in contractors if c.get('phone'))
    with_email = sum(1 for c in contractors if c.get('email'))
    with_website = sum(1 for c in contractors if c.get('website'))
    masters = sum(1 for c in contractors if c.get('is_master'))
    multi_cert = sum(1 for c in contractors if len(c.get('certification_areas', [])) > 1)

    print(f"\n📊 EXTRACTION SUMMARY")
    print(f"   Total Contractors: {total}")
    print(f"   With Phone: {with_phone} ({with_phone*100//total}%)")
    print(f"   With Email: {with_email} ({with_email*100//total}%)")
    print(f"   With Website: {with_website} ({with_website*100//total}%)")
    print(f"   MASTER Tier: {masters} ({masters*100//total}%)")
    print(f"   Multi-Certification: {multi_cert}")

    # Save JSON
    json_path = output_dir / f"schneider_ecoxperts_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump({
            "extraction_date": datetime.now().isoformat(),
            "total_contractors": total,
            "with_phone": with_phone,
            "with_email": with_email,
            "with_website": with_website,
            "master_tier_count": masters,
            "multi_certification_count": multi_cert,
            "contractors": contractors
        }, f, indent=2)
    print(f"\n💾 Saved JSON: {json_path}")

    # Save CSV
    csv_path = output_dir / f"schneider_ecoxperts_{timestamp}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'phone', 'email', 'website', 'city',
            'is_master', 'certification_count', 'certifications',
            'certification_areas', 'account_id', 'detail_url'
        ])
        writer.writeheader()
        for c in contractors:
            writer.writerow({
                'name': c.get('name', ''),
                'phone': c.get('phone', ''),
                'email': c.get('email', ''),
                'website': c.get('website', ''),
                'city': c.get('city', ''),
                'is_master': c.get('is_master', False),
                'certification_count': len(c.get('certifications', [])),
                'certifications': '|'.join(c.get('certifications', [])),
                'certification_areas': '|'.join(c.get('certification_areas', [])),
                'account_id': c.get('account_id', ''),
                'detail_url': c.get('detail_url', '')
            })
    print(f"💾 Saved CSV: {csv_path}")

    return json_path, csv_path


async def main():
    """Main entry point."""
    output_dir = Path("/Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/output/oem_data/schneider")
    output_dir.mkdir(parents=True, exist_ok=True)

    contractors = await scrape_all_certifications()

    if contractors:
        save_results(contractors, output_dir)
        print("\n✅ Schneider Electric EcoXpert scrape complete!")
    else:
        print("\n❌ No contractors extracted")


if __name__ == "__main__":
    asyncio.run(main())
