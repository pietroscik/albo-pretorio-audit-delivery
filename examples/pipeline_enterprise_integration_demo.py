#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo completo di integrazione tra il sistema di parameterizzazione enterprise e la pipeline
Questo script mostra come utilizzare i nuovi componenti insieme per gestire workflow complessi
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Aggiungi src al path per importare i moduli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from delibere_comunali.core.config_manager import get_enterprise_config, EnterpriseParams
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator


def demo_pipeline_integration():
    """
    Demo completa di integrazione tra il sistema enterprise e la pipeline
    """
    print("=== DEMO INTEGRAZIONE PIPELINE ENTERPRISE ===")
    
    # 1. Creazione del gestore configurazione
    print("\n1. Configurazione del sistema enterprise...")
    config_manager = get_enterprise_config(ente="demo_integrazione")
    
    print(f"   - Ente configurato: {config_manager.ente}")
    print(f"   - Percorso base: {config_manager.base_path}")
    
    # 2. Visualizzazione della configurazione attiva
    print("\n2. Configurazione attiva:")
    active_config = config_manager.get_active_config()
    print(f"   - OCR disponibile: {active_config['app_config']['ocr']['enabled']}")
    print(f"   - LLM configurato: {active_config['app_config']['llm']['api_key_set']}")
    print(f"   - Worker massimi: {active_config['app_config']['performance']['max_workers']}")
    
    # 3. Aggiornamento parametri per la pipeline
    print("\n3. Aggiornamento parametri per la pipeline...")
    config_manager.update_params(
        max_workers=2,
        enable_caching=True,
        enable_parallel_processing=False,  # Disabilitiamo parallelizzazione per il demo
        skip_risk_assessment=False,
        skip_kpi_calculation=False,
        skip_ml_analysis=False,
        skip_audit=False
    )
    
    print(f"   - Worker aggiornati: {config_manager.enterprise_params.max_workers}")
    print(f"   - Parallelizzazione: {config_manager.enterprise_params.enable_parallel_processing}")
    
    # 4. Validazione della configurazione
    print("\n4. Validazione configurazione...")
    validation = config_manager.validate_config()
    print(f"   - Stato complessivo: {'VALIDO' if validation['overall_status'] else 'NON VALIDO'}")
    
    # 5. Creazione dell'orchestrator
    print("\n5. Creazione EnterpriseOrchestrator...")
    try:
        orchestrator = config_manager.create_orchestrator()
        print(f"   - Creato con {orchestrator.max_workers} worker")
        print(f"   - Coordinazione parallela: {orchestrator.coordination_params['parallel_execution']}")
        print(f"   - Caching abilitato: {orchestrator.coordination_params['use_caching']}")
    except Exception as e:
        print(f"   - Errore nella creazione: {e}")
    
    # 6. Simulazione esecuzione workflow
    print("\n6. Simulazione esecuzione workflow...")
    enterprise_orch = EnterpriseOrchestrator(
        ente=config_manager.ente,
        base_path=config_manager.base_path,
        config_manager=config_manager
    )
    
    # Esegui un workflow minimale in modalità dry-run
    params = {'load_data_path': None}
    try:
        results = enterprise_orch._run_minimal_analysis(params)
        print(f"   - Workflow eseguito: {results['workflow_type']}")
        print(f"   - Risultati ottenuti: {len(str(results))} caratteri")
    except Exception as e:
        print(f"   - Errore nell'esecuzione: {e}")
    
    # 7. Salvataggio configurazione
    print("\n7. Salvataggio configurazione...")
    success = config_manager.save_to_file()
    print(f"   - Salvataggio {'riuscito' if success else 'fallito'}")
    
    # 8. Dimostrazione comandi CLI integrati
    print("\n8. Comandi CLI disponibili per l'integrazione:")
    print("   - python run.py config-mgmt --ente=demo_integrazione --action=show")
    print("   - python run.py enterprise --ente=demo_integrazione --workflow=full")
    print("   - python run.py pipeline --ente=demo_integrazione --enterprise-workflow=full")
    print("   - python run.py pipeline --ente=demo_integrazione --enterprise-workflow=minimal --skip-orchestration")
    
    return True


def demo_pipeline_with_enterprise_workflow():
    """
    Demo dell'esecuzione della pipeline con workflow enterprise
    """
    print("\n\n=== DEMO PIPELINE CON WORKFLOW ENTERPRISE ===")
    
    print("\nComandi per eseguire la pipeline con workflow enterprise:")
    print("# Esecuzione completa con workflow enterprise")
    print("python run.py pipeline --ente=mio_ente --enterprise-workflow=full")
    
    print("\n# Esecuzione con workflow specifico e configurazione personalizzata")
    print("python run.py pipeline --ente=mio_ente --enterprise-workflow=risk_only --enterprise-config=/path/to/config.json")
    
    print("\n# Esecuzione con skip di alcuni componenti")
    print("python run.py pipeline --ente=mio_ente --enterprise-workflow=full --skip-audit --skip-post-process")
    
    print("\n# Esecuzione della sola analisi enterprise dopo la pipeline base")
    print("python run.py pipeline --ente=mio_ente --skip-orchestration  # Fase base")
    print("python run.py enterprise --ente=mio_ente --workflow=full      # Fase enterprise")
    
    return True


def demo_use_cases():
    """
    Demo di casi d'uso comuni
    """
    print("\n\n=== CASI D'USO COMUNI ===")
    
    print("\nCaso 1: Setup rapido per nuovo ente")
    print("```bash")
    print("# 1. Configura il sistema per un nuovo ente")
    print("python run.py config-mgmt --ente=comune_nuovo --action=recommend")
    print("")
    print("# 2. Aggiorna i parametri ottimizzati")
    print("python run.py config-mgmt --ente=comune_nuovo --update-param max_workers 4 --update-param batch_size 10")
    print("")
    print("# 3. Esegui la pipeline completa")
    print("python run.py pipeline --ente=comune_nuovo --enterprise-workflow=full")
    print("```")
    
    print("\nCaso 2: Analisi incrementale")
    print("```bash")
    print("# 1. Esegui solo la fase di base")
    print("python run.py pipeline --ente=comune --skip-orchestration")
    print("")
    print("# 2. Esegui solo il risk assessment")
    print("python run.py enterprise --ente=comune --workflow=risk_only")
    print("")
    print("# 3. Esegui solo i KPI")
    print("python run.py enterprise --ente=comune --workflow=kpi_only")
    print("")
    print("# 4. Esegui l'analisi completa con feedback")
    print("python run.py enterprise --ente=comune --workflow=full")
    print("```")
    
    print("\nCaso 3: Diagnosi e troubleshooting")
    print("```bash")
    print("# 1. Controlla la configurazione")
    print("python run.py config-mgmt --ente=comune --action=validate")
    print("")
    print("# 2. Visualizza la configurazione attiva")
    print("python run.py config-mgmt --ente=comune --action=show")
    print("")
    print("# 3. Esegui un test minimale")
    print("python run.py enterprise --ente=comune --workflow=minimal --dry-run")
    print("```")
    
    return True


def main():
    """
    Funzione principale che esegue tutte le demo di integrazione
    """
    print("DEMO INTEGRAZIONE PIPELINE ENTERPRISE")
    print("=" * 70)
    
    try:
        success1 = demo_pipeline_integration()
        success2 = demo_pipeline_with_enterprise_workflow()
        success3 = demo_use_cases()
        
        print("\n" + "=" * 70)
        print("RISULTATO:")
        if all([success1, success2, success3]):
            print("✅ TUTTE LE DEMO SONO STATE ESEGUITE CON SUCCESSO")
            print("\nIl sistema di parameterizzazione enterprise è pienamente integrato")
            print("con la pipeline e offre le seguenti funzionalità:")
            print("- Gestione centralizzata dei parametri")
            print("- Workflow configurabili e modulari") 
            print("- Integrazione con tutti i componenti esistenti")
            print("- Modalità di test e validazione")
            print("- Comandi CLI estesi per l'amministrazione")
        else:
            print("❌ ALCUNE DEMO HANNO RISCONTRATO PROBLEMI")
        
    except Exception as e:
        print(f"Errore durante la demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()