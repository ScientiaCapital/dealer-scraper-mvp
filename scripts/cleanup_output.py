#!/usr/bin/env python3
"""
cleanup_output.py - Output folder hygiene for dealer-scraper-mvp

Purpose: Maintain clean, organized output folder structure by:
1. Archiving duplicate/old timestamped files (keeping newest)
2. Moving stray files to proper locations
3. Cleaning up old logs older than N days
4. Removing common garbage files (.DS_Store, __pycache__, etc.)

Usage:
    python scripts/cleanup_output.py              # Dry run (show what would happen)
    python scripts/cleanup_output.py --execute    # Actually perform cleanup
    python scripts/cleanup_output.py --logs-days 7  # Archive logs older than 7 days

Author: Claude + Tim Kipper
Date: 2025-11-26
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "output"
ARCHIVE_DIR = OUTPUT_DIR / "_archive"
MASTER_DIR = OUTPUT_DIR / "master"
SOURCES_DIR = OUTPUT_DIR / "sources"
LOGS_DIR = OUTPUT_DIR / "logs"

# Files that should be in specific locations
EXPECTED_STRUCTURE = {
    "master": ["pipeline.db"],
    "sources/spw_2025": ["spw_lists_*.json"],
    "sources/state_licenses": [],  # Subdirectories for each state
    "sources/amicus": ["amicus_*.json"],
    "sources/oem_networks": [],  # Subdirectories for each OEM
    "analysis": ["*.csv", "*.md"],
    "gtm": ["*.csv", "*.md"],
    "logs": ["*.log"],
}

# Garbage patterns to always remove
GARBAGE_PATTERNS = [
    ".DS_Store",
    "__pycache__",
    "*.pyc",
    ".ipynb_checkpoints",
    "Thumbs.db",
]


def get_timestamp_from_filename(filename: str) -> datetime | None:
    """Extract timestamp from filename like 'spw_lists_20251126_073159.json'"""
    patterns = [
        r'_(\d{8}_\d{6})\.',  # YYYYMMDD_HHMMSS
        r'_(\d{8})\.',        # YYYYMMDD only
        r'(\d{8}_\d{6})_',    # Prefix pattern
        r'(\d{8})_',          # Prefix date only
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            ts = match.group(1)
            try:
                if '_' in ts:
                    return datetime.strptime(ts, '%Y%m%d_%H%M%S')
                else:
                    return datetime.strptime(ts, '%Y%m%d')
            except ValueError:
                continue
    return None


def group_timestamped_files(directory: Path) -> dict[str, list[Path]]:
    """Group files by their base name (without timestamp)"""
    groups = defaultdict(list)

    for file in directory.iterdir():
        if file.is_file() and not file.name.startswith('.'):
            # Remove timestamp to get base name
            base = re.sub(r'_\d{8}(_\d{6})?', '', file.stem)
            groups[base].append(file)

    return groups


def find_stray_files() -> list[tuple[Path, str]]:
    """Find files that are in wrong locations"""
    stray = []

    # Check for old pipeline.db in root output/
    old_db = OUTPUT_DIR / "pipeline.db"
    if old_db.exists():
        stray.append((old_db, "Remove duplicate - master copy is in output/master/"))

    # Check for CSV/JSON files directly in output/ root
    for f in OUTPUT_DIR.iterdir():
        if f.is_file() and f.suffix in ['.csv', '.json'] and f.name != 'pipeline.db':
            stray.append((f, "Move to appropriate sources/ subdirectory"))

    return stray


def find_old_logs(days: int = 14) -> list[Path]:
    """Find log files older than N days"""
    old_logs = []
    cutoff = datetime.now() - timedelta(days=days)

    if not LOGS_DIR.exists():
        return old_logs

    for log_file in LOGS_DIR.glob("*.log"):
        ts = get_timestamp_from_filename(log_file.name)
        if ts and ts < cutoff:
            old_logs.append(log_file)
        elif not ts:
            # If no timestamp, check file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                old_logs.append(log_file)

    return old_logs


def find_duplicate_files() -> list[tuple[Path, Path]]:
    """Find duplicate timestamped files, keeping the newest"""
    duplicates = []  # (old_file, keep_file)

    # Check each source subdirectory
    for source_dir in SOURCES_DIR.iterdir():
        if source_dir.is_dir():
            groups = group_timestamped_files(source_dir)

            for base_name, files in groups.items():
                if len(files) > 1:
                    # Sort by timestamp, newest first
                    sorted_files = sorted(
                        files,
                        key=lambda f: get_timestamp_from_filename(f.name) or datetime.min,
                        reverse=True
                    )
                    keep = sorted_files[0]
                    for old in sorted_files[1:]:
                        duplicates.append((old, keep))

    return duplicates


def find_garbage_files() -> list[Path]:
    """Find garbage files that should be removed"""
    garbage = []

    for pattern in GARBAGE_PATTERNS:
        if '*' in pattern:
            garbage.extend(OUTPUT_DIR.rglob(pattern))
        else:
            garbage.extend(OUTPUT_DIR.rglob(pattern))

    return garbage


def archive_file(file_path: Path, reason: str, execute: bool = False) -> bool:
    """Move file to archive with today's date subdirectory"""
    today = datetime.now().strftime('%Y-%m-%d')
    archive_subdir = ARCHIVE_DIR / f"{today}_cleanup"

    if execute:
        archive_subdir.mkdir(parents=True, exist_ok=True)
        dest = archive_subdir / file_path.name

        # Handle name conflicts
        counter = 1
        while dest.exists():
            dest = archive_subdir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1

        shutil.move(str(file_path), str(dest))
        return True
    return False


def remove_file(file_path: Path, execute: bool = False) -> bool:
    """Remove a garbage file (not archived)"""
    if execute:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        return True
    return False


def run_cleanup(execute: bool = False, logs_days: int = 14, verbose: bool = True):
    """Run the full cleanup process"""

    print("=" * 60)
    print("🧹 Output Folder Cleanup Report")
    print(f"   Mode: {'EXECUTE' if execute else 'DRY RUN (use --execute to apply)'}")
    print("=" * 60)

    total_actions = 0

    # 1. Find and handle stray files
    stray_files = find_stray_files()
    if stray_files:
        print(f"\n📁 Stray files in wrong locations: {len(stray_files)}")
        for file_path, reason in stray_files:
            size = file_path.stat().st_size / (1024 * 1024)  # MB
            print(f"   {'✓' if execute else '○'} {file_path.name} ({size:.1f} MB)")
            print(f"      └─ {reason}")
            if execute:
                archive_file(file_path, reason, execute=True)
            total_actions += 1

    # 2. Find and handle duplicate timestamped files
    duplicates = find_duplicate_files()
    if duplicates:
        print(f"\n📋 Duplicate timestamped files: {len(duplicates)}")
        for old_file, keep_file in duplicates:
            print(f"   {'✓' if execute else '○'} {old_file.name}")
            print(f"      └─ Keeping newer: {keep_file.name}")
            if execute:
                archive_file(old_file, f"Replaced by {keep_file.name}", execute=True)
            total_actions += 1

    # 3. Find and handle old logs
    old_logs = find_old_logs(logs_days)
    if old_logs:
        print(f"\n📜 Log files older than {logs_days} days: {len(old_logs)}")
        for log_file in old_logs[:10]:  # Show first 10
            print(f"   {'✓' if execute else '○'} {log_file.name}")
            if execute:
                archive_file(log_file, f"Older than {logs_days} days", execute=True)
            total_actions += 1
        if len(old_logs) > 10:
            print(f"   ... and {len(old_logs) - 10} more")
            total_actions += len(old_logs) - 10

    # 4. Find and remove garbage files
    garbage = find_garbage_files()
    if garbage:
        print(f"\n🗑️  Garbage files to remove: {len(garbage)}")
        for g in garbage[:10]:  # Show first 10
            print(f"   {'✓' if execute else '○'} {g.relative_to(OUTPUT_DIR)}")
            if execute:
                remove_file(g, execute=True)
            total_actions += 1
        if len(garbage) > 10:
            print(f"   ... and {len(garbage) - 10} more")
            total_actions += len(garbage) - 10

    # Summary
    print("\n" + "=" * 60)
    if total_actions == 0:
        print("✨ Output folder is clean! No actions needed.")
    elif execute:
        print(f"✅ Cleanup complete! {total_actions} items processed.")
        print(f"   Archived files moved to: _archive/{datetime.now().strftime('%Y-%m-%d')}_cleanup/")
    else:
        print(f"📊 Found {total_actions} items that could be cleaned.")
        print("   Run with --execute to apply changes.")
    print("=" * 60)

    return total_actions


def show_structure():
    """Show current output folder structure"""
    print("\n📂 Current Output Structure:")
    print("-" * 40)

    for root, dirs, files in os.walk(OUTPUT_DIR):
        # Skip archive contents
        if '_archive' in root:
            continue

        level = root.replace(str(OUTPUT_DIR), '').count(os.sep)
        indent = '  ' * level
        folder = os.path.basename(root)

        # Count files in this directory
        file_count = len([f for f in files if not f.startswith('.')])
        size_sum = sum(os.path.getsize(os.path.join(root, f)) for f in files) / (1024 * 1024)

        print(f"{indent}📁 {folder}/ ({file_count} files, {size_sum:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description='Cleanup output folder for dealer-scraper-mvp'
    )
    parser.add_argument(
        '--execute', '-x',
        action='store_true',
        help='Actually perform cleanup (default is dry run)'
    )
    parser.add_argument(
        '--logs-days', '-l',
        type=int,
        default=14,
        help='Archive logs older than N days (default: 14)'
    )
    parser.add_argument(
        '--structure', '-s',
        action='store_true',
        help='Show current folder structure'
    )

    args = parser.parse_args()

    if args.structure:
        show_structure()
        return

    run_cleanup(
        execute=args.execute,
        logs_days=args.logs_days
    )


if __name__ == "__main__":
    main()
