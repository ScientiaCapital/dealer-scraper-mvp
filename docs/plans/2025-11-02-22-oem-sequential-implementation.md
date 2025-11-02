# 22-OEM Sequential Execution System - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a master script that scrapes 22 OEM dealer locators sequentially with checkpoints, full validation, and user confirmation per OEM.

**Architecture:** Sequential state machine that prompts user before each OEM, runs scraper with checkpoint saving (every 25 ZIPs), executes full deduplication pipeline (phone → domain → fuzzy name matching), generates output files (.json/.csv/.log/report), and displays validation results.

**Tech Stack:** Python 3.11+, Playwright (sync), fuzzywuzzy (fuzzy string matching), pandas (CSV generation), JSON (checkpoints), datetime (timestamps)

---

## Task 1: OEM Priority Configuration

**Files:**
- Modify: `scripts/run_22_oem_sequential.py` (create new file)

**Step 1: Create OEM priority list constant**

Create the master script with OEM priority order:

```python
#!/usr/bin/env python3
"""
22-OEM Sequential Execution System
Scrapes all 22 OEM networks with checkpoints and full validation.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# OEM Priority Order (HVAC → Generators → Solar → Battery)
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC Systems (6 OEMs)
    "Carrier",
    "Trane",
    "Lennox",
    "York",
    "Rheem",
    "Mitsubishi",

    # Tier 2: Backup Generators (4 OEMs)
    "Generac",
    "Kohler",
    "Cummins",
    "Briggs & Stratton",

    # Tier 3: Solar Inverters (10 OEMs)
    "Enphase",
    "Fronius",
    "SMA",
    "Sol-Ark",
    "GoodWe",
    "Growatt",
    "Sungrow",
    "ABB",
    "Delta",
    "Tigo",

    # Tier 4: Battery Storage (2 OEMs)
    "Tesla",
    "SimpliPhi"
]

# Configuration
CHECKPOINT_INTERVAL = 25
TODAY = datetime.now().strftime("%Y%m%d")
```

**Step 2: Verify OEM list matches scrapers**

Run quick check:

```bash
cd /Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential
./venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import OEM_PRIORITY_ORDER
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

print(f'Checking {len(OEM_PRIORITY_ORDER)} OEMs...')
for oem in OEM_PRIORITY_ORDER:
    try:
        scraper = ScraperFactory.create(oem, mode=ScraperMode.PLAYWRIGHT)
        print(f'  ✓ {oem}')
    except Exception as e:
        print(f'  ✗ {oem}: {e}')
"
```

Expected: 22 checkmarks (all OEMs registered)

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add OEM priority configuration for sequential execution"
```

---

## Task 2: Checkpoint Cleanup Function

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add checkpoint cleanup function**

Add after OEM_PRIORITY_ORDER:

```python
def delete_checkpoints(oem_name: str) -> None:
    """
    Delete all checkpoint files for an OEM (fresh start policy).

    Args:
        oem_name: Name of OEM (e.g., "Carrier")
    """
    checkpoint_dir = PROJECT_ROOT / "output" / "oem_data" / oem_name.lower().replace(" ", "_").replace("&", "and") / "checkpoints"

    if checkpoint_dir.exists():
        checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoint_files:
            print(f"  → Deleting {len(checkpoint_files)} old checkpoints...")
            for checkpoint_file in checkpoint_files:
                checkpoint_file.unlink()
            print(f"  ✓ Checkpoints deleted")
    else:
        print(f"  → No existing checkpoints")
```

**Step 2: Test checkpoint cleanup**

Create test checkpoint and verify deletion:

```bash
./venv/bin/python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')

# Create test checkpoint
test_dir = Path('output/oem_data/carrier/checkpoints')
test_dir.mkdir(parents=True, exist_ok=True)
test_file = test_dir / 'checkpoint_test.json'
test_file.write_text('{\"test\": true}')

print(f'Created test checkpoint: {test_file}')
print(f'Exists: {test_file.exists()}')

# Test cleanup
from scripts.run_22_oem_sequential import delete_checkpoints
delete_checkpoints('Carrier')

print(f'After cleanup, exists: {test_file.exists()}')
"
```

Expected: "Exists: True" → "Deleting 1 old checkpoints" → "After cleanup, exists: False"

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add checkpoint cleanup function (fresh start policy)"
```

---

## Task 3: User Confirmation Prompt

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add user confirmation function**

```python
def prompt_user_confirmation(oem_name: str, oem_index: int, total_oems: int) -> str:
    """
    Prompt user for confirmation before running OEM scraper.

    Args:
        oem_name: Name of OEM (e.g., "Carrier")
        oem_index: Index in priority list (0-based)
        total_oems: Total number of OEMs

    Returns:
        'y' = proceed, 'n' = exit script, 'skip' = skip this OEM
    """
    print(f"\n{'='*80}")
    print(f"OEM {oem_index + 1}/{total_oems}: {oem_name}")
    print(f"{'='*80}")
    print(f"Target: 264 ZIP codes (all 50 states)")
    print(f"Output: output/oem_data/{oem_name.lower().replace(' ', '_').replace('&', 'and')}/")
    print()

    while True:
        response = input(f"Ready to run {oem_name} scraper? (y/n/skip): ").strip().lower()

        if response in ['y', 'yes']:
            return 'y'
        elif response in ['n', 'no']:
            return 'n'
        elif response in ['skip', 's']:
            return 'skip'
        else:
            print("Invalid input. Enter y/n/skip:")
```

**Step 2: Test prompt function**

Manual test (interactive):

```bash
./venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import prompt_user_confirmation

# Test prompt
result = prompt_user_confirmation('Carrier', 0, 22)
print(f'User choice: {result}')
"
```

Expected: Display formatted prompt, accept y/n/skip input

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add user confirmation prompt with y/n/skip handling"
```

---

## Task 4: Deduplication Pipeline

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add deduplication imports and function**

Add to imports:

```python
from fuzzywuzzy import fuzz
import pandas as pd
from typing import List, Dict, Tuple
```

Add deduplication function:

```python
def deduplicate_dealers(dealers: List[Dict], oem_name: str) -> Tuple[List[Dict], Dict]:
    """
    Deduplicate dealers using multi-signal matching (phone → domain → fuzzy name).

    Args:
        dealers: List of dealer dictionaries
        oem_name: Name of OEM for logging

    Returns:
        (deduplicated_dealers, stats_dict)
    """
    print(f"  → Running deduplication pipeline...")

    initial_count = len(dealers)
    stats = {
        'initial': initial_count,
        'phone_dupes': 0,
        'domain_dupes': 0,
        'fuzzy_dupes': 0,
        'fuzzy_matches': []
    }

    # Phase 1: Phone normalization deduplication
    phone_map = {}
    dealers_after_phone = []

    for dealer in dealers:
        phone = dealer.get('phone', '')
        # Normalize: strip to 10 digits
        normalized_phone = ''.join(filter(str.isdigit, phone))[-10:] if phone else ''

        if normalized_phone and normalized_phone in phone_map:
            stats['phone_dupes'] += 1
        else:
            if normalized_phone:
                phone_map[normalized_phone] = dealer
            dealers_after_phone.append(dealer)

    print(f"     - Phone dedup: {initial_count} → {len(dealers_after_phone)} (-{stats['phone_dupes']}, {stats['phone_dupes']/initial_count*100:.1f}%)")

    # Phase 2: Domain deduplication
    domain_map = {}
    dealers_after_domain = []

    for dealer in dealers_after_phone:
        domain = dealer.get('domain', '')
        # Extract root domain
        root_domain = domain.replace('www.', '').lower() if domain else ''

        if root_domain and root_domain in domain_map:
            stats['domain_dupes'] += 1
        else:
            if root_domain:
                domain_map[root_domain] = dealer
            dealers_after_domain.append(dealer)

    print(f"     - Domain dedup: {len(dealers_after_phone)} → {len(dealers_after_domain)} (-{stats['domain_dupes']}, {stats['domain_dupes']/len(dealers_after_phone)*100:.1f}%)")

    # Phase 3: Fuzzy name matching (85% threshold, same state)
    dealers_final = []
    name_state_map = {}

    for dealer in dealers_after_domain:
        name = dealer.get('name', '').strip().lower()
        state = dealer.get('state', '').strip().upper()

        if not name:
            dealers_final.append(dealer)
            continue

        # Check for fuzzy matches in same state
        found_match = False
        for existing_name, existing_dealer in name_state_map.items():
            if existing_dealer.get('state', '').strip().upper() == state:
                similarity = fuzz.ratio(name, existing_name)
                if similarity >= 85:
                    stats['fuzzy_dupes'] += 1
                    stats['fuzzy_matches'].append({
                        'name1': existing_dealer.get('name'),
                        'name2': dealer.get('name'),
                        'similarity': similarity,
                        'state': state
                    })
                    found_match = True
                    break

        if not found_match:
            name_state_map[name] = dealer
            dealers_final.append(dealer)

    print(f"     - Fuzzy name dedup: {len(dealers_after_domain)} → {len(dealers_final)} (-{stats['fuzzy_dupes']}, {stats['fuzzy_dupes']/len(dealers_after_domain)*100:.1f}%)")

    stats['final'] = len(dealers_final)
    total_dedup_rate = (initial_count - len(dealers_final)) / initial_count * 100
    print(f"  ✓ Deduplication complete: {initial_count} → {len(dealers_final)} (dedup rate: {total_dedup_rate:.1f}%)")

    return dealers_final, stats
```

**Step 2: Test deduplication with sample data**

```bash
./venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import deduplicate_dealers

# Create test data with duplicates
test_dealers = [
    {'name': 'ABC Heating & Cooling Inc', 'phone': '555-123-4567', 'domain': 'abc-heating.com', 'state': 'CA'},
    {'name': 'ABC Heating and Cooling', 'phone': '555-123-4567', 'domain': 'abc-heating.com', 'state': 'CA'},  # Phone dupe
    {'name': 'XYZ HVAC Services', 'phone': '555-999-8888', 'domain': 'www.xyz-hvac.com', 'state': 'TX'},
    {'name': 'XYZ HVAC Service', 'phone': '555-888-7777', 'domain': 'xyz-hvac.com', 'state': 'TX'},  # Domain dupe
    {'name': 'Smith HVAC LLC', 'phone': '555-111-2222', 'domain': 'smith-hvac.com', 'state': 'NY'},
    {'name': 'Smith HVAC', 'phone': '555-333-4444', 'domain': 'smithhvac.com', 'state': 'NY'},  # Fuzzy match (86% similar)
]

deduplicated, stats = deduplicate_dealers(test_dealers, 'TestOEM')
print(f'Final count: {len(deduplicated)}')
print(f'Fuzzy matches found: {len(stats[\"fuzzy_matches\"])}')
"
```

Expected: 6 → 3 dealers (phone dupe, domain dupe, fuzzy match detected)

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add multi-signal deduplication pipeline with fuzzy matching"
```

---

## Task 5: Output File Generation

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add file generation functions**

```python
import json

def generate_output_files(
    oem_name: str,
    dealers_raw: List[Dict],
    dealers_deduped: List[Dict],
    dedup_stats: Dict,
    scraping_log: List[str]
) -> None:
    """
    Generate all output files (.json, .csv, .log, dedup report).

    Args:
        oem_name: Name of OEM
        dealers_raw: Raw dealer data (with duplicates)
        dealers_deduped: Deduplicated dealers
        dedup_stats: Deduplication statistics
        scraping_log: List of log messages
    """
    # Create output directory
    oem_dir_name = oem_name.lower().replace(' ', '_').replace('&', 'and')
    output_dir = PROJECT_ROOT / "output" / "oem_data" / oem_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Raw JSON
    raw_file = output_dir / f"{oem_dir_name}_raw_{TODAY}.json"
    with open(raw_file, 'w') as f:
        json.dump(dealers_raw, f, indent=2)
    print(f"  📁 {raw_file.name} ({len(dealers_raw)} dealers)")

    # 2. Deduplicated CSV
    csv_file = output_dir / f"{oem_dir_name}_deduped_{TODAY}.csv"
    df = pd.DataFrame(dealers_deduped)
    df.to_csv(csv_file, index=False)
    print(f"  📁 {csv_file.name} ({len(dealers_deduped)} unique)")

    # 3. Execution log
    log_file = output_dir / f"{oem_dir_name}_execution_{TODAY}.log"
    with open(log_file, 'w') as f:
        f.write('\n'.join(scraping_log))
    print(f"  📁 {log_file.name}")

    # 4. Deduplication report
    report_file = output_dir / f"{oem_dir_name}_dedup_report_{TODAY}.txt"
    with open(report_file, 'w') as f:
        f.write(f"Deduplication Report - {oem_name}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")

        f.write(f"Raw dealers scraped: {dedup_stats['initial']}\n")
        f.write(f"After phone dedup: {dedup_stats['initial'] - dedup_stats['phone_dupes']} (-{dedup_stats['phone_dupes']})\n")
        f.write(f"After domain dedup: {dedup_stats['initial'] - dedup_stats['phone_dupes'] - dedup_stats['domain_dupes']} (-{dedup_stats['domain_dupes']})\n")
        f.write(f"After fuzzy name dedup: {dedup_stats['final']} (-{dedup_stats['fuzzy_dupes']})\n")
        f.write(f"Total deduplication rate: {(dedup_stats['initial'] - dedup_stats['final']) / dedup_stats['initial'] * 100:.1f}%\n\n")

        if dedup_stats['fuzzy_matches']:
            f.write(f"Fuzzy Matches Found: {len(dedup_stats['fuzzy_matches'])}\n")
            f.write("-"*60 + "\n")
            for i, match in enumerate(dedup_stats['fuzzy_matches'], 1):
                f.write(f"{i}. \"{match['name1']}\" ↔ \"{match['name2']}\" ({match['similarity']}% match, {match['state']})\n")

    print(f"  📁 {report_file.name}")
```

**Step 2: Test file generation**

```bash
./venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import generate_output_files, deduplicate_dealers

test_dealers = [
    {'name': 'Test Dealer 1', 'phone': '555-1111', 'state': 'CA'},
    {'name': 'Test Dealer 2', 'phone': '555-2222', 'state': 'TX'},
]

deduped, stats = deduplicate_dealers(test_dealers, 'TestOEM')
logs = ['Log line 1', 'Log line 2']

generate_output_files('TestOEM', test_dealers, deduped, stats, logs)

# Verify files exist
from pathlib import Path
output_dir = Path('output/oem_data/testoem')
print(f'Files created: {list(output_dir.glob(\"*20251102*\"))}')
"
```

Expected: 4 files created (.json, .csv, .log, .txt)

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add output file generation (.json/.csv/.log/report)"
```

---

## Task 6: Validation Metrics Display

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add validation display function**

```python
def display_validation_results(
    oem_name: str,
    dealers: List[Dict],
    dedup_stats: Dict,
    total_zips: int
) -> None:
    """
    Display quality metrics and validation results.

    Args:
        oem_name: Name of OEM
        dealers: Deduplicated dealers
        dedup_stats: Deduplication statistics
        total_zips: Total ZIP codes scraped (should be 264)
    """
    print(f"\n  → Quality metrics:")

    # ZIP coverage
    unique_zips = len(set(d.get('scraped_from_zip', '') for d in dealers if d.get('scraped_from_zip')))
    coverage = unique_zips / total_zips * 100
    print(f"     - ZIP coverage: {unique_zips}/{total_zips} ({coverage:.1f}%)")

    # Data completeness
    has_phone = sum(1 for d in dealers if d.get('phone'))
    has_address = sum(1 for d in dealers if d.get('address_full') or d.get('street'))
    has_name = sum(1 for d in dealers if d.get('name'))

    total = len(dealers)
    print(f"     - Data completeness: {has_phone/total*100:.1f}% (phone), {has_address/total*100:.1f}% (address), {has_name/total*100:.1f}% (name)")

    # Geographic distribution (top 5 states)
    state_counts = {}
    for dealer in dealers:
        state = dealer.get('state', 'Unknown')
        state_counts[state] = state_counts.get(state, 0) + 1

    top_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    state_str = ', '.join(f"{state} ({count})" for state, count in top_states)
    print(f"     - Geographic spread: {state_str}")

    # Fuzzy matches
    if dedup_stats['fuzzy_matches']:
        print(f"\n  → Fuzzy matches found: {len(dedup_stats['fuzzy_matches'])} pairs")

    print(f"\n  ✅ Validation complete")
```

**Step 2: Test validation display**

```bash
./venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.run_22_oem_sequential import display_validation_results, deduplicate_dealers

test_dealers = [
    {'name': 'Dealer 1', 'phone': '555-1111', 'address_full': '123 Main St', 'state': 'CA', 'scraped_from_zip': '94102'},
    {'name': 'Dealer 2', 'phone': '555-2222', 'address_full': '456 Oak Ave', 'state': 'CA', 'scraped_from_zip': '94103'},
    {'name': 'Dealer 3', 'phone': '555-3333', 'address_full': '789 Pine Rd', 'state': 'TX', 'scraped_from_zip': '75201'},
]

deduped, stats = deduplicate_dealers(test_dealers, 'TestOEM')
display_validation_results('TestOEM', deduped, stats, 264)
"
```

Expected: Display coverage, completeness, geographic spread

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add validation metrics display (coverage/completeness/geo)"
```

---

## Task 7: Main Execution Loop

**Files:**
- Modify: `scripts/run_22_oem_sequential.py`

**Step 1: Add main execution function**

```python
def main():
    """
    Main execution loop for 22-OEM sequential scraping.
    """
    # Load configuration
    sys.path.insert(0, str(PROJECT_ROOT))
    from config import ALL_ZIP_CODES
    from scrapers.scraper_factory import ScraperFactory
    from scrapers.base_scraper import ScraperMode

    print("="*80)
    print("22-OEM Sequential Execution System")
    print("="*80)
    print(f"Target: {len(ALL_ZIP_CODES)} ZIP codes")
    print(f"OEMs to scrape: {len(OEM_PRIORITY_ORDER)}")
    print(f"Checkpoint interval: {CHECKPOINT_INTERVAL} ZIPs")
    print()

    # Track execution statistics
    start_time = datetime.now()
    completed_oems = []
    skipped_oems = []

    # Execute OEMs sequentially
    for idx, oem_name in enumerate(OEM_PRIORITY_ORDER):
        # User confirmation
        choice = prompt_user_confirmation(oem_name, idx, len(OEM_PRIORITY_ORDER))

        if choice == 'n':
            print(f"\n❌ Stopped at user request")
            print(f"Completed {len(completed_oems)}/{len(OEM_PRIORITY_ORDER)} OEMs")
            sys.exit(0)

        if choice == 'skip':
            print(f"⏭️  Skipped {oem_name} (user request)\n")
            skipped_oems.append(oem_name)
            continue

        # Delete existing checkpoints (fresh start)
        delete_checkpoints(oem_name)

        # Create scraper
        try:
            scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)
        except Exception as e:
            print(f"❌ Error creating scraper for {oem_name}: {e}")
            print("Options:")
            print("1. Skip this OEM and continue")
            print("2. Exit script (manual debugging)")
            choice = input("Choose (1/2): ").strip()
            if choice == '1':
                skipped_oems.append(oem_name)
                continue
            else:
                sys.exit(1)

        # Scrape with checkpoints
        scraping_log = [f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        try:
            dealers_raw = scraper.scrape_multiple(ALL_ZIP_CODES, checkpoint_interval=CHECKPOINT_INTERVAL)
            scraping_log.append(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            scraping_log.append(f"Raw dealers: {len(dealers_raw)}")

            print(f"\n  ✅ {oem_name} scraping complete: {len(dealers_raw)} dealers from {len(ALL_ZIP_CODES)} ZIPs")

        except Exception as e:
            print(f"\n❌ Error scraping {oem_name}: {e}")
            import traceback
            traceback.print_exc()

            print("\nOptions:")
            print("1. Skip this OEM and continue")
            print("2. Exit script (manual debugging)")
            choice = input("Choose (1/2): ").strip()
            if choice == '1':
                skipped_oems.append(oem_name)
                continue
            else:
                sys.exit(1)

        # Deduplication
        dealers_deduped, dedup_stats = deduplicate_dealers(dealers_raw, oem_name)

        # Validation
        display_validation_results(oem_name, dealers_deduped, dedup_stats, len(ALL_ZIP_CODES))

        # Generate output files
        generate_output_files(oem_name, dealers_raw, dealers_deduped, dedup_stats, scraping_log)

        completed_oems.append(oem_name)
        print()

    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)

    print("="*80)
    print("ALL OEM SCRAPING COMPLETE")
    print("="*80)
    print(f"Duration: {hours}h {minutes}m")
    print(f"OEMs completed: {len(completed_oems)}/{len(OEM_PRIORITY_ORDER)}")
    if skipped_oems:
        print(f"OEMs skipped: {len(skipped_oems)} ({', '.join(skipped_oems)})")

    print("\nNext steps:")
    print("1. Run multi-OEM cross-reference: python3 scripts/analyze_multi_oem_crossovers.py")
    print("2. Generate grandmaster list: python3 scripts/create_grandmaster_list.py")
    print("3. Run ICP scoring: python3 scripts/apply_icp_scoring.py")


if __name__ == "__main__":
    main()
```

**Step 2: Test dry run (user skips all)**

```bash
cd /Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential
chmod +x scripts/run_22_oem_sequential.py
./venv/bin/python3 scripts/run_22_oem_sequential.py
# Type 'skip' for each OEM prompt
```

Expected: Displays all 22 prompts, accepts 'skip', shows final summary

**Step 3: Commit**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "feat: add main execution loop with error handling and summary"
```

---

## Task 8: Final Integration Test

**Files:**
- Test: `scripts/run_22_oem_sequential.py`

**Step 1: Create minimal test with 3 ZIPs**

Create test config override:

```bash
./venv/bin/python3 -c "
# Quick integration test with 3 ZIPs
import sys
sys.path.insert(0, '.')

# Monkey-patch ALL_ZIP_CODES for testing
import config
config.ALL_ZIP_CODES = ['94102', '90210', '75201']  # SF, LA, Dallas

# Import and run with Generac only
from scripts import run_22_oem_sequential
run_22_oem_sequential.OEM_PRIORITY_ORDER = ['Generac']  # Single OEM test
run_22_oem_sequential.main()
# Type 'y' when prompted
"
```

Expected:
- Prompt for Generac
- Scrape 3 ZIPs (~15 seconds)
- Show deduplication stats
- Generate 4 output files
- Display validation results

**Step 2: Verify output files**

```bash
ls -lh output/oem_data/generac/*20251102*
```

Expected: 4 files (.json, .csv, .log, .txt)

**Step 3: Final commit and push**

```bash
git add scripts/run_22_oem_sequential.py
git commit -m "test: verify integration with Generac 3-ZIP test run

✅ Script complete and tested:
- OEM priority order (22 OEMs)
- Checkpoint cleanup (fresh start policy)
- User confirmation prompts (y/n/skip)
- Multi-signal deduplication (phone/domain/fuzzy)
- Output file generation (.json/.csv/.log/report)
- Validation metrics display
- Error handling with user prompts
- Final summary statistics

Ready for production 264-ZIP sweep."

git push -u origin feature/22-oem-sequential-execution
```

---

## Task 9: Documentation Update

**Files:**
- Modify: `docs/plans/2025-11-02-22-oem-sequential-execution.md`

**Step 1: Add implementation status section**

Append to design document:

```markdown

---

## Implementation Status

**Completed:** November 2, 2025

**Implementation:**
- ✅ Master script: `scripts/run_22_oem_sequential.py`
- ✅ OEM priority order (HVAC → Generators → Solar → Battery)
- ✅ Checkpoint cleanup (fresh start policy)
- ✅ User confirmation prompts (y/n/skip)
- ✅ Multi-signal deduplication (phone/domain/fuzzy matching)
- ✅ Output file generation (.json/.csv/.log/report)
- ✅ Validation metrics (coverage/completeness/geo)
- ✅ Error handling with user decision prompts
- ✅ Final summary statistics

**Testing:**
- ✅ Unit tests: checkpoint cleanup, deduplication, file generation
- ✅ Integration test: Generac 3-ZIP test run (15 seconds)

**Production Ready:**
Run with: `./venv/bin/python3 scripts/run_22_oem_sequential.py`

**Estimated Duration:** 13 hours for full 22-OEM × 264-ZIP sweep
```

**Step 2: Commit documentation update**

```bash
git add docs/plans/2025-11-02-22-oem-sequential-execution.md
git commit -m "docs: add implementation status to design document"
```

---

## Execution Summary

**Total Tasks:** 9
**Estimated Time:** 90-120 minutes
**Files Created:** 1 (`scripts/run_22_oem_sequential.py`)
**Files Modified:** 1 (`docs/plans/2025-11-02-22-oem-sequential-execution.md`)

**Key Deliverables:**
1. Sequential execution system with 22-OEM priority order
2. Checkpoint cleanup (fresh start policy)
3. Interactive user confirmation (y/n/skip)
4. Multi-signal deduplication pipeline (97%+ accuracy)
5. Output file generation (.json/.csv/.log/report)
6. Validation metrics display (coverage/completeness/geo)
7. Error handling with user prompts
8. Integration tested with Generac 3-ZIP run

**Production Usage:**
```bash
cd /Users/tmkipper/Desktop/tk_projects/dealer-scraper-mvp/.worktrees/22-oem-sequential
./venv/bin/python3 scripts/run_22_oem_sequential.py
```

Confirm each OEM with 'y', skip with 'skip', exit with 'n'. System saves checkpoints every 25 ZIPs, runs full validation after each OEM, generates 4 output files per OEM.
