#!/usr/bin/env python3
"""
Unit tests for Pipeline Database.

Tests deduplication logic, multi-license detection, and exports.
Run with: pytest tests/test_pipeline_db.py -v
"""

import pytest
import tempfile
from pathlib import Path

from database import (
    PipelineDB,
    normalize_phone,
    normalize_email,
    extract_domain,
    normalize_company_name,
    fuzzy_match_ratio
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    db = PipelineDB(db_path)
    db.initialize()
    yield db

    # Cleanup
    try:
        db_path.unlink()
    except:
        pass


@pytest.fixture
def populated_db(temp_db):
    """Database with sample FL contractors."""
    # Add some FL contractors with different licenses
    contractors = [
        {
            'company_name': 'ABC HVAC LLC',
            'contact_name': 'John Smith',
            'email': 'john@abchvac.com',
            'phone': '555-123-4567',
            'city': 'Miami',
            'state': 'FL',
            'zip': '33101',
            'license_type': 'CAC',
            'license_category': 'HVAC'
        },
        {
            'company_name': 'XYZ Plumbing Inc',
            'contact_name': 'Jane Doe',
            'email': 'jane@xyzplumbing.com',
            'phone': '555-234-5678',
            'city': 'Orlando',
            'state': 'FL',
            'zip': '32801',
            'license_type': 'CPC',
            'license_category': 'PLUMBING'
        },
        {
            'company_name': 'Sunshine Roofing',
            'contact_name': 'Bob Johnson',
            'email': 'bob@sunshineroofing.com',
            'phone': '555-345-6789',
            'city': 'Tampa',
            'state': 'FL',
            'zip': '33601',
            'license_type': 'FRO',
            'license_category': 'ROOFING'
        },
    ]

    for record in contractors:
        temp_db.add_contractor(record, source='test')

    # Make ABC HVAC a multi-license by adding plumbing
    temp_db.add_license(1, 'FL', 'CPC', 'PLUMBING', 'CPC12345', 'test')

    return temp_db


# ============================================
# NORMALIZATION TESTS
# ============================================

class TestNormalization:
    """Tests for data normalization functions."""

    def test_normalize_phone_basic(self):
        """Basic phone normalization."""
        assert normalize_phone('555-123-4567') == '5551234567'
        assert normalize_phone('(555) 123-4567') == '5551234567'
        assert normalize_phone('555.123.4567') == '5551234567'

    def test_normalize_phone_with_country_code(self):
        """Phone with country code."""
        assert normalize_phone('+1 555-123-4567') == '5551234567'
        assert normalize_phone('1-555-123-4567') == '5551234567'

    def test_normalize_phone_invalid(self):
        """Invalid phone numbers return empty string."""
        assert normalize_phone('') == ''
        assert normalize_phone('123') == ''
        assert normalize_phone('abcdefghij') == ''

    def test_normalize_email(self):
        """Email normalization."""
        assert normalize_email('John@Example.COM') == 'john@example.com'
        assert normalize_email('  test@test.com  ') == 'test@test.com'
        assert normalize_email('') == ''

    def test_extract_domain(self):
        """Domain extraction from email."""
        assert extract_domain('john@company.com') == 'company.com'
        assert extract_domain('info@abcsolar.net') == 'abcsolar.net'

    def test_extract_domain_webmail(self):
        """Webmail domains should return empty string."""
        assert extract_domain('john@gmail.com') == ''
        assert extract_domain('jane@yahoo.com') == ''
        assert extract_domain('bob@hotmail.com') == ''
        assert extract_domain('test@aol.com') == ''

    def test_normalize_company_name(self):
        """Company name normalization."""
        assert normalize_company_name('ABC Solar LLC') == 'abc solar'
        assert normalize_company_name('XYZ Inc.') == 'xyz'
        assert normalize_company_name('Test Company, LLC') == 'test'
        assert normalize_company_name('  ABC  DEF  ') == 'abc def'

    def test_fuzzy_match_ratio(self):
        """Fuzzy matching ratio calculation."""
        # Exact match after normalization
        assert fuzzy_match_ratio('ABC Solar LLC', 'ABC Solar Inc') == 1.0

        # High similarity
        ratio = fuzzy_match_ratio('ABC Solar', 'ABC Solarr')
        assert ratio >= 0.85

        # Low similarity
        ratio = fuzzy_match_ratio('ABC Solar', 'XYZ Plumbing')
        assert ratio < 0.5


# ============================================
# DATABASE INITIALIZATION TESTS
# ============================================

class TestDatabaseInit:
    """Tests for database initialization."""

    def test_initialize_creates_tables(self, temp_db):
        """Database initialize creates all required tables."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = {row['name'] for row in cursor.fetchall()}

        expected_tables = {
            'contractors', 'contacts', 'licenses',
            'pipeline_runs', 'dedup_matches', 'oem_certifications',
            'spw_rankings'
        }
        assert expected_tables.issubset(tables)

    def test_initialize_creates_views(self, temp_db):
        """Database initialize creates all required views."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='view'
            """)
            views = {row['name'] for row in cursor.fetchall()}

        expected_views = {
            'v_multi_license', 'v_unicorns',
            'v_multi_oem', 'v_cross_state', 'v_state_stats'
        }
        assert expected_views.issubset(views)


# ============================================
# DEDUPLICATION TESTS
# ============================================

class TestDeduplication:
    """Tests for contractor deduplication."""

    def test_add_new_contractor(self, temp_db):
        """Adding a new contractor returns new=True."""
        record = {
            'company_name': 'Test Company',
            'phone': '555-111-2222',
            'email': 'test@testcompany.com',
            'state': 'FL'
        }
        contractor_id, is_new = temp_db.add_contractor(record)

        assert contractor_id > 0
        assert is_new is True

    def test_dedup_by_phone(self, temp_db):
        """Same phone number should deduplicate."""
        record1 = {
            'company_name': 'Company A',
            'phone': '555-999-8888',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'Company A Different Name',
            'phone': '555-999-8888',  # Same phone
            'state': 'FL'
        }

        id1, new1 = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        assert id1 == id2
        assert new1 is True
        assert new2 is False

    def test_dedup_by_phone_different_format(self, temp_db):
        """Phone in different formats should still match."""
        record1 = {
            'company_name': 'Company A',
            'phone': '(555) 888-7777',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'Company A',
            'phone': '555.888.7777',
            'state': 'FL'
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        assert id1 == id2
        assert new2 is False

    def test_dedup_by_email(self, temp_db):
        """Same email should deduplicate."""
        record1 = {
            'company_name': 'Email Test A',
            'email': 'unique@company.com',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'Email Test B',
            'email': 'UNIQUE@COMPANY.COM',  # Same email, different case
            'state': 'FL'
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        assert id1 == id2
        assert new2 is False

    def test_dedup_by_domain(self, temp_db):
        """Same company domain should deduplicate if names are similar."""
        record1 = {
            'company_name': 'ABC Solar LLC',
            'email': 'info@abcsolar.com',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'ABC Solar',
            'email': 'sales@abcsolar.com',  # Same domain
            'state': 'FL'
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        assert id1 == id2
        assert new2 is False

    def test_dedup_by_fuzzy_name(self, temp_db):
        """Similar names in same state should deduplicate."""
        record1 = {
            'company_name': 'Sunshine Solar Services LLC',
            'phone': '555-111-0001',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'Sunshine Solar Services Inc',  # Same name, different suffix
            'phone': '555-111-0002',  # Different phone
            'state': 'FL'
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        assert id1 == id2
        assert new2 is False

    def test_no_dedup_different_states(self, temp_db):
        """Same name in different states should NOT deduplicate."""
        record1 = {
            'company_name': 'National Solar LLC',
            'phone': '555-222-0001',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'National Solar LLC',
            'phone': '555-222-0002',
            'state': 'CA'  # Different state
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        # Should be different contractors (different states)
        assert id1 != id2
        assert new2 is True

    def test_webmail_not_used_for_domain_match(self, temp_db):
        """Gmail/Yahoo emails should NOT match on domain."""
        # Use completely different company names to avoid fuzzy matching
        record1 = {
            'company_name': 'Alpha Heating Services',
            'email': 'alpha@gmail.com',
            'phone': '555-333-0001',
            'state': 'FL'
        }
        record2 = {
            'company_name': 'Zebra Plumbing Solutions',
            'email': 'zebra@gmail.com',
            'phone': '555-333-0002',
            'state': 'FL'
        }

        id1, _ = temp_db.add_contractor(record1)
        id2, new2 = temp_db.add_contractor(record2)

        # Should be different (gmail is webmail, names are very different)
        assert id1 != id2
        assert new2 is True


# ============================================
# MULTI-LICENSE TESTS
# ============================================

class TestMultiLicense:
    """Tests for multi-license contractor detection."""

    def test_multi_license_detection(self, populated_db):
        """Contractors with 2+ categories are multi-license."""
        multi = populated_db.get_multi_license_contractors(state='FL', min_categories=2)

        # ABC HVAC has HVAC + PLUMBING
        assert len(multi) >= 1
        abc = next((c for c in multi if 'ABC' in c['company_name']), None)
        assert abc is not None
        assert abc['category_count'] >= 2

    def test_unicorn_detection(self, temp_db):
        """Contractors with 3+ categories are unicorns."""
        # Create a unicorn
        record = {
            'company_name': 'Triple Trade Inc',
            'phone': '555-444-5555',
            'state': 'FL',
            'license_type': 'CAC',
            'license_category': 'HVAC'
        }
        contractor_id, _ = temp_db.add_contractor(record)

        # Add more licenses
        temp_db.add_license(contractor_id, 'FL', 'CPC', 'PLUMBING', '', 'test')
        temp_db.add_license(contractor_id, 'FL', 'FRO', 'ROOFING', '', 'test')

        # Should be a unicorn now
        unicorns = temp_db.get_multi_license_contractors(min_categories=3)
        assert len(unicorns) >= 1
        assert any('Triple' in u['company_name'] for u in unicorns)


# ============================================
# STATS TESTS
# ============================================

class TestStats:
    """Tests for statistics queries."""

    def test_get_stats_basic(self, populated_db):
        """Basic stats query returns expected fields."""
        stats = populated_db.get_stats()

        assert 'total_contractors' in stats
        assert 'with_email' in stats
        assert 'with_phone' in stats
        assert 'multi_license' in stats
        assert 'unicorns' in stats
        assert 'categories' in stats

    def test_get_stats_by_state(self, populated_db):
        """Stats filtered by state."""
        stats = populated_db.get_stats(state='FL')

        assert stats['state'] == 'FL'
        assert stats['total_contractors'] >= 3

    def test_get_stats_categories(self, populated_db):
        """Category distribution in stats."""
        stats = populated_db.get_stats(state='FL')

        # Should have HVAC, PLUMBING, ROOFING
        categories = stats['categories']
        assert 'HVAC' in categories
        assert 'PLUMBING' in categories
        assert 'ROOFING' in categories


# ============================================
# EXPORT TESTS
# ============================================

class TestExport:
    """Tests for CSV export functionality."""

    def test_export_multi_license(self, populated_db, tmp_path):
        """Export multi-license contractors to CSV."""
        output_file = tmp_path / 'test_export.csv'

        count = populated_db.export_multi_license(
            output_file,
            state='FL',
            min_categories=2,
            require_email=False  # Include those without email for test
        )

        assert count >= 1
        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            content = f.read()
            assert 'company_name' in content
            assert 'category_count' in content

    def test_export_empty_result(self, temp_db, tmp_path):
        """Export with no results creates empty file."""
        output_file = tmp_path / 'empty_export.csv'

        count = temp_db.export_multi_license(
            output_file,
            state='ZZ',  # No contractors in this state
            min_categories=2
        )

        assert count == 0


# ============================================
# PIPELINE RUN TESTS
# ============================================

class TestPipelineRuns:
    """Tests for pipeline run tracking."""

    def test_start_and_complete_run(self, temp_db):
        """Start and complete a pipeline run."""
        run_id = temp_db.start_pipeline_run('FL', 'test_file.csv')
        assert run_id > 0

        temp_db.complete_pipeline_run(
            run_id,
            records_input=1000,
            records_new=800,
            records_merged=200,
            multi_license_found=50,
            unicorns_found=10,
            duration_seconds=5.5
        )

        runs = temp_db.get_pipeline_runs(state='FL')
        assert len(runs) >= 1
        assert runs[0]['records_input'] == 1000
        assert runs[0]['status'] == 'completed'


# ============================================
# SEARCH TESTS
# ============================================

class TestSearch:
    """Tests for contractor search."""

    def test_search_by_name(self, populated_db):
        """Search contractors by company name."""
        results = populated_db.search_contractors('ABC')

        assert len(results) >= 1
        assert any('ABC' in r['company_name'] for r in results)

    def test_search_by_phone(self, populated_db):
        """Search contractors by phone number."""
        results = populated_db.search_contractors('555-123-4567')

        assert len(results) >= 1


# ============================================
# RESET TEST
# ============================================

class TestReset:
    """Tests for database reset."""

    def test_reset_requires_confirm(self, temp_db):
        """Reset without confirm=True raises error."""
        with pytest.raises(ValueError):
            temp_db.reset_database()

    def test_reset_clears_data(self, populated_db):
        """Reset with confirm=True clears all data."""
        # Verify data exists
        stats_before = populated_db.get_stats()
        assert stats_before['total_contractors'] > 0

        # Reset
        populated_db.reset_database(confirm=True)

        # Verify data cleared
        stats_after = populated_db.get_stats()
        assert stats_after['total_contractors'] == 0


# ============================================
# INTEGRATION TEST
# ============================================

class TestIntegration:
    """Integration tests simulating real FL data loading."""

    def test_fl_style_data_loading(self, temp_db):
        """Simulate loading FL license data."""
        # Sample FL license records (similar to real data)
        fl_records = [
            {'company_name': 'COOL AIR SERVICES LLC', 'contact_name': 'MIKE JOHNSON',
             'email': 'mike@coolair.com', 'phone': '305-555-1000', 'city': 'MIAMI',
             'state': 'FL', 'zip': '33101', 'license_type': 'CAC', 'license_category': 'HVAC'},

            # Same company, different license type (multi-license!)
            {'company_name': 'COOL AIR SERVICES LLC', 'contact_name': 'MIKE JOHNSON',
             'email': 'mike@coolair.com', 'phone': '305-555-1000', 'city': 'MIAMI',
             'state': 'FL', 'zip': '33101', 'license_type': 'CPC', 'license_category': 'PLUMBING'},

            # Different company
            {'company_name': 'SUNSHINE ROOFING INC', 'contact_name': 'SARAH SMITH',
             'email': 'sarah@sunshineroofing.com', 'phone': '407-555-2000', 'city': 'ORLANDO',
             'state': 'FL', 'zip': '32801', 'license_type': 'FRO', 'license_category': 'ROOFING'},

            # Duplicate of Cool Air (different contact, same phone)
            {'company_name': 'Cool Air Services', 'contact_name': 'JANE DOE',
             'email': 'jane@coolair.com', 'phone': '305-555-1000', 'city': 'MIAMI',
             'state': 'FL', 'zip': '33101', 'license_type': 'CFC', 'license_category': 'FIRE'},
        ]

        # Track run
        run_id = temp_db.start_pipeline_run('FL', 'test_fl_data.csv')
        new_count = 0
        merged_count = 0

        for record in fl_records:
            _, is_new = temp_db.add_contractor(record, source='FL_License')
            if is_new:
                new_count += 1
            else:
                merged_count += 1

        # Complete run
        stats = temp_db.get_stats(state='FL')
        temp_db.complete_pipeline_run(
            run_id,
            records_input=len(fl_records),
            records_new=new_count,
            records_merged=merged_count,
            multi_license_found=stats['multi_license'],
            unicorns_found=stats['unicorns'],
            duration_seconds=0.5
        )

        # Verify results
        assert new_count == 2  # Only 2 unique companies
        assert merged_count == 2  # 2 merged

        # Verify deduplication rate
        dedup_rate = merged_count / len(fl_records) * 100
        assert dedup_rate == 50.0  # 2 out of 4 = 50%

        # Verify multi-license detection
        multi = temp_db.get_multi_license_contractors(state='FL')
        assert len(multi) >= 1

        # Cool Air should have 3 categories now (HVAC, PLUMBING, FIRE)
        cool_air = next((c for c in multi if 'COOL' in c['company_name'].upper()), None)
        assert cool_air is not None
        assert cool_air['category_count'] == 3  # UNICORN!


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
