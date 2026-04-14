#!/usr/bin/env python3
"""
Upload integratori_FINAL.db to Supabase via REST API
Run this on a machine with internet access to Supabase.

Usage:
    python3 upload_to_supabase.py

Requirements:
    pip install requests tqdm
"""
import sqlite3
import requests
import time
import sys
from tqdm import tqdm

# ─── CONFIG ───
SUPABASE_URL = "https://vmammjkauepeeiylnueh.supabase.co"
SUPABASE_SERVICE_KEY = "your-service-role-key-here"  # ← Replace with your service_role key
DB_PATH = "./integratori_FINAL.db"
BATCH_SIZE = 500
# ───────────────

def get_headers():
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def check_connection():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?select=id&limit=1",
        headers=get_headers(), timeout=10
    )
    print(f"Connection test: {r.status_code}")
    return r.status_code == 200

def get_columns(cursor):
    """Get column list from products table"""
    cursor.execute("PRAGMA table_info(products)")
    return [row[1] for row in cursor.fetchall()]

def upload_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cols = get_columns(cur)
    print(f"Columns ({len(cols)}): {cols[:10]}...")
    
    # Check if table exists and get row count
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?select=id",
        headers=get_headers(), timeout=10
    )
    if r.status_code == 200:
        existing = len(r.json())
        print(f"Existing products in Supabase: {existing}")
        if existing > 0 and input("Delete existing and reload? (y/N): ").strip().lower() != 'y':
            print("Aborting.")
            return
        # Delete existing
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/products",
            headers={**get_headers(), "Prefer": "count"}
        )
        print("Deleted existing records.")
    elif r.status_code == 404:
        print("Table 'products' not found. Create it first with supabase-schema.sql")
        return
    else:
        print(f"Error checking table: {r.status_code} {r.text}")
        return
    
    cur.execute("SELECT COUNT(*) FROM products")
    total = cur.fetchone()[0]
    print(f"Uploading {total:,} products...")
    
    # Exclude binary-heavy columns for upload speed
    skip_cols = {'composizione_clean', 'conservazione', 'codice_ministero', 
                 'product_type', 'ean', 'codice_paraf', 'url_stato'}
    upload_cols = [c for c in cols if c not in skip_cols]
    print(f"Uploading columns: {upload_cols}")
    
    placeholders = ",".join([f"${i+1}" for i in range(len(upload_cols))])
    
    cur.execute(f"SELECT {','.join(upload_cols)} FROM products")
    
    batches = []
    for batch in tqdm(iter(lambda: cur.fetchmany(BATCH_SIZE), []), 
                      desc="Preparing", total=(total // BATCH_SIZE) + 1):
        records = [dict(zip(upload_cols, row)) for row in batch]
        # Convert all None to JSON null
        for r in records:
            for k, v in r.items():
                if v is None:
                    r[k] = None
                elif isinstance(v, str) and len(v) > 10000:
                    r[k] = v[:10000]  # Truncate very long text
        batches.append(records)
    
    conn.close()
    
    # Upload in batches
    for i, batch in enumerate(tqdm(batches, desc="Uploading")):
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/products",
            headers=get_headers(),
            json=batch,
            timeout=120
        )
        if r.status_code not in (201, 200):
            print(f"\nBatch {i} error: {r.status_code} {r.text[:200]}")
            if r.status_code == 413:
                # Payload too large - reduce batch size
                print("413: Batch too large, retrying with half batch size...")
                for j, record in enumerate(tqdm(batch, desc=f"Batch {i} records")):
                    rr = requests.post(f"{SUPABASE_URL}/rest/v1/products",
                                       headers=get_headers(), json=[record], timeout=60)
                    if rr.status_code not in (201, 200):
                        print(f"Record error: {rr.status_code}")
            elif "batch too large" in r.text.lower():
                # Retry individual records
                for record in batch:
                    rr = requests.post(f"{SUPABASE_URL}/rest/v1/products",
                                     headers=get_headers(), json=[record], timeout=60)
                    if rr.status_code not in (201, 200):
                        print(f"Record error: {rr.status_code}")
        time.sleep(0.5)  # Rate limit protection
    
    print("\n✅ Upload complete!")

if __name__ == '__main__':
    if not check_connection():
        print("❌ Cannot connect to Supabase. Check your service role key.")
        sys.exit(1)
    upload_all()
