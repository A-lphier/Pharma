import asyncio
import aiohttp
import sqlite3
import json
import re
from typing import Optional

DB_PATH = "integratori.db"
BATCH_SIZE = 100
OFFSET = 3000

async def fetch_minsan(session: aiohttp.ClientSession, product_id: int, url: str, semaphore: asyncio.Semaphore) -> tuple[int, str, Optional[str]]:
    """Fetch URL, extract MINSAN from product__subtitleMinsan span."""
    try:
        async with semaphore:
            async with session.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return product_id, url, None
                text = await resp.text()

                # Direct find approach - more robust than regex for this page
                idx = text.find('product__subtitleMinsan')
                if idx >= 0:
                    snippet = text[idx:idx+200]
                    m2 = re.search(r'>(\d+)<', snippet)
                    if m2:
                        return product_id, url, m2.group(1)

                return product_id, url, None
    except Exception as e:
        return product_id, url, None

async def get_products() -> list[tuple]:
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

async def main():
    products = await get_products()
    print(f"Batch 31: {len(products)} products to scrape (offset {OFFSET})")
    
    if not products:
        print("No products to scrape.")
        return
    
    semaphore = asyncio.Semaphore(8)  # 8 concurrent connections
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for (pid, nome, url, fonte) in products:
            tasks.append(fetch_minsan(session, pid, url, semaphore))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    updates = []
    not_found = []
    errors = []
    
    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result))
            continue
        pid, url, minsan = result
        if minsan:
            updates.append((minsan, pid))
        else:
            not_found.append(pid)
    
    print(f"MINSAN found: {len(updates)}")
    print(f"MINSAN not found: {len(not_found)}")
    if errors:
        print(f"Errors: {len(errors)}")
    
    # Update DB
    if updates:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany("UPDATE products SET minsan = ? WHERE id = ?", updates)
        conn.commit()
        rows_updated = cur.rowcount
        conn.close()
        print(f"DB updated: {rows_updated} rows")
    
    # Print sample
    print("\nSample MINSAN updates:")
    for minsan, pid in updates[:5]:
        conn2 = sqlite3.connect(DB_PATH)
        cur2 = conn2.cursor()
        cur2.execute("SELECT nome, url FROM products WHERE id = ?", (pid,))
        row = cur2.fetchone()
        conn2.close()
        if row:
            print(f"  [{pid}] {row[0]} -> MINSAN: {minsan}")
            print(f"       URL: {row[1]}")

if __name__ == "__main__":
    asyncio.run(main())
