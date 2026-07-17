import subprocess
import sys
from pathlib import Path
import click
import os
from delibere_comunali.core.config_manager import ConfigManager
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator
from delibere_comunali.utils.privacy_guard import get_privacy_guard


@click.group()
def cli():
    """Strumento CLI per l'analisi e l'audit degli albo pretori comunali."""
    pass


@cli.command()
@click.option('--ente', required=True, help='Nome dell\'ente locale da analizzare (es. milano, roma)')
@click.option('--workflow', default='full', help='Tipo di workflow da eseguire: full, analyze-only, scrape-only')
@click.option('--config', default='config.yaml', help='Percorso al file di configurazione')
def enterprise(ente: str, workflow: str, config: str):
    """
    Esegue il workflow enterprise per un ente specifico.
    """
    config_path = Path(config)
    if not config_path.exists():
        print(f"❌ Configurazione non trovata: {config_path}")
        return
    
    config_manager = ConfigManager(config_path)
    orchestrator = EnterpriseOrchestrator(config_manager)
    
    try:
        if workflow == 'full':
            orchestrator.execute_full_workflow(ente)
        elif workflow == 'analyze-only':
            orchestrator.execute_analysis_only(ente)
        elif workflow == 'scrape-only':
            orchestrator.execute_scraping_only(ente)
        else:
            print(f"❌ Workflow non riconosciuto: {workflow}")
            return
            
        print(f"✅ Workflow completato per l'ente: {ente}")
    except Exception as e:
        print(f"❌ Errore nell'esecuzione del workflow: {e}")


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
    # Costruisci il comando Python per eseguire il modulo di audit
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.processing.audit_engine import main
import argparse

# Simula argomenti da linea di comando
class Args:
    pass

args = Args()
args.base = "{base}"
args.ente = "{ente}" if "{ente}" != "None" else None
args.use_llm = {use_llm}
args.llm_provider = "{llm_provider}" if "{llm_provider}" != "None" else None
args.llm_model = "{llm_model}" if "{llm_model}" != "None" else None
args.skip_supervision = False  # Di default applica la supervisione

# Imposta args se il modulo ha un parser
import sys
from io import StringIO

# Esegui la funzione main
main()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def build_kg(base: str, ente: str):
    """
    Costruisce il knowledge graph relazionale.
    """
    # Costruisci il comando Python per eseguire il modulo di knowledge graph
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.knowledge_graph.builder import main
import argparse

# Simula argomenti da linea di comando
class Args:
    pass

args = Args()
args.base = "{base}"
args.ente = "{ente}" if "{ente}" != "None" else None

# Esegui la funzione main
main()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
@click.option('--input', required=True, help='File CSV di input con documenti parsati.')
@click.option('--output', required=True, help='File CSV di output con classificazioni migliorate.')
def post_process_classification(input: str, output: str):
    """
    Applica post-elaborazione alle classificazioni dei documenti con OCR.
    """
    # Esegue il modulo di post-process classification
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.parsing.post_process_classification import apply_post_processing_classification
from pathlib import Path

success = apply_post_processing_classification(Path('{input}'), Path('{output}'))
if success:
    print('✅ Post-processing classification completato con successo.')
else:
    print('❌ Errore nel post-processing classification.')
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def analyze_topology(base: str, ente: str):
    """
    Analizza la topologia del knowledge graph.
    """
    # Costruisci il comando Python per eseguire l'analisi topologica
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.analysis.topology_analyzer import main
import argparse

# Simula argomenti da linea di comando
class Args:
    pass

args = Args()
args.base = "{base}"
args.ente = "{ente}" if "{ente}" != "None" else None

# Esegui la funzione main
main()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
@click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
@click.option('--ente', default=None, help='Identificativo ente (opzionale)')
def supervised_training(base: str, ente: str):
    """
    Esegue il riaddestramento supervisionato con feedback umano.
    """
    # Costruisci il comando Python per eseguire il riaddestramento supervisionato
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.ml.trainer import main
import argparse

# Simula argomenti da linea di comando
class Args:
    pass

args = Args()
args.base = "{base}"
args.ente = "{ente}" if "{ente}" != "None" else None

# Esegui la funzione main
main()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
def metrics_exporter():
    """
    Avvia il server per l'esportazione delle metriche e il monitoraggio.
    """
    # Esegue il modulo di esportazione metriche
    cmd = [
        sys.executable,
        "-c",
        """
import sys
sys.path.insert(0, '.')
from delibere_comunali.web.metrics_exporter import main

# Esegui la funzione main
main()
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode


@cli.command()
@click.option('--user-identifier', required=True, help='Identificativo utente da cancellare (CF, PIVA, email, etc.)')
@click.option('--data-path', default='data/', help='Percorso dei dati in cui cercare i dati utente')
def gdpr_delete(user_identifier: str, data_path: str):
    """
    Implementa il diritto all'oblio (GDPR Art. 17) cancellando i dati utente.
    """
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


if __name__ == "__main__":
    cli()