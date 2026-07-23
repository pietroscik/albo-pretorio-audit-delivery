#!/usr/bin/env python3
"""
Script per verificare l'efficacia delle correzioni ai problemi di estrazione testo
sui dati reali dell'albo pretorio.
"""

import pandas as pd
import hashlib
from pathlib import Path
from collections import Counter

def analyze_parsed_documents():
    """Analizza il file allegati_parsed.csv per verificare le correzioni"""
    print("Analisi del file allegati_parsed.csv per verificare le correzioni...")
    
    try:
        df = pd.read_csv('data/baiano/albo_download/allegati_parsed.csv')
    except FileNotFoundError:
        print("File allegati_parsed.csv non trovato. Eseguire prima l'analisi.")
        return
    
    print(f"Numero totale di record: {len(df)}")
    
    # Controlliamo se i nuovi campi sono presenti
    if 'is_problematic_file' in df.columns and 'problematic_reason' in df.columns:
        problematic_docs = df[df['is_problematic_file'] == True]
        print(f"Documenti identificati come problematici: {len(problematic_docs)}")
        
        if len(problematic_docs) > 0:
            print("Cause principali dei file problematici:")
            reason_counts = problematic_docs['problematic_reason'].value_counts()
            for reason, count in reason_counts.items():
                print(f"  - {reason}: {count} documenti")
    else:
        print("I nuovi campi non sono ancora presenti nel file CSV esistente.")
        print("Questo è normale se il file è stato generato prima delle modifiche.")
    
    # Analizziamo gli hash per vedere se ci sono ancora duplicati anomali
    if 'text_sha256' in df.columns:
        hash_counts = df['text_sha256'].value_counts()
        exact_duplicates = sum(1 for count in hash_counts if count > 1)
        print(f"Numero di hash con duplicati esatti: {exact_duplicates}")
        
        if exact_duplicates > 0:
            print("Esempi di hash duplicati:")
            duplicate_hashes = hash_counts[hash_counts > 1].head(5)
            for hash_val, count in duplicate_hashes.items():
                print(f"  - {hash_val[:16]}... apparizioni: {count}")
    
    # Controlliamo se ci sono hash che sembrano essere della stringa vuota
    empty_hash = hashlib.sha256(b"").hexdigest()
    empty_hash_matches = df[df['text_sha256'] == empty_hash] if 'text_sha256' in df.columns else pd.DataFrame()
    
    print(f"Documenti con hash della stringa vuota: {len(empty_hash_matches)}")
    
    # Se ci sono ancora hash della stringa vuota, potrebbe indicare file che non sono stati 
    # ancora elaborati con le nuove correzioni
    if len(empty_hash_matches) > 0:
        print("Attenzione: Ci sono ancora documenti con l'hash della stringa vuota,")
        print("il che indica che potrebbero non essere stati elaborati con le nuove correzioni.")
    
    print("\nRiepilogo:")
    print(f"- Totale documenti: {len(df)}")
    if 'is_problematic_file' in df.columns:
        print(f"- Documenti problematici: {len(problematic_docs)} ({len(problematic_docs)/len(df)*100:.1f}%)")
    print(f"- Hash duplicati esatti: {exact_duplicates}")
    print(f"- Documenti con hash stringa vuota: {len(empty_hash_matches)}")

def compare_with_pdf_files():
    """Confronta i dati nel CSV con i file PDF effettivi per verificare la copertura"""
    pdf_dir = Path('data/baiano/albo_download/pdf')
    
    if not pdf_dir.exists():
        print("Directory PDF non trovata.")
        return
    
    pdf_files = list(pdf_dir.glob('*.pdf')) + list(pdf_dir.glob('*.PDF'))
    print(f"\nFile PDF trovati: {len(pdf_files)}")
    
    try:
        df = pd.read_csv('data/baiano/albo_download/allegati_parsed.csv')
        csv_files = set(df['pdf_name']) if 'pdf_name' in df.columns else set()
        
        print(f"File nel CSV: {len(csv_files)}")
        
        # Troviamo file PDF che non sono stati elaborati
        pdf_names = {f.name for f in pdf_files}
        not_processed = pdf_names - csv_files
        print(f"File PDF non elaborati: {len(not_processed)}")
        
        if len(not_processed) > 0:
            print("Esempi di file PDF non elaborati:")
            for f in list(not_processed)[:10]:
                print(f"  - {f}")
                
    except FileNotFoundError:
        print("File allegati_parsed.csv non trovato per il confronto.")

if __name__ == "__main__":
    print("Verifica dell'efficacia delle correzioni ai problemi di estrazione testo\n")
    
    analyze_parsed_documents()
    compare_with_pdf_files()
    
    print("\nPer verificare completamente l'efficacia delle correzioni, è necessario")
    print("rieseguire il processo di analisi con le nuove modifiche:")
    print("python -m delibere_comunali.parsing.analyze_albo --base data/baiano/albo_download --ente baiano --force")