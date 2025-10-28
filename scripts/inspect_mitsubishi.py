#!/usr/bin/env python3
"""
Quick inspection of Mitsubishi Diamond Commercial contractor locator
to understand DOM structure for extraction script.

Run this with Playwright MCP to manually inspect the page.
"""

print("=" * 80)
print("MITSUBISHI DIAMOND COMMERCIAL CONTRACTOR LOCATOR - MANUAL INSPECTION")
print("=" * 80)
print()
print("URL: https://www.mitsubishicomfort.com/find-a-diamond-commercial-contractor")
print()
print("INSTRUCTIONS:")
print("-" * 80)
print("1. Use Playwright MCP to navigate to the URL above")
print("2. Use browser_snapshot to get the accessibility tree")
print("3. Fill ZIP code field (attribute: 'zipCode') with test ZIP: 10001")
print("4. Click Submit button")
print("5. Wait 3-5 seconds for AJAX results to load")
print("6. Use browser_snapshot again to see results structure")
print("7. Use browser_evaluate to extract dealer data JavaScript")
print()
print("EXPECTED DEALER FIELDS:")
print("-" * 80)
print("- Company name")
print("- Address (street, city, state, ZIP)")
print("- Phone number")
print("- Website/domain")
print("- Diamond Commercial certification badge")
print("- 12-year warranty indicator")
print()
print("EXTRACTION STRATEGY:")
print("-" * 80)
print("Similar to Generac/Briggs/Cummins pattern:")
print("  1. Find results container (likely CSS class 'contractor' or 'dealer')")
print("  2. Loop through result cards")
print("  3. Extract text content for each field")
print("  4. Return JSON array of dealer objects")
print()
print("=" * 80)
