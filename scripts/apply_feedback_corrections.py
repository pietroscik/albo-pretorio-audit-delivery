#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per applicare le correzioni dal file feedback_operatore.csv 
ai dati principali allegati_parsed.csv
Supporta file con righe di strutture diverse (6 e 15 colonne)
"""

import pandas as pd
from pathlib import Path
import argparse
import logging
import csv

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_read_csv_with_mixed_structure(file_path):
    """
    Legge un file CSV che può contenere righe con strutture diverse
    """
    rows_6_fields = []
    rows_15_fields = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Salta l'header
        
        for row_num, row in enumerate(reader, start=2):  # Parti da 2 perché 1 è l'header
            if len(row) == 6:
                # Struttura vecchia: pdf_name, responsabile, beneficiario, category, falso_positivo, timestamp
                rows_6_fields.append({
                    'pdf_name': row[0],
                    'responsabile': row[1],
                    'beneficiario': row[2],
                    'category': row[3],
                    'falso_positivo': row[4],
                    'timestamp': row[5],
                    'structure_type': 'old'
                })
            elif len(row) == 15:
                # Struttura nuova: pdf_name, doc_type, responsabile, beneficiario, piva_beneficiario, 
                # importo_max, cig, cup, data_atto, numero_atto, iban, oggetto, category, falso_positivo, timestamp
                rows_15_fields.append({
                    'pdf_name': row[0],
                    'doc_type': row[1],
                    'responsabile': row[2],
                    'beneficiario': row[3],
                    'piva_beneficiario': row[4],
                    'importo_max': row[5],
                    'cig': row[6],
                    'cup': row[7],
                    'data_atto': row[8],
                    'numero_atto': row[9],
                    'iban': row[10],
                    'oggetto': row[11],
                    'category': row[12],
                    'falso_positivo': row[13],
                    'timestamp': row[14],
                    'structure_type': 'new'
                })
            else:
                logger.warning(f"Riga {row_num} con {len(row)} campi ignorata: {row[:5]}...")
    
    # Converti in DataFrame
    df_6 = pd.DataFrame(rows_6_fields) if rows_6_fields else pd.DataFrame(columns=['structure_type'])
    df_15 = pd.DataFrame(rows_15_fields) if rows_15_fields else pd.DataFrame(columns=['structure_type'])
    
    # Combina i DataFrame
    if df_6.empty and df_15.empty:
        return pd.DataFrame()
    elif df_6.empty:
        return df_15
    elif df_15.empty:
        return df_6
    else:
        combined_df = pd.concat([df_6, df_15], ignore_index=True)
        return combined_df

def apply_corrections_from_feedback(base_path):
    """
    Applica le correzioni dal file feedback_operatore.csv ai dati principali
    """
    # Percorsi dei file
    feedback_path = Path(base_path) / "report" / "feedback_operatore.csv"
    allegati_path = Path(base_path) / "allegati_parsed.csv"
    
    if not feedback_path.exists():
        logger.warning(f"File di feedback non trovato: {feedback_path}")
        return
    
    if not allegati_path.exists():
        logger.warning(f"File allegati_parsed.csv non trovato: {allegati_path}")
        return
    
    # Carica i dati
    logger.info("Caricamento dati...")
    feedback_df = safe_read_csv_with_mixed_structure(feedback_path)
    allegati_df = pd.read_csv(allegati_path)
    
    if feedback_df.empty:
        logger.warning("Nessun feedback da applicare")
        return
    
    logger.info(f"Caricati {len(feedback_df)} feedback (struttura vecchia: {(feedback_df['structure_type'] == 'old').sum()}, struttura nuova: {(feedback_df['structure_type'] == 'new').sum()}) e {len(allegati_df)} allegati")
    
    # Applica le correzioni in base alla struttura
    corrections_applied = 0
    for _, row in feedback_df.iterrows():
        pdf_name = row['pdf_name']
        
        # Trova la riga corrispondente negli allegati
        mask = allegati_df['pdf_name'] == pdf_name
        
        if mask.any():
            structure_type = row['structure_type']
            
            if structure_type == 'new':
                # Aggiorna tutti i campi corretti per la struttura nuova
                if pd.notna(row.get('doc_type')) and str(row['doc_type']) != 'nan' and row['doc_type'] != '':
                    allegati_df.loc[mask, 'doc_type'] = row['doc_type']
                
                if pd.notna(row.get('responsabile')) and str(row['responsabile']) != 'nan' and row['responsabile'] != '':
                    allegati_df.loc[mask, 'responsabile'] = row['responsabile']
                
                if pd.notna(row.get('beneficiario')) and str(row['beneficiario']) != 'nan' and row['beneficiario'] != '':
                    allegati_df.loc[mask, 'beneficiario'] = row['beneficiario']
                
                if pd.notna(row.get('piva_beneficiario')) and str(row['piva_beneficiario']) != 'nan' and row['piva_beneficiario'] != '':
                    allegati_df.loc[mask, 'piva_beneficiario'] = row['piva_beneficiario']
                
                if pd.notna(row.get('importo_max')) and str(row['importo_max']) != 'nan' and row['importo_max'] != '':
                    allegati_df.loc[mask, 'importo_max'] = row['importo_max']
                
                if pd.notna(row.get('cig')) and str(row['cig']) != 'nan' and row['cig'] != '':
                    allegati_df.loc[mask, 'cig'] = row['cig']
                
                if pd.notna(row.get('cup')) and str(row['cup']) != 'nan' and row['cup'] != '':
                    allegati_df.loc[mask, 'cup'] = row['cup']
                
                if pd.notna(row.get('data_atto')) and str(row['data_atto']) != 'nan' and row['data_atto'] != '':
                    allegati_df.loc[mask, 'data_atto'] = row['data_atto']
                
                if pd.notna(row.get('numero_atto')) and str(row['numero_atto']) != 'nan' and row['numero_atto'] != '':
                    allegati_df.loc[mask, 'numero_atto'] = row['numero_atto']
                
                if pd.notna(row.get('iban')) and str(row['iban']) != 'nan' and row['iban'] != '':
                    allegati_df.loc[mask, 'iban'] = row['iban']
                
                if pd.notna(row.get('oggetto')) and str(row['oggetto']) != 'nan' and row['oggetto'] != '':
                    allegati_df.loc[mask, 'oggetto'] = row['oggetto']
                
                if pd.notna(row.get('category')) and str(row['category']) != 'nan' and row['category'] != '':
                    allegati_df.loc[mask, 'category'] = row['category']
                
            elif structure_type == 'old':
                # Aggiorna i campi disponibili per la struttura vecchia
                if pd.notna(row.get('responsabile')) and str(row['responsabile']) != 'nan' and row['responsabile'] != '':
                    allegati_df.loc[mask, 'responsabile'] = row['responsabile']
                
                if pd.notna(row.get('beneficiario')) and str(row['beneficiario']) != 'nan' and row['beneficiario'] != '':
                    allegati_df.loc[mask, 'beneficiario'] = row['beneficiario']
                
                if pd.notna(row.get('category')) and str(row['category']) != 'nan' and row['category'] != '':
                    allegati_df.loc[mask, 'category'] = row['category']
            
            # Aggiorna la confidenza per indicare che questi dati sono stati validati manualmente
            allegati_df.loc[mask, 'classification_confidence'] = 'human_reviewed'
            
            corrections_applied += 1
            logger.info(f"Aggiornati dati per {pdf_name} (struttura: {structure_type})")
        else:
            logger.warning(f"Nessun documento trovato per il nome: {pdf_name}")
    
    # Salva il file aggiornato
    allegati_df.to_csv(allegati_path, index=False)
    logger.info(f"Dati aggiornati salvati in: {allegati_path}")
    
    # Stampa statistiche
    human_reviewed_count = (allegati_df['classification_confidence'] == 'human_reviewed').sum()
    total_corrections = len(feedback_df)
    
    logger.info(f"Totale tentativi di correzione: {total_corrections}")
    logger.info(f"Correzioni effettivamente applicate: {corrections_applied}")
    logger.info(f"Documenti con dati validati manualmente: {human_reviewed_count}")

def main():
    parser = argparse.ArgumentParser(description="Applica le correzioni dal file feedback_operatore.csv ai dati principali")
    parser.add_argument("--base", required=True, help="Percorso base della directory dati (es. data/avella/albo_download)")
    
    args = parser.parse_args()
    
    try:
        apply_corrections_from_feedback(args.base)
        print("\n✅ Correzioni applicate con successo!")
        
    except Exception as e:
        logger.error(f"Errore durante l'applicazione delle correzioni: {e}")
        raise

if __name__ == "__main__":
    main()