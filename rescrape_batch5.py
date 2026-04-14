import asyncio
import aiohttp
import sqlite3
import re
from bs4 import BeautifulSoup

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'

async def fetch_minsan(session, url, product_id):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                return product_id, None, f"HTTP {resp.status}"
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            span = soup.find('span', {'class': 'product__subtitleMinsan'})
            if span:
                minsan = span.get_text(strip=True)
                return product_id, minsan, None
            return product_id, None, "span not found"
    except Exception as e:
        return product_id, None, str(e)

async def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''SELECT id, nome, url, fonte FROM products WHERE (dosaggio IS NULL OR dosaggio = '') AND (ingredienti IS NULL OR ingredienti = '') AND (minsan IS NULL OR minsan = '') AND url IS NOT NULL AND url != '' AND url_stato = 'live' AND LOWER(nome) NOT LIKE '%pasta%' AND LOWER(nome) NOT LIKE '%biscott%' AND LOWER(nome) NOT LIKE '%olio%' AND LOWER(nome) NOT LIKE '%riso%' AND LOWER(nome) NOT LIKE '%farina%' AND LOWER(nome) NOT LIKE '%cracker%' AND LOWER(nome) NOT LIKE '%snack%' AND LOWER(nome) NOT LIKE '%bevanda%' AND LOWER(nome) NOT LIKE '%caffe%' AND LOWER(nome) NOT LIKE '%the%' AND LOWER(nome) NOT LIKE '%cereali%' AND LOWER(nome) NOT LIKE '%quinoa%' AND LOWER(nome) NOT LIKE '%lenticch%' AND LOWER(nome) NOT LIKE '%fagioli%' AND LOWER(nome) NOT LIKE '%olio d%' AND LOWER(nome) NOT LIKE '%acqua%' LIMIT 100 OFFSET 400''')
    rows = cur.fetchall()
    conn.close()

    print(f"Processing {len(rows)} products...")
    results = []
    errors = []

    semaphore = asyncio.Semaphore(15)

    async def bounded_fetch(session, url, pid):
        async with semaphore:
            return await fetch_minsan(session, url, pid)

    connector = aiohttp.TCPConnector(limit=20, force_close=True)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [bounded_fetch(session, row[2], row[0]) for row in rows]
        task_results = await asyncio.gather(*tasks)

    updates = 0
    for idx, (pid, minsan, err) in enumerate(task_results):
        row = rows[idx]
        nome = row[1]
        if minsan:
            cur2 = sqlite3.connect(DB_PATH)
            cur2.execute('UPDATE products SET minsan = ? WHERE id = ?', (minsan, pid))
            cur2.commit()
            cur2.close()
            updates += 1
            print(f"OK id={pid} minsan={minsan}")
        else:
            errors.append(f"id={pid} nome={nome[:40]} err={err}")
            print(f"FAIL id={pid} err={err}")

    print(f"\nDone. Updated {updates} products, {len(errors)} failures.")
    if errors:
        print("Failures:")
        for e in errors[:20]:
            print(f"  {e}")

if __name__ == '__main__':
    asyncio.run(main())