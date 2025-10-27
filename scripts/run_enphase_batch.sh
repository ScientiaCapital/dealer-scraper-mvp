#!/bin/bash
# Enphase batch runner - uses rebuilt progress from CSV
set -e

echo "=========================================="
echo "ENPHASE BATCH COLLECTION"
echo "=========================================="

# Rebuild progress from CSV first (single source of truth)
python3 scripts/rebuild_progress_from_csv.py

# Get remaining ZIPs from progress file
REMAINING=$(python3 -c "
import json
with open('output/enphase_platinum_gold_progress.json') as f:
    p = json.load(f)
    print(' '.join(p['remaining_zips']))
")

echo "Remaining ZIPs: $(echo $REMAINING | wc -w)"
echo ""

# Loop through each ZIP
for zip in $REMAINING; do
    echo "==========================================
"
    echo "Collecting ZIP: $zip"
    echo "=========================================="

    python3 scripts/enphase_collect_single_zip.py $zip

    if [ $? -eq 0 ]; then
        echo "✅ ZIP $zip completed"
    else
        echo "⚠️  ZIP $zip failed, continuing..."
    fi

    echo ""
    sleep 2
done

echo "=========================================="
echo "✅ ENPHASE BATCH COMPLETE!"
echo "=========================================="

# Final deduplication
python3 scripts/deduplicate_enphase_installers.py
