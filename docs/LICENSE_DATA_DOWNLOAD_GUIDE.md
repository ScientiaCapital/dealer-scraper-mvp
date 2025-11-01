# License Data Download Guide - CA/FL/TX

**Created**: October 31, 2025
**Purpose**: Step-by-step instructions for downloading contractor license databases from California, Florida, and Texas

---

## Overview

This guide provides instructions for obtaining bulk contractor license data from the three highest-priority Tier 1 states. Each state uses different download methods and file formats.

**Target License Types:**
- **Electrical** (C-10 in CA, ER in FL, Electrical Contractor in TX)
- **Low Voltage** (C-7 in CA, EL in FL, Low Voltage Contractor in TX)
- **HVAC** (C-20 in CA, CAC in FL, Air Conditioning Contractor in TX)

**Expected Volumes:**
- California: ~50,000 contractors
- Florida: ~35,000 contractors
- Texas: ~35,000 contractors
- **Total**: ~120,000 contractor records

---

## California CSLB (Contractors State License Board)

### Download Method: **Paid Text File Database** OR **PDF Extract** OR **Web Scraping**

### Option 1: Official Paid Database (RECOMMENDED for Production)

**URL**: https://www.cslb.ca.gov/onlineservices/dataportal/

**Cost**: $235 per file (one-time fee)

**File Format**: Text file (NOT Excel, needs parsing)

**What You Get**:
- LICENSE MASTER: All currently renewed or expired-but-renewable licenses
- Includes: license number, business name, address, phone, status, dates, classifications, bond info, workers comp info
- **Does NOT include**: Cancelled, revoked, or expired non-renewable licenses

**Frequency**: Full files run in January and July

**Steps**:
1. Visit https://www.cslb.ca.gov/onlineservices/dataportal/
2. Look for "Purchase Database Files" or similar option
3. Order the LICENSE MASTER file ($235)
4. Receive text file download link via email
5. Parse text file using `CaliforniaScraper.parse_file()`

### Option 2: Free PDF Extract (Budget Option)

**URL**: https://www.cslb.ca.gov/onlineservices/dataportal/ContractorList

**Cost**: Free

**File Format**: PDF (requires extraction)

**What You Get**:
- Public posting lists in PDF format (ADA compliant)
- Can extract data from PDF for programmatic use

**Limitations**:
- Requires PDF parsing (more complex than CSV)
- May not include all fields available in paid database

**Steps**:
1. Visit https://www.cslb.ca.gov/onlineservices/dataportal/ContractorList
2. Download contractor lists by classification:
   - C-10 (Electrical)
   - C-7 (Low Voltage)
   - C-20 (HVAC)
3. Extract data from PDFs using PDF parsing library (PyPDF2 or pdfplumber)
4. Convert to CSV format
5. Parse using `CaliforniaScraper.parse_file()`

### Option 3: Third-Party Aggregator (Convenience)

**URL**: https://opengovus.com/california-contractor-license

**Cost**: Unknown (check their pricing)

**File Format**: Varies

**Note**: Not an official CSLB source, verify data freshness

### Recommendation for This Project

**Use Option 1 (Paid Database)** if budget allows ($235). The text file format is easier to parse than PDF, and the data is comprehensive and official.

**Fallback to Option 2 (PDF)** if budget constrained. Will require additional PDF parsing logic but still viable.

---

## Florida MyFloridaLicense

### Download Method: **Free Bulk CSV Download** ✅ EASIEST

**URL**: https://licenseesearch.fldfs.com/BulkDownload

**Cost**: FREE

**File Format**: CSV (ready to use!)

**What You Get**:
- All Valid Licenses - Business (24.32 MB)
- All Valid Licenses - Individual (313.99 MB)
- Includes construction industry contractor licenses
- **Does NOT include**: NULL & VOID, delinquent, or involuntarily inactive records

**Alternative URL**: https://www2.myfloridalicense.com/construction-industry/public-records/
(Specific to construction industry, includes ReadMe and column headers documentation)

**Steps**:
1. Visit https://licenseesearch.fldfs.com/BulkDownload
2. Download "All Valid Licenses - Business" (24.32 MB CSV)
3. Optional: Also download "All Valid Licenses - Individual" (313.99 MB CSV) for sole proprietors
4. Read the ReadMe/Disclaimer for column descriptions
5. Filter CSV to license types:
   - ER (Electrical Contractor)
   - EL (Low Voltage Contractor)
   - CAC (Air Conditioning Contractor)
6. Parse using `FloridaScraper.parse_file()`

**Expected Columns** (based on configuration):
- License Number
- Name
- License Type
- Primary Status
- Original License Date
- Expiration Date
- Address Line 1
- City
- State
- Zip Code
- County
- Phone
- Email

### Recommendation

Florida is the **easiest state** to download from. Direct CSV downloads, no cost, comprehensive data. Start here for testing the integration script on real data.

---

## Texas TDLR (Department of Licensing and Regulation)

### Download Method: **Texas Open Data Portal** OR **TDLR License Search Export**

### Option 1: Texas Open Data Portal (RECOMMENDED)

**URL**: https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7

**Cost**: FREE

**File Format**: CSV, Excel, JSON, XML (multiple formats available)

**What You Get**:
- All TDLR-regulated licenses (not just contractors)
- Includes electrical, HVAC, and other trade licenses
- Regularly updated

**Steps**:
1. Visit https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7
2. Click "Export" or "Download" button
3. Select CSV or Excel format
4. Filter dataset to license types:
   - "Electrical Contractor"
   - "Low Voltage Contractor"
   - "Air Conditioning Contractor"
5. Save filtered data
6. Parse using `TexasScraper.parse_file()`

### Option 2: TDLR License Search with Download

**URL**: https://www.tdlr.texas.gov/LicenseSearch/

**Cost**: FREE

**File Format**: Varies (check download links)

**What You Get**:
- Downloadable license files from TDLR's license search interface
- May require multiple downloads per license type

**Steps**:
1. Visit https://www.tdlr.texas.gov/LicenseSearch/
2. Look for "Download License files" link
3. Download files for each license type
4. Parse using `TexasScraper.parse_file()`

**Expected Columns** (based on configuration):
- License Number
- Company Name
- License Type
- License Status
- Issue Date
- Expiration Date
- Street Address
- City
- State
- ZIP
- County
- Phone Number
- Email Address

### Recommendation

Use **Option 1 (Texas Open Data Portal)** - it's the most straightforward and offers multiple export formats. The data is official and regularly maintained.

---

## Quick Start Summary

**Fastest Path to Real Data:**

1. **Start with Florida** (easiest):
   - Visit https://licenseesearch.fldfs.com/BulkDownload
   - Download "All Valid Licenses - Business" CSV
   - Filter to ER, EL, CAC licenses
   - Test integration script

2. **Then Texas** (also easy):
   - Visit https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7
   - Export as CSV
   - Filter to electrical/HVAC/low voltage contractors
   - Run integration script

3. **Finally California** (requires budget decision):
   - If $235 is approved: Purchase LICENSE MASTER text file
   - If budget constrained: Download PDF lists and extract data
   - Parse and run integration script

---

## Expected Results After Downloads

Once you have CA/FL/TX CSV files, run the integration script:

```bash
python3 scripts/run_tier1_cross_reference.py \
    --license-files ca_licenses.csv fl_licenses.csv tx_licenses.csv \
    --oem-contractors output/grandmaster_list_expanded_20251029.csv \
    --output output/cross_referenced_contractors_$(date +%Y%m%d).csv
```

**Expected Matches**:
- Total licensees: ~120,000
- Total OEM contractors: 8,277
- Expected matches: **6,000-7,000** (assuming 80% of OEM contractors operate in CA/FL/TX)
- Match rate by signal:
  - Phone: ~95% of matches
  - Domain: ~4% additional
  - Total: ~97-99% match rate

**Enrichment Fields Added**:
- license_number
- license_type (Electrical, HVAC, LowVoltage)
- license_status (Active, Inactive, Expired)
- license_state (CA, FL, TX)
- license_tier (BULK)
- license_issue_date
- license_expiration_date
- license_original_issue_date (growth signal - FL only)

---

## File Storage Recommendations

**Directory Structure**:
```
output/
└── state_licenses/
    ├── ca_licenses_20251031.csv (or .txt if paid version)
    ├── fl_licenses_20251031.csv
    └── tx_licenses_20251031.csv
```

**Git Ignore**: Add to `.gitignore`:
```
output/state_licenses/*.csv
output/state_licenses/*.txt
```

License data files can be large (25-300+ MB) and contain PII. Don't commit to git.

---

## Troubleshooting

### Issue: California PDF extraction fails
**Solution**: Use a robust PDF parsing library like `pdfplumber`:
```python
import pdfplumber
with pdfplumber.open('ca_c10_contractors.pdf') as pdf:
    for page in pdf.pages:
        table = page.extract_table()
        # Process table data
```

### Issue: Florida CSV has unexpected columns
**Solution**: Read the ReadMe/Disclaimer file from MyFloridaLicense public records page to understand column mappings

### Issue: Texas Open Data Portal doesn't have contractor licenses
**Solution**: The dataset includes all TDLR licenses. Filter by license type name containing "Contractor" or "Electrician"

### Issue: Integration script fails with "state not recognized"
**Solution**: Ensure CSV filenames contain state abbreviation (CA, FL, or TX). Script uses filename pattern matching:
- `ca_licenses.csv` ✅
- `california_contractors.csv` ✅
- `contractors.csv` ❌ (no state identifier)

---

## Next Steps

After downloading and running integration script:

1. **Validate match quality**: Review `output/cross_referenced_contractors_YYYYMMDD.csv`
2. **Analyze match statistics**: Check phone vs domain match breakdown
3. **Apply ICP scoring boosts**: Use license metadata to improve ICP scores
4. **Generate GTM deliverables**: Update customer match lists with enriched data
5. **Document process**: Note any state-specific quirks for future automated runs

---

**Questions?** Check the state-specific scraper code in:
- `scrapers/license/scraper_factory.py` (CaliforniaScraper, FloridaScraper, TexasScraper)
- `tests/fixtures/` (Sample CSV structures for each state)
