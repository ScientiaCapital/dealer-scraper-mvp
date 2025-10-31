"""
Apollo.io Enrichment API Client

Enriches contractor data with company and contact information from Apollo.io.

Key Fields Enriched:
- Employee count (for commercial capability scoring)
- Revenue estimate
- Decision-maker emails (Owner, GM, Operations Manager)
- LinkedIn profiles (company + contacts)

Apollo.io API Documentation:
https://apolloio.github.io/apollo-api-docs/

Rate Limits:
- Free tier: 100 calls/minute
- Basic plan: 200 calls/minute
- Professional: 500 calls/minute
"""

import os
import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ApolloCompanyData:
    """
    Enriched company data from Apollo.io
    """
    # Company identification
    apollo_id: str
    name: str
    domain: str

    # Company size and revenue
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None  # "1-10", "11-50", "51-200", etc.
    estimated_annual_revenue: Optional[str] = None  # "$1M-$10M", "$10M-$50M", etc.

    # Contact information
    decision_maker_emails: List[str] = None
    decision_maker_names: List[str] = None

    # LinkedIn profiles
    company_linkedin_url: Optional[str] = None
    contact_linkedin_urls: List[str] = None

    # Metadata
    industry: Optional[str] = None
    founded_year: Optional[int] = None
    confidence_score: float = 0.0  # How confident Apollo is in the match

    def __post_init__(self):
        # Initialize lists if None
        if self.decision_maker_emails is None:
            self.decision_maker_emails = []
        if self.decision_maker_names is None:
            self.decision_maker_names = []
        if self.contact_linkedin_urls is None:
            self.contact_linkedin_urls = []


class ApolloEnricher:
    """
    Apollo.io API client for contractor enrichment.

    Usage:
        enricher = ApolloEnricher(api_key="your_apollo_api_key")
        company_data = enricher.enrich_company(domain="example.com", name="Example Corp")

        if company_data:
            print(f"Employees: {company_data.employee_count}")
            print(f"Revenue: {company_data.estimated_annual_revenue}")
            print(f"Decision Makers: {company_data.decision_maker_emails}")
    """

    API_BASE_URL = "https://api.apollo.io/v1"
    DEFAULT_RATE_LIMIT = 100  # calls per minute

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Apollo enricher.

        Args:
            api_key: Apollo.io API key. If None, reads from APOLLO_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        if not self.api_key:
            raise ValueError("Apollo API key required. Set APOLLO_API_KEY in .env or pass to constructor.")

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        })

        # Rate limiting
        self.call_timestamps = []
        self.rate_limit = self.DEFAULT_RATE_LIMIT

    def _rate_limit_check(self):
        """
        Enforce rate limiting (100 calls per minute default).
        Blocks until safe to make next API call.
        """
        now = time.time()
        # Remove timestamps older than 60 seconds
        self.call_timestamps = [ts for ts in self.call_timestamps if now - ts < 60]

        if len(self.call_timestamps) >= self.rate_limit:
            # Wait until oldest call is 60 seconds old
            sleep_time = 60 - (now - self.call_timestamps[0])
            if sleep_time > 0:
                print(f"[Apollo] Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                # Retry rate limit check
                self._rate_limit_check()

        self.call_timestamps.append(now)

    def search_company(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None,
        location: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Search for a company in Apollo database.

        Search priority:
        1. Domain (most accurate)
        2. Name + location (fallback)
        3. Name only (least accurate)

        Args:
            domain: Company domain (e.g., "example.com")
            name: Company name
            location: City, state or full address

        Returns:
            Raw company dict from Apollo API, or None if not found
        """
        self._rate_limit_check()

        # Build search payload
        payload = {
            "api_key": self.api_key,
            "per_page": 1  # Only need top match
        }

        # Priority 1: Search by domain (most accurate)
        if domain:
            payload["organization_domains"] = [domain]

        # Priority 2: Search by name + location
        if name:
            payload["organization_name"] = name

        if location:
            payload["organization_locations"] = [location]

        try:
            response = self.session.post(
                f"{self.API_BASE_URL}/mixed_companies/search",
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            organizations = data.get("organizations", [])

            if organizations:
                return organizations[0]  # Return top match

            return None

        except requests.exceptions.RequestException as e:
            print(f"[Apollo] Company search failed: {str(e)}")
            return None

    def get_contacts(self, organization_id: str, titles: Optional[List[str]] = None) -> List[Dict]:
        """
        Get contacts (decision-makers) for a company.

        Args:
            organization_id: Apollo organization ID
            titles: Contact titles to search for (e.g., ["Owner", "General Manager", "Operations Manager"])

        Returns:
            List of contact dicts with emails, names, LinkedIn profiles
        """
        self._rate_limit_check()

        # Default decision-maker titles for contractors
        if titles is None:
            titles = [
                "Owner",
                "Co-Owner",
                "General Manager",
                "Operations Manager",
                "Director of Operations",
                "VP Operations",
                "President",
                "CEO"
            ]

        payload = {
            "api_key": self.api_key,
            "organization_ids": [organization_id],
            "person_titles": titles,
            "per_page": 10,  # Get up to 10 decision-makers
        }

        try:
            response = self.session.post(
                f"{self.API_BASE_URL}/mixed_people/search",
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            people = data.get("people", [])

            return people

        except requests.exceptions.RequestException as e:
            print(f"[Apollo] Contact search failed: {str(e)}")
            return []

    def enrich_company(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None,
        location: Optional[str] = None,
        include_contacts: bool = True
    ) -> Optional[ApolloCompanyData]:
        """
        Enrich a company with Apollo data.

        Args:
            domain: Company domain
            name: Company name
            location: Location (city, state)
            include_contacts: Whether to fetch decision-maker contacts (extra API call)

        Returns:
            ApolloCompanyData object, or None if company not found
        """
        print(f"[Apollo] Searching for company: {name or domain}")

        # Step 1: Search for company
        company = self.search_company(domain=domain, name=name, location=location)

        if not company:
            print(f"[Apollo] Company not found: {name or domain}")
            return None

        print(f"[Apollo] Found company: {company.get('name')}")

        # Step 2: Extract company data
        company_data = ApolloCompanyData(
            apollo_id=company.get("id"),
            name=company.get("name", ""),
            domain=company.get("primary_domain", domain or ""),
            employee_count=company.get("estimated_num_employees"),
            employee_range=self._get_employee_range(company.get("estimated_num_employees")),
            estimated_annual_revenue=company.get("estimated_annual_revenue"),
            company_linkedin_url=company.get("linkedin_url"),
            industry=company.get("industry"),
            founded_year=company.get("founded_year"),
        )

        # Step 3: Get decision-maker contacts (optional)
        if include_contacts:
            contacts = self.get_contacts(company_data.apollo_id)

            for contact in contacts:
                # Extract email
                email = contact.get("email")
                if email:
                    company_data.decision_maker_emails.append(email)

                # Extract name
                name = contact.get("name")
                if name:
                    company_data.decision_maker_names.append(name)

                # Extract LinkedIn
                linkedin_url = contact.get("linkedin_url")
                if linkedin_url:
                    company_data.contact_linkedin_urls.append(linkedin_url)

            print(f"[Apollo] Found {len(company_data.decision_maker_emails)} decision-maker emails")

        return company_data

    @staticmethod
    def _get_employee_range(employee_count: Optional[int]) -> Optional[str]:
        """
        Convert exact employee count to range string for scoring.

        Args:
            employee_count: Exact number of employees

        Returns:
            Range string like "1-10", "11-50", "51-200", etc.
        """
        if employee_count is None:
            return None

        if employee_count < 5:
            return "1-4"
        elif employee_count < 10:
            return "5-9"
        elif employee_count < 50:
            return "10-49"
        elif employee_count < 200:
            return "50-199"
        elif employee_count < 500:
            return "200-499"
        elif employee_count < 1000:
            return "500-999"
        else:
            return "1000+"

    def batch_enrich(
        self,
        companies: List[Dict[str, str]],
        include_contacts: bool = True
    ) -> Dict[str, Optional[ApolloCompanyData]]:
        """
        Enrich multiple companies in batch.

        Args:
            companies: List of dicts with 'domain', 'name', 'location' keys
            include_contacts: Whether to fetch decision-maker contacts

        Returns:
            Dict mapping domain/name to ApolloCompanyData (or None if not found)
        """
        results = {}

        for i, company in enumerate(companies, 1):
            print(f"[Apollo] Enriching {i}/{len(companies)}: {company.get('name')}")

            enriched = self.enrich_company(
                domain=company.get("domain"),
                name=company.get("name"),
                location=company.get("location"),
                include_contacts=include_contacts
            )

            # Use domain or name as key
            key = company.get("domain") or company.get("name")
            results[key] = enriched

        # Summary
        found_count = sum(1 for v in results.values() if v is not None)
        print(f"\n[Apollo] Enrichment complete: {found_count}/{len(companies)} found")

        return results


# Example usage
if __name__ == "__main__":
    # Test enrichment
    enricher = ApolloEnricher()

    # Test with a known company
    result = enricher.enrich_company(
        domain="generac.com",
        name="Generac Power Systems",
        include_contacts=True
    )

    if result:
        print(f"\nCompany: {result.name}")
        print(f"Domain: {result.domain}")
        print(f"Employees: {result.employee_count} ({result.employee_range})")
        print(f"Revenue: {result.estimated_annual_revenue}")
        print(f"Industry: {result.industry}")
        print(f"LinkedIn: {result.company_linkedin_url}")
        print(f"Decision Makers: {len(result.decision_maker_emails)}")
        for email in result.decision_maker_emails[:3]:
            print(f"  - {email}")
    else:
        print("Company not found in Apollo")
