#!/usr/bin/env python3
"""
IntegrAction API Server - reads from Supabase (vmammjkauepeeiylnueh)
"""
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

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

@app.route('/stats')
def stats():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=id", headers=HEADERS, timeout=10)
    total = len(r.json()) if r.status_code == 200 else 0
    
    fields = ['nome','azienda','forma_farmaceutica','categoria','confezione',
              'utilizzazioni','modo_duso','ingredienti','dosaggio','avvertenze',
              'minsan','prezzo','fonte']
    
    completezza = {}
    for f in fields:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?{f}=not.is.null&select={f}",
            headers=HEADERS, timeout=10
        )
        cnt = len(r.json()) if r.status_code == 200 else 0
        completezza[f] = {'count': cnt, 'pct': round(100*cnt/total, 1) if total > 0 else 0}
    
    return jsonify({'total': total, 'completezza': completezza})

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
        # Fallback: manual aggregation
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

@app.route('/health')
def health():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=id&limit=1", headers=HEADERS, timeout=5)
    return jsonify({'status': 'ok' if r.status_code == 200 else 'error', 'supabase': 'vmammjkauepeeiylnueh'})

if __name__ == '__main__':
    print(f"Starting IntegrAction API on port 8765 (Supabase backend)")
    app.run(host='0.0.0.0', port=8765, debug=False, threaded=True)
