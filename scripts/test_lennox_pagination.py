#!/usr/bin/env python3
"""
Test Lennox scraper with pagination on single ZIP.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Test ZIP 07078 (NJ - user manually verified has dealers)
print("Testing Lennox scraper with pagination on ZIP 07078...")
scraper = ScraperFactory.create('Lennox', mode=ScraperMode.PLAYWRIGHT)
dealers = scraper._scrape_with_playwright('07078')

print(f'\n✅ Test complete: Found {len(dealers)} dealers for ZIP 07078')
if dealers:
    print('\nFirst 5 dealers:')
    for d in dealers[:5]:
        print(f'   - {d.name} ({d.phone}) - {d.city}, {d.state}')
else:
    print('❌ No dealers found!')
