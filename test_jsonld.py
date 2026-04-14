import sys, re, json
import urllib.request
import ssl

url = 'https://www.farmaciauno.it/integratori/benessere-donna/menopausa.html'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='replace')

print(f"HTML length: {len(html)}")

for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL):
    try:
        data = json.loads(m.group(1))
        if isinstance(data, dict):
            t = data.get('@type', '')
            if t == 'ItemList':
                items = data.get('itemListElement', [])
                print(f'ItemList: {len(items)} items')
                for item in items[:3]:
                    print(f'  {item.get("url", "NO URL")} -> {item.get("name", "NO NAME")[:60]}')
            elif t == 'Product':
                print(f'Product: {data.get("name", "NO NAME")[:60]}')
                desc = data.get('description', '')[:200]
                print(f'  Desc: {desc}')
            elif isinstance(t, list) and 'ItemList' in t:
                items = data.get('itemListElement', [])
                print(f'ItemList (list): {len(items)} items')
                for item in items[:3]:
                    print(f'  {item.get("url", "NO URL")} -> {item.get("name", "NO NAME")[:60]}')
            if '@graph' in data:
                graph = data['@graph']
                print(f'@graph: {len(graph)} items')
                for g in graph[:5]:
                    gt = g.get('@type', 'unknown')
                    gn = str(g.get('name', g.get('url', '')))[:60]
                    print(f'  [{gt}] {gn}')
        elif isinstance(data, list):
            print(f'JSON-LD array: {len(data)} items')
            for d in data[:3]:
                print(f'  {d.get("@type", "no type")}: {str(d.get("name", ""))[:60]}')
    except Exception as e:
        print(f'JSON error: {e}')
