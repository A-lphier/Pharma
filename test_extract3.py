import re, json, urllib.request, ssl

url = 'https://www.farmaciauno.it/integratori/benessere-donna/menopausa.html'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='replace')

# Find JSON-LD blocks with a more robust approach
# Split by <script tag, then find each one
parts = html.split('<script')
products_found = []

for part in parts:
    if 'application/ld+json' not in part:
        continue
    # Extract content after type=...>
    idx = part.find('>')
    if idx < 0:
        continue
    content_start = idx + 1
    end_idx = part.find('</script>')
    if end_idx < 0:
        continue
    content = part[content_start:end_idx]
    
    try:
        data = json.loads(content)
        # Look for OfferCatalog with itemListElement
        if isinstance(data, dict):
            main_entity = data.get('mainEntity', {})
            if main_entity.get('@type') == 'OfferCatalog' or (isinstance(main_entity, list)):
                if isinstance(main_entity, list):
                    items = main_entity
                else:
                    items = main_entity.get('itemListElement', [])
                for item in items:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        name = item.get('name', '')
                        desc = item.get('description', '')
                        # Clean HTML
                        desc_clean = re.sub(r'<[^>]+>', ' ', desc)
                        desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
                        
                        brand = item.get('brand', {})
                        if isinstance(brand, dict):
                            brand = brand.get('name', '')
                        manufacturer = item.get('manufacturer', {})
                        if isinstance(manufacturer, dict):
                            manufacturer = manufacturer.get('name', '')
                        
                        azienda = brand or manufacturer
                        category = item.get('category', '')
                        product_url = item.get('url', '')
                        
                        # Extract nutritional data
                        dosaggio = extract_nutritional(desc_clean)
                        modo_duso = extract_modo_duso(desc_clean)
                        ingredienti = extract_ingredienti(desc_clean)
                        
                        products_found.append({
                            'nome': name[:500],
                            'azienda': str(azienda)[:200],
                            'categoria': category[:500],
                            'ingredienti': ingredienti[:2000],
                            'dosaggio': dosaggio[:2000],
                            'modo_duso': modo_duso[:1000],
                            'indicazioni': desc_clean[:1000],
                            'url': product_url,
                        })
                        
                        if len(products_found) <= 3:
                            print(f"Found: {name[:60]}")
                            print(f"  Brand: {azienda}")
                            print(f"  URL: {product_url[:80]}")
                            print(f"  Dosaggio: {dosaggio[:100]}")
                            print()
    except Exception as e:
        pass

print(f"\nTotal products extracted: {len(products_found)}")

def extract_nutritional(text):
    patterns = [
        r'(?i)composizione[:\s]*[^\n]{0,500}',
        r'(?i)apporto[:\s]*[^\n]{0,500}',
        r'(?i)tenori[:\s]*[^\n]{0,500}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            snippet = m.group(0)
            if any(x in snippet.lower() for x in ['mg', 'g ', 'mcg', 'µg', 'kcal', 'vnr']):
                return snippet
    return ''

def extract_modo_duso(text):
    patterns = [
        r'(?i)modo\s*d[\']?uso[:\s]*[^\n]{0,300}',
        r'(?i)posologia[:\s]*[^\n]{0,300}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''

def extract_ingredienti(text):
    patterns = [
        r'(?i)ingredienti[:\s]*[^\n]{0,500}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)[:500]
    return ''
