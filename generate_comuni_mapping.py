#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script per generare la mappatura completa dei comuni italiani
con relativi URL e adapter di scraping.
"""

import sys
import os
from pathlib import Path

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.comuni_anagrafica import genera_mappatura_comuni, aggiorna_mappatura_con_indicepa
from delibere_comunali.utils.adapter_detector import batch_identify_adapters
import pandas as pd

def main():
    print("=== Generazione Mappatura Comuni Italiani ===")
    
    # Genera la mappatura base da ISTAT
    print("\n1. Generazione mappatura base da ISTAT...")
    df_comuni = genera_mappatura_comuni("mappatura_comuni_template.csv")
    
    if df_comuni is None or df_comuni.empty:
        print("Errore: impossibile generare la mappatura base. Controllare la connessione e la disponibilità delle fonti ISTAT.")
        return
    
    print(f"   -> {len(df_comuni)} comuni nella mappatura base")
    
    # Aggiorna con dati da IndicePA (simulazione)
    print("\n2. Aggiornamento con dati IndicePA (simulazione)...")
    df_aggiornato = aggiorna_mappatura_con_indicepa(df_comuni)
    
    # Salva la versione aggiornata
    df_aggiornato.to_csv("mappatura_comuni_aggiornata.csv", index=False, encoding='utf-8')
    print(f"   -> Mappatura aggiornata salvata: {len(df_aggiornato)} comuni")
    
    # Esempio: rileva alcuni adapter per i primi comuni
    print("\n3. Esempio di rilevamento automatico degli adapter...")
    
    # Filtra alcuni comuni con dati completi per il test
    comuni_test = df_aggiornato[
        (df_aggiornato['url_istituzionale'] != "") | 
        (df_aggiornato['url_albo_pretorio'] != "")
    ].head(10)  # Solo i primi 10 per velocità
    
    if not comuni_test.empty:
        adapters_rilevati = batch_identify_adapters(comuni_test)
        
        print("   Adapter rilevati per alcuni comuni di esempio:")
        for adapter_info in adapters_rilevati[:5]:  # Mostra solo i primi 5
            print(f"   - {adapter_info['nome_comune']}: {adapter_info['adapter_principale']} (conf: {adapter_info['confidenza']:.1f})")
        
        # Aggiorna la mappatura con gli adapter rilevati
        for idx, row in comuni_test.iterrows():
            comune_nome = row['nome_comune']
            adapter_info = next((info for info in adapters_rilevati if info['nome_comune'] == comune_nome), None)
            if adapter_info:
                df_aggiornato.loc[idx, 'scraper_adapter'] = adapter_info['adapter_principale']
    
    # Salva la mappatura finale
    df_aggiornato.to_csv("mappatura_comuni_finale.csv", index=False, encoding='utf-8')
    print(f"\n4. Mappatura finale salvata in: mappatura_comuni_finale.csv")
    print(f"   Totale comuni: {len(df_aggiornato)}")
    print(f"   Comuni con adapter identificato: {(df_aggiornato['scraper_adapter'] != 'unknown').sum()}")
    
    print("\n=== Mappatura Comuni Italiani Generata con Successo ===")
    print("\nFile generati:")
    print("- mappatura_comuni_template.csv: Template base con dati ISTAT")
    print("- mappatura_comuni_aggiornata.csv: Versione con dati aggiunti da IndicePA")
    print("- mappatura_comuni_finale.csv: Versione completa con adapter identificati")

if __name__ == "__main__":
    main()