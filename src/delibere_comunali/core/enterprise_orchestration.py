#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di orchestrazione enterprise con parametri configurabili
Consente di eseguire flussi di lavoro complessi con parametri facilmente configurabili
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Importa i componenti principali
from .orchestrator import CentralOrchestrator
from .data_coordinator import get_global_data_coordinator
from .config_manager import ConfigManager, get_enterprise_config
from ..utils.config import get_tenant_dir

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnterpriseOrchestrator:
    """
    Orchestrator enterprise con parametri configurabili
    """
    
    def __init__(self, ente: str, base_path: str = None, config_manager: ConfigManager = None):
        self.ente = ente
        self.base_path = base_path or str(get_tenant_dir(ente))
        self.config_manager = config_manager or get_enterprise_config(ente, self.base_path)
        
        # Crea l'orchestrator usando la configurazione
        self.orchestrator = self.config_manager.create_orchestrator()
        
        # Ottieni il coordinatore dati
        self.data_coordinator = get_global_data_coordinator()
        
        logger.info(f"Inizializzato EnterpriseOrchestrator per ente: {ente}")
    
    def run_workflow(self, 
                     workflow_type: str = "full",
                     custom_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Esegue un workflow specifico con parametri personalizzabili
        """
        params = custom_params or {}
        
        logger.info(f"Inizio esecuzione workflow: {workflow_type}")
        
        if workflow_type == "full":
            return self._run_full_analysis(params)
        elif workflow_type == "risk_only":
            return self._run_risk_analysis(params)
        elif workflow_type == "kpi_only":
            return self._run_kpi_analysis(params)
        elif workflow_type == "ml_only":
            return self._run_ml_analysis(params)
        elif workflow_type == "audit_only":
            return self._run_audit_analysis(params)
        elif workflow_type == "minimal":
            return self._run_minimal_analysis(params)
        else:
            raise ValueError(f"Tipo di workflow sconosciuto: {workflow_type}")
    
    def _run_full_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue l'analisi completa con tutti i moduli
        """
        skip_risk = params.get('skip_risk', False)
        skip_kpi = params.get('skip_kpi', False)
        skip_ml = params.get('skip_ml', False)
        skip_audit = params.get('skip_audit', False)
        load_data_path = params.get('load_data_path')
        
        results = self.orchestrator.run_full_coordination_pipeline(
            load_data_path=load_data_path,
            skip_risk=skip_risk,
            skip_kpi=skip_kpi,
            skip_ml=skip_ml,
            skip_audit=skip_audit
        )
        
        return results
    
    def _run_risk_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue solo l'analisi del rischio
        """
        load_data_path = params.get('load_data_path')
        
        # Carica i dati
        data = self.orchestrator.load_shared_data(load_data_path)
        
        # Esegui solo il risk assessment
        results = self.orchestrator.run_risk_assessment(data)
        
        return {
            'timestamp': results.get('timestamp', str()),
            'risk_results': results,
            'workflow_type': 'risk_only'
        }
    
    def _run_kpi_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue solo l'analisi KPI
        """
        load_data_path = params.get('load_data_path')
        
        # Carica i dati
        data = self.orchestrator.load_shared_data(load_data_path)
        
        # Esegui solo il calcolo KPI
        results = self.orchestrator.run_kpi_calculation(data)
        
        return {
            'timestamp': str(),
            'kpi_results': results,
            'workflow_type': 'kpi_only'
        }
    
    def _run_ml_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue solo l'analisi ML
        """
        load_data_path = params.get('load_data_path')
        
        # Carica i dati
        data = self.orchestrator.load_shared_data(load_data_path)
        
        # Esegui solo l'analisi ML
        results = self.orchestrator.run_ml_analysis(data)
        
        return {
            'timestamp': str(),
            'ml_results': results,
            'workflow_type': 'ml_only'
        }
    
    def _run_audit_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue solo l'analisi di audit
        """
        load_data_path = params.get('load_data_path')
        
        # Carica i dati
        data = self.orchestrator.load_shared_data(load_data_path)
        
        # Esegui solo l'analisi di audit
        results = self.orchestrator.run_audit_analysis(data)
        
        return {
            'timestamp': str(),
            'audit_results': results,
            'workflow_type': 'audit_only'
        }
    
    def _run_minimal_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue un'analisi minimale per test rapidi
        """
        load_data_path = params.get('load_data_path')
        
        # Carica i dati
        data = self.orchestrator.load_shared_data(load_data_path)
        
        # Esegui solo una parte limitata dell'analisi
        if data is not None and not data.empty:
            # Solo un campione limitato
            sample_data = data.head(10) if len(data) > 10 else data
            
            # Calcola solo alcuni risultati basilari
            results = {
                'sample_size': len(sample_data),
                'columns': list(sample_data.columns),
                'basic_stats': {
                    'total_docs': len(sample_data),
                    'date_range': 'N/A',
                    'doc_types': 'N/A'
                }
            }
        else:
            results = {'sample_size': 0, 'basic_stats': {}}
        
        return {
            'timestamp': str(),
            'minimal_results': results,
            'workflow_type': 'minimal'
        }


def main():
    """
    Funzione principale per l'orchestrazione enterprise da riga di comando
    """
    parser = argparse.ArgumentParser(description='Orchestrazione enterprise con parametri configurabili')
    parser.add_argument('--ente', type=str, required=True, help='Nome dell\'ente da analizzare')
    parser.add_argument('--base-path', type=str, help='Percorso base per i dati')
    parser.add_argument('--workflow', type=str, 
                       choices=['full', 'risk_only', 'kpi_only', 'ml_only', 'audit_only', 'minimal'],
                       default='full', help='Tipo di workflow da eseguire')
    parser.add_argument('--load-data', type=str, help='Percorso specifico per i dati parsati')
    parser.add_argument('--skip-risk', action='store_true', help='Salta l\'esecuzione del risk assessment')
    parser.add_argument('--skip-kpi', action='store_true', help='Salta l\'esecuzione del calcolo KPI')
    parser.add_argument('--skip-ml', action='store_true', help='Salta l\'esecuzione dell\'analisi ML')
    parser.add_argument('--skip-audit', action='store_true', help='Salta l\'esecuzione dell\'audit')
    parser.add_argument('--config-file', type=str, help='File di configurazione da caricare')
    parser.add_argument('--save-results', action='store_true', help='Salva i risultati in formato strutturato')
    parser.add_argument('--dry-run', action='store_true', help='Simula l\'esecuzione senza elaborare dati reali')
    parser.add_argument('--verbose', action='store_true', help='Modalità verbosa')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Carica la configurazione
    config_manager = get_enterprise_config(args.ente, args.base_path)
    
    # Carica la configurazione da file se specificato
    if args.config_file:
        config_manager.load_from_file(args.config_file)
    
    # Aggiorna i parametri in base agli argomenti
    custom_params = {
        'load_data_path': args.load_data,
        'skip_risk': args.skip_risk,
        'skip_kpi': args.skip_kpi,
        'skip_ml': args.skip_ml,
        'skip_audit': args.skip_audit
    }
    
    # Rimuovi i parametri non validi
    custom_params = {k: v for k, v in custom_params.items() if v is not None}
    
    if args.dry_run:
        logger.info("Modalità dry-run: simulazione dell'esecuzione...")
        print("Dry run completato. Nessun dato elaborato.")
        return
    
    try:
        # Crea l'orchestrator enterprise
        enterprise_orch = EnterpriseOrchestrator(
            ente=args.ente,
            base_path=args.base_path,
            config_manager=config_manager
        )
        
        # Esegui il workflow
        results = enterprise_orch.run_workflow(
            workflow_type=args.workflow,
            custom_params=custom_params
        )
        
        # Stampa i risultati
        print("\n=== RISULTATI ORCHESTRAZIONE ENTERPRISE ===")
        print(json.dumps(results, indent=2, default=str))
        
        # Salva i risultati se richiesto
        if args.save_results:
            output_dir = Path(config_manager.base_path) / "report"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"enterprise_results_{args.workflow}_{args.ente}_{str().replace(':', '-')}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Risultati salvati in: {output_file}")
        
        # Stampa un riassunto
        print(f"\nWorkflow '{args.workflow}' completato per ente '{args.ente}'")
        print(f"Tempo totale: N/A")  # In una versione futura aggiungeremo il timing
        print(f"Risultati salvati: {'Sì' if args.save_results else 'No'}")
        
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del workflow: {e}")
        print(f"Errore: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()