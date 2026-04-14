#!/usr/bin/env python3
"""RESCRAPE integratori-only (no foods) batch 1
Filters out food products, targets product__subtitleMinsan span for MINSAN.
"""
import asyncio
import re
import json
import sqlite3
import aiohttp
import sys

DB_PATH = "/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

FOOD_EXCLUSIONS = [
    'pasta','biscott','olio','riso','farina','cracker','snack','bevanda','succh',
    'caffe','tè','the','cereali','fiocchi','biscuit','grissini','fette','pane',
    'waffle','merendina','cioccolat','caramell','chewing gum','gomme','seme',
    'semi','farro','kamut','spelta','lenticc','ceci','fagioli','quinoa','couscous',
    'crostate','torte','gelato','yogurt','latte','burro','formaggio','uovo',
    'pollame','carne','pesce','salmone','tonno','prosciutto','pancett','wurstel',
    'salsicc','lombata','petto','fesa','cotto','raw','kibbeh','currywurst','burger',
    'schnitzel','brodo','minestra','passato','zuppa','crema','besciamella',
    'maionese','ketchup','senape','salsa','sughi','ragù','sugo','pesto','olio d',
    'aceto','acqua','tonico','sciroppo','estratto'
]

def get_products(limit=100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Build food exclusion WHERE clause
    food_clauses = " AND ".join([f"LOWER(nome) NOT LIKE '%{w}%'" for w in FOOD_EXCLUSIONS])
    sql = f'''
    SELECT id, nome, url, fonte 
    FROM products 
    WHERE (dosaggio IS NULL OR dosaggio = '') 
    AND (ingredienti IS NULL OR ingredienti = '')
    AND (minsan IS NULL OR minsan = '')
    AND url IS NOT NULL AND url != ''
    AND url_stato = 'live'
    AND {food_clauses}
    LIMIT ?
    '''
    cur.execute(sql, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_product(pid, forma_farmaceutica, minsan, ingredienti, dosaggio):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    UPDATE products SET forma_farmaceutica=?, minsan=?, ingredienti=?, dosaggio=?, rescrape_batch=9
    WHERE id=?
    ''', (forma_farmaceutica, minsan, ingredienti, dosaggio, pid))
    conn.commit()
    conn.close()

def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extractforma(name):
    m = re.search(r'(\d+\s*(?:cpr|cps|caps?|compresse|bust|fl|ml|g|kg|amp|stick|film|gel|os|pastiglie|tavolette)[a-z]?)', name, re.I)
    if m:
        return m.group(1).lower()
    return None

def extract_from_jsonld(text):
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict) and data.get('@type') == 'Product':
                return data
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        return item
        except:
            pass
    return None

def extract_from_html(text):
    result = {}
    
    # minsan from product__subtitleMinsan span (improved scraper)
    m = re.search(r'product__subtitleMinsan[^>]*>([^<]+)<', text)
    if m:
        result['minsan'] = m.group(1).strip()
    
    # Look for ingredienti in descrizione section
    idx = text.find('Descrizione prodotto')
    if idx > 0:
        section = text[idx:idx+5000]
        section_clean = clean_html(section)
        
        m = re.search(r'(?:ingredienti|principi?\s*attiv[^:]*|composizione)[:\s]*(.{10,300})', section_clean, re.I)
        if m:
            result['ingredienti'] = m.group(1).strip()[:300]
        
        for pattern in [
            r'(?:dosaggio|apporto[^a-z])[:\s]*(.{5,150})',
            r'apporto\s*giornaliero[^:]*:\s*([^\n.]{5,150})',
        ]:
            m = re.search(pattern, section_clean, re.I)
            if m:
                result['dosaggio'] = m.group(1).strip()[:150]
                break
        
        m = re.search(r'forma\s*farmaceutica[:\s]*([^\n.]{3,80})', section_clean, re.I)
        if m:
            result['forma_farmaceutica'] = m.group(1).strip()[:80]
    
    return result

async def fetch_product(session, pid, nome, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return pid, nome, url, None, None, None, None, f'HTTP {resp.status}'
            text = await resp.text()
    except Exception as e:
        return pid, nome, url, None, None, None, None, str(e)

    jsonld = extract_from_jsonld(text)
    
    minsan = None
    forma_farmaceutica = None
    ingredienti = None
    dosaggio = None
    
    if jsonld:
        sku = jsonld.get('sku', '')
        if sku and re.match(r'^\d{9,13}$', str(sku)):
            minsan = str(sku)
        
        desc = jsonld.get('description', '')
        if desc:
            m = re.search(r'dosaggio[:\s]*(.{5,150})', desc, re.I)
            if not m:
                m = re.search(r'apporto[^:]*:\s*([^\n.]{5,150})', desc, re.I)
            if m:
                dosaggio = m.group(1).strip()[:150]
            
            m = re.search(r'(?:ingredienti|principi?\s*attiv[^:]*|composizione)[:\s]*(.{10,300})', desc, re.I)
            if m:
                ingredienti = m.group(1).strip()[:300]
    
    html_data = extract_from_html(text)
    
    if not minsan and 'minsan' in html_data:
        minsan = html_data['minsan']
    
    if not forma_farmaceutica:
        if 'forma_farmaceutica' in html_data:
            forma_farmaceutica = html_data['forma_farmaceutica']
        else:
            forma_farmaceutica = extractforma(nome)
    
    if not ingredienti and 'ingredienti' in html_data:
        ingredienti = html_data['ingredienti']
    
    if not dosaggio and 'dosaggio' in html_data:
        dosaggio = html_data['dosaggio']
    
    return pid, nome, url, forma_farmaceutica, minsan, ingredienti, dosaggio, None

async def main():
    products = get_products(100)
    print(f"RESCRAPE integratori-only batch 1: {len(products)} products to process")
    if not products:
        print("No products found matching criteria.")
        return
    
    print(f"First 5: {[(p[0], p[1][:40]) for p in products[:5]]}")

    semaphore = asyncio.Semaphore(8)
    
    async with aiohttp.ClientSession() as session:
        async def sem_fetch(pid, nome, url):
            async with semaphore:
                return await fetch_product(session, pid, nome, url)
        
        tasks = [sem_fetch(pid, nome, url) for pid, nome, url, fonte in products]
        results = await asyncio.gather(*tasks)

    updates = 0
    skipped = 0
    errors = 0
    enriched_names = []

    for pid, nome, url, forma_farmaceutica, minsan, ingredienti, dosaggio, error in results:
        if error:
            print(f"[ERR] {pid} {nome[:40]}: {error}")
            errors += 1
            continue

        has_data = any([forma_farmaceutica, minsan, ingredienti, dosaggio])
        if not has_data:
            print(f"[SKIP] {pid} {nome[:40]}: no data")
            skipped += 1
            continue

        fields = []
        vals = []
        if forma_farmaceutica:
            fields.append("forma_farmaceutica = ?")
            vals.append(forma_farmaceutica)
        if minsan:
            fields.append("minsan = ?")
            vals.append(minsan)
        if ingredienti:
            fields.append("ingredienti = ?")
            vals.append(ingredienti)
        if dosaggio:
            fields.append("dosaggio = ?")
            vals.append(dosaggio)

        if fields:
            vals.append(pid)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            sql = f"UPDATE products SET {', '.join(fields)} WHERE id = ?"
            cur.execute(sql, vals)
            conn.commit()
            conn.close()
            updates += 1
            enriched_names.append(nome)
            print(f"[OK] {pid} {nome[:40]}: forma={forma_farmaceutica}, minsan={minsan}, dosaggio={str(dosaggio)[:30] if dosaggio else None}")

    print(f"\n=== RESULTS ===")
    print(f"Total processed: {len(products)}")
    print(f"Enriched (updated): {updates}")
    print(f"No data found: {skipped}")
    print(f"Errors: {errors}")
    print(f"\nSample enriched names (first 10):")
    for n in enriched_names[:10]:
        print(f"  - {n[:60]}")

if __name__ == '__main__':
    asyncio.run(main())
