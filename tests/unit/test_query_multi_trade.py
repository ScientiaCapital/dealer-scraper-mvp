#!/usr/bin/env python3
"""
Tests for Multi-Trade Contractor Query Script

Following TDD: These tests are written FIRST, before implementation.
They define the expected behavior of the query_multi_trade_contractors script.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Dict

# Import will fail initially - this is expected in TDD RED phase
try:
    from scripts.query_multi_trade_contractors import (
        query_multi_trade_contractors,
        filter_business_entities,
        assign_icp_tier,
        is_business_entity,
    )
except ImportError:
    # Expected to fail initially - we haven't written the module yet
    pytest.skip("Implementation not yet created (TDD RED phase)", allow_module_level=True)


@pytest.fixture
def test_db():
    """Create a temporary test database with sample data."""
    # Create temp database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema (matching pipeline.db)
    cursor.execute("""
        CREATE TABLE contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            state TEXT,
            primary_phone TEXT,
            primary_email TEXT,
            source_type TEXT DEFAULT 'state_license'
        )
    """)

    cursor.execute("""
        CREATE TABLE licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_id INTEGER REFERENCES contractors(id),
            license_type TEXT,
            state TEXT
        )
    """)

    # Insert test data
    # Business entities (should be included)
    cursor.execute(
        "INSERT INTO contractors (company_name, state, source_type) VALUES (?, ?, ?)",
        ("ACME HVAC LLC", "CO", "state_license")
    )
    business1_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (business1_id, "Electrical Contractor", "CO")
    )
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (business1_id, "Plumbing Contractor", "CO")
    )

    cursor.execute(
        "INSERT INTO contractors (company_name, state, source_type) VALUES (?, ?, ?)",
        ("TIC - THE INDUSTRIAL COMPANY", "CO", "state_license")
    )
    business2_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (business2_id, "Electrical Contractor", "CO")
    )
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (business2_id, "Plumbing Contractor", "CO")
    )
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (business2_id, "HVAC Contractor", "CO")
    )

    # Individuals (should be filtered out)
    cursor.execute(
        "INSERT INTO contractors (company_name, state, source_type) VALUES (?, ?, ?)",
        ("John Smith", "CO", "state_license")
    )
    individual1_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (individual1_id, "Journeyman Electrician", "CO")
    )
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (individual1_id, "Master Plumber", "CO")
    )

    # Single-trade business (should be excluded when min_trades=2)
    cursor.execute(
        "INSERT INTO contractors (company_name, state, source_type) VALUES (?, ?, ?)",
        ("Single Trade Electric Inc", "CO", "state_license")
    )
    single_trade_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (single_trade_id, "Electrical Contractor", "CO")
    )

    # Multi-trade in different state (for state filtering test)
    cursor.execute(
        "INSERT INTO contractors (company_name, state, source_type) VALUES (?, ?, ?)",
        ("Texas Multi-Trade LLC", "TX", "state_license")
    )
    tx_business_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (tx_business_id, "Electrical Contractor", "TX")
    )
    cursor.execute(
        "INSERT INTO licenses (contractor_id, license_type, state) VALUES (?, ?, ?)",
        (tx_business_id, "Plumbing Contractor", "TX")
    )

    conn.commit()
    conn.close()

    yield Path(db_path)

    # Cleanup
    Path(db_path).unlink()


class TestQueryMultiTrade:
    """Test suite for query_multi_trade_contractors function."""

    def test_returns_multi_trade_contractors(self, test_db):
        """Test 1: Query returns contractors with multiple license types."""
        results = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=False  # Include all for this test
        )

        # Should return 4 multi-trade contractors (2 CO businesses + 1 CO individual + 1 TX business)
        assert len(results) >= 3, f"Expected at least 3 multi-trade contractors, got {len(results)}"

        # Check that all returned contractors have 2+ trades
        for contractor in results:
            assert contractor['trade_count'] >= 2, \
                f"Contractor {contractor['company_name']} has only {contractor['trade_count']} trade(s)"

    def test_filters_out_individuals(self, test_db):
        """Test 2: Filter excludes individual contractors (firstname/lastname pattern)."""
        results = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=True
        )

        # Should only return business entities (not "John Smith")
        company_names = [r['company_name'] for r in results]
        assert "John Smith" not in company_names, \
            "Individual contractor 'John Smith' should be filtered out"

        # Should include business entities
        assert any("LLC" in name or "COMPANY" in name for name in company_names), \
            "Should include business entities with LLC or COMPANY"

    def test_icp_tier_assignment_platinum(self, test_db):
        """Test 3a: ICP tier assignment - PLATINUM for 3+ trades."""
        results = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=True
        )

        # Find the 3-trade contractor (TIC - THE INDUSTRIAL COMPANY)
        three_trade = [r for r in results if r['trade_count'] >= 3]
        assert len(three_trade) > 0, "Should find at least one contractor with 3+ trades"

        for contractor in three_trade:
            tier = assign_icp_tier(contractor)
            assert tier == "PLATINUM", \
                f"Contractor with {contractor['trade_count']} trades should be PLATINUM, got {tier}"

    def test_icp_tier_assignment_gold(self, test_db):
        """Test 3b: ICP tier assignment - GOLD for EC+PC combo."""
        results = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=True
        )

        # Find 2-trade contractors with EC+PC
        ec_pc_contractors = [
            r for r in results
            if r['trade_count'] == 2 and
            'Electrical Contractor' in r['license_types'] and
            'Plumbing Contractor' in r['license_types']
        ]

        assert len(ec_pc_contractors) > 0, "Should find EC+PC contractors"

        for contractor in ec_pc_contractors:
            tier = assign_icp_tier(contractor)
            assert tier == "GOLD", \
                f"EC+PC contractor should be GOLD tier, got {tier}"

    def test_state_filtering(self, test_db):
        """Test 4: State filtering returns only contractors from specified state."""
        co_results = query_multi_trade_contractors(
            db_path=test_db,
            state="CO",
            min_trades=2,
            exclude_individuals=False
        )

        # All results should be from CO
        for contractor in co_results:
            assert contractor['state'] == "CO", \
                f"Expected CO contractors only, got {contractor['state']}"

        # Should not include TX contractor
        company_names = [r['company_name'] for r in co_results]
        assert "Texas Multi-Trade LLC" not in company_names, \
            "TX contractor should not appear in CO-filtered results"

    def test_csv_export_format(self, test_db, tmp_path):
        """Test 5: CSV export creates file with correct format."""
        output_csv = tmp_path / "test_export.csv"

        query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=True,
            output_csv=output_csv
        )

        # File should exist
        assert output_csv.exists(), "CSV file should be created"

        # Read and verify content
        import csv
        with open(output_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have header row with expected columns
            assert 'company_name' in reader.fieldnames
            assert 'state' in reader.fieldnames
            assert 'trade_count' in reader.fieldnames
            assert 'license_types' in reader.fieldnames

            # Should have data rows
            assert len(rows) > 0, "CSV should contain data rows"

    def test_empty_database_handling(self):
        """Test 6: Empty database returns empty list without errors."""
        # Create empty database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                state TEXT,
                source_type TEXT DEFAULT 'state_license'
            )
        """)

        cursor.execute("""
            CREATE TABLE licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contractor_id INTEGER REFERENCES contractors(id),
                license_type TEXT,
                state TEXT
            )
        """)

        conn.commit()
        conn.close()

        try:
            results = query_multi_trade_contractors(
                db_path=Path(db_path),
                min_trades=2,
                exclude_individuals=False
            )

            assert isinstance(results, list), "Should return a list"
            assert len(results) == 0, "Empty database should return empty list"

        finally:
            Path(db_path).unlink()

    def test_min_trades_parameter(self, test_db):
        """Test 7: min_trades parameter filters correctly."""
        # Query with min_trades=2
        results_2 = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=2,
            exclude_individuals=True
        )

        # Query with min_trades=3
        results_3 = query_multi_trade_contractors(
            db_path=test_db,
            min_trades=3,
            exclude_individuals=True
        )

        # min_trades=3 should return fewer results than min_trades=2
        assert len(results_3) <= len(results_2), \
            "Higher min_trades should return same or fewer results"

        # All results from min_trades=3 should have 3+ trades
        for contractor in results_3:
            assert contractor['trade_count'] >= 3, \
                f"min_trades=3 returned contractor with only {contractor['trade_count']} trades"


class TestBusinessEntityFilter:
    """Test suite for business entity detection."""

    def test_identifies_llc_as_business(self):
        """Business entities with LLC should be identified."""
        assert is_business_entity("ACME HVAC LLC") is True
        assert is_business_entity("Smith & Sons LLC") is True

    def test_identifies_inc_as_business(self):
        """Business entities with Inc should be identified."""
        assert is_business_entity("Tech Solutions Inc") is True
        assert is_business_entity("ACME CORPORATION") is True

    def test_identifies_all_caps_as_business(self):
        """ALL CAPS company names should be identified as businesses."""
        assert is_business_entity("TIC - THE INDUSTRIAL COMPANY") is True

    def test_excludes_firstname_lastname(self):
        """Firstname Lastname pattern should be identified as individual."""
        assert is_business_entity("John Smith") is False
        assert is_business_entity("Mary Johnson") is False
        assert is_business_entity("Robert Williams") is False

    def test_includes_ampersand_pattern(self):
        """Company names with & should be identified as businesses."""
        assert is_business_entity("Smith & Sons") is True
        assert is_business_entity("Johnson & Associates") is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
