"""
Modulo per la valutazione del rischio negli atti pubblici comunali.
"""

import argparse
import pandas as pd
from pathlib import Path
from typing import Optional
import sys
import os


def main(input_path: Optional[str] = None, output_path: Optional[str] = None):
    """
    Funzione principale per l'esecuzione della valutazione del rischio.
    
    Args:
        input_path: Percorso del file di input (opzionale)
        output_path: Percorso per salvare i risultati (opzionale)
        
    Oppure:
        input_path: Oggetto Args contenente attributi 'ente' (passato dall'orchestrator)
    """
    from ..risk_assessment.risk_calculator import run_risk_assessment
    
    # Controlla se il primo parametro è un oggetto Args con attributo 'ente'
    if hasattr(input_path, 'ente'):
        # Caso in cui viene passato un oggetto Args dall'orchestrator
        ente = getattr(input_path, 'ente', 'avella')
        input_path = f"data/{ente}/albo_download/albo_metadati.csv"
        output_path = f"data/{ente}/albo_download/report"
    elif input_path is None:
        # Usa valori di default
        input_path = "data/avella/albo_download/albo_metadati.csv"
        output_path = "data/avella/albo_download/report"
    
    if output_path is None:
        output_path = "data/avella/albo_download/report"
    
    # Crea la directory di output se non esiste
    os.makedirs(output_path, exist_ok=True)
    
    run_risk_assessment(input_path, output_path)


def cli_main():
    """
    Funzione per l'esecuzione da riga di comando.
    """
    parser = argparse.ArgumentParser(description='Valutazione del rischio per atti pubblici comunali')
    parser.add_argument('--input', type=str, help='Percorso del file di input')
    parser.add_argument('--output', type=str, help='Percorso per salvare i risultati')
    
    # Se non vengono forniti argomenti, usa valori di default
    if len(sys.argv) == 1:
        # Nessun argomento fornito, usa valori di default
        main()
    else:
        args = parser.parse_args()
        main(args.input, args.output)


if __name__ == "__main__":
    cli_main()