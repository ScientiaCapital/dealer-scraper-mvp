/**
 * Enphase Certified Installer Extraction Script
 *
 * URL: https://enphase.com/installer-locator
 *
 * DATA PATTERN:
 * Enphase uses clean semantic HTML with proper CSS classes and data attributes:
 * - Each installer in: <div class="installer-info-box" data-installer-id="...">
 * - Company name: <h3 class="installer-info-box__title">Your Energy Solutions</h3>
 * - Address: <p class="installer-info-box__description">290 Rickenbacker CircleLivermore, CA 94551</p>
 * - Rating: data-google-reviews-rating="4.7" attribute
 * - Tier: <img alt="platinum"> or <img alt="gold"> or <img alt="silver">
 * - Capabilities: Text content includes "Solar", "Storage", "Ops & Maintenance", etc.
 *
 * EXTRACTION STRATEGY:
 * 1. Find all <div> elements with class "installer-info-box" or data-installer-id attribute
 * 2. Extract company name from .installer-info-box__title
 * 3. Parse concatenated address: "Street AddressCityName, STATE ZIP" → split into components
 * 4. Extract rating from data-google-reviews-rating attribute
 * 5. Extract tier from img[alt] value (platinum, gold, silver)
 * 6. Detect capabilities from text content (Solar, Storage, O&M, EV Charger, Commercial)
 * 7. Deduplicate by company name
 *
 * ADDRESS PARSING CHALLENGE:
 * Enphase concatenates street + city without space: "290 Rickenbacker CircleLivermore, CA 94551"
 * Solution: Regex pattern captures street (before capitalized city) and city (capitalized word before comma)
 *
 * TESTED: 94102 (San Francisco) - 27 unique dealers extracted
 */

function extractEnphaseDealers() {
  console.log('[Enphase] Starting dealer extraction...');

  // Find all installer boxes using multiple selectors for robustness
  const installerBoxes = Array.from(
    document.querySelectorAll('.installer-info-box, div[data-installer-id]')
  );
  console.log(`[Enphase] Found ${installerBoxes.length} installer boxes`);

  const dealers = [];
  const seenNames = new Set();

  installerBoxes.forEach((box, index) => {
    // Extract company name
    const nameEl = box.querySelector('.installer-info-box__title');
    const name = nameEl ? nameEl.textContent.trim() : '';

    if (!name) {
      console.log(`[Enphase] Box ${index + 1}: No company name found, skipping`);
      return;
    }

    // Deduplicate by name
    if (seenNames.has(name)) {
      console.log(`[Enphase] Box ${index + 1}: Duplicate name "${name}", skipping`);
      return;
    }
    seenNames.add(name);

    // Extract address (concatenated format)
    const addressEl = box.querySelector('.installer-info-box__description');
    let addressText = addressEl ? addressEl.textContent.trim() : '';

    // Parse concatenated address: "290 Rickenbacker CircleLivermore, CA 94551"
    // Pattern: (street)(CapitalizedCity), (ST) (ZIP)
    let street = '', city = '', state = '', zip = '';
    const addressMatch = addressText.match(/^(.+?)([A-Z][a-z\s]+),\s*([A-Z]{2})\s+(\d{5})/);

    if (addressMatch) {
      street = addressMatch[1].trim();
      city = addressMatch[2].trim();
      state = addressMatch[3];
      zip = addressMatch[4];
    } else {
      // Fallback: Try to parse comma-separated format
      const parts = addressText.split(',').map(s => s.trim());
      if (parts.length >= 2) {
        street = parts[0];
        const cityStateZip = parts[1].match(/([A-Za-z\s]+)\s+([A-Z]{2})\s+(\d{5})/);
        if (cityStateZip) {
          city = cityStateZip[1].trim();
          state = cityStateZip[2];
          zip = cityStateZip[3];
        }
      }
    }

    // Extract rating from data attribute
    const rating = parseFloat(box.getAttribute('data-google-reviews-rating')) || 0.0;

    // Extract tier from img alt attribute
    const tierImg = box.querySelector('img[alt]');
    let tier = '';
    if (tierImg) {
      const tierAlt = tierImg.alt.toLowerCase();
      // Capitalize first letter: "platinum" → "Platinum"
      tier = tierAlt.charAt(0).toUpperCase() + tierAlt.slice(1);
    }

    // Extract capabilities from text content
    const fullText = box.textContent;
    const capabilities = [];

    if (fullText.includes('Solar')) capabilities.push('Solar');
    if (fullText.includes('Storage')) capabilities.push('Storage');
    if (fullText.includes('Ops & Maintenance')) capabilities.push('O&M');
    if (fullText.includes('EV Charger')) capabilities.push('EV Charger');
    if (fullText.includes('Commercial')) capabilities.push('Commercial');

    // Build dealer object
    dealers.push({
      name: name,
      street: street,
      city: city,
      state: state,
      zip: zip,
      address_full: addressText,
      tier: tier,
      rating: rating,
      capabilities: capabilities,
      oem_source: 'Enphase'
    });
  });

  console.log(`[Enphase] Successfully extracted ${dealers.length} unique dealers`);

  return dealers;
}

// Execute extraction
extractEnphaseDealers();
