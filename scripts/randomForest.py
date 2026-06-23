import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
import joblib
import os
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="albo_download", help="Percorso base dei dati")
    args = parser.parse_args()

    # 1. Caricamento del dataset
    base_path = Path(args.base)
    file_path = base_path / 'documenti_features.csv'
    allegati_path = base_path / 'allegati_parsed.csv'
    excel_path = base_path / 'albo_analisi.xlsx'

    if not file_path.exists():
        print(f"ERRORE: File {file_path} non trovato. Esegui analyze_albo.py prima.")
        return

    df_features = pd.read_csv(file_path)
    try:
        df_allegati = pd.read_csv(allegati_path)
    except FileNotFoundError:
        print(f"ERRORE: File {allegati_path} non trovato.")
        return

    # --- FEEDBACK LOOP (ACTIVE LEARNING) ---
    if excel_path.exists():
        try:
            xl = pd.ExcelFile(excel_path)
            if 'revisione_ml' in xl.sheet_names:
                df_revision = pd.read_excel(xl, sheet_name='revisione_ml')
                if 'categoria_corretta' in df_revision.columns:
                    corrections = df_revision.dropna(subset=['categoria_corretta']).copy()
                    if not corrections.empty:
                        print(f"[*] Trovate {len(corrections)} correzioni manuali in Excel. Aggiorno il dataset...")
                        corr_map = dict(zip(corrections['pdf_name'], corrections['categoria_corretta']))
                        for name, cat in corr_map.items():
                            df_features.loc[df_features['pdf_name'] == name, 'category'] = cat
                            df_features.loc[df_features['pdf_name'] == name, 'classification_confidence'] = 'high'
                            df_allegati.loc[df_allegati['pdf_name'] == name, 'category'] = cat
                            df_allegati.loc[df_allegati['pdf_name'] == name, 'classification_confidence'] = 'high'
                        df_features.to_csv(file_path, index=False)
                        df_allegati.to_csv(allegati_path, index=False)
        except Exception as e:
            print(f"[WARN] Impossibile leggere correzioni Excel: {e}")

    # Uniamo i due dataset
    df = pd.merge(df_features, df_allegati, on='pdf_name', how='inner', suffixes=('', '_allegati'))

    # Selezione colonna testo
    text_column = next((c for c in ['text_preview', 'text', 'extracted_text'] if c in df.columns), None)
    if not text_column:
        print("ERRORE: Nessuna colonna di testo trovata.")
        return

    df = df.dropna(subset=[text_column, 'category'])

    # 2. Training e Test Set
    # Consideriamo 'high' confidence o 'high_ml' (già validate)
    train_mask = df['classification_confidence'].isin(['high', 'high_ml'])
    high_conf_df = df[train_mask].copy()
    
    if len(high_conf_df) < 5:
        print(f"Dataset troppo piccolo per il training ({len(high_conf_df)} documenti validi). Saltaggio training.")
        return

    X = high_conf_df[text_column]
    y = high_conf_df['category']

    # Divisione stratificata
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Pipeline Standard (Scikit-Learn Nativo)
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=3000, ngram_range=(1, 2), max_df=0.8, min_df=2)),
        ('clf', RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight='balanced'))
    ])

    print(f"Addestramento su {len(X_train)} documenti...")
    pipeline.fit(X_train, y_train)

    # 4. Valutazione
    y_pred = pipeline.predict(X_test)
    print(f"\nAccuracy Globale: {accuracy_score(y_test, y_pred):.4f}")
    print(classification_report(y_test, y_pred, zero_division=0))

    # 5. Salvataggio
    model_dir = base_path / 'faiss_index' # Salviamo nella cartella dell'ente per isolamento
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / 'random_forest_model.joblib'
    joblib.dump(pipeline, model_path)
    print(f"[OK] Modello salvato in: {model_path}")

    # 6. Riclassificazione Ambigui
    ambiguous_mask = df['classification_confidence'].isin(['ambiguous', 'unknown', 'unknown_low', 'low'])
    ambiguous_df = df[ambiguous_mask].copy()
    
    if not ambiguous_df.empty:
        print(f"\nRiclassificazione di {len(ambiguous_df)} documenti...")
        probs = pipeline.predict_proba(ambiguous_df[text_column])
        preds = pipeline.predict(ambiguous_df[text_column])
        conf = np.max(probs, axis=1)
        
        ambiguous_df['predicted_category'] = preds
        ambiguous_df['predicted_confidence'] = conf
        
        # Aggiornamento Dataset
        sicuri_count = 0
        for idx, row in ambiguous_df.iterrows():
            if row['predicted_confidence'] >= 0.50:
                df_features.loc[df_features['pdf_name'] == row['pdf_name'], 'category'] = row['predicted_category']
                df_features.loc[df_features['pdf_name'] == row['pdf_name'], 'classification_confidence'] = 'ml_predicted'
                df_allegati.loc[df_allegati['pdf_name'] == row['pdf_name'], 'category'] = row['predicted_category']
                df_allegati.loc[df_allegati['pdf_name'] == row['pdf_name'], 'classification_confidence'] = 'ml_predicted'
                sicuri_count += 1
        
        df_features.to_csv(file_path, index=False)
        df_allegati.to_csv(allegati_path, index=False)
        print(f"Aggiornati {sicuri_count} documenti con predizioni ML.")

if __name__ == "__main__":
    main()
