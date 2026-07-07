#!/usr/bin/env python3
"""
Script per migliorare il modello ML utilizzando dati specifici dai documenti ambigui.
Questo script implementa un ciclo di active learning per migliorare continuamente 
la qualità del modello di classificazione.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, precision_recall_fscore_support, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_class_weight
from sklearn.model_selection import cross_validate
import joblib
import argparse
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(base_path):
    """Carica i dati dai file CSV."""
    allegati_path = base_path / "allegati_parsed.csv"
    features_path = base_path / "documenti_features.csv"
    
    if not allegati_path.exists():
        raise FileNotFoundError(f"File {allegati_path} non trovato")
    
    df_allegati = pd.read_csv(allegati_path)
    
    # Unisci con il file features se esiste
    if features_path.exists():
        df_features = pd.read_csv(features_path)
        # Unisci i dati mantenendo le colonne uniche
        df = pd.merge(df_allegati, df_features, on='pdf_name', how='left', suffixes=('', '_feat'))
    else:
        df = df_allegati
    
    return df

def prepare_training_data(df, use_ambiguous_as_training=False):
    """Prepara i dati per il training del modello ML."""
    # Scegli la colonna del testo da utilizzare
    text_column = 'text_preview' if 'text_preview' in df.columns else 'text'
    
    if text_column not in df.columns:
        raise ValueError(f"Colonna '{text_column}' non trovata nei dati")
    
    # Filtra i dati per la qualità della classificazione
    # Usa documenti con alta confidenza come dati di training principali
    high_conf_mask = df['classification_confidence'].isin(['high', 'ml_predicted_high_conf'])
    training_data = df[high_conf_mask].copy()
    
    logger.info(f"Dati di training con alta confidenza: {len(training_data)}")
    
    # Se non ci sono dati con alta confidenza, prova a usare i dati con confidenza media
    if len(training_data) == 0:
        medium_conf_mask = df['classification_confidence'].isin(['ml_predicted_medium_conf'])
        training_data = df[medium_conf_mask].copy()
        logger.info(f"Nessun dato con alta confidenza trovato. Usando {len(training_data)} dati con confidenza media.")
    
    # Se ancora non ci sono dati sufficienti, utilizza i dati risolti dagli ambigui
    if len(training_data) == 0 and use_ambiguous_as_training:
        # Cerca documenti che erano ambigui ma ora hanno una classificazione diversa
        # Dobbiamo identificarli confrontando con i dati originali
        resolved_ambiguous_mask = (
            df['classification_confidence'].str.contains('ml_predicted', na=False) & 
            (df['classification_confidence'] != 'ml_predicted_low_conf')  # Escludi quelli con bassa confidenza
        )
        resolved_data = df[resolved_ambiguous_mask].copy()
        logger.info(f"Usando {len(resolved_data)} dati risolti dagli ambigui come dati di training.")
        
        if len(resolved_data) > 0:
            training_data = resolved_data
        else:
            # Se proprio non ci sono dati con confidenza sufficiente, proviamo con quelli a bassa confidenza
            low_conf_mask = df['classification_confidence'].isin(['ml_predicted_low_conf'])
            low_conf_data = df[low_conf_mask].copy()
            logger.info(f"Nessun dato con confidenza sufficiente trovato. Usando {len(low_conf_data)} dati con bassa confidenza per training (ultimo tentativo).")
            
            if len(low_conf_data) > 0:
                training_data = low_conf_data
            else:
                raise ValueError(f"Nessun dato adatto per il training trovato. Dataset troppo piccolo: {len(training_data)} documenti")
    
    # Rimuovi righe con testo o categoria mancanti
    training_data = training_data.dropna(subset=[text_column, 'category'])
    
    if len(training_data) < 5:  # Abbassiamo la soglia minima
        logger.warning(f"Dataset molto piccolo per il training: {len(training_data)} documenti")
        if len(training_data) == 0:
            raise ValueError(f"Dataset troppo piccolo per il training: {len(training_data)} documenti")
    
    logger.info(f"Totale dati di training dopo filtraggio: {len(training_data)}")
    
    # Bilancia le classi se necessario
    class_counts = training_data['category'].value_counts()
    logger.info("Distribuzione delle classi:")
    for cat, count in class_counts.items():
        logger.info(f"  {cat}: {count}")
    
    # Rimuovi categorie con pochi esempi se necessario
    min_samples_per_class = 1  # Abbassiamo la soglia per consentire anche classi con un solo esempio
    valid_categories = class_counts[class_counts >= min_samples_per_class].index
    training_data = training_data[training_data['category'].isin(valid_categories)]
    
    if len(training_data) < 1:
        raise ValueError(f"Dataset troppo piccolo dopo rimozione classi rare: {len(training_data)} documenti")
    
    X = training_data[text_column]
    y = training_data['category']
    
    return X, y, text_column

def train_optimized_model(X, y):
    """Addestra un modello ottimizzato con ricerca degli iperparametri."""
    logger.info("Inizio ottimizzazione del modello...")
    
    # Controlla la distribuzione delle classi
    class_counts = pd.Series(y).value_counts()
    min_class_count = class_counts.min()
    
    # Se abbiamo classi con meno di 2 membri, non possiamo usare stratify
    if min_class_count < 2:
        logger.info("Classi con meno di 2 membri trovate, uso divisione senza stratificazione")
        # Divisione train-test senza stratificazione
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    elif len(X) < 50:
        logger.info("Pochi dati disponibili: usando una griglia di parametri semplificata")
        # Divisione train-test con meno dati di test
        test_size = max(0.2, 2/len(X)) if len(X) > 2 else 0.0  # Assicura almeno 1 campione per test
        if test_size >= 1.0:
            # Se abbiamo solo 1 o 2 campioni, usiamo cross-validation leave-one-out
            X_train = X
            X_test = X.iloc[:1] if len(X) > 0 else X  # dummy
            y_train = y
            y_test = y.iloc[:1] if len(y) > 0 else y  # dummy
        else:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    else:
        # Divisione train-test con stratificazione
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Calcola i pesi delle classi per gestire lo sbilanciamento
    classes = np.unique(y_train)
    class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, class_weights))
    
    # Pipeline con TF-IDF e Random Forest - usiamo parametri meno intensivi
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2), max_df=0.85, min_df=2)),
        ('clf', RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42, n_jobs=1))  # Ridotto per velocizzare
    ])
    
    # Griglia di iperparametri più semplice per velocizzare
    param_grid = {
        'tfidf__max_features': [5000],  # Rimuovo opzioni per velocizzare
        'tfidf__ngram_range': [(1, 2)],  # Semplificato
        'tfidf__max_df': [0.85],
        'tfidf__min_df': [2],
        'clf__n_estimators': [50],  # Ridotto per velocizzare
        'clf__max_depth': [10],  # Limitato per velocizzare
        'clf__min_samples_split': [5],  # Semplificato
        'clf__class_weight': [class_weight_dict]
    }
    
    # Ricerca a griglia con cross-validation ridotta per velocizzare
    logger.info("Esecuzione della ricerca a griglia...")
    
    # Se abbiamo classi con meno di 3 membri, usiamo cross-validation senza stratificazione
    cv_strategy = 2  # Ridotto da 3 a 2 per velocizzare
    if min_class_count < 3:
        # Se alcuni fold potrebbero non contenere tutte le classi, usiamo una strategia più conservativa
        unique_labels = len(np.unique(y))
        cv_strategy = min(2, len(y), unique_labels)  # Ridotto ulteriormente
        if cv_strategy < 2:
            cv_strategy = 2  # Imposta almeno 2
    
    grid_search = GridSearchCV(
        pipeline, 
        param_grid, 
        cv=cv_strategy, 
        scoring='f1_macro',  # Usiamo f1_macro come richiesto dalle specifiche
        n_jobs=1,  # Impostato a 1 per evitare troppo carico
        verbose=1
    )
    
    grid_search.fit(X_train, y_train)
    
    logger.info(f"Migliori parametri trovati: {grid_search.best_params_}")
    
    # Valutazione del modello ottimizzato
    best_model = grid_search.best_estimator_
    
    # Predizioni sul test set (se abbiamo un test set significativo)
    if len(X_test) > 0 and len(np.unique(y_test)) > 0:
        y_pred = best_model.predict(X_test)
        
        # Calcolo delle metriche
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
        
        logger.info(f"\nRisultati del modello ottimizzato:")
        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Macro Precision: {precision:.4f}")
        logger.info(f"Macro Recall: {recall:.4f}")
        logger.info(f"Macro F1-Score: {f1:.4f}")
        
        # Report dettagliato
        logger.info("\nClassification Report:")
        logger.info(classification_report(y_test, y_pred, zero_division=0))
        
        # Cross-validation score
        cv_scores = cross_val_score(best_model, X_train, y_train, cv=cv_strategy, scoring='f1_macro')
        logger.info(f"\nCross-validation F1-macro scores: {cv_scores}")
        logger.info(f"CV F1-macro medio: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    else:
        logger.info("Non è stato possibile calcolare le metriche sul test set a causa della scarsità di dati")
    
    return best_model

def evaluate_model_performance(model, X_test, y_test):
    """Valuta le prestazioni del modello."""
    if len(X_test) == 0 or len(y_test) == 0:
        logger.warning("Nessun set di test disponibile per la valutazione")
        return
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
    
    logger.info(f"Evaluation on test set:")
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"Macro Precision: {precision:.4f}")
    logger.info(f"Macro Recall: {recall:.4f}")
    logger.info(f"Macro F1-Score: {f1:.4f}")

def main():
    parser = argparse.ArgumentParser(description="Migliora il modello ML con dati specifici dai documenti ambigui.")
    parser.add_argument("--ente", default="avella", help="Nome dell'ente (es. avella, tufino).")
    parser.add_argument("--base", default=None, help="Cartella base dati. Default: data/{ente}/albo_download")
    parser.add_argument("--model-path", default=None, help="Percorso per salvare il modello. Default: <base>/random_forest_model.joblib")
    parser.add_argument("--use-resolved-ambiguous", action="store_true", help="Usa anche i documenti ambigui risolti come dati di training")
    
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
    logger.info(f"Il modello verrà salvato in: {model_path}")
    
    try:
        # Carica i dati
        df = load_data(base_path)
        logger.info(f"Dati caricati: {len(df)} documenti totali")
        
        # Prepara i dati di training
        X, y, text_column = prepare_training_data(df, use_ambiguous_as_training=args.use_resolved_ambiguous)
        
        # Addestra il modello ottimizzato
        model = train_optimized_model(X, y)
        
        # Salva il modello
        model_dir = model_path.parent
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        logger.info(f"Modello salvato in: {model_path}")
        
        # Ora applichiamo il modello ai documenti ambigui per vedere il miglioramento
        ambiguous_mask = df['classification_confidence'] == 'ambiguous'
        ambiguous_docs = df[ambiguous_mask].copy()
        
        if len(ambiguous_docs) > 0:
            logger.info(f"Applicazione del nuovo modello ai {len(ambiguous_docs)} documenti ambigui...")
            
            # Applica il modello ai documenti ambigui
            text_available = ambiguous_docs[text_column].notna() & (ambiguous_docs[text_column].astype(str).str.len() > 50)
            docs_with_text = ambiguous_docs[text_available].copy()
            
            if len(docs_with_text) > 0:
                predictions = model.predict(docs_with_text[text_column])
                prediction_probs = model.predict_proba(docs_with_text[text_column])
                max_probs = np.max(prediction_probs, axis=1)
                
                # Aggiorna le classificazioni
                docs_with_text.loc[:, 'previous_category'] = docs_with_text['category']
                docs_with_text.loc[:, 'previous_confidence'] = docs_with_text['classification_confidence']
                docs_with_text.loc[:, 'category'] = predictions
                docs_with_text.loc[:, 'classification_confidence'] = [
                    'ml_predicted_high_conf' if prob >= 0.65 else 
                    'ml_predicted_medium_conf' if prob >= 0.50 else 
                    'ml_predicted_low_conf' 
                    for prob in max_probs
                ]
                
                # Aggiorna il dataframe originale
                df.update(docs_with_text)
                
                # Controlla quanto è stato risolto
                still_ambiguous = len(df[df['classification_confidence'] == 'ambiguous'])
                resolved = len(ambiguous_docs) - still_ambiguous
                resolution_rate = (resolved / len(ambiguous_docs)) * 100 if len(ambiguous_docs) > 0 else 0
                
                logger.info(f"Risultati dell'applicazione del nuovo modello:")
                logger.info(f"- Documenti ambigui iniziali: {len(ambiguous_docs)}")
                logger.info(f"- Documenti risolti: {resolved}")
                logger.info(f"- Tasso di risoluzione: {resolution_rate:.2f}%")
                
                # Mostra la distribuzione delle nuove categorie
                new_categories = df[df['classification_confidence'].str.contains('ml_predicted', na=False)]['category'].value_counts()
                if not new_categories.empty:
                    logger.info("Nuova distribuzione delle categorie dai documenti risolti:")
                    for cat, count in new_categories.items():
                        logger.info(f"  {cat}: {count}")
        
        # Ora applichiamo il modello ai documenti che avevano bassa confidenza per vedere se possiamo migliorarli
        low_conf_mask = df['classification_confidence'].isin(['ml_predicted_low_conf'])
        low_conf_docs = df[low_conf_mask].copy()
        
        if len(low_conf_docs) > 0:
            logger.info(f"Applicazione del nuovo modello ai {len(low_conf_docs)} documenti con bassa confidenza...")
            
            # Applica il modello ai documenti con bassa confidenza
            text_available = low_conf_docs[text_column].notna() & (low_conf_docs[text_column].astype(str).str.len() > 50)
            docs_with_text = low_conf_docs[text_available].copy()
            
            if len(docs_with_text) > 0:
                predictions = model.predict(docs_with_text[text_column])
                prediction_probs = model.predict_proba(docs_with_text[text_column])
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
        allegati_path = base_path / "allegati_parsed.csv"
        features_path = base_path / "documenti_features.csv"
        
        df.to_csv(allegati_path, index=False)
        logger.info(f"Dati aggiornati salvati in: {allegati_path}")
        
        if features_path.exists():
            df_features = pd.read_csv(features_path)
            # Aggiorna solo le colonne category e classification_confidence
            cols_to_update = ['pdf_name', 'category', 'classification_confidence']
            if all(col in df.columns for col in cols_to_update):
                df_subset = df[cols_to_update].copy()
                df_features.update(df_subset.set_index('pdf_name'))
                df_features.to_csv(features_path, index=False)
                logger.info(f"File features aggiornato salvato in: {features_path}")
        
        logger.info("Processo di miglioramento del modello completato con successo!")
        
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione: {e}")
        raise

if __name__ == "__main__":
    main()