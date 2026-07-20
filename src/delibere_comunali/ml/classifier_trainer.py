import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_class_weight
import joblib
from pathlib import Path
import logging

from .rules import apply_advanced_classification_rules

logger = logging.getLogger(__name__)


def resolve_ambiguities_with_ml(df, rf_model, text_column='text_preview'):
    """Riclassifica i documenti ambigui utilizzando il modello ML e regole avanzate."""
    if rf_model is None:
        logger.warning("Modello ML non fornito, impossibile risolvere le ambiguità")
        return df

    text_available = df[text_column].notna() & (df[text_column].astype(str).str.len() > 50)
    docs_with_text = df[text_available].copy()

    if not docs_with_text.empty:
        logger.info(f"Riclassificazione di {len(docs_with_text)} documenti con testo sufficiente...")

        updated_categories = []
        updated_confidences = []

        for _, row in docs_with_text.iterrows():
            rule_category = apply_advanced_classification_rules(str(row[text_column]), str(row.get('oggetto', '')))
            if rule_category:
                updated_categories.append(rule_category)
                updated_confidences.append('rule_based')
            else:
                text_preview = str(row[text_column])[:1200]
                try:
                    prediction_probs = rf_model.predict_proba([text_preview])
                    max_prob = np.max(prediction_probs)
                    predicted_category = rf_model.predict([text_preview])[0]

                    if max_prob >= 0.65:
                        updated_categories.append(predicted_category)
                        updated_confidences.append('ml_predicted_high_conf')
                    elif max_prob >= 0.50:
                        updated_categories.append(predicted_category)
                        updated_confidences.append('ml_predicted_medium_conf')
                    else:
                        updated_categories.append(predicted_category)
                        updated_confidences.append('ml_predicted_low_conf')
                except Exception as e:
                    logger.warning(f"Errore durante la predizione ML per {row.get('pdf_name', 'N/A')}: {e}")
                    updated_categories.append(row['category'])
                    updated_confidences.append(row['classification_confidence'])

        docs_with_text['category'] = updated_categories
        docs_with_text['classification_confidence'] = updated_confidences
        df.update(docs_with_text)

    return df


def enhance_model_with_resolved_data(df, base_path):
    """Migliora il modello ML utilizzando i dati risolti dagli ambigui."""
    high_confidence_mask = df['classification_confidence'].isin(['rule_based', 'ml_predicted_high_conf', 'ml_predicted_medium_conf'])
    training_data = df[high_confidence_mask].copy()

    if training_data.empty:
        logger.warning("Nessun dato con sufficiente confidenza per migliorare il modello")
        return None

    text_column = 'text_preview' if 'text_preview' in training_data.columns else 'text'
    if text_column not in training_data.columns:
        logger.warning(f"Colonna '{text_column}' non trovata per il miglioramento del modello")
        return None

    training_data = training_data.dropna(subset=[text_column, 'category'])

    if len(training_data) < 10:
        logger.warning(f"Dataset troppo piccolo per il miglioramento del modello: {len(training_data)} documenti")
        return None

    logger.info(f"Miglioramento del modello con {len(training_data)} documenti ad alta confidenza")

    X = training_data[text_column]
    y = training_data['category']

    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    classes = np.unique(y_train)
    class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, class_weights))

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2), max_df=0.85, min_df=2)),
        ('clf', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=1, class_weight=class_weight_dict))
    ])

    pipeline.fit(X_train, y_train)

    if not X_test.empty:
        y_pred = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
        logger.info(f"Risultati del modello migliorato: Accuracy: {accuracy:.4f}, Macro F1: {f1:.4f}")

    enhanced_model_path = base_path / "random_forest_model_enhanced.joblib"
    joblib.dump(pipeline, enhanced_model_path)
    logger.info(f"Modello migliorato salvato in: {enhanced_model_path}")

    return pipeline


def train_and_evaluate_classifier(base_path: Path):
    """Funzione principale per addestrare e valutare il classificatore."""
    file_path = base_path / 'documenti_features.csv'
    allegati_path = base_path / 'allegati_parsed.csv'
    excel_path = base_path / 'albo_analisi.xlsx'

    if not file_path.exists():
        logger.error(f"File {file_path} non trovato. Esegui prima analyze_albo.py.")
        return

    df_features = pd.read_csv(file_path)
    try:
        df_allegati = pd.read_csv(allegati_path)
    except FileNotFoundError:
        logger.error(f"File {allegati_path} non trovato.")
        return

    # Active Learning Feedback Loop
    if excel_path.exists():
        try:
            xl = pd.ExcelFile(excel_path)
            if 'revisione_ml' in xl.sheet_names:
                df_revision = pd.read_excel(xl, sheet_name='revisione_ml')
                if 'categoria_corretta' in df_revision.columns:
                    corrections = df_revision.dropna(subset=['categoria_corretta']).copy()
                    if not corrections.empty:
                        logger.info(f"[*] Trovate {len(corrections)} correzioni manuali in Excel. Aggiorno il dataset...")
                        corr_map = dict(zip(corrections['pdf_name'], corrections['categoria_corretta']))
                        for name, cat in corr_map.items():
                            df_features.loc[df_features['pdf_name'] == name, 'category'] = cat
                            df_features.loc[df_features['pdf_name'] == name, 'classification_confidence'] = 'high'
                            df_allegati.loc[df_allegati['pdf_name'] == name, 'category'] = cat
                            df_allegati.loc[df_allegati['pdf_name'] == name, 'classification_confidence'] = 'high'
                        df_features.to_csv(file_path, index=False)
                        df_allegati.to_csv(allegati_path, index=False)
        except Exception as e:
            logger.warning(f"[WARN] Impossibile leggere correzioni Excel: {e}")

    df = pd.merge(df_features, df_allegati, on='pdf_name', how='inner', suffixes=('', '_allegati'))
    text_column = next((c for c in ['text_preview', 'text', 'extracted_text'] if c in df.columns), None)
    if not text_column:
        logger.error("ERRORE: Nessuna colonna di testo trovata.")
        return

    df = df.dropna(subset=[text_column, 'category'])

    train_mask = df['classification_confidence'].isin(['high', 'high_ml'])
    high_conf_df = df[train_mask].copy()

    if len(high_conf_df) < 5:
        logger.warning(f"Dataset troppo piccolo per il training ({len(high_conf_df)} documenti validi). Saltaggio training.")
        return

    X = high_conf_df[text_column]
    y = high_conf_df['category']

    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    logger.info("🔍 Ottimizzazione degli iperparametri...")
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=10000, ngram_range=(1, 3), max_df=0.85, min_df=2, stop_words='english')),
        ('clf', RandomForestClassifier(random_state=42, n_jobs=-1))
    ])

    param_grid = {
        'tfidf__max_features': [5000, 7500, 10000],
        'tfidf__ngram_range': [(1, 2), (1, 3)],
        'clf__n_estimators': [100, 200],
        'clf__max_depth': [10, 20, None],
        'clf__class_weight': ['balanced', None]
    }

    grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='f1_macro', n_jobs=-1, verbose=1)
    grid_search.fit(X_train, y_train)

    best_pipeline = grid_search.best_estimator_
    logger.info(f"✅ Migliori parametri: {grid_search.best_params_}")

    y_pred = best_pipeline.predict(X_test)
    f1 = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)[2]
    logger.info(f"\n📊 Risultati del modello ottimizzato: Macro F1-Score: {f1:.4f}")
    logger.info("\n📋 Classification Report Dettagliato:\n" + classification_report(y_test, y_pred, zero_division=0))

    model_dir = base_path / 'faiss_index'
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / 'random_forest_model.joblib'
    joblib.dump(best_pipeline, model_path)
    logger.info(f"[OK] Modello salvato in: {model_path}")

    ambiguous_before = len(df[df['classification_confidence'] == 'ambiguous'])
    if ambiguous_before > 0:
        logger.info("🔄 Riclassificazione documenti ambigui...")
        df = resolve_ambiguities_with_ml(df, best_pipeline, text_column)
        ambiguous_after = len(df[df['classification_confidence'] == 'ambiguous'])
        logger.info(f"Ambiguità risolte: {ambiguous_before - ambiguous_after}")

        df_features.set_index('pdf_name', inplace=True)
        df_features.update(df.set_index('pdf_name')[['category', 'classification_confidence']])
        df_features.reset_index(inplace=True)
        df_features.to_csv(file_path, index=False)

        df_allegati.set_index('pdf_name', inplace=True)
        df_allegati.update(df.set_index('pdf_name')[['category', 'classification_confidence']])
        df_allegati.reset_index(inplace=True)
        df_allegati.to_csv(allegati_path, index=False)
        logger.info("✅ File CSV aggiornati con le nuove classificazioni")

    logger.info("🚀 Miglioramento del modello ML con dati risolti...")
    enhance_model_with_resolved_data(df, base_path)

    logger.info("✅ Processo completato con successo!")