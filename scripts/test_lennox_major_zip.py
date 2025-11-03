#!/usr/bin/env python3
"""
Test Lennox scraper with pagination on major city ZIP (should have MANY dealers).
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# Test ZIP 60601 (Chicago downtown - should have tons of dealers)
print("Testing Lennox scraper with pagination on ZIP 60601 (Chicago)...")
scraper = ScraperFactory.create('Lennox', mode=ScraperMode.PLAYWRIGHT)
dealers = scraper._scrape_with_playwright('60601')

print(f'\n✅ Test complete: Found {len(dealers)} dealers for ZIP 60601')
if dealers:
    print('\nFirst 10 dealers:')
    for d in dealers[:10]:
        print(f'   - {d.name} ({d.phone}) - {d.city}, {d.state}')
else:
    print('❌ No dealers found!')
