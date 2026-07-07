#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per arricchire i metadati con la tipologia mancante
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

def infer_tipologia_from_text(titolo, oggetto):
    """
    Inferisce la tipologia dal titolo e dall'oggetto del documento.
    """
    # Combina titolo e oggetto per l'analisi
    full_text = ""
    if pd.notna(titolo):
        full_text += str(titolo) + " "
    if pd.notna(oggetto):
        full_text += str(oggetto)
    
    full_text = full_text.lower()
    
    # Rimuovi caratteri speciali e normalizza
    full_text = re.sub(r'[^\w\s]', ' ', full_text)
    
    # Regole per inferire la tipologia
    tipologia_rules = {
        'Determina': [
            'determina', 'determinazione', 'settore', 'responsabile', 
            'direttore', 'ufficio', 'area', 'servizio', 'impegno', 'liquidazione'
        ],
        'Delibera': [
            'deliber', 'giunta', 'consiglio', 'commissario', 'assemblea',
            'seduta', 'approv', 'adunanza', 'verbale', 'convocat'
        ],
        'Ordinanza': [
            'ordinanza', 'sindaco', 'sindac', 'prefetto', 'presidente',
            'divieto', 'dispone', 'ordina', 'provvede', 'esegue'
        ],
        'Avviso': [
            'avviso', 'pubblic', 'notifica', 'comunic', 'invito', 'presentazione',
            'domanda', 'istanza', 'scadenza', 'termini', 'modalità'
        ],
        'Bando': [
            'bando', 'gara', 'appalto', 'concorso', 'manifestazione', 'interesse',
            'offerta', 'partecipazione', 'aggiudicazione', 'criteri'
        ],
        'Decreto': [
            'decreto', 'commissario', 'dirigente', 'responsabile', 'ufficio',
            'nomina', 'attribuzione', 'funzioni', 'delega', 'autorizzazione'
        ],
        'Regolamento': [
            'regolamento', 'statuto', 'disciplina', 'norme', 'modalità',
            'disciplinare', 'approvazione', 'modifica', 'emanazione'
        ],
        'Parere': [
            'parere', 'tecnico', 'legale', 'controllo', 'regolarit', 'verifica',
            'rilascio', 'rilascia', 'competenza', 'osserva'
        ],
        'Visto': [
            'visto', 'contabile', 'contab', 'bilancio', 'impegno', 'liquidazione',
            'competenza', 'cassa', 'regolarit', 'accertamento'
        ],
        'Certificato': [
            'certificato', 'certifica', 'atto', 'constata', 'documento',
            'autentico', 'verifica', 'riscontro', 'risulta'
        ]
    }
    
    # Calcola punteggio per ogni tipologia
    scores = {}
    for tipologia, keywords in tipologia_rules.items():
        score = sum(1 for keyword in keywords if keyword in full_text)
        scores[tipologia] = score
    
    # Restituisci la tipologia con il punteggio più alto, se > 0
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        return 'Altro'  # Default per casi non riconosciuti

def enhance_metadata_with_tipologia(input_path, output_path):
    """
    Arricchisce i metadati con la tipologia mancante.
    """
    logger.info(f"Caricamento metadati da: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"Caricati {len(df)} record di metadati")
    
    # Conta i record con tipologia mancante
    missing_tipologia = df['tipologia'].isna() | df['tipologia'].eq('')
    logger.info(f"Record con tipologia mancante: {missing_tipologia.sum()}")
    
    # Inferisci la tipologia per i record mancanti
    for idx in df[missing_tipologia].index:
        titolo = df.loc[idx, 'titolo']
        oggetto = df.loc[idx, 'oggetto']
        
        inferred_tipologia = infer_tipologia_from_text(titolo, oggetto)
        df.loc[idx, 'tipologia'] = inferred_tipologia
        
        if idx % 100 == 0:  # Log progresso ogni 100 record
            logger.info(f"Elaborati {idx} record...")
    
    # Salva il file aggiornato
    df.to_csv(output_path, index=False)
    logger.info(f"File metadati aggiornato salvato in: {output_path}")
    
    # Stampa statistiche finali
    final_missing = df['tipologia'].isna() | df['tipologia'].eq('')
    logger.info(f"Dopo l'arricchimento:")
    logger.info(f"Record con tipologia mancante: {final_missing.sum()}")
    
    # Mostra distribuzione finale delle tipologie
    logger.info("Distribuzione finale delle tipologie:")
    print(df['tipologia'].value_counts())
    
    return df

def main():
    parser = argparse.ArgumentParser(description="Arricchimento metadati con tipologia mancante")
    parser.add_argument("--input", required=True, help="Percorso del file CSV di input")
    parser.add_argument("--output", required=True, help="Percorso del file CSV di output")
    
    args = parser.parse_args()
    
    try:
        df = enhance_metadata_with_tipologia(args.input, args.output)
        
        print("\n✅ Arricchimento metadati completato con successo!")
        print(f"File aggiornato salvato in: {args.output}")
        
    except Exception as e:
        logger.error(f"Errore durante l'arricchimento metadati: {e}")
        raise

if __name__ == "__main__":
    main()