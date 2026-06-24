#!/usr/bin/env python3
"""Entry point universale per albo-pretorio-audit-delivery.
Funziona su Windows (py) e Linux (python3)."""

import sys
import subprocess
from pathlib import Path

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

    # Script legacy in scripts/ (mantenuti per backward compatibility)
    "build-kg": ("scripts/build_knowledge_graph.py",),
    "analyze-topology": ("scripts/analyze_topology.py",),
    "detect-anomalies": ("scripts/detect_anomalies.py",),
    "train": ("scripts/train_model.py",),
    "validate-output": ("scripts/validate_output.py",),
    "validate-csv": ("scripts/validate_csv_schema.py",),
    "export-linkeddata": ("scripts/export_linked_data.py",),
    "clean-texts": ("scripts/clean_texts.py",),
    "sync-texts": ("scripts/sync_texts.py",),
    "generate-groundtruth": ("scripts/generate_ground_truth.py",),
    "visualize-graph": ("scripts/visualizza_grafo.py",),
}

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

    cmd = sys.argv[1].lower().replace("_", "-").replace("-", "-")
    args = sys.argv[2:]

    if cmd not in COMMAND_MAP:
        print(f"❌ Comando sconosciuto: {sys.argv[1]}")
        print(f"Did you mean? {', '.join(COMMAND_MAP.keys())}")
        sys.exit(1)

    python_cmd = get_python_cmd()
    cmd_config = COMMAND_MAP[cmd]

    # Costruisci il comando
    if cmd_config[0] == "-m":
        # Modulo
        full_cmd = [*python_cmd, *cmd_config]
    else:
        # Script diretto
        full_cmd = [*python_cmd, *cmd_config]

    full_cmd.extend(args)

    # Esegue
    result = subprocess.run(full_cmd, check=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()