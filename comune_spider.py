#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script asincrono per lo spidering e il fingerprinting dei comuni italiani.
Identifica automaticamente i link agli albi pretori e i fornitori tecnologici.
"""

import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, urlparse
from pathlib import Path
import sys
import os

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComuneSpider:
    """
    Classe per effettuare spidering asincrono delle homepage comunali
    per identificare link agli albi pretori e fornitori tecnologici.
    """
    
    def __init__(self, max_concurrent_requests: int = 10, timeout: int = 15):
        """
        Inizializza lo spider.
        
        Args:
            max_concurrent_requests: Numero massimo di richieste concorrenti
            timeout: Timeout per ogni richiesta
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Pattern per identificare link agli albi pretori
        self.albo_patterns = [
            r'albo.*pretorio',
            r'pretorio',
            r'atti.*pubblici',
            r'pubblicazioni.*ufficiali',
            r'amministrazione.*trasparente',
            r'trasparenza',
            r'delibere',
            r'determinazioni',
            r'atti.*amministrativi'
        ]
        
        # Pattern per identificare fornitori tecnologici
        self.provider_patterns = {
            'halley_adapter': [
                r'halley', r'halleyinformatica', r'openweb', r'soluzioni.*software'
            ],
            'maggioli_adapter': [
                r'maggioli', r'siap', r'informatica', r'maggiolicloud', r'webgis'
            ],
            'asmel_adapter': [
                r'asmel', r'asmelnet', r'websoft', r'asmel.*tecnologie'
            ],
            'kibernetes_adapter': [
                r'kibernetes', r'kibernet', r'kibe', r'telematica.*p\.a\.'
            ],
            'sian_adapter': [
                r'sian', r'system.*engineering', r'sysmap'
            ],
            'trasparenza_valutazione_merito': [
                r'trasparenza-valutazione-merito'
            ],
            'portale_trasparenza': [
                r'portaletrasparenza\.gov\.it'
            ]
        }
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> tuple:
        """
        Recupera una pagina web in modo asincrono.
        
        Args:
            session: Sessione HTTP asincrona
            url: URL da recuperare
            
        Returns:
            Tuple (url, status_code, content, error_message)
        """
        async with self.semaphore:
            try:
                logger.debug(f"Richiesta: {url}")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    content = await response.text()
                    return url, response.status, content, None
            except Exception as e:
                logger.warning(f"Errore nella richiesta {url}: {e}")
                return url, None, None, str(e)
    
    def extract_albo_link(self, soup: BeautifulSoup, base_url: str) -> str:
        """
        Estrae il link all'albo pretorio dalla pagina.
        
        Args:
            soup: Oggetto BeautifulSoup della pagina
            base_url: URL base per risolvere link relativi
            
        Returns:
            URL del link all'albo pretorio o None se non trovato
        """
        # Cerca link usando testo visibile
        for pattern in self.albo_patterns:
            links = soup.find_all('a', string=re.compile(pattern, re.IGNORECASE))
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    return full_url
        
        # Cerca link usando attributo href
        for pattern in self.albo_patterns:
            links = soup.find_all('a', href=re.compile(pattern, re.IGNORECASE))
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    return full_url
        
        # Cerca link usando classi o id comuni
        common_classes_ids = ['albo', 'pretorio', 'trasparenza', 'atti', 'pubblicazioni']
        for selector in common_classes_ids:
            elements = soup.find_all(['a', 'div', 'span'], 
                                  attrs={'class': re.compile(selector, re.IGNORECASE)})
            elements.extend(soup.find_all(['a', 'div', 'span'], 
                                        attrs={'id': re.compile(selector, re.IGNORECASE)}))
            
            for elem in elements:
                link = elem if elem.name == 'a' else elem.find('a')
                if link and link.get('href'):
                    href = link.get('href')
                    full_url = urljoin(base_url, href)
                    return full_url
        
        return None
    
    def identify_provider(self, content: str, url: str) -> str:
        """
        Identifica il fornitore tecnologico basato su contenuto e URL.
        
        Args:
            content: Contenuto HTML della pagina
            url: URL della pagina
            
        Returns:
            Nome dell'adapter identificato o 'unknown'
        """
        content_lower = content.lower() if content else ""
        url_lower = url.lower()
        
        # Cerca nei pattern dei fornitori
        for adapter_name, patterns in self.provider_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower) or re.search(pattern, url_lower):
                    return adapter_name
        
        # Se nessun pattern specifico corrisponde, prova pattern generali
        if 'openweb' in content_lower or 'openweb' in url_lower:
            return 'halley_adapter'
        
        if any(provider in content_lower or provider in url_lower 
               for provider in ['maggioli', 'siap', 'informatica']):
            return 'maggioli_adapter'
        
        return 'unknown'
    
    async def analyze_comune(self, comune_data: dict) -> dict:
        """
        Analizza un singolo comune per identificare albo pretorio e fornitore.
        
        Args:
            comune_data: Dizionario con i dati del comune
            
        Returns:
            Dizionario con i risultati dell'analisi
        """
        nome_comune = comune_data['nome_comune']
        provincia = comune_data['provincia']
        
        # Costruisci URL della homepage
        homepage_url = f"https://www.comune.{nome_comune.lower().replace(' ', '')}.{provincia.lower()}.it"
        
        result = {
            'nome_comune': nome_comune,
            'provincia': provincia,
            'regione': comune_data.get('regione', ''),
            'homepage_url': homepage_url,
            'albo_pretorio_url': '',
            'provider_detected': 'unknown',
            'status_code': None,
            'error': '',
            'success': False
        }
        
        # Usa una sessione temporanea per questa richiesta
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=1)  # Limita connessioni per questo comune
        
        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                # Recupera la homepage
                url, status, content, error = await self.fetch_page(session, homepage_url)
                
                if error:
                    result['error'] = error
                    return result
                
                result['status_code'] = status
                
                if status != 200 or not content:
                    result['error'] = f"Status: {status}" if status else "No content"
                    return result
                
                # Analizza il contenuto
                soup = BeautifulSoup(content, 'html.parser')
                
                # Estrai link all'albo pretorio
                albo_url = self.extract_albo_link(soup, homepage_url)
                if albo_url:
                    result['albo_pretorio_url'] = albo_url
                    
                    # Se abbiamo trovato un link all'albo, analizziamolo anche
                    try:
                        albo_url_result = await self.fetch_page(session, albo_url)
                        _, albo_status, albo_content, albo_error = albo_url_result
                        
                        if albo_status == 200 and albo_content:
                            result['provider_detected'] = self.identify_provider(albo_content, albo_url)
                    except Exception as e:
                        logger.warning(f"Errore nell'analisi del link all'albo per {nome_comune}: {e}")
                
                # Se non abbiamo trovato il link all'albo, prova a identificare il provider dalla homepage
                if result['provider_detected'] == 'unknown':
                    result['provider_detected'] = self.identify_provider(content, homepage_url)
                
                result['success'] = True
                
        except Exception as e:
            result['error'] = f"Eccezione: {str(e)}"
        
        return result
    
    async def analyze_comuni_batch(self, comuni_list: list, max_workers: int = None) -> list:
        """
        Analizza un batch di comuni in parallelo.
        
        Args:
            comuni_list: Lista di dizionari con i dati dei comuni
            max_workers: Numero massimo di worker (default: self.max_concurrent_requests)
            
        Returns:
            Lista di risultati
        """
        if max_workers is None:
            max_workers = self.max_concurrent_requests
        
        semaphore = asyncio.Semaphore(max_workers)
        
        async def limited_analyze(comune_data):
            async with semaphore:
                return await self.analyze_comune(comune_data)
        
        tasks = [limited_analyze(comune_data) for comune_data in comuni_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Gestisci eventuali eccezioni
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                comune_data = comuni_list[i]
                processed_results.append({
                    'nome_comune': comune_data['nome_comune'],
                    'provincia': comune_data['provincia'],
                    'regione': comune_data.get('regione', ''),
                    'homepage_url': f"https://www.comune.{comune_data['nome_comune'].lower().replace(' ', '')}.{comune_data['provincia'].lower()}.it",
                    'albo_pretorio_url': '',
                    'provider_detected': 'unknown',
                    'status_code': None,
                    'error': f"Eccezione durante l'analisi: {str(result)}",
                    'success': False
                })
            else:
                processed_results.append(result)
        
        return processed_results

async def main():
    print("=== Spidering Comuni Italiani per Albo Pretorio ===")
    
    # Carica la mappatura dei comuni
    print("Caricamento mappatura comuni...")
    df_comuni = carica_mappatura_esistente("mappatura_comuni_finale.csv")
    
    if df_comuni is None or df_comuni.empty:
        print("Errore: impossibile caricare la mappatura dei comuni")
        return
    
    print(f"Mappatura caricata: {len(df_comuni)} comuni")
    
    # Seleziona un sottoinsieme di comuni per il test
    # Filtriamo alcuni comuni per provincia per avere una distribuzione rappresentativa
    comuni_selezionati = []
    province_interessanti = ['AV', 'BN', 'CE', 'NA', 'RM', 'MI', 'TO', 'VE']
    
    for provincia in province_interessanti:
        comuni_prov = df_comuni[df_comuni['provincia'] == provincia].head(3)  # 3 per provincia
        comuni_selezionati.extend(comuni_prov.to_dict('records'))
    
    print(f"Selezionati {len(comuni_selezionati)} comuni per l'analisi")
    
    # Inizializza lo spider
    spider = ComuneSpider(max_concurrent_requests=5, timeout=15)
    
    # Esegui l'analisi
    print("Inizio analisi asincrona...")
    results = await spider.analyze_comuni_batch(comuni_selezionati, max_workers=5)
    
    # Converti in DataFrame
    results_df = pd.DataFrame(results)
    
    # Salva i risultati
    output_file = "spidering_results.csv"
    results_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Risultati salvati in: {output_file}")
    
    # Stampa statistiche
    success_count = len(results_df[results_df['success'] == True])
    error_count = len(results_df[results_df['success'] == False])
    
    print(f"\nStatistiche:")
    print(f"  Comuni analizzati: {len(results_df)}")
    print(f"  Successi: {success_count}")
    print(f"  Errori: {error_count}")
    
    # Distribuzione dei provider identificati
    provider_counts = results_df['provider_detected'].value_counts()
    print(f"\nDistribuzione dei provider identificati:")
    for provider, count in provider_counts.items():
        print(f"  {provider}: {count}")
    
    # Comuni con link all'albo trovato
    albo_found = len(results_df[results_df['albo_pretorio_url'] != ''])
    print(f"\nComuni con link all'albo pretorio trovato: {albo_found}")
    
    if albo_found > 0:
        print("Esempi di comuni con link trovato:")
        sample_with_albo = results_df[results_df['albo_pretorio_url'] != ''].head(5)
        for _, row in sample_with_albo.iterrows():
            print(f"  {row['nome_comune']} ({row['provincia']}): {row['albo_pretorio_url']} [{row['provider_detected']}]")
    
    print("\n=== Analisi Completata ===")

if __name__ == "__main__":
    asyncio.run(main())