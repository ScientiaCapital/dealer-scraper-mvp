#!/bin/bash
# Organize output/ folder with clear naming conventions
# Run from project root: ./organize_output.sh

set -e

echo "📁 Organizing output/ directory..."
echo ""

# Move existing OEM data files that are already in oem_data subdirs
echo "✅ OEM data directories already created"

# Move OEM-specific CSVs/JSONs from root
echo "🔄 Moving OEM-specific files..."
[ -f output/enphase_platinum_gold_deduped_20251026.csv ] && mv -v output/enphase_platinum_gold_deduped_20251026.csv output/oem_data/enphase/
[ -f output/carrier_checkpoint.json ] && mv -v output/carrier_checkpoint.json output/oem_data/carrier/

# Move GTM deliverables
echo "🔄 Moving GTM deliverables..."
[ -f output/google_ads_customer_match_20251029.csv ] && mv -v output/google_ads_customer_match_20251029.csv output/gtm_deliverables/
[ -f output/meta_custom_audience_20251029.csv ] && mv -v output/meta_custom_audience_20251029.csv output/gtm_deliverables/

# Move analysis files - ICP Scoring
echo "🔄 Moving ICP scoring files..."
[ -f output/icp_scored_contractors_final_20251029.csv ] && mv -v output/icp_scored_contractors_final_20251029.csv output/analysis/icp_scoring/
[ -f output/top_200_prospects_final_20251029.csv ] && mv -v output/top_200_prospects_final_20251029.csv output/analysis/icp_scoring/
[ -f output/gold_tier_prospects_20251029.csv ] && mv -v output/gold_tier_prospects_20251029.csv output/analysis/icp_scoring/
[ -f output/silver_tier_prospects_20251029.csv ] && mv -v output/silver_tier_prospects_20251029.csv output/analysis/icp_scoring/
[ -f output/bronze_tier_prospects_20251029.csv ] && mv -v output/bronze_tier_prospects_20251029.csv output/analysis/icp_scoring/
[ -f output/tx_icp_scored_20251031.csv ] && mv -v output/tx_icp_scored_20251031.csv output/analysis/icp_scoring/
[ -f output/tx_final_hottest_leads_20251031.csv ] && mv -v output/tx_final_hottest_leads_20251031.csv output/analysis/icp_scoring/

# Move analysis files - Multi-OEM
echo "🔄 Moving multi-OEM analysis files..."
[ -f output/multi_oem_crossovers_expanded_20251029.csv ] && mv -v output/multi_oem_crossovers_expanded_20251029.csv output/analysis/multi_oem/

# Move analysis files - Cross-reference
echo "🔄 Moving cross-reference files..."
[ -f output/tx_cross_referenced_20251031.csv ] && mv -v output/tx_cross_referenced_20251031.csv output/analysis/cross_reference/
[ -f output/nyc_cross_referenced_20251031.csv ] && mv -v output/nyc_cross_referenced_20251031.csv output/analysis/cross_reference/
[ -f output/tx_fuzzy_name_matches_20251031.csv ] && mv -v output/tx_fuzzy_name_matches_20251031.csv output/analysis/cross_reference/
[ -f output/nyc_fuzzy_matches_20251031.csv ] && mv -v output/nyc_fuzzy_matches_20251031.csv output/analysis/cross_reference/
[ -f output/fl_fuzzy_name_matches_20251031.csv ] && mv -v output/fl_fuzzy_name_matches_20251031.csv output/analysis/cross_reference/
[ -f output/nyc_phone_matches_20251031.csv ] && mv -v output/nyc_phone_matches_20251031.csv output/analysis/cross_reference/
[ -f output/tx_full_matched_licenses_20251031.csv ] && mv -v output/tx_full_matched_licenses_20251031.csv output/analysis/cross_reference/
[ -f output/enriched_contractors_tx_nyc_20251031.csv ] && mv -v output/enriched_contractors_tx_nyc_20251031.csv output/analysis/cross_reference/
[ -f output/test_cross_reference.csv ] && mv -v output/test_cross_reference.csv output/analysis/cross_reference/

# Move all log files
echo "🔄 Moving log files..."
find output -maxdepth 1 -name "*.log" -exec mv -v {} output/logs/ \;

# Move state license files (already in subdirectory, just verify)
echo "✅ State license files already organized in output/state_licenses/"

# Move trane debug files
[ -d output/trane_debug ] && echo "✅ Trane debug files already in subdirectory"

# Keep grandmaster list in root for easy access
echo "✅ Keeping grandmaster list in root: grandmaster_list_expanded_20251029.csv"

echo ""
echo "✅ Organization complete!"
echo ""
echo "📊 Final structure:"
tree -L 2 output/ || ls -R output/
