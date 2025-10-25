"""
Apollo.io Enrichment Script

Enriches contractor data with company information from Apollo.io:
- Employee count (for accurate commercial capability scoring)
- Revenue estimate
- Decision-maker emails (for outreach)
- LinkedIn profiles (for research)

Usage:
    python scripts/enrich_with_apollo.py --input output/generac_master_list.json

    # With custom output
    python scripts/enrich_with_apollo.py \
        --input output/generac_master_list.json \
        --output output/generac_enriched_apollo.json

    # Skip contacts to save API calls
    python scripts/enrich_with_apollo.py \
        --input output/generac_master_list.json \
        --no-contacts

Requires:
    - APOLLO_API_KEY in .env
    - Input JSON file with contractor data
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict
from enrichment.apollo_enricher import ApolloEnricher, ApolloCompanyData


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


def enrich_contractors(
    contractors: List[Dict],
    apollo_enricher: ApolloEnricher,
    include_contacts: bool = True
) -> List[Dict]:
    """
    Enrich contractors with Apollo data.

    Args:
        contractors: List of contractor dicts
        apollo_enricher: Apollo API client
        include_contacts: Whether to fetch decision-maker contacts

    Returns:
        List of enriched contractor dicts
    """
    enriched_contractors = []

    for i, contractor in enumerate(contractors, 1):
        print(f"\n[{i}/{len(contractors)}] Enriching: {contractor.get('name')}")

        # Get company data from Apollo
        apollo_data = apollo_enricher.enrich_company(
            domain=contractor.get("domain"),
            name=contractor.get("name"),
            location=f"{contractor.get('city')}, {contractor.get('state')}",
            include_contacts=include_contacts
        )

        # Update contractor with Apollo data
        if apollo_data:
            contractor["employee_count"] = apollo_data.employee_count
            contractor["employee_range"] = apollo_data.employee_range
            contractor["estimated_annual_revenue"] = apollo_data.estimated_annual_revenue
            contractor["decision_maker_emails"] = apollo_data.decision_maker_emails
            contractor["decision_maker_names"] = apollo_data.decision_maker_names
            contractor["company_linkedin_url"] = apollo_data.company_linkedin_url
            contractor["contact_linkedin_urls"] = apollo_data.contact_linkedin_urls
            contractor["industry"] = apollo_data.industry
            contractor["founded_year"] = apollo_data.founded_year
            contractor["apollo_enriched"] = True
            contractor["apollo_enriched_at"] = datetime.now().isoformat()

            print(f"  ✅ Enriched with Apollo data")
            print(f"     Employees: {apollo_data.employee_count}")
            print(f"     Revenue: {apollo_data.estimated_annual_revenue}")
            print(f"     Contacts: {len(apollo_data.decision_maker_emails)} emails")
        else:
            contractor["apollo_enriched"] = False
            contractor["apollo_enriched_at"] = datetime.now().isoformat()
            print(f"  ⚠️  Not found in Apollo database")

        enriched_contractors.append(contractor)

    return enriched_contractors


def save_enriched_data(contractors: List[Dict], output_path: str):
    """
    Save enriched contractors to JSON file.

    Args:
        contractors: List of enriched contractor dicts
        output_path: Path to output JSON file
    """
    print(f"\n[Save] Writing enriched data to {output_path}")

    output_data = {
        "dealers": contractors,
        "total_count": len(contractors),
        "enriched_count": sum(1 for c in contractors if c.get("apollo_enriched")),
        "enriched_at": datetime.now().isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"[Save] Saved {len(contractors)} contractors")
    print(f"       {output_data['enriched_count']} enriched with Apollo")
    print(f"       {len(contractors) - output_data['enriched_count']} not found in Apollo")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich contractor data with Apollo.io company information"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON file with contractor data"
    )
    parser.add_argument(
        "--output",
        help="Path to output JSON file (default: input_path with '_apollo' suffix)"
    )
    parser.add_argument(
        "--no-contacts",
        action="store_true",
        help="Skip fetching decision-maker contacts (saves API calls)"
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Add '_apollo' suffix to input filename
        input_base = args.input.rsplit(".", 1)[0]
        output_path = f"{input_base}_apollo.json"

    # Initialize Apollo enricher
    try:
        enricher = ApolloEnricher()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add APOLLO_API_KEY to your .env file")
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

    # Enrich contractors
    include_contacts = not args.no_contacts
    enriched_contractors = enrich_contractors(contractors, enricher, include_contacts)

    # Save results
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    save_enriched_data(enriched_contractors, output_path)

    print(f"\n✅ Enrichment complete! Output saved to: {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Review enriched data: cat {output_path}")
    print(f"  2. Re-score with updated employee counts")
    print(f"  3. Enrich with Clay (optional): python scripts/enrich_with_clay.py --input {output_path}")


if __name__ == "__main__":
    main()
