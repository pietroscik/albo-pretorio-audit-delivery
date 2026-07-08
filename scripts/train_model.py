import argparse
import pandas as pd
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, precision_recall_fscore_support
import numpy as np

# Importa la funzione get_tenant_dir per supportare il sistema multi-tenant
from delibere_comunali.utils.config import get_tenant_dir

def main():
    parser = argparse.ArgumentParser(description="Riaddestra il modello Random Forest con i dati revisionati.")
    parser.add_argument("--base", default=None, help="Cartella base dei dati.")
    parser.add_argument("--ente", default=None, help="Nome dell'ente per cui addestrare il modello (per supporto multi-tenant).")
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
    base = base_path / "albo_download" if base_path.name != "albo_download" else base_path
    csv_path = base / "allegati_parsed.csv"
    model_path = base / "random_forest_model.joblib"

    if not csv_path.exists():
        print(f"❌ Errore: File {csv_path} non trovato. Esegui prima analyze_albo.py.")
        return

    print(f"📥 Caricamento dataset da {csv_path}...")
    df = pd.read_csv(csv_path)

    # Filtrare i record che hanno una categoria valida e un testo di preview
    df_valid = df.dropna(subset=['category', 'text_preview']).copy()

    if len(df_valid) < 10:
        print("⚠️ Numero insufficiente di record per l'addestramento.")
        return

    print(f"📊 Totale record validi per l'addestramento: {len(df_valid)}")
    
    # Raggruppa le categorie rare in 'Altro' per evitare l'overfitting e i warning di Scikit-Learn
    class_counts = df_valid['category'].value_counts()
    rare_classes = class_counts[class_counts < 4].index
    df_valid.loc[df_valid['category'].isin(rare_classes), 'category'] = 'Altro'

    # Evidenziamo il peso dell'Active Learning
    if 'classification_confidence' in df_valid.columns:
        human_rev = (df_valid['classification_confidence'] == 'human_reviewed').sum()
        print(f"🧑‍🏫 Di cui revisionati umanamente (Active Learning): {human_rev}")

    # Prepariamo X (Features) e y (Target)
    # Combiniamo l'oggetto e il testo estratto per dare più contesto al TF-IDF
    X = df_valid['oggetto'].fillna('') + " " + df_valid['text_preview']
    y = df_valid['category']

    # Splittiamo in Training e Test Set per valutare le prestazioni
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Creazione della pipeline con ricerca a griglia per trovare i migliori iperparametri
    pipeline = make_pipeline(TfidfVectorizer(), RandomForestClassifier(random_state=42))

    # Definizione della griglia di iperparametri
    param_grid = {
        'tfidfvectorizer__max_features': [5000, 7500, 10000],
        'tfidfvectorizer__ngram_range': [(1, 2), (1, 3), (1, 4)],
        'tfidfvectorizer__max_df': [0.8, 0.85, 0.9],
        'tfidfvectorizer__min_df': [2, 3, 5],
        'randomforestclassifier__n_estimators': [100, 200, 300],
        'randomforestclassifier__max_depth': [10, 20, 30, None],
        'randomforestclassifier__min_samples_split': [2, 5, 10],
        'randomforestclassifier__min_samples_leaf': [1, 2, 4],
        'randomforestclassifier__class_weight': ['balanced', 'balanced_subsample', None]
    }

    print("🔍 Ottimizzazione degli iperparametri in corso...")
    grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='f1_macro', n_jobs=-1, verbose=1)
    grid_search.fit(X_train, y_train)

    print(f"✅ Migliori parametri trovati: {grid_search.best_params_}")

    # Otteniamo il miglior modello
    best_model = grid_search.best_estimator_

    print("\n🎯 Valutazione del modello ottimizzato sul Test Set:")
    y_pred = best_model.predict(X_test)
    accuracy = grid_search.score(X_test, y_test)
    precision, recall, f1, support = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro Precision: {precision:.4f}")
    print(f"Macro Recall: {recall:.4f}")
    print(f"Macro F1-Score: {f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    print("\n🚀 Riaddestramento massivo sull'intero dataset per la messa in produzione...")
    best_model.fit(X, y)

    print(f"💾 Salvataggio del modello ottimizzato in: {model_path}")
    joblib.dump(best_model, model_path)
    print("✅ Completato con successo! Il modello ML è ora aggiornato e pronto per analyze_albo.py.")

if __name__ == "__main__":
    main()