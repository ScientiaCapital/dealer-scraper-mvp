"""
TDD Tests for Close CRM Sync Script

Following TDD workflow:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up while keeping green

These tests define the expected behavior for:
- CloseFieldManager: Custom field CRUD
- CloseSyncService: Data transformation and sync orchestration
- DataExtractor: SQLite/Supabase data extraction
"""

import pytest
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path
import json


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_contractor_single_oem():
    """Contractor with single OEM certification"""
    return {
        "id": 1,
        "company_name": "ABC Electric Co",
        "city": "Houston",
        "state": "TX",
        "zip_code": "77002",
        "primary_phone": "5551234567",
        "primary_email": "info@abcelectric.com",
        "website_url": "https://abcelectric.com",
        "oem_certifications": ["Generac"],
        "oem_tiers": {"Generac": "Premier"},
        "state_licenses": ["TX"],
        "license_types": {"TX": ["Master Electrician"]},
        "source_type": "oem_dealer",
        "coperniq_score": 75,
    }


@pytest.fixture
def sample_contractor_multi_oem():
    """Contractor with multiple OEM certifications - high value prospect"""
    return {
        "id": 2,
        "company_name": "Solar & Generator Pros",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94102",
        "primary_phone": "5559876543",
        "primary_email": "contact@solargenpros.com",
        "website_url": "https://solargenpros.com",
        "oem_certifications": ["Generac", "Tesla", "Enphase"],
        "oem_tiers": {"Generac": "Elite Plus", "Tesla": "Certified", "Enphase": "Gold"},
        "state_licenses": ["CA", "NV", "AZ"],
        "license_types": {
            "CA": ["C-10 Electrical", "C-46 Solar"],
            "NV": ["C-2 Electrical"],
            "AZ": ["ROC Electrical"]
        },
        "source_type": "both",
        "coperniq_score": 92,
    }


@pytest.fixture
def sample_contractor_no_contact():
    """Contractor missing contact info - enrichment candidate"""
    return {
        "id": 3,
        "company_name": "Mystery HVAC Inc",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75201",
        "primary_phone": None,
        "primary_email": None,
        "website_url": None,
        "oem_certifications": ["Trane"],
        "oem_tiers": {"Trane": "Comfort Specialist"},
        "state_licenses": ["TX"],
        "license_types": {"TX": ["HVAC"]},
        "source_type": "oem_dealer",
        "coperniq_score": 45,
    }


# ============================================================================
# TEST: CloseFieldManager
# ============================================================================

class TestCloseFieldManager:
    """Tests for Close CRM custom field management"""

    @pytest.mark.unit
    def test_ensure_required_fields_creates_oem_certifications(self):
        """When OEM_Certifications field doesn't exist, create it as multi-select"""
        from crm.close_field_manager import CloseFieldManager

        # Use None API key to get mock responses
        manager = CloseFieldManager(api_key=None)
        manager._existing_fields = {}

        result = manager.ensure_required_fields()

        assert "OEM_Certifications" in result
        assert result["OEM_Certifications"]["type"] == "choices"
        assert "Generac" in result["OEM_Certifications"]["choices"]
        assert "Tesla" in result["OEM_Certifications"]["choices"]

    @pytest.mark.unit
    def test_ensure_required_fields_creates_state_licenses(self):
        """When State_Licenses field doesn't exist, create it as multi-select"""
        from crm.close_field_manager import CloseFieldManager

        manager = CloseFieldManager(api_key=None)
        manager._existing_fields = {}

        result = manager.ensure_required_fields()

        assert "State_Licenses" in result
        assert result["State_Licenses"]["type"] == "choices"
        assert "CA" in result["State_Licenses"]["choices"]
        assert "TX" in result["State_Licenses"]["choices"]

    @pytest.mark.unit
    def test_ensure_required_fields_creates_oem_count(self):
        """When OEM_Count field doesn't exist, create it as number"""
        from crm.close_field_manager import CloseFieldManager

        manager = CloseFieldManager(api_key=None)
        manager._existing_fields = {}

        result = manager.ensure_required_fields()

        assert "OEM_Count" in result
        assert result["OEM_Count"]["type"] == "number"

    @pytest.mark.unit
    def test_ensure_required_fields_skips_existing(self):
        """When field already exists, don't create duplicate"""
        from crm.close_field_manager import CloseFieldManager

        manager = CloseFieldManager(api_key=None)
        # Simulate existing field
        manager._existing_fields = {
            "OEM_Certifications": {"id": "cf_existing123", "type": "choices", "choices": []}
        }

        result = manager.ensure_required_fields()

        # Should return existing field, not create new
        assert result["OEM_Certifications"]["id"] == "cf_existing123"

    @pytest.mark.unit
    def test_get_field_id_mapping_returns_all_required(self):
        """Return mapping of all required field names to IDs"""
        from crm.close_field_manager import CloseFieldManager

        manager = CloseFieldManager(api_key=None)

        mapping = manager.get_field_id_mapping()

        required_fields = [
            "OEM_Certifications",
            "State_Licenses",
            "OEM_Count",
            "License_Count",
            "Is_Multi_OEM",
            "Is_Multi_State",
            "Source_Type"
        ]
        for field in required_fields:
            assert field in mapping, f"Missing required field: {field}"


# ============================================================================
# TEST: CloseSyncService Transform
# ============================================================================

class TestCloseSyncServiceTransform:
    """Tests for data transformation in Close CRM sync"""

    @pytest.mark.unit
    def test_transform_single_oem_contractor(self, sample_contractor_single_oem):
        """Contractor with 1 OEM cert transforms correctly"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_single_oem)

        assert payload.name == "ABC Electric Co"
        assert payload.custom["OEM_Certifications"] == ["Generac"]
        assert payload.custom["OEM_Count"] == 1
        assert payload.custom["Is_Multi_OEM"] == False

    @pytest.mark.unit
    def test_transform_multi_oem_contractor(self, sample_contractor_multi_oem):
        """Contractor with 3+ OEM certs shows all in list"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_multi_oem)

        assert payload.name == "Solar & Generator Pros"
        assert set(payload.custom["OEM_Certifications"]) == {"Generac", "Tesla", "Enphase"}
        assert payload.custom["OEM_Count"] == 3
        assert payload.custom["Is_Multi_OEM"] == True

    @pytest.mark.unit
    def test_transform_extracts_state_licenses(self, sample_contractor_multi_oem):
        """State licenses extracted and formatted correctly"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_multi_oem)

        assert set(payload.custom["State_Licenses"]) == {"CA", "NV", "AZ"}
        assert payload.custom["License_Count"] == 3
        assert payload.custom["Is_Multi_State"] == True

    @pytest.mark.unit
    def test_transform_calculates_counts_correctly(self, sample_contractor_multi_oem):
        """OEM_Count and License_Count calculated correctly"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_multi_oem)

        assert payload.custom["OEM_Count"] == 3
        assert payload.custom["License_Count"] == 3
        assert payload.custom["Coperniq_Score"] == 92

    @pytest.mark.unit
    def test_transform_handles_missing_contact(self, sample_contractor_no_contact):
        """Contractor without phone/email still transforms"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_no_contact)

        assert payload.name == "Mystery HVAC Inc"
        # Should have empty contacts list, not error
        assert payload.contacts == [] or all(
            c.get("phone") is None and c.get("email") is None
            for c in payload.contacts
        )

    @pytest.mark.unit
    def test_transform_sets_source_type(self, sample_contractor_multi_oem):
        """Source type (oem_dealer, state_license, both) set correctly"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        payload = service._transform_to_payload(sample_contractor_multi_oem)

        assert payload.custom["Source_Type"] == "both"


# ============================================================================
# TEST: CloseSyncService Dry Run
# ============================================================================

class TestCloseSyncServiceDryRun:
    """Tests for dry run mode - should NOT call Close API"""

    @pytest.mark.unit
    def test_dry_run_does_not_call_create_api(self, sample_contractor_single_oem):
        """Dry run mode skips all create API calls - importer should not be used"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        # Mock the extractor to return test data without hitting database
        service.extractor.extract_contractors = lambda **kwargs: iter([sample_contractor_single_oem])

        result = service.run_sync()

        # In dry run, importer is None and no API calls happen
        assert service.importer is None or not hasattr(service.importer, "_called")
        assert result.summary["dry_run"] == True
        assert len(result.would_create) == 1

    @pytest.mark.unit
    def test_dry_run_still_transforms_data(self, sample_contractor_single_oem):
        """Dry run should still transform data to show what would happen"""
        from crm.close_sync_service import CloseSyncService

        service = CloseSyncService(source="sqlite", dry_run=True)

        # Mock the extractor to return test data without hitting database
        service.extractor.extract_contractors = lambda **kwargs: iter([sample_contractor_single_oem])

        result = service.run_sync()

        assert result.summary["total_extracted"] == 1
        assert len(result.would_create) > 0


# ============================================================================
# TEST: CloseImporter Upsert
# ============================================================================

class TestCloseImporterUpsert:
    """Tests for lead upsert (create or update) logic"""

    @pytest.mark.unit
    def test_find_lead_by_phone_returns_existing(self):
        """When phone matches existing lead, return that lead"""
        from crm.close_importer import CloseImporter

        importer = CloseImporter(test_mode=True)

        # Mock existing lead
        importer._mock_leads = {
            "5551234567": {"id": "lead_abc123", "name": "Existing Corp"}
        }

        result = importer.find_lead_by_phone("5551234567")

        assert result is not None
        assert result["id"] == "lead_abc123"

    @pytest.mark.unit
    def test_find_lead_by_phone_returns_none_when_not_found(self):
        """When no phone match, return None"""
        from crm.close_importer import CloseImporter

        importer = CloseImporter(test_mode=True)
        importer._mock_leads = {}

        result = importer.find_lead_by_phone("9999999999")

        assert result is None

    @pytest.mark.unit
    def test_upsert_creates_new_lead_when_not_exists(self):
        """When no existing lead found, create new one"""
        from crm.close_importer import CloseImporter
        from crm.models import CloseLeadPayload

        importer = CloseImporter(test_mode=True)
        importer._mock_leads = {}

        payload = CloseLeadPayload(
            name="New Company",
            url="https://newcompany.com",
            description="Test",
            addresses=[],
            contacts=[{"phone": "5551112222"}],
            custom={"OEM_Count": 1}
        )

        lead_id, action, changes = importer.upsert_lead(payload)

        assert action == "created"
        assert lead_id is not None

    @pytest.mark.unit
    def test_upsert_updates_existing_lead(self):
        """When existing lead found, update custom fields"""
        from crm.close_importer import CloseImporter
        from crm.models import CloseLeadPayload

        importer = CloseImporter(test_mode=True)
        importer._mock_leads = {
            "5553334444": {
                "id": "lead_existing",
                "name": "Existing Co",
                "custom": {"OEM_Count": 1}
            }
        }

        payload = CloseLeadPayload(
            name="Existing Co",
            url=None,
            description="Updated",
            addresses=[],
            contacts=[{"phone": "5553334444"}],
            custom={"OEM_Count": 3}  # Updated value
        )

        lead_id, action, changes = importer.upsert_lead(payload)

        assert action == "updated"
        assert lead_id == "lead_existing"
        assert changes["OEM_Count"] == (1, 3)

    @pytest.mark.unit
    def test_upsert_tracks_field_changes(self):
        """Return diff of what changed on update"""
        from crm.close_importer import CloseImporter
        from crm.models import CloseLeadPayload

        importer = CloseImporter(test_mode=True)
        importer._mock_leads = {
            "5555556666": {
                "id": "lead_track",
                "custom": {
                    "OEM_Count": 1,
                    "OEM_Certifications": ["Generac"]
                }
            }
        }

        payload = CloseLeadPayload(
            name="Track Changes Co",
            url=None,
            description="",
            addresses=[],
            contacts=[{"phone": "5555556666"}],
            custom={
                "OEM_Count": 2,
                "OEM_Certifications": ["Generac", "Tesla"]
            }
        )

        _, _, changes = importer.upsert_lead(payload)

        assert "OEM_Count" in changes
        assert changes["OEM_Count"] == (1, 2)
        assert "OEM_Certifications" in changes


# ============================================================================
# TEST: DataExtractor
# ============================================================================

class TestDataExtractor:
    """Tests for extracting contractor data from SQLite"""

    @pytest.mark.unit
    def test_extract_includes_oem_certifications(self, tmp_path):
        """Extracted contractors include all OEM certifications"""
        from crm.data_extractor import DataExtractor

        # Create test SQLite with OEM data
        db_path = tmp_path / "test_pipeline.db"
        _create_test_db(db_path)

        extractor = DataExtractor(source="sqlite", db_path=db_path)

        contractors = list(extractor.extract_contractors(limit=1))

        assert len(contractors) == 1
        assert "oem_certifications" in contractors[0]
        assert isinstance(contractors[0]["oem_certifications"], list)

    @pytest.mark.unit
    def test_extract_includes_state_licenses(self, tmp_path):
        """Extracted contractors include state licenses"""
        from crm.data_extractor import DataExtractor

        db_path = tmp_path / "test_pipeline.db"
        _create_test_db(db_path)

        extractor = DataExtractor(source="sqlite", db_path=db_path)

        contractors = list(extractor.extract_contractors(limit=1))

        assert "state_licenses" in contractors[0]
        assert isinstance(contractors[0]["state_licenses"], list)

    @pytest.mark.unit
    def test_extract_with_oem_filter(self, tmp_path):
        """Filter by OEM returns only contractors with that certification"""
        from crm.data_extractor import DataExtractor

        db_path = tmp_path / "test_pipeline.db"
        _create_test_db_with_multiple_oems(db_path)

        extractor = DataExtractor(source="sqlite", db_path=db_path)

        contractors = list(extractor.extract_contractors(oem_filter="Tesla"))

        for c in contractors:
            assert "Tesla" in c["oem_certifications"]

    @pytest.mark.unit
    def test_extract_with_min_oem_count(self, tmp_path):
        """Filter by min OEM count returns only multi-OEM contractors"""
        from crm.data_extractor import DataExtractor

        db_path = tmp_path / "test_pipeline.db"
        _create_test_db_with_multiple_oems(db_path)

        extractor = DataExtractor(source="sqlite", db_path=db_path)

        contractors = list(extractor.extract_contractors(min_oem_count=2))

        for c in contractors:
            assert len(c["oem_certifications"]) >= 2

    @pytest.mark.unit
    def test_extract_with_state_filter(self, tmp_path):
        """Filter by state returns only contractors in that state"""
        from crm.data_extractor import DataExtractor

        db_path = tmp_path / "test_pipeline.db"
        _create_test_db(db_path)

        extractor = DataExtractor(source="sqlite", db_path=db_path)

        contractors = list(extractor.extract_contractors(state_filter="TX"))

        for c in contractors:
            assert c["state"] == "TX"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _create_test_db(db_path: Path):
    """Create minimal test SQLite database"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables (match real schema with icp_score)
    cur.execute("""
        CREATE TABLE contractors (
            id INTEGER PRIMARY KEY,
            company_name TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            primary_phone TEXT,
            primary_email TEXT,
            website_url TEXT,
            icp_score INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE oem_certifications (
            id INTEGER PRIMARY KEY,
            contractor_id INTEGER,
            oem_name TEXT,
            tier TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE licenses (
            id INTEGER PRIMARY KEY,
            contractor_id INTEGER,
            state TEXT,
            license_type TEXT
        )
    """)

    # Insert test data
    cur.execute("""
        INSERT INTO contractors (id, company_name, city, state, primary_phone, icp_score)
        VALUES (1, 'Test Corp', 'Houston', 'TX', '5551234567', 80)
    """)

    cur.execute("""
        INSERT INTO oem_certifications (contractor_id, oem_name, tier)
        VALUES (1, 'Generac', 'Premier')
    """)

    cur.execute("""
        INSERT INTO licenses (contractor_id, state, license_type)
        VALUES (1, 'TX', 'Master Electrician')
    """)

    conn.commit()
    conn.close()


def _create_test_db_with_multiple_oems(db_path: Path):
    """Create test SQLite database with multi-OEM contractors"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables (match real schema with icp_score)
    cur.execute("""
        CREATE TABLE contractors (
            id INTEGER PRIMARY KEY,
            company_name TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            primary_phone TEXT,
            primary_email TEXT,
            website_url TEXT,
            icp_score INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE oem_certifications (
            id INTEGER PRIMARY KEY,
            contractor_id INTEGER,
            oem_name TEXT,
            tier TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE licenses (
            id INTEGER PRIMARY KEY,
            contractor_id INTEGER,
            state TEXT,
            license_type TEXT
        )
    """)

    # Insert multi-OEM contractor
    cur.execute("""
        INSERT INTO contractors (id, company_name, city, state, primary_phone, icp_score)
        VALUES (1, 'Multi OEM Corp', 'San Francisco', 'CA', '5559999999', 90)
    """)

    for oem in ["Generac", "Tesla", "Enphase"]:
        cur.execute("""
            INSERT INTO oem_certifications (contractor_id, oem_name, tier)
            VALUES (1, ?, 'Certified')
        """, (oem,))

    # Insert single-OEM contractor
    cur.execute("""
        INSERT INTO contractors (id, company_name, city, state, primary_phone, icp_score)
        VALUES (2, 'Single OEM Corp', 'Houston', 'TX', '5558888888', 60)
    """)

    cur.execute("""
        INSERT INTO oem_certifications (contractor_id, oem_name, tier)
        VALUES (2, 'Generac', 'Standard')
    """)

    conn.commit()
    conn.close()


# ============================================================================
# TEST: CLI Interface
# ============================================================================

class TestCloseSyncCLI:
    """Tests for command-line interface"""

    @pytest.mark.unit
    def test_cli_dry_run_flag(self):
        """--dry-run flag enables dry run mode"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--dry-run"])

        assert args.dry_run == True

    @pytest.mark.unit
    def test_cli_limit_flag(self):
        """--limit N limits records processed"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--limit", "5"])

        assert args.limit == 5

    @pytest.mark.unit
    def test_cli_source_flag(self):
        """--source selects data source"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--source", "supabase"])

        assert args.source == "supabase"

    @pytest.mark.unit
    def test_cli_state_filter(self):
        """--state filters by state code"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--state", "TX"])

        assert args.state == "TX"

    @pytest.mark.unit
    def test_cli_oem_filter(self):
        """--oem filters by OEM name"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--oem", "Generac"])

        assert args.oem == "Generac"

    @pytest.mark.unit
    def test_cli_min_oems_filter(self):
        """--min-oems filters by minimum OEM count"""
        from scripts.sync_to_close_crm import create_parser

        parser = create_parser()
        args = parser.parse_args(["--min-oems", "2"])

        assert args.min_oems == 2
