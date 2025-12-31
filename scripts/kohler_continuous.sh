#!/bin/bash
cd /Users/tmk/tmp/worktrees/dealer-scraper-mvp/feature-sprint-dec27
source .venv/bin/activate

while true; do
    echo "$(date): Starting Kohler batch..."
    python3 scripts/kohler_master_scraper.py 0
    
    # Check if we're done (look for 395/395 in status)
    COMPLETED=$(grep -o 'ZIPs completed: [0-9]*/395' output/kohler/kohler_master.log | tail -1 | grep -o '[0-9]*/395')
    echo "$(date): Status: $COMPLETED"
    
    if [[ "$COMPLETED" == "395/395" ]]; then
        echo "$(date): All ZIPs complete!"
        break
    fi
    
    echo "$(date): Sleeping 5 seconds before next batch..."
    sleep 5
done
