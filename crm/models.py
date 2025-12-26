"""
Close CRM Data Models

Dataclasses for Close CRM API payloads and sync results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


@dataclass
class CloseLeadPayload:
    """
    Lead payload for Close CRM API.

    Maps contractor data to Close CRM lead structure with
    custom fields for OEM certifications and state licenses.
    """
    name: str
    url: Optional[str] = None
    description: str = ""
    addresses: List[Dict[str, Any]] = field(default_factory=list)
    contacts: List[Dict[str, Any]] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_api_payload(self, field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert to Close CRM API format.

        Args:
            field_mapping: Map of field names to Close custom field IDs

        Returns:
            Dict ready for Close API POST/PUT
        """
        payload = {
            "name": self.name,
        }

        if self.url:
            payload["url"] = self.url

        if self.description:
            payload["description"] = self.description

        if self.addresses:
            payload["addresses"] = self.addresses

        if self.contacts:
            payload["contacts"] = self.contacts

        # Map custom fields to Close field IDs
        for field_name, value in self.custom.items():
            if field_name in field_mapping:
                field_id = field_mapping[field_name]
                # Skip empty arrays/None - Close rejects empty arrays
                if value is None:
                    continue
                if isinstance(value, list) and len(value) == 0:
                    continue
                payload[f"custom.{field_id}"] = value

        return payload


@dataclass
class SyncReport:
    """
    Report from a sync operation.

    Tracks what was synced, created, updated, and any errors.
    """
    sync_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Counts
    summary: Dict[str, Any] = field(default_factory=lambda: {
        "total_extracted": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "dry_run": False,
    })

    # Dry run results
    would_create: List[Dict[str, Any]] = field(default_factory=list)
    would_update: List[Dict[str, Any]] = field(default_factory=list)

    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "sync_id": self.sync_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "would_create": self.would_create,
            "would_update": self.would_update,
            "errors": self.errors,
        }
