"""
Clay.com Enrichment Script

Sends contractor data to Clay for waterfall enrichment across multiple data sources.

Clay adds:
- Additional emails (Apollo → Hunter → Snov.io waterfall)
- Phone validation (Numverify)
- Company tech stack (BuiltWith)
- Social profiles (Facebook, Twitter)

This script sends data TO Clay. Retrieving enriched data requires either:
1. Manual export from Clay table (download CSV)
2. Clay API integration (future enhancement)

Usage:
    # Send Apollo-enriched contractors to Clay
    python scripts/enrich_with_clay.py --input output/generac_master_list_apollo.json

    # With batch size control
    python scripts/enrich_with_clay.py \
        --input output/generac_master_list_apollo.json \
        --batch-size 50

Requires:
    - CLAY_WEBHOOK_URL in .env (from Clay table → Integrations → Webhook)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict
from enrichment.clay_enricher import ClayEnricher


def load_contractors(input_path: str) -> List[Dict]:
    """
    Load contractors from JSON file.

    Args:
        input_path: Path to JSON file with contractor data

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
    return contractors


def send_to_clay(
    contractors: List[Dict],
    clay_enricher: ClayEnricher,
    batch_size: int = 100
) -> Dict:
    """
    Send contractors to Clay via webhook.

    Args:
        contractors: List of contractor dicts
        clay_enricher: Clay webhook client
        batch_size: Number of contractors per batch

    Returns:
        Summary dict with results
    """
    # Prepare payload (extract only fields Clay needs)
    clay_payload = clay_enricher.prepare_payload(contractors)

    print(f"\n[Clay] Prepared {len(clay_payload)} contractors for enrichment")

    # Send in batches
    results = clay_enricher.send_batch(clay_payload, batch_size=batch_size)

    # Summary
    success_count = sum(1 for r in results if r.get("status") != "error")
    error_count = len(results) - success_count

    summary = {
        "total_contractors": len(contractors),
        "batches_sent": len(results),
        "batches_succeeded": success_count,
        "batches_failed": error_count,
        "sent_at": datetime.now().isoformat(),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Send contractor data to Clay for waterfall enrichment"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON file with contractor data (Apollo-enriched recommended)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of contractors per batch (default: 100)"
    )

    args = parser.parse_args()

    # Initialize Clay enricher
    try:
        enricher = ClayEnricher()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add CLAY_WEBHOOK_URL to your .env file")
        print("\nHow to get Clay webhook URL:")
        print("  1. Go to https://clay.com")
        print("  2. Create or open a table")
        print("  3. Click 'Integrations' → 'Webhook'")
        print("  4. Copy webhook URL to .env as CLAY_WEBHOOK_URL")
        sys.exit(1)

    # Load contractors
    try:
        contractors = load_contractors(args.input)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in input file: {args.input}")
        sys.exit(1)

    # Send to Clay
    summary = send_to_clay(contractors, enricher, batch_size=args.batch_size)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Clay Enrichment Summary")
    print(f"{'='*60}")
    print(f"Total contractors sent: {summary['total_contractors']}")
    print(f"Batches sent: {summary['batches_sent']}")
    print(f"Batches succeeded: {summary['batches_succeeded']}")
    print(f"Batches failed: {summary['batches_failed']}")
    print(f"Sent at: {summary['sent_at']}")
    print(f"{'='*60}\n")

    if summary['batches_failed'] > 0:
        print("⚠️  Some batches failed. Check logs above for details.")
    else:
        print("✅ All contractors sent to Clay successfully!")

    print(f"\nNext steps:")
    print(f"  1. Go to your Clay table: https://clay.com/tables")
    print(f"  2. Wait for Clay to process enrichments (1-5 minutes)")
    print(f"  3. Review enriched data in Clay columns")
    print(f"  4. Export enriched CSV from Clay")
    print(f"  5. (Future) Use Clay API to retrieve enriched data programmatically")


if __name__ == "__main__":
    main()
