import re, json, urllib.request, ssl, sqlite3

url = 'https://www.farmaciauno.it/integratori/benessere-donna/menopausa.html'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='replace')

print(f'HTML length: {len(html)}')

# The script tag looks like: <script type="application/ld+json">
# The attribute value contains the type WITH quotes, then >
pattern = r'<script[^>]*?\btype=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
matches = re.findall(pattern, html, re.DOTALL)
print(f'Found {len(matches)} JSON-LD blocks')

all_products = []
all_itemlist_urls = []

for i, m in enumerate(matches):
    try:
        data = json.loads(m)
        if isinstance(data, dict):
            t = data.get('@type', '')
            if isinstance(t, list):
                types = t
            else:
                types = [t]
            
            print(f'Block {i}: {types}')
            
            if 'Product' in types:
                name = data.get('name', '')
                print(f'  *** PRODUCT: {name[:60]}')
                all_products.append(data)
            
            if 'ItemList' in types:
                items = data.get('itemListElement', [])
                print(f'  ItemList: {len(items)} items')
                for item in items[:3]:
                    url_i = item.get('url', '')
                    if url_i:
                        all_itemlist_urls.append(url_i)
            
            if '@graph' in data:
                graph = data['@graph']
                print(f'  @graph: {len(graph)} items')
                for g in graph:
                    gt = g.get('@type', '')
                    if isinstance(gt, list):
                        gt = gt
                    gn = g.get('name', '')
                    print(f'    [{gt}] {str(gn)[:60]}')
                    if 'Product' in (gt if isinstance(gt, list) else [gt]):
                        all_products.append(g)
        elif isinstance(data, list):
            print(f'Block {i}: list of {len(data)} items')
    except Exception as e:
        print(f'Block {i} error: {e}')

print(f'\nTotal products from JSON-LD: {len(all_products)}')
print(f'Total URLs from ItemList: {len(all_itemlist_urls)}')
if all_itemlist_urls:
    print(f'Sample URLs:')
    for u in all_itemlist_urls[:5]:
        print(f'  {u}')
