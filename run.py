#!/usr/bin/env python3
"""Entry point universale per albo-pretorio-audit-delivery.
Funziona su Windows (py) e Linux (python3)."""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def _resolve_existing_path(candidates: list[str]) -> Path | None:
    for rel in candidates:
        p = PROJECT_ROOT / rel
        if p.exists():
            return p
    return None

def _run_tool(script_candidates: list[str], module_candidates: list[str], args: list[str]) -> None:
    script = _resolve_existing_path(script_candidates)
    if script:
        cmd = [sys.executable, str(script), *args]
    else:
        mod = next((m for m in module_candidates if m), None)
        if not mod:
            raise FileNotFoundError(f"Nessun entrypoint trovato. Cercati script: {script_candidates}")
        cmd = [sys.executable, "-m", mod, *args]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

COMMAND_MAP = {
    # --- Moduli principali ---
    "scrape":           ("-m", "delibere_comunali.scraping.new_albo_scraper"),
    "analyze":          ("-m", "delibere_comunali.parsing.analyze_albo"),
    "pipeline":         ("-m", "delibere_comunali.cli.run_pipeline"),
    "rag":              ("-m", "delibere_comunali.rag.rag_app"),
    "validate-csv": (str(PROJECT_ROOT / "scripts" / "validate_output.py"),),
    "control-room":     ("-m", "delibere_comunali.cli.app_control_room"),
    "audit":            ("-m", "delibere_comunali.processing.audit_engine"),
    "post-process-classification": ("-m", "delibere_comunali.processing.post_process_classification"),
    "apply-corrections": (str(PROJECT_ROOT / "scripts" / "apply_feedback_corrections.py"),),
    
    # --- Nuovi moduli integrati ---
    "risk-assessment":  ("-m", "delibere_comunali.risk_assessment.risk_calculator"),
    "actuarial-analysis": ("-m", "delibere_comunali.actuarial_analysis.provisioning"),
    "management-kpi":   ("-m", "delibere_comunali.management_kpi.kpi_calculator"),

    # --- Alias comodi ---
    "post-process":     ("-m", "delibere_comunali.processing.post_process_classification"),
    "ui":               ("-m", "delibere_comunali.cli.app_control_room"),
    "dashboard":        ("-m", "delibere_comunali.cli.app_control_room"),
    "run-pipeline":     ("-m", "delibere_comunali.cli.run_pipeline"),
    "scraper":          ("-m", "delibere_comunali.scraping.new_albo_scraper"),

    # --- Script legacy in scripts/ ---
    "build-kg":         (str(PROJECT_ROOT / "scripts" / "build_knowledge_graph.py"),),
    "analyze-topology": (str(PROJECT_ROOT / "scripts" / "analyze_topology.py"),),
    "detect-anomalies": (str(PROJECT_ROOT / "scripts" / "detect_anomalies.py"),),
    "export-linkeddata":(str(PROJECT_ROOT / "scripts" / "export_linked_data.py"),),
    "train":            (str(PROJECT_ROOT / "scripts" / "train_model.py"),),
    "validate-output":  (str(PROJECT_ROOT / "scripts" / "validate_output.py"),),
    "clean-texts":      (str(PROJECT_ROOT / "scripts" / "clean_texts.py"),),
    "sync-texts":       (str(PROJECT_ROOT / "scripts" / "sync_texts.py"),),
    "generate-groundtruth": (str(PROJECT_ROOT / "scripts" / "generate_ground_truth.py"),),
    "visualize-graph":  (str(PROJECT_ROOT / "scripts" / "visualizza_grafo.py"),),
    "explore":          (str(PROJECT_ROOT / "scripts" / "explore_albo.py"),),
    "reconcile":        (str(PROJECT_ROOT / "scripts" / "reconcile_semantic.py"),),
    "validate-fase0":   (str(PROJECT_ROOT / "scripts" / "validate_fase0.py"),),
    "validate-ground":  (str(PROJECT_ROOT / "scripts" / "validate_ground_truth.py"),),
    "verify-output":    (str(PROJECT_ROOT / "scripts" / "verify_output.py"),),
    "update-preview":   (str(PROJECT_ROOT / "scripts" / "update_preview.py"),),
    "finance-validate": (str(PROJECT_ROOT / "scripts" / "finance_validator.py"),),
    "random-forest":    (str(PROJECT_ROOT / "scripts" / "randomForest.py"),),
}

STREAMLIT_COMMANDS = {"control-room", "ui", "dashboard", "rag"}

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command> [args...]")
        print("\nAvailable commands:")
        for cmd in sorted(COMMAND_MAP.keys()):
            print(f"  {cmd}")
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMAND_MAP:
        print(f"❌ Comando sconosciuto: {cmd}")
        print("Comandi disponibili:", ", ".join(sorted(COMMAND_MAP.keys())))
        sys.exit(1)

    cmd_config = COMMAND_MAP[cmd]

    # Imposta PYTHONPATH in modo che `src/` sia sempre nel path (necessario per Streamlit e script legacy)
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    if src_path not in existing_pythonpath.split(os.pathsep):
        env["PYTHONPATH"] = src_path + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

    # Streamlit richiede lancio speciale
    if cmd in STREAMLIT_COMMANDS and cmd_config[0] == "-m":
        module_path = cmd_config[1].replace(".", "/")
        script_path = PROJECT_ROOT / "src" / f"{module_path}.py"
        full_cmd = [sys.executable, "-m", "streamlit", "run", str(script_path), *args]
    elif cmd_config[0] == "-m":
        full_cmd = [sys.executable, *cmd_config, *args]
    else:
        full_cmd = [sys.executable, *cmd_config, *args]

    try:
        result = subprocess.run(full_cmd, check=True, env=env)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nell'esecuzione di {' '.join(str(x) for x in full_cmd)}")
        print(f"Codice di uscita: {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError as e:
        print(f"❌ Comando non trovato: {e.filename}")
        print("Assicurati che Python sia installato e nel PATH")
        sys.exit(1)

if __name__ == "__main__":
    main()