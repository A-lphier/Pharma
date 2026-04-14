#!/usr/bin/env python3
"""Rescrape empty products - concurrent version"""
import sqlite3
import asyncio
import aiohttp
import re
import time
import json
from datetime import datetime

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'

SEMAPHORE_LIMIT = 5  # Max concurrent requests

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
    if not data:
        return False
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

async def fetch_url(session, url):
    """Fetch URL with aiohttp"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 404:
                return None, 'dead'
            html = await resp.text(errors='ignore')
            return html, 'ok'
    except asyncio.TimeoutError:
        return None, 'timeout'
    except Exception as e:
        return None, 'error'

def parse_codifa(html):
    """Parse codifa page"""
    result = {}
    if not html:
        return result
    
    # forma_farmaceutica - "Matervit Capsule - capsula"
    forma = re.search(r'<h1[^>]*>[^<]*-\s*([\wàèéìòù]+)\s*<', html, re.IGNORECASE)
    if forma:
        result['forma_farmaceutica'] = forma.group(1).lower()
    
    # minsan patterns
    for pattern in [
        r'(?:AIC\s*(?:n°|n|°|#|code|cod)?\.?\s*:?\s*)(\d{8,9})',
        r'(?:MINSAN\s*(?:n°|n|°|#|code|cod)?\.?\s*:?\s*)(\d{8,9})',
        r'(?:Cod\.?\s*(?:AIC|MINSAN)?\.?\s*:?\s*)(\d{8,9})',
        r'(?:Codice\s*(?:AIC|MINSAN)?\.?\s*:?\s*)(\d{8,9})',
        r'class="minsan"[^>]*>(\d{8,9})',
        r'"minsan"[^>]*>(?:<[^>]*>)*(\d{8,9})',
    ]:
        minsan_match = re.search(pattern, html, re.IGNORECASE)
        if minsan_match:
            result['minsan'] = minsan_match.group(1)
            break
    
    # ingredienti
    ing_patterns = [
        r'(?:Ingredienti|Principi attivi|Composizione)[:\s]*</[^>]+>\s*<[^>]+>([^<]{10,500})',
        r'Ingredienti[:\s]*([\w\s,;.\-àèéìòù()]+?)(?:\.|<br|\\n|Principi|Attivo|$)',
        r'class="ingredienti"[^>]*>([^<]{10,500})',
    ]
    for pattern in ing_patterns:
        ing_match = re.search(pattern, html, re.IGNORECASE)
        if ing_match:
            text = ing_match.group(1).strip()
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 5:
                result['ingredienti'] = text[:500]
                break
    
    # dosaggio
    dos_patterns = [
        r'(?:Dosaggio|Posologia|Dose)[:\s]*([\w\s,.\-àèéìòù()]+?)(?:\.|<br|\\n|$)',
        r'class="dosaggio"[^>]*>([^<]{5,200})',
    ]
    for pattern in dos_patterns:
        dos_match = re.search(pattern, html, re.IGNORECASE)
        if dos_match:
            text = dos_match.group(1).strip()
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 3:
                result['dosaggio'] = text[:200]
                break
    
    return result

async def process_product(session, sem, pid, nome, url, fonte, results):
    """Process single product"""
    async with sem:
        await asyncio.sleep(0.5)  # Small delay between requests
        
        html, status = await fetch_url(session, url)
        
        if status == 'dead' or html is None:
            mark_dead(pid)
            results['dead'] += 1
            return
        
        if '404' in html[:500] or 'page not found' in html[:500].lower():
            mark_dead(pid)
            results['dead'] += 1
            return
        
        if fonte == 'codifa':
            data = parse_codifa(html)
        else:
            data = parse_codifa(html)
        
        if data:
            updated = update_product(pid, data)
            if updated:
                results['success'] += 1
                results['enriched'].append(nome)
                return
        
        results['no_data'] += 1

async def main():
    products = get_products()
    print(f"Processing {len(products)} products...")
    
    results = {'success': 0, 'no_data': 0, 'dead': 0, 'error': 0, 'enriched': []}
    
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_product(session, sem, pid, nome, url, fonte, results)
            for pid, nome, url, fonte in products
        ]
        
        for i, task in enumerate(asyncio.as_completed(tasks)):
            await task
            if (i + 1) % 20 == 0:
                print(f"Progress: {i+1}/{len(products)} - success:{results['success']} no_data:{results['no_data']} dead:{results['dead']}")
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Successfully enriched: {results['success']}")
    print(f"No data found on page: {results['no_data']}")
    print(f"URLs dead: {results['dead']}")
    print(f"\nSample enriched product names ({min(5, len(results['enriched']))}):")
    for name in results['enriched'][:5]:
        print(f"  - {name}")

if __name__ == '__main__':
    asyncio.run(main())
