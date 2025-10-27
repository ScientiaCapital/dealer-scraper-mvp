#!/bin/bash
# Collect the final 7 ZIPs (skipping problematic 60022)

ZIPS=("60043" "60093" "60521" "76092" "77010" "77401" "78733")

echo "=========================================="
echo "FINAL 7 ZIPS COLLECTION"
echo "=========================================="
echo ""

for zip in "${ZIPS[@]}"; do
    echo "=========================================="
    echo "Collecting ZIP: $zip"
    echo "=========================================="

    python3 scripts/enphase_collect_single_zip.py $zip

    if [ $? -eq 0 ]; then
        echo "✅ ZIP $zip completed"
    else
        echo "⚠️  ZIP $zip failed"
    fi

    echo ""
    sleep 3
done

echo "=========================================="
echo "✅ FINAL 7 ZIPS COLLECTION COMPLETE!"
echo "=========================================="

# Rebuild progress
python3 scripts/rebuild_progress_from_csv.py
