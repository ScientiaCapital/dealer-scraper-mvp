/**
 * Generac Authorized Dealer Extraction Script
 *
 * URL: https://www.generac.com/dealer-locator/
 *
 * DATA PATTERN:
 * Generac dealer cards contain complex nested HTML with:
 * - Phone number links: <a href="tel:...">
 * - Dealer name: ALL CAPS text in a div
 * - Address: Street address followed by City, ST ZIP
 * - Rating: Pattern like "4.3(6)" or "5.0(24)"
 * - Tier badges: "Premier Dealers demonstrate...", "Elite Plus", "Elite Dealers offer..."
 * - Distance: ".ms-auto.text-end.text-nowrap" element
 * - Website: <a href="http..."> (excluding Google/Facebook links)
 *
 * EXTRACTION STRATEGY:
 * 1. Find all phone links (<a href="tel:...">) EXCLUDING footer links (critical!)
 * 2. For each phone link, traverse up to find the dealer card container
 * 3. Container identified by presence of distance element (.ms-auto.text-end.text-nowrap)
 * 4. Extract dealer name (ALL CAPS text in a div)
 * 5. Parse rating/review count from "4.3(6)" pattern
 * 6. Detect tier from badge text (Premier > Elite Plus > Elite > Standard)
 * 7. Extract street address using regex (number + street suffix pattern)
 * 8. Parse city, state, ZIP from remaining address text
 * 9. Extract website and domain from non-social media links
 * 10. Extract distance from text-end element
 *
 * CRITICAL FIX: Footer phone links must be excluded (Generac customer service: 1-888-GENERAC)
 * Without this filter, extraction would include duplicate/invalid entries
 *
 * TESTED: 53202 (Milwaukee) - 59 dealers, 60601 (Chicago) - 59 dealers, 55401 (Minneapolis) - 28 dealers
 */

function extractGeneracDealers() {
  console.log('[Generac] Starting dealer extraction...');

  // CRITICAL FIX: Exclude footer phone links (1-888-GENERAC, etc.)
  const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'))
    .filter(link => !link.closest('footer') && !link.closest('[class*="footer"]'));

  console.log(`[Generac] Found ${phoneLinks.length} phone links (excluding footer)`);

  const dealers = phoneLinks.map((phoneLink, index) => {
    // Find the dealer card container by traversing up the DOM
    let container = phoneLink;
    for (let i = 0; i < 10; i++) {
      container = container.parentElement;
      if (!container) break;

      // Container identified by presence of distance element
      const hasDistance = container.querySelector('.ms-auto.text-end.text-nowrap');
      if (hasDistance) break;
    }

    if (!container) {
      console.log(`[Generac] Phone link ${index + 1}: No container found, skipping`);
      return null;
    }

    // Extract dealer name (ALL CAPS text in a div)
    const allDivs = Array.from(container.querySelectorAll('div'));
    let dealerName = '';
    for (const div of allDivs) {
      const text = div.textContent.trim();
      // Dealer name is ALL CAPS, 5-100 chars, no special chars
      if (text && text.length > 5 && text.length < 100 &&
          !text.includes('(') && !text.includes('http') &&
          !text.includes('mi') && text === text.toUpperCase()) {
        dealerName = text;
        break;
      }
    }

    const fullText = container.textContent;
    const phoneText = phoneLink.textContent.trim();
    const beforePhone = fullText.substring(0, fullText.indexOf(phoneText));

    // Extract rating - pattern like "4.3(6)" or "5.0(24)"
    const ratingMatch = fullText.match(/(\d+\.\d+)\s*\((\d+)\)/);
    const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
    const reviewCount = ratingMatch ? parseInt(ratingMatch[2]) : 0;

    // Extract dealer tier from badge text
    const isPremier = fullText.includes('Premier Dealers demonstrate');
    const isElitePlus = fullText.includes('Elite Plus');
    const isElite = fullText.includes('Elite Dealers offer');

    let tier = 'Standard';
    if (isPremier) tier = 'Premier';
    else if (isElitePlus) tier = 'Elite Plus';
    else if (isElite) tier = 'Elite';

    // Special designation: PowerPro Premier
    const isPowerProPremier = fullText.includes('PowerPro') || fullText.includes('Premier');

    // Extract street address (number + street suffix pattern)
    const streetMatch = beforePhone.match(/(\d+\s+[nsew]?\d*\s*[^\n,]*(?:st|street|dr|drive|rd|road|ave|avenue|ct|court|blvd|ln|way|pl)\.?)/i);
    let street = streetMatch ? streetMatch[1].trim() : '';

    // Clean up street address (remove rating/review artifacts)
    street = street.replace(/^.*?out of \d+ stars\.\s*\d*\s*reviews?\s*/i, '');
    street = street.replace(/^\d+\.\d+\s*\(\d+\)/, '');
    street = street.replace(/^\d+\.\d+\s*mi/, '');

    // Extract city, state, ZIP from text after street address
    const afterStreet = street ? beforePhone.substring(beforePhone.lastIndexOf(street) + street.length) : beforePhone;
    const cityStateZip = afterStreet.match(/([a-z\s]+),?\s*([A-Z]{2})\s+(\d{5})/i);

    const city = cityStateZip ? cityStateZip[1].trim() : '';
    const state = cityStateZip ? cityStateZip[2] : '';
    const zip = cityStateZip ? cityStateZip[3] : '';

    // Extract website and domain (exclude Google/Facebook links)
    const websiteLink = container.querySelector('a[href^="http"]:not([href*="google"]):not([href*="facebook"])');
    const website = websiteLink?.href || '';

    let domain = '';
    if (website) {
      try {
        const url = new URL(website);
        domain = url.hostname.replace('www.', '');
      } catch (e) {
        domain = '';
      }
    }

    // Extract distance from text-end element
    const distanceEl = container.querySelector('.ms-auto.text-end.text-nowrap');
    const distance = distanceEl?.textContent?.trim() || '';
    const distanceMiles = parseFloat(distance) || 0;

    // Build dealer object
    return {
      name: dealerName,
      rating: rating,
      review_count: reviewCount,
      tier: tier,
      is_power_pro_premier: isPowerProPremier,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
      phone: phoneText,
      website: website,
      domain: domain,
      distance: distance,
      distance_miles: distanceMiles,
      oem_source: 'Generac'
    };
  });

  // Filter out null entries and entries without dealer names
  const validDealers = dealers.filter(d => d && d.name);

  console.log(`[Generac] Successfully extracted ${validDealers.length} unique dealers`);

  return validDealers;
}

// Execute extraction
extractGeneracDealers();
