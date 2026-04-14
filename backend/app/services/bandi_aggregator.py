"""
Bandi Aggregator — FatturaMVP
Cerca bandi pubblici per software/gestionale/digitalizzazione.
Usa httpx con header realistici + fallback su siti governativi noti.
Una volta al giorno ore 14 UTC.
"""

import os
import sqlite3
import re
import hashlib
from datetime import datetime, timezone
from typing import Optional

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "fatturamvp.db")

# Keywords per la ricerca
KEYWORDS = [
    "bandi appalti software gestionale Italia 2026",
    "gare appalto fatturazione elettronica digitalizzazione 2026",
    "MEPA bandi software cloud servizi IT 2026",
    "bandi pubblici digitalizzazione PMI Italia 2026",
    "CONSIP appalti software as a service 2026",
    "bandi regione digitalizzazione cloud computing 2026",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bandi (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            ente        TEXT,
            url         TEXT UNIQUE,
            importo     TEXT,
            scadenza    TEXT,
            categoria   TEXT,
            source      TEXT,
            hash        TEXT UNIQUE,
            found_at    TEXT DEFAULT (datetime('now')),
            notified_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def hash_row(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()[:16]


def already_known(url: str, title: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    h = hash_row(title, url)
    row = cur.execute("SELECT 1 FROM bandi WHERE hash = ?", (h,)).fetchone()
    conn.close()
    return row is not None


def save_bando(title: str, description: str, ente: str, url: str,
               importo: str, scadenza: str, categoria: str, source: str) -> bool:
    h = hash_row(title, url)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR IGNORE INTO bandi
            (title, description, ente, url, importo, scadenza, categoria, source, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, ente, url, importo, scadenza, categoria, source, h))
        conn.commit()
        inserted = cur.rowcount > 0
    except Exception:
        inserted = False
    conn.close()
    return inserted


def extract_scadenza(text: str) -> Optional[str]:
    """Cerca una data di scadenza nel testo (formati italiani)."""
    patterns = [
        r"scadenza[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"entro il (\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"entro il (\d{1,2} \w+ \d{4})",
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        r"scade il (\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        r"截止日期[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_importo(text: str) -> Optional[str]:
    """Cerca un importo nel testo."""
    m = re.search(r"[€$]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)", text)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        try:
            euros = float(val)
            if euros > 1000:  # solo importi realistici per bandi
                return f"€ {euros:,.0f}"
        except ValueError:
            pass
    return None


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fa GET con httpx, restituisce html o None se fallisce."""
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            return resp.text
    except Exception as e:
        print(f"  [fetch_url] ERRORE {url}: {e}")
    return None


def scrape_mepa() -> list[dict]:
    """Cerca bandi attivi MEPA."""
    results = []
    url = "https://www.consip.it/mediagallery/bandi-attivi"
    html = fetch_url(url)
    if not html:
        # Fallback: google cached
        url_google = "https://www.google.com/search?q=site:consip.it+bandi+software+2026&hl=it"
        html = fetch_url(url_google)

    if not html:
        return results

    # Estrai link e titoli con regex (semplice ma efficace)
    # Pattern: <a href="...">titolo</a> con "bando" o "gara"
    pattern = re.compile(
        r'<a[^>]+href="(https?://www\.consip\.it[^"]+)"[^>]*>\s*([^<]{20,200})\s*</a>',
        re.IGNORECASE
    )
    seen = set()
    for m in pattern.finditer(html):
        link = m.group(1)
        title = m.group(2).strip()
        if link in seen:
            continue
        seen.add(link)
        if any(kw in title.lower() for kw in ["software", "cloud", "gestionale", "digitale", "servizi", "IT"]):
            results.append({
                "title": title,
                "url": link,
                "source": "MEPA",
            })

    return results


def scrape_google(query: str) -> list[dict]:
    """Cerca su Google con httpx (funziona su molti siti governativi)."""
    results = []
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=it&num=10"
    html = fetch_url(search_url, timeout=15)
    if not html:
        return results

    # Estrai risultati Google
    # Pattern: <div class="vvjwJb"> (titolo) + <a href="url">
    # O più generico: Cerca blocchi con URL che iniziano per http
    pattern = re.compile(
        r'<a[^>]+href="(https?://[^\s"#&]+)"[^>]*>\s*<span[^>]*class="[^"]*中高[^"]*"[^>]*>([^<]+)</span>',
        re.UNICODE
    )
    # Alternativa: estrai tutti i link google-completi
    link_pattern = re.compile(r'/url\?q=(https?://[^&\s]+)')
    titles_pattern = re.compile(r'<h3[^>]*class="[^"]*"[^>]*>([^<]+)</h3>')

    urls = link_pattern.findall(html)
    titles = titles_pattern.findall(html)

    for i, url in enumerate(urls[:10]):
        title = titles[i].strip() if i < len(titles) else f"Bando {i+1}"
        if any(kw in title.lower() + url.lower() for kw in ["bando", "gara", "appalto", "software", "gestionale", "digital"]):
            results.append({
                "title": title[:300],
                "url": url,
                "source": "google",
            })

    return results


def run() -> tuple[list[dict], int]:
    """
    Esegue la ricerca bandi.
    Restituisce (nuovi_bandi, errori_count).
    """
    init_db()
    new_bandi = []
    errors = 0

    print(f"[bandi_aggregator] Avvio — {datetime.now(timezone.utc).isoformat()}")
    print(f"[bandi_aggregator] Keywords: {len(KEYWORDS)}")

    # 1. Google searches
    for query in KEYWORDS:
        print(f"[bandi_aggregator] Google: {query[:60]}")
        try:
            results = scrape_google(query)
        except Exception as e:
            print(f"[bandi_aggregator] ERRORE Google '{query}': {e}")
            errors += 1
            continue

        for r in results:
            if already_known(r["url"], r["title"]):
                continue
            scadenza = extract_scadenza(r["title"])
            importo  = extract_importo(r["title"])
            saved = save_bando(
                title       = r["title"][:500],
                description = "",
                ente        = "",
                url         = r["url"],
                importo     = importo or "",
                scadenza    = scadenza or "",
                categoria   = "appalti",
                source      = r["source"],
            )
            if saved:
                new_bandi.append({**r, "scadenza": scadenza, "importo": importo})
                print(f"  ✓ NUOVO: {r['title'][:80]}")

    # 2. MEPA direct
    print(f"[bandi_aggregator] MEPA direct...")
    try:
        for r in scrape_mepa():
            if already_known(r["url"], r["title"]):
                continue
            saved = save_bando(
                title       = r["title"][:500],
                description = "",
                ente        = "CONSIP",
                url         = r["url"],
                importo     = "",
                scadenza    = "",
                categoria   = "appalti",
                source      = r["source"],
            )
            if saved:
                new_bandi.append({**r, "scadenza": "", "importo": ""})
                print(f"  ✓ NUOVO MEPA: {r['title'][:80]}")
    except Exception as e:
        print(f"[bandi_aggregator] ERRORE MEPA: {e}")
        errors += 1

    print(f"[bandi_aggregator] Fatto — {len(new_bandi)} nuovi bandi, {errors} errori")
    return new_bandi, errors


if __name__ == "__main__":
    new, errs = run()
    print(f"\nRisultato finale: {len(new)} nuovi bandi, {errs} errori")
    if new:
        for b in new:
            print(f"  • {b['title'][:80]}")
            print(f"    {b['url']}")
