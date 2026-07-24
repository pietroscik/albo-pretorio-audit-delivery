"""
BaseAdapter - Classe base per tutti gli adapter di scraping.
Centralizza la logica comune (timeout, retry, estrazione entità) per evitare duplicazione.
"""
import re
from typing import Optional, List, Tuple
from pathlib import Path
import urllib.parse as up
import time

import requests
from bs4 import BeautifulSoup

from ..models import AlboItem
from ..utils import looks_like_attachment, url_doc_name


class BaseAdapter:
    """
    Classe base per gli adapter di scraping.
    
    Fornisce:
    - Gestione unificata delle richieste HTTP (timeout, retry)
    - Metodi comuni per estrazione date, numeri, tipologie
    - Download file con gestione errori
    - Paginazione standardizzata
    
    Ogni adapter specifico (Halley, Maggioli, ecc.) deve estendere questa classe
    e implementare i metodi astratti:
    - is_provider_url()
    - scrape_metadata()
    """
    
    def __init__(self, timeout: int = 30000, max_retries: int = 3):
        """
        Inizializza l'adapter con timeout e retry.
        
        Args:
            timeout: Timeout in millisecondi per le richieste HTTP
            max_retries: Numero massimo di tentativi per ogni richiesta
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _make_request(self, url: str) -> Optional[str]:
        """
        Esegue una richiesta HTTP con retry e timeout.
        
        Args:
            url: URL da richiedere
            
        Returns:
            Testo HTML della risposta, o None se fallisce
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout//1000)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"[BaseAdapter] Errore nella richiesta a {url}: {e}")
                    return None
                # Aspetta esponenzialmente
                time.sleep((attempt + 1) * 2)
        return None
    
    def is_provider_url(self, url: str) -> bool:
        """
        Verifica se un URL appartiene al provider specifico.
        DEVE essere implementato dalle sottoclassi.
        
        Args:
            url: URL da verificare
            
        Returns:
            True se l'URL appartiene al provider, False altrimenti
        """
        raise NotImplementedError("is_provider_url deve essere implementato dalla sottoclasse")
    
    def scrape_metadata(self, url: str) -> Tuple[List[AlboItem], Optional[str]]:
        """
        Scraping dei metadati da una pagina di albo pretorio.
        DEVE essere implementato dalle sottoclassi.
        
        Args:
            url: URL della pagina da scrapare
            
        Returns:
            Tupla di (lista di AlboItem, URL pagina successiva)
        """
        raise NotImplementedError("scrape_metadata deve essere implementato dalla sottoclasse")
    
    def download_attachment(self, url: str, download_dir: str) -> List[str]:
        """
        Download di un allegato da un URL.
        
        Args:
            url: URL del file da scaricare
            download_dir: Directory di destinazione
            
        Returns:
            Lista di percorsi dei file scaricati
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
    
    def _download_file(self, url: str, download_dir: str) -> Optional[str]:
        """
        Scarica un file da un URL.
        
        Args:
            url: URL del file
            download_dir: Directory di destinazione
            
        Returns:
            Percorso del file scaricato, o None se fallisce
        """
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
            print(f"[BaseAdapter] Errore nel download di {url}: {e}")
            return None
    
    def _find_next_page_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Trova il link per la pagina successiva.
        
        Args:
            soup: Oggetto BeautifulSoup della pagina
            base_url: URL base per risolvere i link relativi
            
        Returns:
            URL della pagina successiva, o None se non trovato
        """
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
    
    # --- Metodi di utilità per l'estrazione entità ---
    
    def _extract_date(self, text: str) -> Optional[str]:
        """
        Estrae una data dal testo.
        Supporta formati: GG/MM/AAAA, AAAA-MM-GG, "15 gennaio 2025"
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Data in formato stringa, o None se non trovata
        """
        # Formato GG/MM/AAAA
        match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if match:
            return match.group(1)
        
        # Formato AAAA-MM-GG
        match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if match:
            return match.group(1)
        
        # Formato con parole (es. "15 gennaio 2025")
        match = re.search(
            r'\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})\b',
            text, re.I
        )
        if match:
            return f"{match.group(1)}/{self._month_to_num(match.group(2))}/{match.group(3)}"
        
        return None
    
    def _month_to_num(self, month: str) -> str:
        """
        Converte il nome del mese in numero.
        
        Args:
            month: Nome del mese (es. "gennaio")
            
        Returns:
            Numero del mese in formato "01"-"12"
        """
        months = {
            'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
            'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
            'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
        }
        return months.get(month.lower(), '01')
    
    def _extract_numero(self, text: str) -> Optional[str]:
        """
        Estrae un numero di documento dal testo.
        Supporta formati: "N. 123", "Numero: 123", "123/2025", "Delibera n. 123"
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Numero in formato stringa, o None se non trovato
        """
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
        """
        Estrae la tipologia di documento dal testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Tipologia in formato stringa, o None se non trovata
        """
        tipologie = [
            'Delibera', 'Determinazione', 'Ordinanza', 'Decreto',
            'Avviso', 'Bando', 'Attestazione', 'Visto Contabile'
        ]
        
        for tipologia in tipologie:
            if re.search(r'\b' + re.escape(tipologia) + r'\b', text, re.I):
                return tipologia
        
        return None
    
    def _extract_ufficio(self, colonne: List[str]) -> str:
        """
        Estrae l'ufficio dal testo delle colonne.
        
        Args:
            colonne: Lista di stringhe (testo delle colonne di una tabella)
            
        Returns:
            Nome dell'ufficio, o stringa vuota se non trovato
        """
        for col in colonne:
            if re.search(r'\b(ufficio|area|settore)\b', col, re.I):
                return re.sub(r'\b(ufficio|area|settore)\s*[:\s]*', '', col, flags=re.I).strip()
        return ""
    
    def _parse_table_row(self, row, base_url: str) -> Optional[AlboItem]:
        """
        Parsing di una riga di tabella (metodo di utilità).
        
        Args:
            row: Oggetto BeautifulSoup della riga
            base_url: URL base per risolvere i link relativi
            
        Returns:
            Oggetto AlboItem, o None se la riga non è valida
        """
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
            
            # Estrai data, numero, tipologia, ufficio
            data_val = self._extract_date(row_text)
            numero_val = self._extract_numero(row_text)
            tipologia_val = self._extract_tipologia(row_text)
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
        """
        Parsing di un elemento di lista (metodo di utilità).
        
        Args:
            li: Oggetto BeautifulSoup dell'elemento di lista
            base_url: URL base per risolvere i link relativi
            
        Returns:
            Oggetto AlboItem, o None se l'elemento non è valido
        """
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
        """
        Parsing di un div (metodo di utilità).
        
        Args:
            div: Oggetto BeautifulSoup del div
            base_url: URL base per risolvere i link relativi
            
        Returns:
            Oggetto AlboItem, o None se il div non è valido
        """
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
