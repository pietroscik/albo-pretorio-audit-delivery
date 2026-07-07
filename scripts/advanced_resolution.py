#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script avanzato per risolvere documenti ambigui e senza categoria
basato sull'analisi dei contenuti testuali e contestuali.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
import re

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def advanced_text_analysis(text_str, doc_type=None, oggetto=None):
    """
    Funzione avanzata di analisi testuale per risolvere ambiguità.
    """
    if pd.isna(text_str):
        text_str = ""
    
    if pd.isna(oggetto):
        oggetto = ""
        
    full_text = (oggetto + " " + text_str).lower()
    
    # Pulizia del testo
    full_text = re.sub(r'\W+', ' ', full_text).lower()
    
    # Regole contestuali avanzate
    # Contabilità
    accounting_keywords = [
        'impegno', 'spesa', 'liquidazione', 'fattura', 'pagamento', 
        'capitolo', 'accertamento', 'visto contabile', 'bilancio',
        'competenza', 'cassa', 'residui', 'previsione', 'gestione',
        'accertamento', 'competenza', 'accantonamento', 'variazione'
    ]
    
    # Lavori Pubblici
    works_keywords = [
        'lavori', 'pubblici', 'progetto', 'esecutivo', 'manutenzione',
        'cantiere', 'opera', 'infrastruttura', 'strada', 'marciapiede',
        'costruzione', 'ristrutturazione', 'abbattimento', 'realizzazione'
    ]
    
    # Personale
    personnel_keywords = [
        'personale', 'assunzione', 'concorso', 'selezione', 'progressione',
        'inquadramento', 'trasferimento', 'destinazione', 'mobilità',
        'comando', 'distacco', 'aspettativa', 'maternità', 'permesso'
    ]
    
    # Regolamenti
    regulation_keywords = [
        'regolamento', 'approvazione', 'modifica', 'disciplina',
        'normativa', 'interno', 'approvato', 'statuto', 'disciplinare'
    ]
    
    # Servizi
    service_keywords = [
        'servizio', 'ufficio', 'organizzazione', 'funzioni', 'strumentale',
        'supporto', 'gestione', 'amministrazione', 'affari', 'protocollo'
    ]
    
    # Pubblicazione e Trasparenza
    transparency_keywords = [
        'pubblicazione', 'trasparenza', 'pubblico', 'affissione',
        'albo', 'pretorio', 'avviso', 'certificato', 'pubblicità'
    ]
    
    # Conteggio occorrenze per categoria
    accounting_score = sum(1 for keyword in accounting_keywords if keyword in full_text)
    works_score = sum(1 for keyword in works_keywords if keyword in full_text)
    personnel_score = sum(1 for keyword in personnel_keywords if keyword in full_text)
    regulation_score = sum(1 for keyword in regulation_keywords if keyword in full_text)
    service_score = sum(1 for keyword in service_keywords if keyword in full_text)
    transparency_score = sum(1 for keyword in transparency_keywords if keyword in full_text)
    
    # Determinazione automatica basata sui punteggi
    scores = {
        'Contabilità': accounting_score,
        'Lavori Pubblici': works_score,
        'Personale': personnel_score,
        'Regolamenti': regulation_score,
        'Affari Generali': service_score,
        'Pubblicazione e Trasparenza': transparency_score
    }
    
    # Seleziona la categoria con punteggio più alto, ma solo se > 0
    if max(scores.values()) > 0:
        predicted_category = max(scores, key=scores.get)
        confidence = max(scores.values()) / sum(scores.values()) if sum(scores.values()) > 0 else 0
        return predicted_category, confidence
    else:
        # Se nessuna parola chiave trovata, usa tipo documento e contesto
        if doc_type:
            doc_type_lower = str(doc_type).lower()
            if 'determinazione' in doc_type_lower:
                return 'Contabilità', 0.6  # Default per determinazioni
            elif 'delibera' in doc_type_lower:
                return 'Regolamenti', 0.6  # Default per delibere
            elif 'parere' in doc_type_lower:
                return 'Affari Generali', 0.5  # Default per pareri tecnici
            elif 'visto' in doc_type_lower:
                return 'Contabilità', 0.6  # Visto contabile
            elif 'ord' in doc_type_lower:  # ordianza
                return 'Affari Generali', 0.5
        
        return None, 0

def resolve_remaining_ambiguities(csv_path, output_path):
    """
    Risolve i documenti ancora classificati come ambigui o senza categoria.
    """
    logger.info(f"Caricamento dati da: {csv_path}")
    
    df = pd.read_csv(csv_path)
    logger.info(f"Caricati {len(df)} documenti")
    
    # Trova documenti ambigui o senza categoria
    ambiguous_mask = df['classification_confidence'] == 'ambiguous'
    uncategorized_mask = df['category'].isna() | (df['category'] == 'nan') | (df['category'] == '')
    
    logger.info(f"Documenti ambigui: {ambiguous_mask.sum()}")
    logger.info(f"Documenti senza categoria: {uncategorized_mask.sum()}")
    
    # Risolvi ambiguità
    for idx in df[ambiguous_mask | uncategorized_mask].index:
        row = df.loc[idx]
        
        # Ottieni testo e contesto
        text_preview = row.get('text_preview', '') if pd.notna(row.get('text_preview')) else ''
        oggetto = row.get('oggetto', '') if pd.notna(row.get('oggetto')) else ''
        doc_type = row.get('doc_type', '')
        
        # Analisi testuale avanzata
        predicted_category, confidence = advanced_text_analysis(
            text_preview, 
            doc_type, 
            oggetto
        )
        
        if predicted_category:
            df.loc[idx, 'category'] = predicted_category
            
            # Imposta confidenza in base al punteggio
            if confidence >= 0.7:
                df.loc[idx, 'classification_confidence'] = 'ml_predicted_high_conf'
            elif confidence >= 0.5:
                df.loc[idx, 'classification_confidence'] = 'ml_predicted_medium_conf'
            else:
                df.loc[idx, 'classification_confidence'] = 'ml_predicted'
    
    # Salva il file aggiornato
    df.to_csv(output_path, index=False)
    logger.info(f"File aggiornato salvato in: {output_path}")
    
    # Stampa statistiche finali
    final_ambiguous = (df['classification_confidence'] == 'ambiguous').sum()
    final_uncategorized = df['category'].isna().sum()
    
    logger.info(f"Dopo la risoluzione:")
    logger.info(f"Documenti ambigui rimasti: {final_ambiguous}")
    logger.info(f"Documenti senza categoria rimasti: {final_uncategorized}")
    
    return df

def main():
    parser = argparse.ArgumentParser(description="Risoluzione avanzata documenti ambigui e senza categoria")
    parser.add_argument("--input", required=True, help="Percorso del file CSV di input")
    parser.add_argument("--output", required=True, help="Percorso del file CSV di output")
    
    args = parser.parse_args()
    
    try:
        df = resolve_remaining_ambiguities(args.input, args.output)
        
        print("\n✅ Risoluzione avanzata completata con successo!")
        print(f"File aggiornato salvato in: {args.output}")
        
    except Exception as e:
        logger.error(f"Errore durante la risoluzione avanzata: {e}")
        raise

if __name__ == "__main__":
    main()