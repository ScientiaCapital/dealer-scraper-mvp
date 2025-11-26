#!/usr/bin/env python3
"""
amicus_scraper.py - Scrape Amicus Solar and Amicus O&M member directories

Data Sources:
- Amicus Solar: https://www.amicussolar.com/our-member-owners/
- Amicus O&M: https://www.amicusom.com/our-member-owners/

Both cooperatives represent high-quality, values-driven solar companies.
These are excellent ICP targets for Coperniq - established companies with
strong reputations who value brand-agnostic solutions.

Output:
- JSON file with all members
- Saved to output/sources/amicus/

Author: Claude + Tim Kipper
Date: 2025-11-26
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sources" / "amicus"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# URLs
AMICUS_SOLAR_URL = "https://www.amicussolar.com/our-member-owners/"
AMICUS_OM_URL = "https://www.amicusom.com/our-member-owners/"


def normalize_domain(url: str) -> str:
    """Extract clean domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def clean_company_name(name: str) -> str:
    """Clean and normalize company name"""
    name = name.strip()
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name)
    return name


async def scrape_amicus_solar() -> list[dict]:
    """Scrape Amicus Solar member directory"""
    members = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🌞 Scraping Amicus Solar members...")
        await page.goto(AMICUS_SOLAR_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)  # Extra time for dynamic content

        # Get all external links (company websites)
        links = await page.query_selector_all("a[href]")

        for link in links:
            try:
                href = await link.get_attribute("href") or ""
                text = await link.inner_text()
                text = clean_company_name(text)

                # Filter for external company links
                if (href.startswith("http") and
                    "amicussolar.com" not in href and
                    "amicusom.com" not in href and
                    "facebook.com" not in href and
                    "twitter.com" not in href and
                    "linkedin.com" not in href and
                    "instagram.com" not in href and
                    "youtube.com" not in href and
                    len(text) > 2):

                    domain = normalize_domain(href)

                    # Avoid duplicates
                    if not any(m["domain"] == domain for m in members):
                        members.append({
                            "company_name": text,
                            "website": href,
                            "domain": domain,
                            "source": "amicus_solar",
                            "cooperative": "Amicus Solar Cooperative",
                            "scraped_at": datetime.now().isoformat()
                        })

            except Exception as e:
                continue

        await browser.close()

    print(f"   ✅ Found {len(members)} Amicus Solar members")
    return members


async def scrape_amicus_om() -> list[dict]:
    """Scrape Amicus O&M member directory"""
    members = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🔧 Scraping Amicus O&M members...")

        try:
            # Use longer timeout and domcontentloaded instead of networkidle
            await page.goto(AMICUS_OM_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)  # Wait for JS to load

            # Get all external links (company websites)
            links = await page.query_selector_all("a[href]")

            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    text = await link.inner_text()
                    text = clean_company_name(text)

                    # Filter for external company links
                    if (href.startswith("http") and
                        "amicussolar.com" not in href and
                        "amicusom.com" not in href and
                        "facebook.com" not in href and
                        "twitter.com" not in href and
                        "linkedin.com" not in href and
                        "instagram.com" not in href and
                        "youtube.com" not in href and
                        len(text) > 2):

                        domain = normalize_domain(href)

                        # Avoid duplicates
                        if not any(m["domain"] == domain for m in members):
                            members.append({
                                "company_name": text,
                                "website": href,
                                "domain": domain,
                                "source": "amicus_om",
                                "cooperative": "Amicus O&M Cooperative",
                                "scraped_at": datetime.now().isoformat()
                            })

                except Exception as e:
                    continue

            print(f"   ✅ Found {len(members)} Amicus O&M members")

        except Exception as e:
            print(f"   ⚠️ Amicus O&M site issue: {e}")
            print("   (Site may be slow or temporarily unavailable)")

        await browser.close()

    return members


async def scrape_all_amicus() -> dict:
    """Scrape both Amicus cooperatives and combine results"""

    # Scrape both sources
    solar_members = await scrape_amicus_solar()
    om_members = await scrape_amicus_om()

    # Combine and dedupe by domain
    all_members = []
    seen_domains = set()

    for member in solar_members + om_members:
        if member["domain"] not in seen_domains:
            # Check if company is in both cooperatives
            in_solar = any(m["domain"] == member["domain"] for m in solar_members)
            in_om = any(m["domain"] == member["domain"] for m in om_members)

            member["in_amicus_solar"] = in_solar
            member["in_amicus_om"] = in_om
            member["cooperative_count"] = sum([in_solar, in_om])

            all_members.append(member)
            seen_domains.add(member["domain"])

    # Sort by company name
    all_members.sort(key=lambda x: x["company_name"].lower())

    # Create summary
    result = {
        "metadata": {
            "scraped_at": datetime.now().isoformat(),
            "total_members": len(all_members),
            "amicus_solar_count": len(solar_members),
            "amicus_om_count": len(om_members),
            "overlap_count": sum(1 for m in all_members if m["cooperative_count"] == 2)
        },
        "members": all_members
    }

    return result


def save_results(data: dict):
    """Save scraping results to JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"amicus_members_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Saved to: {output_path}")
    return output_path


def print_summary(data: dict):
    """Print summary of scraped data"""
    meta = data["metadata"]
    members = data["members"]

    print("\n" + "=" * 60)
    print("📊 AMICUS SCRAPING SUMMARY")
    print("=" * 60)
    print(f"   Total unique members: {meta['total_members']}")
    print(f"   Amicus Solar members: {meta['amicus_solar_count']}")
    print(f"   Amicus O&M members:   {meta['amicus_om_count']}")
    print(f"   In both cooperatives: {meta['overlap_count']}")

    # Show first 10 companies
    print("\n📋 Sample companies:")
    for member in members[:10]:
        coop_flag = "🌞+🔧" if member["cooperative_count"] == 2 else ("🌞" if member["in_amicus_solar"] else "🔧")
        print(f"   {coop_flag} {member['company_name']}")
        print(f"      └─ {member['domain']}")

    if len(members) > 10:
        print(f"   ... and {len(members) - 10} more")

    print("=" * 60)


async def main():
    print("🚀 Starting Amicus cooperative scraper...")
    print("   Sources: amicussolar.com, amicusom.com")
    print()

    data = await scrape_all_amicus()
    output_path = save_results(data)
    print_summary(data)

    return data


if __name__ == "__main__":
    asyncio.run(main())
