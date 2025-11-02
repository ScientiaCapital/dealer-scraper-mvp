#!/usr/bin/env python3
"""
Test output file generation.
"""

import sys
import json
import tempfile
import csv
from pathlib import Path

sys.path.insert(0, '/Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential')

from scripts.run_22_oem_sequential import generate_output_files

# Create test data
raw_dealers = [
    {"name": "ABC Heating", "phone": "555-1234", "domain": "abcheating.com", "state": "CA", "city": "SF"},
    {"name": "ABC Heating", "phone": "555-1234", "domain": "abcheating.com", "state": "CA", "city": "SF"},  # Duplicate
    {"name": "XYZ Solar", "phone": "555-5678", "domain": "xyzsolar.com", "state": "TX", "city": "Austin"},
]

deduped_dealers = [
    {"name": "ABC Heating", "phone": "555-1234", "domain": "abcheating.com", "state": "CA", "city": "SF"},
    {"name": "XYZ Solar", "phone": "555-5678", "domain": "xyzsolar.com", "state": "TX", "city": "Austin"},
]

dedup_stats = {
    'initial': 3,
    'phone_dupes': 1,
    'domain_dupes': 0,
    'fuzzy_dupes': 0,
    'fuzzy_matches': [],
    'final': 2
}

print("=" * 80)
print("OUTPUT FILE GENERATION TEST")
print("=" * 80)

# Create temporary output directory
with tempfile.TemporaryDirectory() as temp_dir:
    output_dir = Path(temp_dir) / "output" / "oem_data" / "test_oem"

    # Generate files
    print(f"\nGenerating output files to: {output_dir}")
    print()

    generated = generate_output_files(
        raw_dealers=raw_dealers,
        deduped_dealers=deduped_dealers,
        dedup_stats=dedup_stats,
        oem_name="Test OEM",
        output_dir=output_dir
    )

    print(f"\n{'=' * 80}")
    print("VERIFICATION")
    print("=" * 80)

    # Verify all 4 files exist
    assert 'raw_json' in generated, "Missing raw_json in generated files"
    assert 'csv' in generated, "Missing csv in generated files"
    assert 'log' in generated, "Missing log in generated files"
    assert 'report' in generated, "Missing report in generated files"

    assert generated['raw_json'].exists(), "raw_json file not created"
    assert generated['csv'].exists(), "csv file not created"
    assert generated['log'].exists(), "log file not created"
    assert generated['report'].exists(), "report file not created"

    print("✅ All 4 files exist")

    # Verify raw JSON content
    with open(generated['raw_json'], 'r') as f:
        json_data = json.load(f)
        assert len(json_data) == 3, f"Expected 3 raw dealers, got {len(json_data)}"
    print("✅ Raw JSON has correct dealer count (3)")

    # Verify CSV content
    with open(generated['csv'], 'r') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
        assert len(csv_rows) == 2, f"Expected 2 deduped dealers, got {len(csv_rows)}"
    print("✅ CSV has correct dealer count (2)")

    # Verify log content
    with open(generated['log'], 'r') as f:
        log_content = f.read()
        assert "Test OEM" in log_content, "OEM name not in log"
        assert "Raw dealers scraped: 3" in log_content, "Raw count not in log"
        assert "Unique dealers (after dedup): 2" in log_content, "Deduped count not in log"
    print("✅ Log file has correct content")

    # Verify report content
    with open(generated['report'], 'r') as f:
        report_content = f.read()
        assert "DEDUPLICATION REPORT: Test OEM" in report_content, "OEM name not in report"
        assert "Initial dealers: 3" in report_content, "Initial count not in report"
        assert "Final unique dealers: 2" in report_content, "Final count not in report"
        assert "Phase 1 - Phone Deduplication:" in report_content, "Phase 1 not in report"
        assert "Duplicates removed: 1" in report_content, "Duplicate count not in report"
    print("✅ Report file has correct content")

    print(f"\n{'=' * 80}")
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
