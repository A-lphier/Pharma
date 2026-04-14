import re, urllib.request, ssl

url = 'https://www.farmaciauno.it/integratori/benessere-donna/menopausa.html'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9',
})
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='replace')

print(f'HTML length: {len(html)}')

# Find Italfarmaco Flavia
idx = html.find('Italfarmaco Flavia Notte')
if idx >= 0:
    print(f'Found at index: {idx}')
    start = max(0, idx - 300)
    end = min(len(html), idx + 500)
    print(html[start:end])
    print('---')
else:
    print('Not found!')
    
# Search for "application/ld+json" 
count = html.count('application/ld+json')
print(f'\napplication/ld+json count: {count}')

# Find all script tags with JSON content
script_start = html.find('<script')
while script_start >= 0:
    script_end = html.find('</script>', script_start)
    if script_end < 0:
        break
    tag = html[script_start:script_end+9]
    if 'Italfarmaco' in tag or 'product' in tag.lower()[:100]:
        print(f'\nScript tag at {script_start}:')
        print(tag[:500])
        print('---')
    script_start = html.find('<script', script_end)
