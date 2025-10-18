"""
Close CRM Upload Script

Imports enriched contractor data as leads into Close CRM and creates state-based Smart Views.

Prerequisites (setup in Close CRM UI first):
1. Create custom fields:
   - Coperniq_Score (Number, 0-100)
   - Priority_Tier (Dropdown: HIGH, MEDIUM, LOW)
   - Generac_Tier (Dropdown: Premier, Elite Plus, Elite, Standard)
   - Employee_Count (Number)
   - Revenue_Estimate (Text)
   - ITC_Urgency (Dropdown: CRITICAL, HIGH, MEDIUM, LOW)
   - SREC_State (Checkbox)
   - OEM_Certifications (Text)

2. Get API key from Close CRM Settings → API → Generate Key

Usage:
    # Import Apollo+Clay enriched contractors
    python scripts/upload_to_close.py --input output/generac_master_list_apollo.json

    # Create Smart Views only (skip import)
    python scripts/upload_to_close.py --create-views-only

    # Import with custom batch size
    python scripts/upload_to_close.py \
        --input output/generac_master_list_apollo.json \
        --batch-size 50

Requires:
    - CLOSE_API_KEY in .env
    - Custom fields created in Close CRM UI (see prerequisites above)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict
from crm.close_importer import CloseImporter


def load_contractors(input_path: str) -> List[Dict]:
    """
    Load enriched contractors from JSON file.

    Args:
        input_path: Path to JSON file with enriched contractor data

    Returns:
        List of contractor dicts
    """
    print(f"[Load] Reading contractors from {input_path}")

    with open(input_path, "r") as f:
        data = json.load(f)

    # Handle both array format and dict format
    if isinstance(data, list):
        contractors = data
    elif isinstance(data, dict) and "dealers" in data:
        contractors = data["dealers"]
    else:
        raise ValueError("Invalid input format. Expected array or dict with 'dealers' key.")

    print(f"[Load] Loaded {len(contractors)} contractors")

    # Check for enrichment
    apollo_enriched = sum(1 for c in contractors if c.get("apollo_enriched"))
    clay_enriched = sum(1 for c in contractors if c.get("clay_enriched"))

    print(f"       Apollo enriched: {apollo_enriched}/{len(contractors)}")
    print(f"       Clay enriched: {clay_enriched}/{len(contractors)}")

    return contractors


def import_leads(
    contractors: List[Dict],
    close_importer: CloseImporter
) -> Dict:
    """
    Import contractors as leads into Close CRM.

    Args:
        contractors: List of enriched contractor dicts
        close_importer: Close CRM API client

    Returns:
        Summary dict with import results
    """
    print(f"\n{'='*60}")
    print(f"Importing {len(contractors)} contractors to Close CRM")
    print(f"{'='*60}\n")

    # Bulk import
    results = close_importer.bulk_import(contractors)

    # Summary
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    summary = {
        "total": len(results),
        "success": success_count,
        "failed": fail_count,
        "success_rate": (success_count / len(results) * 100) if results else 0,
        "imported_at": datetime.now().isoformat(),
        "failed_contractors": [
            {
                "name": r.contractor_name,
                "phone": r.contractor_phone,
                "error": r.error
            }
            for r in results if not r.success
        ]
    }

    return summary


def create_smart_views(close_importer: CloseImporter) -> Dict:
    """
    Create state-based Smart Views in Close CRM.

    Args:
        close_importer: Close CRM API client

    Returns:
        Summary dict with Smart View creation results
    """
    print(f"\n{'='*60}")
    print(f"Creating State-Based Smart Views")
    print(f"{'='*60}\n")

    # Create 6 state views
    views = close_importer.create_state_smart_views()

    # Summary
    success_count = sum(1 for v in views.values() if v is not None)

    summary = {
        "total": len(views),
        "created": success_count,
        "failed": len(views) - success_count,
        "views": views,
        "created_at": datetime.now().isoformat(),
    }

    return summary


def save_report(import_summary: Dict, views_summary: Dict, output_path: str):
    """
    Save import report to JSON file.

    Args:
        import_summary: Import results
        views_summary: Smart View results
        output_path: Path to output JSON file
    """
    print(f"\n[Save] Writing import report to {output_path}")

    report = {
        "import": import_summary,
        "smart_views": views_summary,
        "generated_at": datetime.now().isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[Save] Report saved")


def main():
    parser = argparse.ArgumentParser(
        description="Import enriched contractors to Close CRM with state-based Smart Views"
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON file with enriched contractor data"
    )
    parser.add_argument(
        "--create-views-only",
        action="store_true",
        help="Only create Smart Views (skip import)"
    )
    parser.add_argument(
        "--output-report",
        help="Path to output report JSON (default: output/close_import_report.json)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.create_views_only and not args.input:
        print("Error: --input required unless --create-views-only is specified")
        sys.exit(1)

    # Determine output report path
    output_report_path = args.output_report or "output/close_import_report.json"

    # Initialize Close CRM importer
    try:
        importer = CloseImporter()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add CLOSE_API_KEY to your .env file")
        print("\nHow to get Close CRM API key:")
        print("  1. Go to https://app.close.com/settings/api/")
        print("  2. Click 'Generate API Key'")
        print("  3. Copy key to .env as CLOSE_API_KEY")
        sys.exit(1)

    import_summary = None
    views_summary = None

    # Import leads (unless --create-views-only)
    if not args.create_views_only:
        try:
            contractors = load_contractors(args.input)
        except FileNotFoundError:
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in input file: {args.input}")
            sys.exit(1)

        import_summary = import_leads(contractors, importer)

    # Create Smart Views
    views_summary = create_smart_views(importer)

    # Save report
    if import_summary or views_summary:
        os.makedirs(os.path.dirname(output_report_path) if os.path.dirname(output_report_path) else ".", exist_ok=True)
        save_report(import_summary or {}, views_summary or {}, output_report_path)

    # Final summary
    print(f"\n{'='*60}")
    print(f"Close CRM Upload Complete!")
    print(f"{'='*60}")

    if import_summary:
        print(f"Leads imported: {import_summary['success']}/{import_summary['total']}")
        print(f"Success rate: {import_summary['success_rate']:.1f}%")

        if import_summary['failed'] > 0:
            print(f"\n⚠️  {import_summary['failed']} leads failed to import")
            print(f"   Check report for details: {output_report_path}")

    if views_summary:
        print(f"Smart Views created: {views_summary['created']}/{views_summary['total']}")

    print(f"\nReport saved to: {output_report_path}")

    print(f"\n✅ Next steps:")
    print(f"  1. Go to Close CRM: https://app.close.com")
    print(f"  2. Check 'Leads' to see imported contractors")
    print(f"  3. Use Smart Views to filter by state (CA, TX, PA, MA, NJ, FL)")
    print(f"  4. Sort by 'Coperniq Score' to prioritize HIGH prospects (80-100)")
    print(f"  5. Start outreach with decision-maker emails from Apollo!")


if __name__ == "__main__":
    main()
