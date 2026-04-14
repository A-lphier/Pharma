#!/usr/bin/env python3
"""
IntegrAction Flask API Server - serves integratori_FINAL.db on port 8765
"""
import sqlite3
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'integratori_FINAL.db')
app = Flask(__name__)
CORS(app)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM products')
    total = cur.fetchone()[0]
    
    fields = ['nome','azienda','categoria','confezione','utilizzi','modo_duso',
              'ingredienti','dosaggio','avvertenze','minsan','prezzo',
              'forma_farmaceutica','fonte']
    
    completezza = {}
    for f in fields:
        cur.execute(f"SELECT COUNT(*) FROM products WHERE {f} IS NOT NULL AND {f} != ''")
        cnt = cur.fetchone()[0]
        completezza[f] = {'count': cnt, 'pct': round(100*cnt/total, 1) if total > 0 else 0}
    
    conn.close()
    return jsonify({'total': total, 'completezza': completezza})

@app.route('/search')
def search():
    q = request.args.get('q', '')
    limit = min(int(request.args.get('limit', 20)), 100)
    offset = int(request.args.get('offset', 0))
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    if q:
        cur.execute(f"""
            SELECT id, nome, azienda, categoria, modo_duso, ingredienti, 
                   dosaggio, avvertenze, minsan, fonte, prezzo, forma_farmaceutica
            FROM products 
            WHERE nome LIKE ? OR azienda LIKE ? OR ingredienti LIKE ?
            LIMIT ? OFFSET ?
        """, (f'%{q}%', f'%{q}%', f'%{q}%', limit, offset))
    else:
        cur.execute(f"SELECT id, nome, azienda, categoria FROM products LIMIT ? OFFSET ?", (limit, offset))
    
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/product/<int:product_id>')
def product(product_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    conn.close()
    return jsonify(dict(zip(cols, row)) if row else {})

@app.route('/categories')
def categories():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT categoria, COUNT(*) as cnt 
        FROM products WHERE categoria != '' AND categoria IS NOT NULL
        GROUP BY categoria ORDER BY cnt DESC LIMIT 50
    """)
    rows = [{'categoria': r[0], 'count': r[1]} for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/aziende')
def aziende():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT azienda, COUNT(*) as cnt 
        FROM products WHERE azienda IS NOT NULL AND azienda != ''
        GROUP BY azienda ORDER BY cnt DESC LIMIT 50
    """)
    rows = [{'azienda': r[0], 'count': r[1]} for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'db': DB_PATH})

if __name__ == '__main__':
    print(f"Starting IntegrAction API on port 8765...")
    print(f"DB: {DB_PATH}")
    app.run(host='0.0.0.0', port=8765, debug=False)
