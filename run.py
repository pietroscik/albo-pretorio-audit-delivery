#!/usr/bin/env python3
"""Entry point universale per albo-pretorio-audit-delivery.
Funziona su Windows (py) e Linux (python3).

Comandi principali di coordinamento:
- orchestrate: Esegue la pipeline completa di coordinamento tra tutti i moduli avanzati
- data-coord: Interfaccia per il coordinatore dati centralizzato

Per maggiori informazioni sui comandi di coordinamento, vedere COORDINATION_GUIDE.md
"""

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
        # Cerca il modulo tra i candidati
        mod = None
        for m in module_candidates:
            # Controlla se il modulo esiste cercando il file corrispondente
            module_parts = m.split('.')
            module_path = PROJECT_ROOT / "src"
            for part in module_parts:
                module_path = module_path / part
            # Controlla se esiste come file .py o come directory con __init__.py
            module_file = module_path.with_suffix('.py')
            module_dir = module_path / "__init__.py"
            if module_file.exists() or module_dir.exists():
                mod = m
                break
        
        if not mod:
            raise FileNotFoundError(f"Nessun entrypoint trovato. Cercati script: {script_candidates}, moduli: {module_candidates}")
        
        cmd = [sys.executable, "-m", mod] + args
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

    # --- Moduli di coordinamento centrale ---
    "orchestrate":      ("-m", "delibere_comunali.core.orchestrator"),  # Coordinamento centrale tra tutti i moduli avanzati (Risk Assessment, KPI, ML, Audit)
    "data-coord":       ("-m", "delibere_comunali.core.data_coordinator"),  # Coordinatore dati centralizzato per la gestione dei dati condivisi tra i moduli

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
        print("\nCore orchestration commands:")
        print("  orchestrate    Execute full coordination pipeline between all advanced modules (Risk Assessment, KPI, ML, Audit)")
        print("  data-coord     Interact with centralized data coordinator for shared data management")
        print("\nAdvanced analysis commands:")
        print("  risk-assessment     Execute risk assessment analysis")
        print("  actuarial-analysis  Execute actuarial analysis and provisioning")
        print("  management-kpi      Execute management KPI calculation")
        print("\nFor more information on orchestration commands, see COORDINATION_GUIDE.md")
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

    if cmd in STREAMLIT_COMMANDS:
        # Per i comandi streamlit, lanciamo direttamente lo script con streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run"] + cmd_config[1:] + args, env=env, cwd=PROJECT_ROOT)
    else:
        # Per gli altri comandi, usiamo il metodo standard
        if cmd_config[0] == "-m":
            # Se il primo elemento è "-m", allora è un modulo
            _run_tool([], (cmd_config[1],), args)
        elif len(cmd_config) == 1 and not cmd_config[0].endswith('.py'):
            # Se il comando è un percorso ma non ha estensione .py, potrebbe essere un modulo
            # Controlla se esiste come modulo
            module_path = PROJECT_ROOT / "src"
            module_parts = cmd_config[0].split('.')
            for part in module_parts:
                module_path = module_path / part
            module_file = module_path.with_suffix('.py')
            module_dir = module_path / "__init__.py"
            
            if module_file.exists() or module_dir.exists():
                _run_tool([], cmd_config, args)
            else:
                _run_tool(cmd_config, [], args)
        else:
            # Altrimenti è uno script
            _run_tool(cmd_config, [], args)

if __name__ == "__main__":
    main()