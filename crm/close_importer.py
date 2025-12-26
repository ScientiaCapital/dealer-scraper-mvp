"""
Close CRM Lead Importer

Handles lead creation and updates in Close CRM with
phone-based deduplication and change tracking.
"""

import os
import requests
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass

from .models import CloseLeadPayload


@dataclass
class ImportResult:
    """Result of a single lead import operation."""
    success: bool
    contractor_name: str
    contractor_phone: str
    lead_id: Optional[str] = None
    action: str = ""  # "created", "updated", "skipped"
    error: Optional[str] = None
    changes: Dict[str, Tuple[Any, Any]] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = {}


class CloseImporter:
    """
    Imports leads to Close CRM with upsert logic.

    Uses phone number for deduplication. Tracks changes on updates.
    Can run in test_mode for unit testing without API calls.
    """

    BASE_URL = "https://api.close.com/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        test_mode: bool = False,
    ):
        """
        Initialize Close importer.

        Args:
            api_key: Close CRM API key
            test_mode: If True, use mock data instead of API calls
        """
        self.api_key = api_key or os.getenv("CLOSE_API_KEY")
        self.test_mode = test_mode
        self._mock_leads: Dict[str, Dict] = {}
        self._field_mapping: Dict[str, str] = {}

    def set_field_mapping(self, mapping: Dict[str, str]) -> None:
        """Set custom field name to ID mapping."""
        self._field_mapping = mapping

    def find_lead_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Find existing lead by phone number.

        Args:
            phone: Normalized phone number (10 digits)

        Returns:
            Lead dict if found, None otherwise
        """
        if self.test_mode:
            return self._mock_leads.get(phone)

        if not self.api_key:
            return None

        try:
            # Search for lead by phone
            query = f'phone:"{phone}"'
            response = requests.get(
                f"{self.BASE_URL}/lead/",
                params={"query": query, "_limit": 1},
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            leads = data.get("data", [])

            if leads:
                return leads[0]
            return None

        except requests.RequestException as e:
            print(f"Error searching for lead: {e}")
            return None

    def upsert_lead(
        self,
        payload: CloseLeadPayload,
    ) -> Tuple[Optional[str], str, Dict[str, Tuple[Any, Any]]]:
        """
        Create or update a lead.

        Args:
            payload: Lead payload with all data

        Returns:
            Tuple of (lead_id, action, changes)
            - lead_id: Close CRM lead ID
            - action: "created" or "updated"
            - changes: Dict of field changes {field: (old, new)}
        """
        # Extract phone from contacts for lookup (Close API format)
        phone = None
        for contact in payload.contacts:
            phones = contact.get("phones", [])
            if phones and phones[0].get("phone"):
                phone = phones[0]["phone"]
                break

        # Check for existing lead
        existing = self.find_lead_by_phone(phone) if phone else None

        if existing:
            # Update existing lead
            return self._update_lead(existing, payload)
        else:
            # Create new lead
            return self._create_lead(payload)

    def _create_lead(
        self,
        payload: CloseLeadPayload,
    ) -> Tuple[str, str, Dict]:
        """Create a new lead in Close CRM."""
        if self.test_mode:
            # Mock creation
            lead_id = f"lead_{len(self._mock_leads) + 1}"

            # Store in mock data if phone present
            for contact in payload.contacts:
                if contact.get("phone"):
                    self._mock_leads[contact["phone"]] = {
                        "id": lead_id,
                        "name": payload.name,
                        "custom": payload.custom,
                    }
                    break

            return lead_id, "created", {}

        if not self.api_key:
            raise ValueError("API key required for lead creation")

        api_payload = payload.to_api_payload(self._field_mapping)

        try:
            response = requests.post(
                f"{self.BASE_URL}/lead/",
                json=api_payload,
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data["id"], "created", {}

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to create lead: {e}")

    def _update_lead(
        self,
        existing: Dict[str, Any],
        payload: CloseLeadPayload,
    ) -> Tuple[str, str, Dict[str, Tuple[Any, Any]]]:
        """Update an existing lead with changes tracked."""
        lead_id = existing["id"]
        changes: Dict[str, Tuple[Any, Any]] = {}

        # Calculate changes in custom fields
        existing_custom = existing.get("custom", {})

        for field, new_value in payload.custom.items():
            old_value = existing_custom.get(field)
            if old_value != new_value:
                changes[field] = (old_value, new_value)

        if self.test_mode:
            # Update mock data
            for phone, lead in self._mock_leads.items():
                if lead["id"] == lead_id:
                    lead["custom"] = payload.custom
                    break
            return lead_id, "updated", changes

        if not self.api_key:
            raise ValueError("API key required for lead update")

        # Only update if there are changes
        if not changes:
            return lead_id, "updated", {}

        api_payload = payload.to_api_payload(self._field_mapping)

        try:
            response = requests.put(
                f"{self.BASE_URL}/lead/{lead_id}/",
                json=api_payload,
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()

            return lead_id, "updated", changes

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to update lead: {e}")

    def bulk_import(
        self,
        contractors: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> List[ImportResult]:
        """
        Import multiple contractors as leads.

        Args:
            contractors: List of contractor dicts
            batch_size: Number of contractors per batch

        Returns:
            List of ImportResult for each contractor
        """
        results = []

        for contractor in contractors:
            try:
                # Build payload from contractor dict
                payload = self._contractor_to_payload(contractor)

                lead_id, action, changes = self.upsert_lead(payload)

                results.append(ImportResult(
                    success=True,
                    contractor_name=contractor.get("company_name", ""),
                    contractor_phone=contractor.get("primary_phone", ""),
                    lead_id=lead_id,
                    action=action,
                    changes=changes,
                ))

            except Exception as e:
                results.append(ImportResult(
                    success=False,
                    contractor_name=contractor.get("company_name", ""),
                    contractor_phone=contractor.get("primary_phone", ""),
                    error=str(e),
                ))

        return results

    def _contractor_to_payload(self, contractor: Dict[str, Any]) -> CloseLeadPayload:
        """Convert contractor dict to CloseLeadPayload."""
        contacts = []
        if contractor.get("primary_phone") or contractor.get("primary_email"):
            contact = {}
            if contractor.get("primary_phone"):
                contact["phones"] = [{"phone": contractor["primary_phone"]}]
            if contractor.get("primary_email"):
                contact["emails"] = [{"email": contractor["primary_email"]}]
            if contact:
                contacts.append(contact)

        addresses = []
        if contractor.get("city") or contractor.get("state"):
            addresses.append({
                "city": contractor.get("city", ""),
                "state": contractor.get("state", ""),
                "zipcode": contractor.get("zip_code", ""),
            })

        return CloseLeadPayload(
            name=contractor.get("company_name", ""),
            url=contractor.get("website_url"),
            description="",
            addresses=addresses,
            contacts=contacts,
            custom={
                "OEM_Certifications": contractor.get("oem_certifications", []),
                "State_Licenses": contractor.get("state_licenses", []),
                "OEM_Count": len(contractor.get("oem_certifications", [])),
                "License_Count": len(contractor.get("state_licenses", [])),
                "Is_Multi_OEM": len(contractor.get("oem_certifications", [])) >= 2,
                "Is_Multi_State": len(contractor.get("state_licenses", [])) >= 2,
                "Source_Type": contractor.get("source_type", ""),
                "Coperniq_Score": contractor.get("coperniq_score", 0),
            },
        )
