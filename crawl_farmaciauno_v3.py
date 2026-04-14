#!/usr/bin/env python3
"""
Smart crawler: Use Playwright with longer wait for JS-rendered content.
Products are loaded dynamically but the category links ARE accessible via curl.
Strategy:
1. Use curl to find all category pages (they're server-side rendered)
2. For each category, find product links in the HTML
3. Use Playwright to visit each product and extract data
4. Fallback: use curl to extract from product page HTML directly
"""

import asyncio
import json
import re
import sqlite3
import time
import urllib.request
import ssl
from playwright.async_api import async_playwright

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'
BASE_URL = 'https://www.farmaciauno.it'
LOG_EVERY = 50

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
ctx = ssl.create_default_context()

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def extract_product_links_from_html(html):
    """Extract product links from rendered HTML."""
    links = set()
    # Product pages have URLs like /product-name-12345.html
    # They appear in the main content area
    for match in re.finditer(r'href="(/[a-z0-9\-]+-\d+\.html)"', html, re.IGNORECASE):
        href = match.group(1)
        # Filter out category/nav links
        if not any(x in href for x in ['/integratori/', '/categor', '/brand', '/catalog']):
            full = BASE_URL + href
            links.add(full)
    return list(links)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = 0")
    return conn

def save_product(conn, data):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO products (
            nome, azienda, categoria, ingredienti, dosaggio,
            modo_duso, indicazioni, url, fonte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('nome'),
        data.get('azienda'),
        data.get('categoria'),
        data.get('ingredienti'),
        data.get('dosaggio'),
        data.get('modo_duso'),
        data.get('indicazioni'),
        data.get('url'),
        'farmaciauno'
    ))
    conn.commit()
    return cur.rowcount > 0

def has_nutritional_data(data):
    text = (data.get('dosaggio', '') + ' ' + data.get('ingredienti', '') + ' ' + data.get('indicazioni', '')).lower()
    return any(x in text for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr', '%'])

def extract_product_data_from_html(html, url):
    """Extract product data from raw HTML (no JS needed)."""
    data = {}
    
    # Title
    m = re.search(r'<h1[^>]*class=["\'][^"\']*product[^"\']*["\'][^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        data['nome'] = title[:500]
    
    if not data.get('nome'):
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            title = m.group(1).split('|')[0].strip()
            data['nome'] = title[:500]
    
    # Brand
    m = re.search(r'(?i)class=["\'][^"\']*product[^"\']*["\'][^>]*>.*?brand[^>]*>([^<]+)', html, re.DOTALL)
    if not m:
        m = re.search(r'(?i)class=["\'][^"\']*manufacturer[^"\']*["\'][^>]*>([^<]+)', html)
    if m:
        data['azienda'] = m.group(1).strip()[:200]
    
    # Category (breadcrumb)
    m = re.search(r'(?i)<nav[^>]*breadcrumb[^>]*>(.*?)</nav>', html, re.DOTALL)
    if m:
        crumbs = re.findall(r'<span[^>]*>([^<]+)</span>', m.group(1))
        data['categoria'] = ' > '.join(crumbs)[:500]
    
    # Try to find JSON-LD with full product data
    for match in re.finditer(r'<script[^>]*type=[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            jld = json.loads(match.group(1))
            if isinstance(jld, dict):
                t = jld.get('@type', '')
                if isinstance(t, list):
                    has_product = 'Product' in t
                else:
                    has_product = t == 'Product'
                if has_product or '@graph' in jld:
                    graph = jld.get('@graph', [jld])
                    for item in graph:
                        if item.get('@type') == 'Product':
                            data['nome'] = item.get('name', data.get('nome', ''))[:500]
                            brand = item.get('brand', {})
                            if isinstance(brand, dict):
                                data['azienda'] = brand.get('name', '')[:200]
                            else:
                                data['azienda'] = str(brand)[:200]
                            data['categoria'] = item.get('category', '')[:500]
                            desc = item.get('description', '')
                            desc_clean = re.sub(r'<[^>]+>', ' ', desc)
                            desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
                            data['indicazioni'] = desc_clean[:1000]
                            
                            # Nutritional data from description
                            data['dosaggio'] = extract_nutritional(desc_clean)[:2000]
                            data['ingredienti'] = extract_ingredienti(desc_clean)[:2000]
                            data['modo_duso'] = extract_modo_duso(desc_clean)[:1000]
                            data['url'] = item.get('url', url)
                            break
        except:
            pass
    
    if not data.get('url'):
        data['url'] = url
    if not data.get('nome'):
        data['nome'] = url.split('/')[-1].replace('-', ' ').replace('_', ' ')[:500]
    
    return data

def extract_nutritional(text):
    patterns = [
        r'(?i)composizione[:\s]*[^\n.]{0,500}',
        r'(?i)apporto[:\s]*[^\n.]{0,500}',
        r'(?i)tenori[:\s]*[^\n.]{0,500}',
        r'(?i)dose[^.]{0,300}',
        r'(?i)valori[^.]{0,300}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            snippet = m.group(0)
            if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr']):
                return snippet
    return ''

def extract_modo_duso(text):
    patterns = [
        r'(?i)modo\s*d[\']?uso[:\s]*[^\n.]{0,300}',
        r'(?i)posologia[:\s]*[^\n.]{0,300}',
        r'(?i)assumere[:\s]*[^\n.]{0,200}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

def extract_ingredienti(text):
    patterns = [
        r'(?i)ingredienti[:\s]*[^\n.]{0,500}',
        r'(?i)principi\s*attivi[:\s]*[^\n.]{0,300}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

async def fetch_product_playwright(page, url, retries=2):
    """Try to fetch product using Playwright (for JS-rendered content)."""
    for attempt in range(retries):
        try:
            await page.goto(url, timeout=30000, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check if we got a real page
            title = await page.title()
            if '404' not in title and '500' not in title and 'page not found' not in title.lower():
                return await page.content()
        except Exception as e:
            if attempt == retries - 1:
                print(f"  PW error {url}: {e}")
    return None

async def main():
    print("=== FarmaciaUno Smart Crawler ===")
    
    # Step 1: Verify site access via curl
    print("Step 1: Testing curl access...")
    html = fetch(BASE_URL + '/')
    if not html:
        print("  Site NOT accessible. Aborting.")
        return
    print(f"  OK. HTML length: {len(html)}")
    
    # Step 2: Discover category pages using curl
    print("Step 2: Discovering category pages...")
    
    # Start from integratori.html
    integratori_html = fetch(BASE_URL + '/integratori.html')
    category_pages = set()
    
    if integratori_html:
        # Find all links under /integratori/
        for match in re.finditer(r'href="(/integratori/[^"]+)"', integratori_html):
            href = match.group(1)
            if href.endswith('.html') and '/prodotti/' not in href:
                category_pages.add(BASE_URL + href)
    
    # Also find from homepage
    for match in re.finditer(r'href="(/integratori/[^"]+)"', html):
        href = match.group(1)
        if href.endswith('.html') and '/prodotti/' not in href:
            category_pages.add(BASE_URL + href)
    
    # Try sitemap
    sitemap = fetch(BASE_URL + '/sitemap.xml')
    if sitemap:
        for match in re.finditer(r'<loc>([^<]+)</loc>', sitemap):
            loc = match.group(1)
            if '/integratori/' in loc and loc.endswith('.html'):
                category_pages.add(loc)
    
    category_pages = sorted(category_pages)
    print(f"  Found {len(category_pages)} category pages")
    for cp in category_pages[:5]:
        print(f"    {cp}")
    
    # Step 3: Collect product links from all categories
    print("Step 3: Collecting product links from categories...")
    all_product_urls = set()
    
    for i, cat_url in enumerate(category_pages, 1):
        if i % 20 == 0:
            print(f"  Category {i}/{len(category_pages)}: found {len(all_product_urls)} products so far")
        
        cat_html = fetch(cat_url)
        if cat_html:
            # Find product links
            # Products have URLs like /product-name-12345.html
            # They appear inside product grid items
            for match in re.finditer(r'href="(/[a-z][a-z0-9\-]+-\d{5,}\.html)"', cat_html, re.IGNORECASE):
                href = match.group(1)
                full = BASE_URL + href
                # Exclude nav/category links
                if '/integratori/' not in href or '/prodotti/' in href:
                    all_product_urls.add(full)
        
        time.sleep(0.3)
    
    all_product_urls = sorted(all_product_urls)
    print(f"  Total product URLs collected: {len(all_product_urls)}")
    
    # Step 4: Extract product data
    print(f"Step 4: Extracting data from {len(all_product_urls)} products...")
    conn = get_db()
    saved_count = 0
    skipped = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                  '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
            extra_http_headers={'Accept-Language': 'it-IT,it;q=0.9'}
        )
        page = await context.new_page()
        
        for i, url in enumerate(all_product_urls, 1):
            if i % LOG_EVERY == 0:
                print(f"  Processing {i}/{len(all_product_urls)} (saved: {saved_count})")
            
            # Try curl first (faster)
            html = fetch(url)
            product_data = None
            
            if html and 'product' in html.lower():
                product_data = extract_product_data_from_html(html, url)
            
            # If curl didn't work, try Playwright
            if not product_data or not product_data.get('nome'):
                pw_html = await fetch_product_playwright(page, url)
                if pw_html:
                    product_data = extract_product_data_from_html(pw_html, url)
            
            if product_data and product_data.get('nome') and has_nutritional_data(product_data):
                if save_product(conn, product_data):
                    saved_count += 1
            else:
                skipped += 1
                if skipped <= 5:
                    print(f"    SKIP: {url}")
            
            # Be polite
            if i % 100 == 0:
                await asyncio.sleep(1)
        
        await browser.close()
    
    conn.close()
    print(f"\nDone! Saved: {saved_count}, Skipped: {skipped}")

if __name__ == '__main__':
    asyncio.run(main())
