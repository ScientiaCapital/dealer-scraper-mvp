#!/usr/bin/env python3
"""
System Readiness Test for 22-OEM Sequential Execution

Verifies all components are importable and system is ready for production.
Does NOT run actual scraping (requires user interaction).
"""

import sys
from pathlib import Path

print("="*80)
print("SYSTEM READINESS TEST")
print("="*80)
print()

# Test 1: Import main script
print("Test 1: Importing main script...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from scripts.run_22_oem_sequential import (
        OEM_PRIORITY_ORDER,
        CHECKPOINT_INTERVAL,
        delete_checkpoints,
        prompt_user_confirmation,
        deduplicate_dealers,
        generate_output_files,
        display_validation_metrics,
        main
    )
    print("✅ PASSED - All functions imported successfully")
except ImportError as e:
    print(f"❌ FAILED - Import error: {e}")
    sys.exit(1)

# Test 2: Import dependencies
print("\nTest 2: Importing dependencies...")
try:
    from scrapers.scraper_factory import ScraperFactory
    from scrapers.base_scraper import ScraperMode
    from fuzzywuzzy import fuzz
    print("✅ PASSED - All dependencies available")
except ImportError as e:
    print(f"❌ FAILED - Dependency error: {e}")
    sys.exit(1)

# Test 3: Verify configuration
print("\nTest 3: Verifying configuration...")
try:
    assert len(OEM_PRIORITY_ORDER) == 17, f"Expected 17 OEMs, got {len(OEM_PRIORITY_ORDER)}"
    assert CHECKPOINT_INTERVAL == 25, f"Expected checkpoint interval 25, got {CHECKPOINT_INTERVAL}"
    print(f"✅ PASSED - Configuration valid ({len(OEM_PRIORITY_ORDER)} OEMs, checkpoint every {CHECKPOINT_INTERVAL} ZIPs)")
except AssertionError as e:
    print(f"❌ FAILED - Configuration error: {e}")
    sys.exit(1)

# Test 4: Verify scraper factory can create scrapers
print("\nTest 4: Testing scraper factory...")
try:
    # Try to create a scraper for first OEM in list
    test_oem = OEM_PRIORITY_ORDER[0]
    scraper = ScraperFactory.create(test_oem, mode=ScraperMode.PLAYWRIGHT)
    assert scraper is not None, "Scraper creation returned None"
    assert hasattr(scraper, 'scrape_multiple'), "Scraper missing scrape_multiple method"
    print(f"✅ PASSED - Successfully created {test_oem} scraper")
except Exception as e:
    print(f"❌ FAILED - Scraper creation error: {e}")
    sys.exit(1)

# Test 5: Verify config.py exists and has ALL_ZIP_CODES
print("\nTest 5: Verifying config.py...")
try:
    # Go up to project root
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    from config import ALL_ZIP_CODES
    assert len(ALL_ZIP_CODES) == 264, f"Expected 264 ZIPs, got {len(ALL_ZIP_CODES)}"
    print(f"✅ PASSED - config.py loaded ({len(ALL_ZIP_CODES)} ZIP codes)")
except ImportError:
    print("⚠️  WARNING - config.py not found (gitignored, expected in production)")
    print("   System will attempt to load from parent directory when running")
except AssertionError as e:
    print(f"❌ FAILED - Config validation error: {e}")
    sys.exit(1)

# Test 6: Verify deduplication pipeline
print("\nTest 6: Testing deduplication pipeline...")
try:
    test_dealers = [
        {"name": "Test Co", "phone": "555-1234", "domain": "test.com", "state": "CA"},
        {"name": "Test Co", "phone": "555-1234", "domain": "test.com", "state": "CA"},  # Duplicate
    ]
    deduped, stats = deduplicate_dealers(test_dealers, "TestOEM")
    assert len(deduped) == 1, f"Expected 1 dealer after dedup, got {len(deduped)}"
    assert stats['phone_dupes'] == 1, f"Expected 1 phone duplicate, got {stats['phone_dupes']}"
    print("✅ PASSED - Deduplication pipeline works correctly")
except Exception as e:
    print(f"❌ FAILED - Deduplication error: {e}")
    sys.exit(1)

# Test 7: Verify output file generation
print("\nTest 7: Testing output file generation...")
try:
    import tempfile
    test_dealers = [{"name": "Test", "phone": "555-1234", "state": "CA"}]
    dedup_stats = {'initial': 1, 'phone_dupes': 0, 'domain_dupes': 0, 'fuzzy_dupes': 0, 'final': 1, 'fuzzy_matches': []}

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_oem"
        files = generate_output_files(
            raw_dealers=test_dealers,
            deduped_dealers=test_dealers,
            dedup_stats=dedup_stats,
            oem_name="Test OEM",
            output_dir=output_dir
        )
        assert len(files) == 4, f"Expected 4 output files, got {len(files)}"
        assert all(path.exists() for path in files.values()), "Not all output files created"
    print("✅ PASSED - Output file generation works correctly")
except Exception as e:
    print(f"❌ FAILED - Output generation error: {e}")
    sys.exit(1)

# Test 8: Verify validation metrics
print("\nTest 8: Testing validation metrics...")
try:
    test_dealers = [
        {"name": "Test", "phone": "555-1234", "address": "123 Main", "state": "CA", "scraped_from_zip": "94102"}
    ]
    metrics = display_validation_metrics(test_dealers, "TestOEM", total_target_zips=264)
    assert 'zip_coverage' in metrics, "Missing zip_coverage in metrics"
    assert 'data_completeness' in metrics, "Missing data_completeness in metrics"
    assert 'geographic_distribution' in metrics, "Missing geographic_distribution in metrics"
    print("✅ PASSED - Validation metrics display works correctly")
except Exception as e:
    print(f"❌ FAILED - Validation metrics error: {e}")
    sys.exit(1)

print()
print("="*80)
print("✅ ALL SYSTEM READINESS TESTS PASSED")
print("="*80)
print()
print("System is ready for production deployment.")
print()
print("To run production scraping:")
print("  python3 scripts/run_22_oem_sequential.py")
print()
print("The script will:")
print("  1. Load 264 ZIP codes from config.py")
print("  2. Process 17 OEMs sequentially (HVAC → Generators → Solar → Battery)")
print("  3. Prompt for confirmation before each OEM")
print("  4. Save checkpoints every 25 ZIPs")
print("  5. Generate 4 output files per OEM")
print("  6. Display validation metrics after each OEM")
print()
print("Expected duration: ~13 hours for all 17 OEMs")
print("="*80)
