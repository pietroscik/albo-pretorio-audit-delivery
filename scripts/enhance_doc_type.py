#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per migliorare la classificazione del tipo di documento
basata sull'analisi del titolo e dell'oggetto.
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

def infer_doc_type_from_text(oggetto, pdf_name):
    """
    Inferisce il tipo di documento dall'oggetto e dal nome del file.
    """
    # Combina oggetto e nome del file per l'analisi
    full_text = ""
    if pd.notna(oggetto):
        full_text += str(oggetto) + " "
    if pd.notna(pdf_name):
        full_text += str(pdf_name)
    
    full_text = full_text.lower()
    
    # Rimuovi caratteri speciali e normalizza
    full_text = re.sub(r'[^\w\s]', ' ', full_text)
    
    # Regole per inferire il tipo di documento
    doc_type_rules = {
        'ParereTecnico': [
            'parere', 'tecnico', 'regolarit', 'verifica', 'controllo', 'osserva'
        ],
        'VistoContabile': [
            'visto', 'contabil', 'impegno', 'liquidazione', 'bilancio', 'accertamento'
        ],
        'Determinazione': [
            'determin', 'settore', 'responsabile', 'direttore', 'ufficio', 'area', 'servizio'
        ],
        'Delibera': [
            'deliber', 'giunta', 'consiglio', 'commissario', 'assemblea', 'seduta'
        ],
        'Ordinanza': [
            'ordinanza', 'sindaco', 'sindac', 'prefetto', 'presidente', 'dispone'
        ],
        'Avviso': [
            'avviso', 'pubblic', 'notifica', 'comunic', 'invito', 'presentazione'
        ],
        'Bando': [
            'bando', 'gara', 'appalto', 'concorso', 'manifestazione', 'interesse'
        ],
        'Decreto': [
            'decreto', 'commissario', 'dirigente', 'responsabile', 'nomina'
        ],
        'AttestazionePubblicazione': [
            'pubblicazione', 'certificato', 'affissione', 'albo', 'pretorio', 'pubblico'
        ],
        'Regolamento': [
            'regolamento', 'statuto', 'disciplina', 'norme', 'modalità'
        ]
    }
    
    # Calcola punteggio per ogni tipo
    scores = {}
    for doc_type, keywords in doc_type_rules.items():
        score = sum(1 for keyword in keywords if keyword in full_text)
        scores[doc_type] = score
    
    # Restituisci il tipo con il punteggio più alto, se > 0
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        # Se nessuna corrispondenza precisa, prova a estrarre dal nome del file
        if pd.notna(pdf_name):
            filename_lower = str(pdf_name).lower()
            if 'parere' in filename_lower:
                return 'ParereTecnico'
            elif 'determin' in filename_lower:
                return 'Determinazione'
            elif 'delib' in filename_lower:
                return 'Delibera'
            elif 'ordin' in filename_lower:
                return 'Ordinanza'
            elif 'avvis' in filename_lower:
                return 'Avviso'
            elif 'band' in filename_lower:
                return 'Bando'
            elif 'decret' in filename_lower:
                return 'Decreto'
            elif 'visto' in filename_lower:
                return 'VistoContabile'
            elif 'pubblic' in filename_lower or 'certific' in filename_lower:
                return 'AttestazionePubblicazione'
        
        return 'Altro'  # Default per casi non riconosciuti

def enhance_doc_type(input_path, output_path):
    """
    Migliora la classificazione del tipo di documento.
    """
    logger.info(f"Caricamento dati da: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"Caricati {len(df)} documenti")
    
    # Trova documenti con tipo sconosciuto
    unknown_type_mask = df['doc_type'] == 'unknown'
    logger.info(f"Documenti con tipo sconosciuto: {unknown_type_mask.sum()}")
    
    # Inferisci il tipo per i documenti sconosciuti
    for idx in df[unknown_type_mask].index:
        oggetto = df.loc[idx, 'oggetto']
        pdf_name = df.loc[idx, 'pdf_name']
        
        inferred_type = infer_doc_type_from_text(oggetto, pdf_name)
        df.loc[idx, 'doc_type'] = inferred_type
        
        if idx % 50 == 0:  # Log progresso ogni 50 record
            logger.info(f"Elaborati {idx} record...")
    
    # Salva il file aggiornato
    df.to_csv(output_path, index=False)
    logger.info(f"File aggiornato salvato in: {output_path}")
    
    # Stampa statistiche finali
    final_unknown = (df['doc_type'] == 'unknown').sum()
    logger.info(f"Dopo il miglioramento:")
    logger.info(f"Documenti con tipo sconosciuto: {final_unknown}")
    
    # Mostra distribuzione finale dei tipi
    logger.info("Distribuzione finale dei tipi di documento:")
    print(df['doc_type'].value_counts().head(15))
    
    return df

def main():
    parser = argparse.ArgumentParser(description="Miglioramento classificazione tipo di documento")
    parser.add_argument("--input", required=True, help="Percorso del file CSV di input")
    parser.add_argument("--output", required=True, help="Percorso del file CSV di output")
    
    args = parser.parse_args()
    
    try:
        df = enhance_doc_type(args.input, args.output)
        
        print("\n✅ Miglioramento classificazione tipo documento completato con successo!")
        print(f"File aggiornato salvato in: {args.output}")
        
    except Exception as e:
        logger.error(f"Errore durante il miglioramento: {e}")
        raise

if __name__ == "__main__":
    main()