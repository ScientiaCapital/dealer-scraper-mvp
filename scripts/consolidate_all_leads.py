#!/usr/bin/env python3
"""
Consolidated Lead Database Builder

Merges all available data sources:
1. SPW 2025 Commercial Contractors (258)
2. SPW 2025 Solar EPCs (153)
3. FL Enphase Installers (396) - with license type tags
4. CA Outreach list (41) - already enriched
5. FL Roofers (9,659) - with emails from state licenses

Cross-references to identify:
- Multi-trade contractors (ELE + HVAC + SOL + PLUM + ROOF)
- Resimercial contractors (C&I | R market segment)
- Contractors with existing emails (no Hunter.io needed)

Output: Prioritized lead list ready for BDR outreach
"""

import csv
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re
from difflib import SequenceMatcher

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "enrichment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path.home() / "Downloads"

# Input files
FL_ENPHASE_FILE = DOWNLOADS / "Enphase Installers FL - Sheet1.csv"
CA_OUTREACH_FILE = DOWNLOADS / "CA_outreach - Sheet1.csv"
FL_ROOFERS_FILE = DOWNLOADS / "Contractor List.xlsx - Roofers.csv"

# SPW 2025 Data (embedded from web extraction)
SPW_COMMERCIAL = """rank,company_name,state,kw_installed
1,DCE Services,NC,116909.53
2,M Bar C Construction,CA,77440.00
3,Teichert Solar,CA,70000.15
4,DMH Services,PA,67339.00
5,Solar Landscape,NJ,62623.85
6,Sunstall,CA,61308.85
7,DEPCOM Power,AZ,54600.00
8,Standard Solar,MD,54284.02
9,SunVest Solar,IL,49211.72
10,New Era Electric,CA,45020.00
11,Elite Electric,CA,41671.22
12,PowerFlex,CA,39640.00
13,iBuild Solar,PA,36165.58
14,ForeFront Power,CA,35693.23
15,Nelnet Renewable Energy,IL,35253.00
16,Core Development Group,NJ,32117.00
17,Knobelsdorff,MN,31600.00
18,Got Electric,MD,30100.33
19,MBL-Energy,CA,28495.12
20,Baja Construction,CA,25483.07
21,Solect Energy,MA,25205.19
22,CalCom Energy,CA,25168.00
23,Encore Renewable Energy,VT,24937.00
24,Pine Energy,GA,24573.55
25,Coldwell Solar,CA,24538.00
26,dGEN Energy Partners,WY,24320.00
27,OnSite Solar,NY,24000.00
28,Baker Electric,CA,23723.63
29,Paradise Energy Solutions,PA,22944.68
30,Radiance Solar,GA,22090.98
31,Ameresco,MA,19936.28
32,NoBull Energy,IN,18800.00
33,Veregy,AZ,18165.13
34,StarAlt Solar,TX,16672.73
35,J.F. Electric,IL,16050.00
36,REC Solar,CA,16048.66
37,SOLON,AZ,15572.56
38,Arevon Energy,AZ,15372.00
39,Collins Electrical,CA,15011.78
40,Sunrise Power Solutions,NY,14684.85
41,Entegrity Energy Partners,AR,14277.00
42,Motive Energy,CA,13465.40
43,ReVision Energy,ME,13328.07
44,Newport Power,CA,13144.00
45,Solar Optimum,CA,12477.00
46,SunPeak,WI,12192.53
47,Renewable Energy Partners,CA,12190.70
48,Cedar Creek Energy,MN,11955.02
49,Artisun Solar,KS,11806.91
50,Pickett Solar,CA,11485.43
51,Faith Technologies Inc. (FTI),WI,11431.61
52,OnSwitch,CA,11191.30
53,Pivot Energy,CO,11154.66
54,Verogy,CT,10279.98
55,Advanced Green Technologies,FL,9922.20
56,StraightUp Solar,MO,9445.25
57,HSI Solar,IN,9241.90
58,Montante Solar,NY,8969.73
59,SitelogIQ,MN,8856.73
60,BEI Construction,CA,8662.32
61,Axis Solar,TX,8578.17
62,GenPro Energy Solutions,SD,8533.87
63,Axium Solar,TX,8210.56
64,Solar One,TX,8194.74
65,Kopp Electric Company,NJ,7936.33
66,HES Renewables,CA,7819.14
67,TMI Energy Solutions,OH,7764.23
68,Melink Solar,OH,7759.00
69,STG Solar,NC,7670.00
70,ACE Solar,MA,7481.91
71,Accord Power,NY,6962.82
72,Aggreko Energy Transition Solutions,CT,6957.20
73,E Light Electric,CO,6674.00
74,Obodo Energy Partners,AZ,6287.90
75,Continental Energy Solutions,IL,6269.70
76,Solar Renewable Energy,PA,6094.00
77,Catalyze,TX,6087.30
78,Treepublic,CA,6012.72
79,Eagle Point Solar,IA,5722.19
80,Tron Solar,IL,5666.00
81,Renewvia Energy,GA,5342.06
82,Dynamic Energy,PA,5326.43
83,Moore Energy,PA,5183.00
84,Verde Solutions,IL,5169.19
85,Fresh Coast Solar,IL,5097.13
86,All Energy Solar,MN,5056.03
87,Colite Technologies,SC,4971.61
88,Tenco Solar,CA,4942.25
89,Sun Light & Power,CA,4927.58
90,Harvest Power,NY,4769.90
91,New Energy Equity,MD,4719.66
92,Advanced Solar Products,NJ,4695.67
93,Solar Technologies,CA,4680.75
94,RevoluSun Smart Home,HI,4627.90
95,Commonwealth Power,VA,4203.71
96,Scenic Hill Solar,AR,4149.23
97,ARCO/Murray Power Solutions (AMPS),IL,4057.00
98,Elemental Energy,OR,4036.63
99,SunRenu Solar,AZ,3967.00
100,1 Source Solar,IA,3945.10"""

SPW_EPC = """rank,company_name,state,kw_installed
1,Quanta Services,TX,10106563.89
2,Moss,FL,4175060.00
3,SOLV Energy,CA,4053100.00
4,Kiewit Energy Group,NE,3113000.00
5,Primoris Renewable Energy,CO,2900000.00
6,McCarthy Building Companies,MO,2794000.00
7,Black & Veatch,KS,2412900.00
8,Mortenson,MN,2030900.00
9,Rosendin Electric,CA,1322860.00
10,RES (Renewable Energy Systems),CO,1114300.00
11,Signal Energy,TX,981600.00
12,DEPCOM Power,AZ,825000.00
13,Qcells USA,CA,719270.00
14,Sundt Construction,AZ,587050.00
15,E Light Electric,CO,386574.15
16,Mill Creek Renewables,NC,385456.13
17,Burns & McDonnell,MO,307000.00
18,NoBull Energy,IN,301800.00
19,Barton Malow,MI,189000.00
20,AUI Partners,TX,180900.00
21,Vanguard Energy Partners,NJ,176516.80
22,ESA,FL,169735.00
23,Gemma Renewable Power,CT,155500.00
24,GreenSpark Solar,NY,112426.13
25,Knobelsdorff,MN,105850.00
26,United Renewable Energy,GA,92160.00
27,Recon Corp.,MI,84272.90
28,Next Generation Solar,NY,79699.34
29,OnSite Solar,NY,76000.00
30,ACE Solar,MA,74013.36"""


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ""
    # Lowercase
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" llc", " inc", " inc.", " corp", " corp.", " co", " co.",
                   " ltd", " ltd.", " company", ", llc", ", inc", ", inc."]:
        name = name.replace(suffix, "")
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def fuzzy_match(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Check if two company names match fuzzy."""
    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)
    if not n1 or not n2:
        return False
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


def parse_fl_enphase(filepath: Path) -> list:
    """Parse FL Enphase installers with license type tags."""
    records = []
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return records

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, None)

        for row in reader:
            if len(row) < 2:
                continue
            license_types = row[0].strip() if row[0] else ""
            company = row[1].strip() if row[1] else ""

            if not company:
                continue

            # Parse license types
            licenses = set()
            for lt in ["ELE", "HVAC", "SOL", "CONT", "PLUM"]:
                if lt in license_types.upper():
                    licenses.add(lt)

            records.append({
                "company_name": company,
                "state": "FL",
                "source": "FL_Enphase",
                "license_types": licenses,
                "is_multi_trade": len(licenses) >= 2,
                "email": "",  # No email in this file
            })

    print(f"✅ FL Enphase: {len(records)} installers loaded")
    return records


def parse_ca_outreach(filepath: Path) -> list:
    """Parse CA outreach list with enrichment data."""
    records = []
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return records

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get("Company", "").strip()
            if not company:
                continue

            markets = row.get("Markets Served", "")
            is_resimercial = "C&I" in markets and "R" in markets

            records.append({
                "company_name": company,
                "state": "CA",
                "source": "CA_Outreach",
                "kw_installed": row.get("kW Installed In California", ""),
                "markets_served": markets,
                "is_resimercial": is_resimercial,
                "service_type": row.get("Primary Service", ""),
                "notes": row.get("Notes", ""),
                "email": "",
            })

    print(f"✅ CA Outreach: {len(records)} companies loaded")
    return records


def parse_fl_roofers(filepath: Path, limit: int = None) -> list:
    """Parse FL roofers with EMAILS from state licenses."""
    records = []
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return records

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break

            company = row.get("Company Name", "").strip()
            email = row.get("Email Address", "").strip()

            if not company and not email:
                continue

            # Use person name if no company
            if not company:
                company = row.get("Name", "").strip()

            records.append({
                "company_name": company,
                "contact_name": row.get("Name", ""),
                "address": row.get("Address", ""),
                "city": row.get("City", ""),
                "state": "FL",
                "zip": row.get("Zip", ""),
                "county": row.get("County", ""),
                "email": email,
                "source": "FL_Roofers_License",
                "license_types": {"ROOF"},
                "has_email": bool(email),
            })

    print(f"✅ FL Roofers: {len(records)} contractors loaded (with emails!)")
    return records


def parse_spw_data(data_str: str, source_name: str) -> list:
    """Parse embedded SPW data."""
    records = []
    lines = data_str.strip().split('\n')
    headers = lines[0].split(',')

    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) >= 4:
            records.append({
                "rank": int(parts[0]),
                "company_name": parts[1],
                "state": parts[2],
                "kw_installed": float(parts[3]),
                "source": source_name,
                "is_top_100": int(parts[0]) <= 100,
            })

    print(f"✅ {source_name}: {len(records)} companies loaded")
    return records


def cross_reference_leads(all_leads: dict) -> dict:
    """
    Cross-reference leads across data sources to find:
    - Multi-trade contractors
    - Companies appearing in multiple lists
    - Matches with existing emails
    """
    # Build company name index
    company_index = defaultdict(list)

    for source, leads in all_leads.items():
        for lead in leads:
            normalized = normalize_company_name(lead.get("company_name", ""))
            if normalized:
                company_index[normalized].append({
                    "source": source,
                    "data": lead
                })

    # Find cross-references
    cross_refs = []
    for name, matches in company_index.items():
        if len(matches) > 1:
            sources = [m["source"] for m in matches]
            emails = [m["data"].get("email", "") for m in matches if m["data"].get("email")]

            # Merge license types
            all_licenses = set()
            for m in matches:
                lt = m["data"].get("license_types", set())
                if isinstance(lt, set):
                    all_licenses.update(lt)

            cross_refs.append({
                "company_name": matches[0]["data"]["company_name"],
                "normalized_name": name,
                "sources": sources,
                "source_count": len(sources),
                "emails_found": emails,
                "has_email": len(emails) > 0,
                "license_types": all_licenses,
                "is_multi_trade": len(all_licenses) >= 2,
            })

    return cross_refs


def score_lead(lead: dict) -> int:
    """
    Score a lead for ICP fit (0-100).

    Scoring:
    - Has email: +20
    - Multi-trade licenses: +25
    - In SPW Commercial top 100: +20
    - In SPW EPC: +15
    - Resimercial market: +15
    - FL state (roofing+solar hub): +5
    """
    score = 0

    if lead.get("has_email") or lead.get("email"):
        score += 20

    if lead.get("is_multi_trade"):
        score += 25

    if lead.get("source") == "SPW_Commercial" and lead.get("is_top_100"):
        score += 20

    if lead.get("source") == "SPW_EPC":
        score += 15

    if lead.get("is_resimercial"):
        score += 15

    if lead.get("state") == "FL":
        score += 5

    # Bonus for appearing in multiple sources
    if lead.get("source_count", 1) > 1:
        score += 10 * (lead.get("source_count") - 1)

    return min(score, 100)


def main():
    print("\n" + "=" * 70)
    print("CONSOLIDATED LEAD DATABASE BUILDER")
    print("=" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Load all data sources
    print("\n📂 Loading data sources...")

    all_leads = {
        "SPW_Commercial": parse_spw_data(SPW_COMMERCIAL, "SPW_Commercial"),
        "SPW_EPC": parse_spw_data(SPW_EPC, "SPW_EPC"),
        "FL_Enphase": parse_fl_enphase(FL_ENPHASE_FILE),
        "CA_Outreach": parse_ca_outreach(CA_OUTREACH_FILE),
        "FL_Roofers": parse_fl_roofers(FL_ROOFERS_FILE, limit=1000),  # Sample first 1000
    }

    # Summary
    print("\n📊 Data Summary:")
    total = 0
    for source, leads in all_leads.items():
        print(f"   {source}: {len(leads)} records")
        total += len(leads)
    print(f"   TOTAL: {total} records")

    # Cross-reference
    print("\n🔗 Cross-referencing leads...")
    cross_refs = cross_reference_leads(all_leads)
    print(f"   Found {len(cross_refs)} companies appearing in multiple sources")

    # Find FL companies that are both roofers AND Enphase installers (GOLD!)
    fl_roofer_names = {normalize_company_name(l["company_name"]) for l in all_leads["FL_Roofers"]}
    fl_enphase_names = {normalize_company_name(l["company_name"]) for l in all_leads["FL_Enphase"]}
    solar_roofers = fl_roofer_names.intersection(fl_enphase_names)

    if solar_roofers:
        print(f"\n🎯 GOLD TARGETS: {len(solar_roofers)} FL companies are BOTH roofers AND Enphase installers!")
        for name in list(solar_roofers)[:10]:
            print(f"   - {name}")

    # Build prioritized output
    print("\n📝 Building prioritized lead list...")

    # Priority 1: SPW Commercial with existing emails (need to enrich)
    spw_commercial_priority = []
    for lead in all_leads["SPW_Commercial"]:
        lead["icp_score"] = score_lead(lead)
        spw_commercial_priority.append(lead)

    spw_commercial_priority.sort(key=lambda x: (-x["icp_score"], -x.get("kw_installed", 0)))

    # Output files

    # 1. SPW Commercial Master (for Hunter.io enrichment)
    spw_output = OUTPUT_DIR / f"spw_commercial_master_{timestamp}.csv"
    with open(spw_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "rank", "company_name", "state", "kw_installed", "icp_score", "source"
        ])
        writer.writeheader()
        for lead in spw_commercial_priority[:100]:  # Top 100
            writer.writerow({
                "rank": lead.get("rank", ""),
                "company_name": lead["company_name"],
                "state": lead["state"],
                "kw_installed": lead.get("kw_installed", ""),
                "icp_score": lead["icp_score"],
                "source": lead["source"],
            })
    print(f"✅ Saved: {spw_output}")

    # 2. FL Roofers with emails (ready for outreach!)
    fl_with_emails = [l for l in all_leads["FL_Roofers"] if l.get("email")]
    fl_output = OUTPUT_DIR / f"fl_roofers_with_emails_{timestamp}.csv"
    with open(fl_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company_name", "contact_name", "email", "city", "zip", "county"
        ])
        writer.writeheader()
        for lead in fl_with_emails[:500]:  # First 500 with emails
            writer.writerow({
                "company_name": lead["company_name"],
                "contact_name": lead.get("contact_name", ""),
                "email": lead["email"],
                "city": lead.get("city", ""),
                "zip": lead.get("zip", ""),
                "county": lead.get("county", ""),
            })
    print(f"✅ Saved: {fl_output}")

    # 3. Cross-reference matches (highest value)
    if cross_refs:
        xref_output = OUTPUT_DIR / f"cross_reference_matches_{timestamp}.csv"
        with open(xref_output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "company_name", "sources", "source_count", "emails_found",
                "license_types", "is_multi_trade"
            ])
            writer.writeheader()
            for ref in sorted(cross_refs, key=lambda x: -x["source_count"]):
                writer.writerow({
                    "company_name": ref["company_name"],
                    "sources": "|".join(ref["sources"]),
                    "source_count": ref["source_count"],
                    "emails_found": "|".join(ref["emails_found"]),
                    "license_types": "|".join(ref.get("license_types", set())),
                    "is_multi_trade": ref["is_multi_trade"],
                })
        print(f"✅ Saved: {xref_output}")

    # Summary stats
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"SPW Commercial top 100 ready for Hunter.io: {spw_output.name}")
    print(f"FL Roofers with emails (ready for outreach): {len(fl_with_emails)}")
    print(f"Cross-reference matches (multi-source): {len(cross_refs)}")

    if solar_roofers:
        print(f"\n🎯 PRIORITY TARGETS: {len(solar_roofers)} Solar+Roofing FL contractors")

    print(f"\n📁 All outputs in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
