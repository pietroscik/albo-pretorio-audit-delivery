#!/usr/bin/env python3
"""Universal entry point per albo-pretorio-audit-delivery."""
import os
import sys
import subprocess
from pathlib import Path

def get_python_cmd():
    """Ritorna il comando python corretto per l'OS."""
    if sys.platform == "win32":
        return ["py", "-3"]
    return ["python3"]

def main():
    if len(sys.argv) < 2:
        print("Uso: python run.py <comando> [args...]")
        print("Comandi disponibili: scrape, analyze, pipeline, rag")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    python_cmd = get_python_cmd()
    module_map = {
        "scrape": "delibere_comunali.scraping.new_albo_scraper",
        "analyze": "delibere_comunali.parsing.analyze_albo",
        "pipeline": "delibere_comunali.cli.run_pipeline",
        "rag": "delibere_comunali.rag.rag_app",
    }

    if cmd not in module_map:
        print(f"Comando sconosciuto: {cmd}")
        sys.exit(1)

    # Esegue il modulo con il comando python corretto
    result = subprocess.run(
        [*python_cmd, "-m", module_map[cmd], *args],
        check=False
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()