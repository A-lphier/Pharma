#!/usr/bin/env python3
"""
Upload integratori_FINAL.db to Supabase (vmammjkauepeeiylnueh)
Handles column mapping and UUID generation
"""
import sqlite3
import requests
import time
import uuid
from tqdm import tqdm

SUPABASE_URL = "https://vmammjkauepeeiylnueh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZtYW1tamthdWVwZWVpeWxudWVoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjA3MDQ4NSwiZXhwIjoyMDkxNjQ2NDg1fQ.TDveBcTklfNhSjDfsBEyplrb8FcydznMLs60hIs9qaY"
DB_PATH = "./integratori_FINAL.db"
BATCH_SIZE = 200

# Our DB columns -> Supabase columns (only matching ones)
COLUMN_MAP = {
    'id': 'id',
    'nome': 'nome',
    'azienda': 'azienda',
    'forma_farmaceutica': 'forma_farmaceutica',
    'categoria': 'categoria',
    'confezione': 'confezione',
    'utilizzi': 'utilizzazioni',
    'modo_duso': 'modo_duso',
    'ingredienti': 'ingredienti',
    'dosaggio': 'dosaggio',
    'avvertenze': 'avvertenze',
    'url': 'url',
    'minsan': 'minsan',
    'indicazioni': 'indicazioni',
    'senza_lattosio': 'senza_lattosio',
    'senza_glutine': 'senza_glutine',
    'vegan': 'vegan',
    'prezzo': 'prezzo',
    'composizione': 'composizione',
    'fonte': 'fonte',
}
# Note: we also have extra columns like ingredienti_norm, dosaggio_norm, etc.
# but Supabase table only has the columns above

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def clean_value(v):
    """Clean a value for Supabase upload"""
    if v is None:
        return None
    if isinstance(v, str):
        if len(v) > 8000:
            v = v[:8000]
        v = v.replace('\x00', '')
    return v

def upload_batch(records):
    """Upload a batch of records"""
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/products",
            headers=get_headers(),
            json=records,
            timeout=120
        )
        return r.status_code in (201, 200), r
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 50)
    print("INTEGRATORI → SUPABASE UPLOAD")
    print("=" * 50)
    
    # Check connection
    r = requests.get(f"{SUPABASE_URL}/rest/v1/products?select=id&limit=1", headers=get_headers(), timeout=10)
    print(f"Connection: {r.status_code}")
    if r.status_code != 200:
        print(f"Failed: {r.text[:200]}")
        return
    
    # Connect to local DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM products")
    total = cur.fetchone()[0]
    print(f"Local DB: {total:,} products")
    
    # Get our columns
    cur.execute("PRAGMA table_info(products)")
    our_cols = [r[1] for r in cur.fetchall()]
    
    # Select only mapped columns
    select_cols = [c for c in our_cols if c in COLUMN_MAP]
    col_list = ','.join(select_cols)
    
    cur.execute(f"SELECT {col_list} FROM products")
    
    uploaded = 0
    errors = 0
    batch_num = 0
    
    pbar = tqdm(total=total, desc="Uploading")
    
    while True:
        rows = cur.fetchmany(BATCH_SIZE)
        if not rows:
            break
        
        records = []
        for row in rows:
            rec = {}
            for i, col in enumerate(select_cols):
                v = clean_value(row[i])
                if col == 'id':
                    # Generate UUID for id
                    rec['id'] = str(uuid.uuid4())
                elif col == 'senza_lattosio' or col == 'senza_glutine' or col == 'vegan':
                    # Boolean fields
                    rec[COLUMN_MAP[col]] = bool(v) if v is not None else False
                elif col == 'prezzo':
                    rec[COLUMN_MAP[col]] = float(v) if v not in (None, '', 'None') else None
                else:
                    rec[COLUMN_MAP[col]] = v
            records.append(rec)
        
        success, resp = upload_batch(records)
        if success:
            uploaded += len(records)
        else:
            # Retry one by one
            for rec in records:
                s, _ = upload_batch([rec])
                if s:
                    uploaded += 1
                else:
                    errors += 1
                    if errors <= 3:
                        print(f"\nError: {str(_)[:100]}")
        
        pbar.update(len(records))
        batch_num += 1
        if batch_num % 10 == 0:
            print(f"\n  Progress: {uploaded:,} uploaded, {errors} errors")
        time.sleep(0.3)
    
    pbar.close()
    conn.close()
    
    print(f"\n✅ Uploaded: {uploaded:,} | Errors: {errors}")
    print(f"Total in Supabase should now be: ~{uploaded}")

if __name__ == '__main__':
    main()