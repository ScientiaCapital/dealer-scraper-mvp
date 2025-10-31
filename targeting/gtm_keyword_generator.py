"""
GTM Keyword Generator for Marketing Campaigns

Generates SEO keywords, Google AdWords keywords, and LinkedIn search queries
for each dealer to enable targeted marketing campaigns by Coperniq's GTM team.

Also evaluates MEP+R (Mechanical, Electrical, Plumbing + Renewables) capabilities
to identify self-performing contractors (highest value targets).
"""

from typing import List, Set
from scrapers.base_scraper import StandardizedDealer, DealerCapabilities


class GTMKeywordGenerator:
    """
    Generate marketing keywords and evaluate MEP+R characteristics.

    MEP+R contractors who are self-performing are Coperniq's ICP (Ideal Customer Profile):
    - They manage complex multi-system installations
    - They have technical crews (not just sales teams)
    - They juggle generators, solar, batteries, HVAC - perfect for unified monitoring
    """

    # Keywords that indicate self-performing contractor (not just broker/sales)
    SELF_PERFORMING_INDICATORS = [
        "electric", "electrical", "hvac", "plumbing", "mechanical",
        "service", "install", "construction", "contracting", "contractor",
        "systems", "solutions", "technical", "engineering", "crew"
    ]

    # Keywords to exclude (indicate sales-only or broker)
    BROKER_INDICATORS = [
        "marketing", "consulting", "broker", "lead", "sales only",
        "referral", "financing", "advisor"
    ]

    @staticmethod
    def generate_seo_keywords(dealer: StandardizedDealer) -> str:
        """
        Generate SEO keywords for organic search targeting.

        Format: "product service city state brand terms"
        Example: "generator installer San Francisco CA Generac Tesla solar battery"
        """
        keywords = []

        # Add company name (exact match)
        keywords.append(dealer.name.lower())

        # Add location keywords
        if dealer.city:
            keywords.append(f"{dealer.city.lower()} {dealer.state}")
            keywords.append(f"{dealer.city.lower()}")
        if dealer.zip:
            keywords.append(dealer.zip)

        # Add product capabilities
        capabilities = dealer.capabilities
        if capabilities.has_generator:
            keywords.extend(["generator installer", "generator dealer", "backup power"])
        if capabilities.has_solar:
            keywords.extend(["solar installer", "solar contractor", "solar panels"])
        if capabilities.has_battery:
            keywords.extend(["battery backup", "energy storage", "powerwall installer"])
        if capabilities.has_microinverters:
            keywords.extend(["microinverter installer", "enphase installer"])

        # Add trade capabilities
        if capabilities.has_electrical:
            keywords.append("electrical contractor")
        if capabilities.has_hvac:
            keywords.append("hvac contractor")
        if capabilities.has_plumbing:
            keywords.append("plumbing contractor")

        # Add OEM certifications
        for oem in capabilities.oem_certifications:
            keywords.append(f"{oem.lower()} dealer")
            keywords.append(f"{oem.lower()} installer")

        # Add commercial/residential focus
        if capabilities.is_commercial:
            keywords.append("commercial installer")
        if capabilities.is_residential:
            keywords.append("residential installer")

        # Remove duplicates and join
        unique_keywords = list(dict.fromkeys(keywords))
        return ", ".join(unique_keywords[:20])  # Limit to top 20 keywords

    @staticmethod
    def generate_adwords_keywords(dealer: StandardizedDealer) -> str:
        """
        Generate Google AdWords keywords for PPC campaigns.

        Focus on high-intent commercial keywords with brand terms.
        Format: "[exact match] +broad +match "phrase match""
        """
        keywords = []

        # Exact match keywords (highest intent)
        exact_matches = []

        # Company name exact match
        exact_matches.append(f'[{dealer.name.lower()}]')

        # Location + service exact matches
        if dealer.city:
            if dealer.capabilities.has_generator:
                exact_matches.append(f'[{dealer.city.lower()} generator installer]')
            if dealer.capabilities.has_solar:
                exact_matches.append(f'[{dealer.city.lower()} solar installer]')
            if dealer.capabilities.has_battery:
                exact_matches.append(f'[{dealer.city.lower()} battery backup]')

        # Broad match modifiers (wider reach)
        broad_matches = []

        # Product + location broad matches
        if dealer.state:
            broad_matches.append(f'+{dealer.state.lower()} +generator +monitoring')
            broad_matches.append(f'+{dealer.state.lower()} +solar +monitoring')
            broad_matches.append(f'+{dealer.state.lower()} +battery +monitoring')

        # Competitor + alternative broad matches (intercept searches)
        for oem in dealer.capabilities.oem_certifications:
            broad_matches.append(f'+{oem.lower()} +monitoring +alternative')
            broad_matches.append(f'+{oem.lower()} +monitoring +software')

        # Phrase matches (balanced approach)
        phrase_matches = []

        # Pain point phrases
        phrase_matches.append('"multiple monitoring platforms"')
        phrase_matches.append('"generator solar monitoring"')
        phrase_matches.append('"unified monitoring platform"')

        # Commercial intent phrases
        if dealer.capabilities.is_commercial:
            phrase_matches.append('"commercial energy monitoring"')
            phrase_matches.append('"commercial generator monitoring"')

        # Combine all keyword types
        all_keywords = exact_matches[:5] + broad_matches[:10] + phrase_matches[:5]
        return " ".join(all_keywords)

    @staticmethod
    def generate_meta_ads_targeting(dealer: StandardizedDealer) -> tuple[str, str]:
        """
        Generate Meta (Facebook/Instagram) ads targeting parameters.

        Meta uses interest-based and behavioral targeting, not keywords.
        Returns: (targeting_params, custom_audience_category)
        """
        # Interest targeting
        interests = []

        # Industry interests
        if dealer.capabilities.has_generator:
            interests.extend(["Backup generators", "Emergency preparedness", "Power outages"])
        if dealer.capabilities.has_solar:
            interests.extend(["Solar energy", "Solar power", "Renewable energy", "Green energy"])
        if dealer.capabilities.has_battery:
            interests.extend(["Energy storage", "Tesla Powerwall", "Home batteries"])
        if dealer.capabilities.has_electrical:
            interests.extend(["Electrical contractor", "Electrician", "Electrical work"])
        if dealer.capabilities.has_hvac:
            interests.extend(["HVAC contractor", "Air conditioning", "Heating contractor"])

        # Business interests
        interests.extend(["Small business owners", "Contractor", "Construction business"])

        # Job title targeting
        job_titles = [
            "Business Owner",
            "President",
            "Chief Executive Officer",
            "Operations Manager",
            "General Manager",
            "Service Manager",
            "Owner Operator"
        ]

        # Behaviors
        behaviors = [
            "Small business owners",
            "Business decision makers",
            "B2B decision makers"
        ]

        # Special targeting for O&M providers
        if dealer.has_ops_maintenance:
            interests.extend(["Service contracts", "Maintenance services", "Fleet management"])
            behaviors.append("Business page admins")

        # Special targeting for resimercial
        if dealer.is_resimercial:
            interests.extend(["Commercial construction", "Residential construction"])
            behaviors.append("Likely to move")  # New construction opportunities

        # Geographic targeting
        geo_params = []
        if dealer.city and dealer.state:
            geo_params.append(f"location: {dealer.city}, {dealer.state}")
            geo_params.append("radius: 25 miles")
        elif dealer.state:
            geo_params.append(f"location: {dealer.state}")

        # Build targeting string
        targeting_parts = []
        targeting_parts.append(f"Interests: {', '.join(interests[:10])}")
        targeting_parts.append(f"Job Titles: {', '.join(job_titles[:5])}")
        targeting_parts.append(f"Behaviors: {', '.join(behaviors[:3])}")
        if geo_params:
            targeting_parts.append(f"Geo: {'; '.join(geo_params)}")

        targeting_string = " | ".join(targeting_parts)

        # Determine custom audience category for upload
        audience_categories = []

        # Primary category based on capabilities
        if dealer.capabilities.has_generator and dealer.capabilities.has_solar:
            audience_categories.append("GENERATOR_SOLAR_HYBRID")
        elif dealer.capabilities.has_generator:
            audience_categories.append("GENERATOR_DEALER")
        elif dealer.capabilities.has_solar:
            audience_categories.append("SOLAR_INSTALLER")

        # Premium categories
        if dealer.has_ops_maintenance:
            audience_categories.append("OPS_MAINTENANCE_PROVIDER")
        if dealer.is_resimercial:
            audience_categories.append("RESIMERCIAL_CONTRACTOR")
        if dealer.is_mep_contractor and dealer.is_self_performing:
            audience_categories.append("MEP_SELF_PERFORMING")

        # Multi-OEM category
        oem_count = len(dealer.capabilities.oem_certifications)
        if oem_count >= 3:
            audience_categories.append("MULTI_OEM_PREMIUM")
        elif oem_count >= 2:
            audience_categories.append("MULTI_OEM_STANDARD")

        custom_audience = ", ".join(audience_categories[:3])  # Top 3 categories

        return targeting_string, custom_audience

    @staticmethod
    def generate_linkedin_query(dealer: StandardizedDealer) -> str:
        """
        Generate LinkedIn Sales Navigator search query.

        Target: Owner, President, Operations Manager, Service Manager
        at companies with MEP+R capabilities.
        """
        # Company name filter
        query_parts = [f'company:"{dealer.name}"']

        # Title filters for decision makers
        titles = [
            'title:"owner"',
            'title:"president"',
            'title:"operations manager"',
            'title:"service manager"',
            'title:"general manager"'
        ]
        query_parts.append(f'({" OR ".join(titles)})')

        # Industry filters
        industries = []
        if dealer.capabilities.has_electrical:
            industries.append('industry:"electrical"')
        if dealer.capabilities.has_hvac:
            industries.append('industry:"hvac"')
        if dealer.capabilities.has_solar:
            industries.append('industry:"solar"')
        if dealer.capabilities.has_generator:
            industries.append('industry:"power generation"')

        if industries:
            query_parts.append(f'({" OR ".join(industries[:3])})')

        # Location filter
        if dealer.city and dealer.state:
            query_parts.append(f'location:"{dealer.city}, {dealer.state}"')

        return " AND ".join(query_parts)

    @staticmethod
    def evaluate_mep_contractor(dealer: StandardizedDealer) -> tuple[bool, bool, int, bool, bool]:
        """
        Evaluate if dealer is an MEP+R contractor, self-performing, O&M provider, and resimercial.

        Returns:
            (is_mep_contractor, is_self_performing, mep_score, has_ops_maintenance, is_resimercial)
        """
        capabilities = dealer.capabilities

        # Check for O&M services (from capabilities or certifications)
        has_ops_maintenance = False
        if hasattr(dealer, 'capabilities') and hasattr(dealer.capabilities, 'capabilities'):
            # Check if "Ops & Maintenance" is in capabilities list (from Enphase)
            if isinstance(dealer.capabilities.capabilities, list):
                has_ops_maintenance = "Ops & Maintenance" in dealer.capabilities.capabilities

        # Also check certifications
        for cert in dealer.certifications:
            if "maintenance" in cert.lower() or "service" in cert.lower() or "O&M" in cert:
                has_ops_maintenance = True
                break

        # Check for resimercial (both residential AND commercial)
        is_resimercial = capabilities.is_residential and capabilities.is_commercial

        # Check MEP capabilities
        mep_count = 0
        if capabilities.has_electrical:
            mep_count += 1
        if capabilities.has_hvac:
            mep_count += 1
        if capabilities.has_plumbing:
            mep_count += 1

        # MEP contractor = has at least 2 of the 3 MEP trades
        is_mep = mep_count >= 2

        # Check renewables/weatherization
        renewables_count = 0
        if capabilities.has_solar:
            renewables_count += 1
        if capabilities.has_battery:
            renewables_count += 1
        if capabilities.has_generator:
            renewables_count += 1
        if capabilities.has_microinverters:
            renewables_count += 1

        # Check if self-performing (not just broker/sales)
        name_lower = dealer.name.lower()

        # Positive indicators
        self_performing_score = 0
        for indicator in GTMKeywordGenerator.SELF_PERFORMING_INDICATORS:
            if indicator in name_lower:
                self_performing_score += 10

        # Check for technical certifications
        if dealer.tier in ["Platinum", "Premier", "PowerPro", "Gold"]:
            self_performing_score += 20

        # Negative indicators (broker/sales only)
        for indicator in GTMKeywordGenerator.BROKER_INDICATORS:
            if indicator in name_lower:
                self_performing_score -= 30

        # Employee count indicates real operations
        if dealer.employee_count:
            if dealer.employee_count > 10:
                self_performing_score += 20
            if dealer.employee_count > 50:
                self_performing_score += 20

        is_self_performing = self_performing_score >= 30

        # Calculate MEP+R score (0-100)
        mep_score = 0

        # MEP trades (30 points max)
        mep_score += mep_count * 10  # 30 points for all 3

        # Renewables (25 points max)
        mep_score += min(renewables_count * 8, 25)

        # Self-performing bonus (15 points)
        if is_self_performing:
            mep_score += 15

        # O&M provider bonus (15 points) - premium target
        if has_ops_maintenance:
            mep_score += 15

        # Resimercial bonus (10 points) - diverse portfolio
        if is_resimercial:
            mep_score += 10

        # Commercial capability (5 points)
        if capabilities.is_commercial and not is_resimercial:  # Don't double count
            mep_score += 5

        # Cap at 100
        mep_score = min(mep_score, 100)

        return is_mep, is_self_performing, mep_score, has_ops_maintenance, is_resimercial

    @classmethod
    def enrich_dealer_with_keywords(cls, dealer: StandardizedDealer) -> StandardizedDealer:
        """
        Add GTM keywords and MEP+R evaluation to dealer record.

        Args:
            dealer: StandardizedDealer to enrich

        Returns:
            Enriched StandardizedDealer with marketing keywords
        """
        # Evaluate MEP+R characteristics first (needed for Meta targeting)
        is_mep, is_self_performing, mep_score, has_ops_maintenance, is_resimercial = cls.evaluate_mep_contractor(dealer)
        dealer.is_mep_contractor = is_mep
        dealer.is_self_performing = is_self_performing
        dealer.mep_score = mep_score
        dealer.has_ops_maintenance = has_ops_maintenance
        dealer.is_resimercial = is_resimercial

        # Generate keywords (after evaluation so Meta can use the flags)
        dealer.seo_keywords = cls.generate_seo_keywords(dealer)
        dealer.adwords_keywords = cls.generate_adwords_keywords(dealer)
        dealer.linkedin_search_query = cls.generate_linkedin_query(dealer)

        # Generate Meta ads targeting
        meta_targeting, custom_audience = cls.generate_meta_ads_targeting(dealer)
        dealer.meta_ads_targeting = meta_targeting
        dealer.meta_custom_audience = custom_audience

        return dealer

    @classmethod
    def enrich_dealers_batch(cls, dealers: List[StandardizedDealer]) -> List[StandardizedDealer]:
        """
        Enrich multiple dealers with GTM keywords and MEP+R scores.

        Args:
            dealers: List of StandardizedDealer objects

        Returns:
            List of enriched StandardizedDealer objects
        """
        enriched_dealers = []

        for dealer in dealers:
            enriched_dealer = cls.enrich_dealer_with_keywords(dealer)
            enriched_dealers.append(enriched_dealer)

        # Sort by MEP score (highest first)
        enriched_dealers.sort(key=lambda d: d.mep_score, reverse=True)

        # Log summary
        mep_contractors = sum(1 for d in enriched_dealers if d.is_mep_contractor)
        self_performing = sum(1 for d in enriched_dealers if d.is_self_performing)
        ops_maintenance = sum(1 for d in enriched_dealers if d.has_ops_maintenance)
        resimercial = sum(1 for d in enriched_dealers if d.is_resimercial)

        print(f"GTM Enrichment Summary:")
        print(f"  Total dealers: {len(enriched_dealers)}")
        print(f"  MEP contractors: {mep_contractors}")
        print(f"  Self-performing: {self_performing}")
        print(f"  O&M providers: {ops_maintenance} (premium targets!)")
        print(f"  Resimercial: {resimercial} (residential + commercial)")
        print(f"  Top MEP+R scores: {[d.mep_score for d in enriched_dealers[:5]]}")

        return enriched_dealers


# Example usage
if __name__ == "__main__":
    # Test with a sample dealer
    from scrapers.base_scraper import DealerCapabilities

    # Create test dealer
    caps = DealerCapabilities()
    caps.has_generator = True
    caps.has_solar = True
    caps.has_battery = True
    caps.has_electrical = True
    caps.has_hvac = True
    caps.is_commercial = True
    caps.oem_certifications = {"Generac", "Tesla", "Enphase"}

    dealer = StandardizedDealer(
        name="ABC Electrical & HVAC Systems",
        phone="555-555-5555",
        domain="abcelectrical.com",
        website="https://abcelectrical.com",
        street="123 Main St",
        city="San Francisco",
        state="CA",
        zip="94102",
        address_full="123 Main St, San Francisco, CA 94102",
        capabilities=caps,
        tier="Premier",
        employee_count=25,
        oem_source="Generac"
    )

    # Enrich with keywords
    enriched = GTMKeywordGenerator.enrich_dealer_with_keywords(dealer)

    print("SEO Keywords:")
    print(f"  {enriched.seo_keywords}\n")

    print("AdWords Keywords:")
    print(f"  {enriched.adwords_keywords}\n")

    print("LinkedIn Query:")
    print(f"  {enriched.linkedin_search_query}\n")

    print("MEP+R Evaluation:")
    print(f"  MEP Contractor: {enriched.is_mep_contractor}")
    print(f"  Self-Performing: {enriched.is_self_performing}")
    print(f"  MEP Score: {enriched.mep_score}/100")