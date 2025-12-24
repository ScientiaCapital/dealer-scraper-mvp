# California License Data - Next Steps

**Created**: October 31, 2025
**Status**: Ready to purchase/download
**Expected Timeline**: 1-2 business days for paid option

---

## Quick Decision Matrix

| Factor | Option 1: Paid ($235) | Option 2: Free PDF |
|--------|----------------------|-------------------|
| **Cost** | $235 one-time | $0 |
| **Ease** | ⭐⭐⭐⭐⭐ Text file | ⭐⭐ Requires PDF parsing |
| **Data Quality** | ⭐⭐⭐⭐⭐ Complete | ⭐⭐⭐ May be incomplete |
| **Time to Setup** | 1-2 business days | 3-4 hours (parsing) |
| **Maintenance** | Updated Jan/July | Manual re-download |
| **Recommended** | ✅ YES (production) | ⚠️ Budget only |

---

## Option 1: Paid LICENSE MASTER (RECOMMENDED)

### Purchase Process

1. **Visit CSLB Data Portal**
   URL: https://www.cslb.ca.gov/onlineservices/dataportal/

2. **Navigate to Purchase Section**
   Look for "Purchase Database Files" or similar link

3. **Select LICENSE MASTER File**
   - File type: Text file (NOT Excel)
   - Cost: $235
   - Contains: All currently renewed or expired-but-renewable licenses

4. **Complete Purchase**
   - Payment: Credit card (likely)
   - Delivery: Email with download link (1-2 business days)

5. **Download & Save**
   - Save as: `output/state_licenses/ca_licenses_raw_20251031.txt`
   - File size: Expected 50-100 MB

### What You Get

**License Types Included**:
- C-10: Electrical Contractor (~15,000-20,000 licenses)
- C-7: Low Voltage Contractor (~5,000-8,000 licenses)
- C-20: Warm-Air Heating, Ventilating and Air-Conditioning (~20,000-25,000 licenses)
- **Total**: ~50,000 contractor licenses

**Fields Included**:
- License number
- Business name
- Mailing address
- Phone number
- License status (Active, Expired-renewable)
- Original license date
- Classifications (C-10, C-7, C-20, etc.)
- Bond information
- Workers compensation info

**Update Frequency**: Full files run in January and July

### Implementation Steps

Once you have the file:

1. **Update CaliforniaScraper** (if needed)
   File: `scrapers/license/scraper_factory.py`
   The scraper already exists but may need text file parsing logic

2. **Run Cross-Reference**
   ```bash
   python3 scripts/run_tier1_cross_reference.py \
       --license-files output/state_licenses/ca_licenses_raw_20251031.txt \
       --oem-contractors output/grandmaster_list_expanded_20251029.csv \
       --output output/ca_cross_referenced_20251031.csv
   ```

3. **Expected Results**
   - CA OEM contractors in database: 520
   - Expected matches: 150-200 (30-40% match rate)
   - Match method: Phone (100%) + Fuzzy name (80%)

---

## Option 2: Free PDF Extraction

### Download Process

1. **Visit Contractor Lists Page**
   URL: https://www.cslb.ca.gov/onlineservices/dataportal/ContractorList

2. **Download Classification PDFs**
   - C-10: Electrical Contractor
   - C-7: Low Voltage Contractor
   - C-20: HVAC Contractor

3. **Save PDFs**
   ```
   output/state_licenses/ca_c10.pdf
   output/state_licenses/ca_c7.pdf
   output/state_licenses/ca_c20.pdf
   ```

### PDF Parsing Implementation

**Install PDF Parser**:
```bash
pip install pdfplumber --break-system-packages
```

**Create Parsing Script**:
```python
import pdfplumber
import pandas as pd

def extract_ca_pdf(pdf_path, classification):
    """Extract contractor data from CA PDF."""
    contractors = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract table data
            tables = page.extract_tables()
            for table in tables:
                # Parse table rows
                for row in table[1:]:  # Skip header
                    if len(row) >= 4:  # Ensure valid row
                        contractors.append({
                            'license_number': row[0],
                            'business_name': row[1],
                            'city': row[2],
                            'classification': classification
                        })

    return pd.DataFrame(contractors)

# Extract all classifications
df_c10 = extract_ca_pdf('output/state_licenses/ca_c10.pdf', 'C-10')
df_c7 = extract_ca_pdf('output/state_licenses/ca_c7.pdf', 'C-7')
df_c20 = extract_ca_pdf('output/state_licenses/ca_c20.pdf', 'C-20')

# Combine
df_all = pd.concat([df_c10, df_c7, df_c20], ignore_index=True)
df_all.to_csv('output/state_licenses/ca_licenses_raw_20251031.csv', index=False)
```

### Limitations

⚠️ PDF extraction challenges:
- May not include phone numbers (critical for matching!)
- Table parsing can be error-prone
- Formatting inconsistencies across pages
- May miss some records due to parsing errors

---

## Expected Match Results (Either Option)

### By the Numbers

| Metric | Value |
|--------|-------|
| CA OEM contractors | 520 |
| CA licenses (total) | ~50,000 |
| Expected matches | 150-200 |
| Match rate | 30-40% |
| Phone-based matches | ~120-150 (25-30%) |
| Fuzzy name matches | ~30-50 (5-10%) |

### OEM Distribution (CA contractors)

From grandmaster list:
- Generac: ~180 contractors
- Tesla: ~80 contractors
- Enphase: ~70 contractors
- SolarEdge: ~60 contractors
- Cummins: ~40 contractors
- Others: ~90 contractors

### ICP Expectations

After CA enrichment:
- PLATINUM (80-100): 5-10 contractors
- GOLD (60-79): 20-30 contractors
- SILVER (40-59): 60-80 contractors
- BRONZE (<40): 50-80 contractors

---

## Budget Justification for Paid Option

**Cost**: $235 one-time

**Value Return**:
- 150-200 enriched CA leads
- Cost per lead: $1.18-$1.57
- CA contractors are higher-value (SREC state, wealthy markets)
- Time savings: 4-5 hours (vs PDF parsing)

**Alternative Cost**:
- Developer time for PDF parsing: 4-5 hours @ $100/hr = $400-500
- Risk of parsing errors requiring rework
- Incomplete data (missing phone numbers)

**Recommendation**: $235 paid option has better ROI

---

## California Priority Justification

**Why CA is High Priority**:

1. **Market Size**: Largest solar market in US
2. **SREC Program**: SGIP + NEM 3.0 creates sustained demand
3. **Wealthy ZIPs**: 15 target ZIPs with $150K-$400K+ median HH income
4. **ITC Urgency**: Residential expires Dec 2025, commercial June 2026
5. **OEM Concentration**: 520 contractors (6.3% of database)

**Expected Revenue Impact**:
- 150 enriched CA leads
- Assume 2% close rate = 3 deals
- Average deal size: $50K-$100K
- Revenue potential: $150K-$300K

**Cost-Benefit**: $235 / $150K-$300K = 0.08-0.16% cost

---

## Next Steps

### Immediate (Today)

1. ✅ Created CA download helper script
   `scripts/download_california_licenses.sh`

2. ⏳ Decision: Paid ($235) or Free (PDF)?
   **Recommendation**: Paid

3. ⏳ If paid: Visit CSLB portal and purchase
   ⏳ If free: Download PDFs and implement parser

### After Download (1-2 business days)

4. Update CaliforniaScraper if needed (text file parsing)
5. Run cross-reference script
6. Analyze CA match results
7. Combine TX + CA enriched lists
8. Generate GTM deliverables (Google Ads, Meta audiences)

### Future (Week 2)

9. Florida construction contractor data (TBD - no bulk download found)
10. Scale to all Tier 1 states (CA + TX + FL)
11. Apollo enrichment for employee count, revenue
12. Close CRM import with Smart Views

---

## Questions?

- **CSLB Portal Issues**: Contact CSLB directly at (800) 321-CSLB
- **File Format Questions**: Check `scrapers/license/scraper_factory.py`
- **Integration Script**: See `scripts/run_tier1_cross_reference.py`
- **Match Rate Concerns**: Reference TX results (33.8% match rate baseline)

---

**Status**: Ready to proceed with CA license data acquisition
**Blocking**: User decision on paid vs free option
**Timeline**: 1-2 business days for paid, 3-4 hours for free implementation
