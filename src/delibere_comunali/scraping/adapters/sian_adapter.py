"""
Adattatore per il sistema SIAN (System Engineering).
Implementa scraping per portali comunali basati su SIAN.
"""
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import urllib.parse as up

import requests
from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from ..models import AlboItem
from ..utils import looks_like_attachment, url_doc_name


class SianAdapter(BaseAdapter):
    """
    Adapter specifico per il sistema SIAN.
    
    Caratteristiche:
    - URL tipici: /sian/, /system/, /sysmap/
    - Struttura HTML specifica per SIAN
    - Gestione download allegati
    """
    
    def __init__(self, timeout: int = 30000, max_retries: int = 3):
        super().__init__(timeout=timeout, max_retries=max_retries)
    
    def is_sian_url(self, url: str) -> bool:
        """Verifica se un URL appartiene a SIAN."""
        url_lower = url.lower()
        sian_patterns = ['sian', 'system', 'sysmap']
        return any(pattern in url_lower for pattern in sian_patterns)
    
    
    def scrape_metadata(self, url: str) -> Tuple[List[AlboItem], Optional[str]]:
        """
        Scraping dei metadati da una pagina di albo pretorio SIAN.
        
        Supporta:
        - Tabelle con classe specifica SIAN
        - Liste di documenti
        - Paginazione
        """
        html = self._make_request(url)
        if not html:
            return [], None
        
        soup = BeautifulSoup(html, "html.parser")
        items: List[AlboItem] = []
        
        # Prova 1: Cerca tabelle con classe tipica SIAN
        tables = soup.find_all('table', class_=re.compile(r'albo|atti|documenti|elenco', re.I))
        if not tables:
            tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Salta l'intestazione
                item = self._parse_table_row(row, url)
                if item:
                    items.append(item)
        
        # Prova 2: Cerca liste di documenti
        if not items:
            lists = soup.find_all(['ul', 'ol'], class_=re.compile(r'albo|atti|documenti', re.I))
            if not lists:
                lists = soup.find_all(['ul', 'ol'])
            
            for lst in lists:
                for li in lst.find_all('li'):
                    item = self._parse_list_item(li, url)
                    if item:
                        items.append(item)
        
        # Prova 3: Cerca div con classe specifica
        if not items:
            divs = soup.find_all('div', class_=re.compile(r'albo-item|atto|documento|risultato', re.I))
            for div in divs:
                item = self._parse_div(div, url)
                if item:
                    items.append(item)
        
        # Trova il link "successivo" per la paginazione
        next_link = self._find_next_page_link(soup, url)
        
        return items, next_link
    
    def _parse_table_row(self, row, base_url: str) -> Optional[AlboItem]:
        """Parsing di una riga di tabella SIAN."""
        a = row.find('a', href=True)
        if not a:
            return None
        
        href = up.urljoin(base_url, a['href'])
        tds = row.find_all('td')
        
        if len(tds) >= 3:
            colonne = [td.get_text(separator=" ", strip=True) for td in tds]
            row_text = " ".join(colonne)
            
            # Oggetto = colonna più lunga
            oggetto_val = max(colonne, key=len) if colonne else ""
            titolo_val = oggetto_val[:150] + ("..." if len(oggetto_val) > 150 else "")
            
            # Estrai data
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
        """Parsing di un elemento di lista SIAN."""
        a = li.find('a', href=True)
        if not a:
            return None
        
        href = up.urljoin(base_url, a['href'])
        text = li.get_text(separator=" ", strip=True)
        
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
        """Parsing di un div SIAN."""
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
    
    
    def download_attachment(self, url: str, download_dir: str) -> List[str]:
        """
        Download di un allegato da una pagina SIAN.
        """
        downloaded_files = []
        
        # Verifica se l'URL punta direttamente a un file
        if looks_like_attachment(url):
            file_path = self._download_file(url, download_dir)
            if file_path:
                downloaded_files.append(file_path)
            return downloaded_files
        
        # Altrimenti, visita la pagina e cerca link a file
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
    
    