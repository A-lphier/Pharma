#!/usr/bin/env python3
"""
IntegrAction API Server - reads from Supabase (vmammjkauepeeiylnueh)
"""
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

SUPABASE_URL = "https://vmammjkauepeeiylnueh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZtYW1tamthdWVwZWVpeWxudWVoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjA3MDQ4NSwiZXhwIjoyMDkxNjQ2NDg1fQ.TDveBcTklfNhSjDfsBEyplrb8FcydznMLs60hIs9qaY"

app = Flask(__name__)
CORS(app)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def clean_value(v):
    if v is None:
        return None
    if isinstance(v, str) and len(v) > 10000:
        v = v[:10000]
    return v if v != 'null' else None

def get_count(query_params):
    headers = {**HEADERS, 'Prefer': 'count=exact'}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?{query_params}", headers=headers, timeout=10)
    if r.status_code not in (200, 206):
        return 0
    content_range = r.headers.get('content-range', '')
    if '/' in content_range:
        try:
            return int(content_range.split('/')[-1])
        except:
            pass
    return len(r.json())

# Simple in-memory cache for stats
_stats_cache = None
_stats_cache_time = 0

@app.route('/stats')
def stats():
    global _stats_cache, _stats_cache_time
    import time
    
    if _stats_cache and (time.time() - _stats_cache_time) < 300:
        return jsonify(_stats_cache)
    
    total = get_count('select=id')
    
    fields = ['nome','azienda','forma_farmaceutica','categoria','confezione',
              'utilizzazioni','modo_duso','ingredienti','dosaggio','avvertenze',
              'minsan','prezzo','fonte']
    
    completezza = {}
    for f in fields:
        cnt = get_count(f'{f}=not.is.null&select={f}')
        completezza[f] = {'count': cnt, 'pct': round(100*cnt/total, 1) if total > 0 else 0}
    
    result = {'total': total, 'completezza': completezza}
    _stats_cache = result
    _stats_cache_time = time.time()
    return jsonify(result)

@app.route('/search')
def search():
    q = request.args.get('q', '')
    limit = min(int(request.args.get('limit', 20)), 100)
    offset = int(request.args.get('offset', 0))
    
    cols = "id,nome,azienda,categoria,modo_duso,ingredienti,dosaggio,avvertenze,minsan,fonte,prezzo,forma_farmaceutica"
    
    if q:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?select={cols}"
            f"&or=(nome.ilike.%25{q}%25,azienda.ilike.%25{q}%25,ingredienti.ilike.%25{q}%25)"
            f"&limit={limit}&offset={offset}",
            headers=HEADERS, timeout=10
        )
    else:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?select={cols}&limit={limit}&offset={offset}",
            headers=HEADERS, timeout=10
        )
    
    if r.status_code != 200:
        return jsonify({'error': r.text}), r.status_code
    
    rows = r.json()
    return jsonify([{k: clean_value(v) for k, v in row.items()} for row in rows])

@app.route('/product/<product_id>')
def product(product_id):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
        headers=HEADERS, timeout=10
    )
    if r.status_code != 200 or not r.json():
        return jsonify({})
    row = r.json()[0]
    return jsonify({k: clean_value(v) for k, v in row.items()})

@app.route('/categories')
def categories():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/rpc/get_categories",
        headers=HEADERS, timeout=10
    )
    if r.status_code != 200:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?categoria=not.is.null&select=categoria",
            headers={**HEADERS, "Accept": "application/json"}, timeout=10
        )
        cats = {}
        for row in r.json():
            c = row.get('categoria')
            if c:
                cats[c] = cats.get(c, 0) + 1
        return jsonify([{'categoria': k, 'count': v} for k, v in sorted(cats.items(), key=lambda x: -x[1])[:50]])
    return jsonify(r.json())

@app.route('/aziende')
def aziende():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?azienda=not.is.null&select=azienda",
        headers={**HEADERS, "Accept": "application/json"}, timeout=10
    )
    az = {}
    for row in r.json():
        a = row.get('azienda')
        if a:
            az[a] = az.get(a, 0) + 1
    return jsonify([{'azienda': k, 'count': v} for k, v in sorted(az.items(), key=lambda x: -x[1])[:50]])

@app.route('/search/ai', methods=['POST'])
def search_ai():
    body = request.get_json(force=True)
    query = (body.get('q') or '').strip()
    if not query:
        return jsonify({'error': 'query mancante'}), 400

    MINIMAX_KEY = 'sk-cp-fEvjtEHLo5X-8KKNtLQvZfCvs_N-fL7yxLZbTNMXyX4O1Ha94esFXopqVEiFLZAzUEiVY4nIInp8Gk7hRzR1zqAONwy6lNRyvFp9AZvv4P_Zk5AWPf-_5zc'

    prompt = f"""L'utente cerca integratori alimentari con questa richiesta:
"{query}"

Estrai dal testo:
1. KEYWORD PRINCIPALE — ingrediente attivo principale (es. polase, magnesio, rodiola)
2. KEYWORD SECONDARIE — altri composti richiesti (es. aminoacidi, vitamina b, ferro)
3. CATEGORIA se menzionata
4. FONTE se specificata

Rispondi SOLO con JSON valido:
{{"primary": "keyword principale", "secondary": ["lista keyword secondarie"], "categoria": "null o categoria", "fonte": "null o fonte"}}

REGOLE CRITICHE:
- primary E secondary DEVONO comparire entrambi nei risultati (ricerca AND)
- Stessa marca/linea di product NON è sufficiente se manca l'ingrediente
- Per "aminoacidi" cerca: taurina, carnitina, glutammina, aspartico, cisteina, leucina, bcaa
- Per "vitamina b" cerca: b1, b2, b6, b12, niacina, folico, pantotenico
- Per "polase" cerca: potassio + magnesio insieme"""

    try:
        mr = requests.post(
            'https://api.minimax.io/anthropic/v1/messages',
            headers={'Authorization': f'Bearer {MINIMAX_KEY}', 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'},
            json={'model': 'MiniMax-M2.7', 'max_tokens': 300, 'messages': [{'role': 'user', 'content': prompt}]},
            timeout=15
        )
        if mr.status_code != 200:
            return jsonify({'error': f'MiniMax error {mr.status_code}', 'detail': mr.text[:200]}), 502

        mr_data = mr.json()
        content = mr_data.get('content', [])
        text = ''
        if isinstance(content, list):
            for block in content:
                if block.get('type') == 'text':
                    text = block.get('text', '')
                    break
        if not text and isinstance(content, list):
            # Fallback: try thinking block text
            for block in content:
                if block.get('type') == 'thinking':
                    t = block.get('text', '')
                    if isinstance(t, str):
                        text = t
                        break
                    elif isinstance(t, dict) and 'thinking' in t:
                        text = t.get('thinking', '')
                        break
        if not text:
            text = str(content)

        import re
        json_match = re.search(r'\{\s*\"primary\".*\}', text, re.DOTALL)
        if not json_match:
            return jsonify({'error': 'Parsing risposta LLM fallito', 'raw': text[:200]}), 500

        parsed = json.loads(json_match.group())
        primary = parsed.get('primary', '')
        secondary = parsed.get('secondary', [])
        categoria = parsed.get('categoria')
        fonte = parsed.get('fonte')

        if not primary:
            return jsonify({'results': [], 'intent': parsed, 'message': 'Nessun keyword principale estratta'})

        cols = 'id,nome,azienda,categoria,modo_duso,ingredienti,dosaggio,fonte'
        
        # First search: primary keyword (OR match on nome/azienda/ingredienti)
        primary_parts = 'or'.join([f'nome.ilike.%25{primary}%25', f'azienda.ilike.%25{primary}%25', f'ingredienti.ilike.%25{primary}%25'])
        params = f'select={cols}&{primary_parts}&limit=50'
        if categoria:
            params += f'&categoria.ilike.%25{categoria}%25'
        if fonte:
            params += f'&fonte.eq.{fonte}'

        sr = requests.get(f'{SUPABASE_URL}/rest/v1/products?{params}', headers=HEADERS, timeout=10)
        results = sr.json() if sr.status_code == 200 else []

        # Filter: secondary keywords must ALL be present in nome OR ingredienti OR dosaggio
        if secondary:
            def matches_all(row):
                text = ' '.join([
                    (row.get('nome') or ''),
                    (row.get('ingredienti') or ''),
                    (row.get('dosaggio') or '')
                ]).lower()
                return all(kw.lower() in text for kw in secondary)
            results = [r for r in results if matches_all(r)]
            results = results[:20]

        return jsonify({
            'results': [{k: clean_value(v) for k, v in row.items()} for row in results],
            'intent': parsed,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stack/compose', methods=['POST'])
def stack_compose():
    """Receive 2-3 product names, return combined profile + warnings."""
    body = request.get_json(force=True)
    product_names = body.get('products', [])
    if not product_names or len(product_names) < 2:
        return jsonify({'error': 'Invia almeno 2 nomi prodotto in products[]'}), 400

    seen_ids = set()
    found_products = []
    errors = []

    for name in product_names:
        try:
            name_enc = name.replace(' ', '%25')
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/products?"
                f"select=id,nome,azienda,dosaggio,ingredienti,modo_duso,confezione,fonte,minsan"
                f"&or=(nome.ilike.%25{name_enc}%25,azienda.ilike.%25{name_enc}%25)"
                f"&limit=5",
                headers=HEADERS, timeout=15
            )
            products = r.json() if r.status_code == 200 else []

            if not products:
                r2 = requests.get(
                    f"{SUPABASE_URL}/rest/v1/products?"
                    f"select=id,nome,azienda,dosaggio,ingredienti,modo_duso,confezione,fonte,minsan"
                    f"&nome=ilike.%25{name_enc}%25&limit=5",
                    headers=HEADERS, timeout=15
                )
                products = r2.json() if r2.status_code == 200 else []

            if not products:
                errors.append(f"'{name}' not found")
                continue

            p = products[0]
            pid = str(p.get('id', ''))
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)

            combo_product = {
                'id': pid,
                'nome': p.get('nome'),
                'azienda': p.get('azienda'),
                'fonte': p.get('fonte'),
            }

            d = p.get('dosaggio', '')
            if d:
                clean = d.split('VNR')[0].split('PRINCIPI')[0].split('screen')[0].strip()
                combo_product['dosaggio_clean'] = clean
                combo_product['dosaggio_raw'] = d[:300]

            i = p.get('ingredienti', '')
            if i and i != 'None' and len(i) > 5:
                clean_i = i.split('screen')[0].split('@media')[0].strip()
                combo_product['ingredienti'] = clean_i[:300]

            found_products.append(combo_product)

        except Exception as e:
            errors.append(f"'{name}': {str(e)}")

    # Build warnings for overlapping nutrients
    warnings = []
    b_keywords = ['vitamina b1', 'vitamina b2', 'vitamina b6', 'vitamina b12', 'niacina', 'folico']
    
    for i, a in enumerate(found_products):
        for j, b in enumerate(found_products):
            if i >= j:
                break
            da = a.get('dosaggio_clean', '')
            db = b.get('dosaggio_clean', '')
            overlap = [k for k in b_keywords if k.lower() in da.lower() and k.lower() in db.lower()]
            if overlap:
                warnings.append(f"Sovrapposizione B-vitamine tra '{a['nome']}' e '{b['nome']}': {', '.join(overlap)}")

    return jsonify({
        'products': found_products,
        'warnings': warnings,
        'errors': errors,
        'gaps': [],
    })

@app.route('/health')
def health():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=id&limit=1", headers=HEADERS, timeout=5)
    return jsonify({'status': 'ok' if r.status_code == 200 else 'error', 'supabase': 'vmammjkauepeeiylnueh'})

if __name__ == '__main__':
    print(f"Starting IntegrAction API on port 8765 (Supabase backend)")
    app.run(host='0.0.0.0', port=8765, debug=False, threaded=True)