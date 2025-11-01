/**
 * Kohler Home Generator Dealer Extraction Script
 *
 * URL: https://www.kohlerhomeenergy.rehlko.com/find-a-dealer
 * Note: Kohler Energy rebranded to Rehlko in 2024
 *
 * DATA PATTERN:
 * Kohler uses a list-based dealer locator with dealer cards:
 * - Dealer cards: ul > li (list items)
 * - Name: First paragraph in card
 * - Distance: Second paragraph (format: "51.5 miles")
 * - Tier badges: Generic elements with text (e.g., "Gold Dealer", "Titan Certified")
 * - Address: Paragraph (format: "150 NARDI LANE, Martinez, CA 94553")
 * - Services: Paragraph (format: "Sales, Installation, and Service up to 150kW")
 * - Phone: a[href^="tel:"]
 * - Website: a with text "Website"
 * - Features: Financing options, Virtual site visit (icons with labels)
 *
 * TIER SYSTEM:
 * - Gold Dealer (highest tier)
 * - Silver Dealer
 * - Bronze Dealer
 * - Titan Certified (premium certification)
 * - Standard (default if no tier badges)
 *
 * EXTRACTION STRATEGY:
 * 1. Find all dealer cards (ul > li elements)
 * 2. Extract name from first paragraph
 * 3. Extract distance from second paragraph (parse miles)
 * 4. Detect tier badges from text content
 * 5. Extract phone from tel: link
 * 6. Extract website from "Website" link and parse domain
 * 7. Parse address (single-line format: "STREET, CITY, STATE ZIP")
 * 8. Extract services description (optional)
 * 9. Filter out dealers without name/phone
 *
 * ADDRESS PARSING:
 * Format: "150 NARDI LANE, Martinez, CA 94553"
 * Regex: /^(.+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})/
 * Groups: street, city, state, zip
 *
 * TESTED: 94102 (San Francisco) - 3 dealers
 */

function extractKohlerDealers() {
  console.log('[Kohler] Starting dealer extraction...');

  // Find the dealer results list (contains phone links)
  const allLists = Array.from(document.querySelectorAll('ul'));
  let dealerList = null;

  for (const list of allLists) {
    const phoneLinks = list.querySelectorAll('a[href^="tel:"]');
    if (phoneLinks.length > 0) {
      dealerList = list;
      break;
    }
  }

  if (!dealerList) {
    console.log('[Kohler] No dealer list found');
    return [];
  }

  // Get all dealer cards (list items)
  const dealerCards = Array.from(dealerList.querySelectorAll('li'));

  console.log(`[Kohler] Found ${dealerCards.length} dealer cards`);

  const dealers = dealerCards.map((card, index) => {
    try {
      // Get all paragraphs in the card
      const paragraphs = Array.from(card.querySelectorAll('p'));

      // First paragraph: Dealer name
      const name = paragraphs[0] ? paragraphs[0].textContent.trim() : '';

      // Second paragraph: Distance (format: "51.5 miles")
      let distance = '';
      let distance_miles = 0;
      if (paragraphs[1]) {
        distance = paragraphs[1].textContent.trim();
        const milesMatch = distance.match(/([\d.]+)\s*miles?/i);
        if (milesMatch) {
          distance_miles = parseFloat(milesMatch[1]);
          distance = `${distance_miles} mi`;
        }
      }

      // Extract tier badges from card text content
      const cardText = card.textContent;
      let tier = 'Certified Installer'; // Default tier
      const certifications = [];

      // Check for tier badges
      if (cardText.includes('Gold Dealer')) {
        tier = 'Gold Dealer';
        certifications.push('Gold Dealer');
      } else if (cardText.includes('Silver Dealer')) {
        tier = 'Silver Dealer';
        certifications.push('Silver Dealer');
      } else if (cardText.includes('Bronze Dealer')) {
        tier = 'Bronze Dealer';
        certifications.push('Bronze Dealer');
      }

      // Check for Titan Certified (premium certification)
      if (cardText.includes('Titan Certified')) {
        certifications.push('Titan Certified');
        if (tier === 'Certified Installer') {
          tier = 'Titan Certified';
        }
      }

      // Default certification if none found
      if (certifications.length === 0) {
        certifications.push('Certified Installer');
      }

      // Extract phone number
      const phoneLink = card.querySelector('a[href^="tel:"]');
      const phone = phoneLink ? phoneLink.textContent.trim() : '';

      // Extract website (look for link with text "Website")
      const websiteLinks = Array.from(card.querySelectorAll('a[href^="http"]'));
      let website = '';
      let domain = '';

      for (const link of websiteLinks) {
        if (link.textContent.trim().toLowerCase() === 'website') {
          website = link.href;
          break;
        }
      }

      // Parse domain from website
      if (website) {
        try {
          const url = new URL(website);
          domain = url.hostname.replace('www.', '');
        } catch (e) {
          console.log(`[Kohler] Card ${index + 1}: Invalid website URL`);
        }
      }

      // Extract address (find paragraph with street address pattern)
      let street = '';
      let city = '';
      let state = '';
      let zip = '';
      let address_full = '';

      // Look for address paragraph (usually contains comma-separated address)
      for (const p of paragraphs) {
        const text = p.textContent.trim();
        // Address pattern: contains street number, comma, and ZIP code
        if (text.match(/\d+\s+[^,]+,\s*[^,]+,\s*[A-Z]{2}\s+\d{5}/)) {
          address_full = text;

          // Parse address components
          // Format: "150 NARDI LANE, Martinez, CA 94553"
          const addressMatch = text.match(/^(.+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})/);

          if (addressMatch) {
            street = addressMatch[1].trim();
            city = addressMatch[2].trim();
            state = addressMatch[3].trim();
            zip = addressMatch[4].trim();
          }
          break;
        }
      }

      // Extract services description (optional)
      // Format: "Sales, Installation, and Service up to 150kW"
      let services = '';
      for (const p of paragraphs) {
        const text = p.textContent.trim();
        if (text.includes('Sales') || text.includes('Installation') || text.includes('Service')) {
          services = text;
          break;
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
        rating: 0,  // Kohler doesn't show ratings
        review_count: 0,
        tier: tier,
        certifications: certifications,
        distance: distance,
        distance_miles: distance_miles,
        services: services,  // Additional field for Kohler
        oem_source: 'Kohler'
      };
    } catch (e) {
      console.error(`[Kohler] Error extracting dealer card ${index + 1}:`, e);
      return null;
    }
  });

  // Filter out null/invalid dealers (must have name and phone)
  const validDealers = dealers.filter(d => d && d.name && d.phone);

  console.log(`[Kohler] Successfully extracted ${validDealers.length} valid dealers`);

  return validDealers;
}

// Execute extraction
extractKohlerDealers();
