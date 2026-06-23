import argparse
import pandas as pd
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def main():
    parser = argparse.ArgumentParser(description="Riaddestra il modello Random Forest con i dati revisionati.")
    parser.add_argument("--base", default="albo_download", help="Cartella base dei dati.")
    args = parser.parse_args()

    base = Path(args.base)
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

    print("🧠 Creazione della pipeline NLP (TF-IDF + Random Forest)...")
    pipeline = make_pipeline(
        TfidfVectorizer(max_features=5000, ngram_range=(1, 2)),
        RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    )

    print("⚙️ Addestramento del modello in corso (Valutazione)...")
    pipeline.fit(X_train, y_train)

    print("\n🎯 Valutazione del modello sul Test Set:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred, zero_division=0))

    print("\n🚀 Riaddestramento massivo sull'intero dataset per la messa in produzione...")
    pipeline.fit(X, y)

    print(f"💾 Salvataggio del modello in: {model_path}")
    joblib.dump(pipeline, model_path)
    print("✅ Completato con successo! Il modello ML è ora aggiornato e pronto per analyze_albo.py.")

if __name__ == "__main__":
    main()