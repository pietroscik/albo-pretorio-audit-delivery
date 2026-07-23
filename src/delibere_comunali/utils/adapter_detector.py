#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modulo per l'identificazione automatica degli adapter di scraping
in base al fornitore del portale comunale (Halley, Maggioli, etc.)
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
from urllib.parse import urlparse

class AdapterDetector:
    """
    Classe per rilevare automaticamente il tipo di sistema di albo pretorio
    utilizzato da un comune basandosi sul sito istituzionale.
    """
    
    def __init__(self):
        self.adapter_patterns = {
            'halley_adapter': {
                'urls': [r'openweb', r'halley', r'halleyinformatica'],
                'html_patterns': [
                    r'Halley\s+Informatica',
                    r'openweb',
                    r'Soluzioni\s+Software',
                    r'Portale\s+Comunale'
                ],
                'meta_tags': [
                    {'name': 'generator', 'content': r'Halley'},
                    {'name': 'author', 'content': r'Halley'}
                ]
            },
            'maggioli_adapter': {
                'urls': [r'maggioli', r'siap', r'informatica', r'webgis'],
                'html_patterns': [
                    r'Maggioli',
                    r'Software\s+House',
                    r'SIA\s+Solution',
                    r'Siap\s+spa'
                ],
                'meta_tags': [
                    {'name': 'generator', 'content': r'Maggioli'},
                    {'name': 'author', 'content': r'Maggioli'}
                ]
            },
            'asmel_adapter': {
                'urls': [r'asmel', r'asmelnet', r'websoft'],
                'html_patterns': [
                    r'Asmel',
                    r'AsmelNet',
                    r'Soluzioni\s+Asmel',
                    r'WebSoft'
                ],
                'meta_tags': [
                    {'name': 'generator', 'content': r'Asmel'},
                    {'name': 'author', 'content': r'Asmel'}
                ]
            },
            'kibernetes_adapter': {
                'urls': [r'kibernetes', r'kibernet', r'kibe'],
                'html_patterns': [
                    r'Kibernetes',
                    r'Sistemi\s+Telematici',
                    r'Telematica\s+P.A.'
                ],
                'meta_tags': [
                    {'name': 'generator', 'content': r'Kibernetes'},
                    {'name': 'author', 'content': r'Kibernetes'}
                ]
            },
            'sian_adapter': {
                'urls': [r'sian', r'system', r'sysmap'],
                'html_patterns': [
                    r'SIAN',
                    r'System\s+Engineering',
                    r'SysMap'
                ],
                'meta_tags': [
                    {'name': 'generator', 'content': r'SIAN'},
                    {'name': 'author', 'content': r'SIAN'}
                ]
            }
        }
    
    def detect_from_url(self, url: str) -> str:
        """
        Rileva l'adapter basandosi sull'URL del sito comunale.
        
        Args:
            url: URL del sito istituzionale del comune
            
        Returns:
            Nome dell'adapter rilevato o 'generic_adapter' se non identificato
        """
        if not url:
            return 'unknown'
        
        url_lower = url.lower()
        
        # Prima prova con i pattern negli URL
        for adapter_name, patterns in self.adapter_patterns.items():
            for url_pattern in patterns['urls']:
                if re.search(url_pattern, url_lower):
                    return adapter_name
        
        # Se non trovato negli URL, prova con il contenuto della pagina
        try:
            return self.detect_from_content(url)
        except Exception:
            # Se non riesce a scaricare il contenuto, ritorna generic
            return 'generic_adapter'
    
    def detect_from_content(self, url: str) -> str:
        """
        Rileva l'adapter scaricando e analizzando il contenuto della pagina.
        
        Args:
            url: URL del sito istituzionale del comune
            
        Returns:
            Nome dell'adapter rilevato o 'generic_adapter' se non identificato
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            html_content = response.text.lower()
            
            # Cerchiamo nei meta tags
            for adapter_name, patterns in self.adapter_patterns.items():
                # Controllo nei meta tags
                for meta_pattern in patterns['meta_tags']:
                    meta_tag = soup.find('meta', attrs=meta_pattern)
                    if meta_tag:
                        return adapter_name
                
                # Controllo nei pattern HTML
                for html_pattern in patterns['html_patterns']:
                    if re.search(html_pattern, html_content, re.IGNORECASE):
                        return adapter_name
            
            return 'generic_adapter'
            
        except Exception as e:
            print(f"Errore durante l'analisi del contenuto di {url}: {e}")
            return 'generic_adapter'
    
    def detect_albo_pretorio_pattern(self, url: str) -> Optional[str]:
        """
        Rileva il pattern specifico per l'albo pretorio basandosi sull'URL.
        
        Args:
            url: URL del sito o dell'albo pretorio del comune
            
        Returns:
            Pattern specifico per l'albo pretorio o None se non identificato
        """
        if not url:
            return None
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Pattern comuni per albi pretori
        patterns = {
            'halley_openweb': r'servizi\.comune\..*\.it/openweb',
            'trasparenza_valutazione_merito': r'trasparenza-valutazione-merito\.it',
            'portale_trasparenza': r'portaletrasparenza\.gov\.it',
            'albopretorio_gov': r'albopretorio\.gov\.it'
        }
        
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, domain + parsed.path.lower()):
                return pattern_name
        
        return None

def identify_comune_adapter(nome_comune: str, url_istituzionale: str = "", url_albo: str = "") -> Dict[str, str]:
    """
    Funzione principale per identificare l'adapter appropriato per un comune.
    
    Args:
        nome_comune: Nome del comune
        url_istituzionale: URL del sito istituzionale del comune
        url_albo: URL specifico dell'albo pretorio
        
    Returns:
        Dizionario con le informazioni sull'adapter rilevato
    """
    detector = AdapterDetector()
    
    result = {
        'nome_comune': nome_comune,
        'adapter_principale': 'unknown',
        'pattern_albo': 'generic',
        'confidenza': 0.0
    }
    
    # Rileva l'adapter principale
    adapter_principale = detector.detect_from_url(url_istituzionale)
    result['adapter_principale'] = adapter_principale
    
    # Rileva il pattern specifico per l'albo
    pattern_albo = detector.detect_albo_pretorio_pattern(url_albo or url_istituzionale)
    if pattern_albo:
        result['pattern_albo'] = pattern_albo
    
    # Imposta la confidenza in base al tipo di rilevamento
    if adapter_principale != 'unknown' and adapter_principale != 'generic_adapter':
        result['confidenza'] = 0.8
    elif adapter_principale == 'generic_adapter':
        result['confidenza'] = 0.3
    else:
        result['confidenza'] = 0.1
    
    return result

def batch_identify_adapters(comuni_df) -> list:
    """
    Identifica gli adapter per un batch di comuni.
    
    Args:
        comuni_df: DataFrame con colonne 'nome_comune', 'url_istituzionale', 'url_albo_pretorio'
        
    Returns:
        Lista di dizionari con le informazioni sugli adapter rilevati
    """
    results = []
    
    for idx, row in comuni_df.iterrows():
        adapter_info = identify_comune_adapter(
            nome_comune=row['nome_comune'],
            url_istituzionale=row.get('url_istituzionale', ''),
            url_albo=row.get('url_albo_pretorio', '')
        )
        results.append(adapter_info)
    
    return results

if __name__ == "__main__":
    # Esempio di utilizzo
    detector = AdapterDetector()
    
    # Test con alcuni comuni noti
    test_comuni = [
        {
            'nome_comune': 'Avella',
            'url_istituzionale': 'https://www.comune.avella.av.it',
            'url_albo': 'https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio_full.php'
        },
        {
            'nome_comune': 'Roma',
            'url_istituzionale': 'https://www.comune.roma.it',
            'url_albo': 'https://albopretorio.comune.roma.it'
        }
    ]
    
    for comune in test_comuni:
        adapter_info = identify_comune_adapter(
            nome_comune=comune['nome_comune'],
            url_istituzionale=comune['url_istituzionale'],
            url_albo=comune['url_albo']
        )
        print(f"Comune: {adapter_info['nome_comune']}")
        print(f"  Adapter: {adapter_info['adapter_principale']}")
        print(f"  Pattern Albo: {adapter_info['pattern_albo']}")
        print(f"  Confidenza: {adapter_info['confidenza']}")
        print()