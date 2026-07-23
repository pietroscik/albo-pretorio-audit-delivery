#!/usr/bin/env python3
"""
Script per verificare l'elaborazione dei file P7M dopo lo scraping.
Controlla che tutti i file P7M siano stati elaborati correttamente e che i PDF estratti siano disponibili.
"""

import os
import sys
from pathlib import Path
import logging

# Aggiungi il percorso src per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from delibere_comunali.utils.p7m_unwrapper import process_p7m_files_in_directory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_p7m_processing(ente: str = "baiano"):
    """
    Controlla lo stato dell'elaborazione dei file P7M.
    
    Args:
        ente: Nome dell'ente da controllare (default: "baiano")
    """
    download_dir = Path(f"data/{ente}/albo_download")
    pdf_dir = download_dir / "pdf"
    
    if not pdf_dir.exists():
        logger.error(f"Directory PDF non trovata: {pdf_dir}")
        return False
    
    # Conta i file P7M rimasti
    p7m_files = list(pdf_dir.glob("*.p7m")) + list(pdf_dir.glob("*.P7M"))
    
    logger.info(f"Trovati {len(p7m_files)} file P7M non elaborati in {pdf_dir}")
    
    if len(p7m_files) > 0:
        logger.info("Elaborando i file P7M rimasti...")
        process_p7m_files_in_directory(pdf_dir)
        
        # Controlla nuovamente
        remaining_p7m = list(pdf_dir.glob("*.p7m")) + list(pdf_dir.glob("*.P7M"))
        logger.info(f"File P7M rimasti dopo elaborazione: {len(remaining_p7m)}")
    
    # Controlla anche la directory di archivio
    archive_dir = pdf_dir / "p7m_archives"
    if archive_dir.exists():
        archived_files = list(archive_dir.glob("*.p7m")) + list(archive_dir.glob("*.P7M"))
        logger.info(f"File P7M archiviati: {len(archived_files)}")
    
    # Conta i PDF estratti
    pdf_files = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
    logger.info(f"PDF estratti disponibili: {len(pdf_files)}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Controlla l\'elaborazione dei file P7M')
    parser.add_argument('--ente', default='baiano', help='Nome dell\'ente da controllare (default: baiano)')
    
    args = parser.parse_args()
    
    success = check_p7m_processing(ente=args.ente)
    
    if success:
        logger.info("Controllo completato con successo")
    else:
        logger.error("Si è verificato un errore durante il controllo")
        sys.exit(1)