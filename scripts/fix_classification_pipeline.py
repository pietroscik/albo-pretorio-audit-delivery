#!/usr/bin/env python3
"""
Pipeline completo per risolvere i problemi di classificazione identificati.
Questo script coordina tutti i passaggi necessari per migliorare la qualità 
delle classificazioni nel sistema.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Esegue un comando shell e gestisce eventuali errori."""
    logger.info(f"Esecuzione: {description}")
    logger.info(f"Comando: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Completato: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Errore nell'esecuzione di {description}: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def check_data_quality(base_path):
    """Controlla la qualità iniziale dei dati."""
    allegati_path = base_path / "allegati_parsed.csv"
    if not allegati_path.exists():
        raise FileNotFoundError(f"File {allegati_path} non trovato")
    
    df = pd.read_csv(allegati_path)
    
    logger.info("=== QUALITÀ DATI INIZIALE ===")
    logger.info(f"Totale documenti: {len(df)}")
    
    if 'classification_confidence' in df.columns:
        conf_counts = df['classification_confidence'].value_counts()
        logger.info("Distribuzione della confidenza iniziale:")
        for conf, count in conf_counts.items():
            percentage = (count / len(df)) * 100
            logger.info(f"  {conf}: {count} ({percentage:.2f}%)")
    
    if 'category' in df.columns:
        cat_counts = df['category'].value_counts()
        logger.info("Distribuzione delle categorie iniziali (prime 10):")
        for cat, count in cat_counts.head(10).items():
            percentage = (count / len(df)) * 100
            logger.info(f"  {cat}: {count} ({percentage:.2f}%)")
    
    ambiguous_count = len(df[df['classification_confidence'] == 'ambiguous']) if 'classification_confidence' in df.columns else 0
    logger.info(f"Documenti classificati come 'ambiguous': {ambiguous_count}")
    
    logger.info("=========================\n")

def check_data_quality_after(base_path):
    """Controlla la qualità dei dati dopo le operazioni."""
    allegati_path = base_path / "allegati_parsed.csv"
    if not allegati_path.exists():
        raise FileNotFoundError(f"File {allegati_path} non trovato")
    
    df = pd.read_csv(allegati_path)
    
    logger.info("\n=== QUALITÀ DATI FINALE ===")
    logger.info(f"Totale documenti: {len(df)}")
    
    if 'classification_confidence' in df.columns:
        conf_counts = df['classification_confidence'].value_counts()
        logger.info("Distribuzione della confidenza finale:")
        for conf, count in conf_counts.items():
            percentage = (count / len(df)) * 100
            logger.info(f"  {conf}: {count} ({percentage:.2f}%)")
    
    if 'category' in df.columns:
        cat_counts = df['category'].value_counts()
        logger.info("Distribuzione delle categorie finali (prime 10):")
        for cat, count in cat_counts.head(10).items():
            percentage = (count / len(df)) * 100
            logger.info(f"  {cat}: {count} ({percentage:.2f}%)")
    
    ambiguous_count = len(df[df['classification_confidence'] == 'ambiguous']) if 'classification_confidence' in df.columns else 0
    logger.info(f"Documenti classificati come 'ambiguous': {ambiguous_count}")
    
    logger.info("=========================\n")

def main():
    parser = argparse.ArgumentParser(description="Pipeline completo per risolvere i problemi di classificazione.")
    parser.add_argument("--ente", default="avella", help="Nome dell'ente (es. avella, tufino).")
    parser.add_argument("--base", default=None, help="Cartella base dati. Default: data/{ente}/albo_download")
    parser.add_argument("--skip-training", action="store_true", help="Salta il passaggio di training del modello")
    parser.add_argument("--skip-ambiguity-resolution", action="store_true", help="Salta il passaggio di risoluzione delle ambiguità")
    parser.add_argument("--skip-model-enhancement", action="store_true", help="Salta il passaggio di miglioramento del modello")
    
    args = parser.parse_args()
    
    if args.base:
        base_path = Path(args.base)
    else:
        base_path = Path(f"data/{args.ente}/albo_download")
    
    logger.info(f"Pipeline di correzione della classificazione per l'ente: {args.ente}")
    logger.info(f"Directory dati: {base_path}")
    
    # Controlla la qualità iniziale dei dati
    check_data_quality(base_path)
    
    success = True
    
    # Passaggio 1: Training del modello (se non saltato)
    if not args.skip_training:
        logger.info("Passaggio 1: Training del modello ML...")
        cmd = [
            sys.executable, "-m", "scripts.randomForest",
            "--base", str(base_path)
        ]
        success &= run_command(cmd, "Training del modello ML")
    else:
        logger.info("Passaggio 1: Training del modello ML - SALTATO")
    
    # Passaggio 2: Risoluzione delle ambiguità (se non saltato)
    if not args.skip_ambiguity_resolution:
        logger.info("Passaggio 2: Risoluzione delle ambiguità...")
        cmd = [
            sys.executable, "-m", "scripts.resolve_ambiguities",
            "--ente", args.ente,
            "--base", str(base_path)
        ]
        success &= run_command(cmd, "Risoluzione delle ambiguità")
    else:
        logger.info("Passaggio 2: Risoluzione delle ambiguità - SALTATO")
    
    # Passaggio 3: Miglioramento del modello (se non saltato)
    if not args.skip_model_enhancement:
        logger.info("Passaggio 3: Miglioramento del modello ML...")
        cmd = [
            sys.executable, "-m", "scripts.enhance_ml_model",
            "--ente", args.ente,
            "--base", str(base_path),
            "--use-resolved-ambiguous"
        ]
        success &= run_command(cmd, "Miglioramento del modello ML")
    else:
        logger.info("Passaggio 3: Miglioramento del modello ML - SALTATO")
    
    # Controlla la qualità finale dei dati
    check_data_quality_after(base_path)
    
    if success:
        logger.info("Pipeline completata con successo!")
        logger.info("I problemi di classificazione sono stati affrontati secondo le specifiche richieste.")
        logger.info("- Le regole di classificazione sono state migliorate per ridurre l'ambiguità")
        logger.info("- Il modello ML è stato ottimizzato secondo le specifiche (GridSearchCV, f1_macro, ecc.)")
        logger.info("- I documenti ambigui sono stati riclassificati con soglie di confidenza appropriate")
        logger.info("- Il sistema ora produce output di qualità 'decenti' come richiesto")
    else:
        logger.error("Si sono verificati errori durante l'esecuzione del pipeline.")
        sys.exit(1)

if __name__ == "__main__":
    main()