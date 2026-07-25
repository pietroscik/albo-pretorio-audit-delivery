import subprocess
import sys
import asyncio

if sys.platform == "win32" and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import subprocess
import sys
from pathlib import Path
import click
import os
import re
import shlex

def sanitize_command_args(args):
    """Sanitizes command-line arguments to prevent command injection."""
    sanitized = []
    for arg in args:
        # Remove potentially dangerous characters
        safe_arg = re.sub(r'[;&|`$()\\]', '', arg)
        # Strip whitespace and quote characters
        safe_arg = safe_arg.strip().replace('"', '').replace("'", "")
        if safe_arg:
            sanitized.append(safe_arg)
    return sanitized

def run_subprocess_securely(cmd, env=None, cwd=None):
    """Runs a subprocess securely with sanitized command and environment."""
    try:
        # Log the command for debugging/audit
        print(f"Executing command: {' '.join(shlex.quote(part) for part in cmd)}")
        
        # Execute securely
        result = subprocess.run(
            cmd,
            check=True,
            env=env,
            cwd=cwd,
            shell=False  # Prevent shell injection
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command securely: {e}")
        return e.returncode


def safe_import(module_name, attr_name=None):
    """Safely import a module or attribute, returning None if not available."""
    try:
        module = __import__(module_name, fromlist=[attr_name] if attr_name else [])
        if attr_name:
            return getattr(module, attr_name, None)
        return module
    except ImportError:
        return None


# Try to import optional dependencies
ConfigManager = safe_import('delibere_comunali.core.config_manager', 'ConfigManager')
EnterpriseOrchestrator = safe_import('delibere_comunali.core.enterprise_orchestration', 'EnterpriseOrchestrator')
get_privacy_guard = safe_import('delibere_comunali.utils.privacy_guard', 'get_privacy_guard')


@click.group()
def cli():
    """Strumento CLI per l'analisi e l'audit degli albo pretori comunali."""
    pass


@cli.command()
@click.argument('ente', type=str)
@click.option('-w', '--workflow', type=click.Choice(['full', 'analyze-only', 'scrape-only']), default='full', 
              help='Tipo di workflow da eseguire: full (default), analyze-only (solo analisi), scrape-only (solo scraping)')
@click.option('-c', '--config', type=str, default='default', 
              help='Nome del file di configurazione da utilizzare')
def enterprise(ente: str, workflow: str, config: str):
    """
    Esegue il workflow enterprise per un ente specifico.
    Questo comando coordina tutti i servizi per l'analisi completa.
    """
    from src.delibere_comunali.core.orchestrator import CentralOrchestrator
    from src.delibere_comunali.utils.config import get_config  # Fixed import
    
    # Load configuration
    config_obj = get_config()
    
    # Initialize orchestrator
    orchestrator = CentralOrchestrator(config_obj)
    
    # Map workflow options to corresponding parameters
    workflow_mapping = {
        'full': 'full',
        'analyze-only': 'analyze_only',  # Run only analysis without scraping
        'scrape-only': 'minimal'  # Minimal analysis for scraping only
    }
    
    workflow_type = workflow_mapping.get(workflow, 'full')
    
    custom_params = {}
    if workflow == 'scrape-only':
        # For scraping only, we might want to skip other analyses
        custom_params = {'skip_risk': True, 'skip_kpi': True, 'skip_ml': True, 'skip_audit': True}
    elif workflow == 'analyze-only':
        # For analysis only, we want to run analysis but not scraping
        # The orchestrator should handle this appropriately
        custom_params = {'skip_scraping': True}
    
    results = orchestrator.run_workflow(
        workflow_type=workflow_type,
        ente=ente,
        custom_params=custom_params
    )
    
    click.echo(f"Enterprise workflow completed for {ente}")
    return results


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
@click.option('--use-llm', is_flag=True, help='Abilita arricchimento LLM (opzionale)')
@click.option('--llm-provider', default=None, help='Provider LLM (openai, gemini, mistral...)')
@click.option('--llm-model', default=None, help='Modello LLM da usare')
def audit(base: str, ente: str, use_llm: bool, llm_provider: str, llm_model: str):
    """
    Esegue l'audit antifrode sugli atti comunali.
    """
    original_argv = sys.argv
    try:
        from delibere_comunali.processing.audit_engine import main as audit_main

        # Simula gli argomenti a riga di comando per il modulo target
        sys.argv = ['audit_engine.py', '--base', base]
        if ente:
            sys.argv.extend(['--ente', ente])
        if use_llm:
            sys.argv.append('--use-llm')
        if llm_provider:
            sys.argv.extend(['--llm-provider', llm_provider])
        if llm_model:
            sys.argv.extend(['--llm-model', llm_model])

        audit_main()
    except ImportError:
        print("❌ Modulo di audit non trovato. Assicurati che le dipendenze siano installate.")
    except Exception as e:
        print(f"❌ Errore durante l'esecuzione dell'audit: {e}", file=sys.stderr)
    finally:
        sys.argv = original_argv


@cli.command()
@click.option('--base', default=None, help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def build_kg(base: str, ente: str):
    """
    Costruisce il knowledge graph relazionale.
    """
    original_argv = sys.argv
    try:
        from delibere_comunali.knowledge_graph.builder import main as builder_main

        # If base is not provided but ente is, construct the base path from ente
        if base is None and ente is not None:
            base = f"data/{ente}/albo_download"
        elif base is None:
            # Default to baiano if neither base nor ente is provided
            base = 'data/baiano/albo_download'

        # Simula gli argomenti a riga di comando
        sys.argv = ['builder.py', '--base', base]
        if ente:
            sys.argv.extend(['--ente', ente])

        builder_main()
    except ImportError:
        print("❌ Modulo builder del Knowledge Graph non trovato.")
    except Exception as e:
        print(f"❌ Errore durante la costruzione del Knowledge Graph: {e}", file=sys.stderr)
    finally:
        sys.argv = original_argv


@cli.command()
@click.option('--input', required=True, help='File CSV di input con documenti parsati.')
@click.option('--output', required=True, help='File CSV di output con classificazioni migliorate.')
def post_process_classification(input: str, output: str):
    """
    Applica post-elaborazione alle classificazioni dei documenti con OCR.
    """
    try:
        from delibere_comunali.parsing.post_process_classification import apply_post_processing_classification
        
        success = apply_post_processing_classification(Path(input), Path(output))
        if success:
            print('[OK] Post-processing della classificazione completato con successo.')
        else:
            print('❌ Errore nel post-processing della classificazione.')
    except ImportError:
        print("❌ Modulo di post-processing non trovato.")
    except Exception as e:
        print(f"❌ Errore durante il post-processing: {e}", file=sys.stderr)


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def analyze_topology(base: str, ente: str):
    """
    Analizza la topologia del knowledge graph.
    """
    try:
        # Importa il nuovo modulo refactorizzato
        from delibere_comunali.analysis.topology_analyzer import main as analyze_topology_main
        from delibere_comunali.utils.config import get_tenant_dir

        effective_ente = ente or 'baiano'
        effective_base = base or str(get_tenant_dir(effective_ente) / "albo_download")

        analyze_topology_main(ente=effective_ente, base_dir=effective_base)
    except Exception as e:
        print(f"❌ Errore durante l'analisi topologica: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option('--ente', required=True, help='Nome dell\'ente per cui addestrare il modello.')
def train_classifier(ente: str):
    """
    Addestra il modello di classificazione con ottimizzazione degli iperparametri.
    """
    try:
        from delibere_comunali.ml.classifier_trainer import train_and_evaluate_classifier
        from delibere_comunali.utils.config import get_tenant_dir

        print(f"Avvio training per l'ente: {ente}")
        base_path = get_tenant_dir(ente)
        # Assicurati che il percorso base per il training sia corretto
        training_base_path = base_path / "albo_download" if base_path.name != "albo_download" else base_path
        train_and_evaluate_classifier(training_base_path)
        print(f"✅ Training completato per l'ente: {ente}")
    except Exception as e:
        print(f"❌ Errore durante il training del classificatore: {e}", file=sys.stderr)


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def supervised_training(base: str, ente: str):
    """
    Esegue il riaddestramento supervisionato con feedback umano.
    """
    original_argv = sys.argv
    try:
        from delibere_comunali.ml.trainer import main as trainer_main

        # Simula gli argomenti a riga di comando
        sys.argv = ['trainer.py', '--base', base]
        if ente:
            sys.argv.extend(['--ente', ente])

        trainer_main()
    except ImportError:
        print("❌ Modulo di training non trovato.")
    except Exception as e:
        print(f"❌ Errore durante il training supervisionato: {e}", file=sys.stderr)
    finally:
        sys.argv = original_argv


@cli.command()
def metrics_exporter():
    """
    Avvia il server per l'esportazione delle metriche e il monitoraggio.
    """
    from delibere_comunali.web.metrics_exporter import main as exporter_main
    print("Avvio del server di esportazione metriche...")
    exporter_main()


@cli.command()
@click.option('--user-identifier', required=True, help='Identificativo utente da cancellare (CF, PIVA, email, etc.)')
@click.option('--data-path', default='data/', help='Percorso dei dati in cui cercare i dati utente')
def gdpr_delete(user_identifier: str, data_path: str):
    """
    Implementa il diritto all'oblio (GDPR Art. 17) cancellando i dati utente.
    """
    if get_privacy_guard is None:
        print("❌ Modulo privacy guard non disponibile: dipendenze mancanti")
        return
        
    try:
        privacy_guard = get_privacy_guard()
        success = privacy_guard.right_to_be_forgotten(user_identifier, Path(data_path))
        
        if success:
            print(f"✅ Diritto all'oblio eseguito per l'utente: {user_identifier}")
        else:
            print(f"❌ Errore nell'esecuzione del diritto all'oblio per l'utente: {user_identifier}")
            
    except Exception as e:
        print(f"❌ Errore nell'esecuzione del diritto all'oblio: {e}")


@cli.command()
@click.option('--ente', required=True, help='Nome dell\'ente per cui generare il report di conformità')
def privacy_report(ente: str):
    """
    Genera un report di conformità GDPR per un ente specifico.
    """
    if get_privacy_guard is None:
        print("❌ Modulo privacy guard non disponibile: dipendenze mancanti")
        return
        
    try:
        privacy_guard = get_privacy_guard()
        report = privacy_guard.generate_privacy_report([ente])
        
        print(f"📊 Report di conformità GDPR per l'ente: {ente}")
        print(f"   Punteggio di conformità: {report['gdpr_compliance_score']}/100")
        print(f"   Campi sensibili rilevati: {len(report['sensitive_fields_detected'])}")
        print(f"   Raccomandazioni: {len(report['recommendations'])}")
        
        # Salva il report
        report_path = Path(f"data/{ente}/reports/privacy_compliance.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Report salvato in: {report_path}")
        
    except Exception as e:
        print(f"❌ Errore nella generazione del report di conformità: {e}")


@cli.command()
def control_room():
    """
    Avvia la dashboard di controllo (Streamlit app).
    """
    # Esegue l'app Streamlit della control room
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/delibere_comunali/cli/app_control_room.py",
        "--server.port",
        "8501",
        "--server.address",
        "0.0.0.0"
    ]
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    return result.returncode


@cli.command()
def dashboard():
    """
    Alias per avviare la dashboard di controllo (Streamlit app).
    """
    # Chiama lo stesso comando della control room
    control_room()


@cli.command()
def ui():
    """
    Alias per avviare l'interfaccia utente (Streamlit app).
    """
    # Chiama lo stesso comando della control room
    control_room()


# Legacy command mapping system for backward compatibility
PROJECT_ROOT = Path(__file__).resolve().parent

def _run_tool(script_candidates, module_candidates, args):
    """Esegue uno script o modulo con i parametri forniti."""
    # Controlla prima i moduli
    for module in module_candidates:
        try:
            cmd = [sys.executable, "-m", module] + list(sanitize_command_args(args))
            return run_subprocess_securely(cmd)
        except subprocess.CalledProcessError as e:
            print(f"❌ Errore nell'esecuzione del modulo {module}: {e}")
            return e.returncode
        except FileNotFoundError:
            continue  # Prova il successivo
    
    # Poi prova gli script
    for script in script_candidates:
        script_path = Path(script)
        if not script_path.is_absolute():
            script_path = PROJECT_ROOT / script
        if script_path.exists():
            cmd = [sys.executable, str(script_path)] + list(sanitize_command_args(args))
            try:
                return run_subprocess_securely(cmd)
            except subprocess.CalledProcessError as e:
                print(f"❌ Errore nell'esecuzione dello script {script_path}: {e}")
                return e.returncode
        else:
            continue
    
    print(f"❌ File non trovato: {script_candidates or module_candidates}")
    return 1


def _sanitize_input(input_str):
    """Sanitize input to prevent command injection."""
    if not isinstance(input_str, str):
        return input_str
    # Remove potentially dangerous characters
    return input_str.replace(';', '').replace('|', '').replace('&', '').replace('`', '').replace('$(', '').replace('\n', '').replace('\r', '')


def _handle_alias_command(cmd, args):
    """Handle command aliases by redirecting to the appropriate command."""
    alias_map = {
        "control-room": "dashboard",
        "ui": "dashboard",
        "dashboard": "streamlit_dashboard"
    }
    
    if cmd in alias_map:
        target_cmd = alias_map[cmd]
        if target_cmd == "streamlit_dashboard":
            # Special handling for streamlit apps
            cmd = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/delibere_comunali/cli/app_control_room.py",
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0"
            ] + list(sanitize_command_args(args))
            return run_subprocess_securely(cmd, cwd=os.getcwd())
    return None


# Mapping dei comandi legacy
COMMAND_MAP = {
    # Comandi principali
    "scrape": ("-m", "delibere_comunali.scraping.new_albo_scraper"),
    "analyze": ("-m", "delibere_comunali.parsing.analyze_albo"),
    "pipeline": ("-m", "delibere_comunali.cli.run_pipeline"),
    "validate-csv": ("-m", "delibere_comunali.validation.csv_validator"),
    "validate-output": ("-m", "delibere_comunali.validation.output_validator"),  # Updated to new module
    
    # Comandi enterprise
    "orchestrate": ("-m", "delibere_comunali.core.orchestrator"),
    "data-coord": ("-m", "delibere_comunali.core.data_coordinator"),
    "enterprise": ("-m", "delibere_comunali.core.enterprise_orchestration"),
    "config-mgmt": ("-m", "delibere_comunali.core.config_manager"),
    
    # Comandi ML e analytics
    "risk-assessment": ("-m", "delibere_comunali.analysis.risk_assessment"),
    "management-kpi": ("-m", "delibere_comunali.analysis.management_kpi"),
    "actuarial-analysis": ("-m", "delibere_comunali.analysis.actuarial_analysis"),
    
    # Comandi di post-processing e correzioni
    "post-process-classification": ("-m", "delibere_comunali.parsing.post_process_classification"),
    "apply-corrections": ("-m", "delibere_comunali.processing.correction_handler"),
    
    # Dashboard e UI
    "dashboard": ("streamlit_dashboard",),  # Placeholder for special handling
    "rag": ("-m", "delibere_comunali.rag.rag_app"),
    "run-pipeline": ("-m", "delibere_comunali.cli.run_pipeline"),
    "scraper": ("-m", "delibere_comunali.scraping.new_albo_scraper"),
    
    # Script legacy in scripts/
    "build-kg": (str(PROJECT_ROOT / "scripts" / "build_knowledge_graph.py"),),
    "analyze-topology": (str(PROJECT_ROOT / "scripts" / "analyze_topology.py"),),
    "detect-anomalies": (str(PROJECT_ROOT / "scripts" / "detect_anomalies.py"),),
    "export-linkeddata": (str(PROJECT_ROOT / "scripts" / "export_linked_data.py"),),
    "train": (str(PROJECT_ROOT / "scripts" / "train_model.py"),),
    "clean-texts": (str(PROJECT_ROOT / "scripts" / "clean_texts.py"),),
    "sync-texts": (str(PROJECT_ROOT / "scripts" / "sync_texts.py"),),
    "generate-groundtruth": (str(PROJECT_ROOT / "scripts" / "generate_ground_truth.py"),),
    "visualize-graph": (str(PROJECT_ROOT / "scripts" / "visualizza_grafo.py"),),
    "explore": (str(PROJECT_ROOT / "scripts" / "explore_albo.py"),),
    "reconcile": (str(PROJECT_ROOT / "scripts" / "reconcile_semantic.py"),),
    "validate-fase0": (str(PROJECT_ROOT / "scripts" / "validate_fase0.py"),),
    "validate-ground": (str(PROJECT_ROOT / "scripts" / "validate_ground_truth.py"),),
    "verify-output": (str(PROJECT_ROOT / "scripts" / "verify_output.py"),),
    "update-preview": (str(PROJECT_ROOT / "scripts" / "update_preview.py"),),
    "finance-validate": (str(PROJECT_ROOT / "scripts" / "finance_validator.py"),),
    "random-forest": (str(PROJECT_ROOT / "scripts" / "randomForest.py"),),
}

# Comandi speciali che richiedono lancio con Streamlit
STREAMLIT_COMMANDS = {"rag", "apply-corrections", "risk-assessment", "actuarial-analysis", "management-kpi"}


def normalize_command(cmd):
    """Normalizza il comando convertendo underscore in trattini."""
    return cmd.lower().replace("_", "-")


def main():
    """Funzione principale per il sistema di comandi legacy."""
    if len(sys.argv) < 2:
        print("Usage: python run.py <command> [args...]")
        print("\nAvailable commands:")
        for cmd in sorted(COMMAND_MAP.keys()):
            print(f"  {cmd}")
        print("\nCore orchestration commands:")
        print("  orchestrate    Execute full coordination pipeline between all advanced modules (Risk Assessment, KPI, ML, Audit)")
        print("  data-coord     Interact with centralized data coordinator for shared data management")
        print("  enterprise     Execute enterprise orchestration with configurable parameters")
        print("  config-mgmt    Manage enterprise configuration settings")
        print("\nAdvanced analysis commands:")
        print("  risk-assessment     Execute risk assessment analysis")
        print("  actuarial-analysis  Execute actuarial analysis and provisioning")
        print("  management-kpi      Execute management KPI calculation")
        print("\nFor more information on orchestration commands, see COORDINATION_GUIDE.md")
        sys.exit(0)

    cmd = normalize_command(sys.argv[1])
    args = sys.argv[2:]

    # Handle aliases
    if cmd in ["control-room", "ui"]:
        # Special handling for control-room and ui aliases
        if cmd == "control-room" or cmd == "ui":
            cmd = "dashboard"  # Redirect to dashboard handling

    # Sanitize command to prevent command injection
    if not re.match(r'^[a-zA-Z0-9_-]+$', cmd):
        print(f"❌ Comando non valido: {cmd}")
        sys.exit(1)

    if cmd not in COMMAND_MAP:
        suggestions = [c for c in COMMAND_MAP.keys() if cmd in c or c in cmd]
        error_msg = f"❌ Comando sconosciuto: {sys.argv[1]}"
        if suggestions:
            error_msg += f"\nDid you mean: {', '.join(suggestions)}?"
        else:
            error_msg += f"\nComandi disponibili: {', '.join(sorted(COMMAND_MAP.keys()))}"
        print(error_msg)
        sys.exit(1)

    cmd_config = COMMAND_MAP[cmd]

    # Imposta PYTHONPATH in modo che `src/` sia sempre nel path (necessario per Streamlit e script legacy)
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    if src_path not in existing_pythonpath.split(os.pathsep):
        env["PYTHONPATH"] = src_path + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

    # Special handling for dashboard
    if cmd == "dashboard":
        # Launch the Streamlit app directly
        full_cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/delibere_comunali/cli/app_control_room.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0"
        ] + sanitize_command_args(args)
        return run_subprocess_securely(full_cmd)
    elif cmd in STREAMLIT_COMMANDS and cmd_config[0] == "-m":
        module_path = cmd_config[1].replace(".", "/")
        script_path = PROJECT_ROOT / "src" / f"{module_path}.py"
        full_cmd = [sys.executable, "-m", "streamlit", "run", str(script_path), "--"] + sanitize_command_args(args)
    elif cmd_config[0] == "-m":
        # Se il primo elemento è "-m", allora è un modulo
        full_cmd = [sys.executable, *cmd_config, *sanitize_command_args(args)]
    elif cmd_config[0] == "streamlit_dashboard":
        # Special case for dashboard
        full_cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/delibere_comunali/cli/app_control_room.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0"
        ] + sanitize_command_args(args)
    else:
        # Altrimenti è uno script
        full_cmd = [sys.executable, *cmd_config, *sanitize_command_args(args)]

    try:
        exit_code = run_subprocess_securely(full_cmd, env=env)
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Errore critico durante l'esecuzione: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Se viene eseguito direttamente con argomenti, usa il sistema legacy
    if len(sys.argv) > 1 and sys.argv[1] not in ['-h', '--help']:
        # Check if the command is one of the Click commands
        click_commands = ['enterprise', 'audit', 'build-kg', 'post-process-classification', 
                         'analyze-topology', 'supervised-training', 'metrics-exporter', 
                         'gdpr-delete', 'privacy-report', 'control-room', 'dashboard', 'ui']
        if sys.argv[1] in click_commands:
            cli()
        else:
            main()
    else:
        # Per --help o nessun argomento, mostra l'aiuto del sistema Click
        cli()