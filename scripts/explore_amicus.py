#!/usr/bin/env python3
"""
explore_amicus.py - Explore Amicus Solar member page structure

This script navigates to the Amicus Solar member page and extracts
the HTML structure to understand how to scrape member data.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sources" / "amicus"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def explore_amicus_solar():
    """Explore Amicus Solar member page"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🔍 Navigating to Amicus Solar members page...")
        await page.goto("https://www.amicussolar.com/our-member-owners/", wait_until="networkidle")
        await page.wait_for_timeout(3000)  # Wait for dynamic content

        # Take screenshot
        screenshot_path = OUTPUT_DIR / "amicus_solar_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Screenshot saved to: {screenshot_path}")

        # Get page title
        title = await page.title()
        print(f"📄 Page title: {title}")

        # Try to find member containers - common patterns
        selectors_to_try = [
            ".member", ".members", ".member-card", ".member-item",
            ".team-member", ".person", ".company", ".partner",
            ".et_pb_text", ".et_pb_blurb", ".et_pb_module",
            "[class*='member']", "[class*='partner']", "[class*='company']",
            "article", ".card", ".item"
        ]

        print("\n🔎 Searching for member containers...")
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 3:  # Looking for repeated elements
                    print(f"   Found {len(elements)} elements with selector: {selector}")

                    # Get HTML of first element
                    first_html = await elements[0].inner_html()
                    if len(first_html) > 50:  # Has meaningful content
                        print(f"   First element preview: {first_html[:200]}...")
            except Exception as e:
                pass

        # Get all images (often company logos)
        print("\n🖼️ Looking for company logos/images...")
        images = await page.query_selector_all("img")
        logo_images = []
        for img in images:
            src = await img.get_attribute("src") or ""
            alt = await img.get_attribute("alt") or ""
            if "logo" in src.lower() or "member" in src.lower() or "partner" in src.lower():
                logo_images.append({"src": src, "alt": alt})
            elif alt and len(alt) > 5 and "icon" not in alt.lower():
                logo_images.append({"src": src, "alt": alt})

        print(f"   Found {len(logo_images)} potential company logos")
        for img in logo_images[:10]:
            print(f"   - {img['alt'][:50]}: {img['src'][:80]}...")

        # Get all links that might be company websites
        print("\n🔗 Looking for external links (company websites)...")
        links = await page.query_selector_all("a[href]")
        external_links = []
        for link in links:
            href = await link.get_attribute("href") or ""
            text = await link.inner_text()
            if href.startswith("http") and "amicussolar.com" not in href:
                external_links.append({"href": href, "text": text.strip()[:50]})

        print(f"   Found {len(external_links)} external links")
        for link in external_links[:15]:
            print(f"   - {link['text']}: {link['href']}")

        # Save full HTML for analysis
        html_path = OUTPUT_DIR / "amicus_solar_full.html"
        full_html = await page.content()
        html_path.write_text(full_html)
        print(f"\n💾 Full HTML saved to: {html_path}")

        # Extract visible text content
        print("\n📝 Extracting visible text (looking for company names)...")
        body_text = await page.inner_text("body")

        # Save text content
        text_path = OUTPUT_DIR / "amicus_solar_text.txt"
        text_path.write_text(body_text)
        print(f"💾 Text content saved to: {text_path}")

        # Print first 2000 chars of body text
        print("\n--- Page Text Preview (first 2000 chars) ---")
        print(body_text[:2000])

        await browser.close()


async def explore_amicus_om():
    """Explore Amicus O&M member page"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("\n" + "=" * 60)
        print("🔍 Navigating to Amicus O&M members page...")
        await page.goto("https://www.amicusom.com/our-member-owners/", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Take screenshot
        screenshot_path = OUTPUT_DIR / "amicus_om_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Screenshot saved to: {screenshot_path}")

        # Get page title
        title = await page.title()
        print(f"📄 Page title: {title}")

        # Get external links
        print("\n🔗 Looking for external links (company websites)...")
        links = await page.query_selector_all("a[href]")
        external_links = []
        for link in links:
            href = await link.get_attribute("href") or ""
            text = await link.inner_text()
            if href.startswith("http") and "amicusom.com" not in href and "amicussolar.com" not in href:
                external_links.append({"href": href, "text": text.strip()[:50]})

        print(f"   Found {len(external_links)} external links")
        for link in external_links[:15]:
            print(f"   - {link['text']}: {link['href']}")

        # Save full HTML
        html_path = OUTPUT_DIR / "amicus_om_full.html"
        full_html = await page.content()
        html_path.write_text(full_html)
        print(f"\n💾 Full HTML saved to: {html_path}")

        # Extract text
        body_text = await page.inner_text("body")
        text_path = OUTPUT_DIR / "amicus_om_text.txt"
        text_path.write_text(body_text)
        print(f"💾 Text content saved to: {text_path}")

        print("\n--- Page Text Preview (first 2000 chars) ---")
        print(body_text[:2000])

        await browser.close()


async def main():
    await explore_amicus_solar()
    await explore_amicus_om()
    print("\n✅ Exploration complete!")


if __name__ == "__main__":
    asyncio.run(main())
