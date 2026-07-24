"""
Generic Adapter - Fallback per enti con provider sconosciuti o non supportati.
Utilizza solo requests + BeautifulSoup (nessuna dipendenza da Playwright).
Estende BaseAdapter per ereditare la logica comune.
"""
import re
from typing import Optional, List, Tuple
from pathlib import Path
import urllib.parse as up

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from ..models import AlboItem
from ..utils import looks_like_attachment, url_doc_name


class GenericAdapter(BaseAdapter):
    """
    Adapter generico per enti con provider sconosciuti.
    Estende BaseAdapter per ereditare:
    - Gestione richieste HTTP (_make_request)
    - Estrazione entita (_extract_date, _extract_numero, ecc.)
    - Download file (_download_file)

    Implementa:
    - Scraping metadati con requests
    - Download diretto di allegati (se l'URL punta a un file)
    - Fallback per qualsiasi struttura HTML
    """

    def __init__(self, timeout: int = 30000, max_retries: int = 3):
        super().__init__(timeout=timeout, max_retries=max_retries)

    def is_generic_url(self, url: str) -> bool:
        """Verifica se un URL non appartiene a provider noti."""
        known_patterns = [
            'halleyweb', 'openweb', 'halleyinformatica',
            'maggioli', 'siap', 'informatica', 'webgis',
            'asmel', 'asmelnet', 'websoft',
            'kibernetes', 'kibernet', 'kibe',
            'sian', 'system', 'sysmap'
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

        # Prova 1: Cerca tabelle
        tables = soup.find_all('table')
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Salta intestazione
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

        # Trova il link successivo per la paginazione
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
            colonne = [td.get_text(separator=" ", strip=True) for td in tds]
            row_text = " ".join(colonne)

            oggetto_val = max(colonne, key=len) if colonne else ""
            titolo_val = oggetto_val[:150] + ("..." if len(oggetto_val) > 150 else "")

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
        """Parsing di un elemento di lista."""
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
