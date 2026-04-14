const { chromium } = require('playwright');

const DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db';
const BASE_URL = 'https://www.lasteat.com';
const FONTE = 'lasteat';

async function saveProduct(product) {
  const sqlite3 = require('sqlite3').verbose();
  const db = new sqlite3.Database(DB_PATH);
  return new Promise((resolve, reject) => {
    const sql = `INSERT OR IGNORE INTO products 
      (nome, azienda, categoria, ingredienti, dosaggio, modo_duso, indicazioni, url, fonte)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`;
    db.run(sql, [
      product.nome || '',
      product.azienda || '',
      product.categoria || '',
      product.ingredienti || '',
      product.dosaggio || '',
      product.modo_duso || '',
      product.indicazioni || '',
      product.url || '',
      FONTE
    ], function(err) {
      db.close();
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}

async function checkExists(url) {
  const sqlite3 = require('sqlite3').verbose();
  const db = new sqlite3.Database(DB_PATH);
  return new Promise((resolve) => {
    db.get('SELECT id FROM products WHERE url = ? AND fonte = ?', [url, FONTE], (err, row) => {
      db.close();
      resolve(!!row);
    });
  });
}

async function extractPageData(page) {
  const data = {};
  
  // Try to get page content via multiple methods
  try {
    // Get all text content
    const content = await page.content();
    
    // Extract product name
    try {
      const nameEl = await page.locator('h1').first();
      data.nome = await nameEl.textContent({ timeout: 3000 }).catch(() => '');
    } catch { data.nome = ''; }
    
    // Extract company/seller
    try {
      const sellerEl = await page.locator('[class*="seller"], [class*="azienda"], [class*="brand"], [class*="ditta"]').first();
      data.azienda = await sellerEl.textContent({ timeout: 2000 }).catch(() => '');
    } catch { data.azienda = ''; }
    
    // Extract category
    try {
      const breadcrumb = await page.locator('[class*="breadcrumb"], nav[class*="nav"] a').allTextContents({ timeout: 2000 }).catch(() => []);
      data.categoria = breadcrumb.filter(t => t.trim()).join(' > ').substring(0, 500);
    } catch { data.categoria = ''; }
    
    // Extract ingredients
    try {
      const ingrEl = await page.locator('[class*="ingredient"], [class*="composizion"]').first();
      data.ingredienti = await ingrEl.textContent({ timeout: 2000 }).catch(() => '');
    } catch { data.ingredienti = ''; }
    
    // Extract dosage / nutritional table
    try {
      const dosEl = await page.locator('[class*="dosaggio"], [class*="nutrizion"], [class*="apporto"], table[class*="nutr"]').first();
      data.dosaggio = await dosEl.textContent({ timeout: 2000 }).catch(() => '');
    } catch { data.dosaggio = ''; }
    
    // Also look for specific nutritional table
    if (!data.dosaggio || data.dosaggio.length < 10) {
      try {
        const tables = await page.locator('table').all();
        for (const table of tables) {
          const txt = await table.textContent();
          if (txt.match(/\d+\s*(mg|g|kcal|kj|µg)/i)) {
            data.dosaggio = txt;
            break;
          }
        }
      } catch {}
    }
    
    // Extract usage instructions
    try {
      const usageEl = await page.locator('[class*="modo"], [class*="usage"], [class*="posologia"]').first();
      data.modo_duso = await usageEl.textContent({ timeout: 2000 }).catch(() => '');
    } catch { data.modo_duso = ''; }
    
    // Extract indications
    try {
      const indEl = await page.locator('[class*="indicazion"], [class*="descr"], [class*="caratter"]').first();
      data.indicazioni = await indEl.textContent({ timeout: 2000 }).catch(() => '');
    } catch { data.indicazioni = ''; }
    
    // Clean up
    data.nome = (data.nome || '').trim().substring(0, 500);
    data.azienda = (data.azienda || '').trim().substring(0, 300);
    data.categoria = (data.categoria || '').trim().substring(0, 500);
    data.ingredienti = (data.ingredienti || '').trim().substring(0, 5000);
    data.dosaggio = (data.dosaggio || '').trim().substring(0, 5000);
    data.modo_duso = (data.modo_duso || '').trim().substring(0, 2000);
    data.indicazioni = (data.indicazioni || '').trim().substring(0, 3000);
    
  } catch (e) {
    console.error('Error extracting page data:', e.message);
  }
  
  return data;
}

function hasNutritionalData(dosaggio, ingredienti) {
  const text = (dosaggio + ' ' + ingredienti).toLowerCase();
  return /\d+\s*(mg|g|kcal|kj|mcg|µg|%|\bvnr\b)/i.test(text);
}

async function main() {
  console.log('🚀 Starting Lasteat crawler...');
  
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();
  
  let totalProducts = 0;
  let savedProducts = 0;
  let skippedProducts = 0;
  
  try {
    // Step 1: Navigate to the site
    console.log('\n📍 Navigating to www.lasteat.com...');
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);
    
    console.log('Page title:', await page.title());
    
    // Step 2: Find integratori section - look for menu links
    console.log('\n🔍 Looking for integratori section...');
    
    let productLinks = [];
    
    // Try to find integratori link in navigation
    const navSelectors = [
      'a[href*="integrator"]',
      'a[href*="Integrator"]',
      'nav a',
      '[class*="menu"] a',
      '[class*="nav"] a',
    ];
    
    let found = false;
    for (const sel of navSelectors) {
      try {
        const links = await page.locator(sel).all();
        for (const link of links) {
          const href = await link.getAttribute('href');
          const text = await link.textContent();
          console.log(`  Nav link: "${text.trim()}" -> ${href}`);
          if (href && (href.includes('integrator') || text.toLowerCase().includes('integrator'))) {
            console.log('✅ Found integratori link:', href);
            await link.click({ timeout: 5000 });
            found = true;
            await page.waitForTimeout(2000);
            break;
          }
        }
        if (found) break;
      } catch {}
    }
    
    if (!found) {
      // Try direct URL patterns for Lasteat integratori
      const possiblePaths = [
        '/integratori',
        '/integratori-alimentari',
        '/category/integratori',
        '/prodotti/integratori',
        '/c/integratori',
        '/collections/integratori',
      ];
      
      for (const path of possiblePaths) {
        try {
          console.log(`Trying: ${BASE_URL}${path}`);
          await page.goto(BASE_URL + path, { waitUntil: 'domcontentloaded', timeout: 15000 });
          await page.waitForTimeout(2000);
          const links = await page.locator('a[href*="/product"], a[href*="/p/"], a[href*="/prod"]').all();
          if (links.length > 0) {
            console.log(`✅ Found ${links.length} product links at ${path}`);
            found = true;
            break;
          }
        } catch (e) {
          console.log(`  Failed: ${e.message.substring(0, 100)}`);
        }
      }
    }
    
    // Step 3: Extract ALL product links from current page
    console.log('\n🔗 Extracting product links...');
    
    // Common product link patterns
    const productPatterns = [
      'a[href*="/product/"]',
      'a[href*="/p/"]',
      'a[href*="/prod/"]',
      'a[href*="/prodotti/"]',
      'a[href*="/item/"]',
      'a[href*="/shop/"]',
      '[class*="product"] a[href]',
      '[class*="card"] a[href]',
      '[class*="item"] a[href]',
    ];
    
    const seenUrls = new Set();
    
    for (const pattern of productPatterns) {
      try {
        const links = await page.locator(pattern).all();
        for (const link of links) {
          const href = await link.getAttribute('href');
          if (href && href.startsWith('/') || href && href.includes('lasteat')) {
            const fullUrl = href.startsWith('http') ? href : BASE_URL + href;
            if (!seenUrls.has(fullUrl) && !fullUrl.includes('/cart') && !fullUrl.includes('/checkout') && !fullUrl.includes('/wishlist')) {
              seenUrls.add(fullUrl);
              productLinks.push(fullUrl);
            }
          }
        }
      } catch {}
    }
    
    console.log(`Found ${productLinks.length} product links (first pass)`);
    
    // Also try to find pagination and get more links
    let pageNum = 1;
    let hasMorePages = true;
    while (hasMorePages && pageNum < 20) {
      pageNum++;
      const nextSelectors = [
        `a[href*="page=${pageNum}"]`,
        `a[href*="paged=${pageNum}"]`,
        '[class*="pagination"] a[href]',
        '[class*="page"] a[href]',
      ];
      
      hasMorePages = false;
      for (const sel of nextSelectors) {
        try {
          const nextLink = await page.locator(sel).first();
          const href = await nextLink.getAttribute('href');
          if (href && href !== '#') {
            console.log(`Found pagination: ${href}`);
            await nextLink.click({ timeout: 5000 });
            await page.waitForTimeout(2000);
            hasMorePages = true;
            
            // Extract links from this page too
            for (const pattern of productPatterns) {
              try {
                const links = await page.locator(pattern).all();
                for (const link of links) {
                  const href = await link.getAttribute('href');
                  if (href) {
                    const fullUrl = href.startsWith('http') ? href : BASE_URL + href;
                    if (!seenUrls.has(fullUrl) && !fullUrl.includes('/cart') && !fullUrl.includes('/checkout')) {
                      seenUrls.add(fullUrl);
                      productLinks.push(fullUrl);
                    }
                  }
                }
              } catch {}
            }
            break;
          }
        } catch {}
      }
    }
    
    console.log(`Total unique product links found: ${productLinks.length}`);
    totalProducts = productLinks.length;
    
    // Step 4: Process each product
    console.log('\n📦 Processing products...');
    
    for (let i = 0; i < productLinks.length; i++) {
      const url = productLinks[i];
      
      if (i % 10 === 0) {
        console.log(`\nProgress: ${i + 1}/${productLinks.length}`);
      }
      
      try {
        // Check if already exists in DB
        const exists = await checkExists(url);
        if (exists) {
          skippedProducts++;
          console.log(`  ⏭️  Skip (exists): ${url.substring(0, 80)}`);
          continue;
        }
        
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
        await page.waitForTimeout(1500);
        
        const data = await extractPageData(page);
        data.url = url;
        
        // Only save if has nutritional data
        if (hasNutritionalData(data.dosaggio, data.ingredienti)) {
          await saveProduct(data);
          savedProducts++;
          console.log(`  ✅ Saved: ${data.nome || '(no name)'} - URL: ${url.substring(0, 60)}`);
        } else {
          skippedProducts++;
          console.log(`  ⚠️  No nutritional data: ${data.nome || url.substring(0, 60)}`);
        }
        
        if ((i + 1) % 50 === 0) {
          console.log(`\n📊 LOG: Processed ${i + 1}/${productLinks.length} | Saved: ${savedProducts} | Skipped: ${skippedProducts}`);
        }
        
      } catch (e) {
        console.error(`  ❌ Error processing ${url}: ${e.message.substring(0, 100)}`);
        skippedProducts++;
      }
    }
    
  } catch (e) {
    console.error('Fatal error:', e);
  } finally {
    await browser.close();
  }
  
  console.log('\n========== CRAWL COMPLETE ==========');
  console.log(`Total links found: ${totalProducts}`);
  console.log(`Products saved: ${savedProducts}`);
  console.log(`Products skipped: ${skippedProducts}`);
  console.log('=====================================');
}

main().catch(console.error);
