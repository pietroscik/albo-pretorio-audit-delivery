#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Albo Pretorio scraper (OpenWeb – Comune di Avella)
- Rispetta robots.txt e applica rate-limit.
- Scarica metadati + allegati (PDF/DOC/ZIP) con filtri e range pagine.
- Paginazione robusta: link "successivo" o calcolo page/start.
- Evita doppioni, supporta resume, logga su file.

Esempi:
  # prime 50 pagine
  python albo_scraper.py --start-url "https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio_full.php?CSRF=XXXX" --out ./albo_download --max-pages 50 --delay 1.5

  # pagine 51–100 (senza CSRF)
  python albo_scraper.py --page-from 51 --page-to 100 --out ./albo_download --delay 1.5

  # solo delibere 2024, senza scaricare PDF
  python albo_scraper.py --page-from 1 --page-to 80 --only-types Delibera --date-from 2024-01-01 --date-to 2024-12-31 --no-download

Note legali:
- Non aggirare protezioni. Rispetta robots.txt, TOS e GDPR.
"""

import argparse
import ast
import csv
import json
import hashlib
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.parse as up
from dataclasses import asdict
from pathlib import Path
from typing import Optional, List, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

# Fix per il problema "I/O operation on closed pipe" di Playwright su Windows
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Importa le funzionalità dai nuovi moduli
from delibere_comunali.scraping.models import AlboItem
from delibere_comunali.scraping.utils import (
    DEFAULT_DELAY,
    DEFAULT_MAX_PAGES,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    ATTACH_EXTS,
    ATTACH_MIME_EXT,
    generate_openweb_base_url,
    slugify,
    compact_text,
    url_doc_name,
    looks_like_attachment,
    infer_tipologia_from_filename,
    infer_tipologia_from_oggetto,
    infer_tipologia_from_url,
    infer_number,
    infer_date,
    metadata_key,
    encode_query,
    page_url,
    extract_csrf,
    ensure_dir,
    polite_sleep,
    parse_date,
    within_dates,
    load_robots_allow,
    can_fetch,
    guess_next_url,
    get_comune_data
)
from delibere_comunali.scraping.parsers import parse_list_page, parse_detail_page

# Importa la funzione get_tenant_dir per supportare il sistema multi-tenant
from delibere_comunali.utils.config import get_tenant_dir

# Importiamo le nuove funzionalità per il rilevamento automatico degli adapter
from delibere_comunali.utils.adapter_detector import identify_comune_adapter
from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente

# Importiamo pandas per gestire i dati della mappatura
import pandas as pd

# Import JavaScript scraper for Halleyweb and other JS-heavy sites
from delibere_comunali.scraping.js_scraper import should_use_js_scraper, sync_scrape_page
# Importa tutti gli adapter disponibili
from delibere_comunali.scraping.adapters import (
    HalleyAdapter,
    MaggioliAdapter,
    AsmelAdapter,
    KibernetesAdapter,
    SianAdapter,
    GenericAdapter
)


OPENWEB_BASE_DEFAULT = "https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio_full.php"

# -------------- Scraper --------------
class AlboScraper:
    def __init__(self, args):
        self.args = args
        if self.args.base:
            # Se viene fornito --base, lo utilizza direttamente come percorso di output
            self.out_dir = Path(self.args.base)
        elif self.args.out:
            self.out_dir = Path(self.args.out)
        else:
            # Se non è specificato né --base né --out, usa il percorso standard basato su --ente
            self.out_dir = Path(f"data/{self.args.ente}/albo_download")
        ensure_dir(self.out_dir)
        ensure_dir(self.out_dir / "pdf")
        if args.save_html:
            ensure_dir(self.out_dir / "html")
        # log file
        self.log_path = self.out_dir / "albo_scraper.log"
        # CSV metadati
        self.csv_path = self.out_dir / "albo_metadati.csv"
        self._csv_lock = threading.Lock()
        if not self.csv_path.exists():
            with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(asdict(AlboItem("", "", "", "", "", "", "", "", [])).keys()), quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
        self.seen_metadata = self._load_seen_metadata()
        # registro URL scaricati (opzionale)
        self.downloaded_json = self.out_dir / "downloads.json"
        if self.downloaded_json.exists():
            try:
                self.downloaded = set(json.loads(self.downloaded_json.read_text(encoding="utf-8")))
            except Exception:
                self.downloaded = set()
        else:
            self.downloaded = set()

        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.headers.update({"User-Agent": args.user_agent or DEFAULT_USER_AGENT})

        # Usa l'URL fornito o genera dinamicamente l'URL in base all'ente
        if args.start_url:
            parsed = up.urlparse(args.start_url)
        else:
            # Cerca prima l'URL specifico nella mappatura
            comune_data = get_comune_data(args.ente)
            url_albo_specifico = comune_data.get('url_albo_pretorio')
            
            # Usa l'URL specifico dalla mappatura se disponibile e valido
            if (url_albo_specifico is not None and 
                pd.notna(url_albo_specifico) and 
                str(url_albo_specifico).strip() != '' and 
                str(url_albo_specifico).lower() != 'nan'):
                
                parsed = up.urlparse(str(url_albo_specifico))
            else:
                generated_url = generate_openweb_base_url(args.ente)
                parsed = up.urlparse(generated_url)
        self.base_root = f"{parsed.scheme}://{parsed.netloc}"
        self.rp = load_robots_allow(self.base_root)

        # Se page-from è impostato, costruisci URL iniziale
        if args.page_from is not None:
            page = max(1, args.page_from)
            step = args.page_step or 15
            csrf = self.bootstrap_csrf()
            
            # Se abbiamo un URL specifico che non è nel formato OpenWeb standard, dobbiamo gestirlo diversamente
            comune_data = get_comune_data(args.ente)
            url_albo_specifico = comune_data.get('url_albo_pretorio')
            
            if (url_albo_specifico is not None and 
                pd.notna(url_albo_specifico) and 
                str(url_albo_specifico).strip() != '' and 
                str(url_albo_specifico).lower() != 'nan'):
                
                # Se abbiamo un URL specifico, potrebbe non essere nel formato OpenWeb standard
                # Quindi usiamo l'URL trovato direttamente, rimuovendo eventuali parametri e mantenendo solo la base
                parsed_url = up.urlparse(str(url_albo_specifico))
                base_url_specifico = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                
                # Se l'URL contiene già parametri di paginazione, li manteniamo; altrimenti generiamo la pagina OpenWeb standard
                if 'page' in parsed_url.query or 'start' in parsed_url.query:
                    # Se contiene già parametri di paginazione, usiamo l'URL cosi com'è
                    self.current_url = str(url_albo_specifico)
                else:
                    # Altrimenti generiamo la pagina OpenWeb standard usando l'URL trovato come base
                    # Ma solo se l'URL trovato sembra essere nel formato OpenWeb
                    if 'openweb' in str(url_albo_specifico).lower() or 'mc_p_ricerca' in str(url_albo_specifico).lower():
                        # L'URL trovato è già nel formato corretto, lo usiamo così com'è
                        self.current_url = str(url_albo_specifico)
                    else:
                        # Come fallback, proviamo a generare un URL OpenWeb standard usando l'host trovato
                        self.current_url = page_url(page, step=step, csrf=csrf, base_url=f"{parsed_url.scheme}://{parsed_url.netloc}/openweb/albo/albo_pretorio_full.php")
            else:
                # Se non abbiamo un URL specifico, usiamo il comportamento standard
                self.current_url = page_url(page, step=step, csrf=csrf, base_url=self.base_root + "/openweb/albo/albo_pretorio_full.php")
            
            # forza max_pages = page_to - page + 1 se specificato
            if args.page_to is not None and args.page_to >= page:
                self.max_pages = args.page_to - page + 1
            else:
                self.max_pages = args.max_pages
        else:
            self.current_url = args.start_url
            self.max_pages = args.max_pages

        self.delay = args.delay
        self.timeout = args.timeout

        # Prepara filtri
        self.only_types = set([t.strip().lower() for t in (args.only_types or "").split(",") if t.strip()]) or None
        self.exclude_types = set([t.strip().lower() for t in (args.exclude_types or "").split(",") if t.strip()]) or None
        self.title_rx = re.compile(args.title_regex, re.I) if args.title_regex else None
        self.dfrom = parse_date(args.date_from) if args.date_from else None
        self.dto = parse_date(args.date_to) if args.date_to else None

    def _load_seen_metadata(self) -> set:
        seen = set()
        if not self.csv_path.exists():
            return seen
        try:
            with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    key = self._metadata_key_from_row(row)
                    if key:
                        seen.add(key)
                    dettaglio = (row.get("dettaglio_url") or "").strip()
                    if dettaglio:
                        seen.add(dettaglio)
                    # Aggiungi anche l'hash dei metadati per una deduplicazione più robusta
                    try:
                        it = AlboItem(
                            page_url=row.get("page_url", ""),
                            titolo=row.get("titolo", ""),
                            numero=row.get("numero"),
                            data_pubblicazione=row.get("data_pubblicazione"),
                            tipologia=row.get("tipologia"),
                            ufficio=row.get("ufficio", ""),
                            oggetto=row.get("oggetto", ""),
                            dettaglio_url=row.get("dettaglio_url", ""),
                        )
                        metadata_hash = self._generate_metadata_hash(it)
                        seen.add(f"hash:{metadata_hash}")
                    except Exception:
                        pass
        except Exception:
            pass
        return seen

    @staticmethod
    def _parse_allegati_field(raw: Optional[str]) -> List[str]:
        if not raw:
            return []
        txt = str(raw).strip()
        if not txt:
            return []
        for parser in (ast.literal_eval, json.loads):
            try:
                val = parser(txt)
                if isinstance(val, list):
                    return [str(x).strip() for x in val if str(x).strip()]
            except Exception:
                pass
        if ";" in txt:
            return [x.strip() for x in txt.split(";") if x.strip()]
        if "|" in txt:
            return [x.strip() for x in txt.split("|") if x.strip()]
        return [txt]

    def _metadata_key_from_row(self, row: dict) -> str:
        dettaglio_url = (row.get("dettaglio_url") or "").strip()
        if dettaglio_url:
            return dettaglio_url
        allegati = self._parse_allegati_field(row.get("allegati"))
        if allegati:
            return allegati[0]
        raw = "|".join([
            row.get("titolo") or "",
            row.get("numero") or "",
            row.get("data_pubblicazione") or "",
            row.get("oggetto") or "",
        ])
        # Usa SHA-256 invece di SHA1 per motivi di sicurezza
        return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()

    def bootstrap_csrf(self) -> Optional[str]:
        """Apre la pagina base per ottenere eventuale token CSRF richiesto da OpenWeb."""
        try:
            # Cerca prima l'URL specifico nella mappatura
            comune_data = get_comune_data(self.args.ente)
            url_albo_specifico = comune_data.get('url_albo_pretorio')
            
            # Usa l'URL specifico dalla mappatura se disponibile e valido
            if (url_albo_specifico is not None and 
                pd.notna(url_albo_specifico) and 
                str(url_albo_specifico).strip() != '' and 
                str(url_albo_specifico).lower() != 'nan'):
                
                base_url = str(url_albo_specifico)
                self.log(f"[sessione] Usando URL specifico dalla mappatura: {base_url}")
            else:
                # Altrimenti usa l'URL generato dinamicamente in base all'ente
                base_url = generate_openweb_base_url(self.args.ente)
                self.log(f"[sessione] Usando URL generato dinamicamente: {base_url}")
            
            # Prova prima con l'URL disponibile
            if not can_fetch(self.rp, base_url, self.args.user_agent or DEFAULT_USER_AGENT):
                self.log(f"[sessione] Accesso vietato da robots.txt: {base_url}")
            
            try:
                r = self.session.get(base_url, timeout=self.args.timeout)
                r.raise_for_status()
                r.encoding = r.apparent_encoding or r.encoding
                csrf = extract_csrf(r.text, r.url)
                if csrf:
                    self.log("[sessione] CSRF recuperato dalla pagina base")
                return csrf
            except requests.exceptions.RequestException as e:
                # Se l'URL non funziona, prova con altre strategie
                self.log(f"[sessione] Errore con URL ({base_url}): {e}")
                
                # Se stiamo usando l'URL generato e non quello specifico, proviamo anche la homepage
                if 'generate_openweb_base_url' in base_url or self.args.ente.lower() in base_url:
                    homepage_url = f"https://www.comune.{self.args.ente.lower()}.{self.infer_provincia_from_ente(self.args.ente)}.it"
                    try:
                        self.log(f"[sessione] Tentativo con homepage: {homepage_url}")
                        r_home = self.session.get(homepage_url, timeout=self.args.timeout)
                        r_home.raise_for_status()
                        
                        # Cerca link all'albo pretorio nella homepage
                        soup = BeautifulSoup(r_home.text, 'html.parser')
                        albo_links = soup.find_all('a', href=True)
                        
                        # Cerca parole chiave che potrebbero indicare l'albo pretorio
                        keywords = ['albo', 'albopretorio', 'trasparenza', 'atti', 'pubblicazioni']
                        for link in albo_links:
                            href = link['href']
                            text = link.get_text().lower()
                            
                            if any(keyword in text or keyword in href.lower() for keyword in keywords):
                                full_url = up.urljoin(homepage_url, href)
                                self.log(f"[sessione] Trovato possibile link albo: {full_url}")
                                
                                # Prova questo URL
                                r_albo = self.session.get(full_url, timeout=self.args.timeout)
                                r_albo.raise_for_status()
                                
                                csrf = extract_csrf(r_albo.text, r_albo.url)
                                if csrf:
                                    self.log(f"[sessione] CSRF recuperato da: {r_albo.url}")
                                    return csrf
                                    
                    except requests.exceptions.RequestException:
                        self.log(f"[sessione] Impossibile accedere alla homepage: {homepage_url}")
                
                return None
        except Exception as e:
            self.log(f"[sessione] impossibile recuperare CSRF dalla pagina base: {e}")
            return None

    def infer_provincia_from_ente(self, ente: str) -> str:
        """Inferisce la provincia dal nome dell'ente, usando la mappatura esistente."""
        # Questa è una versione semplificata - idealmente dovrebbe usare la mappatura completa
        ente_lower = ente.lower()
        
        # Province campana
        if any(x in ente_lower for x in ['avellino', 'av', 'baiano', 'tufino', 'summonte', 'santangelo', 'solofra']):
            return 'av'
        elif any(x in ente_lower for x in ['napoli', 'na', 'pozzuoli', 'ercolano', 'torreannunziata', 'torredelgreco', 'meta', 'castellammare', 'acerra', 'afragola']):
            return 'na'
        elif any(x in ente_lower for x in ['salerno', 'sa', 'eboli', 'battipaglia', 'scafati', 'nocera', 'pagani']):
            return 'sa'
        elif any(x in ente_lower for x in ['benevento', 'bn']):
            return 'bn'
        elif any(x in ente_lower for x in ['caserta', 'ce']):
            return 'ce'
        
        # Province lazio
        elif any(x in ente_lower for x in ['roma', 'rm', 'frosinone', 'fr', 'latina', 'lt', 'rieti', 'ri', 'viterbo', 'vt']):
            return 'rm'  # Per Roma usiamo rm come esempio
        
        # Province emilia-romagna
        elif any(x in ente_lower for x in ['bologna', 'bo', 'modena', 'mo', 'parma', 'pr', 'piacenza', 'pc']):
            return 'bo'
        
        # Province lombardia
        elif any(x in ente_lower for x in ['milano', 'mi', 'bergamo', 'bg', 'brescia', 'bs', 'como', 'co']):
            return 'mi'
        
        # Province veneto
        elif any(x in ente_lower for x in ['venezia', 've', 'verona', 'vr', 'vicenza', 'vi', 'treviso', 'tv']):
            return 've'
        
        # Province piemonte
        elif any(x in ente_lower for x in ['torino', 'to', 'novara', 'no', 'asti', 'at']):
            return 'to'
        
        # Di default, tentativo con abbreviazione standard
        province_mapping = {
            'av': 'av', 'ba': 'ba', 'bn': 'bn', 'ce': 'ce', 'fi': 'fi', 'ge': 'ge', 
            'mi': 'mi', 'na': 'na', 'pd': 'pd', 'rm': 'rm', 'to': 'to', 've': 've',
            'al': 'al', 'ao': 'ao', 'ar': 'ar', 'at': 'at', 'bg': 'bg', 'bi': 'bi',
            'bl': 'bl', 'bn': 'bn', 'bo': 'bo', 'br': 'br', 'bs': 'bs', 'bz': 'bz',
            'ca': 'ca', 'cb': 'cb', 'ce': 'ce', 'ch': 'ch', 'ci': 'ci', 'cl': 'cl',
            'cn': 'cn', 'co': 'co', 'cr': 'cr', 'cs': 'cs', 'ct': 'ct', 'cz': 'cz',
            'en': 'en', 'fc': 'fc', 'fe': 'fe', 'fg': 'fg', 'fi': 'fi', 'fm': 'fm',
            'fr': 'fr', 'ge': 'ge', 'go': 'go', 'gr': 'gr', 'im': 'im', 'is': 'is',
            'kr': 'kr', 'lc': 'lc', 'le': 'le', 'li': 'li', 'lo': 'lo', 'lt': 'lt',
            'lu': 'lu', 'mb': 'mb', 'mc': 'mc', 'me': 'me', 'mi': 'mi', 'mn': 'mn',
            'mo': 'mo', 'ms': 'ms', 'mt': 'mt', 'na': 'na', 'no': 'no', 'nu': 'nu',
            'og': 'og', 'or': 'or', 'ot': 'ot', 'pa': 'pa', 'pc': 'pc', 'pd': 'pd',
            'pe': 'pe', 'pg': 'pg', 'pi': 'pi', 'pn': 'pn', 'po': 'po', 'pr': 'pr',
            'pt': 'pt', 'pu': 'pu', 'pv': 'pv', 'pz': 'pz', 'ra': 'ra', 'rc': 'rc',
            're': 're', 'rg': 'rg', 'ri': 'ri', 'rm': 'rm', 'rn': 'rn', 'ro': 'ro',
            'sa': 'sa', 'si': 'si', 'so': 'so', 'sp': 'sp', 'sr': 'sr', 'ss': 'ss',
            'sv': 'sv', 'ta': 'ta', 'te': 'te', 'tn': 'tn', 'to': 'to', 'tp': 'tp',
            'tr': 'tr', 'ts': 'ts', 'tv': 'tv', 'ud': 'ud', 'va': 'va', 'vb': 'vb',
            'vc': 'vc', 've': 've', 'vi': 'vi', 'vr': 'vr', 'vs': 'vs', 'vt': 'vt',
            'vv': 'vv'
        }
        
        # Se il nome dell'ente contiene una sigla di provincia, usala
        for sigla in province_mapping.keys():
            if sigla in ente_lower:
                return sigla
        
        # Di default, prova con 'rm' per Roma e 'mi' per Milano come esempi comuni
        if 'roma' in ente_lower:
            return 'rm'
        elif 'milano' in ente_lower:
            return 'mi'
        
        # Altrimenti, prova 'rm' come default
        return 'rm'

    def log(self, msg: str):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def fetch(self, url: str) -> Optional[str]:
        """Recupera HTML da URL con gestione errori/retry."""
        try:
            # Check if this is a JavaScript-heavy site that requires special handling
            if should_use_js_scraper(url):
                print(f"DEBUG: Using JavaScript-aware scraper for {url}")
                js_result = sync_scrape_page(url)
                if js_result:
                    # Combine static URLs extracted via JS with the HTML content
                    # Return the fully rendered HTML
                    return js_result.html_content
                else:
                    print(f"WARNING: JavaScript scraper failed for {url}, falling back to requests")
            
            # Fallback to regular requests
            with self.session.get(url, timeout=self.timeout) as r:
                r.raise_for_status()
                # Prova diversi encoding
                for enc in (r.apparent_encoding, "utf-8", "iso-8859-1"):
                    try:
                        return r.text.encode().decode(enc or "utf-8")
                    except (UnicodeDecodeError, LookupError):
                        continue
                return r.text  # fallback
        except Exception as e:
            self.log(f"[error] fetch: {url} - {e}")
            return None

    def write_metadata_once(self, it: AlboItem) -> bool:
        key = metadata_key(it)
        with self._csv_lock:
            if key in self.seen_metadata:
                return False
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(asdict(it).keys()), quoting=csv.QUOTE_MINIMAL)
                w.writerow(asdict(it))
            self.seen_metadata.add(key)
            if it.dettaglio_url:
                self.seen_metadata.add(it.dettaglio_url)
            for attachment in it.allegati:
                if attachment:
                    self.seen_metadata.add(attachment)
        return True

    def item_passes_filters(self, it: AlboItem) -> bool:
        # tipo
        if self.only_types and (it.tipologia or "").lower() not in self.only_types:
            return False
        if self.exclude_types and (it.tipologia or "").lower() in self.exclude_types:
            return False
        # date
        if not within_dates(it.data_pubblicazione, self.dfrom, self.dto):
            return False
        # titolo/oggetto regex
        txt = (it.titolo or "") + " " + (it.oggetto or "")
        if self.title_rx and not self.title_rx.search(txt):
            return False
        return True

    def enrich_item(self, it: AlboItem):
        """Arricchisce l'item con dati aggiuntivi come geolocalizzazione, categorie derivate, ecc."""
        # In questa implementazione di base, possiamo arricchire con informazioni 
        # derivate dai dati esistenti o con dati del comune
        if not it.provincia and hasattr(self, 'comune_data'):
            # Usa i dati del comune già caricati nel costruttore
            comune_data = self.comune_data
            if comune_data and 'provincia' in comune_data:
                it.provincia = comune_data['provincia']
                
        # Arricchimento con dati derivati
        if it.oggetto and not it.titolo:
            # Se abbiamo l'oggetto ma non il titolo, usiamo i primi 150 caratteri dell'oggetto
            it.titolo = it.oggetto[:150] + ("..." if len(it.oggetto) > 150 else "")
            
        # Normalizzazione dei dati
        if it.titolo:
            it.titolo = it.titolo.strip()
        if it.oggetto:
            it.oggetto = it.oggetto.strip()
        if it.tipologia:
            it.tipologia = it.tipologia.strip().title()  # Capitalize first letter of each word
            
        # Aggiungi eventuali logiche di arricchimento specifiche per l'ente o per il tipo di atto
        # Qui possiamo aggiungere logiche specifiche per Halley, OpenWeb, ecc.
        if hasattr(self, 'ente_details') and self.ente_details:
            it.ente_nome = self.ente_details.get('nome_comune', '')
            it.ente_codice_istat = self.ente_details.get('codice_istat', '')

    def run(self):
        current_url = self.current_url
        visited_pages = 0
        visited_urls = set()

        while current_url and visited_pages < self.max_pages:
            if current_url in visited_urls:
                self.log(f"[stop] URL pagina gia' visitato: {current_url}")
                break
            visited_urls.add(current_url)
            self.log(f"[pagina] {visited_pages+1}: {current_url}")
            try:
                html = self.fetch(current_url)
            except requests.HTTPError as e:
                self.log(f"[http] {e}")
                break
            except Exception as e:
                self.log(f"[fatal] {e}")
                break
            if not html:
                break

            # Usa l'adapter selezionato per lo scraping
            adapter = self._get_adapter()
            items, next_url = adapter.scrape_metadata(current_url)
            
            # Se l'adapter non ha trovato nulla, prova con il parser generico
            if not items and not next_url:
                items, next_url = parse_list_page(html, current_url)

            if not items:
                self.log("[stop] nessun atto trovato nella pagina corrente")
                break

            for it in items:
                try:
                    # Salta l'atto se è già stato scaricato e indicizzato in precedenza
                    # MA SOLO SE anche i file PDF esistono fisicamente
                    skip_item = False
                    metadata_hash = self._generate_metadata_hash(it)
                    if it.dettaglio_url and (it.dettaglio_url in self.seen_metadata or f"hash:{metadata_hash}" in self.seen_metadata):
                        # Verifichiamo se esistono file PDF associati a questo documento
                        pdf_exists = False
                        
                        # Controlliamo se esistono PDF con nomi basati sugli allegati
                        for allegato_url in it.allegati or []:
                            filename = up.urlparse(allegato_url).path.split('/')[-1]
                            if filename:  # Assicuriamoci che il filename non sia vuoto
                                # Costruiamo il nome del file come verrebbe generato dallo scraper
                                doc_name = os.path.splitext(filename)[0]
                                stem = slugify(f"{it.tipologia or 'atto'}_{it.numero or ''}_{it.data_pubblicazione or ''}_{doc_name or it.titolo}")[:100]
                                ext = os.path.splitext(filename)[1] or ".pdf"
                                expected_pdf_path = self.out_dir / "pdf" / f"{stem}_1{ext}"
                                
                                # Controlliamo anche per nomi simili con numeri diversi (se ci sono più allegati)
                                for i in range(1, 10):  # Controlliamo fino a 9 allegati
                                    numbered_pdf_path = self.out_dir / "pdf" / f"{stem}_{i}{ext}"
                                    if numbered_pdf_path.exists():
                                        pdf_exists = True
                                        break
                                if pdf_exists:
                                    break
                        
                        # Se non abbiamo ancora verificato con allegati, controlliamo comunque
                        # se esiste un file basato sull'ID del documento
                        if not pdf_exists and it.dettaglio_url:
                            # Estrai l'ID dal dettaglio URL (es. id=49804)
                            from urllib.parse import parse_qs
                            parsed_url = up.urlparse(it.dettaglio_url)
                            params = parse_qs(parsed_url.query)
                            doc_ids = params.get('id', [])
                            
                            # Controlliamo tutti gli ID trovati nell'URL
                            for doc_id in doc_ids:
                                if doc_id:
                                    # Cerchiamo file PDF che contengano l'ID del documento
                                    try:
                                        pdf_files = os.listdir(self.out_dir / "pdf")
                                        for filename in pdf_files:
                                            if filename.endswith('.pdf') and doc_id in filename:
                                                pdf_exists = True
                                                break
                                        if pdf_exists:
                                            break
                                    except FileNotFoundError:
                                        # La directory PDF non esiste ancora
                                        pass
                        
                        # Solo se troviamo file PDF associati, consideriamo il documento come realmente archiviato
                        if pdf_exists:
                            skip_item = True
                    
                    if skip_item:
                        self.log(f"  [skip] Già in archivio: {it.dettaglio_url}")
                        continue

                    # dettaglio
                    if it.dettaglio_url:
                        d_html = self.fetch(it.dettaglio_url)
                        if d_html:
                            ogg, uff, allegati = parse_detail_page(d_html, it.dettaglio_url)
                            it.oggetto = ogg or it.oggetto
                            it.ufficio = uff or it.ufficio
                            it.allegati = allegati
                            if self.args.save_html:
                                name = slugify(it.titolo or f"item_{it.numero or ''}") + ".html"
                                (self.out_dir / "html" / name).write_text(d_html, encoding="utf-8", errors="ignore")

                    self.enrich_item(it)

                    # filtri a valle (dopo aver popolato oggetto/ufficio)
                    if not self.item_passes_filters(it):
                        continue

                    # salva metadati
                    self.write_metadata_once(it)

                    # Scarica allegati
                    for i, url in enumerate(allegati):
                        if args.no_download:
                            break
                        if args.max_attachments_per_item and i >= args.max_attachments_per_item:
                            break

                        # Gestisci duplicati
                        url_key = url_doc_name(url)
                        if url_key in self.downloaded:
                            self.log(f"  [skip] Già scaricato: {url_key}")
                            continue

                        # Gestisci rate limiting
                        polite_sleep(self.delay)

                        try:
                            # Check if this is a javascript_handler (special case for Halleyweb)
                            if url.startswith('javascript_handler:'):
                                # This indicates an element that needs to be clicked via Playwright
                                if should_use_js_scraper(it.dettaglio_url):  # Use the detail page URL to determine if it's Halleyweb
                                    from .js_scraper import download_attachments_sync
                                    # Download attachments from the detail page itself (where the element exists)
                                    downloaded_files = download_attachments_sync(it.dettaglio_url, str(self.out_dir / "pdf"))
                                    if downloaded_files:
                                        for downloaded_file in downloaded_files:
                                            self.downloaded.add(url_doc_name(downloaded_file))
                                            self.log(f"  [download] File scaricato via Playwright click: {Path(downloaded_file).name}")
                                    else:
                                        self.log(f"  [warning] No attachments downloaded from detail page: {it.dettaglio_url}")
                            # Check if this is a Halleyweb site and use download interception
                            elif should_use_js_scraper(url):
                                from .js_scraper import download_attachments_sync
                                downloaded_files = download_attachments_sync(url, str(self.out_dir / "pdf"))
                                if downloaded_files:
                                    for downloaded_file in downloaded_files:
                                        self.downloaded.add(url_doc_name(downloaded_file))
                                        self.log(f"  [download] File scaricato via Playwright: {Path(downloaded_file).name}")
                                else:
                                    # If Playwright download didn't work, fall back to adapter download
                                    adapter = self._get_adapter()
                                    downloaded_files = adapter.download_attachment(url, str(self.out_dir / "pdf"))
                                    if downloaded_files:
                                        for file_path in downloaded_files:
                                            self.downloaded.add(url_doc_name(file_path))
                                            self.log(f"  [download] File scaricato via adapter: {Path(file_path).name}")
                            else:
                                # Use adapter for regular download
                                adapter = self._get_adapter()
                                downloaded_files = adapter.download_attachment(url, str(self.out_dir / "pdf"))
                                if downloaded_files:
                                    for file_path in downloaded_files:
                                        self.downloaded.add(url_doc_name(file_path))
                                        self.log(f"  [download] File scaricato via adapter: {Path(file_path).name}")
                        except Exception as e:
                            self.log(f"[error] Impossibile scaricare {url}: {e}")

                except KeyboardInterrupt:
                    self.log("Interrotto dall'utente.")
                    sys.exit(1)
                except Exception as e:
                    self.log(f"[warn] errore su item: {e}")

            visited_pages += 1
            current_url = next_url

        self.log(f"Completato. CSV: {self.csv_path} | PDF: {self.out_dir / 'pdf'}")

    def download_file(self, url: str, dest: Path):
        """Scarica un file da un URL a una destinazione specificata."""
        # Assicurati che la directory di destinazione esista
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Verifica se il file è già stato scaricato
        if url in self.downloaded:
            return
            
        # Rispetta le regole robots.txt
        if hasattr(self, 'rp') and self.rp:
            from urllib.robotparser import RobotFileParser
            if not can_fetch(self.rp, url, self.args.user_agent or DEFAULT_USER_AGENT):
                self.log(f"[robots] Vietato da robots.txt: {url}")
                return
        
        # Effettua il download
        try:
            import time
            # Aggiungi un piccolo delay per essere gentili col server
            time.sleep(0.5)
            
            with self.session.get(url, timeout=self.timeout) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            
            # Registra il download completato
            self.downloaded.add(url)
            try:
                self.downloaded_json.write_text(json.dumps(sorted(list(self.downloaded))), encoding="utf-8")
            except Exception:
                pass
                
            self.log(f"  [download] File scaricato: {dest.name}")
            
        except Exception as e:
            self.log(f"[error] Impossibile scaricare {url}: {e}")


# -------------- CLI --------------

    def _get_adapter(self):
        """
        Seleziona l'adapter appropriato in base al provider del comune.
        """
        # Rileva l'adapter in base all'URL
        adapter_info = identify_comune_adapter(
            nome_comune=self.args.ente,
            url_istituzionale="",
            url_albo=self.current_url
        )
        
        adapter_name = adapter_info['adapter_principale']
        
        # Mappa dei nomi adapter alle classi
        adapter_map = {
            'halley_adapter': HalleyAdapter,
            'maggioli_adapter': MaggioliAdapter,
            'asmel_adapter': AsmelAdapter,
            'kibernetes_adapter': KibernetesAdapter,
            'sian_adapter': SianAdapter,
        }
        
        # Seleziona l'adapter o usa GenericAdapter come fallback
        AdapterClass = adapter_map.get(adapter_name, GenericAdapter)
        return AdapterClass(timeout=self.timeout * 1000, max_retries=3)

def build_parser():
    ap = argparse.ArgumentParser(description="Scraper Albo Pretorio (OpenWeb)")
    ap.add_argument("--ente", default="avella", help="Nome dell'ente per gestire cartelle separate (es. avella, tufino).")
    ap.add_argument("--base", default=None, help="Percorso base dei dati (per compatibilità con altri moduli).")
    ap.add_argument("--start-url", help="URL iniziale (lista atti). Ignorato se usi --page-from.")
    ap.add_argument("--out", default=None, help="Cartella di output (default: data/{ente}/albo_download).")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Numero max pagine da seguire.")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay (s) tra richieste.")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout richieste (s).")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent HTTP (metti contatto/PEC).")

    # Range di pagine
    ap.add_argument("--page-from", type=int, default=None, help="Pagina iniziale (costruisce URL base OpenWeb).")
    ap.add_argument("--page-to", type=int, default=None, help="Pagina finale (inclusa).")
    ap.add_argument("--page-step", type=int, default=15, help="Passo 'start' per pagina (default 15).")

    # Filtri
    ap.add_argument("--only-types", help="Esempio: 'Delibera,Determinazione'")
    ap.add_argument("--exclude-types", help="Esempio: 'Avviso,Bando'")
    ap.add_argument("--date-from", help="YYYY-MM-DD o DD/MM/YYYY")
    ap.add_argument("--date-to", help="YYYY-MM-DD o DD/MM/YYYY")
    ap.add_argument("--title-regex", help="Regex su titolo/oggetto (es. 'bilancio|rendiconto')")

    # Download comportamenti
    ap.add_argument("--no-download", action="store_true", help="Non scaricare allegati (solo CSV).")
    ap.add_argument("--max-attachments-per-item", type=int, default=None, help="Limita n. allegati per atto.")
    ap.add_argument("--save-html", action="store_true", help="Salva HTML del dettaglio per debug.")
    return ap

def main():
    args = build_parser().parse_args()

    # Ottieni i dati del comune dalla mappatura
    comune_data = get_comune_data(args.ente)
    
    # Se --ente è specificato ma non --start-url né --page-from, 
    # usiamo l'URL specifico dalla mappatura o generiamo automaticamente
    if not args.start_url and args.page_from is None:
        # Se abbiamo un URL specifico per l'albo pretorio, usalo
        url_albo = comune_data.get('url_albo_pretorio')
        
        # Controllo semplificato: verifica se l'URL esiste ed è valido
        if pd.notna(url_albo) and isinstance(url_albo, str) and url_albo.strip():
            args.start_url = url_albo.strip()  # Assicuriamoci che sia una stringa pulita
            print(f"DEBUG: Usando URL specifico per l'albo pretorio di '{args.ente}' dalla mappatura: {args.start_url}")
        else:
            # Altrimenti genera l'URL in base al nome ente
            args.start_url = generate_openweb_base_url(args.ente)
            print(f"DEBUG: Usando URL generato automaticamente per l'ente '{args.ente}': {args.start_url}")

    # Precondizioni minme
    if args.page_from is None and not args.start_url:
        print("Errore: specifica --start-url oppure --page-from/--page-to.", file=sys.stderr)
        sys.exit(2)

    scraper = AlboScraper(args)
    try:
        scraper.run()
    except requests.HTTPError as e:
        print(f"[http] {e}")
        sys.exit(2)
    except Exception as e:
        print(f"[fatal] {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
