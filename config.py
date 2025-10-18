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

# Browserbase API Configuration
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")

# Browserbase API URLs
BROWSERBASE_API_URL = "https://www.browserbase.com/v1/sessions"
BROWSERBASE_TIMEOUT = 60000  # 60 seconds default timeout

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

# ============================================================================
# COPERNIQ PARTNER PROSPECTING - SREC State ZIP Codes
# ============================================================================
# Focus: States with Solar Renewable Energy Credit programs (sustainable post-ITC)
# Priority: CA, TX, PA, MA, NJ, FL (primary focus)

# California - SGIP + NEM 3.0
ZIP_CODES_CALIFORNIA = [
    # San Francisco Bay Area
    "94102", "94301", "94022", "94024", "94027",  # SF, Palo Alto, Los Altos, Atherton
    # Los Angeles
    "90001", "90210", "90265", "91101",  # LA, Beverly Hills, Malibu, Pasadena
    # San Diego
    "92101", "92037", "92067",  # Downtown SD, La Jolla, Rancho Santa Fe
    # Sacramento
    "95814", "95819",  # Downtown, East Sac
    # Orange County
    "92660", "92625", "92657",  # Newport Beach, Corona del Mar
]

# Texas - Deregulated Market + ERCOT
ZIP_CODES_TEXAS = [
    # Houston
    "77002", "77019", "77024", "77005", "77056",  # Downtown, River Oaks, Memorial, West U, Galleria
    # Dallas
    "75201", "75205", "75225", "75229",  # Downtown, Highland Park, Preston Hollow
    # Austin
    "78701", "78746", "78733", "78730",  # Downtown, Westlake Hills, Barton Creek
    # San Antonio
    "78201", "78209",  # Downtown, Alamo Heights
    # Fort Worth
    "76102", "76107",  # Downtown, Rivercrest
]

# Pennsylvania - PA SREC Program
ZIP_CODES_PENNSYLVANIA = [
    # Philadelphia
    "19102", "19103", "19146",  # Center City
    # Philadelphia suburbs (wealthy)
    "19035", "19087", "19085", "19003", "19010",  # Gladwyne, Wayne, Villanova, Ardmore, Bryn Mawr
    # Pittsburgh
    "15222", "15215", "15238",  # Downtown, Fox Chapel, Sewickley
]

# Massachusetts - SREC II + SMART Program
ZIP_CODES_MASSACHUSETTS = [
    # Boston
    "02108", "02116", "02199",  # Downtown, Back Bay
    # Boston suburbs (wealthy)
    "02467", "02481", "02492", "02445", "02482",  # Chestnut Hill, Wellesley, Needham, Brookline
    # Cambridge
    "02138", "02139", "02142",  # Cambridge
]

# New Jersey - NJ TREC Program
ZIP_CODES_NEW_JERSEY = [
    # Northern NJ (wealthy)
    "07078", "07920", "07039", "07931",  # Short Hills, Basking Ridge, Livingston, Far Hills
    # Central NJ
    "08540", "08648",  # Princeton, Lawrence
    # Shore
    "07733", "07740", "07726",  # Holmdel, Long Branch, Englishtown
]

# Florida - Net Metering + Property Tax Exemptions
ZIP_CODES_FLORIDA = [
    # Miami
    "33109", "33139", "33158", "33156",  # Fisher Island, Miami Beach, Pinecrest, Palmetto Bay
    # Palm Beach
    "33480", "33455",  # Palm Beach, Hobe Sound
    # Naples
    "34102", "34103",  # Naples, Old Naples
    # Tampa
    "33606", "33629",  # South Tampa, Bayshore
    # Orlando
    "32801", "32819",  # Downtown, Dr. Phillips
]

# Combined SREC state ZIPs (for batch scraping)
ZIP_CODES_SREC_ALL = (
    ZIP_CODES_CALIFORNIA +
    ZIP_CODES_TEXAS +
    ZIP_CODES_PENNSYLVANIA +
    ZIP_CODES_MASSACHUSETTS +
    ZIP_CODES_NEW_JERSEY +
    ZIP_CODES_FLORIDA
)
