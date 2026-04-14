#!/usr/bin/env python3
"""Batch 5 scraper - products 401-500 (offset 400, limit 100)"""
import sqlite3
import asyncio
import re
import json
from urllib.parse import urljoin

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import urllib.request as urllib2

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
        LIMIT 100 OFFSET 400
    """)
    return cur.fetchall()

async def fetch_page(client, url):
    try:
        resp = await client.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }, timeout=15.0)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"  FETCH ERROR {url}: {e}")
    return None

def extract_fields(html, url):
    forma_farmaceutica = ''
    minsan = ''
    ingredienti = ''
    dosaggio = ''

    # Try JSON-LD first
    json_ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for match in json_ld_matches:
        try:
            data = json.loads(match)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get('@type') == 'Product':
                    # forma_farmaceutica
                    ff = item.get('additionalProperty', [])
                    for p in ff:
                        if p.get('name', '').lower() in ['forma farmaceutica', 'formafarmac']:
                            forma_farmaceutica = p.get('value', '')
                    # description for ingredients/dosage
                    desc = item.get('description', '')
                    if desc:
                        ingredienti = desc
        except:
            pass

    # Try OpenGraph
    og_type = re.search(r'<meta property="og:type" content="product"', html)
    if og_type:
        pass

    # Look for specific data in HTML
    # minsan
    minsan_match = re.search(r'(?:minsan|cod\.?\s*minsan|codice\s*minsan)[\s:]*</td>\s*<td[^>]*>([^<]+)', html, re.IGNORECASE)
    if minsan_match:
        minsan = minsan_match.group(1).strip()

    # Try to find minsan in page text
    if not minsan:
        minsan_patterns = [
            r'Minsan[:\s]+([0-9]{9,13})',
            r'Cod\.?\s*Minsan[:\s]+([0-9]{9,13})',
            r'AIC[:\s]+([0-9]{9,13})',
            r'Cod\.?\s*AIC[:\s]+([0-9]{9,13})',
        ]
        text_search = re.search(r'(?:Minsan|AIC|Codice\s*Minsan)[\s:]*([0-9]{9,13})', html, re.IGNORECASE)
        if text_search:
            minsan = text_search.group(1).strip()

    # forma_farmaceutica - look for it in tables
    ff_patterns = [
        r'Forma[_\s]?farmaceutica[:\s]*</td>\s*<td[^>]*>([^<]+)',
        r'Forma\s*farmaceutica[:\s]*([A-Za-zÀ-ÿ\s]+)',
        r'<td[^>]*>Forma\s*farmaceutica</td>\s*<td[^>]*>([^<]+)',
    ]
    for pat in ff_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            forma_farmaceutica = m.group(1).strip()
            break

    # Try product details section
    details = re.search(r'"additionalProperty":\s*\[\{"@type":"PropertyValue","name":"Forma farmaceutica","value":"([^"]+)"', html)
    if details:
        forma_farmaceutica = details.group(1).strip()

    # Try schemaorg text
    ff_schema = re.search(r'"name"\s*:\s*"Forma\s*farmaceutica"\s*,\s*"value"\s*:\s*"([^"]+)"', html)
    if ff_schema:
        forma_farmaceutica = ff_schema.group(1).strip()

    # ingredienti - look in description or specific fields
    desc_match = re.search(r'Ingredienti[:\s]*</td>\s*<td[^>]*>([^<]+)', html)
    if desc_match:
        ingredienti = desc_match.group(1).strip()

    if not ingredienti:
        ingr_patterns = [
            r'Ingredienti\s*[:\-]\s*([A-Za-zÀ-ÿ0-9\s,\.%\-]+?)(?:\n|</p>|</div>|<br)',
            r'Composizione\s*[:\-]\s*([A-Za-zÀ-ÿ0-9\s,\.%\-]+?)(?:\n|</p>|</div>)',
        ]
        for pat in ingr_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                ingredienti = m.group(1).strip()[:500]
                break

    # dosaggio
    dos_patterns = [
        r'dosaggio[:\s]*</td>\s*<td[^>]*>([^<]+)',
        r'dosaggio\s*[:\-]\s*([A-Za-zÀ-ÿ0-9\s,\.%\-]+?)(?:\n|</p>|</div>)',
        r'Dose[:\s]*([A-Za-zÀ-ÿ0-9\s,\.%\-]+?)(?:\n|</p>|</div>)',
    ]
    for pat in dos_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            dosaggio = m.group(1).strip()[:300]
            break

    # Clean up
    forma_farmaceutica = re.sub(r'<[^>]+>', '', forma_farmaceutica).strip()
    ingredienti = re.sub(r'<[^>]+>', '', ingredienti).strip()
    dosaggio = re.sub(r'<[^>]+>', '', dosaggio).strip()

    return forma_farmaceutica, minsan, ingredienti, dosaggio

async def main():
    products = get_products()
    print(f"Processing {len(products)} products (batch 5, offset 400)...")

    updates = []
    errors = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for i, (pid, nome, url, fonte) in enumerate(products):
            print(f"[{i+1}/100] Fetching {pid}: {nome[:50]}...")
            html = await fetch_page(client, url)
            if html:
                forma, minsan_val, ingr, dos = extract_fields(html, url)
                print(f"  -> ff={forma[:30]!r}, minsan={minsan_val!r}, ingr={ingr[:40]!r}, dos={dos[:30]!r}")
                if forma or minsan_val or ingr or dos:
                    updates.append((forma, minsan_val, ingr, dos, pid))
            else:
                errors.append(pid)

    print(f"\nResults: {len(updates)} updated, {len(errors)} failed")

    if updates:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany(
            "UPDATE products SET forma_farmaceutica=?, minsan=?, ingredienti=?, dosaggio=? WHERE id=?",
            updates
        )
        conn.commit()
        print(f"Updated {len(updates)} rows in DB")

    print(f"Failed URLs: {errors}")
    return len(updates), len(errors)

if __name__ == '__main__':
    if not HAS_HTTPX:
        print("httpx not available, using curl")
    else:
        asyncio.run(main())