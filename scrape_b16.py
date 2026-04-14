#!/usr/bin/env python3
import asyncio
import aiosqlite
import httpx
import re
import sys

DB_PATH = "/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db"

async def get_products(offset, limit=100):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT id, nome, url, fonte FROM products 
            WHERE (dosaggio IS NULL OR dosaggio = '') 
            AND (ingredienti IS NULL OR ingredienti = '')
            AND (minsan IS NULL OR minsan = '')
            AND url IS NOT NULL AND url != '' AND url_stato = 'live'
            AND LOWER(nome) NOT LIKE '%pasta%' AND LOWER(nome) NOT LIKE '%biscott%'
            AND LOWER(nome) NOT LIKE '%olio%' AND LOWER(nome) NOT LIKE '%riso%'
            AND LOWER(nome) NOT LIKE '%farina%' AND LOWER(nome) NOT LIKE '%cracker%'
            AND LOWER(nome) NOT LIKE '%snack%' AND LOWER(nome) NOT LIKE '%bevanda%'
            AND LOWER(nome) NOT LIKE '%caffe%' AND LOWER(nome) NOT LIKE '%the%'
            AND LOWER(nome) NOT LIKE '%cereali%' AND LOWER(nome) NOT LIKE '%quinoa%'
            AND LOWER(nome) NOT LIKE '%lenticch%' AND LOWER(nome) NOT LIKE '%fagioli%'
            AND LOWER(nome) NOT LIKE '%acqua%'
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return await cur.fetchall()

async def update_minsan(db, product_id, minsan):
    await db.execute("UPDATE products SET minsan = ? WHERE id = ?", (minsan, product_id))

async def scrape_minsan(client, url):
    try:
        resp = await client.get(url, timeout=15.0, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return None
        # Try to find product__subtitleMinsan span
        match = re.search(r'product__subtitleMinsan[^>]*>([^<]+)</span>', resp.text)
        if match:
            minsan = match.group(1).strip()
            minsan = re.sub(r'^MINSAN:\s*', '', minsan, flags=re.IGNORECASE).strip()
            return minsan if minsan else None
        return None
    except Exception as e:
        return None

async def main():
    offset = 1500
    products = await get_products(offset)
    print(f"Batch 16 offset={offset}: got {len(products)} products to scrape")
    
    if not products:
        print("No products to process")
        return
    
    updated = 0
    minsan_found = 0
    errors = 0
    sample = []
    
    async with httpx.AsyncClient() as client:
        for i, row in enumerate(products):
            minsan = await scrape_minsan(client, row["url"])
            if minsan:
                minsan_found += 1
                async with aiosqlite.connect(DB_PATH) as db:
                    await update_minsan(db, row["id"], minsan)
                    await db.commit()
                updated += 1
                entry = {"id": row["id"], "nome": row["nome"], "minsan": minsan}
                sample.append(entry)
                print(f"[{i+1}/{len(products)}] id={row['id']} MINSAN={minsan}")
            else:
                errors += 1
                print(f"[{i+1}/{len(products)}] id={row['id']} NO MINSAN (url={row['url'][:80]})")
    
    print(f"\n=== DONE ===")
    print(f"Updated: {updated}")
    print(f"MINSAN found: {minsan_found}")
    print(f"Errors/no MINSAN: {errors}")
    print(f"\nSample (up to 5):")
    for s in sample[:5]:
        print(f"  id={s['id']}, nome={s['nome']}, minsan={s['minsan']}")

asyncio.run(main())