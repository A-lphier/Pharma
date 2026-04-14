#!/usr/bin/env python3
"""
Crawl FarmaciaUno using curl + JSON-LD structured data extraction.
Much faster than Playwright - fetch HTML, parse JSON-LD for products.
"""

import json
import re
import sqlite3
import time
import urllib.request
import urllib.parse
import ssl

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
    """Fetch URL with headers and return response text."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

def extract_json_ld(html):
    """Extract all JSON-LD structured data from HTML."""
    results = []
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            results.append(data)
        except:
            pass
    return results

def parse_itemlist_page(json_ld):
    """Parse ItemList JSON-LD for product URLs."""
    if isinstance(json_ld, dict):
        if json_ld.get('@type') == 'ItemList':
            items = json_ld.get('itemListElement', [])
            urls = []
            for item in items:
                if isinstance(item, dict):
                    url = item.get('url') or item.get('item', {}).get('@id', '')
                    if url:
                        urls.append(url)
            return urls
        # Also check for @graph
        if '@graph' in json_ld:
            return parse_itemlist_page(json_ld['@graph'])
    elif isinstance(json_ld, list):
        urls = []
        for item in json_ld:
            urls.extend(parse_itemlist_page(item))
        return urls
    return []

def parse_product_page(json_ld):
    """Parse Product JSON-LD for product details."""
    if isinstance(json_ld, dict):
        ptype = json_ld.get('@type', '')
        if ptype == 'Product' or (isinstance(ptype, list) and 'Product' in ptype):
            name = json_ld.get('name', '')
            brand = json_ld.get('brand', {})
            if isinstance(brand, dict):
                brand = brand.get('name', '')
            manufacturer = json_ld.get('manufacturer', {})
            if isinstance(manufacturer, dict):
                manufacturer = manufacturer.get('name', manufacturer.get('manufacturer', ''))
            
            category = json_ld.get('category', '')
            
            desc = json_ld.get('description', '')
            # Clean HTML from description
            desc = re.sub(r'<[^>]+>', ' ', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            
            url = ''
            offers = json_ld.get('offers', {})
            if isinstance(offers, dict):
                url = offers.get('url', '')
            if not url:
                url = json_ld.get('url', '')
            
            # Extract nutritional data from description
            dosaggio = extract_nutritional_from_desc(desc)
            
            # Extract modo d'uso from description
            modo_duso = extract_modo_duso(desc)
            
            # Extract ingredients
            ingredienti = extract_ingredienti(desc)
            
            return {
                'nome': name[:500],
                'azienda': (brand or manufacturer)[:200],
                'categoria': category[:500],
                'ingredienti': ingredienti[:2000],
                'dosaggio': dosaggio[:2000],
                'modo_duso': modo_duso[:1000],
                'indicazioni': desc[:1000],
                'url': url,
            }
        if '@graph' in json_ld:
            return parse_product_page(json_ld['@graph'])
    elif isinstance(json_ld, list):
        for item in json_ld:
            result = parse_product_page(item)
            if result:
                return result
    return None

def extract_nutritional_from_desc(desc):
    """Extract nutritional/dosage info from description text."""
    patterns = [
        r'(?i)dose[^.]{0,200}',
        r'(?i)apporto[^.]{0,300}',
        r'(?i)tenori[^.]{0,300}',
        r'(?i)composizione[^.]{0,500}',
        r'(?i)valori[^.]{0,300}',
        r'\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal|UI|%\s*VNR)',
    ]
    results = []
    for p in patterns:
        matches = re.findall(p, desc, re.IGNORECASE)
        for m in matches:
            if any(x in m.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr', '%']):
                results.append(m.strip()[:300])
    
    # Look for the composition/nutritional section specifically
    comp_match = re.search(r'(?i)(?:composizione|apporto|tenori|dose[^a-z]).*?(?=\n\n|tenori|dose|modo|avvert|$)', desc, re.DOTALL)
    if comp_match:
        snippet = comp_match.group(0)[:500]
        if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal']):
            return snippet
    
    return ' | '.join(results[:3])

def extract_modo_duso(desc):
    """Extract usage instructions from description."""
    patterns = [
        r'(?i)modo\s*d[\']?uso[:\s]*[^\n.]{0,300}',
        r'(?i)posologia[:\s]*[^\n.]{0,300}',
        r'(?i)come\s*assumere[:\s]*[^\n.]{0,300}',
        r'(?i)assumere[:\s]*[^\n.]{0,200}',
    ]
    for p in patterns:
        m = re.search(p, desc, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

def extract_ingredienti(desc):
    """Extract ingredients from description."""
    patterns = [
        r'(?i)ingredienti[:\s]*([^\n.]{0,500})',
        r'(?i)principi\s*attivi[:\s]*([^\n.]{0,500})',
        r'(?i)composizione[:\s]*([^\n.]{0,500})',
    ]
    for p in patterns:
        m = re.search(p, desc, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

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
    """Check if product has nutritional data."""
    text = (data.get('dosaggio', '') + ' ' + data.get('ingredienti', '') + ' ' + data.get('indicazioni', '')).lower()
    return any(x in text for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr', '%', 'dose', 'apporto'])

def crawl_category_page(url, conn):
    """Crawl a single category page and save products."""
    html = fetch(url)
    if not html:
        return 0, 0
    
    json_ld_list = extract_json_ld(html)
    
    # First look for ItemList (product listing)
    product_urls = set()
    for jld in json_ld_list:
        urls = parse_itemlist_page(jld)
        product_urls.update(urls)
    
    # Then look for individual products on the page
    for jld in json_ld_list:
        product_data = parse_product_page(jld)
        if product_data and product_data.get('nome') and has_nutritional_data(product_data):
            if save_product(conn, product_data):
                product_urls.add(product_data.get('url', ''))
    
    return len(product_urls), sum(1 for u in product_urls if u)

def discover_category_pages():
    """Discover all integratori category pages."""
    # Start from integratori.html and follow all links
    html = fetch(BASE_URL + '/integratori.html')
    if not html:
        return []
    
    # Find all integratori category links
    cat_links = set()
    # Match /integratori/*.html but NOT product pages (which have product names with numbers)
    for match in re.finditer(r'href="(/integratori/[^"]+)"', html):
        href = match.group(1)
        # Skip product pages - they typically have product-name-number.html pattern
        # Category pages are like /integratori/benessere-donna/menopausa.html
        if not re.search(r'/integratori/[^/]+/[a-z0-9-]+\.html$', href):
            cat_links.add(BASE_URL + href)
    
    return list(cat_links)

def main():
    print("Starting FarmaciaUno crawler (v2 - JSON-LD extraction)...")
    
    # Step 1: Verify site access
    print("Step 1: Testing site access...")
    test_html = fetch(BASE_URL + '/')
    if test_html:
        print(f"  Site accessible. HTML length: {len(test_html)}")
    else:
        print("  Site NOT accessible. Aborting.")
        return
    
    # Step 2: Discover category pages
    print("Step 2: Discovering category pages...")
    # First get the integratori sitemap
    sitemap_html = fetch(BASE_URL + '/sitemap.xml')
    category_pages = []
    
    if sitemap_html:
        # Extract category sitemaps
        sitemap_links = re.findall(r'<loc>([^<]+)</loc>', sitemap_html)
        for link in sitemap_links:
            if 'integratori' in link.lower() and not re.search(r'/prodotti?/', link):
                category_pages.append(link)
        print(f"  Found {len(category_pages)} category pages from sitemap")
    
    # Also find from homepage
    home_html = fetch(BASE_URL + '/')
    if home_html:
        for match in re.finditer(r'href="(/integratori/[^"]+)"', home_html):
            href = match.group(1)
            # Only category pages (not direct product links)
            if '.html' in href and '/integratori/' in href:
                full = BASE_URL + href if href.startswith('/') else href
                if full not in category_pages:
                    category_pages.append(full)
    
    # Remove duplicates
    category_pages = list(set(category_pages))
    print(f"  Total unique category pages: {len(category_pages)}")
    
    # Also add known category pages
    known_pages = [
        BASE_URL + '/integratori.html',
        BASE_URL + '/integratori/vitamine.html',
        BASE_URL + '/integratori/minerali.html',
        BASE_URL + '/integratori/omega.html',
        BASE_URL + '/integratori/probiotici.html',
        BASE_URL + '/integratori/estratti-vegetali.html',
        BASE_URL + '/integratori/benessere-donna.html',
        BASE_URL + '/integratori/benessere-uomo.html',
        BASE_URL + '/integratori/salute.html',
        BASE_URL + '/integratori/sport.html',
        BASE_URL + '/integratori/bellezza.html',
    ]
    for kp in known_pages:
        if kp not in category_pages:
            html = fetch(kp)
            if html and 'application/ld+json' in html:
                category_pages.append(kp)
                print(f"  Added known category: {kp}")
    
    print(f"\n  Total category pages to crawl: {len(category_pages)}")
    for cp in sorted(category_pages)[:10]:
        print(f"    {cp}")
    if len(category_pages) > 10:
        print(f"    ... and {len(category_pages) - 10} more")
    
    # Step 3: Crawl all category pages
    print(f"\nStep 3: Crawling {len(category_pages)} category pages...")
    conn = get_db()
    total_products_saved = 0
    total_products_found = 0
    
    for i, cat_url in enumerate(sorted(category_pages), 1):
        if i % 10 == 0:
            print(f"  Processing category {i}/{len(category_pages)}...")
        
        saved, found = crawl_category_page(cat_url, conn)
        total_products_saved += saved
        total_products_found += found
        
        if i % LOG_EVERY == 0:
            print(f"  Progress: {i}/{len(category_pages)} categories | Saved: {total_products_saved} | Found: {total_products_found}")
        
        time.sleep(0.5)  # Be polite
    
    conn.close()
    print(f"\nDone! Products saved: {total_products_saved}, Total found: {total_products_found}")

if __name__ == '__main__':
    main()
