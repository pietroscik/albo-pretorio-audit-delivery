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


def resolve_ambiguities_with_ml(df, rf_model, text_column='text_preview'):
    """Riclassifica i documenti ambigui utilizzando il modello ML e regole avanzate."""
    if rf_model is None:
        logger.warning("Modello ML non fornito, impossibile risolvere le ambiguità")
        return df
    
    # Filtra i documenti che hanno testo sufficiente
    text_available = df[text_column].notna() & (df[text_column].astype(str).str.len() > 50)
    docs_with_text = df[text_available].copy()
    
    if len(docs_with_text) == 0:
        logger.info("Nessun documento con testo sufficiente per la riclassificazione ML")
        return df
    
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
    df.update(docs_with_text)
    
    return df


def enhance_model_with_resolved_data(df, base_path):
    """Migliora il modello ML utilizzando i dati risolti dagli ambigui."""
    # Seleziona i dati che hanno una classificazione con buona confidenza
    high_confidence_mask = df['classification_confidence'].isin(['rule_based', 'ml_predicted_high_conf', 'ml_predicted_medium_conf'])
    training_data = df[high_confidence_mask].copy()
    
    if len(training_data) == 0:
        logger.warning("Nessun dato con sufficiente confidenza per migliorare il modello")
        return None
    
    # Seleziona la colonna del testo da utilizzare
    text_column = 'text_preview' if 'text_preview' in training_data.columns else 'text'
    if text_column not in training_data.columns:
        logger.warning(f"Colonna '{text_column}' non trovata nei dati per il miglioramento del modello")
        return None
    
    # Rimuovi righe con testo o categoria mancanti
    training_data = training_data.dropna(subset=[text_column, 'category'])
    
    if len(training_data) < 10:  # Minimo necessario per il training
        logger.warning(f"Dataset troppo piccolo per il miglioramento del modello: {len(training_data)} documenti")
        return None
    
    logger.info(f"Miglioramento del modello con {len(training_data)} documenti ad alta confidenza")
    
    # Prepara i dati
    X = training_data[text_column]
    y = training_data['category']
    
    # Dividi i dati per il training
    try:
        # Se abbiamo meno di 10 campioni, usiamo tutti per il training
        if len(X) < 10:
            X_train = X
            y_train = y
        else:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if len(y.unique()) <= len(X)//2 else None)
    except:
        # Se la stratificazione fallisce, esegui senza
        if len(X) >= 2:  # Assicurati di avere almeno 2 campioni
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            X_train = X
            y_train = y
            X_test = X  # dummy
            y_test = y  # dummy
    
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
    parser.add_argument("--base", default="albo_download", help="Base directory for data files")
    args = parser.parse_args()
    
    base_path = Path(args.base)
    
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