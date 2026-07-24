import argparse
import pandas as pd
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import classification_report, precision_recall_fscore_support
from scipy.stats import randint, uniform
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
    # Check if the file is empty before attempting to read it
    if csv_path.stat().st_size == 0:
        print(f"⚠️  File {csv_path} è vuoto, impossibile addestrare il modello")
        return
    
    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        print(f"⚠️  File {csv_path} non contiene colonne valide, impossibile addestrare il modello")
        return

    # Check if required columns exist before trying to filter
    required_columns = ['category', 'text_preview']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"⚠️  Colonne mancanti nel dataset: {missing_columns}, impossibile addestrare il modello")
        return

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

    # Creazione della pipeline con ricerca randomizzata per trovare i migliori iperparametri
    pipeline = make_pipeline(TfidfVectorizer(), RandomForestClassifier(random_state=42))

    # Definizione dello spazio di ricerca per RandomizedSearchCV
    param_distributions = {
        'tfidfvectorizer__max_features': randint(5000, 10000),
        'tfidfvectorizer__ngram_range': [(1, 2), (1, 3), (1, 4)],
        'tfidfvectorizer__max_df': uniform(0.80, 0.10),  # Da 0.80 a 0.90
        'tfidfvectorizer__min_df': randint(2, 6),
        'randomforestclassifier__n_estimators': randint(100, 301),
        'randomforestclassifier__max_depth': [10, 20, 30, None],
        'randomforestclassifier__min_samples_split': randint(2, 11),
        'randomforestclassifier__min_samples_leaf': randint(1, 5),
        'randomforestclassifier__class_weight': ['balanced', 'balanced_subsample', None]
    }

    print("🔍 Ottimizzazione degli iperparametri in corso (RandomizedSearchCV)...")
    print(f"📊 Numero di combinazioni da provare: 200")
    randomized_search = RandomizedSearchCV(
        pipeline, 
        param_distributions, 
        n_iter=200,  # Numero ridotto di combinazioni da provare
        cv=3, 
        scoring='f1_macro', 
        n_jobs=2,  # Ridotto il numero di job paralleli per evitare problemi di memoria
        verbose=1,
        random_state=42
    )
    randomized_search.fit(X_train, y_train)

    print(f"✅ Migliori parametri trovati: {randomized_search.best_params_}")

    # Otteniamo il miglior modello
    best_model = randomized_search.best_estimator_

    print("\n🎯 Valutazione del modello ottimizzato sul Test Set:")
    y_pred = best_model.predict(X_test)
    accuracy = randomized_search.score(X_test, y_test)
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