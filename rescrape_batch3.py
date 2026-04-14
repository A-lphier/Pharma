#!/usr/bin/env python3
"""Rescrape batch 3 - corrected extraction for superfarma Shopify pages"""
import asyncio
import re
import sqlite3
import aiohttp
from html import unescape

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'

def extract_fields(html):
    """Extract forma_farmaceutica, minsan, ingredienti, dosaggio from superfarma HTML"""
    forma = None
    minsan = None
    ingredienti = None
    dosaggio = None

    # ── 1. MinSan / AIC ──────────────────────────────────────────────
    # Italian pharma code: 9-10 digits, may be prefixed
    for pat in [
        r'(?:AIC|a\.i\.c\.)\s*[:,.]?\s*([0-9]{9,10})',
        r'(?:codice\s*min(?:isteriale)?\s*[:,.]?\s*)([0-9]{9,10})',
        r'(?:min\.?\s*san)\s*[:,.]?\s*([0-9]{9,10})',
    ]:
        m = re.search(pat, html, re.I)
        if m:
            raw = re.sub(r'[\.\s\-/]', '', m.group(1)).strip()
            if re.match(r'^[0-9]{9}$', raw):
                raw = '0' + raw
            if re.match(r'^[0-9]{10}$', raw):
                minsan = raw
                break

    # ── 2. Forma farmaceutica ─────────────────────────────────────────
    # Pattern: "<strong>Formato</strong><br>NN <Type>
    # Examples: "30 Capsule", "60 compresse", "10 flaconcini"
    m = re.search(r'<strong>Formato</strong>\s*<br\s*/?>\s*([^\n<]+)', html, re.I)
    if m:
        raw = m.group(1).strip()
        # Remove trailing "Cod. ..." etc
        raw = re.sub(r'\s+Cod\..*$', '', raw, flags=re.I).strip()
        # Normalize: drop leading count → keep only the unit type
        # "30 Capsule" → "Capsule", "250g" → skip (not a pharma form)
        count_m = re.match(r'^(\d+)\s+(.{3,30})$', raw)
        if count_m:
            forma = count_m.group(2).strip().rstrip('s').rstrip('.')
        elif re.match(r'^\d+\s*g?(?:\s|$)', raw):
            forma = None  # weight, not a form
        else:
            forma = raw.strip().rstrip('s').rstrip('.')

    # ── 3. Ingredienti ────────────────────────────────────────────────
    m = re.search(r'<strong>Ingredienti</strong>\s*<br\s*/?>\s*([^\n<]{20,800])', html, re.I)
    if m:
        ingredienti = m.group(1).strip()
        ingredienti = unescape(ingredienti)
        # Clean HTML tags
        ingredienti = re.sub(r'<[^>]+>', '', ingredienti)
        ingredienti = re.sub(r'\s+', ' ', ingredienti).strip()
        if len(ingredienti) > 500:
            ingredienti = ingredienti[:500]

    # ── 4. Dosaggio ───────────────────────────────────────────────────
    # Look for dosage/quantity per unit info
    for label in ['Dosaggio', 'Dose', 'Quantità']:
        m = re.search(rf'<strong>{label}</strong>\s*<br\s*/?>\s*([^\n<]{{5,200}})', html, re.I)
        if m:
            dosaggio = m.group(1).strip()
            dosaggio = unescape(dosaggio)
            dosaggio = re.sub(r'<[^>]+>', '', dosaggio)
            dosaggio = re.sub(r'\s+', ' ', dosaggio).strip()
            if len(dosaggio) > 150:
                dosaggio = dosaggio[:150]
            break

    return forma, minsan, ingredienti, dosaggio


async def fetch_and_parse(session, product):
    pid, nome, url, fonte = product
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 404:
                return pid, nome, url, 'dead', None, None, None, None
            if resp.status != 200:
                return pid, nome, url, f'http_{resp.status}', None, None, None, None
            html = await resp.text(errors='ignore')
            forma, minsan, ingredienti, dosaggio = extract_fields(html)
            return pid, nome, url, 'ok', forma, minsan, ingredienti, dosaggio
    except asyncio.TimeoutError:
        return pid, nome, url, 'timeout', None, None, None, None
    except Exception as e:
        return pid, nome, url, f'error', None, None, None, None


async def main():
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
        LIMIT 100 OFFSET 200
    """)
    products = cur.fetchall()
    conn.close()

    print(f"Batch 3: {len(products)} products", flush=True)

    connector = aiohttp.TCPConnector(limit=8, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_and_parse(session, p) for p in products]
        results = await asyncio.gather(*tasks)

    updated = 0
    errors = 0
    conn2 = sqlite3.connect(DB_PATH)
    cu = conn2.cursor()

    for r in results:
        pid, nome, url, status, forma, minsan, ingredienti, dosaggio = r

        if status == 'dead':
            cu.execute("UPDATE products SET url_stato='dead' WHERE id=?", (pid,))
            print(f"  DEAD [{pid}] {str(nome)[:40]}", flush=True)
            continue

        if status not in ('ok', None):
            errors += 1
            print(f"  ERR [{pid}] {str(nome)[:40]} | {status}", flush=True)
            continue

        cu.execute("""
            UPDATE products SET forma_farmaceutica=?, minsan=?, ingredienti=?, dosaggio=?
            WHERE id=?
        """, (forma, minsan, ingredienti, dosaggio, pid))

        if forma or minsan or ingredienti or dosaggio:
            updated += 1
            d_preview = str(dosaggio)[:40] if dosaggio else '-'
            i_preview = str(ingredienti)[:40] if ingredienti else '-'
            print(f"  [+{pid}] {str(nome)[:40]:40s} | forma={forma} | ing={i_preview}", flush=True)

    conn2.commit()
    conn2.close()
    print(f"\nDone. Updated {updated}/{len(products)}, {errors} errors.", flush=True)


if __name__ == '__main__':
    asyncio.run(main())
