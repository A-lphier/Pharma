#!/usr/bin/env python3
"""Rescrape empty products from integratori.db"""
import sqlite3
import time
import re
import sys

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'

def get_products():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nome, url, fonte 
        FROM products 
        WHERE (dosaggio IS NULL OR dosaggio = '') 
        AND (ingredienti IS NULL OR ingredienti = '')
        AND (minsan IS NULL OR minsan = '')
        AND url IS NOT NULL AND url != '' 
        AND url_stato = 'live'
        LIMIT 100
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def update_product(pid, data):
    """Update product with scraped data, only non-empty fields"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    sets = []
    vals = []
    for field in ['dosaggio', 'ingredienti', 'minsan', 'forma_farmaceutica']:
        if data.get(field):
            sets.append(f"{field} = ?")
            vals.append(data[field])
    
    if not sets:
        conn.close()
        return False
    
    vals.append(pid)
    sql = f"UPDATE products SET {', '.join(sets)} WHERE id = ?"
    cur.execute(sql, vals)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0

def mark_dead(pid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE products SET url_stato = 'dead' WHERE id = ?", (pid,))
    conn.commit()
    conn.close()

def fetch_page_codifa(url):
    """Use curl to fetch page content"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def parse_codifa(html, url):
    """Parse codifa page for ingredienti, dosaggio, minsan, forma_farmaceutica"""
    result = {}
    
    # forma_farmaceutica - often in title like "Matervit Capsule - capsula"
    forma = re.search(r'<h1[^>]*>[^<]*-\s*([\w]+)\s*<', html, re.IGNORECASE)
    if forma:
        result['forma_farmaceutica'] = forma.group(1).lower()
    
    # Try to find minsan - pattern like "AIC 123456" or "MINSAN 123456" or "Cod. 123456"
    minsan_match = re.search(r'(?:AIC|MINSAN|Cod[^.]*?|Cod\.?)\s*[:.]?\s*(\d{8,9})', html, re.IGNORECASE)
    if minsan_match:
        result['minsan'] = minsan_match.group(1)
    
    # Try ingredienti section - look for "Ingredienti" heading and content
    ingredienti_match = re.search(r'(?:Ingredienti|Principi attivi)[:\s]*([^<\\.]+)', html, re.IGNORECASE)
    if ingredienti_match:
        text = ingredienti_match.group(1).strip()[:500]
        if len(text) > 3:
            result['ingredienti'] = text
    
    # Try to extract from "A cosa serve" section for more structured info
    # Look for dosage info
    dosaggio_match = re.search(r'dosaggio[:\s]*([^<\\n]+)', html, re.IGNORECASE)
    if dosaggio_match:
        result['dosaggio'] = dosaggio_match.group(1).strip()[:200]
    
    return result

def fetch_superfarma(url):
    """Fetch superfarma page"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def parse_superfarma(html):
    """Parse superfarma page"""
    result = {}
    
    # forma_farmaceutica
    forma = re.search(r'Forma\s*(?:farmaceutica)?[:\s]*([\w]+)', html, re.IGNORECASE)
    if forma:
        result['forma_farmaceutica'] = forma.group(1).lower()
    
    # minsan
    minsan_match = re.search(r'(?:AIC|MINSAN|Cod[^.]*?|Cod\.?)\s*[:.]?\s*(\d{8,9})', html, re.IGNORECASE)
    if minsan_match:
        result['minsan'] = minsan_match.group(1)
    
    # ingredienti
    ing_match = re.search(r'Ingredienti[:\s]*([^<\\n]+)', html, re.IGNORECASE)
    if ing_match:
        result['ingredienti'] = ing_match.group(1).strip()[:500]
    
    return result

def process_product(pid, nome, url, fonte):
    """Process single product"""
    html = None
    
    if fonte == 'codifa':
        html = fetch_page_codifa(url)
        if html:
            data = parse_codifa(html, url)
        else:
            return 'error'
    elif fonte == 'superfarma':
        html = fetch_superfarma(url)
        if html:
            data = parse_superfarma(html)
        else:
            return 'error'
    else:
        # web_fetch for farmaderbe/erbavita
        html = fetch_page_codifa(url)
        if html:
            data = parse_codifa(html, url)
        else:
            return 'error'
    
    if html is None:
        return 'dead'
    
    if '404' in html[:500] or 'Page not found' in html[:500]:
        return 'dead'
    
    if not data:
        return 'no_data'
    
    updated = update_product(pid, data)
    return 'success' if updated else 'no_data'

def main():
    products = get_products()
    print(f"Processing {len(products)} products...")
    
    stats = {'success': 0, 'no_data': 0, 'dead': 0, 'error': 0}
    enriched_names = []
    
    for i, (pid, nome, url, fonte) in enumerate(products):
        if i > 0 and i % 50 == 0:
            print(f"Progress: {i}/{len(products)} - success:{stats['success']} no_data:{stats['no_data']} dead:{stats['dead']} error:{stats['error']}")
        
        result = process_product(pid, nome, url, fonte)
        stats[result] += 1
        
        if result == 'success':
            enriched_names.append(nome)
        
        time.sleep(2.5)  # Rate limiting
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Successfully enriched: {stats['success']}")
    print(f"No data found on page: {stats['no_data']}")
    print(f"URLs dead: {stats['dead']}")
    print(f"Errors: {stats['error']}")
    print(f"\nSample enriched product names ({min(5, len(enriched_names))}):")
    for name in enriched_names[:5]:
        print(f"  - {name}")

if __name__ == '__main__':
    main()
