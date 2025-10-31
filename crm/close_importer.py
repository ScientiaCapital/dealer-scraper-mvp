"""
Close CRM API Client

Imports enriched contractor data as leads into Close CRM.

Features:
- Bulk lead import with custom fields
- Contact creation (decision-maker emails/phones)
- State-based Smart View creation
- Error handling and retry logic

Close CRM API Documentation:
https://developer.close.com/

Custom Fields Required (setup in Close CRM UI first):
- custom.Coperniq_Score (Number, 0-100)
- custom.Priority_Tier (Dropdown: HIGH/MEDIUM/LOW)
- custom.Generac_Tier (Dropdown: Premier/Elite Plus/Elite/Standard)
- custom.Employee_Count (Number)
- custom.Revenue_Estimate (Text)
- custom.ITC_Urgency (Dropdown: CRITICAL/HIGH/MEDIUM/LOW)
- custom.SREC_State (Checkbox: Yes/No)
- custom.OEM_Certifications (Text: comma-separated)
"""

import os
import time
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CloseLeadResult:
    """
    Result of lead import attempt
    """
    contractor_name: str
    contractor_phone: str
    success: bool
    lead_id: Optional[str] = None
    error: Optional[str] = None


class CloseImporter:
    """
    Close CRM API client for contractor lead import.

    Usage:
        importer = CloseImporter(api_key="your_close_api_key")

        # Import contractors
        results = importer.bulk_import(contractors)

        # Create Smart Views
        views = importer.create_state_smart_views()

        print(f"Imported {sum(r.success for r in results)} leads")
    """

    API_BASE_URL = "https://api.close.com/api/v1"
    DEFAULT_RATE_LIMIT = 30  # calls per second

    # SREC states for Smart View creation
    SREC_STATES = ["CA", "TX", "PA", "MA", "NJ", "FL"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Close CRM importer.

        Args:
            api_key: Close CRM API key. If None, reads from CLOSE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CLOSE_API_KEY")
        if not self.api_key:
            raise ValueError("Close API key required. Set CLOSE_API_KEY in .env or pass to constructor.")

        self.session = requests.Session()
        self.session.auth = (self.api_key, "")  # Close uses HTTP Basic Auth with API key as username
        self.session.headers.update({
            "Content-Type": "application/json"
        })

        # Rate limiting
        self.call_timestamps = []
        self.rate_limit = self.DEFAULT_RATE_LIMIT

    def _rate_limit_check(self):
        """
        Enforce rate limiting (30 calls per second).
        Blocks until safe to make next API call.
        """
        now = time.time()
        # Remove timestamps older than 1 second
        self.call_timestamps = [ts for ts in self.call_timestamps if now - ts < 1]

        if len(self.call_timestamps) >= self.rate_limit:
            # Wait until oldest call is 1 second old
            sleep_time = 1 - (now - self.call_timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Retry rate limit check
                self._rate_limit_check()

        self.call_timestamps.append(now)

    def create_lead(self, contractor: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a lead in Close CRM from contractor data.

        Args:
            contractor: Contractor dict with all enrichment data

        Returns:
            Tuple of (success, lead_id, error_message)
        """
        self._rate_limit_check()

        # Build lead payload
        lead_payload = {
            "name": contractor.get("name", ""),
            "url": contractor.get("website", ""),
            "description": self._build_description(contractor),
            "status_label": "Lead",  # Default status
            "addresses": [
                {
                    "address_1": contractor.get("street", ""),
                    "city": contractor.get("city", ""),
                    "state": contractor.get("state", ""),
                    "zipcode": contractor.get("zip", ""),
                    "country": "US"
                }
            ],
        }

        # Add custom fields
        lead_payload["custom"] = self._build_custom_fields(contractor)

        # Add contacts (decision-makers)
        contacts = self._build_contacts(contractor)
        if contacts:
            lead_payload["contacts"] = contacts

        try:
            response = self.session.post(
                f"{self.API_BASE_URL}/lead/",
                json=lead_payload,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            lead_id = result.get("id")

            print(f"  ✅ Created lead: {contractor.get('name')} (ID: {lead_id})")

            return True, lead_id, None

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            print(f"  ❌ Failed to create lead: {contractor.get('name')} - {error_msg}")
            return False, None, error_msg

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            print(f"  ❌ Failed to create lead: {contractor.get('name')} - {error_msg}")
            return False, None, error_msg

    @staticmethod
    def _build_description(contractor: Dict) -> str:
        """Build lead description from contractor data"""
        tier = contractor.get("tier", "Standard")
        oem_sources = contractor.get("oem_sources", [])
        oem_str = ", ".join(oem_sources) if isinstance(oem_sources, list) else str(oem_sources)

        description_parts = [
            f"Tier: {tier}",
            f"OEM Certifications: {oem_str}",
        ]

        # Add score if available
        if contractor.get("score"):
            description_parts.append(f"Coperniq Score: {contractor['score']}")

        return " | ".join(description_parts)

    @staticmethod
    def _build_custom_fields(contractor: Dict) -> Dict:
        """Build custom fields dict for Close CRM"""
        custom_fields = {}

        # Coperniq Score (from scoring)
        if "score" in contractor:
            custom_fields["Coperniq_Score"] = contractor["score"]

        # Priority Tier
        if "priority_tier" in contractor:
            custom_fields["Priority_Tier"] = contractor["priority_tier"]

        # Generac Tier
        if "tier" in contractor:
            custom_fields["Generac_Tier"] = contractor["tier"]

        # Employee Count (from Apollo)
        if "employee_count" in contractor:
            custom_fields["Employee_Count"] = contractor["employee_count"]

        # Revenue Estimate (from Apollo)
        if "estimated_annual_revenue" in contractor:
            custom_fields["Revenue_Estimate"] = contractor["estimated_annual_revenue"]

        # ITC Urgency
        if contractor.get("srec_metadata", {}).get("urgency"):
            custom_fields["ITC_Urgency"] = contractor["srec_metadata"]["urgency"]

        # SREC State
        if contractor.get("srec_metadata", {}).get("is_srec"):
            custom_fields["SREC_State"] = True

        # OEM Certifications
        if "oem_sources" in contractor:
            oem_sources = contractor["oem_sources"]
            oem_str = ", ".join(oem_sources) if isinstance(oem_sources, list) else str(oem_sources)
            custom_fields["OEM_Certifications"] = oem_str

        return custom_fields

    @staticmethod
    def _build_contacts(contractor: Dict) -> List[Dict]:
        """Build contacts list from contractor data"""
        contacts = []

        # Primary contact (contractor phone)
        primary_contact = {
            "name": contractor.get("name", ""),
            "phones": [{"phone": contractor.get("phone", "")}] if contractor.get("phone") else [],
            "emails": [],
        }

        # Add decision-maker emails (from Apollo)
        if contractor.get("decision_maker_emails"):
            for i, email in enumerate(contractor["decision_maker_emails"][:3]):  # Limit to 3 emails
                name = contractor.get("decision_maker_names", [])[i] if i < len(contractor.get("decision_maker_names", [])) else ""
                primary_contact["emails"].append({
                    "email": email,
                    "type": "office"
                })

        contacts.append(primary_contact)

        return contacts

    def bulk_import(self, contractors: List[Dict], max_retries: int = 3) -> List[CloseLeadResult]:
        """
        Bulk import contractors as leads.

        Args:
            contractors: List of enriched contractor dicts
            max_retries: Number of retries for failed imports

        Returns:
            List of CloseLeadResult objects
        """
        results = []

        print(f"[Close] Starting bulk import of {len(contractors)} contractors...\n")

        for i, contractor in enumerate(contractors, 1):
            print(f"[{i}/{len(contractors)}] Importing: {contractor.get('name')}")

            # Retry logic
            success = False
            lead_id = None
            error = None

            for attempt in range(1, max_retries + 1):
                success, lead_id, error = self.create_lead(contractor)

                if success:
                    break

                if attempt < max_retries:
                    print(f"  🔄 Retry {attempt}/{max_retries - 1}...")
                    time.sleep(1)  # Wait before retry

            # Record result
            result = CloseLeadResult(
                contractor_name=contractor.get("name", ""),
                contractor_phone=contractor.get("phone", ""),
                success=success,
                lead_id=lead_id,
                error=error
            )
            results.append(result)

        # Summary
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        print(f"\n{'='*60}")
        print(f"Bulk Import Summary")
        print(f"{'='*60}")
        print(f"Total: {len(results)}")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"{'='*60}\n")

        return results

    def create_smart_view(self, name: str, filters: Dict) -> Optional[str]:
        """
        Create a Smart View in Close CRM.

        Args:
            name: Smart View name
            filters: Filter criteria dict

        Returns:
            Smart View ID, or None if failed
        """
        self._rate_limit_check()

        payload = {
            "name": name,
            "type": "lead",
            "query": filters
        }

        try:
            response = self.session.post(
                f"{self.API_BASE_URL}/saved_search/",
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            view_id = result.get("id")

            print(f"  ✅ Created Smart View: {name} (ID: {view_id})")

            return view_id

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Failed to create Smart View: {name} - {str(e)}")
            return None

    def create_state_smart_views(self) -> Dict[str, Optional[str]]:
        """
        Create 6 state-based Smart Views for SREC states.

        Each view filters by state and sorts by Coperniq Score (descending).

        Returns:
            Dict mapping state code to Smart View ID
        """
        print(f"[Close] Creating state-based Smart Views...\n")

        views = {}

        for state in self.SREC_STATES:
            view_name = f"{state} Contractors"

            # Build filter query
            # Note: Close CRM query syntax - adjust based on actual API
            filters = {
                "queries": [
                    {
                        "type": "object_type",
                        "object_type": "lead"
                    },
                    {
                        "type": "field_condition",
                        "field": {
                            "type": "lead",
                            "field_name": "addresses.state"
                        },
                        "condition": {
                            "type": "text",
                            "value": state,
                            "mode": "is"
                        }
                    }
                ],
                "order_by": [
                    {
                        "field": "custom.Coperniq_Score",
                        "direction": "desc"
                    }
                ]
            }

            view_id = self.create_smart_view(view_name, filters)
            views[state] = view_id

        # Summary
        success_count = sum(1 for v in views.values() if v is not None)

        print(f"\n{'='*60}")
        print(f"Smart Views Summary")
        print(f"{'='*60}")
        print(f"Total: {len(views)}")
        print(f"Created: {success_count}")
        print(f"Failed: {len(views) - success_count}")
        print(f"{'='*60}\n")

        return views


# Example usage
if __name__ == "__main__":
    # Test Close CRM connection
    importer = CloseImporter()

    # Test with sample contractor
    test_contractor = {
        "name": "ABC Electrical Contractors",
        "phone": "555-123-4567",
        "website": "https://abcelectrical.com",
        "domain": "abcelectrical.com",
        "street": "123 Main St",
        "city": "Milwaukee",
        "state": "WI",
        "zip": "53202",
        "tier": "Premier",
        "oem_sources": ["Generac"],
        "score": 85,
        "priority_tier": "HIGH",
        "employee_count": 25,
        "estimated_annual_revenue": "$1M-$10M",
    }

    # Create lead
    success, lead_id, error = importer.create_lead(test_contractor)

    if success:
        print(f"\n✅ Test lead created successfully: {lead_id}")
    else:
        print(f"\n❌ Test failed: {error}")
