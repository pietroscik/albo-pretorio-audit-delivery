"""
Generic Adapter - Fallback per enti con provider sconosciuti o non supportati.
Utilizza solo requests + BeautifulSoup (nessuna dipendenza da Playwright).
"""
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import urllib.parse as up

import requests
from bs4 import BeautifulSoup

from ..models import AlboItem
from ..utils import looks_like_attachment, url_doc_name


class GenericAdapter:
    """
    Adapter generico per enti con provider sconosciuti.
    Implementa:
    - Scraping metadati con requests
    - Download diretto di allegati (se l'URL punta a un file)
    - Fallback per qualsiasi struttura HTML
    """
    
    def __init__(self, timeout: int = 30000, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _make_request(self, url: str) -> Optional[str]:
        """Esegue una richiesta HTTP con retry e timeout."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout//1000)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"Errore nella richiesta a {url}: {e}")
                    return None
                # Aspetta esponenzialmente
                import time
                time.sleep((attempt + 1) * 2)
        return None
    
    def is_generic_url(self, url: str) -> bool:
        """Verifica se un URL non appartiene a provider noti."""
        # Elenco di pattern per provider noti (da escludere)
        known_patterns = [
            'halleyweb', 'openweb', 'halleyinformatica',
            'maggioli', 'siap', 'asmel', 'kibernetes',
            'sian', 'webgis', 'portaletrasparenza.gov.it'
        ]
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in known_patterns)
    
    def scrape_metadata(self, url: str) -> Tuple[List[AlboItem], Optional[str]]:
        """
        Scraping generico dei metadati da una pagina di albo pretorio.
        Supporta:
        - Tabelle HTML
        - Liste (<ul>, <ol>, <li>)
        - Div con classe 'albo', 'atti', 'documenti', ecc.
        """
        html = self._make_request(url)
        if not html:
            return [], None
        
        soup = BeautifulSoup(html, "html.parser")
        items: List[AlboItem] = []
        
        # Prova 1: Cerca tabelle (formato più comune)
        tables = soup.find_all('table')
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Salta l'intestazione
                    item = self._parse_table_row(row, url)
                    if item:
                        items.append(item)
        
        # Prova 2: Cerca liste
        if not items:
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                for li in lst.find_all('li'):
                    item = self._parse_list_item(li, url)
                    if item:
                        items.append(item)
        
        # Prova 3: Cerca div con classi specifiche
        if not items:
            albo_divs = soup.find_all('div', class_=re.compile(r'albo|atti|documenti|allegati', re.I))
            for div in albo_divs:
                item = self._parse_div(div, url)
                if item:
                    items.append(item)
        
        # Prova 4: Cerca tutti i link che sembrano documenti
        if not items:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                item = self._parse_link(link, url)
                if item:
                    items.append(item)
        
        # Trova il link "successivo" per la paginazione
        next_link = self._find_next_page_link(soup, url)
        
        return items, next_link
    
    def _parse_table_row(self, row, base_url: str) -> Optional[AlboItem]:
        """Parsing di una riga di tabella."""
        a = row.find('a', href=True)
        if not a:
            return None
        
        href = up.urljoin(base_url, a['href'])
        tds = row.find_all('td')
        
        if len(tds) >= 3:
            # Estrai testo da tutte le celle
            colonne = [td.get_text(separator=" ", strip=True) for td in tds]
            row_text = " ".join(colonne)
            
            # Oggetto = colonna più lunga
            oggetto_val = max(colonne, key=len) if colonne else ""
            titolo_val = oggetto_val[:150] + ("..." if len(oggetto_val) > 150 else "")
            
            # Estrai data (formato GG/MM/AAAA o AAAA-MM-GG)
            data_val = self._extract_date(row_text)
            
            # Estrai numero
            numero_val = self._extract_numero(row_text)
            
            # Estrai tipologia
            tipologia_val = self._extract_tipologia(row_text)
            
            # Estrai ufficio
            ufficio_val = self._extract_ufficio(colonne)
            
            return AlboItem(
                page_url=base_url,
                titolo=titolo_val or "Senza titolo",
                numero=numero_val,
                data_pubblicazione=data_val,
                tipologia=tipologia_val,
                ufficio=ufficio_val,
                oggetto=oggetto_val,
                dettaglio_url=href,
            )
        
        return None
    
    def _parse_list_item(self, li, base_url: str) -> Optional[AlboItem]:
        """Parsing di un elemento di lista."""
        a = li.find('a', href=True)
        if not a:
            return None
        
        href = up.urljoin(base_url, a['href'])
        text = li.get_text(separator=" ", strip=True)
        
        # Estrai data e numero dal testo
        data_val = self._extract_date(text)
        numero_val = self._extract_numero(text)
        tipologia_val = self._extract_tipologia(text)
        
        return AlboItem(
            page_url=base_url,
            titolo=text[:150] + ("..." if len(text) > 150 else ""),
            numero=numero_val,
            data_pubblicazione=data_val,
            tipologia=tipologia_val,
            ufficio="",
            oggetto=text,
            dettaglio_url=href,
        )
    
    def _parse_div(self, div, base_url: str) -> Optional[AlboItem]:
        """Parsing di un div."""
        a = div.find('a', href=True)
        if not a:
            return None
        
        href = up.urljoin(base_url, a['href'])
        text = div.get_text(separator=" ", strip=True)
        
        data_val = self._extract_date(text)
        numero_val = self._extract_numero(text)
        tipologia_val = self._extract_tipologia(text)
        
        return AlboItem(
            page_url=base_url,
            titolo=text[:150] + ("..." if len(text) > 150 else ""),
            numero=numero_val,
            data_pubblicazione=data_val,
            tipologia=tipologia_val,
            ufficio="",
            oggetto=text,
            dettaglio_url=href,
        )
    
    def _parse_link(self, link, base_url: str) -> Optional[AlboItem]:
        """Parsing di un link generico."""
        href = up.urljoin(base_url, link['href'])
        text = link.get_text(separator=" ", strip=True)
        
        # Verifica se il link punta a un documento
        if not looks_like_attachment(href):
            return None
        
        data_val = self._extract_date(text)
        numero_val = self._extract_numero(text)
        tipologia_val = self._extract_tipologia(text)
        
        return AlboItem(
            page_url=base_url,
            titolo=text[:150] + ("..." if len(text) > 150 else ""),
            numero=numero_val,
            data_pubblicazione=data_val,
            tipologia=tipologia_val,
            ufficio="",
            oggetto=text,
            dettaglio_url=href,
        )
    
    def _find_next_page_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Trova il link per la pagina successiva."""
        # Cerca link con testo "successiva", "next", ">", ecc.
        next_patterns = [
            r'successiva', r'successivo', r'pagina\s+successiva',
            r'avanti', r'>', r'next', r'>>', r'pagina\s+\d+'
        ]
        
        for pattern in next_patterns:
            a = soup.find('a', string=re.compile(pattern, re.I))
            if a and a.get('href'):
                return up.urljoin(base_url, a['href'])
        
        # Cerca immagini con freccia
        img = soup.find('img', alt=re.compile(r'successiva|next|>', re.I))
        if img and img.find_parent('a') and img.find_parent('a').get('href'):
            return up.urljoin(base_url, img.find_parent('a')['href'])
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Estrae una data dal testo."""
        # Formato GG/MM/AAAA
        match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if match:
            return match.group(1)
        
        # Formato AAAA-MM-GG
        match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if match:
            return match.group(1)
        
        # Formato con parole (es. "15 gennaio 2025")
        match = re.search(r'\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})\b', text, re.I)
        if match:
            return f"{match.group(1)}/{self._month_to_num(match.group(2))}/{match.group(3)}"
        
        return None
    
    def _month_to_num(self, month: str) -> str:
        """Converte il nome del mese in numero."""
        months = {
            'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
            'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
            'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
        }
        return months.get(month.lower(), '01')
    
    def _extract_numero(self, text: str) -> Optional[str]:
        """Estrae un numero di documento dal testo."""
        # Formato "N. 123" o "Numero: 123"
        match = re.search(r'\b(n\.?|numero)\s*[:\s]*([0-9/]+)\b', text, re.I)
        if match:
            return match.group(2)
        
        # Formato "123/2025"
        match = re.search(r'\b(\d+)/20\d{2}\b', text)
        if match:
            return match.group(1)
        
        # Formato "Delibera n. 123"
        match = re.search(r'\b(delibera|determinazione|ordinanza)\s+n\.?\s*(\d+)\b', text, re.I)
        if match:
            return match.group(2)
        
        return None
    
    def _extract_tipologia(self, text: str) -> Optional[str]:
        """Estrae la tipologia di documento dal testo."""
        tipologie = [
            'Delibera', 'Determinazione', 'Ordinanza', 'Decreto',
            'Avviso', 'Bando', 'Attestazione', 'Visto Contabile'
        ]
        
        for tipologia in tipologie:
            if re.search(r'\b' + re.escape(tipologia) + r'\b', text, re.I):
                return tipologia
        
        return None
    
    def _extract_ufficio(self, colonne: List[str]) -> str:
        """Estrae l'ufficio dal testo delle colonne."""
        for col in colonne:
            if re.search(r'\b(ufficio|area|settore)\b', col, re.I):
                return re.sub(r'\b(ufficio|area|settore)\s*[:\s]*', '', col, flags=re.I).strip()
        return ""
    
    def download_attachment(self, url: str, download_dir: str) -> List[str]:
        """
        Download diretto di un allegato se l'URL punta a un file.
        """
        downloaded_files = []
        
        # Verifica se l'URL punta a un file
        if not looks_like_attachment(url):
            # Prova a visitare la pagina e cercare link a file
            html = self._make_request(url)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all('a', href=True):
                    href = up.urljoin(url, a['href'])
                    if looks_like_attachment(href):
                        file_path = self._download_file(href, download_dir)
                        if file_path:
                            downloaded_files.append(file_path)
            return downloaded_files
        
        # Download diretto
        file_path = self._download_file(url, download_dir)
        if file_path:
            downloaded_files.append(file_path)
        
        return downloaded_files
    
    def _download_file(self, url: str, download_dir: str) -> Optional[str]:
        """Scarica un file da un URL."""
        try:
            response = self.session.get(url, timeout=self.timeout//1000, stream=True)
            response.raise_for_status()
            
            # Determina il nome del file
            filename = url_doc_name(url) or f"attachment_{int(time.time())}"
            
            # Pulisci il nome del file
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Crea la directory se non esiste
            Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            filepath = Path(download_dir) / filename
            
            # Salva il file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(filepath)
        except Exception as e:
            print(f"Errore nel download di {url}: {e}")
            return None


# Import time per _download_file
import time
