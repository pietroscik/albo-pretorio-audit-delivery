#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del sistema di parameterizzazione enterprise
Questo script mostra come utilizzare i nuovi componenti per gestire
workflow complessi con parametri facilmente configurabili
"""

import os
import sys
from pathlib import Path

# Aggiungi src al path per importare i moduli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from delibere_comunali.core.config_manager import get_enterprise_config, EnterpriseParams
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator


def demo_basic_configuration():
    """
    Dimostra la configurazione di base del sistema enterprise
    """
    print("=== DEMONSTRAZIONE CONFIGURAZIONE BASE ===")
    
    # Creazione del gestore configurazione
    config_manager = get_enterprise_config(ente="comune_demo")
    
    print(f"Ente configurato: {config_manager.ente}")
    print(f"Percorso base: {config_manager.base_path}")
    
    # Visualizza la configurazione attiva
    active_config = config_manager.get_active_config()
    print(f"OCR disponibile: {active_config['app_config']['ocr']['enabled']}")
    print(f"LLM configurato: {active_config['app_config']['llm']['api_key_set']}")
    
    # Mostra i parametri enterprise
    ep = config_manager.enterprise_params
    print(f"Worker massimi: {ep.max_workers}")
    print(f"Elaborazione parallela: {ep.enable_parallel_processing}")
    

def demo_parameter_updates():
    """
    Dimostra come aggiornare i parametri in tempo reale
    """
    print("\n=== DEMONSTRAZIONE AGGIORNAMENTO PARAMETRI ===")
    
    config_manager = get_enterprise_config(ente="comune_demo")
    
    print(f"Parametri iniziali - Max workers: {config_manager.enterprise_params.max_workers}")
    
    # Aggiorna alcuni parametri
    config_manager.update_params(
        max_workers=2,
        enable_caching=False,
        similarity_threshold=0.6
    )
    
    print(f"Nuovi parametri - Max workers: {config_manager.enterprise_params.max_workers}")
    print(f"Caching abilitato: {config_manager.enterprise_params.enable_caching}")
    print(f"Soglia similarità: {config_manager.enterprise_params.similarity_threshold}")


def demo_validation():
    """
    Dimostra la funzionalità di validazione della configurazione
    """
    print("\n=== DEMONSTRAZIONE VALIDAZIONE CONFIGURAZIONE ===")
    
    config_manager = get_enterprise_config(ente="comune_demo")
    validation = config_manager.validate_config()
    
    print(f"Stato complessivo: {'VALIDO' if validation['overall_status'] else 'NON VALIDO'}")
    print(f"Ente valido: {validation['ente_valid']}")
    print(f"Percorso esistente: {validation['base_path_exists']}")
    
    print("Controllo servizi disponibili:")
    for service, available in validation['services_available'].items():
        print(f"  {service}: {'✓' if available else '✗'}")


def demo_workflow_simulation():
    """
    Simula un workflow enterprise (senza eseguirlo realmente)
    """
    print("\n=== SIMULAZIONE WORKFLOW ENTERPRISE ===")
    
    # Configura i parametri per una simulazione
    config_manager = get_enterprise_config(ente="comune_demo")
    config_manager.update_params(dry_run=True)
    
    print("Preparazione del workflow...")
    print(f"Ente: {config_manager.ente}")
    print(f"Tipo coordinamento: {config_manager.enterprise_params.enable_coordination}")
    print(f"Elaborazione parallela: {config_manager.enterprise_params.enable_parallel_processing}")
    
    # Simula la creazione dell'orchestrator
    print("\nCreazione EnterpriseOrchestrator...")
    try:
        # Creiamo un orchestrator ma non eseguiamo nulla in realtà
        orchestrator = config_manager.create_orchestrator()
        print(f"Orchestrator creato con {orchestrator.max_workers} worker")
        print(f"Cache abilitata: {orchestrator.coordination_params['use_caching']}")
        print(f"Parallelizzazione: {orchestrator.coordination_params['parallel_execution']}")
    except Exception as e:
        print(f"Simulazione creazione orchestrator: {e}")


def demo_recommendations():
    """
    Mostra le raccomandazioni automatiche
    """
    print("\n=== RACCOMANDAZIONI AUTOMATICHE ===")
    
    config_manager = get_enterprise_config(ente="comune_demo")
    recommendations = config_manager.get_param_recommendations()
    
    print("Raccomandazioni basate sulle risorse di sistema:")
    for key, value in recommendations.items():
        if key != 'system_specs':
            print(f"  {key}: {value}")
    
    print(f"\nSpecifiche di sistema:")
    for spec, value in recommendations['system_specs'].items():
        print(f"  {spec}: {value}")


def main():
    """
    Funzione principale che esegue tutte le dimostrazioni
    """
    print("DEMO SISTEMA DI PARAMETERIZZAZIONE ENTERPRISE")
    print("=" * 50)
    
    try:
        demo_basic_configuration()
        demo_parameter_updates()
        demo_validation()
        demo_workflow_simulation()
        demo_recommendations()
        
        print("\n" + "=" * 50)
        print("DEMO COMPLETATA CON SUCCESSO")
        print("\nPer eseguire workflow reali, usa i comandi:")
        print("  python run.py enterprise --ente=NOME_ENTE --workflow=full")
        print("  python run.py config-mgmt --ente=NOME_ENTE --action=show")
        
    except Exception as e:
        print(f"Errore durante la demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()