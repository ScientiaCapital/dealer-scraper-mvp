#!/bin/bash
# Florida License Data Download Helper Script
# Run after manually downloading from https://licenseesearch.fldfs.com/BulkDownload

echo "Florida License Data Download Helper"
echo "===================================="
echo ""
echo "Step 1: Download FL data manually"
echo "  URL: https://licenseesearch.fldfs.com/BulkDownload"
echo "  File: 'All Valid Licenses - Business' (24.32 MB)"
echo "  Save to: output/state_licenses/fl_licenses_raw_20251031.csv"
echo ""
echo "Step 2: Once downloaded, this script will filter to contractor types"
echo ""

# Check if raw file exists
if [ ! -f "output/state_licenses/fl_licenses_raw_20251031.csv" ]; then
    echo "❌ Raw file not found: output/state_licenses/fl_licenses_raw_20251031.csv"
    echo ""
    echo "Please download manually from:"
    echo "https://licenseesearch.fldfs.com/BulkDownload"
    echo ""
    exit 1
fi

echo "✅ Found raw file"
echo ""
echo "Filtering to contractor license types (ER, EL, CAC)..."

python3 << 'EOF'
import pandas as pd

# Read raw file
print("Loading raw FL license data...")
df = pd.read_csv('output/state_licenses/fl_licenses_raw_20251031.csv')
print(f"  Total licenses: {len(df):,}")

# Check column names (may vary)
print(f"  Columns: {list(df.columns)}")

# Find the license type column (might be 'License Type', 'LicType', etc.)
type_col = None
for col in df.columns:
    if 'type' in col.lower() and 'license' in col.lower():
        type_col = col
        break

if not type_col:
    print("❌ Could not find license type column")
    print("Available columns:", list(df.columns))
    exit(1)

print(f"  Using column: '{type_col}'")

# Filter to contractor types
contractor_types = ['ER', 'EL', 'CAC']
contractors = df[df[type_col].isin(contractor_types)]

print(f"\nFiltered to contractor types:")
print(f"  ER (Electrical): {len(df[df[type_col] == 'ER']):,}")
print(f"  EL (Low Voltage): {len(df[df[type_col] == 'EL']):,}")
print(f"  CAC (HVAC): {len(df[df[type_col] == 'CAC']):,}")
print(f"  Total: {len(contractors):,}")

# Save filtered data
contractors.to_csv('output/state_licenses/fl_licenses_20251031.csv', index=False)
print(f"\n✅ Saved to: output/state_licenses/fl_licenses_20251031.csv")

EOF

echo ""
echo "===================================="
echo "Next step: Run integration script"
echo ""
echo "python3 scripts/run_tier1_cross_reference.py \\"
echo "    --license-files output/state_licenses/fl_licenses_20251031.csv \\"
echo "    --oem-contractors output/grandmaster_list_expanded_20251029.csv \\"
echo "    --output output/fl_cross_referenced_20251031.csv"
echo ""
