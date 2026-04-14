#!/usr/bin/env python3
"""
Crawl www.farmaciauno.it for integratori alimentari.
Saves to integratori.db with fonte='farmaciauno'.
"""

import asyncio
import re
import sqlite3
import time
from playwright.async_api import async_playwright

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'
BASE_URL = 'https://www.farmaciauno.it'
LOG_EVERY = 50

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = 0")
    return conn

def save_product(conn, data):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO products (
            nome, azienda, categoria, ingredienti, dosaggio,
            modo_duso, indicazioni, url, fonte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('nome'),
        data.get('azienda'),
        data.get('categoria'),
        data.get('ingredienti'),
        data.get('dosaggio'),
        data.get('modo_duso'),
        data.get('indicazioni'),
        data.get('url'),
        'farmaciauno'
    ))
    conn.commit()
    return cur.rowcount > 0

def extract_nutritional_data(text):
    """Look for nutritional table / dose info in page text."""
    patterns = [
        r'(?i)apporto.*?(?:per\s*(?:capsula|compressa|bustina|cpr|caps|cp|tbl|flacone|dose|dose\s*giornaliera|dose\s*max|daily|dose).*?(?:\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal|UI|%|\w+))+.*?)(?=\n\n|\n\n\n|##|\Z)',
        r'(?i)dosaggio.*?(?:\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal|UI|%).*?)+',
        r'(?i)ingredienti.*?(?:\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal).*?)+',
        r'(?i)tabella.*?nutri.*?(?:\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal|%).*?)+',
        r'(?i)valori.*?nutri.*?(?:\d+[.,]?\d*\s*(?:mg|g|mcg|µg|kcal|%).*?)+',
    ]
    results = []
    for p in patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            snippet = m.group(0)[:500]
            if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', '%']):
                results.append(snippet)
    return ' | '.join(results[:2])

async def extract_product_details(page, url):
    """Extract product details from a product page."""
    try:
        await page.goto(url, timeout=20000, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  ERROR loading {url}: {e}")
        return None

    text = ''
    try:
        text = await page.inner_text('body')
    except:
        pass

    # Product name
    title = ''
    try:
        title = await page.inner_text('h1')
    except:
        try:
            title_el = await page.query_selector('h1')
            if title_el:
                title = await title_el.inner_text()
        except:
            pass

    if not title:
        title = url.split('/')[-1].replace('-', ' ').replace('_', ' ')

    # Category (breadcrumb or sidebar)
    category = ''
    try:
        breadcrumb = await page.inner_text('[class*="breadcrumb"]')
        category = breadcrumb
    except:
        pass

    # Company/Brand
    azienda = ''
    brand_patterns = [
        r'(?i)marchio[:\s]*([^\n<]+)',
        r'(?i)azienda[:\s]*([^\n<]+)',
        r'(?i)prodotto\s+da[:\s]*([^\n<]+)',
        r'(?i)by\s+([^\n<]+)',
    ]
    for p in brand_patterns:
        m = re.search(p, text)
        if m:
            azienda = m.group(1).strip()[:200]
            break

    # Try meta tags
    if not azienda:
        try:
            brand = await page.get_attribute('meta[property="product:brand"]', 'content')
            if brand:
                azienda = brand
        except:
            pass

    # Ingredients
    ingredienti = ''
    ing_patterns = [
        r'(?i)ingredienti[:\s]*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|dose|modo|avvert|conser)',
        r'(?i)principi\s*attivi[:\s]*([^\n]+(?:\n[^\n]+)*?)',
        r'(?i)composizione[:\s]*([^\n]+(?:\n[^\n]+)*?)',
    ]
    for p in ing_patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            ingredienti = m.group(0)[:1000].strip()
            break

    # Nutritional data / Dosage
    dosaggio = extract_nutritional_data(text)
    if not dosaggio:
        # Try specific tables
        try:
            table_texts = []
            tables = await page.query_selector_all('table')
            for tbl in tables:
                tbl_txt = await tbl.inner_text()
                if any(x in tbl_txt.lower() for x in ['mg', 'g ', 'kcal', 'dose', 'apporto']):
                    table_texts.append(tbl_txt[:500])
            if table_texts:
                dosaggio = ' | '.join(table_texts[:2])
        except:
            pass

    # Usage instructions
    modo_duso = ''
    uso_patterns = [
        r'(?i)modo\s*d[\']?uso[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
        r'(?i)posologia[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
        r'(?i)come\s*assumere[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
        r'(?i)utilizzo[:\s]*([^\n]+(?:\n[^\n]+){0,3})',
    ]
    for p in uso_patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            modo_duso = m.group(0)[:500].strip()
            break

    # Indicazioni
    indicazioni = ''
    ind_patterns = [
        r'(?i)indicazioni[:\s]*([^\n]+(?:\n[^\n]+){0,5})',
        r'(?i)benefici[:\s]*([^\n]+(?:\n[^\n]+){0,5})',
        r'(?i)proprietà[:\s]*([^\n]+(?:\n[^\n]+){0,5})',
    ]
    for p in ind_patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            indicazioni = m.group(0)[:500].strip()
            break

    return {
        'nome': title.strip()[:500],
        'azienda': azienda.strip()[:200],
        'categoria': category.strip()[:500],
        'ingredienti': ingredienti.strip()[:2000],
        'dosaggio': dosaggio.strip()[:2000] if dosaggio else '',
        'modo_duso': modo_duso.strip()[:1000] if modo_duso else '',
        'indicazioni': indicazioni.strip()[:1000] if indicazioni else '',
        'url': url,
    }

async def get_product_links_from_list(page, url):
    """Extract all product links from a listing page."""
    try:
        await page.goto(url, timeout=20000, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"ERROR loading list {url}: {e}")
        return []

    links = set()
    try:
        # Find product links
        anchors = await page.query_selector_all('a[href*="/prodotto/"], a[href*="/integratori/"], a[href*="/prodotti/"]')
        for a in anchors:
            href = await a.get_attribute('href')
            if href and '/prodotti/' in href or '/prodotto/' in href or '/integratori/' in href:
                if href.startswith('/'):
                    href = BASE_URL + href
                if 'farmaciauno.it' in href:
                    links.add(href.split('?')[0].split('#')[0])
    except:
        pass

    # Try pagination
    next_pages = set()
    try:
        next_anchors = await page.query_selector_all('a[class*="next"], a[class*="page"], a[class*="pagin"]')
        for a in next_anchors:
            href = await a.get_attribute('href')
            if href:
                if href.startswith('/'):
                    href = BASE_URL + href
                next_pages.add(href.split('?')[0])
    except:
        pass

    return list(links), list(next_pages)

async def main():
    print("Starting FarmaciaUno crawler...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'it-IT,it;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        )
        page = await context.new_page()

        # Step 1: Test site access
        print("Step 1: Testing site access...")
        try:
            resp = await page.goto(BASE_URL, timeout=20000)
            print(f"  Site responded with status: {resp.status}")
            await page.wait_for_timeout(1000)
            title = await page.title()
            print(f"  Page title: {title}")
        except Exception as e:
            print(f"  ERROR accessing site: {e}")
            print("Site blocked or unreachable, aborting.")
            return

        # Step 2: Navigate to integratori section
        print("Step 2: Finding integratori section...")
        integratori_urls = [
            BASE_URL + '/integratori',
            BASE_URL + '/integratori-alimentari',
            BASE_URL + '/integratori/alimentari',
            BASE_URL + '/categories/integratori',
            BASE_URL + '/c/integratori',
        ]

        selected_url = None
        for test_url in integratori_urls:
            print(f"  Testing: {test_url}")
            try:
                resp = await page.goto(test_url, timeout=15000)
                if resp and resp.status < 400:
                    await page.wait_for_timeout(1500)
                    text = await page.inner_text('body')
                    if 'integratori' in text.lower() or 'supplement' in text.lower():
                        selected_url = test_url
                        print(f"  SUCCESS: {test_url}")
                        break
            except:
                pass

        if not selected_url:
            # Try sitemap
            print("  Trying sitemap.xml...")
            try:
                resp = await page.goto(BASE_URL + '/sitemap.xml', timeout=15000)
                if resp and resp.status < 400:
                    text = await page.inner_text('body')
                    integratori_sitemap = re.findall(r'(?i)integratori[^\n"]+\.xml|sitemap[^\n"]*integratori[^\n"]*\.xml', text)
                    if integratori_sitemap:
                        print(f"  Found sitemap links: {integratori_sitemap[:3]}")
            except Exception as e:
                print(f"  Sitemap error: {e}")
            
            # Fallback: search for integratori links on homepage
            print("  Searching homepage for integratori links...")
            try:
                await page.goto(BASE_URL, timeout=15000)
                await page.wait_for_timeout(1000)
                links = await page.query_selector_all('a[href*="integratori"]')
                for link in links[:10]:
                    href = await link.get_attribute('href')
                    txt = await link.inner_text()
                    print(f"    Found link: {href} -> {txt[:50]}")
            except:
                pass

            selected_url = integratori_urls[0]

        print(f"\nUsing integratori URL: {selected_url}")

        # Step 3: Collect ALL product links from listing pages
        print("Step 3: Collecting product links...")
        all_product_links = set()
        visited_list_pages = set()
        pages_to_visit = [selected_url]
        iteration = 0
        max_iterations = 100

        while pages_to_visit and iteration < max_iterations:
            iteration += 1
            list_url = pages_to_visit.pop(0)
            if list_url in visited_list_pages:
                continue
            visited_list_pages.add(list_url)
            print(f"  List page [{iteration}]: {list_url}")
            print(f"    Total product links so far: {len(all_product_links)}")

            links, next_pages = await get_product_links_from_list(page, list_url)
            all_product_links.update(links)
            print(f"    Found {len(links)} links on this page, {len(next_pages)} next pages")

            for np in next_pages:
                if np not in visited_list_pages:
                    pages_to_visit.append(np)

            await asyncio.sleep(1)

        all_product_links = list(all_product_links)
        print(f"\nTotal product links collected: {len(all_product_links)}")

        # Step 4: Extract details for each product
        print("Step 4: Extracting product details...")
        conn = get_db()
        saved_count = 0
        skipped_nutrition = 0

        for i, url in enumerate(all_product_links, 1):
            if i % LOG_EVERY == 0:
                print(f"  Processing {i}/{len(all_product_links)} (saved: {saved_count}, skipped: {skipped_nutrition})")

            data = await extract_product_details(page, url)

            if data is None:
                continue

            # Only save if it has nutritional data
            if data.get('dosaggio'):
                save_product(conn, data)
                saved_count += 1
            else:
                skipped_nutrition += 1
                if skipped_nutrition <= 5:
                    print(f"    SKIP (no nutrition data): {url}")

            if i % 100 == 0:
                await asyncio.sleep(2)  # Be polite
            else:
                await asyncio.sleep(0.5)

        conn.close()
        print(f"\nDone! Saved: {saved_count}, Skipped (no nutrition): {skipped_nutrition}, Total: {len(all_product_links)}")

if __name__ == '__main__':
    asyncio.run(main())
