#!/bin/bash
# Quick Enphase monitoring script

echo "════════════════════════════════════════"
echo "📊 ENPHASE COLLECTION STATUS"
echo "════════════════════════════════════════"

# Check if batch is running
if pgrep -f "run_enphase_batch.sh" > /dev/null; then
    echo "✅ Batch script: RUNNING"
else
    echo "⚠️  Batch script: STOPPED"
fi

echo ""

# Total installers
TOTAL=$(wc -l < output/enphase_platinum_gold_installers.csv)
INSTALLERS=$((TOTAL - 1))  # Subtract header
echo "📈 Total installers: $INSTALLERS"

# Completed ZIPs
COMPLETED=$(python3 -c "
import json
with open('output/enphase_platinum_gold_progress.json') as f:
    p = json.load(f)
    print(len(p['completed_zips']))
")
echo "✅ Completed ZIPs: $COMPLETED / 41"

# Current ZIP from log
CURRENT=$(tail -20 output/enphase_batch_final.log | grep "Collecting ZIP:" | tail -1 | awk '{print $NF}')
if [ -n "$CURRENT" ]; then
    echo "🔄 Current ZIP: $CURRENT"
fi

echo ""
echo "════════════════════════════════════════"

# Recent progress
echo "📝 Last 5 completed:"
tail -100 output/enphase_batch_final.log | grep "Successfully collected" | tail -5
