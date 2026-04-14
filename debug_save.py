#!/usr/bin/env python3
"""Debug crawler to see what's happening with saving."""

import re
import json
import sqlite3
import time
import urllib.request
import ssl

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'
BASE_URL = 'https://www.farmaciauno.it'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
}
ctx = ssl.create_default_context()

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except:
        return None

def extract_products_from_html(html):
    products = []
    parts = html.split('<script')
    for part in parts:
        if 'application/ld+json' not in part:
            continue
        idx = part.find('>')
        if idx < 0:
            continue
        content = part[idx+1:part.find('</script>')]
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                continue
            me = data.get('mainEntity', {})
            if me.get('@type') == 'OfferCatalog' or (isinstance(me, list) and me and me[0].get('@type') == 'OfferCatalog'):
                entities = me if isinstance(me, list) else [me]
                for entity in entities:
                    if not isinstance(entity, dict): continue
                    entity_type = entity.get('@type', '')
                    if entity_type == 'OfferCatalog' or (isinstance(entity_type, list) and 'OfferCatalog' in entity_type):
                        items = entity.get('itemListElement', [])
                        for item in items:
                            if not isinstance(item, dict): continue
                            item_type = item.get('@type', '')
                            if item_type == 'Product' or (isinstance(item_type, list) and 'Product' in item_type):
                                product = parse_product(item)
                                if product and has_nutritional_data(product):
                                    products.append(product)
        except:
            pass
    return products

def parse_product(item):
    name = item.get('name', '')
    if not name:
        return None
    brand = item.get('brand', {})
    if isinstance(brand, dict): brand = brand.get('name', '')
    manufacturer = item.get('manufacturer', {})
    if isinstance(manufacturer, dict): manufacturer = manufacturer.get('name', '')
    azienda = str(brand or manufacturer)
    category = item.get('category', '')
    desc = item.get('description', '')
    desc_clean = re.sub(r'<[^>]+>', ' ', desc)
    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
    url = item.get('url', '')
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
    text = (product.get('dosaggio', '') + ' ' + product.get('ingredienti', '') + ' ' + product.get('indicazioni', '')).lower()
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
            if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr']):
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

# Test with the menopausa category
html = fetch('https://www.farmaciauno.it/integratori/benessere-donna/menopausa.html')
products = extract_products_from_html(html)
print(f'Products with nutritional data from menopausa: {len(products)}')

conn = get_db()
saved = 0
for p in products[:5]:
    print(f'  Trying to save: {p[\"nome\"][:60]}')
    print(f'    azienda={p[\"azienda\"][:30]}, url={p[\"url\"][:60]}')
    print(f'    dosaggio starts with: {p[\"dosaggio\"][:80]}')
    ok = save_product(conn, p)
    print(f'    save_product returned: {ok}')
    if ok:
        saved += 1

print(f'Total saved: {saved}')
conn.close()
