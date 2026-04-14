#!/usr/bin/env python3
"""Explore FarmaciaUno site structure with Playwright."""

import asyncio
import re
from playwright.async_api import async_playwright

BASE_URL = 'https://www.farmaciauno.it'

async def explore():
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

        # Check the integratori main page
        print("=== INTEGRATORI MAIN PAGE ===")
        await page.goto(BASE_URL + '/integratori', timeout=20000)
        await page.wait_for_timeout(2000)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")
        
        # Get all links from this page
        all_links = await page.query_selector_all('a')
        product_links = []
        category_links = []
        
        for link in all_links:
            href = await link.get_attribute('href')
            if not href:
                continue
            text = await link.inner_text()
            text = text.strip()[:80]
            
            if '/prodotti/' in href or '/prodotto/' in href or '/integratori/' in href:
                full_url = href if href.startswith('http') else BASE_URL + href
                # Check if it's a product (usually has product name with dashes, not just category names)
                if 'prodotti' in href and ('.html' in href or '/p/' in href):
                    product_links.append((full_url, text))
                else:
                    category_links.append((full_url, text))
        
        print(f"\nCategory links ({len(category_links)}):")
        for url, text in category_links[:20]:
            print(f"  {url} -> {text}")
        
        print(f"\nProduct links ({len(product_links)}):")
        for url, text in product_links[:20]:
            print(f"  {url} -> {text}")
        
        # Try to get product links from grid items
        print("\n=== Looking for product grid items ===")
        grid_items = await page.query_selector_all('[class*="product"], [class*="item"], [class*="card"]')
        print(f"Found {len(grid_items)} grid items")
        
        for item in grid_items[:5]:
            item_html = await item.inner_html()
            # Extract links from item
            links_in_item = await item.query_selector_all('a')
            for a in links_in_item:
                href = await a.get_attribute('href')
                if href:
                    print(f"  Item link: {href}")
        
        # Look for pagination
        print("\n=== Looking for pagination ===")
        pagination = await page.query_selector_all('[class*="pagin"], [class*="page"], [class*="next"]')
        for p_el in pagination:
            href = await p_el.get_attribute('href')
            text = await p_el.inner_text()
            print(f"  Pagination: {href} -> {text.strip()[:50]}")
        
        # Try to find products on second page
        print("\n=== Checking page 2 of integratori ===")
        try:
            # Try common pagination patterns
            for test_url in [
                BASE_URL + '/integratori?page=2',
                BASE_URL + '/integratori?p=2',
                BASE_URL + '/integratori.html?page=2',
            ]:
                await page.goto(test_url, timeout=15000)
                await page.wait_for_timeout(1500)
                links = await page.query_selector_all('a[href]')
                found_prods = []
                for a in links:
                    href = await a.get_attribute('href')
                    if href and '/prodotti/' in href:
                        found_prods.append(href)
                if found_prods:
                    print(f"  {test_url}: found {len(found_prods)} product links")
                    for lp in found_prods[:5]:
                        print(f"    {lp}")
                    break
                else:
                    print(f"  {test_url}: no product links found")
        except Exception as e:
            print(f"  Error: {e}")

        # Try sitemap
        print("\n=== Checking sitemap ===")
        try:
            await page.goto(BASE_URL + '/sitemap.xml', timeout=15000)
            await page.wait_for_timeout(2000)
            text = await page.inner_text('body')
            # Look for product-like URLs in sitemap
            prod_urls = re.findall(r'https?://[^\s<>"]+\.html', text)
            print(f"Found {len(prod_urls)} .html URLs in sitemap")
            for u in prod_urls[:10]:
                print(f"  {u}")
        except Exception as e:
            print(f"Sitemap error: {e}")

        # Try to find specific product page structure
        print("\n=== Looking for product URL patterns ===")
        await page.goto(BASE_URL + '/integratori', timeout=20000)
        await page.wait_for_timeout(2000)
        
        all_anchors = await page.query_selector_all('a')
        hrefs = []
        for a in all_anchors:
            href = await a.get_attribute('href')
            if href:
                hrefs.append(href)
        
        # Find unique patterns
        patterns = {}
        for h in hrefs:
            # Extract the path pattern
            if '/integratori/' in h:
                parts = h.split('/')
                if len(parts) >= 3:
                    pattern = '/'.join(parts[2:4]) if len(parts) > 3 else '/'.join(parts[2:])
                    patterns[pattern] = patterns.get(pattern, 0) + 1
        
        print("URL path patterns in /integratori:")
        for pat, count in sorted(patterns.items(), key=lambda x: -x[1])[:15]:
            print(f"  {pat}: {count}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(explore())
