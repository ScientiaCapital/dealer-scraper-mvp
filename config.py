"""
Configuration for Generac Dealer Scraper
Includes selectors, extraction script, and ZIP code lists
"""

# Generac Dealer Locator URL
DEALER_LOCATOR_URL = "https://www.generac.com/dealer-locator/"

# RunPod Serverless API Configuration
import os

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "")

# Construct RunPod API URL from endpoint ID
if RUNPOD_ENDPOINT_ID:
    RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
else:
    RUNPOD_API_URL = ""

# CSS Selectors
SELECTORS = {
    "cookie_accept": "button:has-text('Accept Cookies')",
    "zip_input": "textbox[name*='zip' i]",
    "search_button": "button:has-text('Search')",
    "phone_links": 'a[href^="tel:"]',
    "distance_class": ".ms-auto.text-end.text-nowrap",
}

# Extraction JavaScript (from extraction.js)
EXTRACTION_SCRIPT = """
() => {
  const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'));

  const dealers = phoneLinks.map(phoneLink => {
    // Find the dealer card container
    let container = phoneLink;
    for (let i = 0; i < 10; i++) {
      container = container.parentElement;
      if (!container) break;
      const hasDistance = container.querySelector('.ms-auto.text-end.text-nowrap');
      if (hasDistance) break;
    }

    if (!container) return null;

    // Extract dealer name (ALL CAPS text)
    const allDivs = Array.from(container.querySelectorAll('div'));
    let dealerName = '';
    for (const div of allDivs) {
      const text = div.textContent.trim();
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
    const ratingMatch = fullText.match(/(\\d+\\.\\d+)\\s*\\((\\d+)\\)/);
    const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
    const reviewCount = ratingMatch ? parseInt(ratingMatch[2]) : 0;

    // Extract dealer tier
    const isPremier = fullText.includes('Premier Dealers demonstrate');
    const isElitePlus = fullText.includes('Elite Plus');
    const isElite = fullText.includes('Elite Dealers offer');

    let tier = 'Standard';
    if (isPremier) tier = 'Premier';
    else if (isElitePlus) tier = 'Elite Plus';
    else if (isElite) tier = 'Elite';

    const isPowerProPremier = fullText.includes('PowerPro') || fullText.includes('Premier');

    // Extract street address
    const streetMatch = beforePhone.match(/(\\d+\\s+[nsew]?\\d*\\s*[^\\n,]*(?:st|street|dr|drive|rd|road|ave|avenue|ct|court|blvd|ln|way|pl)\\.?)/i);
    let street = streetMatch ? streetMatch[1].trim() : '';
    street = street.replace(/^.*?out of \\d+ stars\\.\\s*\\d*\\s*reviews?\\s*/i, '');
    street = street.replace(/^\\d+\\.\\d+\\s*\\(\\d+\\)/, '');
    street = street.replace(/^\\d+\\.\\d+\\s*mi/, '');

    // Extract city, state, ZIP
    const afterStreet = street ? beforePhone.substring(beforePhone.lastIndexOf(street) + street.length) : beforePhone;
    const cityStateZip = afterStreet.match(/([a-z\\s]+),?\\s*([A-Z]{2})\\s+(\\d{5})/i);

    const city = cityStateZip ? cityStateZip[1].trim() : '';
    const state = cityStateZip ? cityStateZip[2] : '';
    const zip = cityStateZip ? cityStateZip[3] : '';

    // Extract website and domain
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

    // Extract distance
    const distanceEl = container.querySelector('.ms-auto.text-end.text-nowrap');
    const distance = distanceEl?.textContent?.trim() || '';
    const distanceMiles = parseFloat(distance) || 0;

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
      distance_miles: distanceMiles
    };
  });

  return dealers.filter(d => d && d.name);
}
"""

# Wait times (seconds)
WAIT_AFTER_SEARCH = 3
WAIT_BETWEEN_ZIPS = 3

# ZIP Code Lists for Testing

# Test set - small sample for validation
ZIP_CODES_TEST = [
    "53202",  # Milwaukee, WI - 59 dealers (tested)
    "60601",  # Chicago, IL
    "55401",  # Minneapolis, MN
]

# Milwaukee Metro Area
ZIP_CODES_MILWAUKEE = [
    "53202", "53203", "53204", "53205", "53206",
    "53207", "53208", "53209", "53210", "53211",
    "53212", "53213", "53214", "53215", "53216",
]

# Major US Cities - High Coverage
ZIP_CODES_MAJOR_CITIES = [
    "10001",  # New York, NY
    "90001",  # Los Angeles, CA
    "60601",  # Chicago, IL
    "77001",  # Houston, TX
    "85001",  # Phoenix, AZ
    "19101",  # Philadelphia, PA
    "78201",  # San Antonio, TX
    "92101",  # San Diego, CA
    "75201",  # Dallas, TX
    "95101",  # San Jose, CA
]

# Regional Centers - Midwest Focus
ZIP_CODES_MIDWEST = [
    "53202",  # Milwaukee, WI
    "55401",  # Minneapolis, MN
    "50301",  # Des Moines, IA
    "43201",  # Columbus, OH
    "46201",  # Indianapolis, IN
    "48201",  # Detroit, MI
    "63101",  # St. Louis, MO
    "64101",  # Kansas City, MO
]
