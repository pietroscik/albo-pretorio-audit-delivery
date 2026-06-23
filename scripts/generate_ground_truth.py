#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per generare ground_truth.json, con supporto opzionale a LLM per l'annotazione.

Requisiti:
- Accesso alle librerie UserLibrary (394 documenti totali)
- Python 3.8+

Output:
- data/ground_truth.json (Documenti casuali per validazione iniziale)

Uso:
    python scripts/generate_ground_truth.py --sample 50
    python scripts/generate_ground_truth.py --sample 50 --use-llm
    python scripts/generate_ground_truth.py --all

ISTRUZIONI:
1. Se si usa --use-llm, assicurarsi che GOOGLE_API_KEY o MISTRAL_API_KEY siano nel file .env
2. Apri data/ground_truth.json e completa manualmente:
   - event_type (OBBLIGATORIO)
   - actors (OBBLIGATORIO)
   - Verifica: doc_type, cig, cup, economic_value
   - Imposta is_validated: true
4. Esegui: python scripts/validate_ground_truth.py
"""

import argparse
import json
import random
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os
import sys

from dotenv import load_dotenv
load_dotenv()

# Aggiungi la root del progetto al sys.path per importare i moduli
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    from langchain_mistralai import ChatMistralAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ============================================================================
# CONFIGURAZIONE E FUNZIONI LLM
# ============================================================================

def configure_llm():
    """Configura e restituisce un client LLM (Gemini o Mistral)."""
    if not LLM_AVAILABLE:
        return None, None

    google_api_key = os.getenv("GOOGLE_API_KEY")
    mistral_api_key = os.getenv("MISTRAL_API_KEY")

    if google_api_key:
        try:
            genai.configure(api_key=google_api_key)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest",
                safety_settings=safety_settings,
                system_instruction="""
                Sei un esperto in documenti amministrativi della Pubblica Amministrazione italiana.
                Il tuo compito è estrarre informazioni strutturate da documenti comunali (Determine, Delibere, Bandi, ecc.).
                Rispondi SOLO in formato JSON, senza spiegazioni o testata.
                Se non sei sicuro di un campo, lascialo come null.
                """
            )
            print("✅ LLM Gemini configurato.")
            return model, "gemini"
        except Exception as e:
            print(f"⚠️  Errore configurazione Gemini: {e}")

    if mistral_api_key:
        try:
            model = ChatMistralAI(model="mistral-large-latest", temperature=0, api_key=mistral_api_key)
            print("✅ LLM Mistral configurato.")
            return model, "mistral"
        except Exception as e:
            print(f"⚠️  Errore configurazione Mistral: {e}")

    print("⚠️  Nessuna chiave API (GOOGLE_API_KEY o MISTRAL_API_KEY) trovata. LLM non attivo.")
    return None, None


# ============================================================================
# FUNZIONI DI ESTRAZIONE
# ============================================================================


def extract_importo(text: str) -> Optional[float]:
    """Estrae il primo importo in euro dal testo."""
    patterns = [
        r'€\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
        r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)\s*euro',
        r'totale[\s:]*€?\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
        r'importo[\s:]*€?\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
        r'per\s+(?:un\s+)?importo\s+(?:complessivo\s+)?di\s+€?\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
        r'si\s+(?:liquidano|impegnano|pagano)\s+€?\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            importo_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return round(float(importo_str), 2)
            except ValueError:
                continue
    return None


def extract_all_importi(text: str) -> List[float]:
    """Estrae TUTTI gli importi dal testo."""
    # This improved pattern looks for numbers that are more likely to be currency:
    # - Optionally starts with €
    # - Contains a comma or a period as a decimal separator, followed by 2 digits.
    # - Or is a whole number followed by ",00".
    # - It avoids matching simple years or protocol numbers like '2024' or '123'.
    pattern = r'€?\s*(\d{1,3}(?:[.,]\d{3})*,\d{2}|\d+\.\d{2,})'
    matches = re.findall(pattern, text)
    importi = []
    for m in matches:
        try:
            # Normalize the string to a float-compatible format ('.' for decimal)
            s = m.replace('.', '').replace(',', '.')
            importo = float(s)
            # A reasonable filter to avoid matching irrelevant large numbers
            if 0 < importo < 50_000_000:
                importi.append(importo)
        except ValueError:
            continue
    return importi


def extract_date_from_text(text: str) -> Optional[str]:
    """Estrae la data dal testo."""
    patterns = [
        r'(\d{1,2})[\/_\-](\d{1,2})[\/_\-](\d{2,4})',
        r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
    ]
    
    month_map = {
        'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
        'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
        'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
    }
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if pattern == patterns[0]:
                day = match.group(1).zfill(2)
                month = match.group(2).zfill(2)
                year = match.group(3)
                if len(year) == 2:
                    year = f"20{year}"
                return f"{year}-{month}-{day}"
            else:
                day = match.group(1).zfill(2)
                month = month_map.get(match.group(2).lower())
                year = match.group(3)
                if month:
                    return f"{year}-{month}-{day}"
    return None


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Estrae la data dal nome del file."""
    match = re.search(r'(\d{1,2})[\/_\-](\d{1,2})[\/_\-](\d{2,4})', filename)
    if match:
        day = match.group(1).zfill(2)
        month = match.group(2).zfill(2)
        year = match.group(3)
        if len(year) == 2:
            year = f"20{year}"
        return f"{year}-{month}-{day}"
    return None


def extract_document_number(text: str, filename: str) -> Optional[str]:
    """Estrae il numero del documento."""
    patterns = [
        (r'n\.?\s*(\d+)\s*/\s*(\d{4})', lambda m: f"{m.group(1)}/{m.group(2)}"),
        (r'n\.?\s*(\d+)\s*del\s*\d{1,2}[\/_\-]\d{1,2}[\/_\-](\d{2,4})', lambda m: f"{m.group(1)}/{m.group(2)}"),
        (r'(determinazione|delibera|ordinanza|avviso|bando)\s*n\.?\s*(\d+)', lambda m: m.group(2)),
        (r'num\.?\s*(\d+)', lambda m: m.group(1)),
    ]
    
    for pattern, formatter in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return formatter(match)
    
    match = re.search(r'(\d+)[\/_\-](\d{4})', filename)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    
    match = re.search(r'(determinazione|delibera|ordinanza)_(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(2)
    
    return None


def infer_doc_type(filename: str, text: str) -> str:
    """Inferisce il tipo di documento."""
    filename_lower = filename.lower()
    text_lower = text.lower()
    
    if any(kw in filename_lower for kw in ['determinazione', 'determina']):
        return "DETERMINA"
    if any(kw in filename_lower for kw in ['delibera']):
        return "DELIBERA"
    if any(kw in filename_lower for kw in ['bando']):
        return "BANDO"
    if any(kw in filename_lower for kw in ['ordinanza']):
        return "ORDINANZA"
    if any(kw in filename_lower for kw in ['avviso']):
        return "AVVISO"
    if any(kw in filename_lower for kw in ['atto']):
        return "ATTO"
    if any(kw in filename_lower for kw in ['liquidazione', 'impegno', 'mandato', 'pagamento']):
        return "NUMERARIA"
    if any(kw in text_lower for kw in ['esito', 'aggiudicazione', 'verbale']):
        return "ESITO"
    if any(kw in text_lower for kw in ['contratto', 'convenzione']):
        return "CONTRATTO"
    
    return "UNKNOWN"


def extract_cig(text: str) -> Optional[str]:
    """Estrae il CIG."""
    match = re.search(r'CIG[\s:\-]*([A-Z0-9]{10,15})', text, re.IGNORECASE)
    return match.group(1) if match else None


def extract_cup(text: str) -> Optional[str]:
    """Estrae il CUP."""
    match = re.search(r'CUP[\s:\-]*([A-Z0-9]{15})', text, re.IGNORECASE)
    return match.group(1) if match else None


# ============================================================================
# FUNZIONE PRINCIPALE
# ============================================================================


def create_ground_truth_entry_rules(doc: Dict) -> Dict:
    """Crea un entry del ground truth."""
    text = doc.get('text', '')
    filename = doc.get('pdf_name', '')
    
    doc_type = infer_doc_type(filename, text)
    cig = extract_cig(text) or doc.get('cig')
    cup = extract_cup(text) or doc.get('cup')
    importo = extract_importo(text)
    all_importi = extract_all_importi(text)
    date = extract_date_from_text(text) or extract_date_from_filename(filename)
    doc_number = extract_document_number(text, filename)
    
    if all_importi and len(all_importi) > 1:
        totale_match = re.search(r'(?:importo\s+complessivo|totale)[\s:]*€?\s*(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)', text, re.IGNORECASE)
        if totale_match:
            totale_str = totale_match.group(1).replace('.', '').replace(',', '.')
            try:
                importo = round(float(totale_str), 2)
            except:
                pass
        else:
            importo = round(sum(all_importi), 2)
    
    return {
        "document_id": doc.get('text_sha256', ''),
        "library": doc.get('category', 'UNKNOWN'),
        "library_id": "",
        "document_name": filename,
        "text": text[:3000],  # Limitiamo la lunghezza del testo nel JSON per comodità visiva
        "full_text_available": False,
        "doc_type": doc_type,
        "event_type": None,
        "cig": cig,
        "cup": cup,
        "economic_value": importo,
        "all_importi": all_importi,
        "currency": "EUR",
        "date": date,
        "document_number": doc_number,
        "actors": [],
        "confidence": 1.0,
        "notes": "",
        "is_validated": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }


def main():
    parser = argparse.ArgumentParser(description='Genera ground_truth.json dal corpus locale, con supporto LLM.')
    parser.add_argument('--ente', type=str, default='avella', help='Nome dell\'ente (es. avella, tufino).')
    parser.add_argument('--base', type=str, default=None, help='Cartella base dei dati. Se non specificato, usa data/{ente}/albo_download')
    parser.add_argument('--sample', type=int, default=50, help='Numero documenti casuali')
    parser.add_argument('--all', action='store_true', help='Tutti i 394 documenti')
    parser.add_argument('--output', type=str, default='data/ground_truth.json',
                        help='Percorso file output')
    parser.add_argument('--use-llm', action='store_true', help='Usa LLM (Gemini/Mistral) per l\'annotazione automatica.')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("GENERAZIONE GROUND TRUTH DATASET")
    print("=" * 70)
    
    # Configura LLM se richiesto
    model, model_type = configure_llm() if args.use_llm else (None, None)
    use_llm = model is not None

    if args.base:
        base_dir = Path(args.base)
    else:
        base_dir = Path(f"data/{args.ente}/albo_download")

    corpus_path = base_dir / "documenti_corpus.jsonl"
    if not corpus_path.exists():
        print(f"❌ Errore: File {corpus_path} non trovato. Assicurati che il percorso sia corretto.")
        return
        
    all_docs = []
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_docs.append(json.loads(line))
                
    if not args.all and len(all_docs) > args.sample:
        docs_to_process = random.sample(all_docs, args.sample)
    else:
        docs_to_process = all_docs
    
    ground_truth = []
    for i, doc in enumerate(docs_to_process, 1):
        print(f"\r📄 Elaborazione documento {i}/{len(docs_to_process)}...", end="")

        text = doc.get('text', '')
        filename = doc.get('pdf_name', '')
        
        entry_data = {}
        if use_llm:
            prompt = f"""
            Analizza il seguente documento amministrativo e estrai le informazioni in formato JSON.

            TESTO:
            {text[:8000]}

            NOME FILE: {filename}

            ESTRARRE I SEGUENTI CAMPI (in JSON):
            - event_type: uno di [IMPEGNO, LIQUIDAZIONE, PAGAMENTO, RETTIFICA, AFFIDAMENTO, AGGIUDICAZIONE, PROROGA, ANNULLAMENTO, REVOCA, VARIAZIONE, NOMINA, PROGRESSIONE, SELEZIONE, CONCORSO, PIANIFICAZIONE, REGOLAMENTAZIONE, UNKNOWN]
            - doc_type: uno di [DETERMINA, DELIBERA, BANDO, AVVISO, ORDINANZA, ATTO, NUMERARIA, ESITO, CONTRATTO, UNKNOWN]
            - actors: array di oggetti {{ "name": "...", "actor_type": "..." }}, dove actor_type è uno di [RUP, DIRIGENTE, SINDACO, GIUNTA, CONSIGLIO, BENEFICIARIO, OPERATORE_ECONOMICO, FUNZIONARIO, UNKNOWN]
            - economic_value: numero (float) o null
            - cig: stringa o null
            - cup: stringa o null
            - date: stringa nel formato YYYY-MM-DD o null
            - document_number: stringa o null

            RISPOSTA (SOLO JSON):
            """
            try:
                if model_type == "gemini":
                    response = model.generate_content(prompt)
                    result_text = response.text
                else: # mistral
                    response = model.invoke(prompt)
                    result_text = response.content

                result_text = result_text.replace("```json", "").replace("```", "").strip()
                entry_data = json.loads(result_text)
            except Exception as e:
                print(f"\n⚠️  Errore LLM per {filename}: {e}. Fallback a regole.")
                entry_data = {}

        # Se LLM fallisce o non è usato, usiamo le regole
        if not entry_data:
            rules_entry = create_ground_truth_entry_rules(doc)
            # Mappiamo i campi per coerenza
            entry_data = {
                "doc_type": rules_entry.get("doc_type"),
                "event_type": None,
                "actors": [],
                "economic_value": rules_entry.get("economic_value"),
                "cig": rules_entry.get("cig"),
                "cup": rules_entry.get("cup"),
                "date": rules_entry.get("date"),
                "document_number": rules_entry.get("document_number"),
            }

        # Unifichiamo l'output
        final_entry = create_ground_truth_entry_rules(doc)
        final_entry.update(entry_data) # Sovrascriviamo i campi con l'output dell'LLM se presente
        final_entry["is_validated"] = False
        final_entry["extracted_with_llm"] = use_llm
        ground_truth.append(final_entry)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n✅ Generato {output_path} con {len(ground_truth)} documenti")
    print("\n📝 Prossimi passi:")
    print("   1. Apri data/ground_truth.json")
    print("   2. Completa manualmente:")
    print("      - event_type (OBBLIGATORIO)")
    print("      - actors (OBBLIGATORIO)")
    print("      - Verifica gli altri campi")
    print("      - Imposta is_validated: true")
    print("   3. Esegui: python scripts/validate_ground_truth.py")


if __name__ == '__main__':
    main()