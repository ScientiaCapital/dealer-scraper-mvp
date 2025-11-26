#!/usr/bin/env python3
"""
Research ALL SREC State Licensing Databases

Complete list of SREC (Solar Renewable Energy Credit) states plus
high solar adoption states for MEP+Energy contractor prospecting.

SREC States (Active Markets):
1. DC - District of Columbia (~$400/SREC - HIGHEST)
2. NJ - New Jersey (~$200/SREC - established market)
3. MA - Massachusetts (~$250/SREC - SREC II + SMART)
4. PA - Pennsylvania (~$35/SREC)
5. MD - Maryland (~$55/SREC)
6. DE - Delaware (~$50/SREC)
7. OH - Ohio (~$15/SREC - regional hub)
8. VA - Virginia (~$45/SREC - new market)
9. IL - Illinois (variable)

High Solar Adoption (non-SREC but key markets):
- CA - California (SGIP + NEM 3.0, largest solar market)
- TX - Texas (ERCOT arbitrage, fastest growing)
- FL - Florida (net metering + tax exemptions)
- AZ - Arizona (high solar irradiance)
- NV - Nevada (high solar irradiance)
- NY - New York (NYSERDA programs)
- NC - North Carolina (can sell into other SREC markets)

Target: MEP+Energy contractors for Coperniq ICP
- Electrical (solar, battery, EV charging)
- Plumbing (geothermal, solar thermal)
- HVAC/Mechanical (heat pumps, VRF)
- Low Voltage (fire alarm, security, data)
- Fire & Safety (sprinklers, suppression)
- General Contractors (resimercial)
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "state_licenses" / "srec_research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ALL SREC states + high solar adoption states
ALL_STATE_DATABASES = {
    # ====== SREC STATES (Active Markets) ======
    "DC": {
        "name": "District of Columbia",
        "category": "SREC",
        "srec_price": "$400+",
        "urls": [
            "https://dcra.dc.gov/page/licensing-and-registration",
            "https://eservices.dcra.dc.gov/BBLV/Default.aspx",
        ],
        "notes": "DCRA handles contractor licensing. Highest SREC prices in US!",
        "license_types": ["Electrical", "Plumbing", "HVAC", "General Contractor"],
    },
    "NJ": {
        "name": "New Jersey DCA",
        "category": "SREC",
        "srec_price": "$200+",
        "urls": [
            "https://newjersey.mylicense.com/verification/",
        ],
        "notes": "State level limited - MEP is county-level. Already researched.",
        "license_types": ["Electrical Contractor", "Home Improvement"],
    },
    "MA": {
        "name": "Massachusetts DPL",
        "category": "SREC",
        "srec_price": "$250+",
        "urls": [
            "https://www.mass.gov/orgs/division-of-professional-licensure",
            "https://elicensing.state.ma.us/CitizenAccess/",
        ],
        "notes": "SREC II + SMART program. E-licensing portal.",
        "license_types": ["Electrician", "Plumber/Gas Fitter", "Sheet Metal", "Fire Alarm"],
    },
    "PA": {
        "name": "Pennsylvania L&I PALS",
        "category": "SREC",
        "srec_price": "$35",
        "urls": [
            "https://www.pals.pa.gov/",
        ],
        "notes": "PALS licensing system. Systems up to 3MW eligible for SRECs.",
        "license_types": ["Home Improvement Contractor", "Electrician", "Plumber"],
    },
    "MD": {
        "name": "Maryland DLLR",
        "category": "SREC",
        "srec_price": "$55",
        "urls": [
            "https://www.dllr.state.md.us/license/",
            "https://www.dllr.state.md.us/license/mhic/",
            "https://www.dllr.state.md.us/cgi-bin/ElectronicLicensing/OP_Search/OP_search.cgi",
        ],
        "notes": "MHIC (Home Improvement Commission) + separate trade boards.",
        "license_types": ["Home Improvement", "Electrician", "HVACR", "Plumber", "Master Gas Fitter"],
    },
    "DE": {
        "name": "Delaware DPRP",
        "category": "SREC",
        "srec_price": "$50",
        "urls": [
            "https://dpr.delaware.gov/boards/",
            "https://delpros.delaware.gov/OH_HomePage",
        ],
        "notes": "Systems up to 25MW eligible for SRECs.",
        "license_types": ["Electrical", "Plumbing", "HVAC", "Fire Protection"],
    },
    "OH": {
        "name": "Ohio OCILB",
        "category": "SREC",
        "srec_price": "$15",
        "urls": [
            "https://www.com.ohio.gov/dico/",
            "https://elicense.ohio.gov/oh_verifylicense",
        ],
        "notes": "Regional SREC hub - WV, IN, KY, MI can sell here.",
        "license_types": ["Electrical Contractor", "HVAC", "Plumbing", "Fire Protection"],
    },
    "VA": {
        "name": "Virginia DPOR",
        "category": "SREC",
        "srec_price": "$45",
        "urls": [
            "https://www.dpor.virginia.gov/",
            "https://www.dpor.virginia.gov/LicenseLookup",
        ],
        "notes": "New SREC market (Clean Economy Act). License lookup available.",
        "license_types": ["Class A/B/C Contractor", "Electrical", "Plumbing", "HVAC", "Fire Sprinkler"],
    },
    "IL": {
        "name": "Illinois IDFPR",
        "category": "SREC",
        "srec_price": "Variable",
        "urls": [
            "https://online-dfpr.micropact.com/lookup/licenselookup.aspx",
            "https://www.idfpr.com/Profs/Info/ElecLicensing.asp",
        ],
        "notes": "Active SREC market. License lookup portal.",
        "license_types": ["Electrician", "Plumber", "Roofing"],
    },

    # ====== HIGH SOLAR ADOPTION STATES (non-SREC) ======
    "CA": {
        "name": "California CSLB",
        "category": "High Solar",
        "srec_price": "N/A (SGIP)",
        "urls": [
            "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx",
        ],
        "notes": "GOLD STANDARD - Largest solar market. SGIP + NEM 3.0.",
        "license_types": ["C-10 Electrical", "C-20 HVAC", "C-36 Plumbing", "C-46 Solar", "C-7 Low Voltage", "C-16 Fire Protection", "B General"],
    },
    "TX": {
        "name": "Texas TDLR",
        "category": "High Solar",
        "srec_price": "N/A (ERCOT)",
        "urls": [
            "https://www.tdlr.texas.gov/LicenseSearch/",
        ],
        "notes": "Fastest growing solar market. ZIP + License Type search. Has download option!",
        "license_types": ["Electrician", "HVAC", "Plumber", "Fire Alarm", "Fire Sprinkler"],
    },
    "FL": {
        "name": "Florida DBPR",
        "category": "High Solar",
        "srec_price": "N/A (Net Metering)",
        "urls": [
            "https://www.myfloridalicense.com/wl11.asp",
        ],
        "notes": "Unified portal. Net metering + property tax exemptions.",
        "license_types": ["Electrical", "Plumbing", "Mechanical", "General", "Roofing", "Solar", "Fire Alarm"],
    },
    "AZ": {
        "name": "Arizona ROC",
        "category": "High Solar",
        "srec_price": "N/A",
        "urls": [
            "https://roc.az.gov/contractor-search",
        ],
        "notes": "High solar irradiance. Registrar of Contractors searchable.",
        "license_types": ["C-11 Electrical", "C-37 Plumbing", "C-39 HVAC", "B-1 General", "C-77 Low Voltage"],
    },
    "NV": {
        "name": "Nevada NSCB",
        "category": "High Solar",
        "srec_price": "N/A",
        "urls": [
            "https://www.nvcontractorsboard.com/",
            "https://app.nvcontractorsboard.com/",
        ],
        "notes": "High solar irradiance. Searchable database.",
        "license_types": ["C-2 Electrical", "C-1 Plumbing/Heating", "C-21 Refrigeration/AC", "B General"],
    },
    "NY": {
        "name": "New York State (NYC DOB + Counties)",
        "category": "High Solar",
        "srec_price": "N/A (NYSERDA)",
        "urls": [
            "https://a810-bisweb.nyc.gov/bisweb/LicenseTypeServlet",
        ],
        "notes": "NYC DOB already scraped! NYSERDA solar programs.",
        "license_types": ["A Electrical", "P Master Plumber", "O Oil Burner", "G General", "F Fire Suppression"],
    },
    "NC": {
        "name": "North Carolina",
        "category": "High Solar",
        "srec_price": "Can sell to other markets",
        "urls": [
            "https://www.nclbgc.org/",
            "https://www.ncbeec.org/",
        ],
        "notes": "State licensing board + Electrical Board. Can sell SRECs to other markets.",
        "license_types": ["General Contractor", "Electrical", "Plumbing", "HVAC", "Fire Sprinkler"],
    },

    # ====== SELL-INTO-OHIO STATES ======
    "WV": {
        "name": "West Virginia",
        "category": "Sell into OH",
        "srec_price": "Sell to OH market",
        "urls": [
            "https://labor.wv.gov/licensing/Pages/default.aspx",
        ],
        "notes": "Can sell SRECs into Ohio market.",
        "license_types": ["Electrical", "Plumbing", "HVAC", "Fire Protection"],
    },
    "IN": {
        "name": "Indiana",
        "category": "Sell into OH",
        "srec_price": "Sell to OH market",
        "urls": [
            "https://www.in.gov/pla/professions/",
        ],
        "notes": "Can sell SRECs into Ohio market.",
        "license_types": ["Electrician", "Plumber"],
    },
    "KY": {
        "name": "Kentucky",
        "category": "Sell into OH",
        "srec_price": "Sell to OH market",
        "urls": [
            "https://dhbc.ky.gov/",
        ],
        "notes": "Can sell SRECs into Ohio market.",
        "license_types": ["Electrical", "Plumbing", "HVAC"],
    },
    "MI": {
        "name": "Michigan",
        "category": "Sell into OH",
        "srec_price": "Sell to OH market",
        "urls": [
            "https://www.michigan.gov/lara/bureau-list/bcc",
        ],
        "notes": "Can sell SRECs into Ohio market.",
        "license_types": ["Electrical", "Plumbing", "Mechanical"],
    },
}


async def explore_state_database(browser, state_code, state_info):
    """Explore a state licensing database"""

    print(f"\n{'='*60}")
    print(f"{state_code}: {state_info['name']}")
    print(f"Category: {state_info['category']} | SREC Price: {state_info['srec_price']}")
    print(f"Notes: {state_info['notes']}")
    print('='*60)

    result = {
        "state": state_code,
        "name": state_info["name"],
        "category": state_info["category"],
        "srec_price": state_info["srec_price"],
        "notes": state_info["notes"],
        "urls": state_info["urls"],
        "license_types": state_info.get("license_types", []),
        "accessible": False,
        "has_search": False,
        "search_fields": [],
        "screenshots": [],
        "error": None,
    }

    page = await browser.new_page()

    for i, url in enumerate(state_info["urls"]):
        print(f"   URL {i+1}: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            result["accessible"] = True

            # Take screenshot
            safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_').replace(':', '_')[:50]
            screenshot_path = OUTPUT_DIR / f"{state_code}_{i+1}_{safe_name}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            result["screenshots"].append(str(screenshot_path))
            print(f"      ✅ Screenshot saved")

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
                result["search_fields"].extend(forms)
                print(f"      ✅ Found {len(forms)} search fields")

            # Look for license type keywords
            keywords_found = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    const keywords = ['electrical', 'plumbing', 'hvac', 'mechanical', 'solar',
                                      'general contractor', 'fire', 'low voltage', 'license lookup',
                                      'search', 'verify', 'contractor'];
                    return keywords.filter(kw => text.includes(kw));
                }
            """)

            if keywords_found:
                print(f"      ✅ Keywords: {keywords_found[:5]}")

        except Exception as e:
            print(f"      ❌ Error: {str(e)[:100]}")
            if not result["error"]:
                result["error"] = str(e)[:200]

    await page.close()
    return result


async def main():
    print("\n" + "="*80)
    print("ALL SREC + HIGH SOLAR STATE LICENSE DATABASE RESEARCH")
    print("="*80)

    # Count by category
    srec_count = len([s for s in ALL_STATE_DATABASES.values() if s["category"] == "SREC"])
    high_solar_count = len([s for s in ALL_STATE_DATABASES.values() if s["category"] == "High Solar"])
    sell_into_count = len([s for s in ALL_STATE_DATABASES.values() if s["category"] == "Sell into OH"])

    print(f"\nTotal States: {len(ALL_STATE_DATABASES)}")
    print(f"  SREC States: {srec_count}")
    print(f"  High Solar States: {high_solar_count}")
    print(f"  Sell-into-OH States: {sell_into_count}")
    print("\nFocus: MEP+Energy, Low Voltage, Fire & Safety")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        for state_code, state_info in ALL_STATE_DATABASES.items():
            result = await explore_state_database(browser, state_code, state_info)
            results.append(result)
            await asyncio.sleep(1)

        await browser.close()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = OUTPUT_DIR / f"all_srec_states_research_{timestamp}.json"
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

    print("\n📋 BY CATEGORY:")
    for category in ["SREC", "High Solar", "Sell into OH"]:
        cat_results = [r for r in results if r["category"] == category]
        accessible_cat = [r for r in cat_results if r["accessible"]]
        search_cat = [r for r in cat_results if r["has_search"]]
        print(f"\n   {category}:")
        for r in cat_results:
            status = "✅" if r["has_search"] else ("⚠️" if r["accessible"] else "❌")
            print(f"      {r['state']}: {r['name']} {status}")

    print("\n🎯 RECOMMENDED SCRAPER PRIORITY:")
    priority_states = [
        ("CA", "GOLD STANDARD - ZIP search"),
        ("TX", "ZIP search + Downloads"),
        ("FL", "License Type search"),
        ("MD", "MHIC searchable"),
        ("VA", "License lookup"),
        ("OH", "Regional SREC hub"),
        ("IL", "License lookup"),
        ("DC", "Highest SREC prices"),
    ]
    for i, (state, reason) in enumerate(priority_states, 1):
        print(f"   {i}. {state}: {reason}")

    print(f"\n📁 Results saved to: {OUTPUT_DIR}/")

    return results


if __name__ == "__main__":
    asyncio.run(main())
