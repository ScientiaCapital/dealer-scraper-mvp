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
  // CRITICAL FIX: Exclude footer phone links (1-888-GENERAC, etc.)
  const phoneLinks = Array.from(document.querySelectorAll('a[href^="tel:"]'))
    .filter(link => !link.closest('footer') && !link.closest('[class*="footer"]'));

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

# New York - NY-Sun + Megawatt Block Incentives
ZIP_CODES_NEW_YORK = [
    # Manhattan (wealthiest)
    "10007",  # Lower Manhattan - $512k avg, $253k median (WEALTHIEST IN NY)
    "10024",  # Upper West Side - $155k median
    "10065", "10021", "10028",  # Upper East Side - $150k+ median
    "10013", "10012", "10014",  # Tribeca, SoHo, West Village
    # Westchester (wealthy suburbs)
    "10583", "10580", "10504", "10510",  # Scarsdale, Rye, Armonk, Briarcliff Manor
    # Long Island (Hamptons)
    "11962",  # Sagaponack - $114k median, $5.2M homes (wealthiest in Hamptons)
    "11932",  # Bridgehampton - $113k median, $3.8M homes
    "11968", "11976",  # Southampton, Water Mill
]

# ============================================================================
# MEDIUM PRIORITY SREC STATES - Secondary Markets
# ============================================================================

# Ohio - OH Solar Renewable Energy Credits
ZIP_CODES_OHIO = [
    "45174",  # Terrace Park, Cincinnati - $292k avg, $206k median (WEALTHIEST IN OH)
    "44040",  # Gates Mills, Cleveland - $167k median, $284k avg
    "43021",  # Galena, Columbus - $160k median
    "45208",  # Hyde Park, Cincinnati - $133k median
    "45243",  # Cincinnati suburbs
    "44236",  # Hudson, Akron
    "43065",  # Powell, Columbus
]

# Maryland - MD Solar Renewable Energy Credits
ZIP_CODES_MARYLAND = [
    "20896",  # Garrett Park - #1 for household income in MD
    "21056",  # Gibson Island - #2 for household income in MD
    "20816",  # Bethesda - $1.32M median home value
    "20817",  # Bethesda - #8 nationally for income
    "20815",  # Chevy Chase
    "20850", "20852",  # Rockville
    "21401", "21403",  # Annapolis
]

# District of Columbia - DC Solar Renewable Energy Credits
ZIP_CODES_DC = [
    "20007",  # Georgetown - wealthiest in DC
    "20008",  # Cathedral Heights
    "20016",  # Palisades/Upper Northwest
]

# Delaware - DE Solar Renewable Energy Credits
ZIP_CODES_DELAWARE = [
    "19807",  # Greenville, Wilmington - $247k avg (WEALTHIEST IN DE)
    "19802", "19803",  # Wilmington wealthy suburbs
    "19901", "19958",  # Dover/Rehoboth Beach
]

# New Hampshire - NH Renewable Energy Fund
ZIP_CODES_NEW_HAMPSHIRE = [
    "03854",  # New Castle - $338k avg (WEALTHIEST IN NH)
    "03087",  # Windham
    "03033",  # Brookline
    "03304",  # Bow
    "03110",  # Bedford
]

# Rhode Island - RI Renewable Energy Growth Program
ZIP_CODES_RHODE_ISLAND = [
    "02806",  # Barrington - $210k avg (WEALTHIEST IN RI)
    "02807",  # Block Island - $1.64M median home
    "02835",  # Jamestown - $950k median home
    "02874",  # Saunderstown - $136k median
]

# Connecticut - CT Zonal Solar Renewable Energy Credits
ZIP_CODES_CONNECTICUT = [
    "06870",  # Old Greenwich - $826k avg (WEALTHIEST IN CT)
    "06820",  # Darien - $717k avg
    "06880",  # Westport
    "06878",  # Riverside Greenwich
    "06831",  # Greenwich
    "06840",  # New Canaan
]

# Illinois - IL Adjustable Block Program
ZIP_CODES_ILLINOIS = [
    "60043",  # Kenilworth - $460k avg, $250k median (WEALTHIEST IN IL)
    "60022",  # Glencoe - $416k avg, $250k median
    "60093",  # Winnetka - $381k avg, $231k median
    "60521",  # Hinsdale - $363k avg, $244k median
    "60045",  # Lake Forest - $297k avg, $226k median
    "60091",  # Wilmette - $291k avg, $190k median
    "60558",  # Western Springs - $295k avg, $219k median
    "60601",  # Loop (from previous config)
]

# Combined SREC state ZIPs (for batch scraping) - ALL 15 SREC STATES
ZIP_CODES_SREC_ALL = (
    ZIP_CODES_CALIFORNIA +
    ZIP_CODES_TEXAS +
    ZIP_CODES_PENNSYLVANIA +
    ZIP_CODES_MASSACHUSETTS +
    ZIP_CODES_NEW_JERSEY +
    ZIP_CODES_FLORIDA +
    ZIP_CODES_NEW_YORK +
    ZIP_CODES_OHIO +
    ZIP_CODES_MARYLAND +
    ZIP_CODES_DC +
    ZIP_CODES_DELAWARE +
    ZIP_CODES_NEW_HAMPSHIRE +
    ZIP_CODES_RHODE_ISLAND +
    ZIP_CODES_CONNECTICUT +
    ZIP_CODES_ILLINOIS
)

# ============================================================================
# TOP 20 WEALTHIEST ZIP CODES BY STATE (Researched 2024-2025)
# ============================================================================
# For targeted prospecting in high-value markets
# Data sources: Census median household income, property values, demographics

# ============================================================================
# NATIONWIDE WEALTHY ZIP CODES - ALL 50 STATES
# ============================================================================
# Targeting: $150K-$250K+ median household income across United States
# Coverage: 179 ZIPs across all 50 states (3-5 per state)
# Data Source: 2023-2024 Census ACS, property value data
# Purpose: Target affluent solar/battery/generator buyers ($40K-$80K+ systems)

WEALTHY_ZIPS_NATIONWIDE = {
    # ===== NORTHEAST =====
    "MA": ["02030", "02482", "01776", "02420", "02052"],  # Dover ($421k avg), Wellesley, Sudbury, Lexington, Medfield
    "CT": ["06870", "06820", "06880", "06878", "06831"],  # Old Greenwich ($826k avg), Darien, Westport, Riverside, Greenwich
    "NY": ["10007", "10024", "10065", "10583", "11962"],  # Lower Manhattan ($512k avg), UWS, UES, Scarsdale, Sagaponack
    "NJ": ["07078", "07021", "07620", "07458", "07042"],  # Short Hills ($518k avg), Essex Fells, Alpine, Saddle River, Montclair
    "PA": ["19035", "19087", "19085", "19003", "19010"],  # Gladwyne ($480k avg), Wayne, Villanova, Ardmore, Bryn Mawr
    "RI": ["02806", "02807", "02835"],  # Barrington ($210k avg), Block Island ($1.64M homes), Jamestown
    "NH": ["03854", "03087", "03033"],  # New Castle ($338k avg), Windham, Brookline
    "VT": ["05452", "05753", "05001"],  # Essex Junction, Manchester, Barnard (ski resort areas)
    "ME": ["04005", "04096", "04849"],  # Biddeford Pool, Yarmouth, Lincolnville (coastal wealthy)

    # ===== MID-ATLANTIC =====
    "MD": ["20896", "21056", "20816", "20817", "20815"],  # Garrett Park, Gibson Island, Bethesda (3 ZIPs)
    "DC": ["20007", "20008", "20016"],  # Georgetown, Cathedral Heights, Palisades
    "DE": ["19807", "19802", "19803"],  # Greenville ($247k avg), Wilmington suburbs
    "VA": ["22101", "22066", "20170"],  # McLean, Great Falls, Herndon (DC suburbs)
    "WV": ["25314", "25401", "26301"],  # Charleston Kanawha City, Martinsburg, Morgantown

    # ===== SOUTHEAST =====
    "FL": ["33109", "33480", "33156", "33496", "34102"],  # Fisher Island ($800k avg), Palm Beach, Pinecrest, Boca, Naples
    "GA": ["30327", "30305", "30022"],  # Buckhead Atlanta, Morningside, Alpharetta
    "NC": ["28207", "27514", "28226"],  # Charlotte Myers Park ($184k per capita #7 nationally), Chapel Hill, Ballantyne
    "SC": ["29464", "29455", "29401"],  # Mount Pleasant (Charleston), Kiawah Island, Charleston Downtown
    "TN": ["37215", "37027", "37919"],  # Nashville Green Hills, Brentwood, Knoxville Sequoyah Hills
    "KY": ["40025", "40207", "40502"],  # Glenview ($480k avg, $250k median), Louisville Highlands, Lexington
    "AL": ["35213", "35223", "36117"],  # Birmingham Mountain Brook, Vestavia, Montgomery East
    "MS": ["39120", "39216", "38654"],  # Clinton, Jackson Northeast, Olive Branch (Memphis suburb)
    "LA": ["70605", "70433", "70127"],  # Lake Charles South, Covington, New Orleans Lakeview
    "AR": ["72223", "72227", "72712"],  # Little Rock Chenal, Little Rock West, Bentonville (Walmart execs)

    # ===== MIDWEST =====
    "IL": ["60043", "60022", "60093", "60521", "60045"],  # Kenilworth ($460k avg), Glencoe, Winnetka, Hinsdale, Lake Forest
    "OH": ["45174", "44040", "43021", "45208", "44236"],  # Terrace Park ($292k avg), Gates Mills, Galena, Hyde Park, Hudson
    "MI": ["48067", "48084", "48108"],  # Royal Oak, Troy, Ann Arbor (Detroit metro + university)
    "IN": ["46032", "46240", "46250"],  # Carmel, Indianapolis North, Indianapolis Geist
    "WI": ["53217", "53211", "53097"],  # Milwaukee Shorewood, Milwaukee East Side, Mequon
    "MN": ["55391", "55424", "55436"],  # Wayzata, Edina, Edina South (Twin Cities wealthy suburbs)
    "MO": ["64112", "63105", "63124"],  # Kansas City Plaza, Clayton (St. Louis), Ladue
    "IA": ["52240", "50312", "52001"],  # Iowa City, Des Moines Beaverdale, Dubuque

    # ===== GREAT PLAINS =====
    "KS": ["66208", "66206", "66221"],  # Prairie Village, Leawood, Overland Park (KC suburbs)
    "NE": ["68022", "68130", "68114"],  # Elkhorn, Omaha West, Omaha Midtown
    "SD": ["57106", "57103", "57701"],  # Sioux Falls Southeast, Sioux Falls South, Rapid City
    "ND": ["58501", "58102", "58103"],  # Bismarck, Fargo South, Fargo North
    "OK": ["73013", "74133", "73118"],  # Edmond, Tulsa South, Oklahoma City Nichols Hills

    # ===== SOUTH =====
    "TX": ["76092", "77010", "77401", "77005", "78733"],  # Southlake ($382k avg), Houston, Bellaire, West U, West Lake Hills

    # ===== MOUNTAIN WEST =====
    "CO": ["80220", "80206", "80218", "80209", "80203"],  # Denver: Cherry Creek, Hilltop, Country Club, Washington Park
    "WY": ["82001", "83001", "82070"],  # Cheyenne, Jackson Hole ($250k+ median), Laramie
    "MT": ["59715", "59718", "59047"],  # Bozeman, Big Sky, Livingston (wealthy resort areas)
    "ID": ["83340", "83702", "83706"],  # Sun Valley, Boise North End, Boise Bench
    "UT": ["84108", "84020", "84092"],  # Salt Lake City East, Draper, Sandy (wealthy suburbs)
    "NV": ["89449", "89511", "89119"],  # Incline Village (Lake Tahoe), Reno wealthy, Las Vegas Summerlin
    "AZ": ["85253", "85255", "85260", "85262"],  # Scottsdale (multiple wealthy ZIPs), Paradise Valley
    "NM": ["87501", "87506", "87122"],  # Santa Fe, Santa Fe suburbs, Albuquerque High Desert

    # ===== PACIFIC =====
    "CA": ["94027", "94022", "94024", "94301", "90210"],  # Atherton ($618k avg), Los Altos, Palo Alto, Beverly Hills
    "WA": ["98039", "98004", "98040", "98102"],  # Medina (Gates/Bezos), Bellevue, Mercer Island, Seattle Capitol Hill
    "OR": ["97034", "97221", "97035"],  # Lake Oswego, West Hills Portland, Lake Grove
    "AK": ["99645", "99501", "99516"],  # Girdwood, Anchorage Downtown, Anchorage Hillside
    "HI": ["96821", "96815", "96734"],  # Hawaii Kai, Waikiki/Diamond Head, Kailua (Oahu wealthy)
}

# Flatten nationwide wealthy ZIPs into single list for scraping
ZIP_CODES_NATIONWIDE_WEALTHY = []
for state_zips in WEALTHY_ZIPS_NATIONWIDE.values():
    ZIP_CODES_NATIONWIDE_WEALTHY.extend(state_zips)

# ============================================================================
# MAJOR METRO ZIP CODES - ALL 50 STATES
# ============================================================================
# Coverage: 2-3 major cities per state for comprehensive geographic coverage
# Target: Major metropolitan areas to maximize dealer discovery

MAJOR_METRO_ZIPS = {
    # NORTHEAST
    "MA": ["02101", "01608", "01103", "02138", "02141"],  # Boston, Worcester, Springfield, Cambridge, Somerville
    "CT": ["06103", "06510", "06901", "06604"],  # Hartford, New Haven, Stamford, Bridgeport
    "NY": ["10001", "14201", "14604", "12207", "13202", "11201"],  # NYC, Buffalo, Rochester, Albany, Syracuse, Brooklyn
    "NJ": ["07102", "07302", "07501", "08901", "07001"],  # Newark, Jersey City, Paterson, New Brunswick, Trenton
    "PA": ["19019", "15201", "17101", "18015", "16501"],  # Philadelphia, Pittsburgh, Harrisburg, Bethlehem, Erie
    "RI": ["02901", "02886", "02840"],  # Providence, Warwick, Newport
    "NH": ["03101", "03060", "03301"],  # Manchester, Nashua, Concord
    "VT": ["05401", "05602"],  # Burlington, Montpelier
    "ME": ["04101", "04401", "04330"],  # Portland, Bangor, Augusta

    # MID-ATLANTIC
    "MD": ["21201", "21401", "20850", "21740"],  # Baltimore, Annapolis, Rockville, Hagerstown
    "DC": ["20001", "20020"],  # Washington DC (multiple zones)
    "DE": ["19801", "19901", "19702"],  # Wilmington, Dover, Newark
    "VA": ["23451", "23510", "23219", "22201", "24011"],  # Virginia Beach, Norfolk, Richmond, Arlington, Roanoke
    "WV": ["25301", "25701", "26501"],  # Charleston, Huntington, Morgantown

    # SOUTHEAST
    "FL": ["33101", "33601", "32801", "32202", "33301", "33401"],  # Miami, Tampa, Orlando, Jacksonville, Fort Lauderdale, West Palm Beach
    "GA": ["30301", "31401", "30901", "30060", "31501"],  # Atlanta, Savannah, Augusta, Marietta, Waycross
    "NC": ["28202", "27601", "27401", "28801", "27834"],  # Charlotte, Raleigh, Greensboro, Asheville, Greenville
    "SC": ["29401", "29201", "29601", "29501"],  # Charleston, Columbia, Greenville, Florence
    "TN": ["37201", "38101", "37901", "37601"],  # Nashville, Memphis, Knoxville, Johnson City
    "KY": ["40202", "40502", "42001"],  # Louisville, Lexington, Paducah
    "AL": ["35201", "36601", "36101", "35801"],  # Birmingham, Mobile, Montgomery, Huntsville
    "MS": ["39201", "39501", "39701"],  # Jackson, Gulfport, Meridian
    "LA": ["70112", "70801", "71101", "70501"],  # New Orleans, Baton Rouge, Shreveport, Lafayette
    "AR": ["72201", "72701", "72601"],  # Little Rock, Fayetteville, Harrison

    # MIDWEST
    "IL": ["60601", "62701", "61601", "61801", "60540"],  # Chicago, Springfield, Peoria, Champaign, Naperville
    "OH": ["43201", "44101", "45201", "43601", "44312"],  # Columbus, Cleveland, Cincinnati, Toledo, Akron
    "MI": ["48201", "49501", "48103", "48601", "49001"],  # Detroit, Grand Rapids, Ann Arbor, Saginaw, Kalamazoo
    "IN": ["46201", "46801", "47701", "47901"],  # Indianapolis, Fort Wayne, Evansville, Lafayette
    "WI": ["53201", "53701", "54301", "53081"],  # Milwaukee, Madison, Green Bay, Sheboygan
    "MN": ["55401", "55101", "55801", "55901"],  # Minneapolis, St. Paul, Duluth, Rochester
    "MO": ["63101", "64101", "65801", "63301"],  # St. Louis, Kansas City, Springfield, St. Charles
    "IA": ["50301", "52401", "52801"],  # Des Moines, Cedar Rapids, Davenport

    # GREAT PLAINS
    "KS": ["67201", "66101", "66601", "66502"],  # Wichita, Kansas City, Topeka, Manhattan
    "NE": ["68101", "68501", "69361"],  # Omaha, Lincoln, Scottsbluff
    "SD": ["57101", "57701", "57401"],  # Sioux Falls, Rapid City, Aberdeen
    "ND": ["58102", "58501", "58801"],  # Fargo, Bismarck, Minot
    "OK": ["73101", "74101", "73069"],  # Oklahoma City, Tulsa, Norman

    # SOUTH
    "TX": ["77001", "75201", "78701", "78201", "76101", "79901", "79901", "76541"],  # Houston, Dallas, Austin, San Antonio, Fort Worth, El Paso, Corpus Christi, Killeen

    # MOUNTAIN WEST
    "CO": ["80201", "80901", "80010", "80526", "81501"],  # Denver, Colorado Springs, Aurora, Fort Collins, Grand Junction
    "WY": ["82001", "82601", "82801"],  # Cheyenne, Casper, Sheridan
    "MT": ["59101", "59801", "59601"],  # Billings, Missoula, Helena
    "ID": ["83701", "83401", "83201"],  # Boise, Idaho Falls, Pocatello
    "UT": ["84101", "84601", "84401"],  # Salt Lake City, Provo, Ogden
    "NV": ["89101", "89501", "89002", "89701"],  # Las Vegas, Reno, Henderson, Carson City
    "AZ": ["85001", "85701", "85250", "85201"],  # Phoenix, Tucson, Scottsdale, Mesa
    "NM": ["87101", "87501", "88001"],  # Albuquerque, Santa Fe, Las Cruces

    # PACIFIC
    "CA": ["90001", "94102", "92101", "95814", "95101", "92612", "93101", "94550"],  # LA, SF, San Diego, Sacramento, San Jose, Irvine, Santa Barbara, Livermore
    "WA": ["98101", "99201", "98401", "99301", "98661"],  # Seattle, Spokane, Tacoma, Pasco, Vancouver
    "OR": ["97201", "97401", "97301", "97701"],  # Portland, Eugene, Salem, Bend
    "AK": ["99501", "99701", "99901"],  # Anchorage, Fairbanks, Ketchikan
    "HI": ["96801", "96720", "96753"],  # Honolulu, Hilo, Kihei
}

# Flatten major metro ZIPs into single list
ZIP_CODES_MAJOR_METROS_ALL = []
for state_zips in MAJOR_METRO_ZIPS.values():
    ZIP_CODES_MAJOR_METROS_ALL.extend(state_zips)
