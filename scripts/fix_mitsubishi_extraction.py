#!/usr/bin/env python3
"""
Fix the Mitsubishi scraper extraction script based on actual DOM structure
"""

def get_improved_extraction_script():
    """Improved extraction script for Mitsubishi Diamond Commercial contractors"""
    return """
() => {
  const contractors = [];
  const seen = new Set();

  // Find all contractor cards - they're in a grid layout
  const contractorCards = document.querySelectorAll('div[role="generic"]:has(h3)');

  // If no cards found, try alternative method with h3 elements
  if (contractorCards.length === 0) {
    const h3Elements = document.querySelectorAll('h3');

    h3Elements.forEach(h3 => {
      const name = h3.textContent.trim();

      // Skip non-contractor headings
      if (name.toLowerCase().includes('training') ||
          name.toLowerCase().includes('warranty') ||
          name.toLowerCase().includes('hire with') ||
          name.toLowerCase().includes('manage consent') ||
          name.toLowerCase().includes('cookie') ||
          name.length < 3) {
        return;
      }

      // Get the parent container that has all the info
      const container = h3.closest('div[class*="Card"]') ||
                       h3.parentElement?.parentElement ||
                       h3.parentElement;

      if (!container) return;

      // Extract phone from tel: link
      let phone = '';
      const phoneLink = container.querySelector('a[href^="tel:"]');
      if (phoneLink) {
        // Extract just digits from the href
        phone = phoneLink.href.replace('tel:', '').replace(/\\D/g, '');
        // Remove country code if present
        if (phone.length === 11 && phone.startsWith('1')) {
          phone = phone.substring(1);
        }
      }

      // Extract location from text containing "miles away"
      let city = '', state = '', zip = '';
      const locationEl = container.querySelector('[class*="miles away"]') ||
                        container.querySelector('div:has(img[alt*="location"]) + div') ||
                        Array.from(container.querySelectorAll('div')).find(el =>
                          el.textContent.includes('miles away'));

      if (locationEl) {
        // Remove the "X.X miles away" part and extract location
        const locationText = locationEl.textContent
          .replace(/\\d+(\\.\\d+)?\\s*miles?\\s*away/gi, '')
          .trim();

        // Parse "City, ST ZIP" format
        const parts = locationText.split(',').map(s => s.trim());
        if (parts.length >= 2) {
          city = parts[0];
          const stateZip = parts[1].trim().split(/\\s+/);
          if (stateZip.length >= 2) {
            state = stateZip[0];
            zip = stateZip[1];
          }
        }
      }

      // Alternative: look for pattern in container text
      if (!city && container.textContent) {
        const match = container.textContent.match(/([A-Za-z][A-Za-z\\s-]+),\\s*([A-Z]{2})\\s+(\\d{5})/);
        if (match) {
          city = match[1].trim();
          state = match[2];
          zip = match[3];
        }
      }

      // Extract website from "Visit website" link
      let website = '';
      let domain = '';

      // Look for links with text containing "website" or starting with http
      const websiteLink = container.querySelector('a[href*="//"][href*="."]:not([href*="tel:"]):not([href*="mitsubishicomfort"]):not([href*="google"])');
      if (websiteLink) {
        website = websiteLink.href;
        // Extract domain from URL
        try {
          const url = new URL(website);
          domain = url.hostname.replace('www.', '');
        } catch (e) {
          domain = '';
        }
      }

      // Create unique key to avoid duplicates
      const key = `${phone}|${name}`;

      // Only add if we have minimum required fields and not seen before
      if (!seen.has(key) && name && phone) {
        seen.add(key);

        contractors.push({
          name: name,
          phone: phone,
          domain: domain,
          website: website,
          street: '',  // Not available in results
          city: city || '',
          state: state || '',
          zip: zip || '',
          address_full: city && state ? `${city}, ${state} ${zip}`.trim() : '',
          rating: 0.0,
          review_count: 0,
          tier: 'Diamond Commercial',
          certifications: ['Diamond Commercial', 'VRF Certified', '12-Year Warranty'],
          distance: '',
          distance_miles: 0.0,
          oem_source: 'Mitsubishi'
        });
      }
    });
  }

  return contractors;
}
"""

if __name__ == "__main__":
    print("Improved Mitsubishi extraction script:")
    print(get_improved_extraction_script())