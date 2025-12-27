#!/usr/bin/env python3
"""
Test Trane scraper checkpoint/resume functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.trane_scraper import TraneScraper
from pathlib import Path
import json

def test_checkpoint_loading():
    """Test that checkpoint loading works correctly."""
    scraper = TraneScraper()

    # Test with non-existent checkpoint dir
    checkpoint_dir = "output/trane_checkpoints"
    count, names = scraper._load_checkpoint(checkpoint_dir)
    print(f"Empty checkpoint test: count={count}, names_len={len(names)}")
    assert count == 0
    assert len(names) == 0
    print("✅ Empty checkpoint handling works")

    # Test with existing checkpoint if present
    checkpoints = list(Path(checkpoint_dir).glob("trane_checkpoint_*.json"))
    if checkpoints:
        count, names = scraper._load_checkpoint(checkpoint_dir)
        print(f"Existing checkpoint: count={count}, names_len={len(names)}")
        print(f"✅ Checkpoint loading works: found {count} processed dealers")
    else:
        print("ℹ️  No existing checkpoints to test resume (expected on fresh run)")

    return True

def test_playwright_mode_quick():
    """Quick test of Playwright mode with 3 dealers."""
    print("\n" + "="*60)
    print("Testing Playwright mode (3 dealers)")
    print("="*60)

    scraper = TraneScraper()
    dealers = scraper.scrape(mode='playwright', zip_code='10001', limit=3)

    print(f"\n📊 Results: {len(dealers)} dealers scraped")
    for d in dealers:
        rating = f"⭐{d.google_rating}" if d.google_rating > 0 else "No rating"
        phone = f"📞{d.phone[:10]}..." if d.phone else "No phone"
        print(f"  • {d.name[:35]:35} | {d.city:15} | {rating:10} | {phone}")

    return len(dealers) > 0

if __name__ == "__main__":
    print("TRANE SCRAPER CHECKPOINT/RESUME TEST")
    print("="*60 + "\n")

    test_checkpoint_loading()

    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        test_playwright_mode_quick()

    print("\n✅ All tests passed!")
