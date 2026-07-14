import subprocess
import sys
from pathlib import Path
import click
import os
from delibere_comunali.core.config_manager import ConfigManager
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator

@click.group()
def cli():
    """Strumento CLI per l'analisi e l'audit degli albi pretori comunali."""
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
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.kg.knowledge_graph_builder import main
import argparse

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
def analyze_topology(base: str, ente: str):
    """
    Analizza la topologia del knowledge graph.
    """
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
from delibere_comunali.topology.topology_analyzer import main
import argparse

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
@click.option('--limit', default=0.1, help='Percentuale di casi da selezionare per il riaddestramento supervisionato (default: 0.1 per il 10%)')
def supervised_training(base: str, ente: str, limit: float):
    """
    Esegue il riaddestramento supervisionato utilizzando il 10% dei casi più critici.
    """
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '.')
import pandas as pd
from pathlib import Path

# Carica i dati di audit esistenti
base_path = Path('{base}')
if '{ente}' != 'None':
    base_path = Path(f'data/{{'{ente}'}}/albo_download')

atti_audited_path = base_path / 'atti_audited.csv'
if not atti_audited_path.exists():
    print(f"❌ File atti_audited.csv non trovato in: {{atti_audited_path}}")
    sys.exit(1)

print("🔄 Caricamento dati di audit...")
df = pd.read_csv(atti_audited_path)

print(f"📊 Dataset originale: {{len(df)}} documenti")

# Ordina per punteggio di rischio decrescente e importo decrescente come criterio secondario
df_sorted = df.sort_values(['risk_score', 'importo_clean'], ascending=[False, False])

# Calcola il numero di documenti da selezionare (10% o valore specificato)
n_to_select = max(1, int(len(df) * {limit}))
top_cases = df_sorted.head(n_to_select)

print(f"🎯 Selezionati {{len(top_cases)}} casi per il riaddestramento supervisionato ({{ {limit} * 100 :.1f}}% del dataset)")
print(f"📈 Range del punteggio di rischio: {{top_cases['risk_score'].min()}} a {{top_cases['risk_score'].max()}}")
print(f"💰 Range dell'importo: {{top_cases['importo_clean'].min()}} a {{top_cases['importo_clean'].max()}}")

# Salva il dataset supervisionato
supervised_path = base_path / 'training_supervised_10percent.csv'
top_cases.to_csv(supervised_path, index=False)
print(f"💾 Dataset supervisionato salvato in: {{supervised_path}}")

# Ora applichiamo le correzioni supervisionate dal feedback_operatore.csv se esiste
feedback_path = base_path / 'report' / 'feedback_operatore.csv'
if feedback_path.exists():
    print("🔄 Applicazione delle correzioni supervisionate dal feedback...")
    feedback_df = pd.read_csv(feedback_path)
    
    # Applica le correzioni ai dati
    for idx, feedback_row in feedback_df.iterrows():
        pdf_name = feedback_row['pdf_name']
        falso_positivo = str(feedback_row['falso_positivo']).strip().upper() == 'SI'
        
        mask_documento = df['pdf_name'] == pdf_name
        if mask_documento.any():
            if falso_positivo:
                df.loc[mask_documento, 'risk_score'] = 0.0
                df.loc[mask_documento, 'anomalie_rilevate'] = "Falso Positivo (Validato Umanamente)"
                
                # Aggiorna eventuali campi corretti dal feedback
                for campo in ['doc_type', 'responsabile', 'beneficiario', 'importo_max', 'cig', 'cup', 'data_atto', 'numero_atto', 'oggetto', 'category']:
                    if campo in feedback_df.columns and not pd.isna(feedback_row[campo]):
                        df.loc[mask_documento, campo] = feedback_row[campo]

    print("✅ Correzioni supervisionate applicate")

    # Riordina il dataset completo con i nuovi punteggi
    df_updated = df.sort_values(['risk_score', 'importo_clean'], ascending=[False, False])
    
    # Salva il dataset aggiornato
    updated_path = base_path / 'atti_audited_supervised.csv'
    df_updated.to_csv(updated_path, index=False)
    print(f"💾 Dataset aggiornato con supervisione umana salvato in: {{updated_path}}")

print("✅ Processo di riaddestramento supervisionato completato")
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
    
    return result.returncode

if __name__ == '__main__':
    cli()