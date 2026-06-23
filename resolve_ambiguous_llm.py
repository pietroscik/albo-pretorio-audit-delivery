import pandas as pd
try:
    import google.generativeai as genai
except ImportError:
    genai = None
import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from llm_factory import get_llm_client

def ask_llm_to_refine(text, current_data, max_retries: int = 5):
    """Chiede a un LLM (Gemini o Mistral) di rifinire i dati estratti basandosi sul testo completo."""
    prompt = f"""
    Sei un auditor esperto della Pubblica Amministrazione italiana. 
    Analizza il testo dell'atto e correggi/integra i metadati forniti.
    
    METADATI ATTUALI (Potrebbero contenere errori o 'NON IDENTIFICATO'):
    - RUP: {current_data.get('responsabile')}
    - Beneficiario: {current_data.get('beneficiario')}
    - Categoria: {current_data.get('category')}
    
    ISTRUZIONI CRITICHE:
    1. Se il RUP attuale è una formula giuridica (es. "HA ADOTTATO", "AREA FINANZIARIA"), trova il NOME E COGNOME reale del firmatario.
    2. Se il Beneficiario è "NON IDENTIFICATO", cercalo nel testo (cerca nomi di ditte, professionisti o P.IVA).
    3. Restituisci SOLO un JSON valido.
    
    {{"responsabile": "NOME COGNOME", "beneficiario": "NOME DITTA O PERSONA", "category": "CATEGORIA CORRETTA", "cig": "CIG SE TROVATO"}}
    
    TESTO ATTO:
    {text[:12000]}
    """
    
    # get_llm_client gestisce internamente la rotazione dei modelli definiti in config.py
    # (ora include anche Mistral)
    return get_llm_client(prompt)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="data/baiano/albo_download", help="Percorso base dei dati dell'ente")
    parser.add_argument("--limit", type=int, default=30, help="Limite atti da processare in questo run per risparmiare quota")
    args = parser.parse_args()

    base_path = Path(args.base)
    csv_path = base_path / "allegati_parsed.csv"
    
    if not csv_path.exists():
        print(f"ERRORE: File {csv_path} non trovato.")
        return

    print(f"🚀 Avvio arricchimento intelligente per: {args.base}")
    df = pd.read_csv(csv_path)

    # Identifichiamo i casi critici: RUP errati o Beneficiari mancanti
    conf_numeric = pd.to_numeric(df['classification_confidence'], errors='coerce').fillna(0.99)
    
    # Filtriamo quelli non ancora processati da Gemini per evitare loop o spreco di quota
    if 'extraction_method' not in df.columns:
        df['extraction_method'] = "original"
        
    mask_critici = (
        (~df['extraction_method'].str.contains("GEMINI_REFINED", na=False)) & (
            (df['responsabile'].str.contains("HA ADOTTATO|FINANZIARIA|DELIBERA|DETERMINA|SETTORE", case=False, na=True)) |
            (df['beneficiario'] == "NON IDENTIFICATO") |
            (conf_numeric < 0.6)
        )
    )
    
    target_df = df[mask_critici].head(args.limit)
    total_to_process = len(target_df)
    print(f"[*] Trovati {len(df[mask_critici])} atti critici totali. Ne processerò {total_to_process} in questo batch.")

    if total_to_process == 0:
        print("✅ Tutti gli atti sembrano già ottimizzati o non ci sono casi critici.")
        return

    count = 0
    try:
        for idx, row in target_df.iterrows():
            # Rimuoviamo .pdf per cercare il .txt
            filename_base = row['pdf_name'].replace('.pdf', '')
            text_path = base_path / "texts" / f"{filename_base}.txt"
            
            if not text_path.exists():
                print(f"  [MISSING] Testo non trovato: {text_path.name}")
                continue
            
            print(f"[{count+1}/{total_to_process}] Analisi: {row['pdf_name']}...")
            text = text_path.read_text(encoding='utf-8', errors='ignore')
            
            refined = ask_llm_to_refine(text, row.to_dict())
            
            if refined:
                if refined.get('responsabile'): 
                    df.at[idx, 'responsabile'] = refined['responsabile'].upper()
                    df.at[idx, 'rup_nome'] = refined['responsabile'].upper()
                if refined.get('beneficiario'): 
                    df.at[idx, 'beneficiario'] = refined['beneficiario'].upper()
                if refined.get('category'): 
                    df.at[idx, 'category'] = refined['category']
                    df.at[idx, 'classification_confidence'] = 0.95 
                if refined.get('cig') and pd.isna(df.at[idx, 'cig']):
                    df.at[idx, 'cig'] = refined['cig'].upper()
                
                df.at[idx, 'extraction_method'] = str(df.at[idx, 'extraction_method']) + "+GEMINI_REFINED"
                count += 1
                
                # Checkpoint ogni 1 successo per non perdere lavoro in caso di crash/quota esaurita
                df.to_csv(csv_path, index=False)
                print(f"    [✓] Salvataggio progressivo effettuato.")
            else:
                print(f"    [!] Impossibile rifinire l'atto (Quota esaurita su tutti i modelli o errore).")
                # Se abbiamo esaurito tutti i modelli, forse è meglio fermarsi
                break

    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Salvataggio finale...")
    
    print(f"\n✅ Sessione conclusa. Aggiornati {count} atti.")

if __name__ == "__main__":
    main()
