#!/usr/bin/env python3
"""
Explore County-Level AHJ (Authority Having Jurisdiction) Contractor Licensing Portals

Target: Top 10 wealthiest counties in NJ/NY
Goal: Find which have online searchable contractor databases for HVAC/Plumbing/Electrical
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "county_ahj_research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Wealthy counties with known/suspected contractor licensing portals
AHJ_PORTALS = {
    # New York Counties
    "Westchester_NY": {
        "url": "https://consumer.westchestergov.com/trade-licenses-search",
        "state": "NY",
        "median_income": "$110K",
        "notes": "Known trade license search portal"
    },
    "Nassau_NY": {
        "url": "https://www.nassaucountyny.gov/1563/Licensing-Registrations",
        "state": "NY",
        "median_income": "$130K",
        "notes": "Long Island - highest income NY county outside NYC"
    },
    "Suffolk_NY": {
        "url": "https://suffolkcountyny.gov/Departments/Consumer-Affairs",
        "state": "NY",
        "median_income": "$95K",
        "notes": "Long Island East"
    },
    "Rockland_NY": {
        "url": "https://www.rocklandgov.com/departments/consumer-protection/",
        "state": "NY",
        "median_income": "$98K",
        "notes": "North of NYC"
    },

    # New Jersey Counties
    "Bergen_NJ": {
        "url": "https://www.co.bergen.nj.us/consumer-affairs",
        "state": "NJ",
        "median_income": "$110K",
        "notes": "Most populous NJ county"
    },
    "Morris_NJ": {
        "url": "https://morriscountynj.gov/",
        "state": "NJ",
        "median_income": "$120K",
        "notes": "3rd wealthiest NJ county"
    },
    "Somerset_NJ": {
        "url": "https://www.co.somerset.nj.us/",
        "state": "NJ",
        "median_income": "$123K",
        "notes": "2nd wealthiest NJ county"
    },
    "Hunterdon_NJ": {
        "url": "https://www.co.hunterdon.nj.us/",
        "state": "NJ",
        "median_income": "$126K",
        "notes": "Wealthiest NJ county"
    },
    "Monmouth_NJ": {
        "url": "https://www.co.monmouth.nj.us/",
        "state": "NJ",
        "median_income": "$106K",
        "notes": "Jersey Shore wealthy suburbs"
    },
    "Middlesex_NJ": {
        "url": "https://www.middlesexcountynj.gov/",
        "state": "NJ",
        "median_income": "$95K",
        "notes": "High population, Central NJ"
    },
}


async def explore_single_ahj(browser, county_name, portal_info):
    """Explore a single AHJ portal to find contractor licensing database"""

    print(f"\n{'='*60}")
    print(f"{county_name} ({portal_info['state']})")
    print(f"Median Income: {portal_info['median_income']}")
    print(f"URL: {portal_info['url']}")
    print('='*60)

    page = await browser.new_page()
    result = {
        "county": county_name,
        "state": portal_info["state"],
        "url": portal_info["url"],
        "median_income": portal_info["median_income"],
        "has_license_search": False,
        "license_types_found": [],
        "search_type": None,
        "notes": ""
    }

    try:
        # Navigate
        await page.goto(portal_info["url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Take screenshot
        screenshot_path = OUTPUT_DIR / f"{county_name}_portal.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"   ✅ Screenshot saved")

        # Look for contractor/license related links
        license_links = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                const keywords = ['license', 'contractor', 'plumb', 'electric', 'hvac',
                                  'trade', 'permit', 'register', 'consumer', 'business'];
                const found = [];

                for (let link of links) {
                    const text = link.textContent.toLowerCase().trim();
                    const href = link.href || '';

                    if (keywords.some(kw => text.includes(kw) || href.toLowerCase().includes(kw))) {
                        found.push({
                            text: link.textContent.trim().slice(0, 100),
                            href: href
                        });
                    }
                }

                return found.slice(0, 20);  // First 20 relevant links
            }
        """)

        if license_links:
            print(f"   Found {len(license_links)} relevant links:")
            for link in license_links[:10]:
                print(f"      - {link['text'][:50]}")
                if 'search' in link['text'].lower() or 'lookup' in link['text'].lower():
                    result["has_license_search"] = True
                    result["search_type"] = "likely searchable"

            result["license_types_found"] = [l['text'][:50] for l in license_links]
        else:
            print(f"   ⚠️  No contractor/license links found on main page")
            result["notes"] = "No contractor links on main page - may need deeper navigation"

        # Look for search forms
        forms = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input[type="text"], input[type="search"], select');
                return inputs.length;
            }
        """)

        if forms > 0:
            print(f"   Found {forms} search/form elements")
            result["search_type"] = f"{forms} form elements found"

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["notes"] = f"Error: {str(e)}"
    finally:
        await page.close()

    return result


async def main():
    print("\n" + "="*80)
    print("COUNTY AHJ CONTRACTOR LICENSING PORTAL RESEARCH")
    print("="*80)
    print(f"\nExploring {len(AHJ_PORTALS)} wealthy county portals...")
    print("Goal: Find AHJs with online searchable HVAC/Plumbing/Electrical databases")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for county_name, portal_info in AHJ_PORTALS.items():
            result = await explore_single_ahj(browser, county_name, portal_info)
            results.append(result)
            await asyncio.sleep(2)  # Be nice to servers

        await browser.close()

    # Save results
    with open(OUTPUT_DIR / "ahj_research_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Summary
    print("\n" + "="*80)
    print("RESEARCH SUMMARY")
    print("="*80)

    has_search = [r for r in results if r["has_license_search"]]
    print(f"\nCounties with likely searchable databases: {len(has_search)}")
    for r in has_search:
        print(f"   ✅ {r['county']} ({r['state']})")

    no_search = [r for r in results if not r["has_license_search"]]
    print(f"\nCounties needing deeper research: {len(no_search)}")
    for r in no_search:
        print(f"   ❓ {r['county']} ({r['state']})")

    print(f"\n📁 Results saved to: {OUTPUT_DIR}/")
    print("📷 Screenshots saved for manual inspection")


if __name__ == "__main__":
    asyncio.run(main())
