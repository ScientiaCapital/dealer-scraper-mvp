#!/usr/bin/env python3
"""
Push dealer-scraper CSV outputs to sales-agent Supabase.

This script:
1. Reads CSV files from /output/ directory
2. Creates a batch record in scraper_batches
3. Inserts all leads into scraper_imports with full audit trail
4. Marks batch as complete

Usage:
    python push_to_supabase.py                          # Push latest CSV
    python push_to_supabase.py clean_leads_gold.csv     # Push specific file
    python push_to_supabase.py --all                    # Push all unprocessed CSVs
    python push_to_supabase.py --list                   # List available CSVs
"""

import os
import sys
import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# Try to load from local .env first, fall back to hardcoded for testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Sales-agent Supabase credentials (shared database)
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://oyyakkuvvtckocncuwwf.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')

# Output directory
OUTPUT_DIR = Path(__file__).parent / 'output'

# Track which files have been pushed
PUSHED_TRACKER = OUTPUT_DIR / '.pushed_to_supabase.json'


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file for dedup."""
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def load_pushed_tracker() -> dict:
    """Load list of already-pushed files."""
    if PUSHED_TRACKER.exists():
        with open(PUSHED_TRACKER) as f:
            return json.load(f)
    return {}


def save_pushed_tracker(tracker: dict):
    """Save list of pushed files."""
    with open(PUSHED_TRACKER, 'w') as f:
        json.dump(tracker, f, indent=2, default=str)


def detect_source_type(filename: str, first_row: dict) -> str:
    """Detect source type from filename or content."""
    filename_lower = filename.lower()

    if 'oem' in filename_lower or 'cummins' in filename_lower or 'carrier' in filename_lower:
        return 'oem_dealer'
    if 'license' in filename_lower or 'contractor' in filename_lower:
        return 'license_contractor'
    if 'mep' in filename_lower:
        return 'mep_list'
    if first_row.get('source'):
        return first_row.get('source')

    return 'unknown'


def push_csv_to_supabase(csv_path: Path, force: bool = False) -> dict:
    """Push a single CSV file to Supabase."""
    from supabase import create_client

    if not SUPABASE_KEY:
        return {'error': 'SUPABASE_SERVICE_KEY not set in environment'}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    filename = csv_path.name
    file_hash = get_file_hash(csv_path)

    # Check if already pushed
    tracker = load_pushed_tracker()
    if not force and filename in tracker and tracker[filename].get('hash') == file_hash:
        return {
            'status': 'skipped',
            'reason': 'Already pushed (same hash)',
            'batch_id': tracker[filename].get('batch_id')
        }

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return {'error': 'Empty CSV file'}

    # Detect source type
    source_type = detect_source_type(filename, rows[0])

    # Create batch record
    batch_data = {
        'batch_name': filename.replace('.csv', ''),
        'source_type': source_type,
        'source_file': filename,
        'source_project': 'dealer-scraper-mvp',
        'total_records': len(rows),
        'status': 'processing'
    }

    try:
        batch_result = client.table('scraper_batches').insert(batch_data).execute()
        batch_id = batch_result.data[0]['id']
    except Exception as e:
        return {'error': f'Failed to create batch: {e}'}

    # Insert imports
    imported = 0
    duplicates = 0
    errors = 0

    for i, row in enumerate(rows):
        import_data = {
            'batch_id': batch_id,
            'company_name': row.get('company_name', row.get('name', '')),
            'city': row.get('city', ''),
            'state': row.get('state', ''),
            'zip': row.get('zip', ''),
            'phone': row.get('phone', ''),
            'email': row.get('email', ''),
            'website': row.get('website', ''),
            'domain': row.get('domain', ''),
            'source': row.get('source', source_type),
            'tier': row.get('tier', ''),
            'row_number': i + 1,
            'raw_data': row
        }

        # Parse OEM brands if present
        if 'oem_brands' in row or 'OEM_Count' in row:
            oem_list = []
            for key in row:
                if key.startswith('OEM_') and key != 'OEM_Count' and row[key]:
                    oem_list.append(row[key])
            if oem_list:
                import_data['oem_brands'] = oem_list

        try:
            client.table('scraper_imports').insert(import_data).execute()
            imported += 1
        except Exception as e:
            if 'duplicate' in str(e).lower():
                duplicates += 1
            else:
                errors += 1
                print(f"  Row {i+1} error: {e}")

    # Update batch with final counts
    client.table('scraper_batches').update({
        'imported_records': imported,
        'duplicate_records': duplicates,
        'error_records': errors,
        'status': 'completed',
        'completed_at': datetime.utcnow().isoformat(),
        'file_hash': file_hash
    }).eq('id', batch_id).execute()

    # Track this push
    tracker[filename] = {
        'batch_id': batch_id,
        'hash': file_hash,
        'pushed_at': datetime.utcnow().isoformat(),
        'records': imported
    }
    save_pushed_tracker(tracker)

    return {
        'status': 'success',
        'batch_id': batch_id,
        'filename': filename,
        'total': len(rows),
        'imported': imported,
        'duplicates': duplicates,
        'errors': errors
    }


def list_csvs():
    """List all CSV files in output directory."""
    tracker = load_pushed_tracker()
    csvs = sorted(OUTPUT_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)

    print(f"\n📁 CSV files in {OUTPUT_DIR}:\n")
    print(f"{'Status':<10} {'Size':>10} {'Modified':<20} {'Filename'}")
    print("-" * 80)

    for csv_path in csvs[:20]:
        filename = csv_path.name
        size = csv_path.stat().st_size
        mtime = datetime.fromtimestamp(csv_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')

        if filename in tracker:
            status = "✅ pushed"
        else:
            status = "⏳ new"

        size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        print(f"{status:<10} {size_str:>10} {mtime:<20} {filename}")

    print(f"\nTotal: {len(csvs)} files")


def main():
    if len(sys.argv) < 2:
        # Push latest CSV by default
        csvs = sorted(OUTPUT_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)
        if not csvs:
            print("No CSV files found in output/")
            return
        csv_path = csvs[0]
        print(f"📤 Pushing latest: {csv_path.name}")
    elif sys.argv[1] == '--list':
        list_csvs()
        return
    elif sys.argv[1] == '--all':
        csvs = sorted(OUTPUT_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)
        print(f"📤 Pushing {len(csvs)} CSV files...")
        for csv_path in csvs:
            result = push_csv_to_supabase(csv_path)
            status = result.get('status', 'error')
            if status == 'success':
                print(f"  ✅ {csv_path.name}: {result['imported']} imported")
            elif status == 'skipped':
                print(f"  ⏭️  {csv_path.name}: skipped (already pushed)")
            else:
                print(f"  ❌ {csv_path.name}: {result.get('error', 'unknown error')}")
        return
    else:
        csv_path = OUTPUT_DIR / sys.argv[1]
        if not csv_path.exists():
            print(f"❌ File not found: {csv_path}")
            return

    result = push_csv_to_supabase(csv_path)

    if result.get('status') == 'success':
        print(f"""
✅ PUSH SUCCESSFUL
   Batch ID: {result['batch_id']}
   File: {result['filename']}
   Total rows: {result['total']}
   Imported: {result['imported']}
   Duplicates: {result['duplicates']}
   Errors: {result['errors']}

📊 View in sales-agent dashboard or query scraper_imports table
""")
    elif result.get('status') == 'skipped':
        print(f"⏭️  Skipped: {result['reason']}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
