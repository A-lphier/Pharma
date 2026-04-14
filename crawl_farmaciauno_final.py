#!/usr/bin/env python3
"""
FarmaciaUno crawler using curl + JSON-LD extraction.
Strategy: curl fetches category pages (server-side rendered with full product data in JSON-LD).
Products are embedded in WebPage > mainEntity > OfferCatalog > itemListElement.
"""

import re
import json
import sqlite3
import time
import urllib.request
import ssl

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'
BASE_URL = 'https://www.farmaciauno.it'
LOG_EVERY = 10
REQUEST_DELAY = 0.5  # seconds between requests

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

def extract_products_from_html(html):
    """Extract all products from HTML using JSON-LD split method."""
    products = []
    parts = html.split('<script')
    
    for part in parts:
        if 'application/ld+json' not in part:
            continue
        
        # Find the first > that closes the opening script tag
        idx = part.find('>')
        if idx < 0:
            continue
        content_start = idx + 1
        end_idx = part.find('</script>')
        if end_idx < 0:
            continue
        content = part[content_start:end_idx]
        
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                continue
            
            # Look for WebPage with mainEntity > OfferCatalog
            main_entity = None
            if data.get('@type') == 'WebPage' and 'mainEntity' in data:
                main_entity = data['mainEntity']
            elif '@graph' in data:
                for g in data['@graph']:
                    if isinstance(g, dict) and g.get('@type') == 'WebPage':
                        main_entity = g.get('mainEntity')
                        break
            
            if not main_entity:
                continue
            
            # Handle list or dict
            entities = main_entity if isinstance(main_entity, list) else [main_entity]
            
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                entity_type = entity.get('@type', '')
                if entity_type == 'OfferCatalog' or (isinstance(entity_type, list) and 'OfferCatalog' in entity_type):
                    items = entity.get('itemListElement', [])
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get('@type', '')
                        if item_type == 'Product' or (isinstance(item_type, list) and 'Product' in item_type):
                            product = parse_product(item)
                            if product and has_nutritional_data(product):
                                products.append(product)
        except:
            pass
    
    return products

def parse_product(item):
    """Parse a Product JSON-LD item into our data format."""
    name = item.get('name', '')
    if not name:
        return None
    
    # Brand
    brand = item.get('brand', {})
    if isinstance(brand, dict):
        brand = brand.get('name', '')
    brand = str(brand) if brand else ''
    
    # Manufacturer
    manufacturer = item.get('manufacturer', {})
    if isinstance(manufacturer, dict):
        manufacturer = manufacturer.get('name', '')
    manufacturer = str(manufacturer) if manufacturer else ''
    
    azienda = brand or manufacturer
    
    # Category
    category = item.get('category', '')
    
    # Description
    desc = item.get('description', '')
    desc_clean = re.sub(r'<[^>]+>', ' ', desc)
    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
    
    # URL
    url = item.get('url', '')
    
    # Extract nutritional data from description
    dosaggio = extract_nutritional(desc_clean)
    modo_duso = extract_modo_duso(desc_clean)
    ingredienti = extract_ingredienti(desc_clean)
    
    return {
        'nome': name[:500],
        'azienda': azienda[:200],
        'categoria': category[:500],
        'ingredienti': ingredienti[:2000],
        'dosaggio': dosaggio[:2000],
        'modo_duso': modo_duso[:1000],
        'indicazioni': desc_clean[:1000],
        'url': url,
    }

def has_nutritional_data(product):
    """Check if product has nutritional data."""
    text = (
        product.get('dosaggio', '') + ' ' +
        product.get('ingredienti', '') + ' ' +
        product.get('indicazioni', '')
    ).lower()
    return any(x in text for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr', '%', 'apporto', 'dose', 'tenori'])

def extract_nutritional(text):
    patterns = [
        r'(?i)composizione[:\s]*[^\n]{0,600}',
        r'(?i)apporto[:\s]*[^\n]{0,600}',
        r'(?i)tenori[:\s]*[^\n]{0,600}',
        r'(?i)dose[^.]{0,400}',
        r'(?i)valori[^.]{0,400}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            snippet = m.group(0)[:500]
            if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr', '%']):
                return snippet
    return ''

def extract_modo_duso(text):
    patterns = [
        r'(?i)modo\s*d[\']?uso[:\s]*[^\n]{0,400}',
        r'(?i)posologia[:\s]*[^\n]{0,400}',
        r'(?i)assumere[:\s]*[^\n]{0,200}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

def extract_ingredienti(text):
    patterns = [
        r'(?i)ingredienti[:\s]*[^\n]{0,600}',
        r'(?i)principi\s*attivi[:\s]*[^\n]{0,400}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
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

def discover_category_pages():
    """Discover all integratori category pages."""
    category_pages = set()
    
    # Start from integratori.html
    html = fetch(BASE_URL + '/integratori.html')
    if html:
        # Find all integratori category links
        for match in re.finditer(r'href="(/integratori/[^"]+)"', html):
            href = match.group(1)
            if href.endswith('.html') and '/prodotti/' not in href:
                category_pages.add(BASE_URL + href)
    
    # Also from homepage
    home_html = fetch(BASE_URL + '/')
    if home_html:
        for match in re.finditer(r'href="(/integratori/[^"]+)"', home_html):
            href = match.group(1)
            if href.endswith('.html') and '/prodotti/' not in href:
                category_pages.add(BASE_URL + href)
    
    return sorted(category_pages)

def main():
    print("=== FarmaciaUno Crawler (curl + JSON-LD) ===")
    
    # Step 1: Verify site access
    print("\nStep 1: Verifying site access...")
    test_html = fetch(BASE_URL + '/')
    if not test_html:
        print("  ERROR: Site not accessible!")
        return
    print(f"  OK. HTML length: {len(test_html)}")
    
    # Step 2: Discover category pages
    print("\nStep 2: Discovering category pages...")
    category_pages = discover_category_pages()
    print(f"  Found {len(category_pages)} category pages:")
    for cp in category_pages[:10]:
        print(f"    {cp}")
    if len(category_pages) > 10:
        print(f"    ... and {len(category_pages) - 10} more")
    
    # Step 3: Crawl each category page
    print(f"\nStep 3: Crawling {len(category_pages)} category pages...")
    conn = get_db()
    total_saved = 0
    total_found = 0
    
    for i, cat_url in enumerate(category_pages, 1):
        if i % 5 == 0:
            print(f"  [{i}/{len(category_pages)}] Processing: {cat_url.split('/')[-1]}")
        
        html = fetch(cat_url)
        if not html:
            continue
        
        products = extract_products_from_html(html)
        total_found += len(products)
        
        for product in products:
            if save_product(conn, product):
                total_saved += 1
        
        if i % LOG_EVERY == 0:
            print(f"  Progress: {i}/{len(category_pages)} | Found: {total_found} | Saved: {total_saved}")
        
        time.sleep(REQUEST_DELAY)
    
    conn.close()
    print(f"\n=== Done! ===")
    print(f"  Category pages processed: {len(category_pages)}")
    print(f"  Total products found: {total_found}")
    print(f"  New products saved to DB: {total_saved}")

if __name__ == '__main__':
    main()
