#!/usr/bin/env python3
import asyncio
import sqlite3
import re
import aiohttp

DB_PATH = "integratori.db"

def get_products(offset, limit=100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    SELECT id, nome, url, fonte 
    FROM products 
    WHERE (dosaggio IS NULL OR dosaggio = '') 
    AND (ingredienti IS NULL OR ingredienti = '')
    AND (minsan IS NULL OR minsan = '')
    AND url IS NOT NULL AND url != ''
    AND url_stato = 'live'
    LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_product(pid, forma_farmaceutica, minsan, ingredienti, dosaggio):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    UPDATE products SET forma_farmaceutica=?, minsan=?, ingredienti=?, dosaggio=?, rescrape_batch=8
    WHERE id=?
    ''', (forma_farmaceutica, minsan, ingredienti, dosaggio, pid))
    conn.commit()
    conn.close()

def parse_page(html, url):
    forma_farmaceutica = None
    minsan = None
    ingredienti = None
    dosaggio = None

    if not html:
        return forma_farmaceutica, minsan, ingredienti, dosaggio

    # Try to extract minsan
    minsan_match = re.search(r'(?:minsan|cod\.?\s*minsan|code\.?\s*(?: Ministero| S.sn)|AIC\.?\s*:?\s*)([A-Z0-9]+)', html, re.IGNORECASE)
    if minsan_match:
        minsan = minsan_match.group(1).strip()

    # forma_farmaceutica (capsule, compresse, etc.)
    forma_map = {
        'capsule': 'capsule', 'compresse': 'compresse', 'bustine': 'bustine',
        'flacone': 'flacone', 'fiale': 'fiale', 'cerotti': 'cerotti',
        'gel': 'gel', 'crema': 'crema', 'spray': 'spray', 'gocce': 'gocce',
        'sciroppo': 'sciroppo', 'polvere': 'polvere', 'granulato': 'granulato',
        'soluzione': 'soluzione', 'integratore': 'integratore', 'barattolo': 'barattolo',
        'confezione': 'confezione', 'tavolette': 'tavolette'
    }
    for key, val in forma_map.items():
        if re.search(r'\b' + key + r'\b', html, re.IGNORECASE):
            forma_farmaceutica = val
            break

    # ingredienti
    ingr_match = re.search(r'(?:ingredienti|principi attivi|componenti|contenuto per)[:\s]*([^.<\n]{20,500})', html, re.IGNORECASE)
    if ingr_match:
        ingredienti = ingr_match.group(1).strip()[:500]

    # dosaggio (500mg, 30 capsule, etc.)
    dosaggio_patterns = [
        r'(\d+\s*(?:mg|g|mcg|ml|%)\s*(?:di\s+\w+)?)',
        r'(\d+\s*(?:capsule|compresse|bustine|fiale|cpr|cps)\s*(?:da\s+\d+)?)',
        r'(?:dosaggio|dose)[:\s]*(\d+[^\s,.<]{1,50})',
        r'(\d+\s*(?:porzioni?|servizi?|bust)[\s,])',
    ]
    for pat in dosaggio_patterns:
        dm = re.search(pat, html, re.IGNORECASE)
        if dm:
            dosaggio = dm.group(1).strip()[:200]
            break

    return forma_farmaceutica, minsan, ingredienti, dosaggio

async def fetch_one(session, pid, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    forma, minsan, ingr, dos in parse_page(html, url)
                    return pid, forma, minsan, ingr, dos
                else:
                    return pid, None, None, None, None
        except Exception as e:
            return pid, None, None, None, None

async def main():
    products = get_products(700, 100)
    print(f"Fetching {len(products)} products (batch 8, offset 700)...")

    semaphore = asyncio.Semaphore(8)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for pid, nome, url, fonte in products:
            tasks.append(fetch_one(session, pid, url, semaphore))
        results = await asyncio.gather(*tasks)

    updated = 0
    for pid, forma, minsan, ingr, dos in results:
        if forma or minsan or ingr or dos:
            update_product(pid, forma, minsan, ingr, dos)
            updated += 1
            print(f"  [{pid}] OK - forma={forma}, minsan={minsan}, dosaggio={dos}")

    print(f"\nDone. Updated {updated}/{len(products)} products.")

if __name__ == "__main__":
    asyncio.run(main())