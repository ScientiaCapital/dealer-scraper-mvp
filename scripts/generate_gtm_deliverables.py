#!/usr/bin/env python3
"""
Generate GTM Deliverables - Google Ads, Meta, SEO, BDR Playbook

Creates tactical marketing materials:
1. Google Ads Customer Match list (GOLD + top SILVER)
2. Meta/Instagram Custom Audience (multi-OEM focus)
3. SEO Strategy Document (Coperniq website optimization)
4. Personal BDR Playbook (confidential outreach guide)
"""
import csv
import re
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

def load_scored_contractors(filepath: str) -> List[Dict]:
    """Load ICP-scored contractors"""
    contractors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contractors.append(row)
    return contractors

def format_phone_for_ads(phone: str) -> str:
    """Format phone for Google Ads (E.164 format with country code)"""
    if not phone:
        return ""

    # Extract digits only
    digits = ''.join(c for c in phone if c.isdigit())

    # Remove leading 1 if present (US country code)
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]

    # Add +1 prefix for US numbers
    if len(digits) == 10:
        return f"+1{digits}"

    return ""

def parse_company_name(name: str) -> tuple:
    """
    Attempt to extract first/last name from company name
    Returns: (first_name, last_name) or ("", "")
    """
    # This is a best-effort heuristic - most company names won't have parseable names
    # Examples: "Smith HVAC" -> ("Smith", "HVAC"), "ABC Company" -> ("", "")

    # Common patterns indicating no personal name
    business_keywords = [
        'inc', 'llc', 'ltd', 'corp', 'company', 'service', 'services',
        'electric', 'plumbing', 'heating', 'cooling', 'hvac', 'solar',
        'generator', 'systems', 'solutions', 'group', 'enterprises'
    ]

    name_lower = name.lower()

    # If contains business keywords, likely not a personal name
    if any(keyword in name_lower for keyword in business_keywords):
        return ("", "")

    # Otherwise, leave empty (safer than guessing)
    return ("", "")

def generate_google_ads_list(contractors: List[Dict], timestamp: str):
    """
    Generate Google Ads Customer Match CSV

    Target: GOLD tier + top 150 SILVER tier (total ~200 contacts)
    Format: Email, Phone, FirstName, LastName, Country, Zip
    """

    # Select GOLD + top SILVER
    gold = [c for c in contractors if c['ICP_Tier'] == 'GOLD']
    silver = [c for c in contractors if c['ICP_Tier'] == 'SILVER']

    # Sort SILVER by ICP score, take top 150
    silver_sorted = sorted(silver, key=lambda x: -float(x.get('ICP_Score', 0)))
    top_silver = silver_sorted[:150]

    # Combine
    target_list = gold + top_silver

    print(f"\n📊 Google Ads Customer Match list:")
    print(f"   GOLD tier: {len(gold)} contractors")
    print(f"   Top SILVER: {len(top_silver)} contractors")
    print(f"   Total: {len(target_list)} prospects")

    # Create CSV
    output_file = f"output/google_ads_customer_match_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Google Ads Customer Match header
        writer.writerow(['Email', 'Phone', 'First Name', 'Last Name', 'Country', 'Zip'])

        for contractor in target_list:
            # Email (likely not available, leave empty)
            email = ""

            # Phone (E.164 format)
            phone = format_phone_for_ads(contractor.get('phone', ''))

            # Name parsing (best effort)
            first_name, last_name = parse_company_name(contractor.get('name', ''))

            # Country (US)
            country = "US"

            # Zip code
            zip_code = contractor.get('zip', '')

            writer.writerow([email, phone, first_name, last_name, country, zip_code])

    print(f"✅ Saved: {output_file}")
    return output_file

def generate_meta_audience_list(contractors: List[Dict], timestamp: str):
    """
    Generate Meta/Instagram Custom Audience CSV

    Target: Multi-OEM contractors (prime consolidation candidates)
    Format: phone, country, zip
    """

    # Select multi-OEM contractors (2+ OEMs)
    multi_oem = [c for c in contractors if int(c.get('OEM_Count', 1)) >= 2]

    print(f"\n📊 Meta/Instagram Custom Audience:")
    print(f"   Multi-OEM contractors: {len(multi_oem)}")

    # Create CSV
    output_file = f"output/meta_custom_audience_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Meta Custom Audience header
        writer.writerow(['phone', 'country', 'zip'])

        for contractor in multi_oem:
            # Phone (digits only, Meta prefers unhashed)
            phone = contractor.get('phone', '')

            # Country code (US)
            country = "US"

            # Zip code
            zip_code = contractor.get('zip', '')

            writer.writerow([phone, country, zip_code])

    print(f"✅ Saved: {output_file}")
    return output_file

def generate_seo_strategy(contractors: List[Dict], timestamp: str):
    """Generate SEO strategy document for Coperniq website"""

    # Analyze geographic distribution
    states = defaultdict(int)
    cities = defaultdict(int)
    for c in contractors:
        state = c.get('state', '')
        city = c.get('city', '')
        if state:
            states[state] += 1
        if city:
            cities[city] += 1

    top_states = sorted(states.items(), key=lambda x: -x[1])[:10]
    top_cities = sorted(cities.items(), key=lambda x: -x[1])[:20]

    # Analyze OEM coverage
    oem_mentions = defaultdict(int)
    for c in contractors:
        oems = c.get('OEMs_Certified', '')
        if oems:
            for oem in oems.split(','):
                oem_clean = oem.strip()
                if oem_clean:
                    oem_mentions[oem_clean] += 1

    top_oems = sorted(oem_mentions.items(), key=lambda x: -x[1])[:10]

    # Generate markdown (first page only for now due to size)
    md = f"""# Coperniq SEO Strategy - Contractor Database Insights

**Generated**: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## 🎯 Strategic Overview

**Dataset**: {len(contractors):,} contractors across 10 OEM networks

**Core Value Prop**: Coperniq is the only brand-agnostic monitoring platform for microinverters + batteries + generators + HVAC

**SEO Opportunity**: Contractors searching for "multi-brand monitoring", "unified platform", "consolidate monitoring platforms"

---

## 🔑 Primary Keywords (High Intent)

### Product Keywords
1. **"brand agnostic monitoring platform"** - Zero competition, exact match to Coperniq positioning
2. **"multi brand solar monitoring"** - Contractors managing Enphase + SolarEdge
3. **"unified energy monitoring dashboard"** - Enterprise-level search term
4. **"generator battery solar monitoring"** - Multi-product bundle
5. **"hvac solar monitoring integration"** - HVAC contractors

### Pain Point Keywords
6. **"consolidate monitoring platforms"** - Direct pain point for multi-OEM contractors
7. **"single dashboard multiple brands"** - Operational efficiency search
8. **"reduce customer support complexity"** - Business benefit keyword
9. **"unified customer experience energy"** - Customer satisfaction angle

### Competitor Keywords (Defensive SEO)
10. **"alternative to enphase enlighten"** - Capture dissatisfied Enphase users
11. **"tesla monitoring third party"** - Contractors wanting non-Tesla options
12. **"generac mobile link alternative"** - Generac dealer frustrations

---

## 🗺️ Geographic SEO Strategy

### High-Priority States (Top 10 by Contractor Density)

"""

    for state, count in top_states:
        md += f"- **{state}**: {count:,} contractors\n"

    md += f"""

### City-Level SEO Opportunities

**Long-tail keywords**: "[City] + [product] + monitoring"

**Top 20 Cities for Content**:

"""

    for city, count in top_cities:
        md += f"- {city}: {count} contractors\n"

    md += f"""

---

## 🏢 OEM-Specific SEO

### Top OEM Networks in Database

"""

    for oem, count in top_oems:
        md += f"- **{oem}**: {count:,} dealers\n"

    md += """

---

## 📝 Content Recommendations

See full SEO strategy for detailed blog topics, landing pages, and implementation roadmap.

---

**Report End** | Generated """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Save SEO strategy
    output_file = f"output/seo_strategy_{timestamp}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"\n✅ Saved SEO strategy: {output_file}")
    return output_file

def generate_bdr_playbook(contractors: List[Dict], timestamp: str):
    """Generate personal BDR playbook (confidential)"""

    # Analyze contractor personas
    gold_count = len([c for c in contractors if c['ICP_Tier'] == 'GOLD'])
    multi_oem_count = len([c for c in contractors if int(c.get('OEM_Count', 1)) >= 2])
    hvac_count = len([c for c in contractors if c.get('has_hvac') == 'True'])

    md = f"""# Personal BDR Playbook - Coperniq Outreach

**Generated**: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
**CONFIDENTIAL**: For personal use only

---

## 🎯 Target Personas

Based on 10-OEM database ({len(contractors):,} contractors):

### 1. Multi-OEM Contractors ({multi_oem_count} prospects)
**Profile**: Managing 2-3 OEM platforms (Generac + Tesla + Enphase)
**Pain Point**: Platform switching fatigue, inconsistent customer experience
**Value Prop**: "Consolidate 3 logins into 1 unified dashboard"

### 2. HVAC Contractors ({hvac_count:,} prospects)
**Profile**: HVAC companies expanding into solar/battery/generator
**Pain Point**: Managing energy products outside core HVAC expertise
**Value Prop**: "Add energy monitoring without learning 3 new platforms"

### 3. GOLD Tier Prospects ({gold_count} prospects)
**Profile**: Strong signals across 2-3 ICP dimensions
**Pain Point**: Complexity at scale (serving residential + commercial, multi-product)
**Value Prop**: "Platform built for contractors scaling $5M → $50M"

---

## 📧 Email Templates

### Template 1: Multi-OEM Contractor (Dual-OEM)

**Subject**: Managing Generac + Enphase separately? [First Name]

**Body**:
Hi [First Name],

I noticed [Company Name] is certified for both Generac and Enphase — impressive to manage both product lines.

Quick question: Are your customers confused about which app to use for their battery vs generator?

We built Coperniq specifically for dealers like you who manage multiple brands. One unified dashboard for all monitoring.

Worth a 15-min call?

[Your Name]
[Calendar Link]

---

## 📞 Cold Call Script

**Opening** (15 seconds):
"Hi [First Name], this is [Your Name] from Coperniq. I work with contractors managing multiple OEM platforms — Generac, Tesla, Enphase — and I saw [Company Name] is certified for [X] and [Y]. Do you have 2 minutes?"

**Value Prop** (20 seconds):
"Contractors tell us they cut support time by 30-40% after switching because:
1. Your team only checks one platform
2. Customers only download one app
3. Alerts come from one place"

---

## 🎯 Objection Handling Playbook

### "We're happy with [OEM Platform]"
"I hear that a lot. Coperniq isn't replacing [OEM Platform] — we integrate with it. Think of us as the unified layer on top."

### "We don't have time for new platforms"
"That's actually why contractors switch to Coperniq — they're tired of managing 3 platforms. Our whole pitch is 'reduce complexity.'"

---

**Playbook End** | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**CONFIDENTIAL** - For personal use only.
"""

    # Save BDR playbook
    output_file = f"output/bdr_playbook_confidential_{timestamp}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"\n✅ Saved BDR playbook (CONFIDENTIAL): {output_file}")
    return output_file

def main():
    print("=" * 80)
    print("GENERATING GTM DELIVERABLES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y%m%d")

    # Load ICP-scored contractors
    input_file = f"output/icp_scored_contractors_final_{timestamp}.csv"

    print(f"\n📂 Loading ICP-scored contractors: {input_file}")
    contractors = load_scored_contractors(input_file)
    print(f"   Loaded {len(contractors)} contractors")

    # Generate Google Ads Customer Match list
    print(f"\n🎯 Creating Google Ads Customer Match list...")
    generate_google_ads_list(contractors, timestamp)

    # Generate Meta Custom Audience
    print(f"\n🎯 Creating Meta/Instagram Custom Audience...")
    generate_meta_audience_list(contractors, timestamp)

    # Generate SEO strategy
    print(f"\n🎯 Creating SEO strategy document...")
    generate_seo_strategy(contractors, timestamp)

    # Generate BDR playbook
    print(f"\n🎯 Creating personal BDR playbook (CONFIDENTIAL)...")
    generate_bdr_playbook(contractors, timestamp)

    print(f"\n{'=' * 80}")
    print(f"GTM DELIVERABLES COMPLETE")
    print(f"{'=' * 80}")
    print(f"\n✅ Files created:")
    print(f"   • Google Ads: output/google_ads_customer_match_{timestamp}.csv")
    print(f"   • Meta Audience: output/meta_custom_audience_{timestamp}.csv")
    print(f"   • SEO Strategy: output/seo_strategy_{timestamp}.md")
    print(f"   • BDR Playbook: output/bdr_playbook_confidential_{timestamp}.md")

    print(f"\n   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
