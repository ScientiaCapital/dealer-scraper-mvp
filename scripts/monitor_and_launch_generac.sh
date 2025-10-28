#!/bin/bash
# Monitor Briggs completion and auto-launch Generac

echo "🔍 Monitoring Briggs national run for completion..."
echo "📊 Current: ZIP 76/137 (55% complete)"
echo ""

while true; do
  # Check if Briggs is complete
  if grep -q "✅ SCRAPING COMPLETE" /Users/tmkipper/Desktop/dealer-scraper-mvp/output/briggs_national.log; then
    echo ""
    echo "🎉 Briggs scraping complete!"
    echo ""
    
    # Extract final stats
    echo "📊 Briggs Final Results:"
    tail -50 /Users/tmkipper/Desktop/dealer-scraper-mvp/output/briggs_national.log | grep -E "Total dealers:|unique dealers|Deduplication rate:"
    echo ""
    
    echo "🎬 Starting Generac with asciinema recording..."
    echo ""
    
    # Start asciinema recording
    asciinema rec /Users/tmkipper/Desktop/dealer-scraper-mvp/output/generac_national_demo.cast -c "PYTHONPATH=. python3 -u scripts/run_generac_national.py 2>&1 | tee output/generac_national.log"
    
    break
  fi
  
  # Show progress update every 2 minutes
  CURRENT_ZIP=$(tail -100 /Users/tmkipper/Desktop/dealer-scraper-mvp/output/briggs_national.log | grep -oE "\[[0-9]+/137\]" | tail -1)
  CURRENT_TOTAL=$(tail -100 /Users/tmkipper/Desktop/dealer-scraper-mvp/output/briggs_national.log | grep -oE "Total: [0-9]+" | tail -1)
  
  echo "⏳ $(date +%H:%M:%S) - Briggs still running: $CURRENT_ZIP $CURRENT_TOTAL"
  
  sleep 120  # Check every 2 minutes
done
