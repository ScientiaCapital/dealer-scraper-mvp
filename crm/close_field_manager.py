"""
Close CRM Custom Field Manager

Handles creation and management of custom fields in Close CRM
for OEM certifications, state licenses, and contractor scoring.
"""

import os
import requests
from typing import Dict, Optional, List, Any


# Required custom fields for contractor sync
REQUIRED_FIELDS = {
    "OEM_Certifications": {
        "type": "choices",
        "accepts_multiple_values": True,
        "choices": [
            "Generac", "Tesla", "Enphase", "SolarEdge", "SunPower",
            "Trane", "Carrier", "Lennox", "Rheem", "Daikin",
            "Kohler", "Briggs & Stratton", "Cummins", "Caterpillar",
            "LG", "Panasonic", "Franklin Electric", "Mitsubishi",
        ],
    },
    "State_Licenses": {
        "type": "choices",
        "accepts_multiple_values": True,
        "choices": [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        ],
    },
    "OEM_Count": {
        "type": "number",
    },
    "License_Count": {
        "type": "number",
    },
    "Is_Multi_OEM": {
        "type": "hidden",  # Boolean stored as hidden field
    },
    "Is_Multi_State": {
        "type": "hidden",
    },
    "Source_Type": {
        "type": "text",
    },
    "Coperniq_Score": {
        "type": "number",
    },
}


class CloseFieldManager:
    """
    Manages custom fields in Close CRM.

    Ensures all required fields exist before sync operations.
    Can run in mock mode (api_key=None) for testing.
    """

    BASE_URL = "https://api.close.com/api/v1"

    # Sentinel value to distinguish "not provided" from "explicitly None"
    _NOT_PROVIDED = object()

    def __init__(self, api_key: Optional[str] = _NOT_PROVIDED):
        """
        Initialize field manager.

        Args:
            api_key: Close CRM API key.
                     If None (explicitly), runs in mock mode.
                     If not provided, uses CLOSE_API_KEY env var.
        """
        # Explicit None = mock mode, not provided = use env var
        if api_key is self._NOT_PROVIDED:
            self.api_key = os.getenv("CLOSE_API_KEY")
            self._mock_mode = self.api_key is None
        else:
            self.api_key = api_key
            self._mock_mode = api_key is None

        self._existing_fields: Dict[str, Dict[str, Any]] = {}

        if not self._mock_mode:
            self._load_existing_fields()

    def _load_existing_fields(self) -> None:
        """Load existing custom fields from Close CRM."""
        if self._mock_mode:
            return

        try:
            response = requests.get(
                f"{self.BASE_URL}/custom_field/lead/",
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            for field in data.get("data", []):
                self._existing_fields[field["name"]] = {
                    "id": field["id"],
                    "type": field["type"],
                    "choices": field.get("choices", []),
                }
        except requests.RequestException as e:
            print(f"Warning: Could not load existing fields: {e}")

    def _create_field(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom field in Close CRM.

        Args:
            name: Field name
            config: Field configuration (type, choices, etc.)

        Returns:
            Created field info with ID
        """
        if self._mock_mode:
            # Return mock field for testing
            mock_id = f"cf_mock_{name.lower().replace(' ', '_')}"
            return {
                "id": mock_id,
                "type": config["type"],
                "choices": config.get("choices", []),
            }

        payload = {
            "name": name,
            "type": config["type"],
        }

        if config.get("accepts_multiple_values"):
            payload["accepts_multiple_values"] = True

        if config.get("choices"):
            payload["choices"] = config["choices"]

        try:
            response = requests.post(
                f"{self.BASE_URL}/custom_field/lead/",
                json=payload,
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return {
                "id": data["id"],
                "type": data["type"],
                "choices": data.get("choices", []),
            }
        except requests.RequestException as e:
            print(f"Error creating field {name}: {e}")
            raise

    def ensure_required_fields(self) -> Dict[str, Dict[str, Any]]:
        """
        Ensure all required custom fields exist in Close CRM.

        Creates any missing fields and returns mapping of all fields.

        Returns:
            Dict mapping field names to their info (id, type, choices)
        """
        result = {}

        for field_name, config in REQUIRED_FIELDS.items():
            if field_name in self._existing_fields:
                # Field already exists
                result[field_name] = self._existing_fields[field_name]
            else:
                # Create the field
                field_info = self._create_field(field_name, config)
                result[field_name] = field_info
                self._existing_fields[field_name] = field_info

        return result

    def get_field_id_mapping(self) -> Dict[str, str]:
        """
        Get mapping of field names to Close field IDs.

        Returns:
            Dict mapping field names to their Close CRM IDs
        """
        # Ensure fields exist first
        fields = self.ensure_required_fields()

        return {name: info["id"] for name, info in fields.items()}

    def add_choice_to_field(self, field_name: str, choice: str) -> bool:
        """
        Add a new choice to a choices field.

        Args:
            field_name: Name of the field
            choice: New choice value to add

        Returns:
            True if successful
        """
        if self._mock_mode:
            return True

        if field_name not in self._existing_fields:
            return False

        field_info = self._existing_fields[field_name]
        if field_info["type"] != "choices":
            return False

        if choice in field_info.get("choices", []):
            return True  # Already exists

        try:
            response = requests.put(
                f"{self.BASE_URL}/custom_field/lead/{field_info['id']}/",
                json={"choices": field_info["choices"] + [choice]},
                auth=(self.api_key, ""),
                timeout=30,
            )
            response.raise_for_status()
            field_info["choices"].append(choice)
            return True
        except requests.RequestException:
            return False
