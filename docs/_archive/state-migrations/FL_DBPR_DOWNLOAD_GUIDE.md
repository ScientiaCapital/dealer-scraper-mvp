# Florida DBPR Construction Contractor License Data - Download Guide

**Created**: October 31, 2025
**Status**: Ready to download
**Source**: Department of Business & Professional Regulation (DBPR)
**Timeline**: Manual download + CSV export (30-60 minutes)

---

## IMPORTANT: DBPR vs DFS

⚠️ **Common Mistake**: Florida has TWO licensing agencies:

| Agency | What They License | Bulk Download |
|--------|------------------|---------------|
| **DBPR** (Department of Business & Professional Regulation) | Construction contractors (ER, CAC, EL) | ❌ No bulk download (manual export) |
| **DFS** (Department of Financial Services) | Insurance & financial licenses | ✅ Bulk download available |

**This guide covers DBPR (construction contractors) - the correct source for contractor data.**

---

## Quick Summary

| Factor | Details |
|--------|---------|
| **URL** | https://www2.myfloridalicense.com/construction-industry/public-records/ |
| **Cost** | FREE |
| **Format** | Manual search → CSV export |
| **License Types** | ER (Electrical), CAC (Air Conditioning), EL (Electrical) |
| **Expected Records** | ~35,000 contractor licenses |
| **Time to Setup** | 30-60 minutes (manual export) |
| **Maintenance** | Manual re-download as needed |

---

## Download Process

### Step 1: Access DBPR Public Records Portal

1. **Visit DBPR Construction Portal**:
   ```
   https://www2.myfloridalicense.com/construction-industry/public-records/
   ```

2. **Navigate to License Search**:
   - Look for "Search License Information" or similar link
   - May be labeled "Licensee Search" or "Verify a License"

### Step 2: Export License Data by Type

**Target License Types**:
- **ER**: Electrical Contractor (Residential)
- **CAC**: Air Conditioning Contractor
- **EL**: Electrical Contractor (Unlimited)

**Export Process** (repeat for each license type):

1. **Select License Type**: Choose ER, CAC, or EL from dropdown
2. **Set Status Filter**: Active licenses only
3. **Run Search**: Click "Search" or "Submit"
4. **Export Results**: Look for "Export to CSV" or "Download" button
5. **Save File**:
   ```
   output/state_licenses/fl_dbpr_er_20251031.csv
   output/state_licenses/fl_dbpr_cac_20251031.csv
   output/state_licenses/fl_dbpr_el_20251031.csv
   ```

### Step 3: Combine Files

After downloading all 3 license types, combine into single file:

```bash
# Merge CSV files
python3 -c "
import pandas as pd

# Load all 3 files
df_er = pd.read_csv('output/state_licenses/fl_dbpr_er_20251031.csv')
df_cac = pd.read_csv('output/state_licenses/fl_dbpr_cac_20251031.csv')
df_el = pd.read_csv('output/state_licenses/fl_dbpr_el_20251031.csv')

# Add license type column
df_er['License_Type'] = 'ER'
df_cac['License_Type'] = 'CAC'
df_el['License_Type'] = 'EL'

# Combine
df_all = pd.concat([df_er, df_cac, df_el], ignore_index=True)

# Save combined file
df_all.to_csv('output/state_licenses/fl_licenses_raw_20251031.csv', index=False)

print(f'Combined {len(df_all):,} FL contractor licenses')
"
```

---

## Expected Data Fields

Based on typical FL DBPR export format:

```
- License Number
- Business Name
- Primary Licensee Name
- License Status (Active, Inactive, Expired)
- License Type (ER, CAC, EL)
- Issue Date
- Expiration Date
- Business Address
- Business City
- Business State
- Business ZIP
- Business Phone
- Email (if available)
```

---

## Alternative: Public Records Request

If the online portal doesn't allow bulk export:

### Option 1: Contact DBPR Directly

**DBPR Public Records Office**:
- Phone: (850) 487-1395
- Email: DBPRPublicRecords@myfloridalicense.com
- Request: "Bulk export of active electrical and HVAC contractor licenses (ER, CAC, EL types)"

### Option 2: Use Florida Public Records Law

Under Florida Sunshine Law (Chapter 119, F.S.), license data is public record:

**Sample Request Letter**:
```
To: DBPR Public Records Custodian
Subject: Public Records Request - Contractor License Database

I am requesting a copy of the following public records under Florida Statute Chapter 119:

1. All active contractor licenses for the following license types:
   - ER (Electrical Contractor - Residential)
   - CAC (Air Conditioning Contractor)
   - EL (Electrical Contractor - Unlimited)

2. Fields requested:
   - License number, business name, primary licensee name
   - License status, issue date, expiration date
   - Business address, city, state, ZIP, phone
   - Email address (if available)

3. Preferred format: CSV or Excel

Please provide a cost estimate for fulfilling this request.

Thank you,
[Your Name]
```

**Expected Response Time**: 10-15 business days

---

## Cross-Reference Integration

Once you have the FL license data file:

```bash
python3 scripts/run_tier1_cross_reference.py \
    --license-files output/state_licenses/fl_licenses_raw_20251031.csv \
    --oem-contractors output/grandmaster_list_expanded_20251029.csv \
    --output output/fl_cross_referenced_20251031.csv
```

---

## Expected Match Results

### By the Numbers

| Metric | Value |
|--------|-------|
| FL OEM contractors | ~280 |
| FL licenses (total) | ~35,000 |
| Expected matches | 85-110 |
| Match rate | 30-40% |
| Phone-based matches | ~70-90 (25-30%) |
| Fuzzy name matches | ~15-20 (5-10%) |

### OEM Distribution (FL contractors)

From grandmaster list:
- Generac: ~90 contractors
- Tesla: ~50 contractors
- Enphase: ~40 contractors
- SolarEdge: ~35 contractors
- Cummins: ~25 contractors
- Others: ~40 contractors

### ICP Expectations

After FL enrichment:
- PLATINUM (80-100): 3-5 contractors
- GOLD (60-79): 10-15 contractors
- SILVER (40-59): 30-40 contractors
- BRONZE (<40): 40-50 contractors

---

## Florida Priority Justification

**Why FL is High Priority**:

1. **Market Size**: 3rd largest solar market in US
2. **Net Metering**: Strong net metering policies (NEM 2.0 equivalent)
3. **Property Tax Exemption**: Solar systems exempt from property tax assessment
4. **Hurricane Risk**: High demand for backup generators + batteries
5. **OEM Concentration**: 280 contractors (3.4% of database)

**Expected Revenue Impact**:
- 85-110 enriched FL leads
- Assume 2% close rate = 2-3 deals
- Average deal size: $50K-$100K
- Revenue potential: $100K-$300K

---

## Troubleshooting

### Problem: Portal doesn't allow bulk export

**Solution**: Use public records request (see above)

### Problem: Export limited to 1,000 records

**Solution**: Export in batches by:
- County (Miami-Dade, Broward, Palm Beach, etc.)
- ZIP code ranges
- Alphabetical ranges (A-D, E-H, etc.)

### Problem: Missing phone numbers

**Solution**:
- Phone numbers are required for matching (96.5% of matches)
- If export lacks phone data, public records request may provide more complete data
- Alternative: Cross-reference with Google My Business data

---

## Next Steps

### Immediate (Today)

1. ⏳ Visit DBPR portal and attempt manual export
2. ⏳ If manual export works, download ER/CAC/EL license types
3. ⏳ If manual export doesn't work, submit public records request

### After Download (1-2 days for manual, 10-15 days for request)

4. Combine ER/CAC/EL files into single CSV
5. Update FloridaScraper to parse DBPR format
6. Run cross-reference script
7. Analyze FL match results
8. Combine TX + CA + FL enriched lists
9. Generate GTM deliverables (Google Ads, Meta audiences)

---

## Questions?

- **DBPR Portal Issues**: Contact (850) 487-1395
- **Public Records Request**: DBPRPublicRecords@myfloridalicense.com
- **File Format Questions**: Check `scrapers/license/scraper_factory.py`
- **Integration Script**: See `scripts/run_tier1_cross_reference.py`
- **Match Rate Concerns**: Reference TX results (33.8% match rate baseline, 86.3% with fuzzy matching)

---

**Status**: Ready to download from DBPR construction contractor portal
**Blocking**: Manual export or public records request required
**Timeline**: 30-60 minutes (manual) OR 10-15 days (public records request)
