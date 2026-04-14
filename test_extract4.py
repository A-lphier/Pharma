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
found_any = False

for i, part in enumerate(parts):
    if 'application/ld+json' not in part:
        continue
    
    found_any = True
    # Extract content after type=...>
    # Find the first > after the script tag starts
    idx = part.find('>')
    if idx < 0:
        print(f"Part {i}: no > found")
        continue
    content_start = idx + 1
    end_idx = part.find('</script>')
    if end_idx < 0:
        print(f"Part {i}: no </script> found")
        continue
    content = part[content_start:end_idx]
    
    try:
        data = json.loads(content)
        print(f"Part {i}: JSON parsed OK, @type={data.get('@type', 'no type')}")
        if 'mainEntity' in data:
            me = data['mainEntity']
            print(f"  mainEntity @type: {me.get('@type', 'no type')}")
            if 'itemListElement' in me:
                items = me['itemListElement']
                print(f"  itemListElement: {len(items)} items")
                for item in items[:2]:
                    print(f"    [{item.get('@type')}] {item.get('name', 'NO NAME')[:60]}")
        elif isinstance(data.get('mainEntity'), list):
            print(f"  mainEntity is list with {len(data['mainEntity'])} items")
    except Exception as e:
        print(f"Part {i}: JSON error: {e}")
        print(f"  Content preview: {content[:200]}")

if not found_any:
    print("NO application/ld+json found in parts!")
    # Check the raw HTML for JSON-LD
    idx = html.find('application/ld+json')
    print(f"application/ld+json at: {idx}")
    if idx > 0:
        print(f"Context: {html[idx-50:idx+200]}")
