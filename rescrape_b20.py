import asyncio
import aiohttp
import sqlite3
import re
from typing import Optional, Tuple

DB_PATH = "integratori.db"

async def scrape_minsan(session: aiohttp.ClientSession, url: str) -> Tuple[str, str, int]:
    """Scrape MINSAN from superfarma.it product page."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return url, "", resp.status
            text = await resp.text()
            # Look for product__subtitleMinsan span
            match = re.search(r'<span[^>]*class=["\']product__subtitleMinsan["\'][^>]*>([\d]+)</span>', text)
            if match:
                return url, match.group(1), resp.status
            return url, "", resp.status
    except Exception as e:
        return url, "", -1

async def worker(semaphore: asyncio.Semaphore, session: aiohttp.ClientSession, row: tuple, results: list):
    async with semaphore:
        pid, nome, url, fonte = row
        _, minsan, status = await scrape_minsan(session, url)
        results.append((pid, minsan, status, nome))

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('''SELECT id, nome, url, fonte FROM products 
    WHERE (dosaggio IS NULL OR dosaggio = '') 
    AND (ingredienti IS NULL OR ingredienti = '')
    AND (minsan IS NULL OR minsan = '')
    AND url IS NOT NULL AND url != '' AND url_stato = 'live'
    AND LOWER(nome) NOT LIKE '%pasta%' AND LOWER(nome) NOT LIKE '%biscott%'
    AND LOWER(nome) NOT LIKE '%olio%' AND LOWER(nome) NOT LIKE '%risco%'
    AND LOWER(nome) NOT LIKE '%farina%' AND LOWER(nome) NOT LIKE '%cracker%'
    AND LOWER(nome) NOT LIKE '%snack%' AND LOWER(nome) NOT LIKE '%bevanda%'
    AND LOWER(nome) NOT LIKE '%caffe%' AND LOWER(nome) NOT LIKE '%the%'
    AND LOWER(nome) NOT LIKE '%cereali%' AND LOWER(nome) NOT LIKE '%quinoa%'
    AND LOWER(nome) NOT LIKE '%lenticch%' AND LOWER(nome) NOT LIKE '%fagioli%'
    AND LOWER(nome) NOT LIKE '%acqua%'
    LIMIT 100 OFFSET 1900''')
    rows = cur.fetchall()
    
    print(f"Processing {len(rows)} products...")
    
    results = []
    semaphore = asyncio.Semaphore(15)
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = [worker(semaphore, session, row, results) for row in rows]
        await asyncio.gather(*tasks)
    
    updated = 0
    failed = 0
    for pid, minsan, status, nome in results:
        if minsan:
            cur.execute('UPDATE products SET minsan = ? WHERE id = ?', (minsan, pid))
            updated += 1
        else:
            failed += 1
            print(f"  MISS [{pid}] {nome} (status={status})")
    
    conn.commit()
    print(f"\nDone. Updated={updated}, Failed={failed}")
    
    # Show sample of updated
    cur.execute('SELECT id, minsan, nome FROM products WHERE minsan IS NOT NULL AND minsan != "" ORDER BY id DESC LIMIT 10')
    sample = cur.fetchall()
    print("\nSample updated:")
    for r in sample:
        print(f"  {r}")

if __name__ == "__main__":
    asyncio.run(main())
