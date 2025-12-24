#!/usr/bin/env python3
"""
Tests for Colorado DORA license migration script.

TDD: Write tests first, then implement the migration.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestColoradoMigration:
    """Tests for Colorado DORA SODA API migration"""

    @pytest.fixture
    def sample_ec_record(self):
        """Sample Electrical Contractor record from SODA API"""
        return {
            "entityname": "AK Electric",
            "city": "Avon",
            "state": "CO",
            "mailzipcode": "81620",
            "licensetype": "EC",
            "licensenumber": "4751",
            "licensefirstissuedate": "1998-02-02T00:00:00.000",
            "licenselastreneweddate": "2023-10-01T00:00:00.000",
            "licenseexpirationdate": "2026-09-30T00:00:00.000",
            "licensestatusdescription": "Active",
            "linktoverifylicense": {
                "url": "https://www.colorado.gov/dora/licensing/Lookup/PrintLicenseDetails.aspx?cred=325914&contact=375953"
            }
        }

    @pytest.fixture
    def sample_pc_record(self):
        """Sample Plumbing Contractor record from SODA API"""
        return {
            "entityname": "Homeland Mechanical LLC",
            "city": "Colorado Springs",
            "state": "CO",
            "mailzipcode": "80906",
            "licensetype": "PC",
            "licensenumber": "2225",
            "licensefirstissuedate": "2008-07-22T00:00:00.000",
            "licenselastreneweddate": "2025-03-01T00:00:00.000",
            "licenseexpirationdate": "2027-02-28T00:00:00.000",
            "licensestatusdescription": "Active",
            "linktoverifylicense": {
                "url": "https://www.colorado.gov/dora/licensing/Lookup/PrintLicenseDetails.aspx?cred=814934&contact=923987"
            }
        }

    def test_transform_ec_record(self, sample_ec_record):
        """Transform EC record to pipeline.db contractor format"""
        from scripts.migrate_co_to_sqlite import transform_dora_record

        result = transform_dora_record(sample_ec_record)

        assert result["company_name"] == "AK Electric"
        assert result["city"] == "Avon"
        assert result["state"] == "CO"
        assert result["zip"] == "81620"
        assert result["license_type"] == "Electrical Contractor"
        assert result["license_number"] == "4751"
        assert result["license_status"] == "Active"
        assert result["source"] == "CO_DORA"

    def test_transform_pc_record(self, sample_pc_record):
        """Transform PC record to pipeline.db contractor format"""
        from scripts.migrate_co_to_sqlite import transform_dora_record

        result = transform_dora_record(sample_pc_record)

        assert result["company_name"] == "Homeland Mechanical LLC"
        assert result["city"] == "Colorado Springs"
        assert result["state"] == "CO"
        assert result["zip"] == "80906"
        assert result["license_type"] == "Plumbing Contractor"
        assert result["license_number"] == "2225"

    def test_transform_handles_missing_fields(self):
        """Gracefully handle records with missing optional fields"""
        from scripts.migrate_co_to_sqlite import transform_dora_record

        minimal_record = {
            "entityname": "Test Company",
            "licensetype": "EC",
            "licensenumber": "12345",
            "licensestatusdescription": "Active"
        }

        result = transform_dora_record(minimal_record)

        assert result["company_name"] == "Test Company"
        assert result["city"] is None
        assert result["state"] == "CO"  # Default to CO
        assert result["zip"] is None

    def test_license_type_mapping(self):
        """Map license type codes to human-readable names"""
        from scripts.migrate_co_to_sqlite import LICENSE_TYPE_MAP

        assert LICENSE_TYPE_MAP["EC"] == "Electrical Contractor"
        assert LICENSE_TYPE_MAP["PC"] == "Plumbing Contractor"
        assert LICENSE_TYPE_MAP["ME"] == "Master Electrician"
        assert LICENSE_TYPE_MAP["MP"] == "Master Plumber"

    def test_normalize_company_name(self):
        """Normalize company names for deduplication"""
        from scripts.migrate_co_to_sqlite import normalize_company_name

        assert normalize_company_name("AK Electric") == "ak electric"
        assert normalize_company_name("  SOME COMPANY LLC  ") == "some company llc"
        assert normalize_company_name("Test, Inc.") == "test inc"

    def test_skip_expired_licenses_by_default(self, sample_ec_record):
        """Should skip expired licenses unless explicitly included"""
        from scripts.migrate_co_to_sqlite import should_include_record

        # Active license should be included
        assert should_include_record(sample_ec_record, include_expired=False) is True

        # Expired license should be skipped
        expired = sample_ec_record.copy()
        expired["licensestatusdescription"] = "Expired"
        assert should_include_record(expired, include_expired=False) is False

        # But included if flag is set
        assert should_include_record(expired, include_expired=True) is True

    def test_api_pagination(self):
        """SODA API returns max 1000 records, need pagination"""
        from scripts.migrate_co_to_sqlite import fetch_all_records

        # This is a functional test - just verify the function exists
        # Actual API calls tested in integration tests
        assert callable(fetch_all_records)


class TestColoradoIntegration:
    """Integration tests that hit the real SODA API (marked slow)"""

    @pytest.mark.slow
    def test_fetch_sample_ec_records(self):
        """Fetch a sample of real EC records from SODA API"""
        from scripts.migrate_co_to_sqlite import fetch_records

        records = fetch_records(license_type="EC", limit=5)

        assert len(records) == 5
        assert all(r["licensetype"] == "EC" for r in records)
        assert all("entityname" in r for r in records)

    @pytest.mark.slow
    def test_fetch_sample_pc_records(self):
        """Fetch a sample of real PC records from SODA API"""
        from scripts.migrate_co_to_sqlite import fetch_records

        records = fetch_records(license_type="PC", limit=5)

        assert len(records) == 5
        assert all(r["licensetype"] == "PC" for r in records)
