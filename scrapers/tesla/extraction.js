/**
 * Tesla Powerwall Certified Installer Extraction Script
 *
 * URL: https://www.tesla.com/support/certified-installers-powerwall
 *
 * DATA PATTERN:
 * Tesla concatenates all dealer info without spaces:
 * "Premier InstallerLuminalt Energy Corporation4156414000https://luminalt.com/powerwall@luminalt.com"
 *
 * EXTRACTION STRATEGY:
 * 1. Find all <div> elements containing exactly 1 "Premier Installer" text
 * 2. Extract phone (10 digits) as anchor point
 * 3. Extract email (standard pattern with @)
 * 4. Extract website (https:// OR www.domain patterns)
 * 5. Extract name (everything before phone, cleaned)
 * 6. Deduplicate by phone number
 *
 * TESTED: 94102 (San Francisco) - 14 unique dealers extracted
 */

function extractTeslaDealers() {
  console.log('[Tesla] Starting dealer extraction...');

  // Find all <div> elements that contain exactly one "Premier Installer" badge
  const allDivs = Array.from(document.querySelectorAll('div'));
  const dealerCards = allDivs.filter(div => {
    const text = div.textContent;
    const badgeCount = (text.match(/Premier Installer/g) || []).length;

    // Must have exactly 1 badge and reasonable length
    return badgeCount === 1 && text.length > 20 && text.length < 500;
  });

  console.log(`[Tesla] Found ${dealerCards.length} potential dealer cards`);

  const dealers = [];
  const seenPhones = new Set();

  dealerCards.forEach((card, index) => {
    let text = card.textContent.trim();

    // Remove "Premier Installer" badge text
    text = text.replace(/Premier Installer/g, '').trim();

    // Extract phone number (10 digits) - ANCHOR POINT
    const phoneMatch = text.match(/(\d{10})/);
    if (!phoneMatch) {
      console.log(`[Tesla] Card ${index + 1}: No phone found, skipping`);
      return;
    }
    const phone = phoneMatch[1];

    // Deduplicate by phone
    if (seenPhones.has(phone)) {
      console.log(`[Tesla] Card ${index + 1}: Duplicate phone ${phone}, skipping`);
      return;
    }
    seenPhones.add(phone);

    // Extract email (standard pattern with @)
    const emailMatch = text.match(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/);
    const email = emailMatch ? emailMatch[1] : '';

    // Extract website - handle both https:// and www. patterns
    let website = '';

    if (email) {
      const emailPrefix = email.split('@')[0];

      // Try Pattern 1: https:// URL before email prefix
      const httpsPattern = new RegExp('(https?://[^@]+?)' + emailPrefix + '@');
      const httpsMatch = text.match(httpsPattern);

      if (httpsMatch) {
        website = httpsMatch[1];
      } else {
        // Try Pattern 2: www.domain.com before email prefix
        const wwwPattern = new RegExp('(www\\.[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})' + emailPrefix + '@');
        const wwwMatch = text.match(wwwPattern);
        if (wwwMatch) {
          website = 'https://' + wwwMatch[1];
        } else {
          // Fallback: Extract domain from email
          const emailDomain = email.split('@')[1];
          website = 'https://' + emailDomain;
        }
      }
    } else {
      // No email, try to find any https:// URL before phone
      const match = text.match(/(https?:\/\/[^\d\s]+?)(?=\d{10}|$)/);
      if (match) website = match[1];
    }

    // Clean up website
    website = website.replace(/\/$/, '').trim();

    // Extract name (everything before phone number)
    let name = text.substring(0, text.indexOf(phone)).trim();

    // Remove website and email from name
    if (website) {
      name = name.replace(website, '').trim();
      name = name.replace(website.replace('https://', ''), '').trim();
    }
    if (email) name = name.replace(email, '').trim();

    // Clean up any remaining URLs or domains
    name = name.replace(/https?:\/\/[^\s]+/g, '').trim();
    name = name.replace(/www\.[^\s]+/g, '').trim();

    // Only add if we have at least name and phone
    if (name && phone) {
      dealers.push({
        name: name,
        phone: phone,
        website: website,
        email: email,
        tier: 'Premier Installer',  // All Tesla installers are Premier
        oem_source: 'Tesla'
      });
    }
  });

  console.log(`[Tesla] Successfully extracted ${dealers.length} unique dealers`);

  return dealers;
}

// Execute extraction
extractTeslaDealers();
