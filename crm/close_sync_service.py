"""
Close CRM Sync Service

Orchestrates the full sync workflow:
1. Extract contractors from SQLite/Supabase
2. Transform to Close CRM lead format
3. Upsert to Close CRM (or dry run)
4. Generate sync report
"""

import os
from datetime import datetime
from typing import Dict, Optional, Any, List

from .models import CloseLeadPayload, SyncReport
from .data_extractor import DataExtractor
from .close_importer import CloseImporter
from .close_field_manager import CloseFieldManager


class CloseSyncService:
    """
    Orchestrates Close CRM sync operations.

    Supports dry run mode for testing without API calls.
    """

    def __init__(
        self,
        source: str = "sqlite",
        dry_run: bool = False,
        limit: Optional[int] = None,
        db_path: Optional[str] = None,
    ):
        """
        Initialize sync service.

        Args:
            source: Data source ("sqlite" or "supabase")
            dry_run: If True, don't make API calls
            limit: Max contractors to process
            db_path: Path to SQLite database
        """
        self.source = source
        self.dry_run = dry_run
        self.limit = limit

        # Initialize components
        from pathlib import Path
        db = Path(db_path) if db_path else None
        self.extractor = DataExtractor(source=source, db_path=db)

        # Only create importer if not dry run
        if dry_run:
            self.importer = None
            self.field_manager = None
        else:
            api_key = os.getenv("CLOSE_API_KEY")
            self.field_manager = CloseFieldManager(api_key=api_key)
            self.importer = CloseImporter(api_key=api_key)

    def _transform_to_payload(
        self, contractor: Dict[str, Any], owner_id: Optional[str] = None
    ) -> CloseLeadPayload:
        """
        Transform contractor dict to Close CRM lead payload.

        Args:
            contractor: Contractor data from extractor
            owner_id: Close CRM user ID for lead assignment

        Returns:
            CloseLeadPayload ready for API
        """
        # Build contacts list (Close API format)
        contacts = []
        if contractor.get("primary_phone") or contractor.get("primary_email"):
            contact = {}
            if contractor.get("primary_phone"):
                contact["phones"] = [{"phone": contractor["primary_phone"]}]
            if contractor.get("primary_email"):
                contact["emails"] = [{"email": contractor["primary_email"]}]
            if contact:
                contacts.append(contact)

        # Build addresses list
        addresses = []
        if contractor.get("city") or contractor.get("state") or contractor.get("zip_code"):
            addresses.append({
                "city": contractor.get("city", ""),
                "state": contractor.get("state", ""),
                "zipcode": contractor.get("zip_code", ""),
            })

        # Calculate derived fields
        oem_certs = contractor.get("oem_certifications", [])
        state_licenses = contractor.get("state_licenses", [])

        return CloseLeadPayload(
            name=contractor.get("company_name", "Unknown"),
            url=contractor.get("website_url"),
            description=self._build_description(contractor),
            addresses=addresses,
            contacts=contacts,
            custom={
                "OEM_Certifications": oem_certs,
                "State_Licenses": state_licenses,
                "OEM_Count": len(oem_certs),
                "License_Count": len(state_licenses),
                "Is_Multi_OEM": len(oem_certs) >= 2,
                "Is_Multi_State": len(state_licenses) >= 2,
                "Source_Type": contractor.get("source_type", ""),
                "Coperniq_Score": contractor.get("coperniq_score", 0),
            },
            owner_id=owner_id,
        )

    def _build_description(self, contractor: Dict[str, Any]) -> str:
        """Build lead description from contractor data."""
        parts = []

        # OEM tiers
        oem_tiers = contractor.get("oem_tiers", {})
        if oem_tiers:
            tier_strs = [f"{oem}: {tier}" for oem, tier in oem_tiers.items()]
            parts.append(f"OEM Tiers: {', '.join(tier_strs)}")

        # License types
        license_types = contractor.get("license_types", {})
        if license_types:
            for state, types in license_types.items():
                parts.append(f"{state} Licenses: {', '.join(types)}")

        return "\n".join(parts) if parts else ""

    def run_sync(
        self,
        state_filter: Optional[str] = None,
        oem_filter: Optional[str] = None,
        min_oem_count: int = 0,
        owner_id: Optional[str] = None,
    ) -> SyncReport:
        """
        Run the full sync operation.

        Args:
            state_filter: Filter by state code
            oem_filter: Filter by OEM name
            min_oem_count: Minimum OEM certification count
            owner_id: Close CRM user ID for lead assignment

        Returns:
            SyncReport with results
        """
        report = SyncReport()
        report.summary["dry_run"] = self.dry_run

        start_time = datetime.now()

        # Ensure custom fields exist (unless dry run)
        field_mapping = {}
        if not self.dry_run and self.field_manager:
            field_mapping = self.field_manager.get_field_id_mapping()
            if self.importer:
                self.importer.set_field_mapping(field_mapping)

        # Extract contractors
        contractors = list(self.extractor.extract_contractors(
            limit=self.limit,
            state_filter=state_filter,
            oem_filter=oem_filter,
            min_oem_count=min_oem_count,
        ))

        report.summary["total_extracted"] = len(contractors)

        # Process each contractor
        for contractor in contractors:
            try:
                payload = self._transform_to_payload(contractor, owner_id=owner_id)

                if self.dry_run:
                    # Check if would create or update
                    report.would_create.append({
                        "name": payload.name,
                        "oem_count": payload.custom.get("OEM_Count", 0),
                        "state_licenses": payload.custom.get("State_Licenses", []),
                    })
                else:
                    # Actually sync to Close
                    lead_id, action, changes = self.importer.upsert_lead(payload)

                    if action == "created":
                        report.summary["created"] += 1
                    elif action == "updated":
                        report.summary["updated"] += 1
                    else:
                        report.summary["skipped"] += 1

            except Exception as e:
                report.summary["failed"] += 1
                report.errors.append({
                    "company_name": contractor.get("company_name", "Unknown"),
                    "error": str(e),
                })

        # Finalize report
        end_time = datetime.now()
        report.completed_at = end_time
        report.duration_seconds = (end_time - start_time).total_seconds()

        return report
