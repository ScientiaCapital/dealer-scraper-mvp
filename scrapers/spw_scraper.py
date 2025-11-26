#!/usr/bin/env python3
"""
Solar Power World (SPW) Scraper - Comprehensive List + Profile Extraction

Two-phase scraping approach:
1. Phase A: Extract all companies from 11 SPW list pages (tables)
2. Phase B: Visit each company's profile page for enriched data

Usage:
    # Scrape master list only
    python3 scrapers/spw_scraper.py --list master

    # Scrape all 11 lists
    python3 scrapers/spw_scraper.py --all

    # Scrape profiles for companies already extracted
    python3 scrapers/spw_scraper.py --enrich-profiles

    # Full pipeline (lists + profiles)
    python3 scrapers/spw_scraper.py --full
"""

import asyncio
import json
import sqlite3
import re
import sys
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from urllib.parse import urljoin

# Logging setup - will be configured in main()
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Run: pip install playwright && playwright install chromium")

from database import PipelineDB, normalize_company_name


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.solarpowerworldonline.com"

# All 11 SPW lists to scrape
SPW_LISTS = {
    "master": "/2025-top-solar-contractors/",
    "commercial": "/2025-top-commercial-solar-contractors/",
    "residential": "/2025-top-residential-solar-contractors/",
    "epcs": "/2025-top-solar-epcs/",
    "developers": "/2025-top-solar-developers/",
    "installers": "/2025-top-solar-installers/",
    "storage": "/2025-top-solar-storage-installers/",
    "community": "/2025-top-community-solar-contractors/",
    "utility": "/2025-top-utility-solar-contractors/",
    "electrical_subs": "/2025-top-solar-electrical-subcontractors/",
    "installation_subs": "/2025-top-solar-installation-subcontractors/",
}

DB_PATH = Path(__file__).parent.parent / "output" / "master" / "pipeline.db"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sources" / "spw_2025"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SPWCompany:
    """Data extracted from SPW list pages."""
    company_name: str
    profile_url: str
    headquarters_state: str = ""
    list_name: str = ""
    rank_position: int = 0
    kw_installed: int = 0
    primary_service: str = ""
    primary_project: str = ""
    total_kw: int = 0
    year: int = 2024
    # Multi-source tracking: which SPW lists this company appears on
    source_lists: List[str] = field(default_factory=list)
    list_count: int = 0  # Number of lists (higher = more prominent company)


@dataclass
class SPWProfile:
    """Enriched data from SPW profile pages."""
    company_name: str
    profile_url: str
    city: str = ""
    state: str = ""
    website: str = ""
    year_founded: int = 0
    employee_count: int = 0
    kw_2024: int = 0
    cumulative_kw: int = 0
    description: str = ""
    markets_served: List[str] = field(default_factory=list)
    service_areas: List[str] = field(default_factory=list)
    primary_service: str = ""
    scraped_at: str = ""


# =============================================================================
# PHASE A: LIST EXTRACTION
# =============================================================================

class SPWListScraper:
    """Scrapes company data from SPW list/ranking pages."""

    def __init__(self, browser: Browser):
        self.browser = browser
        self.companies: List[SPWCompany] = []

    async def scrape_list_page(self, list_name: str, url_path: str) -> List[SPWCompany]:
        """
        Scrape a single SPW list page and extract all companies.

        SPW list pages contain HTML tables with company rankings.
        Table structure varies slightly by list type.
        """
        full_url = urljoin(BASE_URL, url_path)
        print(f"\n📋 Scraping {list_name}: {full_url}")

        page = await self.browser.new_page()
        companies = []

        try:
            # SPW pages are slow - use longer timeout and domcontentloaded
            print(f"   Loading page (60s timeout)...")
            await page.goto(full_url, timeout=60000, wait_until="domcontentloaded")
            print(f"   DOM loaded, waiting for tables...")

            # Wait for DataTables.js to initialize (SPW uses this for rendering)
            await asyncio.sleep(5)

            # Try to wait for the specific SPW table
            try:
                await page.wait_for_selector("table.posts-data-table", timeout=10000)
                print(f"   Found posts-data-table")
            except:
                print(f"   No posts-data-table, trying other selectors...")

            # Extract table data using JavaScript
            # SPW tables have class "posts-data-table" and use DataTables.js
            # Company links point to /suppliers/[company-slug]/
            table_data = await page.evaluate("""
                () => {
                    const companies = [];

                    // SPW uses posts-data-table class, but also try others
                    const tables = document.querySelectorAll('table.posts-data-table, table.tablepress, table');

                    console.log('Found tables:', tables.length);

                    for (const table of tables) {
                        const rows = table.querySelectorAll('tbody tr');

                        console.log('Table rows:', rows.length);

                        for (const row of rows) {
                            // Skip header rows
                            if (row.querySelector('th')) continue;

                            const cells = row.querySelectorAll('td');
                            if (cells.length < 2) continue;

                            // Look for company name link (SPW uses /suppliers/ path)
                            let companyName = '';
                            let profileUrl = '';

                            // Check all cells for company name link
                            for (const cell of cells) {
                                const link = cell.querySelector('a');
                                if (link && link.href && link.href.includes('/suppliers/')) {
                                    companyName = link.textContent.trim();
                                    profileUrl = link.href;
                                    break;
                                }
                            }

                            // If no supplier link, try any link
                            if (!companyName) {
                                for (const cell of cells) {
                                    const link = cell.querySelector('a');
                                    if (link && link.textContent.trim().length > 2) {
                                        companyName = link.textContent.trim();
                                        profileUrl = link.href || '';
                                        break;
                                    }
                                }
                            }

                            // If still no link found, try first cell text
                            if (!companyName && cells.length > 0) {
                                companyName = cells[0].textContent.trim();
                            }

                            if (companyName && companyName.length > 1) {
                                // Extract other data from cells
                                const rowData = {
                                    company_name: companyName,
                                    profile_url: profileUrl || '',
                                    cells: Array.from(cells).map(c => c.textContent.trim())
                                };
                                companies.push(rowData);
                            }
                        }
                    }

                    return companies;
                }
            """)

            print(f"   Found {len(table_data)} rows in table(s)")

            # Debug output (uncomment for troubleshooting)
            # if table_data and len(table_data) > 0:
            #     print(f"   DEBUG - First row cells: {table_data[0].get('cells', [])[:8]}")

            # Process extracted data
            # SPW DataTables.js combines header + value in cell text:
            # 'HQ StateNC' = header "HQ State" + value "NC"
            # 'C&I kW Installed in 2024116,909.53' = header + value

            # Known header prefixes to strip
            # Order matters - more specific patterns first!
            HEADER_PATTERNS = {
                'hq_state': ['HQ State', 'HQ'],
                'primary_service': ['Primary Service'],
                'primary_project': ['Primary Project Type', 'Primary Project'],
                'kw_installed': [
                    'C&I kW Installed in 2024',
                    'Residential kW Installed in 2024',
                    'Storage kW Installed in 2024',
                    'Utility kW Installed in 2024',
                    'Community kW Installed in 2024',
                    'kW Installed in 2024',  # Generic (master list uses this!)
                    'kW Installed'
                ],
                'total_kw': ['Total kW Installed in 2024', 'Total kW'],
                'overall_rank': ['Overall Rank'],
                'rank': ['C&I Rank', 'Residential Rank', 'Storage Rank', 'Utility Rank',
                         'Community Rank', 'EPC Rank', 'Developer Rank', 'Rank']
            }

            def strip_header(cell_text: str, patterns: list) -> str:
                """Strip known header prefix from cell text."""
                text = cell_text.strip()
                for pattern in patterns:
                    if text.startswith(pattern):
                        return text[len(pattern):].strip()
                return text

            def extract_kw(cell_text: str) -> int:
                """Extract kW value from cell text (handles commas and decimals).

                Handles DataTables.js format where header + value are concatenated:
                'kW Installed in 202410,106,563' → 10106563
                """
                text = cell_text
                # First strip any known header
                for header in HEADER_PATTERNS['kw_installed'] + HEADER_PATTERNS['total_kw']:
                    if text.startswith(header):
                        text = text[len(header):]
                        break

                # AGGRESSIVE: Strip everything up to and including year (2024, 2025)
                # Handles: "kW Installed in 202410,106,563" → "10,106,563"
                # Handles: "202410,106,563" → "10,106,563"
                text = re.sub(r'.*202[0-9]', '', text)

                # Extract numeric value
                kw_match = re.search(r'([\d,]+(?:\.\d+)?)', text)
                if kw_match:
                    try:
                        return int(float(kw_match.group(1).replace(',', '')))
                    except ValueError:
                        return 0
                return 0

            for idx, row in enumerate(table_data):
                cells = row.get('cells', [])

                company = SPWCompany(
                    company_name=row['company_name'],
                    profile_url=row['profile_url'],
                    list_name=list_name,
                    rank_position=idx + 1,
                )

                # Parse each cell with header stripping
                for cell in cells:
                    cell_text = cell.strip()

                    # Extract HQ State (2-letter code after header)
                    if 'HQ State' in cell_text or 'HQ' in cell_text:
                        state_val = strip_header(cell_text, HEADER_PATTERNS['hq_state'])
                        if len(state_val) == 2 and state_val.isupper():
                            company.headquarters_state = state_val

                    # Extract Primary Service
                    elif 'Primary Service' in cell_text:
                        company.primary_service = strip_header(cell_text, HEADER_PATTERNS['primary_service'])

                    # Extract Primary Project Type
                    elif 'Primary Project' in cell_text:
                        company.primary_project = strip_header(cell_text, HEADER_PATTERNS['primary_project'])

                    # Extract Category kW (not Total kW)
                    elif 'kW Installed' in cell_text and 'Total' not in cell_text:
                        company.kw_installed = extract_kw(cell_text)

                    # Extract Total kW
                    elif 'Total kW' in cell_text:
                        company.total_kw = extract_kw(cell_text)

                companies.append(company)

            print(f"   ✅ Extracted {len(companies)} companies from {list_name}")

        except Exception as e:
            print(f"   ❌ Error scraping {list_name}: {e}")
        finally:
            await page.close()

        self.companies.extend(companies)
        return companies

    async def scrape_all_lists(self) -> List[SPWCompany]:
        """Scrape all 11 SPW list pages."""
        print("\n" + "=" * 70)
        print("PHASE A: SPW LIST EXTRACTION")
        print("=" * 70)

        for list_name, url_path in SPW_LISTS.items():
            await self.scrape_list_page(list_name, url_path)
            await asyncio.sleep(1)  # Polite delay between requests

        # Deduplicate by company name (same company appears on multiple lists)
        # Track which lists each company appears on for multi-source analysis
        unique_companies = {}
        for company in self.companies:
            key = normalize_company_name(company.company_name)
            if key not in unique_companies:
                # First time seeing this company - initialize source_lists
                company.source_lists = [company.list_name]
                company.list_count = 1
                unique_companies[key] = company
            else:
                # Merge data from multiple lists
                existing = unique_companies[key]
                # Track all lists this company appears on
                if company.list_name not in existing.source_lists:
                    existing.source_lists.append(company.list_name)
                    existing.list_count = len(existing.source_lists)
                # Keep best data
                if company.profile_url and not existing.profile_url:
                    existing.profile_url = company.profile_url
                if company.kw_installed > existing.kw_installed:
                    existing.kw_installed = company.kw_installed
                if company.headquarters_state and not existing.headquarters_state:
                    existing.headquarters_state = company.headquarters_state
                if company.primary_service and not existing.primary_service:
                    existing.primary_service = company.primary_service

        deduped = list(unique_companies.values())

        # Sort by list_count (companies on more lists are more prominent)
        multi_list = [c for c in deduped if c.list_count > 1]
        print(f"\n📊 Total: {len(self.companies)} rows → {len(deduped)} unique companies")
        print(f"   🌟 {len(multi_list)} companies appear on 2+ lists (multi-source)")

        return deduped


# =============================================================================
# PHASE B: PROFILE ENRICHMENT
# =============================================================================

class SPWProfileScraper:
    """Scrapes detailed data from individual SPW company profile pages."""

    def __init__(self, browser: Browser):
        self.browser = browser

    async def scrape_profile(self, company_name: str, profile_url: str) -> Optional[SPWProfile]:
        """
        Scrape a single SPW company profile page.

        Profile pages contain rich data:
        - Location (City, State)
        - Website URL
        - Year founded
        - Employee count
        - kW installed (2024)
        - Cumulative kW (all-time)
        - Company description
        - Markets served (Utility, C&I, Community, Residential)
        - Service areas (states/territories)
        """
        if not profile_url:
            return None

        page = await self.browser.new_page()
        profile = None

        try:
            await page.goto(profile_url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Extract profile data using JavaScript
            data = await page.evaluate("""
                () => {
                    const result = {
                        company_name: '',
                        city: '',
                        state: '',
                        website: '',
                        year_founded: 0,
                        employee_count: 0,
                        kw_2024: 0,
                        cumulative_kw: 0,
                        description: '',
                        markets_served: [],
                        service_areas: [],
                        primary_service: ''
                    };

                    // Company name from header
                    const header = document.querySelector('h1, .company-name, .entry-title');
                    if (header) {
                        result.company_name = header.textContent.trim();
                    }

                    // Look for profile data in various formats
                    const content = document.body.innerText;

                    // Location pattern: "City, ST"
                    const locationMatch = content.match(/Headquarters[:\\s]+([A-Za-z\\s]+),\\s*([A-Z]{2})/i);
                    if (locationMatch) {
                        result.city = locationMatch[1].trim();
                        result.state = locationMatch[2].trim();
                    }

                    // Website
                    const websiteLink = document.querySelector('a[href*="://"][rel*="nofollow"]');
                    if (websiteLink) {
                        result.website = websiteLink.href;
                    }

                    // Year founded
                    const foundedMatch = content.match(/(?:Founded|Established)[:\\s]+([0-9]{4})/i);
                    if (foundedMatch) {
                        result.year_founded = parseInt(foundedMatch[1]);
                    }

                    // Employees
                    const empMatch = content.match(/([0-9,]+)\\s*(?:employees|staff)/i);
                    if (empMatch) {
                        result.employee_count = parseInt(empMatch[1].replace(',', ''));
                    }

                    // kW installed
                    const kwMatch = content.match(/([0-9,]+)\\s*kW\\s*(?:installed|in\\s*2024)/i);
                    if (kwMatch) {
                        result.kw_2024 = parseInt(kwMatch[1].replace(',', ''));
                    }

                    // Cumulative kW
                    const cumKwMatch = content.match(/(?:Cumulative|Total)[:\\s]*([0-9,]+)\\s*kW/i);
                    if (cumKwMatch) {
                        result.cumulative_kw = parseInt(cumKwMatch[1].replace(',', ''));
                    }

                    // Markets served
                    const marketsText = content.match(/Markets[:\\s]+([^\\n]+)/i);
                    if (marketsText) {
                        const markets = marketsText[1].split(/[,&]/);
                        result.markets_served = markets.map(m => m.trim()).filter(m => m);
                    }

                    // Service areas (states)
                    const areasMatch = content.match(/(?:Service\\s*areas|States?\\s*served)[:\\s]+([^\\n]+)/i);
                    if (areasMatch) {
                        // Extract state codes or "Nationwide"
                        const areas = areasMatch[1].split(/[,;]/);
                        result.service_areas = areas.map(a => a.trim()).filter(a => a);
                    }

                    // Description (first substantial paragraph)
                    const paragraphs = document.querySelectorAll('p');
                    for (const p of paragraphs) {
                        const text = p.textContent.trim();
                        if (text.length > 100 && !text.includes('Cookie') && !text.includes('©')) {
                            result.description = text.substring(0, 500);
                            break;
                        }
                    }

                    return result;
                }
            """)

            profile = SPWProfile(
                company_name=data.get('company_name') or company_name,
                profile_url=profile_url,
                city=data.get('city', ''),
                state=data.get('state', ''),
                website=data.get('website', ''),
                year_founded=data.get('year_founded', 0),
                employee_count=data.get('employee_count', 0),
                kw_2024=data.get('kw_2024', 0),
                cumulative_kw=data.get('cumulative_kw', 0),
                description=data.get('description', ''),
                markets_served=data.get('markets_served', []),
                service_areas=data.get('service_areas', []),
                primary_service=data.get('primary_service', ''),
                scraped_at=datetime.now().isoformat()
            )

            print(f"   ✅ {company_name}: {profile.city}, {profile.state} | {profile.employee_count} employees")

        except Exception as e:
            print(f"   ❌ Error scraping {company_name}: {e}")
        finally:
            await page.close()

        return profile


# =============================================================================
# DATABASE INTEGRATION
# =============================================================================

class SPWDatabaseWriter:
    """Writes SPW data to SQLite pipeline database."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def save_company(self, company: SPWCompany):
        """Save company from list extraction to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if company already exists
            cursor.execute("""
                SELECT id FROM spw_rankings
                WHERE company_name = ? AND list_name = ?
            """, (company.company_name, company.list_name))

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE spw_rankings SET
                        rank_position = ?,
                        kw_installed = ?,
                        headquarters_state = ?,
                        profile_url = ?
                    WHERE id = ?
                """, (company.rank_position, company.kw_installed,
                      company.headquarters_state, company.profile_url, existing[0]))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO spw_rankings
                    (company_name, list_name, rank_position, kw_installed,
                     headquarters_state, profile_url, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (company.company_name, company.list_name, company.rank_position,
                      company.kw_installed, company.headquarters_state,
                      company.profile_url, company.year))

            conn.commit()
        finally:
            conn.close()

    def update_profile(self, profile: SPWProfile):
        """Update SPW record with enriched profile data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE spw_rankings SET
                    city = ?,
                    website = ?,
                    year_founded = ?,
                    employee_count = ?,
                    cumulative_kw = ?,
                    description = ?,
                    markets_served = ?,
                    service_areas = ?,
                    scraped_at = ?
                WHERE profile_url = ?
            """, (
                profile.city,
                profile.website,
                profile.year_founded if profile.year_founded else None,
                profile.employee_count if profile.employee_count else None,
                profile.cumulative_kw if profile.cumulative_kw else None,
                profile.description,
                json.dumps(profile.markets_served) if profile.markets_served else None,
                json.dumps(profile.service_areas) if profile.service_areas else None,
                profile.scraped_at,
                profile.profile_url
            ))
            conn.commit()
        finally:
            conn.close()

    def get_companies_needing_profiles(self) -> List[tuple]:
        """Get companies that haven't had their profiles scraped yet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT company_name, profile_url
            FROM spw_rankings
            WHERE profile_url IS NOT NULL
              AND profile_url != ''
              AND (scraped_at IS NULL OR scraped_at = '')
        """)

        results = cursor.fetchall()
        conn.close()
        return results

    def link_to_contractors(self):
        """
        Link SPW companies to contractors in the state license database.

        Uses fuzzy matching on normalized company names.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all SPW companies without contractor links
        cursor.execute("""
            SELECT id, company_name, headquarters_state
            FROM spw_rankings
            WHERE contractor_id IS NULL
        """)
        spw_companies = cursor.fetchall()

        matched = 0
        for spw_id, company_name, state in spw_companies:
            norm_name = normalize_company_name(company_name)

            # Try exact normalized match first
            cursor.execute("""
                SELECT id FROM contractors
                WHERE normalized_name = ?
                AND (state = ? OR ? IS NULL OR ? = '')
            """, (norm_name, state, state, state))

            contractor = cursor.fetchone()

            if contractor:
                cursor.execute("""
                    UPDATE spw_rankings SET contractor_id = ? WHERE id = ?
                """, (contractor[0], spw_id))
                matched += 1

        conn.commit()
        conn.close()

        print(f"\n🔗 Linked {matched} SPW companies to contractors in state license database")


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

async def run_phase_a(browser: Browser, lists_to_scrape: List[str] = None) -> List[SPWCompany]:
    """
    Phase A: Extract companies from SPW list pages.

    Args:
        browser: Playwright browser instance
        lists_to_scrape: Specific lists to scrape (None = all)

    Returns:
        List of SPWCompany objects
    """
    scraper = SPWListScraper(browser)

    if lists_to_scrape:
        companies = []
        for list_name in lists_to_scrape:
            if list_name in SPW_LISTS:
                result = await scraper.scrape_list_page(list_name, SPW_LISTS[list_name])
                companies.extend(result)
    else:
        companies = await scraper.scrape_all_lists()

    # Save to database
    db = SPWDatabaseWriter()
    for company in companies:
        db.save_company(company)

    # Save to JSON for backup
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"spw_lists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump([asdict(c) for c in companies], f, indent=2)
    print(f"\n💾 Saved {len(companies)} companies to {output_file}")

    return companies


async def run_phase_b(browser: Browser, limit: int = None):
    """
    Phase B: Enrich companies with profile page data.

    Args:
        browser: Playwright browser instance
        limit: Max profiles to scrape (None = all)
    """
    print("\n" + "=" * 70)
    print("PHASE B: SPW PROFILE ENRICHMENT")
    print("=" * 70)

    db = SPWDatabaseWriter()
    companies = db.get_companies_needing_profiles()

    if limit:
        companies = companies[:limit]

    print(f"\n📋 {len(companies)} profiles to scrape")

    profile_scraper = SPWProfileScraper(browser)
    profiles = []

    for idx, (name, url) in enumerate(companies, 1):
        print(f"\n[{idx}/{len(companies)}] Scraping: {name}")
        profile = await profile_scraper.scrape_profile(name, url)

        if profile:
            profiles.append(profile)
            db.update_profile(profile)

        # Polite delay
        await asyncio.sleep(1.5)

    print(f"\n✅ Enriched {len(profiles)} company profiles")

    # Save profiles to JSON backup
    output_file = OUTPUT_DIR / f"spw_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump([asdict(p) for p in profiles], f, indent=2)
    print(f"💾 Saved to {output_file}")


async def run_full_pipeline():
    """Run complete SPW scraping pipeline (Phase A + Phase B)."""
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright required. Install with: pip install playwright && playwright install chromium")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            # Phase A: Extract all companies from lists
            companies = await run_phase_a(browser)

            # Phase B: Enrich with profile data
            await run_phase_b(browser)

            # Link to contractor database
            db = SPWDatabaseWriter()
            db.link_to_contractors()

        finally:
            await browser.close()


def setup_logging():
    """Configure logging to both file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOG_DIR / f"spw_scraper_{timestamp}.log"

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info(f"📋 SPW Scraper started - log file: {log_file}")
    return log_file


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SPW Solar Scraper")
    parser.add_argument("--list", type=str, help="Scrape specific list (master, commercial, etc.)")
    parser.add_argument("--all", action="store_true", help="Scrape all 11 lists")
    parser.add_argument("--enrich-profiles", action="store_true", help="Scrape profile pages only")
    parser.add_argument("--full", action="store_true", help="Full pipeline (lists + profiles)")
    parser.add_argument("--limit", type=int, help="Limit number of profiles to scrape")

    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging()
    logging.info(f"Arguments: {args}")

    if not PLAYWRIGHT_AVAILABLE:
        logging.error("❌ Playwright required. Install with: pip install playwright && playwright install chromium")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            if args.full:
                companies = await run_phase_a(browser)
                await run_phase_b(browser, limit=args.limit)
                db = SPWDatabaseWriter()
                db.link_to_contractors()

            elif args.enrich_profiles:
                await run_phase_b(browser, limit=args.limit)

            elif args.all:
                await run_phase_a(browser)

            elif args.list:
                await run_phase_a(browser, lists_to_scrape=[args.list])

            else:
                # Default: scrape master list
                await run_phase_a(browser, lists_to_scrape=["master"])

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
