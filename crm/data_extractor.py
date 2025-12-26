"""
Data Extractor for Close CRM Sync

Extracts contractor data from SQLite or Supabase for syncing to Close CRM.
Aggregates OEM certifications and state licenses per contractor.
"""

import os
import ast
import sqlite3
from pathlib import Path
from typing import Iterator, Dict, Any, Optional, List
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv(override=True)


class DataExtractor:
    """
    Extracts contractor data with OEM certifications and licenses.

    Supports SQLite and Supabase data sources.
    """

    DEFAULT_SQLITE_PATH = Path("data/pipeline.db")

    def __init__(
        self,
        source: str = "sqlite",
        db_path: Optional[Path] = None,
    ):
        """
        Initialize data extractor.

        Args:
            source: Data source type ("sqlite" or "supabase")
            db_path: Path to SQLite database (for sqlite source)
        """
        self.source = source
        self.db_path = db_path or self.DEFAULT_SQLITE_PATH

    def extract_contractors(
        self,
        limit: Optional[int] = None,
        state_filter: Optional[str] = None,
        oem_filter: Optional[str] = None,
        min_oem_count: int = 0,
    ) -> Iterator[Dict[str, Any]]:
        """
        Extract contractors with all related data.

        Args:
            limit: Maximum number of contractors to extract
            state_filter: Filter by state code (e.g., "TX", "CA")
            oem_filter: Filter by OEM name (e.g., "Generac", "Tesla")
            min_oem_count: Minimum number of OEM certifications required

        Yields:
            Contractor dicts with oem_certifications and state_licenses
        """
        if self.source == "sqlite":
            yield from self._extract_from_sqlite(
                limit=limit,
                state_filter=state_filter,
                oem_filter=oem_filter,
                min_oem_count=min_oem_count,
            )
        elif self.source == "supabase":
            yield from self._extract_from_supabase(
                limit=limit,
                state_filter=state_filter,
                oem_filter=oem_filter,
                min_oem_count=min_oem_count,
            )
        else:
            raise ValueError(f"Unknown source: {self.source}")

    def _extract_from_sqlite(
        self,
        limit: Optional[int] = None,
        state_filter: Optional[str] = None,
        oem_filter: Optional[str] = None,
        min_oem_count: int = 0,
    ) -> Iterator[Dict[str, Any]]:
        """Extract contractors from SQLite database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Build contractor query with filters
        query = "SELECT * FROM contractors WHERE 1=1"
        params: List[Any] = []

        if state_filter:
            query += " AND state = ?"
            params.append(state_filter)

        if limit:
            query += f" LIMIT {int(limit)}"

        # Load all contractors
        cur.execute(query, params)
        contractors = [dict(row) for row in cur.fetchall()]

        # Load OEM certifications for all contractors
        oem_by_contractor = self._load_oem_certifications(cur)

        # Load licenses for all contractors
        licenses_by_contractor = self._load_licenses(cur)

        conn.close()

        # Yield contractors with aggregated data
        for contractor in contractors:
            cid = contractor["id"]

            # Get OEM certifications
            oem_certs = oem_by_contractor.get(cid, [])
            oem_names = [c["oem_name"] for c in oem_certs]
            oem_tiers = {c["oem_name"]: c.get("tier", "") for c in oem_certs}

            # Apply OEM filter
            if oem_filter and oem_filter not in oem_names:
                continue

            # Apply min OEM count filter
            if len(oem_names) < min_oem_count:
                continue

            # Get licenses
            licenses = licenses_by_contractor.get(cid, [])
            state_licenses = list(set(lic["state"] for lic in licenses))
            license_types = defaultdict(list)
            for lic in licenses:
                license_types[lic["state"]].append(lic["license_type"])

            # Determine source type
            source_type = self._determine_source_type(oem_certs, licenses)

            yield {
                "id": cid,
                "company_name": contractor.get("company_name", ""),
                "city": contractor.get("city", ""),
                "state": contractor.get("state", ""),
                "zip_code": contractor.get("zip", ""),
                "primary_phone": contractor.get("primary_phone"),
                "primary_email": contractor.get("primary_email"),
                "website_url": contractor.get("website_url"),
                "oem_certifications": oem_names,
                "oem_tiers": oem_tiers,
                "state_licenses": state_licenses,
                "license_types": dict(license_types),
                "source_type": source_type,
                "coperniq_score": contractor.get("icp_score", 0),
            }

    def _load_oem_certifications(self, cur: sqlite3.Cursor) -> Dict[int, List[Dict]]:
        """Load all OEM certifications grouped by contractor ID."""
        result = defaultdict(list)

        cur.execute("""
            SELECT contractor_id, oem_name, tier
            FROM oem_certifications
        """)

        for row in cur.fetchall():
            result[row["contractor_id"]].append({
                "oem_name": row["oem_name"],
                "tier": row["tier"],
            })

        return result

    def _load_licenses(self, cur: sqlite3.Cursor) -> Dict[int, List[Dict]]:
        """Load all licenses grouped by contractor ID."""
        result = defaultdict(list)

        cur.execute("""
            SELECT contractor_id, state, license_type
            FROM licenses
        """)

        for row in cur.fetchall():
            result[row["contractor_id"]].append({
                "state": row["state"],
                "license_type": row["license_type"],
            })

        return result

    def _determine_source_type(
        self,
        oem_certs: List[Dict],
        licenses: List[Dict],
    ) -> str:
        """
        Determine source type based on available data.

        Returns:
            "oem_dealer" if only OEM certs
            "state_license" if only licenses
            "both" if has both
        """
        has_oem = len(oem_certs) > 0
        has_license = len(licenses) > 0

        if has_oem and has_license:
            return "both"
        elif has_oem:
            return "oem_dealer"
        elif has_license:
            return "state_license"
        else:
            return "unknown"

    def _extract_from_supabase(
        self,
        limit: Optional[int] = None,
        state_filter: Optional[str] = None,
        oem_filter: Optional[str] = None,
        min_oem_count: int = 0,
    ) -> Iterator[Dict[str, Any]]:
        """Extract contractors from Supabase dim_companies table."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            print("Warning: SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
            return

        # Build query URL with filters
        base_url = f"{supabase_url}/rest/v1/dim_companies"
        params = ["select=*"]

        if state_filter:
            params.append(f"state=eq.{state_filter}")

        if min_oem_count > 0:
            # Filter for non-empty oem_brands array
            params.append("oem_brands=not.eq.{}")

        if limit:
            params.append(f"limit={limit}")

        # Order by OEM dealers first (those with oem_brands), then by ICP score
        params.append("order=oem_brands.desc.nullslast,icp_score.desc.nullslast")

        url = f"{base_url}?{'&'.join(params)}"

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            rows = response.json()
        except Exception as e:
            print(f"Supabase query failed: {e}")
            return

        for row in rows:
            # Parse oem_brands - may be stored as string repr of list
            oem_brands_raw = row.get("oem_brands")
            if isinstance(oem_brands_raw, str) and oem_brands_raw.startswith("["):
                try:
                    oem_brands = ast.literal_eval(oem_brands_raw)
                except (ValueError, SyntaxError):
                    oem_brands = []
            elif isinstance(oem_brands_raw, list):
                oem_brands = oem_brands_raw
            else:
                oem_brands = []

            # Parse license_types similarly
            license_types_raw = row.get("license_types")
            if isinstance(license_types_raw, str) and license_types_raw.startswith("["):
                try:
                    license_types = ast.literal_eval(license_types_raw)
                except (ValueError, SyntaxError):
                    license_types = []
            elif isinstance(license_types_raw, list):
                license_types = license_types_raw
            else:
                license_types = []

            # Apply OEM filter (check if OEM is in the brands list)
            if oem_filter and oem_filter not in oem_brands:
                continue

            # Determine source type
            has_oem = len(oem_brands) > 0
            has_license = len(license_types) > 0
            if has_oem and has_license:
                source_type = "both"
            elif has_oem:
                source_type = "oem_dealer"
            elif has_license:
                source_type = "state_license"
            else:
                source_type = row.get("source_type", "unknown")

            yield {
                "id": row.get("company_id"),
                "company_name": row.get("company_name", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "zip_code": row.get("zip", ""),
                "primary_phone": row.get("phone"),
                "primary_email": None,  # dim_companies doesn't have email directly
                "website_url": row.get("website"),
                "oem_certifications": oem_brands,
                "oem_tiers": {},  # Not stored in dim_companies
                "state_licenses": license_types,
                "license_types": {},
                "source_type": source_type,
                "coperniq_score": row.get("icp_score", 0),
            }
