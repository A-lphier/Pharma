import asyncio
import aiohttp
import sqlite3
import re
import time

DB_PATH = "/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db"
BATCH_SIZE = 100
OFFSET = 2500
CONCURRENCY = 10
PAUSE_BETWEEN_BATCHES = 2

def get_products():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    SELECT id, nome, url, fonte FROM products 
    WHERE (dosaggio IS NULL OR dosaggio = "") 
    AND (ingredienti IS NULL OR ingredienti = "")
    AND (minsan IS NULL OR minsan = "")
    AND url IS NOT NULL AND url != "" AND url_stato = "live"
    AND LOWER(nome) NOT LIKE "%pasta%" AND LOWER(nome) NOT LIKE "%biscott%"
    AND LOWER(nome) NOT LIKE "%olio%" AND LOWER(nome) NOT LIKE "%riso%"
    AND LOWER(nome) NOT LIKE "%farina%" AND LOWER(nome) NOT LIKE "%cracker%"
    AND LOWER(nome) NOT LIKE "%snack%" AND LOWER(nome) NOT LIKE "%bevanda%"
    AND LOWER(nome) NOT LIKE "%caffe%" AND LOWER(nome) NOT LIKE "%the%"
    AND LOWER(nome) NOT LIKE "%cereali%" AND LOWER(nome) NOT LIKE "%quinoa%"
    AND LOWER(nome) NOT LIKE "%lenticch%" AND LOWER(nome) NOT LIKE "%fagioli%"
    AND LOWER(nome) NOT LIKE "%acqua%"
    LIMIT ? OFFSET ?
    ''', (BATCH_SIZE, OFFSET))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_minsan(product_id, minsan):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE products SET minsan = ? WHERE id = ?", (minsan, product_id))
    conn.commit()
    conn.close()

async def scrape_page(session, product_id, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Extract MINSAN from product__subtitleMinsan span
                match = re.search(r'class="product__subtitleMinsan"[^>]*>\s*(\d+)\s*</span>', text)
                if match:
                    minsan = match.group(1)
                    return product_id, minsan, None
                return product_id, None, "MINSAN span not found"
            return product_id, None, f"HTTP {resp.status}"
    except Exception as e:
        return product_id, None, str(e)

async def run():
    products = get_products()
    print(f"Processing {len(products)} products (offset {OFFSET})...")
    
    results = {"found": 0, "not_found": 0, "errors": 0}
    updates = []
    
    for i in range(0, len(products), CONCURRENCY):
        batch = products[i:i+CONCURRENCY]
        connectors = aiohttp.TCPConnector(limit=CONCURRENCY, force_close=True)
        async with aiohttp.ClientSession(connector=connectors, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }) as session:
            tasks = [scrape_page(session, pid, url) for pid, nome, url, fonte in batch]
            batch_results = await asyncio.gather(*tasks)
        
        for product_id, minsan, err in batch_results:
            if minsan:
                updates.append((minsan, product_id))
                results["found"] += 1
            elif err and "not_found" in str(err):
                results["not_found"] += 1
            else:
                results["errors"] += 1
        
        # Batch update DB
        if updates:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.executemany("UPDATE products SET minsan = ? WHERE id = ?", updates)
            conn.commit()
            conn.close()
            print(f"  Batch {i//CONCURRENCY+1}: updated {len(updates)} MINSAN values")
            updates = []
        
        await asyncio.sleep(PAUSE_BETWEEN_BATCHES)
    
    print(f"\nDone! Found: {results['found']}, Not found: {results['not_found']}, Errors: {results['errors']}")
    return results

if __name__ == "__main__":
    asyncio.run(run())
