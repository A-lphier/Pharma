#!/usr/bin/env python3
"""
Scraper for salute.gov.it integratori database
Uses Playwright with SSL certificate bypass
"""

import asyncio
import re
import sqlite3
import json
from pathlib import Path

DB_PATH = '/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db'
OUTPUT_FILE = '/home/agent/.openclaw/workspace/solgar_salute_gov.json'

async def scrape_with_playwright():
    """Use Playwright for JS-rendered pages with SSL bypass"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed")
        return []
    
    results = []
    
    async with async_playwright() as p:
        # Launch with SSL bypass
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-web-security',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content',
                '--disable-setuid-sandbox',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        try:
            # Navigate to search page
            url = "https://salute.gov.it/portale/integratori/ricercaIntegratori.html"
            print(f"Navigating to {url}...")
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Wait a bit for JS
            await asyncio.sleep(2)
            
            print(f"Page title: {await page.title()}")
            
            # Try to find search input
            # Look for various search input patterns
            search_selectors = [
                'input[type="text"]',
                'input[name*="search"]',
                'input[id*="search"]',
                'input[placeholder*="cerca"]',
                'input[placeholder*="search"]',
                'input[placeholder*="integratori"]',
            ]
            
            search_input = None
            for selector in search_selectors:
                inputs = page.locator(selector)
                count = await inputs.count()
                if count > 0:
                    search_input = inputs.first
                    print(f"Found search input with selector: {selector}")
                    break
            
            if search_input:
                await search_input.fill('SOLGAR')
                await asyncio.sleep(1)
                
                # Find and click submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Cerca")',
                    'button:has-text("Ricerca")',
                ]
                
                for selector in submit_selectors:
                    btns = page.locator(selector)
                    if await btns.count() > 0:
                        await btns.first.click()
                        print(f"Clicked submit: {selector}")
                        break
                
                # Wait for results
                await asyncio.sleep(3)
                await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get page content
            content = await page.content()
            print(f"Page content length: {len(content)}")
            
            # Look for results table
            table = page.locator('table')
            if await table.count() > 0:
                rows = table.locator('tr')
                row_count = await rows.count()
                print(f"Table has {row_count} rows")
                
                for i in range(min(row_count, 200)):
                    row = rows[i]
                    cells = row.locator('td, th')
                    cell_count = await cells.count()
                    if cell_count > 0:
                        cell_texts = []
                        for j in range(cell_count):
                            text = await cells[j].text_content()
                            cell_texts.append(text.strip() if text else '')
                        
                        # Look for MINSAN (9 digits) in row
                        row_text = ' '.join(cell_texts)
                        minsan_match = re.search(r'\b\d{9}\b', row_text)
                        if minsan_match:
                            results.append({
                                'minsan': minsan_match.group(),
                                'nome': cell_texts[0] if cell_texts else '',
                                'row': row_text[:300]
                            })
            
            # Also look for any 9-digit codes anywhere on page
            all_minsans = re.findall(r'\b\d{9}\b', content)
            print(f"Found {len(all_minsans)} MINSAN codes on page")
            
            if not results and all_minsans[:5]:
                # Create results from all found MINSANs
                for m in all_minsans[:50]:
                    results.append({'minsan': m, 'source': 'page_scan'})
            
            # Save to file
            if results:
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Saved {len(results)} results to {OUTPUT_FILE}")
            
        finally:
            await browser.close()
    
    return results

def update_db_with_results(results):
    """Update integratori.db with scraped MINSAN data"""
    if not results:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    updated = 0
    for item in results:
        minsan = item.get('minsan', '')
        if len(minsan) == 9:
            cur.execute('''
                UPDATE products 
                SET minsan = ?
                WHERE (minsan IS NULL OR minsan = '')
                AND (LOWER(nome) LIKE '%solgar%' OR LOWER(azienda) LIKE '%solgar%')
            ''', (minsan,))
            if cur.rowcount > 0:
                updated += 1
    
    conn.commit()
    conn.close()
    return updated

if __name__ == '__main__':
    print("="*60)
    print("salute.gov.it Integratori Scraper (Playwright SSL bypass)")
    print("="*60)
    
    results = asyncio.run(scrape_with_playwright())
    
    if results:
        print(f"\nScraped {len(results)} results")
        
        # Try to update DB
        updated = update_db_with_results(results)
        print(f"Updated {updated} products in DB")
    else:
        print("\nNo results scraped")
