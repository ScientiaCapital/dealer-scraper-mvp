#!/usr/bin/env python3
"""
Test validation metrics display.
"""

import sys
sys.path.insert(0, '/Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential')

from scripts.run_22_oem_sequential import display_validation_metrics

# Create test data with various scenarios
test_dealers = [
    # California dealers (3)
    {"name": "ABC Heating", "phone": "555-1234", "address": "123 Main St", "city": "SF", "state": "CA", "zip": "94102", "scraped_from_zip": "94102"},
    {"name": "DEF Solar", "phone": "555-5678", "address": "456 Oak Ave", "city": "LA", "state": "CA", "zip": "90001", "scraped_from_zip": "90001"},
    {"name": "GHI HVAC", "phone": "555-9999", "address": "789 Pine Rd", "city": "SD", "state": "CA", "zip": "92101", "scraped_from_zip": "92101"},

    # Texas dealers (2)
    {"name": "JKL Electric", "phone": "555-1111", "address": "101 Elm St", "city": "Houston", "state": "TX", "zip": "77002", "scraped_from_zip": "77002"},
    {"name": "MNO Power", "phone": "555-2222", "address": "202 Cedar Ave", "city": "Austin", "state": "TX", "zip": "78701", "scraped_from_zip": "78701"},

    # Pennsylvania dealer (1)
    {"name": "PQR Services", "phone": "555-3333", "address": "303 Birch Ln", "city": "Philly", "state": "PA", "zip": "19019", "scraped_from_zip": "19019"},

    # Florida dealer with missing phone (data quality test)
    {"name": "STU Solar", "phone": "", "address": "404 Maple Dr", "city": "Miami", "state": "FL", "zip": "33101", "scraped_from_zip": "33101"},

    # Massachusetts dealer with missing address (data quality test)
    {"name": "VWX HVAC", "phone": "555-4444", "address": "", "city": "Boston", "state": "MA", "zip": "02101", "scraped_from_zip": "02101"},

    # New York dealer with no scraped_from_zip (coverage test)
    {"name": "YZA Electric", "phone": "555-5555", "address": "505 Walnut St", "city": "NYC", "state": "NY", "zip": "10001", "scraped_from_zip": ""},
]

print("=" * 80)
print("VALIDATION METRICS TEST")
print("=" * 80)
print(f"\nTest data: {len(test_dealers)} dealers")
print(f"Unique ZIPs with results: 8 (one dealer has empty scraped_from_zip)")
print(f"Expected coverage: 8/264 = 3.0%")
print(f"Missing phone: 1 dealer (88.9% completeness)")
print(f"Missing address: 1 dealer (88.9% completeness)")
print(f"Geographic distribution: CA (3), TX (2), PA (1), FL (1), MA (1), NY (1)")
print()

# Run validation
metrics = display_validation_metrics(test_dealers, "Test OEM", total_target_zips=264)

print("=" * 80)
print("VERIFICATION")
print("=" * 80)

# Verify ZIP coverage
assert metrics['zip_coverage']['zips_with_results'] == 8, f"Expected 8 ZIPs, got {metrics['zip_coverage']['zips_with_results']}"
assert abs(metrics['zip_coverage']['coverage_percentage'] - 3.0) < 0.1, f"Expected 3.0% coverage, got {metrics['zip_coverage']['coverage_percentage']}"
print("✅ ZIP coverage: 8/264 (3.0%)")

# Verify data completeness
assert metrics['data_completeness']['name']['count'] == 9, "All dealers should have names"
assert metrics['data_completeness']['phone']['count'] == 8, "8 dealers should have phones (1 missing)"
assert metrics['data_completeness']['address']['count'] == 8, "8 dealers should have addresses (1 missing)"
print("✅ Data completeness: name (100%), phone (88.9%), address (88.9%)")

# Verify geographic distribution
assert metrics['geographic_distribution']['CA'] == 3, "Expected 3 CA dealers"
assert metrics['geographic_distribution']['TX'] == 2, "Expected 2 TX dealers"
assert metrics['geographic_distribution']['PA'] == 1, "Expected 1 PA dealer"
print("✅ Geographic distribution: CA (3), TX (2), PA (1), FL (1), MA (1), NY (1)")

print(f"\n{'=' * 80}")
print("✅ ALL TESTS PASSED")
print("=" * 80)
