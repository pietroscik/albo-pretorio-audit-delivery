#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modulo per l'estrazione e gestione dell'anagrafica ufficiale dei comuni italiani.
Si basa su fonti ISTAT e IndicePA per garantire dati aggiornati e coerenti.
"""

import pandas as pd
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def scarica_anagrafica_istat() -> Optional[pd.DataFrame]:
    """
    Scarica l'elenco ufficiale dei comuni italiani da ISTAT.
    
    Returns:
        DataFrame con i dati anagrafici dei comuni o None in caso di errore
    """
    print("Download anagrafica ISTAT in corso...")
    
    # URL ufficiale ISTAT aggiornato (controlla periodicamente per l'URL più recente)
    # L'URL potrebbe variare, questo è il formato standard aggiornato
    url_istat = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
    
    try:
        # Molti file ISTAT usano la codifica latin1 o windows-1252 e il separatore punto e virgola
        df = pd.read_csv(url_istat, sep=';', encoding='latin1')
        
        # Selezioniamo e rinominiamo solo le colonne utili per il mapping
        colonne_utili = {
            'Codice Comune formato alfanumerico': 'codice_istat',
            'Denominazione in italiano': 'nome_comune',
            'Sigla automobilistica': 'provincia',
            'Denominazione Regione': 'regione',
            'Codice Catastale del comune': 'codice_belfiore'
        }
        
        # Assicuriamoci che tutte le colonne richieste esistano
        colonne_presenti = [col for col in colonne_utili.keys() if col in df.columns]
        colonne_mancanti = [col for col in colonne_utili.keys() if col not in df.columns]
        
        if colonne_mancanti:
            logger.warning(f"Colonne mancanti nell'elenco ISTAT: {colonne_mancanti}")
            # Cerchiamo varianti dei nomi delle colonne
            for col_nome in colonne_mancanti:
                # Cerchiamo varianti comuni
                for col_df in df.columns:
                    if col_nome.lower().replace(' ', '').replace('-', '') in col_df.lower().replace(' ', '').replace('-', ''):
                        colonne_utili[col_nome] = colonne_utili[col_nome]
                        colonne_presenti.append(col_nome)
                        break
        
        df_mappatura = df.rename(columns={k: v for k, v in colonne_utili.items() if k in df.columns})[list(v for k, v in colonne_utili.items() if k in df.columns)]
        
        # Aggiungiamo le colonne vuote che andranno popolate con i dati di scraping
        df_mappatura['url_istituzionale'] = ""
        df_mappatura['url_albo_pretorio'] = ""
        df_mappatura['scraper_adapter'] = "unknown"  # Es. halley_adapter, maggioli_adapter
        df_mappatura['is_active'] = True
        
        logger.info(f"Anagrafica ISTAT generata con successo: {len(df_mappatura)} comuni trovati.")
        
        return df_mappatura
        
    except Exception as e:
        logger.error(f"Errore durante il download dell'anagrafica ISTAT: {e}")
        # Proviamo un URL alternativo
        return scarica_anagrafica_alternativa()

def scarica_anagrafica_alternativa() -> Optional[pd.DataFrame]:
    """
    Scarica l'anagrafica dei comuni da un'alternativa fonte ufficiale.
    
    Returns:
        DataFrame con i dati anagrafici dei comuni o None in caso di errore
    """
    print("Tentativo con fonte alternativa per l'anagrafica...")
    
    # Alternativa: usare un dataset aggiornato disponibile pubblicamente
    # Questo URL è un esempio, potrebbe cambiare nel tempo
    url_alternativo = "https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json"
    
    try:
        response = requests.get(url_alternativo)
        response.raise_for_status()
        
        comuni_data = response.json()
        
        # Convertiamo in DataFrame
        df = pd.DataFrame(comuni_data)
        
        # Rinominiamo le colonne per uniformità
        mapping_colonne = {
            'codice': 'codice_istat',
            'nome': 'nome_comune',
            'sigla_provincia': 'provincia',
            'regione': 'regione',
            'codice_catastale': 'codice_belfiore'
        }
        
        df_mapped = df.rename(columns=mapping_colonne)
        
        # Selezioniamo solo le colonne necessarie
        colonne_necessarie = ['codice_istat', 'nome_comune', 'provincia', 'regione', 'codice_belfiore']
        df_filtered = df_mapped[[col for col in colonne_necessarie if col in df_mapped.columns]]
        
        # Aggiungiamo le colonne vuote
        df_filtered['url_istituzionale'] = ""
        df_filtered['url_albo_pretorio'] = ""
        df_filtered['scraper_adapter'] = "unknown"
        df_filtered['is_active'] = True
        
        logger.info(f"Anagrafica alternativa generata con successo: {len(df_filtered)} comuni trovati.")
        
        return df_filtered
        
    except Exception as e:
        logger.error(f"Errore durante il download dell'anagrafica alternativa: {e}")
        return None

def genera_mappatura_comuni(output_file: str = "mappatura_comuni_template.csv") -> Optional[pd.DataFrame]:
    """
    Genera il template completo della mappatura dei comuni italiani.
    
    Args:
        output_file: Nome del file di output per la mappatura
        
    Returns:
        DataFrame con la mappatura completa o None in caso di errore
    """
    df = scarica_anagrafica_istat()
    
    if df is None:
        print("Impossibile scaricare l'anagrafica ufficiale. Creazione di un template vuoto...")
        # Creiamo un template minimale
        df = pd.DataFrame({
            'codice_istat': [],
            'nome_comune': [],
            'provincia': [],
            'regione': [],
            'codice_belfiore': [],
            'url_istituzionale': [],
            'url_albo_pretorio': [],
            'scraper_adapter': [],
            'is_active': []
        })
    
    # Salvataggio del template
    output_path = Path(output_file)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Mappatura generata con successo: {len(df)} comuni trovati.")
    print(f"File salvato in: {output_path.absolute()}")
    
    return df

def carica_mappatura_esistente(file_path: str = "mappatura_comuni_template.csv") -> Optional[pd.DataFrame]:
    """
    Carica una mappatura esistente dei comuni.
    
    Args:
        file_path: Percorso del file di mappatura esistente
        
    Returns:
        DataFrame con la mappatura caricata o None in caso di errore
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"Mappatura caricata con successo: {len(df)} comuni trovati.")
        return df
    except FileNotFoundError:
        logger.warning(f"File mappatura non trovato: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Errore durante il caricamento della mappatura: {e}")
        return None

def aggiorna_mappatura_con_indicepa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggiorna la mappatura dei comuni con dati da IndicePA dove possibile.
    Questa è una funzione placeholder che mostra come potrebbe essere implementata
    l'integrazione con IndicePA.
    
    Args:
        df: DataFrame con la mappatura esistente
        
    Returns:
        DataFrame aggiornato con dati da IndicePA
    """
    print("Aggiornamento della mappatura con dati IndicePA (placeholder)...")
    
    # Questa è una simulazione - in realtà si dovrebbe fare una chiamata API a IndicePA
    # per ottenere dati come URL istituzionali e PEC
    # Per ora, aggiorniamo solo alcuni esempi
    
    # Esempio: aggiorniamo alcuni comuni noti
    aggiornamenti = {
        'Avella': {
            'url_istituzionale': 'https://www.comune.avella.av.it',
            'url_albo_pretorio': 'https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio_full.php',
            'scraper_adapter': 'halley_adapter'
        },
        'Baiano': {
            'url_istituzionale': 'https://www.comune.baiano.av.it',
            'url_albo_pretorio': 'https://servizi.comune.baiano.av.it/openweb/albo/albo_pretorio_full.php',
            'scraper_adapter': 'halley_adapter'
        }
    }
    
    for idx, row in df.iterrows():
        nome_comune = row['nome_comune']
        if nome_comune in aggiornamenti:
            for campo, valore in aggiornamenti[nome_comune].items():
                df.at[idx, campo] = valore
    
    return df

def identifica_adapter_per_comune(url: str) -> str:
    """
    Identifica automaticamente l'adapter di scraping appropriato in base all'URL del sito comunale.
    
    Args:
        url: URL del sito istituzionale del comune
        
    Returns:
        Nome dell'adapter appropriato
    """
    if not url:
        return "unknown"
    
    url_lower = url.lower()
    
    # Riconoscimento dei fornitori principali di portali comunali
    if any(provider in url_lower for provider in ['halley', 'halleyinformatica', 'openweb']):
        return "halley_adapter"
    elif any(provider in url_lower for provider in ['maggioli', 'siap', 'informatica', 'webgis']):
        return "maggioli_adapter"
    elif any(provider in url_lower for provider in ['asmel', 'asmelnet', 'websoft']):
        return "asmel_adapter"
    elif any(provider in url_lower for provider in ['kibernetes', 'kibernet', 'kibe']):
        return "kibernetes_adapter"
    elif any(provider in url_lower for provider in ['sian', 'system', 'sysmap']):
        return "sian_adapter"
    else:
        return "generic_adapter"

if __name__ == "__main__":
    # Eseguiamo la generazione della mappatura
    anagrafica = genera_mappatura_comuni()
    
    if anagrafica is not None:
        print("\nAnteprima dei dati:")
        print(anagrafica[['codice_istat', 'nome_comune', 'provincia', 'regione']].head())
        
        # Proviamo ad aggiornare con dati IndicePA (simulazione)
        anagrafica_aggiornata = aggiorna_mappatura_con_indicepa(anagrafica)
        
        # Salviamo la versione aggiornata
        output_aggiornato = "mappatura_comuni_aggiornata.csv"
        anagrafica_aggiornata.to_csv(output_aggiornato, index=False, encoding='utf-8')
        print(f"Mappatura aggiornata salvata in: {output_aggiornato}")
    else:
        print("Impossibile generare la mappatura. Controllare la connessione Internet e la disponibilità delle fonti ISTAT.")