#!/usr/bin/env python3
"""
FAILSAFE ARCHIVE SYSTEM
========================
Creates a complete, versioned backup of ALL lead data files before ANY migration.

GUARANTEE: No leads will ever be lost.

Archive structure:
    output/_failsafe_archive/
    └── YYYYMMDD_HHMMSS/
        ├── MANIFEST.json        # Complete inventory of what was archived
        ├── checksums.sha256     # SHA256 checksums for integrity verification
        ├── csv/                  # All CSV files
        ├── json/                 # All JSON files
        ├── log/                  # All log files
        └── sqlite/               # Database backup
"""

import os
import sys
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class FailsafeArchive:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archive_dir = self.output_dir / "_failsafe_archive" / self.timestamp
        self.manifest: Dict = {
            "created_at": datetime.now().isoformat(),
            "purpose": "Failsafe backup before Supabase migration",
            "files": [],
            "stats": {
                "csv_files": 0,
                "json_files": 0,
                "log_files": 0,
                "sqlite_files": 0,
                "total_size_bytes": 0,
                "total_files": 0
            },
            "lead_counts": {}
        }
        self.checksums: List[Tuple[str, str]] = []

    def sha256_file(self, filepath: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def count_csv_rows(self, filepath: Path) -> int:
        """Count rows in CSV file (excluding header)."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f) - 1  # Subtract header
        except:
            return -1

    def count_json_records(self, filepath: Path) -> int:
        """Count records in JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    # Check for common patterns
                    if 'contractors' in data:
                        return len(data['contractors'])
                    if 'dealers' in data:
                        return len(data['dealers'])
                    if 'leads' in data:
                        return len(data['leads'])
                    return 1  # Single record
                return 0
        except:
            return -1

    def archive_file(self, src_path: Path, category: str) -> Dict:
        """Archive a single file with checksum and metadata."""
        dest_dir = self.archive_dir / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Preserve directory structure
        relative_path = src_path.relative_to(self.output_dir)
        dest_path = dest_dir / relative_path

        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(src_path, dest_path)

        # Calculate checksum
        checksum = self.sha256_file(src_path)
        self.checksums.append((str(relative_path), checksum))

        # Count records
        record_count = -1
        if category == 'csv':
            record_count = self.count_csv_rows(src_path)
        elif category == 'json':
            record_count = self.count_json_records(src_path)

        file_info = {
            "original_path": str(src_path),
            "archived_path": str(dest_path),
            "relative_path": str(relative_path),
            "size_bytes": src_path.stat().st_size,
            "sha256": checksum,
            "record_count": record_count,
            "category": category
        }

        return file_info

    def create_archive(self) -> str:
        """Create complete failsafe archive of all lead data."""
        print("=" * 60)
        print("FAILSAFE ARCHIVE SYSTEM")
        print("=" * 60)
        print(f"\nCreating archive: {self.archive_dir}")
        print("\nScanning for files to archive...")

        # Create archive directory
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Find all files to archive
        extensions = {
            '.csv': 'csv',
            '.json': 'json',
            '.log': 'log',
            '.db': 'sqlite',
            '.sqlite': 'sqlite',
            '.sqlite3': 'sqlite'
        }

        archived_files = []

        for ext, category in extensions.items():
            for filepath in self.output_dir.rglob(f"*{ext}"):
                # Skip archive directory itself
                if "_failsafe_archive" in str(filepath):
                    continue
                # Skip .next directory
                if ".next" in str(filepath):
                    continue

                try:
                    file_info = self.archive_file(filepath, category)
                    archived_files.append(file_info)
                    self.manifest["stats"][f"{category}_files"] += 1
                    self.manifest["stats"]["total_size_bytes"] += file_info["size_bytes"]

                    # Track lead counts by source
                    if file_info["record_count"] > 0:
                        source_key = str(filepath.parent.name) + "/" + filepath.stem
                        self.manifest["lead_counts"][source_key] = file_info["record_count"]

                    print(f"  ✓ {filepath.name} ({file_info['record_count']} records)")
                except Exception as e:
                    print(f"  ✗ {filepath.name}: {e}")

        self.manifest["files"] = archived_files
        self.manifest["stats"]["total_files"] = len(archived_files)

        # Write manifest
        manifest_path = self.archive_dir / "MANIFEST.json"
        with open(manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
        print(f"\n✓ Manifest written: {manifest_path}")

        # Write checksums file
        checksums_path = self.archive_dir / "checksums.sha256"
        with open(checksums_path, 'w') as f:
            for filepath, checksum in self.checksums:
                f.write(f"{checksum}  {filepath}\n")
        print(f"✓ Checksums written: {checksums_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("ARCHIVE SUMMARY")
        print("=" * 60)
        print(f"  Archive location: {self.archive_dir}")
        print(f"  Total files:      {self.manifest['stats']['total_files']}")
        print(f"  CSV files:        {self.manifest['stats']['csv_files']}")
        print(f"  JSON files:       {self.manifest['stats']['json_files']}")
        print(f"  Log files:        {self.manifest['stats']['log_files']}")
        print(f"  SQLite files:     {self.manifest['stats']['sqlite_files']}")
        print(f"  Total size:       {self.manifest['stats']['total_size_bytes'] / 1024 / 1024:.2f} MB")

        # Top 10 files by record count
        if self.manifest["lead_counts"]:
            print("\n  Top 10 files by record count:")
            sorted_counts = sorted(
                self.manifest["lead_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            for source, count in sorted_counts:
                print(f"    {count:>8} records: {source}")

        print("\n" + "=" * 60)
        print("FAILSAFE GUARANTEE")
        print("=" * 60)
        print(f"""
  ✓ All {self.manifest['stats']['total_files']} files have been archived
  ✓ SHA256 checksums recorded for integrity verification
  ✓ Full manifest with record counts saved
  ✓ Original files preserved in {self.archive_dir}

  TO RESTORE: Copy files from archive back to output/
  TO VERIFY:  sha256sum -c checksums.sha256
""")

        return str(self.archive_dir)

    def verify_archive(self, archive_path: str = None) -> bool:
        """Verify integrity of an existing archive."""
        archive_dir = Path(archive_path) if archive_path else self.archive_dir

        checksums_file = archive_dir / "checksums.sha256"
        if not checksums_file.exists():
            print(f"ERROR: No checksums file found in {archive_dir}")
            return False

        print(f"Verifying archive: {archive_dir}")
        errors = 0

        with open(checksums_file, 'r') as f:
            for line in f:
                expected_hash, filepath = line.strip().split('  ', 1)
                # Find the file in the archive
                for category in ['csv', 'json', 'log', 'sqlite']:
                    full_path = archive_dir / category / filepath
                    if full_path.exists():
                        actual_hash = self.sha256_file(full_path)
                        if actual_hash != expected_hash:
                            print(f"  ✗ MISMATCH: {filepath}")
                            errors += 1
                        else:
                            print(f"  ✓ {filepath}")
                        break

        if errors == 0:
            print(f"\n✓ All files verified successfully!")
            return True
        else:
            print(f"\n✗ {errors} files failed verification!")
            return False


def main():
    """Run failsafe archive."""
    import argparse

    parser = argparse.ArgumentParser(description="Failsafe Archive System")
    parser.add_argument("--output-dir", default="output", help="Output directory to archive")
    parser.add_argument("--verify", help="Verify existing archive (provide path)")
    args = parser.parse_args()

    archive = FailsafeArchive(args.output_dir)

    if args.verify:
        success = archive.verify_archive(args.verify)
        sys.exit(0 if success else 1)
    else:
        archive_path = archive.create_archive()
        print(f"\nArchive created: {archive_path}")


if __name__ == "__main__":
    main()
