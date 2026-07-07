#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per analizzare le statistiche di classificazione prima e dopo
l'applicazione delle regole avanzate di classificazione.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
from collections import Counter

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(base_path):
    """Carica i dati dai file CSV principali."""
    base = Path(base_path)
    
    allegati_path = base / "allegati_parsed.csv"
    
    if not allegati_path.exists():
        raise FileNotFoundError(f"File allegati_parsed.csv non trovato in {base}")
    
    df = pd.read_csv(allegati_path)
    
    # Controlla se esiste la colonna text_preview nel dataframe principale
    if 'text_preview' not in df.columns:
        logger.warning("Colonna 'text_preview' non trovata nel file allegati_parsed.csv")
    
    return df

def calculate_basic_stats(df):
    """Calcola statistiche di base sui dati di classificazione."""
    total_docs = len(df)
    
    # Distribuzione della confidenza
    confidence_dist = df['classification_confidence'].value_counts() if 'classification_confidence' in df.columns else pd.Series([])
    confidence_pct = (confidence_dist / total_docs * 100) if len(confidence_dist) > 0 else pd.Series([])
    
    # Distribuzione delle categorie
    category_dist = df['category'].value_counts() if 'category' in df.columns else pd.Series([])
    category_pct = (category_dist / total_docs * 100) if len(category_dist) > 0 else pd.Series([])
    
    # Conteggio documenti ambigui
    ambiguous_count = len(df[df['classification_confidence'] == 'ambiguous']) if 'classification_confidence' in df.columns else 0
    
    return {
        'total_docs': total_docs,
        'confidence_distribution': confidence_dist,
        'confidence_percentages': confidence_pct,
        'category_distribution': category_dist,
        'category_percentages': category_pct,
        'ambiguous_count': ambiguous_count
    }

def apply_advanced_classification_rules(text_str, oggetto_str=""):
    """Applica le stesse regole avanzate di classificazione implementate nel sistema."""
    if pd.isna(text_str):
        text_str = ""
    
    if pd.isna(oggetto_str):
        oggetto_str = ""
        
    full_text = (oggetto_str + " " + text_str).lower()
    
    # Regole specifiche per distinguere tra categorie simili
    # Basate su pattern specifici trovati nei documenti reali
    if "determinazione" in full_text or "determina" in full_text:
        # Cerca termini specifici per la contabilità in ambito di determinazioni
        if any(term in full_text for term in ["impegno di spesa", "liquidazione", "fattura", "pagamento", "capitolo", "accertamento", "visto contabile"]):
            return "Contabilità"
        elif any(term in full_text for term in ["lavori pubblici", "progetto esecutivo", "manutenzione", "cantiere", "opera pubblica"]):
            return "Lavori Pubblici"
        elif any(term in full_text for term in ["personale", "assunzioni", "concorso", "selezione", "progressione"]):
            return "Personale"
    
    elif "delibera" in full_text:
        if any(term in full_text for term in ["approvazione", "regolamento", "modifica"]):
            return "Regolamenti"
        elif any(term in full_text for term in ["impegno di spesa", "variazione di bilancio", "riconoscimento debito"]):
            return "Contabilità"
    
    elif "ordinanza" in full_text:
        if any(term in full_text for term in ["ufficio", "responsabile", "organizzazione"]):
            return "Affari Generali"
    
    elif "pubblicazione" in full_text or "attestazione" in full_text:
        return "Pubblicazione e Trasparenza"
    
    elif any(term in full_text for term in ["contenzioso", "incarico legale", "patrocinio", "tribunale"]):
        return "Contenzioso"
    
    elif any(term in full_text for term in ["urbanistica", "piano di sviluppo", "permesso di costruire"]):
        return "Urbanistica"
    
    elif any(term in full_text for term in ["servizi sociali", "assistenza", "contributo economico"]):
        return "Servizi Sociali"
    
    elif any(term in full_text for term in ["cultura", "turismo", "manifestazione", "evento"]):
        return "Cultura e Turismo"
    
    elif any(term in full_text for term in ["ambiente", "ecologia", "rifiuti", "inquinamento"]):
        return "Ambiente"
    
    elif any(term in full_text for term in ["commercio", "suap", "attività produttive"]):
        return "Commercio"
    
    elif any(term in full_text for term in ["anagrafe", "stato civile", "elettorale"]):
        return "Servizi Demografici"
    
    # Se nessuna regola specifica si applica, ritorna None per lasciare decidere al modello ML
    return None

def simulate_rule_application(df):
    """Simula l'applicazione delle regole avanzate ai dati esistenti."""
    df_simulated = df.copy()
    
    # Solo se abbiamo colonne di testo disponibili
    text_col = 'text_preview' if 'text_preview' in df.columns else 'oggetto' if 'oggetto' in df.columns else None
    
    if text_col:
        logger.info("Applicazione simulata delle regole avanzate di classificazione...")
        
        # Applica le regole avanzate a tutti i documenti
        simulated_categories = []
        for idx, row in df.iterrows():
            rule_category = apply_advanced_classification_rules(
                str(row.get(text_col, "")),
                str(row.get('oggetto', ''))
            )
            simulated_categories.append(rule_category)
        
        df_simulated['category_with_rules'] = df_simulated['category'].copy()
        
        # Dove le regole avanzate forniscono una classificazione, aggiorna la categoria
        rule_applied_mask = pd.Series(simulated_categories).notna()
        df_simulated.loc[rule_applied_mask, 'category_with_rules'] = pd.Series(simulated_categories)[rule_applied_mask]
        
        # Aggiorna anche la confidenza dove applichiamo regole (le consideriamo ad alta confidenza)
        df_simulated.loc[rule_applied_mask, 'classification_confidence_with_rules'] = 'rule_based'
        # Mantieni la confidenza originale dove non applichiamo regole
        df_simulated.loc[~rule_applied_mask, 'classification_confidence_with_rules'] = df_simulated.loc[~rule_applied_mask, 'classification_confidence']
    else:
        logger.warning(f"Nessuna colonna di testo trovata in {df.columns}")
        df_simulated['category_with_rules'] = df_simulated['category'].copy()
        df_simulated['classification_confidence_with_rules'] = df_simulated['classification_confidence'].copy()
    
    return df_simulated

def compare_stats(original_df, modified_df):
    """Confronta le statistiche prima e dopo l'applicazione delle regole."""
    original_stats = calculate_basic_stats(original_df)
    modified_stats = calculate_basic_stats(modified_df)
    
    comparison = {}
    
    # Confronto distribuzione categorie
    comparison['original_categories'] = original_stats['category_distribution']
    comparison['modified_categories'] = modified_stats['category_distribution']
    comparison['original_category_percentages'] = original_stats['category_percentages']
    comparison['modified_category_percentages'] = modified_stats['category_percentages']
    
    # Confronto confidenza
    comparison['original_confidence'] = original_stats['confidence_distribution']
    comparison['modified_confidence'] = modified_stats['confidence_distribution']
    comparison['original_confidence_percentages'] = original_stats['confidence_percentages']
    comparison['modified_confidence_percentages'] = modified_stats['confidence_percentages']
    
    # Confronto documenti ambigui
    comparison['original_ambiguous'] = original_stats['ambiguous_count']
    comparison['modified_ambiguous'] = modified_stats['ambiguous_count']
    
    return comparison

def print_comparison(comparison):
    """Stampa il confronto delle statistiche in formato leggibile."""
    print("\n" + "="*80)
    print("CONFRONTO STATISTICHE DI CLASSIFICAZIONE")
    print("="*80)
    
    print(f"\n📊 DOCUMENTI TOTALI: {comparison['original_categories'].sum()}")
    
    print(f"\n🔍 CONFRONTO CONFIDENZA:")
    print(f"   Documenti 'ambiguous' prima: {comparison['original_ambiguous']} ({comparison['original_ambiguous']/comparison['original_categories'].sum()*100:.2f}%)")
    print(f"   Documenti 'ambiguous' dopo:  {comparison['modified_ambiguous']} ({comparison['modified_ambiguous']/comparison['original_categories'].sum()*100:.2f}%)")
    print(f"   RIDUZIONE: {comparison['original_ambiguous'] - comparison['modified_ambiguous']} documenti ({(comparison['original_ambiguous'] - comparison['modified_ambiguous'])/comparison['original_categories'].sum()*100:.2f}%)")
    
    print(f"\n📈 CONFRONTO CATEGORIE PRINCIPALI (prima/dopo):")
    # Ottieni le categorie principali (quelle con più documenti)
    top_original_cats = comparison['original_categories'].head(10)
    top_modified_cats = comparison['modified_categories'].head(10)
    
    all_cats = set(top_original_cats.index).union(set(top_modified_cats.index))
    all_cats = sorted(all_cats, key=lambda x: max(top_original_cats.get(x, 0), top_modified_cats.get(x, 0)), reverse=True)
    
    for cat in all_cats[:10]:  # Mostra solo le prime 10
        orig_count = comparison['original_categories'].get(cat, 0)
        mod_count = comparison['modified_categories'].get(cat, 0)
        orig_pct = comparison['original_category_percentages'].get(cat, 0)
        mod_pct = comparison['modified_category_percentages'].get(cat, 0)
        
        print(f"   {cat:<25} {orig_count:>6} ({orig_pct:>5.2f}%) → {mod_count:>6} ({mod_pct:>5.2f}%)")

def save_detailed_comparison(original_df, modified_df, output_dir):
    """Salva un report dettagliato delle differenze."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Crea un DataFrame con le differenze
    diff_data = []
    for idx in original_df.index:
        orig_cat = original_df.loc[idx, 'category']
        orig_conf = original_df.loc[idx, 'classification_confidence'] if 'classification_confidence' in original_df.columns else 'unknown'
        mod_cat = modified_df.loc[idx, 'category_with_rules']
        mod_conf = modified_df.loc[idx, 'classification_confidence_with_rules']
        
        # Determina se la classificazione è stata modificata
        changed = (orig_cat != mod_cat) or (orig_conf != mod_conf)
        
        diff_data.append({
            'pdf_name': original_df.loc[idx, 'pdf_name'],
            'original_category': orig_cat,
            'original_confidence': orig_conf,
            'modified_category': mod_cat,
            'modified_confidence': mod_conf,
            'changed': changed
        })
    
    diff_df = pd.DataFrame(diff_data)
    
    # Salva il report differenze
    diff_df.to_csv(output_path / "classification_changes.csv", index=False)
    
    # Calcola statistiche aggiuntive
    changes_summary = {
        'total_documents': len(diff_df),
        'documents_changed': len(diff_df[diff_df['changed']]),
        'change_percentage': len(diff_df[diff_df['changed']]) / len(diff_df) * 100,
        'categories_changed': len(diff_df[(diff_df['original_category'] != diff_df['modified_category']) & (diff_df['original_category'].notna())]),
        'confidence_improved': len(diff_df[(diff_df['original_confidence'] == 'ambiguous') & (diff_df['modified_confidence'] != 'ambiguous')])
    }
    
    # Salva il sommario
    summary_df = pd.DataFrame([changes_summary])
    summary_df.to_csv(output_path / "changes_summary.csv", index=False)
    
    print(f"\n📁 Report dettagliato salvato in: {output_path}")
    print(f"   - classification_changes.csv: tutte le modifiche individuali")
    print(f"   - changes_summary.csv: sommario delle modifiche")

def main():
    parser = argparse.ArgumentParser(description="Analizza le statistiche di classificazione prima e dopo l'applicazione delle regole avanzate")
    parser.add_argument("--base", default="albo_download", help="Directory base contenente i file CSV")
    parser.add_argument("--output", default="report/stats_analysis", help="Directory per i file di output")
    
    args = parser.parse_args()
    
    try:
        # Carica i dati
        logger.info(f"Caricamento dati da: {args.base}")
        df = load_data(args.base)
        
        print(f"✅ Dati caricati: {len(df)} documenti totali")
        
        # Calcola statistiche originali
        original_stats = calculate_basic_stats(df)
        print(f"📊 Distribuzione originale categorie (prime 10):")
        for cat, count in original_stats['category_distribution'].head(10).items():
            pct = original_stats['category_percentages'].get(cat, 0)
            print(f"   {cat}: {count} ({pct:.2f}%)")
        
        # Simula l'applicazione delle regole
        df_with_rules = simulate_rule_application(df)
        
        # Confronta le statistiche
        comparison = compare_stats(df, df_with_rules)
        
        # Stampa il confronto
        print_comparison(comparison)
        
        # Salva il report dettagliato
        save_detailed_comparison(df, df_with_rules, args.output)
        
        print(f"\n✅ Analisi completata con successo!")
        
    except Exception as e:
        logger.error(f"Errore durante l'analisi: {e}")
        raise

if __name__ == "__main__":
    main()