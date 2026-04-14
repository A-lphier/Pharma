"""
Integratori Product Lookup API.
Provides fast product search for the FatturaMVP invoice enrichment.
"""
import os
import sqlite3
import re
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/integratori", tags=["integratori"])

DB_PATH = os.environ.get(
    "INTEGRATORI_DB",
    "/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db"
)


def normalize(s: str) -> str:
    """Normalize product name for fuzzy matching."""
    if not s:
        return ""
    s = s.upper()
    s = re.sub(r'[®™°\-\_]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def get_db():
    """Get a connection to the integratori DB."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class ProductResponse(BaseModel):
    id: int
    nome: str
    azienda: Optional[str]
    minsan: Optional[str]
    codice_paraf: Optional[str]
    forma_farmaceutica: Optional[str]
    ingredienti: Optional[str]
    indicazioni: Optional[str]
    modalita_duso: Optional[str]
    senza_lattosio: bool
    senza_glutine: bool
    vegan: bool
    score: Optional[float] = None


def _row_to_response(row: dict, score: float = 1.0) -> ProductResponse:
    return ProductResponse(
        id=row['id'], nome=row['nome'], azienda=row['azienda'],
        minsan=row['minsan'], codice_paraf=row['codice_paraf'],
        forma_farmaceutica=row['forma_farmaceutica'],
        ingredienti=row['ingredienti'], indicazioni=row['indicazioni'],
        modalita_duso=row['modalita_duso'],
        senza_lattosio=bool(row['senza_lattosio']),
        senza_glutine=bool(row['senza_glutine']),
        vegan=bool(row['vegan']),
        score=score
    )


@router.get("/search", response_model=list[ProductResponse])
def search_products(
    q: str = Query(default="", min_length=2, description="Search term (nome prodotto)"),
    limit: int = Query(default=10, ge=1, le=50),
    exact_minsan: Optional[str] = Query(default=None, description="Exact MINSAN code lookup"),
):
    # Resolve Query defaults to Python values
    q = q if isinstance(q, str) else str(q)
    limit = limit if isinstance(limit, int) else int(limit)
    if exact_minsan is not None and not isinstance(exact_minsan, str):
        exact_minsan = None
    """
    Search integratori by name or MINSAN code.
    
    - **q**: Product name search (fuzzy matching on nome)
    - **exact_minsan**: If provided, does exact MINSAN lookup instead of name search
    - **limit**: Max results (default 10, max 50)
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Integratori DB not available")
    
    # If exact_minsan provided, use that directly
    if exact_minsan:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT id, nome, azienda, minsan, codice_paraf, forma_farmaceutica,
                   ingredienti, indicazioni, modalita_duso,
                   senza_lattosio, senza_glutine, vegan
            FROM products WHERE minsan = ? LIMIT 1
        """, (exact_minsan,))
        row = c.fetchone()
        conn.close()
        if row:
            return [_row_to_response(dict(row))]
        return []
    
    if not q or len(q) < 2:
        return []
    
    conn = get_db()
    c = conn.cursor()
    results = []
    
    q_norm = normalize(q)
    
    # 1. Exact normalized name match
    c.execute("""
        SELECT id, nome, azienda, minsan, codice_paraf, forma_farmaceutica,
               ingredienti, indicazioni, modalita_duso,
               senza_lattosio, senza_glutine, vegan
        FROM products
        WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(nome, '®', ''), '™', ''), '°', ''), '-', '')) = ?
        LIMIT ?
    """, (q_norm, limit))
    
    for row in c.fetchall():
        results.append(_row_to_response(dict(row), score=1.0))
    
    if len(results) >= limit:
        conn.close()
        return results
    
    # 2. Word-based fallback — all words must appear in name
    q_words = [w for w in q_norm.split() if len(w) >= 3]
    if q_words:
        placeholders = ' AND '.join([
            "UPPER(REPLACE(REPLACE(REPLACE(REPLACE(nome, '®', ''), '™', ''), '°', ''), '-', '')) LIKE ?"
        ] * len(q_words))
        c.execute(f"""
            SELECT id, nome, azienda, minsan, codice_paraf, forma_farmaceutica,
                   ingredienti, indicazioni, modalita_duso,
                   senza_lattosio, senza_glutine, vegan
            FROM products
            WHERE {placeholders}
            LIMIT ?
        """, [f'%{w}%' for w in q_words] + [limit])
        
        seen_ids = {r.id for r in results}
        for row in c.fetchall():
            if row['id'] not in seen_ids:
                seen_ids.add(row['id'])
                results.append(_row_to_response(dict(row), score=0.8))
                if len(results) >= limit:
                    break
    
    conn.close()
    return results


@router.get("/stats")
def get_stats():
    """Return database statistics."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Integratori DB not available")
    
    conn = get_db()
    c = conn.cursor()
    
    total = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    with_minsan = c.execute("SELECT COUNT(*) FROM products WHERE minsan IS NOT NULL AND minsan != ''").fetchone()[0]
    with_ing = c.execute("SELECT COUNT(*) FROM products WHERE ingredienti IS NOT NULL AND ingredienti != '' AND ingredienti != 'N/A' AND LENGTH(ingredienti) > 10").fetchone()[0]
    vegan = c.execute("SELECT COUNT(*) FROM products WHERE vegan = 1").fetchone()[0]
    senza_lattosio = c.execute("SELECT COUNT(*) FROM products WHERE senza_lattosio = 1").fetchone()[0]
    senza_glutine = c.execute("SELECT COUNT(*) FROM products WHERE senza_glutine = 1").fetchone()[0]
    
    conn.close()
    
    return {
        "total": total,
        "with_minsan": with_minsan,
        "with_minsan_pct": round(with_minsan / total * 100, 1) if total else 0,
        "with_ingredienti": with_ing,
        "with_ingredienti_pct": round(with_ing / total * 100, 1) if total else 0,
        "vegan": vegan,
        "senza_lattosio": senza_lattosio,
        "senza_glutine": senza_glutine,
    }


@router.get("/by-minsan/{minsan}", response_model=ProductResponse | None)
def get_by_minsan(minsan: str):
    """Get a single product by MINSAN code."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Integratori DB not available")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, nome, azienda, minsan, codice_paraf, forma_farmaceutica,
               ingredienti, indicazioni, modalita_duso,
               senza_lattosio, senza_glutine, vegan
        FROM products WHERE minsan = ?
    """, (minsan,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return _row_to_response(dict(row))
