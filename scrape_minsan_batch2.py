#!/usr/bin/env python3
import asyncio
import aiohttp
from pathlib import Path
import re
import sys

URLS = [
    ("42704", "https://www.superfarma.it/products/miso-hatcho-300g-bio"),
    ("42706", "https://www.superfarma.it/products/nutilis-aqua-gel-gra-12x125g"),
    ("42709", "https://www.superfarma.it/products/pelvilen-dual-act-60bust"),
    ("42717", "https://www.superfarma.it/products/viropa-tisana-malva-sylvestris-15-filtri"),
    ("42720", "https://www.superfarma.it/products/lemon-pharma-39-emerg-dragees-day-night-46g"),
    ("42730", "https://www.superfarma.it/products/ultra-luteina-60cps"),
    ("42732", "https://www.superfarma.it/products/cadimint-15filt-3g"),
    ("42745", "https://www.superfarma.it/products/catalitic-cu-au-ag-20amp"),
    ("42755", "https://www.superfarma.it/products/normast-mps-sospensione-20bust"),
    ("42767", "https://www.superfarma.it/products/istangial-dren-30-compresse"),
    ("42777", "https://www.superfarma.it/products/vitamina-a-10000-idro"),
    ("42785", "https://www.superfarma.it/products/psicophyt-remedy-9a-4tub-1-2g"),
    ("42792", "https://www.superfarma.it/products/ostie-7cm-1bust"),
    ("42795", "https://www.superfarma.it/products/sciroppo-d-acero-canad-c-1l"),
    ("42799", "https://www.superfarma.it/products/pelvilen-dual-act-20bust"),
    ("42801", "https://www.superfarma.it/products/viropa-zenzero-puro-bio-15bust"),
    ("42807", "https://www.superfarma.it/products/ensure-plus-advance-ban4x220ml"),
    ("42808", "https://www.superfarma.it/products/ensure-plus-advance-cio4x220ml"),
    ("42810", "https://www.superfarma.it/products/bariatrifast-30cpr"),
    ("42818", "https://www.superfarma.it/products/mevalia-flavis-crostini-150g"),
    ("42822", "https://www.superfarma.it/products/farabella-il-tarallino-class"),
    ("42832", "https://www.superfarma.it/products/viropa-tisana-karkade-bio-15-filtri"),
    ("42839", "https://www.superfarma.it/products/flufast-apix-respiro-arancia-9-buste"),
    ("42843", "https://www.superfarma.it/products/longlife-prostafactors-60-perle"),
    ("42854", "https://www.superfarma.it/products/yogi-tea-entusiasmo-ed-allegria-tisana-bio-17-filtri-30-6g"),
    ("42855", "https://www.superfarma.it/products/yogi-tea-rooibos-bio-17filtri"),
    ("42863", "https://www.superfarma.it/products/betacarotene-25000ui-90cps"),
    ("42868", "https://www.superfarma.it/products/ultra-sugar-control-60tav"),
    ("42869", "https://www.superfarma.it/products/commando-2000-antiossid-60tav"),
    ("42883", "https://www.superfarma.it/products/psicophyt-remedy-13a-4tub-1-2g"),
    ("42889", "https://www.superfarma.it/products/miele-di-acacia-bio-500g"),
    ("42891", "https://www.superfarma.it/products/acidulato-umeboshi-250ml"),
    ("42895", "https://www.superfarma.it/products/tahin-300g-bio"),
    ("42896", "https://www.superfarma.it/products/sale-marino-int-fino-sicil1kg"),
    ("42901", "https://www.superfarma.it/products/labcatal-nutrition-cu-ag-au-gt"),
    ("42902", "https://www.superfarma.it/products/starguo-menu-salato-16bust"),
    ("42904", "https://www.superfarma.it/products/viropa-ortica-bio-15bust"),
    ("42907", "https://www.superfarma.it/products/liquirizia-bianconeri-20g"),
    ("42923", "https://www.superfarma.it/products/cicoria-tostata-solubile-100g"),
    ("42925", "https://www.superfarma.it/products/nutridrink-cioccolato-4x200ml"),
    ("42926", "https://www.superfarma.it/products/nutridrink-banana-4x200ml"),
    ("42932", "https://www.superfarma.it/products/catalitic-mn-co-20amp"),
    ("42937", "https://www.superfarma.it/products/apropos-caramelle-prop-agru50g"),
    ("42940", "https://www.superfarma.it/products/shirataki-fettuccine-bio-250g"),
    ("42941", "https://www.superfarma.it/products/shirataki-spaghetti-bio-250g"),
    ("42944", "https://www.superfarma.it/products/ensure-plus-advance-caf4x220ml"),
    ("42946", "https://www.superfarma.it/products/flufast-apix-respiro-bals9bust"),
    ("42947", "https://www.superfarma.it/products/leukinal-15cps"),
    ("42948", "https://www.superfarma.it/products/fusilli-di-piselli-bio-250g"),
    ("42951", "https://www.superfarma.it/products/e-zucchero-addolcente-300g"),
    ("42952", "https://www.superfarma.it/products/grano-saraceno-bio-400g"),
    ("42955", "https://www.superfarma.it/products/mucolid-bronc-salvia-lim-24car"),
    ("42958", "https://www.superfarma.it/products/mevalia-flavis-fruit-bar-125g"),
    ("42959", "https://www.superfarma.it/products/glialia-sospensione-orale200ml"),
    ("42960", "https://www.superfarma.it/products/cobaxil-b12-5000mcg-5cpr-sunbl"),
    ("42962", "https://www.superfarma.it/products/pelvilen-90cpr"),
    ("42963", "https://www.superfarma.it/products/abiflor-kids-immuno-14stick-or"),
    ("42966", "https://www.superfarma.it/products/meritene-resource-diabet-fragola-200ml"),
    ("42969", "https://www.superfarma.it/products/eos-d3-k2-advance-60-compresse-masticabili"),
    ("42971", "https://www.superfarma.it/products/pharcos-agex-fluid-15-flaconcini"),
    ("42973", "https://www.superfarma.it/products/quinton-plasma-isotonic-30x10ml"),
    ("42974", "https://www.superfarma.it/products/nevridol-300-40-compresse"),
    ("42976", "https://www.superfarma.it/products/vado-sciroppo-30-stick"),
    ("42977", "https://www.superfarma.it/products/named-cardionam-no-colest-30-compresse"),
    ("42978", "https://www.superfarma.it/products/alkeven-30-compresse"),
    ("42979", "https://www.superfarma.it/products/bios-line-apix-propoli-caramelle-3kg"),
    ("42981", "https://www.superfarma.it/products/mucolid-bronc-immuno-24-caramelle"),
    ("42982", "https://www.superfarma.it/products/nutricia-fortimel-plant-based-energy-mango-passion-fruit-4x200ml"),
    ("42986", "https://www.superfarma.it/products/fortiral-30-bustine"),
    ("42987", "https://www.superfarma.it/products/lisozima-plus-spray-30ml"),
    ("42990", "https://www.superfarma.it/products/adamah-eie-venclean-60ml"),
    ("42992", "https://www.superfarma.it/products/aproten-fettuccine-250g-1"),
    ("42996", "https://www.superfarma.it/products/composta-ciliegia-250g"),
    ("42999", "https://www.superfarma.it/products/dimagra-mct-oil-100-30-stick"),
    ("43000", "https://www.superfarma.it/products/dr-viti-abbinata-capelli-unghie-2x60-capsule"),
    ("43001", "https://www.superfarma.it/products/dp-vitreo-30-bustine"),
    ("43002", "https://www.superfarma.it/products/erbavoglio-polvere-di-erba-di-orzo-della-nuova-zelanda-bio-200g"),
    ("43003", "https://www.superfarma.it/products/enervit-meal-shake-cacao-420g"),
    ("43004", "https://www.superfarma.it/products/eos-lievit-active-30-capsule"),
    ("43005", "https://www.superfarma.it/products/enervit-carbo-chews-c2-1-pro-caramelle-gommose-energetiche-34g"),
    ("43006", "https://www.superfarma.it/products/farabella-acini-pepe-250"),
    ("43422", "https://www.superfarma.it/products/bamicid-30cps"),
    ("43423", "https://www.superfarma.it/products/bacche-goji-bio-150g"),
    ("43424", "https://www.superfarma.it/products/avec-30-compresse"),
    ("43427", "https://www.superfarma.it/products/barilife-proteine-450g"),
    ("43431", "https://www.superfarma.it/products/camomilla-20bust-filtro"),
    ("43433", "https://www.superfarma.it/products/catalitic-mn-cu-co-20amp"),
    ("43434", "https://www.superfarma.it/products/catalitic-oligatro-20amp"),
    ("43437", "https://www.superfarma.it/products/catalitic-ni-co-20amp"),
    ("43439", "https://www.superfarma.it/products/butyrose-fast-10-stick"),
    ("43440", "https://www.superfarma.it/products/calcocyst-30-compresse"),
    ("43441", "https://www.superfarma.it/products/cemon-catalitic-oligoelementi-bismuto-bi-20-fiale"),
    ("43442", "https://www.superfarma.it/products/chirotir-selenio-30cpr"),
    ("43446", "https://www.superfarma.it/products/climax-fast-spray-30ml"),
    ("43449", "https://www.superfarma.it/products/colplatir-30-compresse-rivestite"),
    ("43450", "https://www.superfarma.it/products/contracol-30-compresse"),
    ("43452", "https://www.superfarma.it/products/drenax-forte-cist-plus-18-stick-pack"),
    ("43454", "https://www.superfarma.it/products/echinutra-c-20-flaconcini"),
    ("43459", "https://www.superfarma.it/products/enneaphyt-9-40cpr-orosol-300mg"),
]

async def scrape_minsan(session, pid, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return pid, url, None, f"HTTP {resp.status}"
            text = await resp.text()
            # Look for product__subtitleMinsan span
            match = re.search(r'<span[^>]*class=["\']product__subtitleMinsan["\'][^>]*>([^<]+)</span>', text, re.IGNORECASE)
            if match:
                minsan = match.group(1).strip()
                # Extract numeric code
                minsan_match = re.search(r'\d{9}', minsan)
                if minsan_match:
                    return pid, url, minsan_match.group(0), None
                return pid, url, minsan, None
            return pid, url, None, "MINSAN span not found"
    except asyncio.TimeoutError:
        return pid, url, None, "timeout"
    except Exception as e:
        return pid, url, None, str(e)[:50]

async def main():
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [scrape_minsan(session, pid, url) for pid, url in URLS]
        results = await asyncio.gather(*tasks)
    
    found = 0
    not_found = 0
    errors = 0
    print("id|url|minsan|status")
    for pid, url, minsan, err in results:
        if err:
            print(f"{pid}|{url}|MISSING|{err}")
            errors += 1
        elif minsan:
            print(f"{pid}|{url}|{minsan}|OK")
            found += 1
        else:
            print(f"{pid}|{url}|MISSING|not_found")
            not_found += 1
    
    print(f"\n--- SUMMARY: found={found} not_found={not_found} errors={errors} total={len(URLS)}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
