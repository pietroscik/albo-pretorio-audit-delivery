#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script per integrare i risultati dello spidering con la mappatura esistente dei comuni.
Aggiorna i dati con le informazioni scoperte automaticamente sugli albi pretori e fornitori.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente

def integrate_spidering_results(mappatura_file: str = "mappatura_comuni_finale.csv", 
                              spidering_file: str = "spidering_results.csv",
                              output_file: str = "mappatura_comuni_integrata.csv") -> pd.DataFrame:
    """
    Integra i risultati dello spidering con la mappatura esistente dei comuni.
    
    Args:
        mappatura_file: File con la mappatura esistente
        spidering_file: File con i risultati dello spidering
        output_file: File di output per la mappatura integrata
        
    Returns:
        DataFrame con la mappatura aggiornata
    """
    print(f"Caricamento mappatura esistente da: {mappatura_file}")
    df_mappatura = carica_mappatura_esistente(mappatura_file)
    
    if df_mappatura is None or df_mappatura.empty:
        print(f"Errore: impossibile caricare la mappatura da {mappatura_file}")
        return pd.DataFrame()
    
    print(f"Mappatura esistente caricata: {len(df_mappatura)} comuni")
    
    print(f"Caricamento risultati spidering da: {spidering_file}")
    try:
        # Gestione più robusta dei valori mancanti in lettura
        df_spidering = pd.read_csv(spidering_file, encoding='utf-8', na_values=['nan', 'NA', 'N/A', 'na', 'n/a'])
        print(f"Risultati spidering caricati: {len(df_spidering)} comuni analizzati")
    except FileNotFoundError:
        print(f"File {spidering_file} non trovato. Creazione di una mappatura vuota aggiornata.")
        # Torniamo comunque la mappatura originale
        df_mappatura.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Mappatura originale salvata in: {output_file}")
        return df_mappatura
    
    # Crea un dizionario per mappare i risultati dello spidering
    spidering_map = {}
    for _, row in df_spidering.iterrows():
        # Gestisci i valori NaN
        nome_comune = row['nome_comune']
        provincia = row['provincia']
        
        if pd.isna(nome_comune) or pd.isna(provincia):
            continue
            
        key = (str(nome_comune).lower(), str(provincia).lower())
        spidering_map[key] = {
            'albo_pretorio_url': '' if pd.isna(row['albo_pretorio_url']) or str(row['albo_pretorio_url']).lower() == 'nan' else str(row['albo_pretorio_url']),
            'provider_detected': 'unknown' if pd.isna(row['provider_detected']) or str(row['provider_detected']).lower() == 'nan' else str(row['provider_detected']),
            'homepage_url': '' if pd.isna(row['homepage_url']) or str(row['homepage_url']).lower() == 'nan' else str(row['homepage_url'])
        }
    """
    Integra i risultati dello spidering con la mappatura esistente dei comuni.
    
    Args:
        mappatura_file: File con la mappatura esistente
        spidering_file: File con i risultati dello spidering
        output_file: File di output per la mappatura integrata
        
    Returns:
        DataFrame con la mappatura aggiornata
    """
    print(f"Caricamento mappatura esistente da: {mappatura_file}")
    df_mappatura = carica_mappatura_esistente(mappatura_file)
    
    if df_mappatura is None or df_mappatura.empty:
        print(f"Errore: impossibile caricare la mappatura da {mappatura_file}")
        return pd.DataFrame()
    
    print(f"Mappatura esistente caricata: {len(df_mappatura)} comuni")
    
    print(f"Caricamento risultati spidering da: {spidering_file}")
    try:
        df_spidering = pd.read_csv(spidering_file, encoding='utf-8')
        print(f"Risultati spidering caricati: {len(df_spidering)} comuni analizzati")
    except FileNotFoundError:
        print(f"File {spidering_file} non trovato. Creazione di una mappatura vuota aggiornata.")
        # Torniamo comunque la mappatura originale
        df_mappatura.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Mappatura originale salvata in: {output_file}")
        return df_mappatura
    
    # Crea un dizionario per mappare i risultati dello spidering
    spidering_map = {}
    for _, row in df_spidering.iterrows():
        # Gestisci i valori NaN
        nome_comune = row['nome_comune']
        provincia = row['provincia']
        
        if pd.isna(nome_comune) or pd.isna(provincia):
            continue
            
        key = (str(nome_comune).lower().strip(), str(provincia).lower().strip())
        spidering_map[key] = {
            'albo_pretorio_url': row['albo_pretorio_url'] if pd.notna(row['albo_pretorio_url']) and row['albo_pretorio_url'] != 'nan' else '',
            'provider_detected': row['provider_detected'] if pd.notna(row['provider_detected']) and row['provider_detected'] != 'nan' else 'unknown',
            'homepage_url': row['homepage_url'] if pd.notna(row['homepage_url']) and row['homepage_url'] != 'nan' else ''
        }
    
    # Aggiorna la mappatura esistente con i risultati dello spidering
    updates_count = 0
    new_fields_added = 0
    
    # Aggiungi eventuali nuove colonne necessarie
    if 'homepage_url' not in df_mappatura.columns:
        df_mappatura['homepage_url'] = ""
        new_fields_added += 1
    
    # Itera solo sui comuni che hanno nome e provincia validi
    valid_rows = df_mappatura[
        df_mappatura['nome_comune'].notna() & 
        df_mappatura['provincia'].notna()
    ]
    
    for idx in valid_rows.index:
        row = df_mappatura.loc[idx]
        
        nome_comune = row['nome_comune']
        provincia = row['provincia']
        
        # Assicuriamoci che siano stringhe e non NaN
        if pd.isna(nome_comune) or pd.isna(provincia):
            continue
            
        nome_comune_str = str(nome_comune).lower().strip()
        provincia_str = str(provincia).lower().strip()
        
        key = (nome_comune_str, provincia_str)
        
        if key in spidering_map:
            spidering_data = spidering_map[key]
            
            # Aggiorna l'URL dell'albo pretorio solo se non è già presente o se è vuoto
            current_albo = row['url_albo_pretorio']
            if (pd.isna(current_albo) or current_albo == '' or str(current_albo) == 'nan'):
                if spidering_data['albo_pretorio_url'] != '':
                    df_mappatura.at[idx, 'url_albo_pretorio'] = spidering_data['albo_pretorio_url']
                    updates_count += 1
            
            # Aggiorna l'URL homepage se non presente
            current_homepage = row.get('homepage_url', '')
            if (pd.isna(current_homepage) or current_homepage == '' or str(current_homepage) == 'nan'):
                if spidering_data['homepage_url'] != '':
                    df_mappatura.at[idx, 'homepage_url'] = spidering_data['homepage_url']
            
            # Aggiorna l'adapter solo se era 'unknown' o non era impostato
            current_adapter = row['scraper_adapter']
            if (pd.isna(current_adapter) or current_adapter == '' or str(current_adapter) == 'unknown'):
                if spidering_data['provider_detected'] != 'unknown':
                    df_mappatura.at[idx, 'scraper_adapter'] = spidering_data['provider_detected']
                    updates_count += 1
    
    print(f"\nAggiornamenti effettuati: {updates_count}")
    print(f"Nuovi campi aggiunti: {new_fields_added}")
    
    # Salva la mappatura integrata
    df_mappatura.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Mappatura integrata salvata in: {output_file}")
    
    # Stampa statistiche
    # Filtra i dati per calcolare le statistiche solo sui record validi
    valid_data = df_mappatura[
        df_mappatura['nome_comune'].notna() & 
        df_mappatura['provincia'].notna()
    ]
    
    stats = {
        'totale_comuni_validi': len(valid_data),
        'comuni_con_albo_url': len(valid_data[valid_data['url_albo_pretorio'].notna() & 
                                               (valid_data['url_albo_pretorio'] != '') & 
                                               (valid_data['url_albo_pretorio'] != 'nan')]),
        'comuni_con_adapter': len(valid_data[valid_data['scraper_adapter'].notna() & 
                                             (valid_data['scraper_adapter'] != '') & 
                                             (valid_data['scraper_adapter'] != 'unknown')])
    }
    
    print(f"\nStatistiche mappatura integrata:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Mostra la distribuzione degli adapter (solo sui dati validi)
    valid_with_adapter = valid_data[valid_data['scraper_adapter'].notna() & 
                                   (valid_data['scraper_adapter'] != '') & 
                                   (valid_data['scraper_adapter'] != 'unknown')]
    adapter_counts = valid_with_adapter['scraper_adapter'].value_counts()
    print(f"\nDistribuzione degli adapter:")
    for adapter, count in adapter_counts.head(10).items():
        print(f"  {adapter}: {count}")
    
    return df_mappatura

def generate_integration_report(original_df: pd.DataFrame, integrated_df: pd.DataFrame, 
                              report_file: str = "integration_report.md"):
    """
    Genera un report dettagliato dell'integrazione.
    
    Args:
        original_df: DataFrame originale
        integrated_df: DataFrame integrato
        report_file: File di output per il report
    """
    print(f"Generazione report di integrazione in: {report_file}")
    
    # Calcola le differenze
    original_with_albo = len(original_df[original_df['url_albo_pretorio'].notna() & 
                                       (original_df['url_albo_pretorio'] != '') & 
                                       (original_df['url_albo_pretorio'] != 'nan')])
    integrated_with_albo = len(integrated_df[integrated_df['url_albo_pretorio'].notna() & 
                                           (integrated_df['url_albo_pretorio'] != '') & 
                                           (integrated_df['url_albo_pretorio'] != 'nan')])
    
    original_with_adapter = len(original_df[original_df['scraper_adapter'].notna() & 
                                         (original_df['scraper_adapter'] != '') & 
                                         (original_df['scraper_adapter'] != 'unknown')])
    integrated_with_adapter = len(integrated_df[integrated_df['scraper_adapter'].notna() & 
                                              (integrated_df['scraper_adapter'] != '') & 
                                              (integrated_df['scraper_adapter'] != 'unknown')])
    
    # Scrivi il report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Report Integrazione Mappatura Comuni\n\n")
        f.write("Questo report descrive i risultati dell'integrazione tra la mappatura esistente\n")
        f.write("dei comuni e i risultati dello spidering automatico.\n\n")
        
        f.write("## Statistiche Generali\n\n")
        f.write(f"- Comuni totali: {len(integrated_df)}\n")
        f.write(f"- Comuni con URL albo pretorio (prima): {original_with_albo}\n")
        f.write(f"- Comuni con URL albo pretorio (dopo): {integrated_with_albo}\n")
        f.write(f"- Aumento URL albo: {integrated_with_albo - original_with_albo}\n\n")
        f.write(f"- Comuni con adapter identificato (prima): {original_with_adapter}\n")
        f.write(f"- Comuni con adapter identificato (dopo): {integrated_with_adapter}\n")
        f.write(f"- Aumento adapter identificati: {integrated_with_adapter - original_with_adapter}\n\n")
        
        f.write("## Distribuzione degli Adapter\n\n")
        adapter_counts = integrated_df['scraper_adapter'].value_counts()
        for adapter, count in adapter_counts.head(15).items():
            f.write(f"- {adapter}: {count}\n")
        
        f.write("\n## Comuni con Nuovi Link all'Albo Trovati\n\n")
        new_albo_links = integrated_df[
            (integrated_df['url_albo_pretorio'].notna()) & 
            (integrated_df['url_albo_pretorio'] != '') & 
            (integrated_df['url_albo_pretorio'] != 'nan') &
            (~original_df['url_albo_pretorio'].notna())
        ]
        
        if not new_albo_links.empty:
            f.write(f"Trovati {len(new_albo_links)} nuovi link all'albo pretorio:\n\n")
            for _, row in new_albo_links.head(20).iterrows():  # Mostra i primi 20
                f.write(f"- {row['nome_comune']} ({row['provincia']}): {row['url_albo_pretorio']} [{row['scraper_adapter']}]\n")
        else:
            f.write("Nessun nuovo link all'albo pretorio trovato attraverso lo spidering.\n")
    
    print(f"Report di integrazione salvato in: {report_file}")

def main():
    print("=== Integrazione Risultati Spidering con Mappatura Comuni ===")
    
    # Esegui l'integrazione
    integrated_df = integrate_spidering_results()
    
    if integrated_df.empty:
        print("Errore nell'integrazione dei dati.")
        return
    
    # Carica la mappatura originale per confronto
    original_df = carica_mappatura_esistente("mappatura_comuni_finale.csv")
    
    # Genera il report di integrazione
    if original_df is not None:
        generate_integration_report(original_df, integrated_df)
    
    print("\n=== Integrazione Completata ===")
    print("\nFile generati:")
    print("- mappatura_comuni_integrata.csv: Mappatura aggiornata con dati dello spidering")
    print("- integration_report.md: Report dettagliato dell'integrazione")

if __name__ == "__main__":
    main()