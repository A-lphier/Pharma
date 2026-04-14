#!/usr/bin/env python3
import asyncio
import re
import json
import sqlite3
import aiohttp

PRODUCTS = [
    (43108, 'The Rosso Tisana 20filt', 'https://www.superfarma.it/products/the-rosso-tisana-20filt', 'superfarma'),
    (43109, 'Activated Coral Calcium', 'https://www.superfarma.it/products/activated-coral-calcium', 'superfarma'),
    (43110, 'Tisana Mamma 20bust', 'https://www.superfarma.it/products/tisana-mamma-20bust', 'superfarma'),
    (43114, 'Rescue Int Spray 50ml', 'https://www.superfarma.it/products/rescue-int-spray-50ml', 'superfarma'),
    (43116, 'Psicophyt Remedy 32b 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-32b-4tub-1-2g', 'superfarma'),
    (43122, 'Psicophyt Remedy 26b 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-26b-4tub-1-2g', 'superfarma'),
    (43129, 'Vitamina E 400 Orthica', 'https://www.superfarma.it/products/vitamina-e-400-orthica', 'superfarma'),
    (43130, 'Humana Tis Finocchio 200g', 'https://www.superfarma.it/products/humana-tis-finocchio-200g', 'superfarma'),
    (43131, 'Humana Tis Frut 200g', 'https://www.superfarma.it/products/humana-tis-frut-200g', 'superfarma'),
    (43134, 'Rescue 1 Gocce 50ml', 'https://www.superfarma.it/products/rescue-1-gocce-50ml', 'superfarma'),
    (43142, 'Psicophyt Remedy 11a 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-11a-4tub-1-2g', 'superfarma'),
    (43156, 'Psicophyt Remedy 16b 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-16b-4tub-1-2g', 'superfarma'),
    (43158, 'Psicophyt Remedy 7b 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-7b-4tub-1-2g', 'superfarma'),
    (43159, 'Psicophyt Remedy 8b 4tub 1,2g', 'https://www.superfarma.it/products/psicophyt-remedy-8b-4tub-1-2g', 'superfarma'),
    (43164, 'Riso Basmati Bianco 500g', 'https://www.superfarma.it/products/riso-basmati-bianco-500g', 'superfarma'),
    (43170, 'Farabella Penne Corte 500g', 'https://www.superfarma.it/products/farabella-penne-corte-500g', 'superfarma'),
    (43173, 'Shoyu 250ml Bio +bb2 B1003', 'https://www.superfarma.it/products/shoyu-250ml-bio-bb2-b1003', 'superfarma'),
    (43178, 'Seitan Instant 120g Bio', 'https://www.superfarma.it/products/seitan-instant-120g-bio', 'superfarma'),
    (43182, 'Mirin 250ml', 'https://www.superfarma.it/products/mirin-250ml', 'superfarma'),
    (43186, 'Schar Pizza Base 300g', 'https://www.superfarma.it/products/schar-fondo-pizza-300g', 'superfarma'),
    (43190, 'Sale Marino Int Grosso Sic1kg', 'https://www.superfarma.it/products/sale-marino-int-grosso-sic1kg', 'superfarma'),
    (43193, 'Olio Cocco Alim 100ml', 'https://www.superfarma.it/products/olio-cocco-alim-100ml', 'superfarma'),
    (43194, 'Quisetil Calciofix 60cpr', 'https://www.superfarma.it/products/quisetil-calciofix-60cpr', 'superfarma'),
    (43196, 'Riso Semilav Lungo Ita Bio 1kg', 'https://www.superfarma.it/products/riso-semilav-lungo-ita-bio-1kg', 'superfarma'),
    (43199, 'Magredo 2 Scir Acero 660g', 'https://www.superfarma.it/products/magredo-2-scir-acero-660g', 'superfarma'),
    (43200, 'Dialbrodo Classico 500g', 'https://www.superfarma.it/products/dialbrodo-classico-500g', 'superfarma'),
    (43201, 'Dialbrodo Classico 1kg', 'https://www.superfarma.it/products/dialbrodo-classico-1kg', 'superfarma'),
    (43203, 'Friliver 50bust', 'https://www.superfarma.it/products/friliver-50bust', 'superfarma'),
    (43204, 'Friliver 20bust', 'https://www.superfarma.it/products/friliver-20bust', 'superfarma'),
    (43205, 'Apigola Miele Balsamico 250g', 'https://www.superfarma.it/products/apigola-miele-balsamico-250g', 'superfarma'),
    (43207, 'Api 4+1 10fl 10ml', 'https://www.superfarma.it/products/api-4-1-10fl-10ml', 'superfarma'),
    (43210, 'Lvs 62s Ginkgo Biloba Comp', 'https://www.superfarma.it/products/lvs-62s-ginkgo-biloba-comp', 'superfarma'),
    (43212, 'Viropa Camomilla Bio 15bust', 'https://www.superfarma.it/products/viropa-camomilla-bio-15bust', 'superfarma'),
    (43213, 'Viropa Menta Piperita Bio 15b', 'https://www.superfarma.it/products/viropa-menta-piperita-bio-15b', 'superfarma'),
    (43216, 'Loprofin Ave Storte 250g Nf', 'https://www.superfarma.it/products/loprofin-ave-storte-250g-nf', 'superfarma'),
    (43217, 'Loprofin Gnocchetti 500g Nf', 'https://www.superfarma.it/products/loprofin-gnocchetti-500g-nf', 'superfarma'),
    (43218, 'Loprofin Penne 500g', 'https://www.superfarma.it/products/loprofin-penne-500g', 'superfarma'),
    (43227, 'Schar Pausa Ciok Pan Spagna350', 'https://www.superfarma.it/products/schar-pausa-ciok-pan-spagna350', 'superfarma'),
    (43228, 'Nutilis Aqua Gel Ment 12x125g', 'https://www.superfarma.it/products/nutilis-aqua-gel-ment-12x125g', 'superfarma'),
    (43239, 'Tisana Tarassaco 100g', 'https://www.superfarma.it/products/tisana-tarassaco-100g', 'superfarma'),
    (43240, "Karkade' Bustine Filtro", 'https://www.superfarma.it/products/karkade-bustine-filtro', 'superfarma'),
    (43241, 'Finocchio 20bust Filtro', 'https://www.superfarma.it/products/finocchio-20bust-filtro', 'superfarma'),
    (43242, 'The Nero Bustine Filtro', 'https://www.superfarma.it/products/the-nero-bustine-filtro', 'superfarma'),
    (43247, 'Meritene Creme Nocciola 3x125g', 'https://www.superfarma.it/products/meritene-creme-nocciola-3x125g', 'superfarma'),
    (43248, 'Meritene Creme Cioccolat3x125g', 'https://www.superfarma.it/products/meritene-creme-cioccolat3x125g', 'superfarma'),
    (43249, 'Paidinil 150ml', 'https://www.superfarma.it/products/paidinil-150ml', 'superfarma'),
    (43252, 'Nutridrink Vaniglia 4x200ml', 'https://www.superfarma.it/products/nutridrink-vaniglia-4x200ml', 'superfarma'),
    (43253, 'Catalitic K 20amp', 'https://www.superfarma.it/products/catalitic-k-20amp', 'superfarma'),
    (43254, 'Catalitic Zinco Rame Zn-cu 20f', 'https://www.superfarma.it/products/catalitic-zinco-rame-zn-cu-20f', 'superfarma'),
    (43255, 'Catalitic P 20amp', 'https://www.superfarma.it/products/catalitic-p-20amp', 'superfarma'),
    (43256, 'Kombucha', 'https://www.superfarma.it/products/kombucha', 'superfarma'),
    (43267, 'Felicia Bio Riso Integra Penne', 'https://www.superfarma.it/products/felicia-bio-riso-integra-penne', 'superfarma'),
    (43272, 'Zen Shirataki Riso Essicat Mon', 'https://www.superfarma.it/products/zen-shirataki-riso-essicat-mon', 'superfarma'),
    (43273, 'Fiberpasta Diet Fusilli 500g', 'https://www.superfarma.it/products/fiberpasta-diet-fusilli-500g', 'superfarma'),
    (43274, 'Fiberpasta Diet Penne 500g', 'https://www.superfarma.it/products/fiberpasta-diet-penne-500g', 'superfarma'),
    (43275, 'Zenpasta Rigataki Ess Rigat60g', 'https://www.superfarma.it/products/zenpasta-rigataki-ess-rigat60g', 'superfarma'),
    (43279, 'Eflors Idra 100ml', 'https://www.superfarma.it/products/eflors-idra-100ml', 'superfarma'),
    (43281, 'Vital 1,5kcal Vaniglia 200ml', 'https://www.superfarma.it/products/vital-1-5kcal-vaniglia-200ml', 'superfarma'),
    (43283, 'Curcuma 100g', 'https://www.superfarma.it/products/curcuma-100g', 'superfarma'),
    (43285, 'Flogeril Breath Forte 18bust', 'https://www.superfarma.it/products/flogeril-breath-forte-18bust', 'superfarma'),
    (43286, 'Flogeril Breath Junior 20bust', 'https://www.superfarma.it/products/flogeril-breath-junior-20bust', 'superfarma'),
    (43287, "Nestle' Nan Ar 800g", 'https://www.superfarma.it/products/nestle-nan-ar-800g', 'superfarma'),
    (43288, 'Miraenergy 20stick', 'https://www.superfarma.it/products/miraenergy-20stick', 'superfarma'),
    (43289, 'Vitamina C System 60cps', 'https://www.superfarma.it/products/vitamina-c-system-60cps', 'superfarma'),
    (43290, 'Flebo-up Sh 500 30cpr', 'https://www.superfarma.it/products/flebo-up-sh-500-30cpr', 'superfarma'),
    (43294, 'Prother 10bust', 'https://www.superfarma.it/products/prother-10bust', 'superfarma'),
    (43296, 'Fior Di Loto Olio Verg Co450ml', 'https://www.superfarma.it/products/fior-di-loto-olio-verg-co450ml', 'superfarma'),
    (43298, 'Farina Riso Impalpab Bio 375g', 'https://www.superfarma.it/products/farina-riso-impalpab-bio-375g', 'superfarma'),
    (43301, 'Lenticchie Pic Ro Ita Bio400g', 'https://www.superfarma.it/products/lenticchie-pic-ro-ita-bio400g', 'superfarma'),
    (43306, 'Massimo Zero Mezze Penne Rigate 1kg', 'https://www.superfarma.it/products/massimo-zero-m-penne-rig-1kg', 'superfarma'),
    (43308, 'Massimo Zero M/penne Rig 400g', 'https://www.superfarma.it/products/massimo-zero-m-penne-rig-400g', 'superfarma'),
    (43310, 'Antalbimbo 24% Sterile 10fx2ml', 'https://www.superfarma.it/products/antalbimbo-24-sterile-10fx2ml', 'superfarma'),
    (43323, 'Massimo Zero Ruote 1kg', 'https://www.superfarma.it/products/massimo-zero-ruote-1kg', 'superfarma'),
    (43326, 'Flavis Fette Biscottat', 'https://www.superfarma.it/products/mevalia-flavis-fette-biscottat', 'superfarma'),
    (43328, 'Piaceri Medit Pasta Riso Farfa', 'https://www.superfarma.it/products/piaceri-medit-pasta-riso-farfa', 'superfarma'),
    (43332, 'Sustar Complex 60cpr', 'https://www.superfarma.it/products/sustar-complex-60cpr', 'superfarma'),
    (43334, 'Buongiornobio Biscotti Mat500g', 'https://www.superfarma.it/products/buongiornobio-biscotti-mat500g', 'superfarma'),
    (43335, 'Eleuterococco 60cpr Terranata', 'https://www.superfarma.it/products/eleuterococco-60cpr-terranata', 'superfarma'),
    (43336, 'Macrocea Gyn Hp 20bust', 'https://www.superfarma.it/products/macrocea-gyn-hp-20bust', 'superfarma'),
    (43337, 'Neuraxbiotic Zen 30cps', 'https://www.superfarma.it/products/neuraxbiotic-zen-30cps', 'superfarma'),
    (43338, 'Neocolina Ofta 20bust', 'https://www.superfarma.it/products/neocolina-ofta-20bust', 'superfarma'),
    (43348, 'VitaCalm Propositiv 30 compresse', 'https://www.superfarma.it/products/vitacalm-propositiv-30-compresse', 'superfarma'),
    (43350, 'Meritene Resource Diabet Vaniglia 200ml', 'https://www.superfarma.it/products/meritene-resource-diabet-vaniglia-200ml', 'superfarma'),
    (43351, 'Optima Manuka Benefit Miele Manuka 550+ MGO 250g', 'https://www.superfarma.it/products/optima-manuka-benefit-miele-manuka-550-mgo-250g', 'superfarma'),
    (43356, 'Butyrose Fast 20 Stick', 'https://www.superfarma.it/products/butyrose-fast-20-stick', 'superfarma'),
    (43359, 'Terranova Riso Rosso Fermentato Advance Complex 50 Capsule', 'https://www.superfarma.it/products/terranova-riso-rosso-fermentato-advance-complex-50-capsule', 'superfarma'),
    (43360, 'Danone Fortimel Advanced Fragola Di Bosco 4x200ml', 'https://www.superfarma.it/products/danone-fortimel-advanced-fragola-di-bosco-4x200ml', 'superfarma'),
    (43361, 'Oti C Vitamina C Liposom 30 Bustine', 'https://www.superfarma.it/products/oti-c-vitamina-c-liposom-30-bustine', 'superfarma'),
    (43363, 'Coleris1000 30 Compresse', 'https://www.superfarma.it/products/coleris1000-30-compresse', 'superfarma'),
    (43365, 'Proctolyn Integra Plus Forte 14 Bustine', 'https://www.superfarma.it/products/proctolyn-integra-plus-forte-14-bustine', 'superfarma'),
    (43366, 'Dicoflor IbdImmuno 30 Capsule', 'https://www.superfarma.it/products/dicoflor-ibdimmuno-30-capsule', 'superfarma'),
    (43367, 'Nocol Plus 30 Compresse', 'https://www.superfarma.it/products/nocol-plus-30-compresse', 'superfarma'),
    (43368, 'Refluward HA 20 Bustine', 'https://www.superfarma.it/products/refluward-ha-20-bustine', 'superfarma'),
    (43372, "Meritene Diabet Creme Caffe' 3x125g", 'https://www.superfarma.it/products/meritene-diabet-creme-caffe-3x125g', 'superfarma'),
    (43374, 'Liquisol 20 Bustine', 'https://www.superfarma.it/products/liquisol-20-bustine', 'superfarma'),
    (43377, 'Adamah Eie Degemix 60ml', 'https://www.superfarma.it/products/adamah-eie-degemix-60ml', 'superfarma'),
    (43378, 'Aproten Pane Biscottato 280g', 'https://www.superfarma.it/products/aproten-pane-biscottato-280g', 'superfarma'),
    (43379, 'Spirulina Polvere Bio 200g', 'https://www.superfarma.it/products/spirulina-polvere-bio-200g', 'superfarma'),
    (43386, 'Maca Integrale Polvere Bio 200g', 'https://www.superfarma.it/products/maca-integrale-polvere-bio-200g', 'superfarma'),
    (43387, 'Viropa Tisana Zenzero E Limone Bio 15 Filtri', 'https://www.superfarma.it/products/viropa-tisana-zenzero-e-limone-bio-15-filtri', 'superfarma'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extractforma(name):
    """Extract pharmaceutical form from product name suffix."""
    # Patterns like "60cpr", "20bust", "30cps", "50ml", "200g", etc.
    m = re.search(r'(\d+\s*(?:cpr|cps|caps?|compresse|bust|fl|ml|g|kg|amp|stick|film|gel|os|pastiglie|tavolette)[a-z]?)', name, re.I)
    if m:
        return m.group(1).lower()
    return None

def extract_from_jsonld(text):
    """Extract from JSON-LD Product schema."""
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict) and data.get('@type') == 'Product':
                return data
            # Sometimes it's a list
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        return item
        except:
            pass
    return None

def extract_from_html(text):
    """Extract fields from HTML."""
    result = {}
    
    # minsan from HTML span
    m = re.search(r'product__subtitleMinsan[^>]*>([^<]+)<', text)
    if m:
        result['minsan'] = m.group(1).strip()
    
    # Look for ingredienti in descrizione section
    idx = text.find('Descrizione prodotto')
    if idx > 0:
        section = text[idx:idx+5000]
        section_clean = clean_html(section)
        
        # ingredienti
        m = re.search(r'(?:ingredienti|principi?\s*attiv[^:]*|composizione)[:\s]*(.{10,300})', section_clean, re.I)
        if m:
            result['ingredienti'] = m.group(1).strip()[:300]
        
        # dosaggio / apporto
        for pattern in [
            r'(?:dosaggio|apporto[^a-z])[:\s]*(.{5,150})',
            r'apporto\s*giornaliero[^:]*:\s*([^\n.]{5,150})',
        ]:
            m = re.search(pattern, section_clean, re.I)
            if m:
                result['dosaggio'] = m.group(1).strip()[:150]
                break
        
        # forma_farmaceutica from description text
        m = re.search(r'forma\s*farmaceutica[:\s]*([^\n.]{3,80})', section_clean, re.I)
        if m:
            result['forma_farmaceutica'] = m.group(1).strip()[:80]
    
    return result

async def fetch_product(session, pid, nome, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return pid, nome, url, None, None, None, None, f'HTTP {resp.status}'
            text = await resp.text()
    except Exception as e:
        return pid, nome, url, None, None, None, None, str(e)

    # Extract from JSON-LD
    jsonld = extract_from_jsonld(text)
    
    minsan = None
    forma_farmaceutica = None
    ingredienti = None
    dosaggio = None
    
    if jsonld:
        # sku in JSON-LD = minsan for pharma products
        sku = jsonld.get('sku', '')
        if sku and re.match(r'^\d{9,13}$', str(sku)):
            minsan = str(sku)
        
        # description
        desc = jsonld.get('description', '')
        if desc:
            desc_lower = desc.lower()
            # Try to extract dosaggio from description
            m = re.search(r'dosaggio[:\s]*(.{5,150})', desc, re.I)
            if not m:
                m = re.search(r'apporto[^:]*:\s*([^\n.]{5,150})', desc, re.I)
            if m:
                dosaggio = m.group(1).strip()[:150]
            
            # Try to extract ingredienti
            m = re.search(r'(?:ingredienti|principi?\s*attiv[^:]*|composizione)[:\s]*(.{10,300})', desc, re.I)
            if m:
                ingredienti = m.group(1).strip()[:300]
    
    # Extract from HTML (overrides/augments JSON-LD)
    html_data = extract_from_html(text)
    
    # minsan from HTML if not found in JSON-LD
    if not minsan and 'minsan' in html_data:
        minsan = html_data['minsan']
    
    # forma_farmaceutica: try HTML first, then product name suffix
    if not forma_farmaceutica:
        if 'forma_farmaceutica' in html_data:
            forma_farmaceutica = html_data['forma_farmaceutica']
        else:
            forma_farmaceutica = extractforma(nome)
    
    # ingredienti from HTML if not found in JSON-LD
    if not ingredienti and 'ingredienti' in html_data:
        ingredienti = html_data['ingredienti']
    
    # dosaggio from HTML if not found in JSON-LD
    if not dosaggio and 'dosaggio' in html_data:
        dosaggio = html_data['dosaggio']
    
    return pid, nome, url, forma_farmaceutica, minsan, ingredienti, dosaggio, None

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_product(session, pid, nome, url) for pid, nome, url, fonte in PRODUCTS]
        results = await asyncio.gather(*tasks)

    updates = 0
    skipped = 0
    errors = 0

    conn = sqlite3.connect('/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db')
    cur = conn.cursor()

    for pid, nome, url, forma_farmaceutica, minsan, ingredienti, dosaggio, error in results:
        if error:
            print(f"[ERR] {pid} {nome}: {error}")
            errors += 1
            continue

        has_data = any([forma_farmaceutica, minsan, ingredienti, dosaggio])
        if not has_data:
            print(f"[SKIP] {pid} {nome}: no data extracted")
            skipped += 1
            continue

        # Build update
        fields = []
        vals = []
        if forma_farmaceutica:
            fields.append("forma_farmaceutica = ?")
            vals.append(forma_farmaceutica)
        if minsan:
            fields.append("minsan = ?")
            vals.append(minsan)
        if ingredienti:
            fields.append("ingredienti = ?")
            vals.append(ingredienti)
        if dosaggio:
            fields.append("dosaggio = ?")
            vals.append(dosaggio)

        if fields:
            vals.append(pid)
            sql = f"UPDATE products SET {', '.join(fields)} WHERE id = ?"
            cur.execute(sql, vals)
            updates += 1
            print(f"[OK] {pid} {nome[:40]}: forma={forma_farmaceutica}, minsan={minsan}, dosaggio={str(dosaggio)[:40] if dosaggio else None}")

    conn.commit()
    conn.close()
    print(f"\nDone: {updates} updated, {skipped} skipped, {errors} errors")

if __name__ == '__main__':
    asyncio.run(main())
