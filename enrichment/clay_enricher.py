"""
Clay.com Webhook Integration

Sends contractor data to Clay for waterfall enrichment across multiple data sources.

Clay Enrichment Workflow (configured in Clay table):
- Email waterfall: Apollo → Hunter → Snov.io → RocketReach
- Phone validation: Numverify
- Company tech stack: BuiltWith
- Additional social profiles: LinkedIn, Facebook, Twitter

Clay provides more comprehensive enrichment than single-source APIs,
but requires manual setup of the Clay table and enrichment workflow.

Clay Documentation:
https://www.clay.com/docs

Webhook Setup:
1. Create a Clay table
2. Add "Webhook" integration
3. Configure enrichment columns
4. Copy webhook URL to CLAY_WEBHOOK_URL in .env
"""

import os
import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ClayEnrichmentResult:
    """
    Result from Clay enrichment
    """
    # Original data
    contractor_name: str
    contractor_phone: str

    # Additional emails (waterfall enrichment)
    additional_emails: List[str] = None

    # Phone validation
    phone_valid: Optional[bool] = None
    phone_carrier: Optional[str] = None

    # Tech stack
    tech_stack: List[str] = None

    # Social profiles
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None

    # Clay metadata
    clay_enriched: bool = False
    clay_enriched_at: Optional[str] = None

    def __post_init__(self):
        # Initialize lists if None
        if self.additional_emails is None:
            self.additional_emails = []
        if self.tech_stack is None:
            self.tech_stack = []


class ClayEnricher:
    """
    Clay.com webhook client for contractor enrichment.

    Usage:
        enricher = ClayEnricher(webhook_url="https://clay.com/webhooks/...")
        enricher.send_contractors(contractors)

        # Wait for Clay processing (manual trigger or polling)
        # ...

        # Retrieve enriched data
        enriched_data = enricher.retrieve_enriched_data(table_id="...")
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Clay enricher.

        Args:
            webhook_url: Clay table webhook URL. If None, reads from CLAY_WEBHOOK_URL env var.
        """
        self.webhook_url = webhook_url or os.getenv("CLAY_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("Clay webhook URL required. Set CLAY_WEBHOOK_URL in .env or pass to constructor.")

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

    def send_to_clay(self, contractors: List[Dict]) -> Dict:
        """
        Send contractors to Clay via webhook.

        Args:
            contractors: List of contractor dicts to enrich

        Returns:
            Response dict from Clay webhook
        """
        print(f"[Clay] Sending {len(contractors)} contractors to webhook...")

        # Clay webhooks accept JSON array
        payload = contractors

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json() if response.text else {"status": "success"}

            print(f"[Clay] Successfully sent {len(contractors)} contractors")
            print(f"[Clay] Response: {result}")

            return result

        except requests.exceptions.RequestException as e:
            print(f"[Clay] Webhook request failed: {str(e)}")
            raise

    def send_batch(self, contractors: List[Dict], batch_size: int = 100) -> List[Dict]:
        """
        Send contractors in batches to avoid webhook timeouts.

        Args:
            contractors: List of contractor dicts
            batch_size: Number of contractors per batch (default 100)

        Returns:
            List of response dicts from each batch
        """
        results = []

        for i in range(0, len(contractors), batch_size):
            batch = contractors[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(contractors) + batch_size - 1) // batch_size

            print(f"\n[Clay] Sending batch {batch_num}/{total_batches} ({len(batch)} contractors)")

            try:
                result = self.send_to_clay(batch)
                results.append(result)

                # Rate limiting: wait 1 second between batches
                if i + batch_size < len(contractors):
                    time.sleep(1)

            except Exception as e:
                print(f"[Clay] Batch {batch_num} failed: {str(e)}")
                results.append({"status": "error", "error": str(e)})

        print(f"\n[Clay] All batches sent ({len(results)}/{total_batches} succeeded)")
        return results

    @staticmethod
    def prepare_payload(contractors: List[Dict]) -> List[Dict]:
        """
        Prepare contractor data for Clay webhook.

        Extracts only the fields Clay needs for enrichment:
        - Name, domain, phone, address (for company search)
        - Email (for email enrichment)
        - LinkedIn (for social enrichment)

        Args:
            contractors: List of contractor dicts with all fields

        Returns:
            List of simplified dicts for Clay
        """
        clay_payload = []

        for contractor in contractors:
            # Extract essential fields for Clay enrichment
            payload_item = {
                "name": contractor.get("name"),
                "domain": contractor.get("domain"),
                "phone": contractor.get("phone"),
                "website": contractor.get("website"),
                "address": contractor.get("address_full"),
                "city": contractor.get("city"),
                "state": contractor.get("state"),
                "zip": contractor.get("zip"),
                # For matching enriched results back
                "original_phone": contractor.get("phone"),
            }

            # Include Apollo data if available (Clay can use it as fallback)
            if contractor.get("company_linkedin_url"):
                payload_item["linkedin_url"] = contractor.get("company_linkedin_url")

            if contractor.get("decision_maker_emails"):
                payload_item["known_emails"] = contractor.get("decision_maker_emails")

            clay_payload.append(payload_item)

        return clay_payload

    @staticmethod
    def merge_clay_results(
        original_contractors: List[Dict],
        clay_results: List[Dict]
    ) -> List[Dict]:
        """
        Merge Clay enrichment results back into original contractor data.

        Matches by phone number (primary key).

        Args:
            original_contractors: Original contractor dicts
            clay_results: Enriched results from Clay

        Returns:
            List of contractors with Clay data merged
        """
        # Create phone → contractor mapping
        phone_to_contractor = {
            contractor.get("phone"): contractor
            for contractor in original_contractors
        }

        # Merge Clay results
        for clay_result in clay_results:
            phone = clay_result.get("original_phone")

            if phone and phone in phone_to_contractor:
                contractor = phone_to_contractor[phone]

                # Merge Clay fields
                if "enriched_emails" in clay_result:
                    contractor["clay_additional_emails"] = clay_result["enriched_emails"]

                if "phone_valid" in clay_result:
                    contractor["phone_valid"] = clay_result["phone_valid"]

                if "phone_carrier" in clay_result:
                    contractor["phone_carrier"] = clay_result["phone_carrier"]

                if "tech_stack" in clay_result:
                    contractor["tech_stack"] = clay_result["tech_stack"]

                if "facebook_url" in clay_result:
                    contractor["facebook_url"] = clay_result["facebook_url"]

                if "twitter_url" in clay_result:
                    contractor["twitter_url"] = clay_result["twitter_url"]

                contractor["clay_enriched"] = True

        return original_contractors


# Example usage
if __name__ == "__main__":
    # Test Clay webhook
    enricher = ClayEnricher()

    # Sample contractors
    test_contractors = [
        {
            "name": "ABC Electrical Contractors",
            "domain": "abcelectrical.com",
            "phone": "555-123-4567",
            "address_full": "123 Main St, Milwaukee, WI 53202",
        }
    ]

    # Send to Clay
    enricher.send_to_clay(test_contractors)

    print("\n✅ Test webhook sent successfully")
    print("Check your Clay table to see if the data arrived")
