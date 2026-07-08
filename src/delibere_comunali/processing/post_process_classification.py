#!/usr/bin/env python3
"""
Modulo di post-processing per ottimizzare la classificazione dei documenti.
Questo modulo implementa le logiche di risoluzione delle ambiguità e miglioramento
del modello ML sviluppate per risolvere i problemi identificati.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.utils.class_weight import compute_class_weight
import argparse

# Importa la funzione get_tenant_dir per supportare il sistema multi-tenant
from delibere_comunali.utils.config import get_tenant_dir

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    elif "atto" in full_text and any(term in full_text for term in ["contabile", "finanziario", "bilancio", "spesa", "entrata"]):
        return "Contabilità"
    
    elif any(term in full_text for term in ["pubblicazione", "albo pretorio", "avviso", "bando"]):
        return "Pubblicazioni"
    
    elif any(term in full_text for term in ["protocollo", "ufficio", "servizio", "settore"]):
        return "Organizzazione"
    
    # Regole aggiuntive per casi specifici
    if any(term in full_text for term in ["ufficio tecnico", "ingegnere", "architetto", "progettazione"]):
        return "Lavori Pubblici"
    
    if any(term in full_text for term in ["ufficio ragioneria", "ragioniere", "contabilità", "tributo", "bilancio"]):
        return "Contabilità"
    
    if any(term in full_text for term in ["ufficio personale", "personale", "dipendenti", "dirigenza"]):
        return "Personale"
    
    # Se nessuna regola specifica è applicabile, restituisci None per mantenere la classificazione precedente
    return None


def resolve_ambiguities_with_ml(df, model):
    """Risolvi le ambiguità utilizzando il modello ML e le regole avanzate."""
    logger.info("Risoluzione ambiguità con modello ML e regole avanzate...")
    
    # Filtra solo i documenti ambigui
    ambiguous_mask = df['classification_confidence'] == 'ambiguous'
    ambiguous_docs = df[ambiguous_mask].copy()
    
    if len(ambiguous_docs) == 0:
        logger.info("Nessun documento ambiguo da risolvere.")
        return df
    
    logger.info(f"Trovati {len(ambiguous_docs)} documenti ambigui da risolvere.")
    
    # Prova a risolvere usando le regole avanzate per prima
    resolved_by_rules = 0
    for idx in ambiguous_docs.index:
        text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
        oggetto_col = 'oggetto' if 'oggetto' in df.columns else 'title'
        
        text_val = df.loc[idx, text_col] if text_col in df.columns else ""
        oggetto_val = df.loc[idx, oggetto_col] if oggetto_col in df.columns else ""
        
        rule_category = apply_advanced_classification_rules(text_val, oggetto_val)
        
        if rule_category is not None:
            df.loc[idx, 'category'] = rule_category
            df.loc[idx, 'classification_confidence'] = 'rule_based'
            resolved_by_rules += 1
    
    logger.info(f"Risolte {resolved_by_rules} ambiguità con regole avanzate.")
    
    # Per i documenti rimanenti, prova con il modello ML
    still_ambiguous_mask = df['classification_confidence'] == 'ambiguous'
    still_ambiguous_docs = df[still_ambiguous_mask].copy()
    
    if len(still_ambiguous_docs) > 0:
        text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
        text_available = still_ambiguous_docs[text_col].notna() & (still_ambiguous_docs[text_col].astype(str).str.len() > 50)
        docs_with_text = still_ambiguous_docs[text_available].copy()
        
        if len(docs_with_text) > 0:
            try:
                # Prepara i dati per la classificazione ML
                X = docs_with_text[text_col].astype(str)
                
                # Predici con il modello
                predictions = model.predict(X)
                prediction_probs = model.predict_proba(X)
                max_probs = np.max(prediction_probs, axis=1)
                
                # Applica le predizioni ai documenti originali
                for i, idx in enumerate(docs_with_text.index):
                    df.loc[idx, 'category'] = predictions[i]
                    
                    # Assegna confidenza in base alla probabilità
                    if max_probs[i] >= 0.65:
                        df.loc[idx, 'classification_confidence'] = 'ml_predicted_high_conf'
                    elif max_probs[i] >= 0.50:
                        df.loc[idx, 'classification_confidence'] = 'ml_predicted_medium_conf'
                    else:
                        df.loc[idx, 'classification_confidence'] = 'ml_predicted_low_conf'
                
                logger.info(f"Risolte {len(docs_with_text)} ambiguità con modello ML.")
            except Exception as e:
                logger.warning(f"Errore durante la classificazione ML: {e}")
    
    return df


def enhance_model_with_resolved_data(df, base_path):
    """Migliora il modello ML utilizzando i dati risolti dagli ambigui."""
    logger.info("Miglioramento del modello ML con dati risolti...")
    
    # Filtra i dati risolti (sia per regole che per ML con alta confidenza)
    resolved_mask = (
        (df['classification_confidence'] == 'rule_based') |
        (df['classification_confidence'] == 'ml_predicted_high_conf') |
        (df['classification_confidence'] == 'human_reviewed')
    )
    
    resolved_data = df[resolved_mask].copy()
    
    if len(resolved_data) < 10:  # Minimo numero di campioni per fare un retraining
        logger.info(f"Numero insufficiente di dati risolti ({len(resolved_data)}) per il retraining del modello.")
        return None
    
    logger.info(f"Utilizzo di {len(resolved_data)} documenti risolti per il miglioramento del modello.")
    
    # Prepara i dati
    text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
    X = resolved_data[text_col].astype(str)
    y = resolved_data['category']
    
    # Rimuovi eventuali NaN
    valid_idx = X.notna() & y.notna()
    X = X[valid_idx]
    y = y[valid_idx]
    
    if len(X) < 10:
        logger.info("Numero insufficiente di dati validi per il retraining del modello.")
        return None
    
    # Dividi i dati
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Calcola i pesi delle classi per gestire lo sbilanciamento
    classes = np.unique(y_train)
    class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, class_weights))
    
    # Pipeline con TF-IDF e Random Forest
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2), max_df=0.85, min_df=2)),
        ('clf', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=1, class_weight=class_weight_dict))
    ])
    
    # Addestra il modello
    pipeline.fit(X_train, y_train)
    
    # Valutazione del modello (solo se abbiamo dati di test sufficienti)
    if len(X_test) > 0 and len(y_test) > 0 and len(np.unique(y_test)) > 0:
        y_pred = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
        
        logger.info(f"Risultati del modello migliorato:")
        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Macro Precision: {precision:.4f}")
        logger.info(f"Macro Recall: {recall:.4f}")
        logger.info(f"Macro F1-Score: {f1:.4f}")
    
    # Salva il modello migliorato
    enhanced_model_path = base_path / "random_forest_model_enhanced.joblib"
    joblib.dump(pipeline, enhanced_model_path)
    logger.info(f"Modello migliorato salvato in: {enhanced_model_path}")
    
    return pipeline


def main():
    parser = argparse.ArgumentParser(description="Post-process classification results to improve quality")
    parser.add_argument("--base", default=None, help="Base directory for data files")
    parser.add_argument("--ente", default=None, help="Nome dell'ente per cui eseguire il post-processing (per supporto multi-tenant).")
    args = parser.parse_args()
    
    # Se viene fornito il nome dell'ente, usa il percorso standard per quell'ente
    if args.ente:
        base_path = Path(get_tenant_dir(args.ente))
    elif args.base:
        base_path = Path(args.base)
    else:
        # Default fallback
        base_path = Path("albo_download")
    
    # Assicurati che la directory esista
    base_path = base_path / "albo_download" if base_path.name != "albo_download" else base_path
    
    # Carica i dati
    allegati_path = base_path / "allegati_parsed.csv"
    features_path = base_path / "documenti_features.csv"
    
    if not allegati_path.exists():
        logger.error(f"File {allegati_path} non trovato")
        return
    
    df = pd.read_csv(allegati_path)
    
    # Carica anche il file features se esiste
    if features_path.exists():
        df_features = pd.read_csv(features_path)
        # Unisci i dati mantenendo le colonne uniche
        df = pd.merge(df, df_features, on='pdf_name', how='left', suffixes=('', '_feat'))
    
    logger.info(f"Dati caricati: {len(df)} documenti")
    
    # Carica il modello ML
    model_path = base_path / "faiss_index" / "random_forest_model.joblib"
    if not model_path.exists():
        logger.warning(f"Modello ML non trovato: {model_path}. Impossibile procedere con la riclassificazione.")
        return
    
    try:
        rf_model = joblib.load(model_path)
        logger.info(f"Modello ML caricato da: {model_path}")
    except Exception as e:
        logger.error(f"Errore nel caricamento del modello: {e}")
        return
    
    # Conta i documenti ambigui prima della riclassificazione
    ambiguous_before = len(df[df['classification_confidence'] == 'ambiguous'])
    logger.info(f"Documenti ambigui prima della riclassificazione: {ambiguous_before}")
    
    if ambiguous_before > 0:
        # Risolvi le ambiguità utilizzando il modello ML e le regole avanzate
        df = resolve_ambiguities_with_ml(df, rf_model)
        
        # Conta i documenti ambigui dopo la riclassificazione
        ambiguous_after = len(df[df['classification_confidence'] == 'ambiguous'])
        logger.info(f"Documenti ambigui dopo la riclassificazione: {ambiguous_after}")
        logger.info(f"Ambiguità risolte: {ambiguous_before - ambiguous_after}")
    
    # Migliora il modello utilizzando i dati risolti
    logger.info("Miglioramento del modello ML con dati risolti...")
    enhanced_model = enhance_model_with_resolved_data(df, base_path)
    
    if enhanced_model is not None:
        # Applica il modello migliorato ai documenti che avevano bassa confidenza
        low_conf_mask = df['classification_confidence'].isin(['ml_predicted_low_conf'])
        low_conf_docs = df[low_conf_mask].copy()
        
        if len(low_conf_docs) > 0:
            logger.info(f"Applicazione del modello migliorato ai {len(low_conf_docs)} documenti con bassa confidenza...")
            
            # Seleziona la colonna del testo
            text_column = 'text_preview' if 'text_preview' in low_conf_docs.columns else 'text'
            text_available = low_conf_docs[text_column].notna() & (low_conf_docs[text_column].astype(str).str.len() > 50)
            docs_with_text = low_conf_docs[text_available].copy()
            
            if len(docs_with_text) > 0:
                predictions = enhanced_model.predict(docs_with_text[text_column])
                prediction_probs = enhanced_model.predict_proba(docs_with_text[text_column])
                max_probs = np.max(prediction_probs, axis=1)
                
                # Aggiorna le classificazioni per aumentare la confidenza dove possibile
                mask_high_conf = max_probs >= 0.65
                mask_medium_conf = (max_probs >= 0.50) & (max_probs < 0.65)
                
                # Aggiorna la confidenza in base alla probabilità predetta
                updated_confidence = docs_with_text['classification_confidence'].copy()
                updated_confidence[mask_high_conf] = 'ml_predicted_high_conf'
                updated_confidence[mask_medium_conf] = 'ml_predicted_medium_conf'
                
                # Aggiorna le categorie predette
                updated_categories = predictions
                
                # Aggiorna il dataframe originale in modo sicuro
                df.loc[docs_with_text.index, 'category'] = updated_categories
                df.loc[docs_with_text.index, 'classification_confidence'] = updated_confidence
                
                improved_count = len(docs_with_text[mask_high_conf]) + len(docs_with_text[mask_medium_conf])
                logger.info(f"Riclassificati {improved_count} documenti da bassa a media/alta confidenza")
    
    # Salva i dati aggiornati
    df.to_csv(allegati_path, index=False)
    logger.info(f"Dati aggiornati salvati in: {allegati_path}")
    
    # Se esiste il file features, aggiorna anche quello
    if features_path.exists():
        df_features_subset = df[['pdf_name', 'category', 'classification_confidence']].copy()
        df_features_orig = pd.read_csv(features_path)
        df_features_orig = df_features_orig.set_index('pdf_name')
        df_features_subset = df_features_subset.set_index('pdf_name')
        df_features_orig.update(df_features_subset)
        df_features_orig.reset_index(inplace=True)
        df_features_orig.to_csv(features_path, index=False)
        logger.info(f"File features aggiornato salvato in: {features_path}")
    
    # Genera report finali
    report_dir = base_path / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Report delle statistiche di classificazione
    stats_report_path = report_dir / "classification_stats.csv"
    classification_stats = df['classification_confidence'].value_counts().reset_index()
    classification_stats.columns = ['confidence_level', 'count']
    classification_stats['percentage'] = (classification_stats['count'] / len(df)) * 100
    classification_stats.to_csv(stats_report_path, index=False)
    
    # Report delle categorie
    category_report_path = report_dir / "category_distribution.csv"
    category_stats = df['category'].value_counts().reset_index()
    category_stats.columns = ['category', 'count']
    category_stats['percentage'] = (category_stats['count'] / len(df)) * 100
    category_stats.to_csv(category_report_path, index=False)
    
    logger.info("Processo di post-processing completato con successo!")
    logger.info(f"Documenti ambigui risolti: {ambiguous_before - ambiguous_after}")
    logger.info(f"Documenti migliorati con modello potenziato: {improved_count if 'improved_count' in locals() else 0}")


if __name__ == "__main__":
    main()