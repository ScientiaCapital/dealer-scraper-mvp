#!/usr/bin/env python3
"""
22-OEM Sequential Execution System
Scrapes all 22 OEM networks with checkpoints and full validation.

NOTE: Currently 17 OEMs are production-ready. Missing:
- Generac (needs conversion to unified framework)
- Tesla (needs conversion to unified framework)
- Enphase (needs conversion to unified framework)
- Tigo (placeholder, needs implementation)
"""

import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from fuzzywuzzy import fuzz
from typing import List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import scraper factory
from scrapers.scraper_factory import ScraperFactory
from scrapers.base_scraper import ScraperMode

# OEM Priority Order (HVAC → Generators → Solar → Battery)
# Updated to reflect 18 production-ready OEMs (22 planned, 4 not yet implemented)
OEM_PRIORITY_ORDER = [
    # Tier 1: HVAC Systems (6 OEMs)
    "Carrier",
    "Trane",
    "Lennox",
    "York",
    "Rheem",
    "Mitsubishi",

    # Tier 2: Backup Generators (3 OEMs - Generac needs conversion)
    "Kohler",
    "Cummins",
    "Briggs & Stratton",

    # Tier 3: Solar Inverters (8 OEMs - Enphase/Tigo not ready, ABB/Delta commented out)
    "Fronius",
    "SMA",
    "Sol-Ark",
    "GoodWe",
    "Growatt",
    "Sungrow",
    "SolarEdge",
    # "ABB",      # Commented out in scraper (FIMER acquisition)
    # "Delta",    # Commented out in scraper (no public locator)
    # "Tigo",     # Commented out in scraper (needs implementation)

    # Tier 4: Battery Storage (1 OEM - Tesla needs conversion)
    "SimpliPhi"
    # "Tesla",    # Needs conversion to unified framework
]

# Configuration
CHECKPOINT_INTERVAL = 25
TODAY = datetime.now().strftime("%Y%m%d")


def delete_checkpoints(oem_name: str) -> None:
    """
    Delete all checkpoint files for an OEM (fresh start policy).

    Args:
        oem_name: Name of OEM (e.g., "Carrier", "Briggs & Stratton")
    """
    # Normalize OEM name: lowercase, replace spaces with _, replace & with "and"
    oem_dir_name = oem_name.lower().replace(" ", "_").replace("&", "and")
    checkpoint_dir = PROJECT_ROOT / "output" / "oem_data" / oem_dir_name / "checkpoints"

    if checkpoint_dir.exists():
        checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoint_files:
            print(f"  → Deleting {len(checkpoint_files)} old checkpoints...")
            for checkpoint_file in checkpoint_files:
                checkpoint_file.unlink()
            print(f"  ✓ Checkpoints deleted")
    else:
        print(f"  → No existing checkpoints")


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

        # If phone exists and is a duplicate, skip this dealer
        if normalized_phone and normalized_phone in phone_map:
            stats['phone_dupes'] += 1
            continue  # Skip duplicate dealer

        # Otherwise, keep this dealer
        if normalized_phone:
            phone_map[normalized_phone] = dealer
        dealers_after_phone.append(dealer)

    phone_dedup_pct = (stats['phone_dupes']/initial_count*100) if initial_count > 0 else 0.0
    print(f"     - Phone dedup: {initial_count} → {len(dealers_after_phone)} (-{stats['phone_dupes']}, {phone_dedup_pct:.1f}%)")

    # Phase 2: Domain deduplication
    domain_map = {}
    dealers_after_domain = []

    for dealer in dealers_after_phone:
        domain = dealer.get('domain', '')
        # Extract root domain
        root_domain = domain.replace('www.', '').lower() if domain else ''

        # If domain exists and is a duplicate, skip this dealer
        if root_domain and root_domain in domain_map:
            stats['domain_dupes'] += 1
            continue  # Skip duplicate dealer

        # Otherwise, keep this dealer
        if root_domain:
            domain_map[root_domain] = dealer
        dealers_after_domain.append(dealer)

    domain_dedup_pct = (stats['domain_dupes']/len(dealers_after_phone)*100) if len(dealers_after_phone) > 0 else 0.0
    print(f"     - Domain dedup: {len(dealers_after_phone)} → {len(dealers_after_domain)} (-{stats['domain_dupes']}, {domain_dedup_pct:.1f}%)")

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

    fuzzy_dedup_pct = (stats['fuzzy_dupes']/len(dealers_after_domain)*100) if len(dealers_after_domain) > 0 else 0.0
    print(f"     - Fuzzy name dedup: {len(dealers_after_domain)} → {len(dealers_final)} (-{stats['fuzzy_dupes']}, {fuzzy_dedup_pct:.1f}%)")

    stats['final'] = len(dealers_final)
    total_dedup_rate = ((initial_count - len(dealers_final)) / initial_count * 100) if initial_count > 0 else 0.0
    print(f"  ✓ Deduplication complete: {initial_count} → {len(dealers_final)} (dedup rate: {total_dedup_rate:.1f}%)")

    return dealers_final, stats


def generate_output_files(
    raw_dealers: List[Dict],
    deduped_dealers: List[Dict],
    dedup_stats: Dict,
    oem_name: str,
    output_dir: Path
) -> Dict[str, Path]:
    """
    Generate all output files for an OEM scraping run.

    Generates 4 files:
    1. {oem}_raw_{date}.json - All dealers with duplicates
    2. {oem}_deduped_{date}.csv - Unique dealers after deduplication
    3. {oem}_execution_{date}.log - Execution log
    4. {oem}_dedup_report_{date}.txt - Deduplication report with fuzzy matches

    Args:
        raw_dealers: List of all dealers before deduplication
        deduped_dealers: List of unique dealers after deduplication
        dedup_stats: Statistics from deduplication pipeline
        oem_name: Name of OEM (e.g., "Carrier")
        output_dir: Output directory path

    Returns:
        Dict mapping file type to Path (e.g., {"raw_json": Path(...), "csv": Path(...)})
    """
    print(f"  → Generating output files...")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalize OEM name for filenames
    oem_safe_name = oem_name.lower().replace(" ", "_").replace("&", "and")

    generated_files = {}

    # 1. Raw JSON (all dealers with duplicates)
    raw_json_path = output_dir / f"{oem_safe_name}_raw_{TODAY}.json"
    with open(raw_json_path, 'w') as f:
        json.dump(raw_dealers, f, indent=2)
    generated_files['raw_json'] = raw_json_path
    print(f"     - {raw_json_path.name} ({len(raw_dealers)} dealers)")

    # 2. Deduplicated CSV
    csv_path = output_dir / f"{oem_safe_name}_deduped_{TODAY}.csv"
    if deduped_dealers:
        # Get all unique keys across all dealers
        fieldnames = set()
        for dealer in deduped_dealers:
            fieldnames.update(dealer.keys())
        fieldnames = sorted(fieldnames)

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deduped_dealers)
    else:
        # Create empty CSV with header
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'phone', 'domain', 'address', 'city', 'state', 'zip'])

    generated_files['csv'] = csv_path
    print(f"     - {csv_path.name} ({len(deduped_dealers)} unique)")

    # 3. Execution log
    log_path = output_dir / f"{oem_safe_name}_execution_{TODAY}.log"
    with open(log_path, 'w') as f:
        f.write(f"OEM: {oem_name}\n")
        f.write(f"Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target ZIPs: 264\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"SCRAPING RESULTS\n")
        f.write(f"{'='*60}\n")
        f.write(f"Raw dealers scraped: {len(raw_dealers)}\n")
        f.write(f"Unique dealers (after dedup): {len(deduped_dealers)}\n")
        f.write(f"Deduplication rate: {dedup_stats.get('initial', 0) - dedup_stats.get('final', 0)}/{dedup_stats.get('initial', 0)} ")
        dedup_pct = ((dedup_stats.get('initial', 0) - dedup_stats.get('final', 0)) / dedup_stats.get('initial', 0) * 100) if dedup_stats.get('initial', 0) > 0 else 0.0
        f.write(f"({dedup_pct:.1f}%)\n")

    generated_files['log'] = log_path
    print(f"     - {log_path.name}")

    # 4. Deduplication report
    report_path = output_dir / f"{oem_safe_name}_dedup_report_{TODAY}.txt"
    with open(report_path, 'w') as f:
        f.write(f"{'='*80}\n")
        f.write(f"DEDUPLICATION REPORT: {oem_name}\n")
        f.write(f"{'='*80}\n\n")

        f.write(f"Initial dealers: {dedup_stats.get('initial', 0)}\n")
        f.write(f"Final unique dealers: {dedup_stats.get('final', 0)}\n")
        f.write(f"Total removed: {dedup_stats.get('initial', 0) - dedup_stats.get('final', 0)}\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"DEDUPLICATION BREAKDOWN\n")
        f.write(f"{'='*80}\n\n")

        phone_pct = (dedup_stats.get('phone_dupes', 0) / dedup_stats.get('initial', 1) * 100) if dedup_stats.get('initial', 0) > 0 else 0.0
        f.write(f"Phase 1 - Phone Deduplication:\n")
        f.write(f"  Duplicates removed: {dedup_stats.get('phone_dupes', 0)} ({phone_pct:.1f}%)\n\n")

        domain_pct = (dedup_stats.get('domain_dupes', 0) / dedup_stats.get('initial', 1) * 100) if dedup_stats.get('initial', 0) > 0 else 0.0
        f.write(f"Phase 2 - Domain Deduplication:\n")
        f.write(f"  Duplicates removed: {dedup_stats.get('domain_dupes', 0)} ({domain_pct:.1f}%)\n\n")

        fuzzy_pct = (dedup_stats.get('fuzzy_dupes', 0) / dedup_stats.get('initial', 1) * 100) if dedup_stats.get('initial', 0) > 0 else 0.0
        f.write(f"Phase 3 - Fuzzy Name Matching (≥85% similarity):\n")
        f.write(f"  Duplicates removed: {dedup_stats.get('fuzzy_dupes', 0)} ({fuzzy_pct:.1f}%)\n\n")

        # Fuzzy match details
        if dedup_stats.get('fuzzy_matches'):
            f.write(f"{'='*80}\n")
            f.write(f"FUZZY MATCHES DETECTED ({len(dedup_stats['fuzzy_matches'])} pairs)\n")
            f.write(f"{'='*80}\n\n")

            for i, match in enumerate(dedup_stats['fuzzy_matches'], 1):
                f.write(f"{i}. \"{match['name1']}\" ↔ \"{match['name2']}\" ")
                f.write(f"({match['similarity']}%, {match['state']})\n")
        else:
            f.write(f"No fuzzy name matches detected.\n")

    generated_files['report'] = report_path
    print(f"     - {report_path.name}")

    print(f"  ✓ All output files generated")

    return generated_files


def display_validation_metrics(dealers: List[Dict], oem_name: str, total_target_zips: int = 264) -> Dict:
    """
    Display validation metrics for scraped dealers.

    Metrics displayed:
    1. ZIP coverage: % of target ZIPs that returned results
    2. Data completeness: % of dealers with phone, address, name
    3. Geographic distribution: Dealers per state (top 10)

    Args:
        dealers: List of dealer dictionaries
        oem_name: Name of OEM for logging
        total_target_zips: Total number of target ZIPs (default: 264)

    Returns:
        Dict with validation metrics
    """
    print(f"  → Running validation metrics...")

    metrics = {
        'total_dealers': len(dealers),
        'data_completeness': {},
        'geographic_distribution': {},
        'zip_coverage': {}
    }

    if not dealers:
        print(f"     ⚠️  No dealers to validate")
        return metrics

    # Data Completeness: Check critical fields
    fields_to_check = ['name', 'phone', 'address', 'city', 'state', 'zip']
    for field in fields_to_check:
        non_empty_count = sum(1 for d in dealers if d.get(field, '').strip())
        completeness_pct = (non_empty_count / len(dealers) * 100) if dealers else 0.0
        metrics['data_completeness'][field] = {
            'count': non_empty_count,
            'percentage': completeness_pct
        }

    # Geographic Distribution: Count dealers per state
    state_counts = {}
    for dealer in dealers:
        state = dealer.get('state', '').strip().upper()
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1

    metrics['geographic_distribution'] = state_counts

    # ZIP Coverage: Count unique ZIPs that returned results
    unique_zips = set()
    for dealer in dealers:
        scraped_from_zip = dealer.get('scraped_from_zip', '').strip()
        if scraped_from_zip:
            unique_zips.add(scraped_from_zip)

    zips_with_results = len(unique_zips)
    zip_coverage_pct = (zips_with_results / total_target_zips * 100) if total_target_zips > 0 else 0.0

    metrics['zip_coverage'] = {
        'zips_with_results': zips_with_results,
        'total_target_zips': total_target_zips,
        'coverage_percentage': zip_coverage_pct
    }

    # Display metrics
    print(f"\n  {'=' * 76}")
    print(f"  VALIDATION METRICS: {oem_name}")
    print(f"  {'=' * 76}\n")

    # ZIP Coverage
    coverage_status = "✅" if zip_coverage_pct >= 95.0 else "⚠️"
    print(f"  {coverage_status} ZIP Coverage: {zips_with_results}/{total_target_zips} ({zip_coverage_pct:.1f}%)")
    if zip_coverage_pct < 95.0:
        print(f"     Warning: Coverage below 95% target")

    # Data Completeness
    print(f"\n  📊 Data Completeness:")
    for field in ['name', 'phone', 'address']:
        pct = metrics['data_completeness'][field]['percentage']
        count = metrics['data_completeness'][field]['count']
        status = "✅" if pct >= 95.0 else "⚠️"
        print(f"     {status} {field.capitalize()}: {count}/{len(dealers)} ({pct:.1f}%)")

    # Geographic Distribution (top 10 states)
    print(f"\n  🌎 Geographic Distribution (Top 10):")
    sorted_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for state, count in sorted_states:
        pct = (count / len(dealers) * 100) if dealers else 0.0
        print(f"     {state}: {count} dealers ({pct:.1f}%)")

    print(f"\n  {'=' * 76}\n")

    return metrics


def main():
    """
    Main execution loop: Run all OEMs sequentially with user confirmation.
    """
    print(f"\n{'='*80}")
    print(f"22-OEM SEQUENTIAL EXECUTION SYSTEM")
    print(f"{'='*80}\n")
    print(f"Total OEMs: {len(OEM_PRIORITY_ORDER)}")
    print(f"Target ZIPs: 264 (all 50 states)")
    print(f"Mode: PLAYWRIGHT (local browser automation)")
    print(f"Checkpoint interval: Every {CHECKPOINT_INTERVAL} ZIPs")
    print(f"\n{'='*80}\n")

    # Load ALL_ZIP_CODES from config
    try:
        # Try to import from config module
        from config import ALL_ZIP_CODES
        print(f"✅ Loaded {len(ALL_ZIP_CODES)} ZIP codes from config.py\n")
    except ImportError:
        print(f"❌ ERROR: Could not import ALL_ZIP_CODES from config.py")
        print(f"   Make sure config.py exists in project root with ALL_ZIP_CODES defined")
        sys.exit(1)

    # Statistics tracking
    stats_summary = {
        'completed': [],
        'skipped': [],
        'failed': [],
        'start_time': datetime.now()
    }

    # Sequential OEM execution loop
    for oem_index, oem_name in enumerate(OEM_PRIORITY_ORDER):
        try:
            # Step 1: Delete old checkpoints
            delete_checkpoints(oem_name)

            # Step 2: Prompt user for confirmation
            response = prompt_user_confirmation(oem_name, oem_index, len(OEM_PRIORITY_ORDER))

            if response == 'n':
                print(f"\n⏹️  Stopped at user request\n")
                break
            elif response == 'skip':
                print(f"\n⏭️  Skipped {oem_name}\n")
                stats_summary['skipped'].append(oem_name)
                continue

            # Step 3: Create scraper instance
            print(f"\n  → Creating {oem_name} scraper...")
            try:
                scraper = ScraperFactory.create(oem_name, mode=ScraperMode.PLAYWRIGHT)
                print(f"  ✓ Scraper created")
            except Exception as e:
                print(f"\n  ❌ ERROR: Could not create scraper for {oem_name}")
                print(f"     {str(e)}")

                choice = input("\n  Options: (s)kip this OEM / (q)uit script: ").strip().lower()
                if choice == 's':
                    stats_summary['failed'].append({'oem': oem_name, 'error': str(e)})
                    continue
                else:
                    break

            # Step 4: Scrape all ZIPs with checkpoints
            print(f"\n  → Scraping {len(ALL_ZIP_CODES)} ZIP codes...")
            print(f"     (Checkpoint saves every {CHECKPOINT_INTERVAL} ZIPs)")

            raw_dealers = []
            # TODO: Implement actual scraping with checkpoint system
            # For now, this is a placeholder that will be implemented in Task 8 integration test
            print(f"  ⚠️  Scraping not yet integrated (placeholder for Task 8)")

            # Step 5: Deduplicate dealers
            print(f"\n  → Deduplicating dealers...")
            deduped_dealers, dedup_stats = deduplicate_dealers(raw_dealers, oem_name)

            # Step 6: Generate output files
            oem_dir = PROJECT_ROOT / "output" / "oem_data" / oem_name.lower().replace(" ", "_").replace("&", "and")
            output_files = generate_output_files(
                raw_dealers=raw_dealers,
                deduped_dealers=deduped_dealers,
                dedup_stats=dedup_stats,
                oem_name=oem_name,
                output_dir=oem_dir
            )

            # Step 7: Display validation metrics
            validation_metrics = display_validation_metrics(deduped_dealers, oem_name, total_target_zips=len(ALL_ZIP_CODES))

            # Mark as completed
            stats_summary['completed'].append({
                'oem': oem_name,
                'raw_count': len(raw_dealers),
                'unique_count': len(deduped_dealers),
                'dedup_rate': dedup_stats.get('initial', 0) - dedup_stats.get('final', 0),
                'files': output_files
            })

            print(f"  ✅ {oem_name} complete!\n")

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user (Ctrl+C)")
            print(f"   Progress saved in checkpoints")
            break

        except Exception as e:
            print(f"\n  ❌ UNEXPECTED ERROR in {oem_name}:")
            print(f"     {str(e)}")
            import traceback
            traceback.print_exc()

            choice = input("\n  Options: (s)kip this OEM / (q)uit script: ").strip().lower()
            if choice == 's':
                stats_summary['failed'].append({'oem': oem_name, 'error': str(e)})
                continue
            else:
                break

    # Final summary
    stats_summary['end_time'] = datetime.now()
    duration = stats_summary['end_time'] - stats_summary['start_time']

    print(f"\n{'='*80}")
    print(f"ALL OEM SCRAPING COMPLETE")
    print(f"{'='*80}\n")
    print(f"Duration: {duration}")
    print(f"OEMs completed: {len(stats_summary['completed'])}/{len(OEM_PRIORITY_ORDER)}")
    print(f"OEMs skipped: {len(stats_summary['skipped'])}")
    print(f"OEMs failed: {len(stats_summary['failed'])}")

    if stats_summary['completed']:
        total_raw = sum(oem['raw_count'] for oem in stats_summary['completed'])
        total_unique = sum(oem['unique_count'] for oem in stats_summary['completed'])
        total_dedup_rate = ((total_raw - total_unique) / total_raw * 100) if total_raw > 0 else 0.0

        print(f"\nTotal raw records: {total_raw}")
        print(f"Total unique contractors: {total_unique}")
        print(f"Overall dedup rate: {total_dedup_rate:.1f}%")

    if stats_summary['skipped']:
        print(f"\nSkipped OEMs: {', '.join(stats_summary['skipped'])}")

    if stats_summary['failed']:
        print(f"\nFailed OEMs:")
        for failure in stats_summary['failed']:
            print(f"  - {failure['oem']}: {failure['error']}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
