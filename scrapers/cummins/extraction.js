/**
 * Cummins Home Standby Generator Dealer Extraction Script
 *
 * URL: https://locator.cummins.com/ (Cummins Sales and Service Locations)
 * Alternative: https://www.cummins.com/na/generators/home-standby/find-a-dealer
 *
 * DATA PATTERN:
 * Cummins uses a map-based locator with dealer cards:
 * - Dealer cards: .dealer-listing-col.com_locator_entry
 * - Name: .title .info h3 a.marker-link
 * - Tier: .title .info .location (e.g., "Dealer")
 * - Phone: .phone a[href^="tel:"]
 * - Website: .website a
 * - Address: .address .address-info (contains <br> tags)
 * - Distance: <p> text (format: "Approximately 26.26 Mi from 94102")
 *
 * EXTRACTION STRATEGY:
 * 1. Find all dealer cards (.dealer-listing-col.com_locator_entry)
 * 2. Extract name from h3 a.marker-link
 * 3. Extract tier from .location span
 * 4. Extract phone from tel: link
 * 5. Extract website and parse domain
 * 6. Parse address split by <br> tags:
 *    - First part: Street address
 *    - Second part: "City, STATE ZIP"
 * 7. Extract distance from paragraph text (regex: /(\d+\.\d+)\s*Mi/i)
 * 8. Filter out dealers without name/phone
 *
 * ADDRESS PARSING:
 * Address is split by <br> tags in HTML:
 * Line 1: "7045 North Loop E Service Road"
 * Line 2: "Houston, TX 77028"
 *
 * TESTED: Map shows 200 dealers nationwide
 */

function extractCumminsDealers() {
  console.log('[Cummins] Starting dealer extraction...');

  // Find all dealer cards
  const dealerCards = Array.from(document.querySelectorAll('.dealer-listing-col.com_locator_entry'));

  console.log(`[Cummins] Found ${dealerCards.length} dealer cards`);

  const dealers = dealerCards.map((card, index) => {
    try {
      // Extract dealer name
      const nameLink = card.querySelector('.title .info h3 a.marker-link');
      const name = nameLink ? nameLink.textContent.trim() : '';

      // Extract tier (e.g., "Dealer")
      const tierSpan = card.querySelector('.title .info .location');
      const tier = tierSpan ? tierSpan.textContent.trim() : 'Authorized Dealer';

      // Extract phone
      const phoneLink = card.querySelector('.phone a[href^="tel:"]');
      const phone = phoneLink ? phoneLink.textContent.trim() : '';

      // Extract website
      const websiteLink = card.querySelector('.website a');
      const website = websiteLink ? websiteLink.href : '';

      // Extract domain from website
      let domain = '';
      if (website) {
        try {
          const url = new URL(website);
          domain = url.hostname.replace('www.', '');
        } catch (e) {
          console.log(`[Cummins] Card ${index + 1}: Invalid website URL`);
        }
      }

      // Extract address (contains <br> tags)
      const addressDiv = card.querySelector('.address .address-info');
      let street = '';
      let city = '';
      let state = '';
      let zip = '';
      let address_full = '';

      if (addressDiv) {
        // Get innerHTML to preserve <br> structure
        const addressHTML = addressDiv.innerHTML;

        // Split by <br> tag
        const addressParts = addressHTML.split(/<br\s*\/?>/i).map(p => p.trim()).filter(p => p);

        if (addressParts.length >= 2) {
          // First part: street address
          street = addressParts[0].trim();

          // Second part: "City, STATE ZIP"
          const cityStateZip = addressParts[1].trim();
          const match = cityStateZip.match(/^([^,]+),\s*([A-Z]{2,})\s+(\d{5})/);

          if (match) {
            city = match[1].trim();
            state = match[2].trim();
            zip = match[3].trim();
          } else {
            // Fallback: just use the text as-is
            city = cityStateZip;
          }
        }

        address_full = addressDiv.textContent.trim().replace(/\s+/g, ' ');
      }

      // Extract distance
      const distanceP = card.querySelector('p');
      let distance = '';
      let distance_miles = 0;

      if (distanceP) {
        const distanceText = distanceP.textContent.trim();
        // Format: "Approximately 26.26 Mi from 94102"
        const milesMatch = distanceText.match(/([\d.]+)\s*Mi/i);
        if (milesMatch) {
          distance_miles = parseFloat(milesMatch[1]);
          distance = `${distance_miles} mi`;
        }
      }

      return {
        name: name,
        phone: phone,
        website: website,
        domain: domain,
        street: street,
        city: city,
        state: state,
        zip: zip,
        address_full: address_full,
        rating: 0,  // Cummins doesn't show ratings
        review_count: 0,
        tier: tier,
        certifications: [tier],
        distance: distance,
        distance_miles: distance_miles,
        oem_source: 'Cummins'
      };
    } catch (e) {
      console.error(`[Cummins] Error extracting dealer card ${index + 1}:`, e);
      return null;
    }
  });

  // Filter out null/invalid dealers (must have name and phone)
  const validDealers = dealers.filter(d => d && d.name && d.phone);

  console.log(`[Cummins] Successfully extracted ${validDealers.length} valid dealers`);

  return validDealers;
}

// Execute extraction
extractCumminsDealers();
