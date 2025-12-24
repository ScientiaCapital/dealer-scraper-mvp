#!/usr/bin/env python3
"""
Sync Contractor Data to Close CRM

Syncs contractor data from SQLite/Supabase to Close CRM with
OEM certifications and state licenses as custom fields.

Usage:
    # Dry run with 5 records
    python scripts/sync_to_close_crm.py --dry-run --limit 5

    # Sync Texas multi-OEM contractors
    python scripts/sync_to_close_crm.py --state TX --min-oems 2

    # Full sync from SQLite
    python scripts/sync_to_close_crm.py --source sqlite

    # Create custom fields only
    python scripts/sync_to_close_crm.py --setup-fields-only
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crm.close_sync_service import CloseSyncService
from crm.close_field_manager import CloseFieldManager


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(
        description="Sync contractor data to Close CRM with OEM/license tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 5 records
  python scripts/sync_to_close_crm.py --dry-run --limit 5

  # Sync Texas multi-OEM contractors
  python scripts/sync_to_close_crm.py --state TX --min-oems 2

  # Full sync to Close CRM
  python scripts/sync_to_close_crm.py --source sqlite
        """
    )

    # Source selection
    parser.add_argument(
        "--source",
        choices=["sqlite", "supabase"],
        default="sqlite",
        help="Data source (default: sqlite)"
    )

    # Execution modes
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of records to sync (for testing)"
    )

    # Filters
    parser.add_argument(
        "--state",
        help="Filter by state code (e.g., TX, CA)"
    )
    parser.add_argument(
        "--oem",
        help="Filter by OEM name (e.g., Generac)"
    )
    parser.add_argument(
        "--min-oems",
        type=int,
        default=0,
        help="Minimum OEM certification count"
    )

    # Assignment
    parser.add_argument(
        "--owner",
        help="Email of lead owner in Close CRM"
    )

    # Setup modes
    parser.add_argument(
        "--setup-fields-only",
        action="store_true",
        help="Only create custom fields (no sync)"
    )
    parser.add_argument(
        "--create-views-only",
        action="store_true",
        help="Only create Smart Views (no sync)"
    )

    # Output
    parser.add_argument(
        "--report",
        default="output/close_sync_report.json",
        help="Path for sync report JSON"
    )

    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Close CRM Sync - Contractor Data Integration")
    print("=" * 60)

    # Check for API key
    if not os.getenv("CLOSE_API_KEY"):
        if not args.dry_run:
            print("\n ERROR: CLOSE_API_KEY not set in environment")
            print("   Set it in .env or export CLOSE_API_KEY=your_key")
            print("   Use --dry-run to preview without API key\n")
            sys.exit(1)
        else:
            print("\n Note: Running in dry-run mode (no API key required)\n")

    # Setup fields only mode
    if args.setup_fields_only:
        print("\n Creating custom fields in Close CRM...\n")
        manager = CloseFieldManager()
        fields = manager.ensure_required_fields()

        print("\n Custom fields ensured:")
        for name, info in fields.items():
            print(f"   - {name}: {info.get('type')} (ID: {info.get('id', 'N/A')})")

        print("\n Done!\n")
        return

    # Create sync service
    service = CloseSyncService(
        source=args.source,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    # Display configuration
    print(f"\n Configuration:")
    print(f"   Source: {args.source}")
    print(f"   Dry Run: {args.dry_run}")
    print(f"   Limit: {args.limit or 'None'}")
    print(f"   State Filter: {args.state or 'None'}")
    print(f"   OEM Filter: {args.oem or 'None'}")
    print(f"   Min OEMs: {args.min_oems}")
    print(f"   Report: {args.report}")
    print()

    # Run sync
    print(" Starting sync...\n")

    report = service.run_sync(
        state_filter=args.state,
        oem_filter=args.oem,
        min_oem_count=args.min_oems,
        owner_email=args.owner,
    )

    # Display summary
    print("\n" + "=" * 60)
    print(" Sync Summary")
    print("=" * 60)
    print(f"   Sync ID: {report.sync_id}")
    print(f"   Duration: {report.duration_seconds:.1f}s")
    print(f"   Total Extracted: {report.summary['total_extracted']}")

    if args.dry_run:
        print(f"\n   [DRY RUN] Would Create: {len(report.would_create)}")
        print(f"   [DRY RUN] Would Update: {len(report.would_update)}")
    else:
        print(f"\n   Created: {report.summary['created']}")
        print(f"   Updated: {report.summary['updated']}")
        print(f"   Skipped: {report.summary['skipped']}")
        print(f"   Failed: {report.summary['failed']}")

    if report.errors:
        print(f"\n   Errors: {len(report.errors)}")
        for err in report.errors[:5]:
            print(f"      - {err['company_name']}: {err['error']}")
        if len(report.errors) > 5:
            print(f"      ... and {len(report.errors) - 5} more")

    print("=" * 60 + "\n")

    # Save report
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f" Report saved: {report_path}\n")


if __name__ == "__main__":
    main()
