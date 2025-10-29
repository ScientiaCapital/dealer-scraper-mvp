"""
Test script to check Trane dealer detail pages for phone numbers.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
import time

def test_dealer_detail_page():
    """Test extracting phone from a Trane dealer detail page."""
    
    # Test with first dealer from our extraction
    detail_url = "https://www.trane.com/residential/en/dealers/1st-choice-heating-and-air-knoxville-tennessee-379211"
    
    with sync_playwright() as p:
        print(f"\n🔧 Testing Trane dealer detail page...")
        print(f"   URL: {detail_url}\n")
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to detail page
            print("   → Navigating to dealer detail page...")
            page.goto(detail_url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(3)
            
            # Check for phone numbers
            phone_check = page.evaluate("""
                () => {
                    // Strategy 1: tel: links
                    const telLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'));
                    
                    // Strategy 2: Text patterns (###-###-####)
                    const phonePatterns = document.body.textContent.match(/\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}/g) || [];
                    
                    // Strategy 3: Look for "Phone:", "Call:", "Contact:" labels
                    const allText = document.body.textContent;
                    const phoneMatch = allText.match(/(?:Phone|Call|Contact|Tel):\\s*([\\d\\-\\.\\s()]+)/i);
                    
                    return {
                        telLinks: telLinks.map(l => ({
                            href: l.href,
                            text: l.textContent.trim(),
                            parent: l.parentElement?.className || ''
                        })),
                        phonePatterns: phonePatterns.slice(0, 5),
                        phoneMatch: phoneMatch ? phoneMatch[0] : null,
                        hasAddress: allText.includes('Address') || allText.includes('Location'),
                        hasWebsite: document.querySelectorAll('a[href^="http"]').length > 0
                    };
                }
            """)
            
            print(f"   📞 Phone detection results:")
            print(f"      Tel links found: {len(phone_check['telLinks'])}")
            if phone_check['telLinks']:
                for link in phone_check['telLinks'][:3]:
                    print(f"         - {link['href']} | Text: {link['text']}")
            
            print(f"\n      Phone patterns in text: {len(phone_check['phonePatterns'])}")
            if phone_check['phonePatterns']:
                for pattern in phone_check['phonePatterns'][:3]:
                    print(f"         - {pattern}")
            
            if phone_check['phoneMatch']:
                print(f"\n      Phone label match: {phone_check['phoneMatch']}")
            
            print(f"\n      Has address info: {phone_check['hasAddress']}")
            print(f"      Has website links: {phone_check['hasWebsite']}")
            
            # Take screenshot
            os.makedirs("output/trane_debug", exist_ok=True)
            page.screenshot(path="output/trane_debug/detail_page_sample.png", full_page=True)
            print(f"\n   📸 Screenshot saved: output/trane_debug/detail_page_sample.png")
            
            browser.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            browser.close()


if __name__ == "__main__":
    test_dealer_detail_page()
