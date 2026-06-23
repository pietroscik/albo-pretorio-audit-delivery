
import argparse
import pandas as pd
import re
from pathlib import Path
from rapidfuzz import process, fuzz

def clean_text(text):
    if pd.isna(text): return ""
    # Rimuove caratteri speciali e normalizza spazi
    text = re.sub(r'[^\w\s]', ' ', str(text).lower())
    return " ".join(text.split())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    
    base = Path(args.base)
    meta_path = base / "albo_metadati.csv"
    parsed_path = base / "allegati_parsed.csv"
    
    if not meta_path.exists() or not parsed_path.exists():
        print("File non trovati.")
        return

    df_meta = pd.read_csv(meta_path)
    df_parsed = pd.read_csv(parsed_path)

    # Filtra solo i documenti "nobili" per il mapping delle tipologie
    # Evitiamo di mappare "VistoContabile" come tipologia principale se c'è altro
    priority = {
        'Determinazione': 100,
        'Delibera': 100,
        'Ordinanza': 100,
        'Decreto': 100,
        'Bando': 50,
        'Avviso': 50,
        'unknown': 10,
        'VistoContabile': 5,
        'AttestazionePubblicazione': 1
    }

    # Prepariamo i dati per il fuzzy matching
    # Usiamo l'oggetto dell'atto come chiave semantica
    print("Inizio matching semantico (Oggetto)...")
    
    # Crea un set univoco di oggetti dagli allegati parsed (dove abbiamo la tipologia)
    # Raggruppiamo per oggetto pulito e prendiamo la tipologia migliore
    df_parsed['oggetto_clean'] = df_parsed['oggetto'].apply(clean_text)
    
    mapping_data = []
    for obj, group in df_parsed[df_parsed['oggetto_clean'] != ""].groupby('oggetto_clean'):
        best_type = max(group['doc_type'].tolist(), key=lambda x: priority.get(x, 0))
        mapping_data.append({'oggetto_clean': obj, 'best_type': best_type})
    
    df_mapping = pd.DataFrame(mapping_data)
    choices = df_mapping['oggetto_clean'].tolist()
    
    count_updated = 0
    df_meta['oggetto_clean'] = df_meta['oggetto'].apply(clean_text)
    
    for idx, row in df_meta.iterrows():
        # Se la tipologia manca o è un numero (ID atto erroneamente messo in tipologia)
        curr_type = str(row['tipologia']).strip()
        if pd.isna(row['tipologia']) or curr_type.isdigit() or curr_type.lower() == 'nan':
            target_obj = row['oggetto_clean']
            if not target_obj: continue
            
            # Trova il match migliore
            match = process.extractOne(target_obj, choices, scorer=fuzz.token_set_ratio)
            
            if match and match[1] > 85: # Soglia di confidenza 85%
                matched_obj = match[0]
                new_type = df_mapping[df_mapping['oggetto_clean'] == matched_obj]['best_type'].values[0]
                df_meta.at[idx, 'tipologia'] = new_type
                count_updated += 1

    print(f"Tipologie aggiornate tramite matching semantico: {count_updated}")
    
    # Pulizia e salvataggio
    df_meta.drop(columns=['oggetto_clean'], inplace=True)
    df_meta.to_csv(meta_path, index=False)
    print(f"File {meta_path} aggiornato con successo.")

if __name__ == "__main__":
    main()
