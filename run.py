#!/usr/bin/env python3
"""Entry point universale per albo-pretorio-audit-delivery.
Funziona su Windows (py) e Linux (python3)."""

import sys
import subprocess
from pathlib import Path

# Ottieni la root del progetto (dove si trova questo file)
PROJECT_ROOT = Path(__file__).parent.resolve()

def get_python_cmd():
    """Ritorna il comando python corretto per l'OS."""
    if sys.platform == "win32":
        return ["py", "-3"]
    return ["python3"]

# Mappa tutti i comandi (moduli + script legacy)
COMMAND_MAP = {
    # Moduli principali
    "scrape": ("-m", "delibere_comunali.scraping.new_albo_scraper"),
    "analyze": ("-m", "delibere_comunali.parsing.analyze_albo"),
    "pipeline": ("-m", "delibere_comunali.cli.run_pipeline"),
    "rag": ("-m", "delibere_comunali.rag.rag_app"),
    "control-room": ("-m", "delibere_comunali.cli.app_control_room"),
    
    # Script legacy in scripts/ (usiamo path assoluti)
    "build-kg": (str(PROJECT_ROOT / "scripts" / "build_knowledge_graph.py"),),
    "analyze-topology": (str(PROJECT_ROOT / "scripts" / "analyze_topology.py"),),
    "detect-anomalies": (str(PROJECT_ROOT / "scripts" / "detect_anomalies.py"),),
    "train": (str(PROJECT_ROOT / "scripts" / "train_model.py"),),
    "validate-output": (str(PROJECT_ROOT / "scripts" / "validate_output.py"),),
    "validate-csv": (str(PROJECT_ROOT / "scripts" / "validate_csv_schema.py"),),
    "export-linkeddata": (str(PROJECT_ROOT / "scripts" / "export_linked_data.py"),),
    "clean-texts": (str(PROJECT_ROOT / "scripts" / "clean_texts.py"),),
    "sync-texts": (str(PROJECT_ROOT / "scripts" / "sync_texts.py"),),
    "generate-groundtruth": (str(PROJECT_ROOT / "scripts" / "generate_ground_truth.py"),),
    "visualize-graph": (str(PROJECT_ROOT / "scripts" / "visualizza_grafo.py"),),
}

def normalize_command(cmd):
    """Normalizza il comando: build_kg -> build-kg, buildkg -> build-kg (non valido)"""
    # Sostituisci underscore con trattino
    normalized = cmd.lower().replace("_", "-")
    return normalized

def main():
    if len(sys.argv) < 2:
        print("Uso: python run.py <comando> [args...]")
        print("\nComandi disponibili:")
        for cmd in sorted(COMMAND_MAP.keys()):
            print(f"  - {cmd}")
        print("\nEsempi:")
        print("  python run.py scrape --ente baiano")
        print("  python run.py pipeline --ente baiano --force")
        print("  python run.py build-kg --base data/baiano/albo_download")
        sys.exit(0)

    cmd = normalize_command(sys.argv[1])
    args = sys.argv[2:]

    if cmd not in COMMAND_MAP:
        # Prova a trovare comandi simili
        suggestions = [c for c in COMMAND_MAP.keys() if cmd in c or c in cmd]
        error_msg = f"❌ Comando sconosciuto: {sys.argv[1]}"
        if suggestions:
            error_msg += f"\nDid you mean: {', '.join(suggestions)}?"
        else:
            error_msg += f"\nComandi disponibili: {', '.join(sorted(COMMAND_MAP.keys()))}"
        print(error_msg)
        sys.exit(1)

    python_cmd = get_python_cmd()
    cmd_config = COMMAND_MAP[cmd]

    # Costruisci il comando
    if cmd_config[0] == "-m":
        # Modulo
        full_cmd = [*python_cmd, *cmd_config]
    else:
        # Script diretto (path assoluto già calcolato)
        full_cmd = [*python_cmd, *cmd_config]

    full_cmd.extend(args)

    # Esegue
    try:
        result = subprocess.run(full_cmd, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nell'esecuzione di {' '.join(full_cmd)}")
        print(f"Codice di uscita: {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError as e:
        print(f"❌ Comando non trovato: {e.filename}")
        print(f"Assicurati che Python sia installato e nel PATH")
        sys.exit(1)

if __name__ == "__main__":
    main()