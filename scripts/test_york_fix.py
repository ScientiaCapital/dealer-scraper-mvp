#!/usr/bin/env python3
"""
Test York scraper fix for cookie consent issue.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Test ZIP 33109 (Miami Beach - should have dealers)
print("Testing York scraper with cookie consent fix on ZIP 33109...")
scraper = ScraperFactory.create('York', mode=ScraperMode.PLAYWRIGHT)
dealers = scraper._scrape_with_playwright('33109')

print(f'\n✅ Test complete: Found {len(dealers)} dealers for ZIP 33109')
if dealers:
    print('\nFirst 5 dealers:')
    for d in dealers[:5]:
        print(f'   - {d.name} ({d.phone}) - {d.city}, {d.state}')
else:
    print('❌ No dealers found!')
