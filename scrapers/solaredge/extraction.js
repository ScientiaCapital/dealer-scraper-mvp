/**
 * SolarEdge Installer Extraction Script
 *
 * URL: https://www.solaredge.com/us/find-installer
 *
 * ARCHITECTURE:
 * SolarEdge uses a two-step Drupal AJAX pattern:
 * 1. Search form requires Google Maps autocomplete to populate lat/long
 * 2. AJAX POST to /us/find-an-installer?ajax_form=1 returns installer cards
 * 3. Each installer card must be clicked to reveal phone/website in detail panel
 * 4. "Back to Installers List" button returns to list view
 *
 * DATA PATTERN:
 * - List view: Shows name, address, services (no phone/website)
 * - Detail view: Shows phone (tel: link), website, full description
 *
 * EXTRACTION STRATEGY:
 * 1. Find all installer cards in results list
 * 2. For each card: click it, wait for detail panel, extract full data, go back
 * 3. Handle async operations with Promises
 * 4. Return array of complete dealer objects
 *
 * TESTED: San Francisco, CA - 5 installers extracted successfully
 */

async function extractSolarEdgeDealers() {
  console.log('[SolarEdge] Starting dealer extraction...');

  // Wait briefly for AJAX results to fully render
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Find all installer cards (they have a specific class pattern)
  const installerCards = Array.from(document.querySelectorAll('.installer-item, [class*="installer"]'))
    .filter(card => {
      // Filter to actual installer cards (not empty divs)
      const text = card.textContent;
      return text && text.length > 50 && !text.includes('Back to Installers List');
    });

  console.log(`[SolarEdge] Found ${installerCards.length} installer cards`);

  if (installerCards.length === 0) {
    // Fallback: try to find any clickable elements with installer names
    const allClickable = Array.from(document.querySelectorAll('[role], [onclick], .clickable, [cursor="pointer"]'));
    console.log(`[SolarEdge] No installer cards found. Trying fallback with ${allClickable.length} clickable elements`);
  }

  const dealers = [];

  // Extract data from each installer card
  for (let i = 0; i < installerCards.length; i++) {
    const card = installerCards[i];

    try {
      console.log(`[SolarEdge] Processing installer ${i + 1}/${installerCards.length}...`);

      // Click the card to reveal details
      card.click();

      // Wait for detail panel to load
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Extract data from detail panel (left side panel)
      const detailPanel = document.querySelector('[class*="installer-detail"], .installer-info, [class*="detail-panel"]');

      if (!detailPanel) {
        console.log(`[SolarEdge] No detail panel found for installer ${i + 1}, skipping`);
        continue;
      }

      // Extract name
      const nameEl = detailPanel.querySelector('h2, h3, h4, [class*="name"], [class*="title"]');
      const name = nameEl ? nameEl.textContent.trim() : '';

      // Extract phone from tel: link
      const phoneLink = detailPanel.querySelector('a[href^="tel:"]');
      const phone = phoneLink ? phoneLink.textContent.trim() : '';

      // Extract website
      const websiteLink = Array.from(detailPanel.querySelectorAll('a[href^="http"]'))
        .find(link => !link.href.includes('google') && !link.href.includes('facebook') && !link.href.includes('marketing.solaredge'));
      const website = websiteLink ? websiteLink.href : '';
      const domain = website ? new URL(website).hostname.replace('www.', '') : '';

      // Extract address
      const addressEl = detailPanel.querySelector('[class*="address"], img[alt="address"] + *');
      let street = '';
      let city = '';
      let state = '';
      let zip = '';

      if (addressEl) {
        const addressText = addressEl.textContent.trim();
        // Parse address: "1035 Folger Ave, Berkeley, CA 94510"
        const parts = addressText.split(',');
        if (parts.length >= 2) {
          street = parts[0].trim();
          const cityStateParts = parts[1].trim().split(/\s+/);
          if (cityStateParts.length >= 2) {
            city = cityStateParts.slice(0, -2).join(' ');
            state = cityStateParts[cityStateParts.length - 2];
            zip = cityStateParts[cityStateParts.length - 1];
          }
        }
      }

      // Extract services (Maintenance, Solar, Storage)
      const servicesList = detailPanel.querySelectorAll('li[class*="service"], [class*="services"] li');
      const services = Array.from(servicesList).map(li => li.textContent.trim());

      const hasSolar = services.some(s => s.toLowerCase().includes('solar'));
      const hasStorage = services.some(s => s.toLowerCase().includes('storage'));
      const hasMaintenance = services.some(s => s.toLowerCase().includes('maintenance'));

      // Extract experience/description
      const descEl = detailPanel.querySelector('p[class*="description"], p[class*="bio"]');
      const description = descEl ? descEl.textContent.trim() : '';

      // Extract "Installing since" year
      const experienceMatch = detailPanel.textContent.match(/Installing.*since\s+(\d{4})/i);
      const yearStarted = experienceMatch ? parseInt(experienceMatch[1]) : null;

      // Build dealer object
      const dealer = {
        name: name,
        phone: phone,
        website: website,
        domain: domain,
        street: street,
        city: city,
        state: state,
        zip: zip,
        address_full: street && city ? `${street}, ${city}, ${state} ${zip}` : '',
        rating: 0, // SolarEdge doesn't show ratings
        review_count: 0,
        tier: '', // No tier system visible
        certifications: services,
        has_solar: hasSolar,
        has_storage: hasStorage,
        has_maintenance: hasMaintenance,
        description: description.substring(0, 500), // Limit description length
        year_started: yearStarted,
        oem_source: 'SolarEdge'
      };

      dealers.push(dealer);

      // Click back to list
      const backButton = document.querySelector('[class*="back"], button:has-text("Back to Installers List")');
      if (backButton) {
        backButton.click();
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

    } catch (error) {
      console.log(`[SolarEdge] Error processing installer ${i + 1}: ${error.message}`);
    }
  }

  // Deduplicate by phone
  const uniqueDealers = dealers.filter((dealer, index, self) =>
    dealer.phone && index === self.findIndex(d => d.phone === dealer.phone)
  );

  console.log(`[SolarEdge] Successfully extracted ${uniqueDealers.length} unique dealers`);

  return uniqueDealers;
}

// Execute extraction
extractSolarEdgeDealers();
