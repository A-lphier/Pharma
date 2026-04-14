#!/usr/bin/env python3
"""Async scraper for superfarma products - batch 10 (offset 900)"""

import asyncio
import sqlite3
import re
import html as html_module
from typing import Optional
from dataclasses import dataclass

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.run(["pip3", "install", "aiohttp", "-q"])
    import aiohttp

@dataclass
class ProductData:
    id: int
    forma_farmaceutica: Optional[str] = None
    minsan: Optional[str] = None
    ingredienti: Optional[str] = None
    dosaggio: Optional[str] = None

def clean_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return None
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    text = html_module.unescape(text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else None

def extract_field(html: str, pattern: str, group_idx: int = 1, max_len: int = 500) -> Optional[str]:
    """Extract and clean a field from HTML."""
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if m:
        val = clean_html(m.group(group_idx))
        if val and len(val) > 1:
            return val[:max_len]
    return None

async def fetch_product(session: aiohttp.ClientSession, product_id: int, url: str, semaphore: asyncio.Semaphore) -> ProductData:
    """Fetch a single product page and extract data."""
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return ProductData(id=product_id)
                
                html = await resp.text()
                
                minsan = extract_field(html, r'MINSAN\s*[:\-]?\s*([A-Z0-9\-]+)', max_len=50)
                ingredienti = extract_field(html, r'(?:ingredienti|principi attivi)[:\s]*([^.<\n]{20,500})', max_len=500)
                dosaggio = extract_field(html, r'(?:dosaggio|quantità|dose)[:\s]*([^.<\n]{5,200})', max_len=200)
                
                # Try more general ingredienti extraction
                if not ingredienti:
                    # Look for ingredient list in description
                    ingr_block = re.search(r'ingredienti\s*</[^>]+>\s*<[^>]+>([^<]{20,})', html, re.IGNORECASE)
                    if ingr_block:
                        ingredienti = clean_html(ingr_block.group(1))[:500]
                
                return ProductData(
                    id=product_id,
                    forma_farmaceutica=None,
                    minsan=minsan,
                    ingredienti=ingredienti,
                    dosaggio=dosaggio
                )
        except Exception as e:
            return ProductData(id=product_id)

async def main():
    conn = sqlite3.connect('integratori.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT id, nome, url, fonte 
        FROM products 
        WHERE (dosaggio IS NULL OR dosaggio = '') 
        AND (ingredienti IS NULL OR ingredienti = '')
        AND (minsan IS NULL OR minsan = '')
        AND url IS NOT NULL AND url != ''
        AND url_stato = 'live'
        LIMIT 100 OFFSET 900
    ''')
    products = cur.fetchall()
    conn.close()
    
    print(f"Processing {len(products)} products...")
    
    semaphore = asyncio.Semaphore(15)
    async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    }) as session:
        tasks = [
            fetch_product(session, p[0], p[2], semaphore)
            for p in products
        ]
        results = await asyncio.gather(*tasks)
    
    updated = 0
    skipped = 0
    updated_ids = []
    
    conn = sqlite3.connect('integratori.db')
    cur = conn.cursor()
    
    for pd in results:
        has_data = any([pd.forma_farmaceutica, pd.minsan, pd.ingredienti, pd.dosaggio])
        
        if has_data:
            cur.execute('''
                UPDATE products 
                SET forma_farmaceutica = ?, minsan = ?, ingredienti = ?, dosaggio = ?
                WHERE id = ?
            ''', (pd.forma_farmaceutica, pd.minsan, pd.ingredienti, pd.dosaggio, pd.id))
            updated += 1
            updated_ids.append(pd.id)
        else:
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n=== BATCH 10 RESULTS (offset 900) ===")
    print(f"Total processed: {len(products)}")
    print(f"Updated with data: {updated}")
    print(f"No data found: {skipped}")
    
    if updated > 0:
        conn = sqlite3.connect('integratori.db')
        cur = conn.cursor()
        placeholders = ','.join('?' * len(updated_ids[:20]))
        cur.execute(f'''
            SELECT id, nome, forma_farmaceutica, minsan, ingredienti, dosaggio
            FROM products
            WHERE id IN ({placeholders})
        ''', updated_ids[:20])
        print("\nSample updated products:")
        for row in cur.fetchall():
            print(f"  ID {row[0]}: {row[1][:40]}")
            print(f"    forma={row[2]}, minsan={row[3]}")
            print(f"    ingrediente={str(row[4])[:80]}")
            print(f"    dosaggio={row[5]}")
        conn.close()

if __name__ == '__main__':
    asyncio.run(main())