"""
Test script for Trane scraper - Extract ALL dealers (no ZIP filtering)

Trane lists all dealers on a single page, so we can scrape them all at once.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
import json
import time

def test_trane_extraction():
    """Test Trane dealer extraction."""
    
    url = "https://www.trane.com/residential/en/dealers/"
    
    with sync_playwright() as p:
        print(f"\n🔧 Testing Trane dealer extraction...")
        print(f"   URL: {url}\n")
        
        # Launch browser in non-headless mode to see what's happening
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to dealer locator
            print("   → Navigating to Trane dealer locator...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(3)  # Let page fully load
            
            # Take screenshot for reference
            os.makedirs("output/trane_debug", exist_ok=True)
            page.screenshot(path="output/trane_debug/01_initial_page.png")
            print("   → Screenshot saved: output/trane_debug/01_initial_page.png")
            
            # Try to find dealer elements using different strategies
            print("\n   🔍 Testing different selector strategies...")
            
            # Strategy 1: Look for any links with tel: hrefs
            phone_links_count = page.evaluate("""
                () => document.querySelectorAll('a[href^="tel:"]').length
            """)
            print(f"   → Found {phone_links_count} phone links (tel: hrefs)")
            
            # Strategy 2: Look for headings (h1-h6)
            headings = page.evaluate("""
                () => {
                    const counts = {};
                    for (let i = 1; i <= 6; i++) {
                        counts[`h${i}`] = document.querySelectorAll(`h${i}`).length;
                    }
                    return counts;
                }
            """)
            print(f"   → Heading counts: {headings}")
            
            # Strategy 3: Look for elements with "dealer" in class name
            dealer_class_count = page.evaluate("""
                () => document.querySelectorAll('[class*="dealer" i], [class*="location" i], [class*="contractor" i]').length
            """)
            print(f"   → Elements with dealer/location/contractor in class: {dealer_class_count}")
            
            # Strategy 4: Extract sample phone links to understand structure
            if phone_links_count > 0:
                sample_phone_structures = page.evaluate("""
                    () => {
                        const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]')).slice(0, 3);
                        return phoneLinks.map(link => {
                            return {
                                phone: link.href,
                                text: link.textContent.trim(),
                                parentTag: link.parentElement?.tagName,
                                parentClass: link.parentElement?.className,
                                grandparentTag: link.parentElement?.parentElement?.tagName,
                                grandparentClass: link.parentElement?.parentElement?.className
                            };
                        });
                    }
                """)
                print(f"\n   📋 Sample phone link structures:")
                for i, sample in enumerate(sample_phone_structures, 1):
                    print(f"      {i}. Phone: {sample['phone']}")
                    print(f"         Parent: <{sample['parentTag']} class=\"{sample['parentClass']}\">")
                    print(f"         Grandparent: <{sample['grandparentTag']} class=\"{sample['grandparentClass']}\">")
                    print()
            
            # Strategy 5: Try the current extraction script
            print("\n   🧪 Testing current extraction script...")
            
            extraction_script = """
            () => {
              const dealers = [];
              
              // Find all dealer cards - look for headings/containers with dealer names
              const dealerCards = Array.from(document.querySelectorAll('[class*="dealer"], [class*="Dealer"], [class*="card"]')).filter(card => {
                // Must have both name and phone to be a valid dealer card
                const hasName = card.textContent.length > 10;
                const hasPhone = card.querySelector('a[href^="tel:"]') !== null;
                return hasName && hasPhone;
              });
              
              console.log('Found dealer cards:', dealerCards.length);
              
              // Remove duplicates by phone number
              const seen = new Set();
              const uniqueCards = dealerCards.filter(card => {
                const phoneLink = card.querySelector('a[href^="tel:"]');
                if (!phoneLink) return false;
                const phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
                if (seen.has(phone)) return false;
                seen.add(phone);
                return true;
              });
              
              console.log('Unique dealer cards:', uniqueCards.length);
              
              uniqueCards.slice(0, 5).forEach(card => {
                // Extract dealer name (usually in a heading or strong tag)
                let name = '';
                const nameEl = card.querySelector('h2, h3, h4, h5, strong, [class*="name"]');
                if (nameEl) {
                  name = nameEl.textContent.trim();
                }
                
                // Extract phone from tel: link
                const phoneLink = card.querySelector('a[href^="tel:"]');
                let phone = '';
                if (phoneLink) {
                  phone = phoneLink.href.replace('tel:', '').replace(/[^0-9]/g, '');
                  if (phone.length === 11 && phone.startsWith('1')) {
                    phone = phone.substring(1);
                  }
                }
                
                dealers.push({
                  name: name,
                  phone: phone,
                  cardTag: card.tagName,
                  cardClass: card.className
                });
              });
              
              return dealers;
            }
            """
            
            current_results = page.evaluate(extraction_script)
            print(f"   → Current script found {len(current_results)} dealers")
            if len(current_results) > 0:
                print(f"   → Sample dealers:")
                for dealer in current_results[:3]:
                    print(f"      - {dealer['name']} | {dealer['phone']}")
                    print(f"        Card: <{dealer['cardTag']} class=\"{dealer['cardClass']}\">")
            
            # Pause for manual inspection
            print("\n   ⏸️  Browser paused for manual inspection...")
            print("   Press Enter in this terminal when ready to continue...")
            input()
            
            browser.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            browser.close()
            raise


if __name__ == "__main__":
    test_trane_extraction()
