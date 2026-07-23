#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script per aggiornare la mappatura dei comuni con l'identificazione automatica degli adapter.
Questo script esegue il rilevamento degli adapter per un elenco di comuni e aggiorna la mappatura.
"""

import sys
import os
import pandas as pd
from pathlib import Path
from typing import List

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente
from delibere_comunali.utils.adapter_detector import batch_identify_adapters

def update_adapter_mapping(input_file: str = "mappatura_comuni_finale.csv", 
                         output_file: str = "mappatura_comuni_con_adapter.csv",
                         batch_size: int = 100) -> pd.DataFrame:
    """
    Aggiorna la mappatura dei comuni con l'identificazione automatica degli adapter.
    
    Args:
        input_file: File di input con la mappatura esistente
        output_file: File di output per la mappatura aggiornata
        batch_size: Dimensione del batch per il rilevamento (per limitare le richieste)
        
    Returns:
        DataFrame con la mappatura aggiornata
    """
    print(f"Caricamento mappatura esistente da: {input_file}")
    
    # Carica la mappatura esistente
    df = carica_mappatura_esistente(input_file)
    
    if df is None:
        print(f"Errore: impossibile caricare il file {input_file}")
        return pd.DataFrame()
    
    print(f"Mappatura caricata: {len(df)} comuni")
    
    # Filtra i comuni con URL disponibili per il rilevamento
    comuni_da_aggiornare = df[
        ((df['url_istituzionale'] != "") & (df['url_istituzionale'].notna())) |
        ((df['url_albo_pretorio'] != "") & (df['url_albo_pretorio'].notna()))
    ].copy()
    
    print(f"Comuni con URL disponibili per rilevamento: {len(comuni_da_aggiornare)}")
    
    if comuni_da_aggiornare.empty:
        print("Nessun comune con URL disponibili per il rilevamento. Aggiornamento terminato.")
        # Salva comunque il file originale
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Mappatura salvata in: {output_file}")
        return df
    
    # Suddividi in batch per limitare le richieste simultanee
    batches = [comuni_da_aggiornare[i:i + batch_size] for i in range(0, len(comuni_da_aggiornare), batch_size)]
    
    print(f"Elaborazione in {len(batches)} batch di dimensione massima {batch_size}...")
    
    total_updated = 0
    
    for i, batch in enumerate(batches):
        print(f"Batch {i+1}/{len(batches)}: {len(batch)} comuni")
        
        # Esegui il rilevamento per il batch corrente
        adapter_results = batch_identify_adapters(batch)
        
        # Aggiorna la mappatura principale con i risultati
        for j, (idx, row) in enumerate(batch.iterrows()):
            if j < len(adapter_results):
                adapter_info = adapter_results[j]
                # Aggiorna solo se il risultato è diverso da 'unknown' o se era 'unknown'
                if (adapter_info['adapter_principale'] != 'unknown' or 
                    df.loc[idx, 'scraper_adapter'] == 'unknown'):
                    df.loc[idx, 'scraper_adapter'] = adapter_info['adapter_principale']
        
        total_updated += len(batch)
        print(f"  Aggiornati {total_updated}/{len(comuni_da_aggiornare)} comuni")
    
    # Salva la mappatura aggiornata
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nMappatura aggiornata salvata in: {output_file}")
    
    # Stampa statistiche
    adapter_counts = df['scraper_adapter'].value_counts()
    print(f"\nDistribuzione degli adapter rilevati:")
    for adapter, count in adapter_counts.items():
        print(f"  {adapter}: {count}")
    
    return df

def filter_comuni_by_adapter(df: pd.DataFrame, adapter_name: str) -> pd.DataFrame:
    """
    Filtra i comuni per tipo di adapter.
    
    Args:
        df: DataFrame con la mappatura dei comuni
        adapter_name: Nome dell'adapter da filtrare
        
    Returns:
        DataFrame filtrato
    """
    filtered = df[df['scraper_adapter'] == adapter_name]
    print(f"Comuni con adapter '{adapter_name}': {len(filtered)}")
    return filtered

def main():
    print("=== Aggiornamento Mappatura Adapter Comuni ===")
    
    # Aggiorna la mappatura con rilevamento automatico degli adapter
    df_aggiornato = update_adapter_mapping()
    
    if df_aggiornato.empty:
        print("Errore nell'aggiornamento della mappatura.")
        return
    
    # Mostra alcune statistiche
    total_comuni = len(df_aggiornato)
    comuni_con_adapter = len(df_aggiornato[df_aggiornato['scraper_adapter'] != 'unknown'])
    percentuale = (comuni_con_adapter / total_comuni) * 100 if total_comuni > 0 else 0
    
    print(f"\nRiepilogo:")
    print(f"  Comuni totali: {total_comuni}")
    print(f"  Comuni con adapter identificato: {comuni_con_adapter} ({percentuale:.1f}%)")
    
    # Esempio: mostra alcuni comuni per ciascun adapter
    print(f"\nEsempi di comuni per ciascun adapter:")
    adapter_counts = df_aggiornato['scraper_adapter'].value_counts()
    
    for adapter in adapter_counts.head(5).index:  # Mostra i primi 5 adapter
        comuni_sample = df_aggiornato[
            df_aggiornato['scraper_adapter'] == adapter
        ]['nome_comune'].head(3).tolist()  # Mostra i primi 3 comuni
        
        print(f"  {adapter}: {', '.join(comuni_sample)}")
    
    print(f"\n=== Aggiornamento Completato ===")

if __name__ == "__main__":
    main()