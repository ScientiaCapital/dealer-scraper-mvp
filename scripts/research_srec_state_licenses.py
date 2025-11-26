#!/usr/bin/env python3
"""
Research SREC State Licensing Databases

Target: MEP+Energy contractors for Coperniq ICP
- Electrical (solar, battery, EV charging)
- Plumbing (geothermal, solar thermal)
- HVAC/Mechanical (heat pumps, VRF)
- Low Voltage (fire alarm, security, data)
- Fire & Safety (sprinklers, suppression)
- General Contractors (resimercial)

Priority States (SREC + high solar adoption):
1. CA - CSLB (California Contractor State License Board)
2. TX - TDLR (Texas Department of Licensing & Regulation)
3. FL - DBPR (Florida Dept Business & Professional Regulation)
4. MA - DPL (Division of Professional Licensure)
5. PA - L&I (Labor & Industry)
6. NJ - DCA + County-level (discovered in prior research)
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "srec_research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# State licensing databases to research
STATE_DATABASES = {
    "CA": {
        "name": "California CSLB",
        "url": "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx",
        "api_url": "https://www.cslb.ca.gov/onlineservices/checklicenseii/checklicense.aspx",
        "notes": "GOLD STANDARD - Searchable by license type, city, ZIP",
        "license_types": [
            "C-10 Electrical",
            "C-20 HVAC",
            "C-36 Plumbing",
            "C-46 Solar",
            "B General Building",
            "C-7 Low Voltage",
            "C-16 Fire Protection",
        ]
    },
    "TX": {
        "name": "Texas TDLR",
        "url": "https://www.tdlr.texas.gov/LicenseSearch/",
        "notes": "Electrical, HVAC, Plumbing have separate boards",
        "license_types": [
            "Electrician",
            "HVAC",
            "Plumber",
            "Fire Alarm",
            "Fire Sprinkler",
        ]
    },
    "FL": {
        "name": "Florida DBPR",
        "url": "https://www.myfloridalicense.com/wl11.asp",
        "notes": "Unified portal, good search",
        "license_types": [
            "Electrical Contractor",
            "Plumbing Contractor",
            "Mechanical Contractor",
            "General Contractor",
            "Roofing Contractor",
            "Solar Contractor",
            "Fire Alarm System Contractor",
        ]
    },
    "MA": {
        "name": "Massachusetts DPL",
        "url": "https://elicensing.state.ma.us/CitizenAccess/",
        "notes": "E-licensing portal",
        "license_types": [
            "Electrician",
            "Plumber/Gas Fitter",
            "Sheet Metal Worker",
            "Fire Alarm Technician",
        ]
    },
    "PA": {
        "name": "Pennsylvania L&I",
        "url": "https://www.pals.pa.gov/",
        "notes": "PALS licensing system",
        "license_types": [
            "Home Improvement Contractor",
            "Electrician",
            "Plumber",
        ]
    },
    "NJ": {
        "name": "New Jersey DCA",
        "url": "https://newjersey.mylicense.com/verification/",
        "notes": "State has limited MEP - most is county-level",
        "license_types": [
            "Electrical Contractor",
            "Home Improvement Contractor",
            "Fire Alarm/Suppression",
        ]
    },
    "AZ": {
        "name": "Arizona ROC",
        "url": "https://roc.az.gov/contractor-search",
        "notes": "Registrar of Contractors - searchable",
        "license_types": [
            "C-11 Electrical",
            "C-37 Plumbing",
            "C-39 HVAC",
            "B-1 General Commercial",
            "C-77 Low Voltage",
        ]
    },
    "NV": {
        "name": "Nevada NSCB",
        "url": "https://app.nvcontractorsboard.com/Clients/NVSCB/Public/ContractorLicenseSearch.aspx",
        "notes": "Searchable database",
        "license_types": [
            "C-2 Electrical",
            "C-1 Plumbing/Heating",
            "C-21 Refrigeration/AC",
            "B General Building",
        ]
    },
}


async def explore_state_database(browser, state_code, state_info):
    """Explore a state licensing database"""

    print(f"\n{'='*60}")
    print(f"{state_code}: {state_info['name']}")
    print(f"URL: {state_info['url']}")
    print(f"Notes: {state_info['notes']}")
    print('='*60)

    result = {
        "state": state_code,
        "name": state_info["name"],
        "url": state_info["url"],
        "notes": state_info["notes"],
        "accessible": False,
        "has_search": False,
        "search_fields": [],
        "license_types": state_info.get("license_types", []),
        "sample_data": [],
        "error": None,
    }

    page = await browser.new_page()

    try:
        await page.goto(state_info["url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        result["accessible"] = True

        # Take screenshot
        screenshot_path = OUTPUT_DIR / f"{state_code}_portal.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"   ✅ Screenshot saved")

        # Look for search forms
        forms = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input[type="text"], input[type="search"], select');
                const searchFields = [];

                for (let input of inputs) {
                    const name = input.name || input.id || '';
                    const placeholder = input.placeholder || '';
                    const label = input.previousElementSibling?.textContent || '';

                    if (name || placeholder || label) {
                        searchFields.push({
                            type: input.tagName,
                            name: name,
                            placeholder: placeholder,
                            label: label.trim().slice(0, 50)
                        });
                    }
                }

                return searchFields.slice(0, 15);
            }
        """)

        if forms:
            result["has_search"] = True
            result["search_fields"] = forms
            print(f"   ✅ Found {len(forms)} search fields:")
            for f in forms[:5]:
                print(f"      - {f['name'] or f['label'] or f['placeholder']}")

        # Look for license type dropdowns
        license_links = await page.evaluate("""
            () => {
                const text = document.body.innerText.toLowerCase();
                const keywords = ['electrical', 'plumbing', 'hvac', 'mechanical', 'solar',
                                  'general contractor', 'fire', 'low voltage', 'c-10', 'c-20'];
                const found = keywords.filter(kw => text.includes(kw));
                return found;
            }
        """)

        if license_links:
            print(f"   ✅ License keywords found: {license_links[:5]}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["error"] = str(e)
    finally:
        await page.close()

    return result


async def main():
    print("\n" + "="*80)
    print("SREC STATE LICENSE DATABASE RESEARCH")
    print("="*80)
    print(f"\nResearching {len(STATE_DATABASES)} state licensing portals...")
    print("Focus: MEP+Energy, Low Voltage, Fire & Safety")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for state_code, state_info in STATE_DATABASES.items():
            result = await explore_state_database(browser, state_code, state_info)
            results.append(result)
            await asyncio.sleep(2)

        await browser.close()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = OUTPUT_DIR / f"srec_database_research_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Summary
    print(f"\n{'='*80}")
    print("RESEARCH SUMMARY")
    print('='*80)

    accessible = [r for r in results if r["accessible"]]
    has_search = [r for r in results if r["has_search"]]

    print(f"\nAccessible portals: {len(accessible)}/{len(results)}")
    print(f"With search functionality: {len(has_search)}/{len(results)}")

    print("\n📋 RECOMMENDED PRIORITY ORDER:")
    priority = ["CA", "FL", "TX", "AZ", "NV", "MA", "PA", "NJ"]
    for i, state in enumerate(priority, 1):
        r = next((x for x in results if x["state"] == state), None)
        if r:
            status = "✅" if r["has_search"] else "⚠️"
            print(f"   {i}. {state}: {r['name']} {status}")

    print(f"\n📁 Results saved to: {OUTPUT_DIR}/")

    return results


if __name__ == "__main__":
    asyncio.run(main())
