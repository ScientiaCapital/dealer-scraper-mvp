"""
Test script for Trane table-based extraction

Trane lists ALL dealers in a sortable table on page load (no ZIP search needed).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
import json
import time

def test_trane_table_extraction():
    """Test Trane dealer table extraction."""
    
    url = "https://www.trane.com/residential/en/dealers/"
    
    with sync_playwright() as p:
        print(f"\n🔧 Testing Trane table extraction...")
        print(f"   URL: {url}\n")
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate
            print("   → Navigating to Trane dealer directory...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(5)  # Wait for table to fully render
            
            # New extraction script for table format
            extraction_script = """
            () => {
              const dealers = [];
              
              // Strategy 1: Find table rows
              console.log('Looking for table rows...');
              const rows = Array.from(document.querySelectorAll('tr'));
              console.log('Found rows:', rows.length);
              
              // Strategy 2: Find all dealer name links (red text in screenshot)
              const dealerLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const text = link.textContent.trim();
                // Dealer names seem to be in ALL CAPS or Title Case, reasonable length
                return text.length > 5 && text.length < 100 && !text.includes('Find a') && !text.includes('Trane');
              });
              console.log('Found potential dealer links:', dealerLinks.length);
              
              // Strategy 3: Look for table with dealer data
              const tables = Array.from(document.querySelectorAll('table'));
              console.log('Found tables:', tables.length);
              
              if (tables.length > 0) {
                tables.forEach((table, idx) => {
                  console.log(`Table ${idx} has ${table.querySelectorAll('tr').length} rows`);
                });
              }
              
              // Try extracting from rows
              rows.forEach((row, idx) => {
                const cells = Array.from(row.querySelectorAll('td, th'));
                if (cells.length >= 4) {  // Need at least: name, state, city, zip
                  const cellTexts = cells.map(c => c.textContent.trim());
                  
                  // Look for dealer name (usually first cell, has a link)
                  const nameLink = cells[0]?.querySelector('a');
                  if (nameLink) {
                    const name = nameLink.textContent.trim();
                    
                    // Check if this looks like a dealer name (not a header)
                    if (name.length > 5 && name !== 'Dealer Name' && !name.includes('Heating') === false) {
                      const state = cells[1]?.textContent.trim() || '';
                      const city = cells[2]?.textContent.trim() || '';
                      const zip = cells[3]?.textContent.trim() || '';
                      const country = cells[4]?.textContent.trim() || 'US';
                      
                      dealers.push({
                        name: name,
                        state: state,
                        city: city,
                        zip: zip,
                        country: country,
                        detailUrl: nameLink.href || ''
                      });
                    }
                  }
                }
              });
              
              console.log('Extracted dealers:', dealers.length);
              return dealers;
            }
            """
            
            print("   → Executing table extraction script...")
            dealers = page.evaluate(extraction_script)
            
            print(f"\n   ✅ Extracted {len(dealers)} dealers from table!\n")
            
            if len(dealers) > 0:
                print("   📊 Sample dealers (first 10):")
                for i, dealer in enumerate(dealers[:10], 1):
                    print(f"      {i:2d}. {dealer['name']}")
                    print(f"          Location: {dealer['city']}, {dealer['state']} {dealer['zip']}")
                    if dealer.get('detailUrl'):
                        print(f"          Detail URL: {dealer['detailUrl'][:80]}...")
                    print()
                
                # Save full results
                os.makedirs("output/trane_debug", exist_ok=True)
                output_file = "output/trane_debug/table_extraction_test.json"
                with open(output_file, 'w') as f:
                    json.dump(dealers, f, indent=2)
                print(f"   💾 Full results saved to: {output_file}")
                print(f"   📈 Total dealers extracted: {len(dealers)}")
                
                # Statistics
                states = {}
                for dealer in dealers:
                    state = dealer.get('state', 'Unknown')
                    states[state] = states.get(state, 0) + 1
                
                print(f"\n   📍 Dealers by state (top 10):")
                for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"      {state}: {count} dealers")
            else:
                print("   ❌ No dealers extracted - extraction script needs debugging")
                print("\n   💡 Trying alternative approach...")
                
                # Debug: Show page structure
                page_info = page.evaluate("""
                    () => {
                        return {
                            title: document.title,
                            tables: document.querySelectorAll('table').length,
                            rows: document.querySelectorAll('tr').length,
                            links: document.querySelectorAll('a').length,
                            bodyText: document.body.textContent.substring(0, 500)
                        };
                    }
                """)
                print(f"   Page title: {page_info['title']}")
                print(f"   Tables: {page_info['tables']}")
                print(f"   Rows: {page_info['rows']}")
                print(f"   Links: {page_info['links']}")
                print(f"   Body text preview: {page_info['bodyText'][:200]}...")
            
            browser.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
            raise


if __name__ == "__main__":
    test_trane_table_extraction()
