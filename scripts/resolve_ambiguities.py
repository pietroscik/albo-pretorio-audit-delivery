#!/usr/bin/env python3
"""
Script per risolvere le ambiguità nella classificazione dei documenti.
Questo script analizza i documenti classificati come 'ambiguous' e applica
strategie avanzate per migliorare la classificazione.
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
import joblib
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(base_path):
    """Carica i dati dai file CSV."""
    allegati_path = base_path / "allegati_parsed.csv"
    features_path = base_path / "documenti_features.csv"
    
    if not allegati_path.exists():
        raise FileNotFoundError(f"File {allegati_path} non trovato")
    
    df_allegati = pd.read_csv(allegati_path)
    
    # Carica anche il file features se esiste
    if features_path.exists():
        df_features = pd.read_csv(features_path)
        # Unisci i dati
        df = pd.merge(df_allegati, df_features, on='pdf_name', how='left', suffixes=('', '_feat'))
    else:
        df = df_allegati
    
    return df

def identify_ambiguous_documents(df):
    """Identifica i documenti classificati come ambigui."""
    ambiguous_mask = df['classification_confidence'] == 'ambiguous'
    ambiguous_docs = df[ambiguous_mask].copy()
    
    logger.info(f"Trovati {len(ambiguous_docs)} documenti classificati come ambigui")
    
    if len(ambiguous_docs) > 0:
        logger.info("Distribuzione delle categorie nei documenti ambigui:")
        logger.info(ambiguous_docs['category'].value_counts())
    
    return ambiguous_docs

def apply_advanced_classification_rules(text_str, oggetto_str=""):
    """Applica regole avanzate di classificazione per risolvere ambiguità."""
    if pd.isna(text_str):
        text_str = ""
    
    if pd.isna(oggetto_str):
        oggetto_str = ""
        
    full_text = (oggetto_str + " " + text_str).lower()
    
    # Regole specifiche per distinguere tra categorie simili
    # Basate su pattern specifici trovati nei documenti reali
    if "determinazione" in full_text or "determina" in full_text:
        # Cerca termini specifici per la contabilità in ambito di determinazioni
        if any(term in full_text for term in ["impegno di spesa", "liquidazione", "fattura", "pagamento", "capitolo", "accertamento", "visto contabile"]):
            return "Contabilità"
        elif any(term in full_text for term in ["lavori pubblici", "progetto esecutivo", "manutenzione", "cantiere", "opera pubblica"]):
            return "Lavori Pubblici"
        elif any(term in full_text for term in ["personale", "assunzioni", "concorso", "selezione", "progressione"]):
            return "Personale"
    
    elif "delibera" in full_text:
        if any(term in full_text for term in ["approvazione", "regolamento", "modifica"]):
            return "Regolamenti"
        elif any(term in full_text for term in ["impegno di spesa", "variazione di bilancio", "riconoscimento debito"]):
            return "Contabilità"
    
    elif "ordinanza" in full_text:
        if any(term in full_text for term in ["ufficio", "responsabile", "organizzazione"]):
            return "Affari Generali"
    
    elif "pubblicazione" in full_text or "attestazione" in full_text:
        return "Pubblicazione e Trasparenza"
    
    elif any(term in full_text for term in ["contenzioso", "incarico legale", "patrocinio", "tribunale"]):
        return "Contenzioso"
    
    elif any(term in full_text for term in ["urbanistica", "piano di sviluppo", "permesso di costruire"]):
        return "Urbanistica"
    
    elif any(term in full_text for term in ["servizi sociali", "assistenza", "contributo economico"]):
        return "Servizi Sociali"
    
    elif any(term in full_text for term in ["cultura", "turismo", "manifestazione", "evento"]):
        return "Cultura e Turismo"
    
    elif any(term in full_text for term in ["ambiente", "ecologia", "rifiuti", "inquinamento"]):
        return "Ambiente"
    
    elif any(term in full_text for term in ["commercio", "suap", "attività produttive"]):
        return "Commercio"
    
    elif any(term in full_text for term in ["anagrafe", "stato civile", "elettorale"]):
        return "Servizi Demografici"
    
    # Se nessuna regola specifica si applica, ritorna None per lasciare decidere al modello ML
    return None

def resolve_ambiguities_with_ml(ambiguous_docs, model_path, base_path):
    """Riclassifica i documenti ambigui utilizzando il modello ML."""
    if not model_path.exists():
        logger.warning(f"Modello ML non trovato: {model_path}. Provvedere ad addestrarlo prima.")
        return ambiguous_docs
    
    try:
        rf_model = joblib.load(model_path)
        logger.info(f"Modello ML caricato da: {model_path}")
    except Exception as e:
        logger.error(f"Errore nel caricamento del modello: {e}")
        return ambiguous_docs

    # Prepara i dati per la riclassificazione
    text_column = 'text_preview' if 'text_preview' in ambiguous_docs.columns else 'text'
    
    if text_column not in ambiguous_docs.columns:
        logger.error(f"Colonna '{text_column}' non trovata nei dati ambigui")
        return ambiguous_docs
    
    # Filtra i documenti che hanno testo sufficiente
    text_available = ambiguous_docs[text_column].notna() & (ambiguous_docs[text_column].astype(str).str.len() > 50)
    docs_with_text = ambiguous_docs[text_available].copy()
    
    if len(docs_with_text) == 0:
        logger.info("Nessun documento con testo sufficiente per la riclassificazione ML")
        return ambiguous_docs
    
    logger.info(f"Riclassificazione di {len(docs_with_text)} documenti con testo sufficiente...")
    
    # Applica le regole avanzate prima del modello ML
    updated_categories = []
    updated_confidences = []
    
    for idx, row in docs_with_text.iterrows():
        # Prima prova con le regole avanzate
        rule_category = apply_advanced_classification_rules(
            str(row[text_column]), 
            str(row.get('oggetto', ''))
        )
        
        if rule_category:
            # Se le regole avanzate forniscono una categoria, usala
            updated_categories.append(rule_category)
            updated_confidences.append('rule_based')
        else:
            # Altrimenti usa il modello ML
            text_preview = str(row[text_column])[:1200]
            try:
                # Otteniamo la probabilità massima per valutare la confidenza
                prediction_probs = rf_model.predict_proba([text_preview])
                max_prob = np.max(prediction_probs)
                
                predicted_category = rf_model.predict([text_preview])[0]
                
                # Applica le soglie di confidenza
                if max_prob >= 0.65:
                    updated_categories.append(predicted_category)
                    updated_confidences.append('ml_predicted_high_conf')
                elif max_prob >= 0.50:
                    updated_categories.append(predicted_category)
                    updated_confidences.append('ml_predicted_medium_conf')
                else:
                    # Anche il modello ML è incerto, manteniamo come ambiguo ma con nuova categoria
                    updated_categories.append(predicted_category)
                    updated_confidences.append('ml_predicted_low_conf')
                    
            except Exception as e:
                logger.warning(f"Errore durante la predizione ML per {row.get('pdf_name', idx)}: {e}")
                # Manteniamo la classificazione originale se il modello fallisce
                updated_categories.append(row['category'])
                updated_confidences.append(row['classification_confidence'])
    
    # Aggiorna i dati originali
    docs_with_text.loc[:, 'category'] = updated_categories
    docs_with_text.loc[:, 'classification_confidence'] = updated_confidences
    
    # Aggiorna il dataframe completo
    ambiguous_docs.update(docs_with_text)
    
    return ambiguous_docs

def main():
    parser = argparse.ArgumentParser(description="Risolvi le ambiguità nella classificazione dei documenti.")
    parser.add_argument("--ente", default="avella", help="Nome dell'ente (es. avella, tufino).")
    parser.add_argument("--base", default=None, help="Cartella base dati. Default: data/{ente}/albo_download")
    parser.add_argument("--model-path", default=None, help="Percorso al modello ML. Default: <base>/random_forest_model.joblib")
    
    args = parser.parse_args()
    
    if args.base:
        base_path = Path(args.base)
    else:
        base_path = Path(f"data/{args.ente}/albo_download")
    
    if args.model_path:
        model_path = Path(args.model_path)
    else:
        model_path = base_path / "random_forest_model.joblib"
    
    logger.info(f"Caricamento dati da: {base_path}")
    logger.info(f"Modello ML atteso in: {model_path}")
    
    try:
        # Carica i dati
        df = load_data(base_path)
        logger.info(f"Dati caricati: {len(df)} documenti")
        
        # Identifica documenti ambigui
        ambiguous_docs = identify_ambiguous_documents(df)
        
        if len(ambiguous_docs) == 0:
            logger.info("Nessun documento ambiguo trovato. Operazione completata.")
            return
        
        # Risolvi le ambiguità con il modello ML
        resolved_docs = resolve_ambiguities_with_ml(ambiguous_docs, model_path, base_path)
        
        # Aggiorna il dataframe originale con i risultati
        df.update(resolved_docs)
        
        # Salva i risultati aggiornati
        allegati_path = base_path / "allegati_parsed.csv"
        features_path = base_path / "documenti_features.csv"
        
        # Salva allegati_parsed.csv aggiornato
        df.to_csv(allegati_path, index=False)
        logger.info(f"File aggiornato salvato: {allegati_path}")
        
        # Se esiste il file features, aggiorna anche quello
        if features_path.exists():
            df_features = pd.read_csv(features_path)
            # Aggiorna solo le colonne category e classification_confidence
            cols_to_update = ['pdf_name', 'category', 'classification_confidence']
            if all(col in df.columns for col in cols_to_update):
                df_subset = df[cols_to_update].copy()
                df_features_subset = df_features[['pdf_name', 'category', 'classification_confidence']].copy()
                df_features_subset.update(df_subset.set_index('pdf_name'), overwrite=True)
                df_features.update(df_features_subset.set_index('pdf_name'), overwrite=True)
                df_features.to_csv(features_path, index=False)
                logger.info(f"File features aggiornato salvato: {features_path}")
        
        # Stampa un riassunto dei cambiamenti
        original_ambiguous = len(ambiguous_docs)
        still_ambiguous = len(df[df['classification_confidence'] == 'ambiguous'])
        resolved = original_ambiguous - still_ambiguous
        
        logger.info(f"Risoluzione ambiguità completata:")
        logger.info(f"- Documenti ambigui iniziali: {original_ambiguous}")
        logger.info(f"- Documenti ancora ambigui: {still_ambiguous}")
        logger.info(f"- Documenti risolti: {resolved}")
        logger.info(f"- Risoluzione: {(resolved/original_ambiguous)*100:.2f}%")
        
        if resolved > 0:
            logger.info("Distribuzione delle nuove categorie nei documenti risolti:")
            resolved_categories = df[(df.index.isin(ambiguous_docs.index)) & (df['classification_confidence'] != 'ambiguous')]['category']
            logger.info(resolved_categories.value_counts())
        
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione: {e}")
        raise

if __name__ == "__main__":
    main()